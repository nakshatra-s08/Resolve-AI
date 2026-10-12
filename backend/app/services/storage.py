import os
import uuid
from pathlib import Path
from typing import Tuple
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
