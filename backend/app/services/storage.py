import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

import httpx
from fastapi import UploadFile, HTTPException, status
from app.config import get_settings

settings = get_settings()

SUPPORTED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}

# Magic byte signatures for client MIME spoofing detection
FILE_SIGNATURES = {
    b"%PDF": "pdf",
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
}


def _storage_backend() -> str:
    backend = (settings.UPLOAD_STORAGE_BACKEND or "local").strip().lower()
    if backend not in {"local", "supabase"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence storage is misconfigured. Choose local or supabase storage.",
        )
    if os.getenv("VERCEL") and backend != "supabase":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vercel evidence uploads require Supabase Storage. Configure UPLOAD_STORAGE_BACKEND=supabase.",
        )
    return backend


def _supabase_config() -> tuple[str, str, str, dict[str, str]]:
    base_url = (settings.SUPABASE_URL or "").strip().rstrip("/")
    service_key = (settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()
    bucket = (settings.SUPABASE_STORAGE_BUCKET or "case-evidence").strip()
    if not base_url or not service_key or not bucket:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Cloud evidence storage is not configured. Set SUPABASE_URL, "
                "SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_STORAGE_BUCKET in the backend environment."
            ),
        )
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }
    return base_url, bucket, service_key, headers


def _encoded_key(key: str) -> str:
    return "/".join(quote(part, safe="") for part in key.split("/"))


def _supabase_object_url(base_url: str, bucket: str, key: str) -> str:
    return f"{base_url}/storage/v1/object/{quote(bucket, safe='')}/{_encoded_key(key)}"


def _safe_storage_filename(storage_filename: str) -> bool:
    return bool(storage_filename) and Path(storage_filename).name == storage_filename and storage_filename not in {".", ".."}


async def _upload_to_supabase(storage_filename: str, content: bytes, mime_type: str) -> None:
    base_url, bucket, _, headers = _supabase_config()
    headers.update({"Content-Type": mime_type, "x-upsert": "false"})
    url = _supabase_object_url(base_url, bucket, f"uploads/{storage_filename}")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, content=content)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach cloud evidence storage.",
        ) from exc
    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloud evidence storage rejected the upload (HTTP {response.status_code}).",
        )


def _supabase_request(method: str, url: str, headers: dict[str, str], json: dict | None = None) -> httpx.Response:
    try:
        with httpx.Client(timeout=20.0) as client:
            return client.request(method, url, headers=headers, json=json)
    except httpx.RequestError:
        raise


def _move_supabase_object(source_key: str, target_key: str) -> httpx.Response:
    base_url, bucket, _, headers = _supabase_config()
    return _supabase_request(
        "POST",
        f"{base_url}/storage/v1/object/move",
        headers,
        json={"bucketId": bucket, "sourceKey": source_key, "destinationKey": target_key},
    )


def _delete_supabase_object(key: str) -> httpx.Response:
    base_url, bucket, _, headers = _supabase_config()
    return _supabase_request(
        "DELETE",
        f"{base_url}/storage/v1/object/{quote(bucket, safe='')}",
        headers,
        json={"prefixes": [key]},
    )


def get_upload_dir() -> Path:
    """Return the resolved Path to the upload directory and ensure it exists."""
    upload_path = Path(settings.UPLOAD_DIR).resolve()
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def sanitize_filename(filename: Optional[str]) -> str:
    """Return a sanitized basename without directory components."""
    if not filename:
        return "unnamed_document"
    # Take basename only to prevent directory traversal
    base = Path(filename).name
    # Strip dangerous characters
    clean = "".join(c for c in base if c.isalnum() or c in "._- ")
    return clean.strip() or "unnamed_document"


def validate_file_header(first_bytes: bytes, extension: str) -> bool:
    """Validate magic bytes against expected file extension."""
    if extension == "pdf":
        return first_bytes.startswith(b"%PDF")
    elif extension == "png":
        return first_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in {"jpg", "jpeg"}:
        return first_bytes.startswith(b"\xff\xd8\xff")
    return False


async def save_uploaded_file(file: UploadFile) -> Tuple[str, str, int, str, str, bytes]:
    """
    Validate, stream, and safely save uploaded file to local storage.
    Returns: (original_filename, storage_filename, file_size, relative_path, file_extension, full_content)
    """
    original_filename = sanitize_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension '.{extension}'. "
                f"Allowed formats: {sorted(list(SUPPORTED_EXTENSIONS))}."
            ),
        )

    expected_mimes = {
        "pdf": {"application/pdf", "application/octet-stream"},
        "png": {"image/png", "application/octet-stream"},
        "jpg": {"image/jpeg", "image/jpg", "application/octet-stream"},
        "jpeg": {"image/jpeg", "image/jpg", "application/octet-stream"},
    }
    declared_mime = (file.content_type or "application/octet-stream").lower()
    if declared_mime not in expected_mimes[extension]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Declared content type does not match file extension '.{extension}'.",
        )

    # Read bounded content to prevent arbitrary memory usage
    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    content = bytearray()
    chunk_size = 1024 * 1024  # 1MB chunks

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_size} bytes ({max_size // (1024*1024)} MB).",
            )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # Validate header signature
    if not validate_file_header(bytes(content[:16]), extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File contents do not match declared extension '.{extension}'.",
        )

    # Generate server-side unique storage filename
    storage_filename = f"{uuid.uuid4().hex}.{extension}"
    if _storage_backend() == "supabase":
        await _upload_to_supabase(storage_filename, bytes(content), declared_mime)
    else:
        upload_dir = get_upload_dir()
        dest_path = upload_dir / storage_filename
        try:
            dest_path.write_bytes(content)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file to disk storage.",
            ) from exc

    relative_path = f"uploads/{storage_filename}"
    return (
        original_filename,
        storage_filename,
        len(content),
        relative_path,
        extension,
        bytes(content),
    )


def remove_stored_file(storage_filename: str) -> bool:
    """Safely remove a stored file from the upload directory."""
    try:
        if not _safe_storage_filename(storage_filename):
            return False
        if _storage_backend() == "supabase":
            response = _delete_supabase_object(f"uploads/{storage_filename}")
            return response.status_code in (200, 204)

        upload_dir = get_upload_dir()
        target_path = (upload_dir / storage_filename).resolve()
        # Ensure target is strictly inside upload directory
        if upload_dir in target_path.parents and target_path.exists():
            target_path.unlink()
            return True
        elif target_path.exists():
            # If path traversal or weird directory resolved outside, reject
            return False
        return True  # If already absent, treat as cleanly removed
    except Exception:
        return False


def stage_stored_file_for_deletion(storage_filename: str) -> str | None:
    """Atomically move a stored file aside so a failed DB commit can restore it."""
    try:
        if not _safe_storage_filename(storage_filename):
            return None
        if _storage_backend() == "supabase":
            staged_name = f".deleting-{uuid.uuid4().hex}"
            response = _move_supabase_object(
                f"uploads/{storage_filename}",
                f"uploads/{staged_name}",
            )
            if response.status_code == 404:
                return ""
            return staged_name if response.status_code == 200 else None

        upload_dir = get_upload_dir()
        source = (upload_dir / storage_filename).resolve()
        if upload_dir not in source.parents:
            return None
        if not source.exists():
            return ""
        staged_name = f".deleting-{uuid.uuid4().hex}"
        source.replace(upload_dir / staged_name)
        return staged_name
    except Exception:
        return None


def restore_staged_file(storage_filename: str, staged_filename: str) -> bool:
    """Restore a staged file after a failed database transaction."""
    if not staged_filename:
        return True
    try:
        if not _safe_storage_filename(storage_filename) or not _safe_storage_filename(staged_filename):
            return False
        if _storage_backend() == "supabase":
            response = _move_supabase_object(
                f"uploads/{staged_filename}",
                f"uploads/{storage_filename}",
            )
            return response.status_code == 200

        upload_dir = get_upload_dir()
        staged = (upload_dir / staged_filename).resolve()
        target = (upload_dir / storage_filename).resolve()
        if upload_dir not in staged.parents or upload_dir not in target.parents:
            return False
        if not staged.exists():
            return False
        staged.replace(target)
        return True
    except Exception:
        return False


def discard_staged_file(staged_filename: str) -> bool:
    """Remove a staged file after the database deletion has committed."""
    if not staged_filename:
        return True
    try:
        if not _safe_storage_filename(staged_filename):
            return False
        if _storage_backend() == "supabase":
            response = _delete_supabase_object(f"uploads/{staged_filename}")
            return response.status_code in (200, 204)

        upload_dir = get_upload_dir()
        staged = (upload_dir / staged_filename).resolve()
        if upload_dir not in staged.parents:
            return False
        if staged.exists():
            staged.unlink()
        return True
    except Exception:
        return False
