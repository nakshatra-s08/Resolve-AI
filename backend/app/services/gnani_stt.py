import logging
from typing import Optional, Dict, Any
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

class GnaniSTTError(Exception):
    """Base exception for Gnani STT operations."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class GnaniNotConfiguredError(GnaniSTTError):
    """Raised when GNANI_PRISMA_API_KEY is not configured."""
    def __init__(self, message: str = "Gnani Prisma API key is not configured. Set GNANI_PRISMA_API_KEY in your backend/.env file."):
        super().__init__(message, status_code=503)

class AudioValidationError(GnaniSTTError):
    """Raised when the submitted audio file fails size or format validation."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class GnaniAuthenticationError(GnaniSTTError):
    """Raised when Gnani rejects the API key or its STT permissions."""
    def __init__(self, message: str):
        super().__init__(message, status_code=502)

class GnaniRateLimitError(GnaniSTTError):
    """Raised when Gnani returns 429 Too Many Requests."""
    def __init__(self, message: str = "Gnani API rate limit reached. Please try again shortly."):
        super().__init__(message, status_code=429)

class GnaniUpstreamError(GnaniSTTError):
    """Raised when Gnani returns a 5xx server error or network connection fails."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)


class GnaniSTTService:
    """Service to interact with the Gnani Prisma Speech-to-Text API (vachana.ai).

    Processes audio completely in memory and does not persist recordings.
    Keeps API credentials strictly server-side and never leaks them in logs or exceptions.
    """

    SUPPORTED_MIME_TYPES = {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
        "audio/flac",
        "audio/aac",
    }

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def validate_audio(self, audio_bytes: bytes, filename: str, content_type: Optional[str]) -> str:
        """Validate audio byte length and content type safely in memory."""
        if not audio_bytes or len(audio_bytes) < 100:
            raise AudioValidationError("Audio recording is empty or too short. Please speak clearly and record again.")

        if len(audio_bytes) > self.settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = self.settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise AudioValidationError(f"Audio file exceeds the maximum allowed size of {max_mb} MB.")

        clean_type = (content_type or "").split(";")[0].strip().lower()
        if clean_type not in self.SUPPORTED_MIME_TYPES:
            raise AudioValidationError(
                f"Unsupported audio format '{clean_type or 'unknown'}'. Gnani supports WAV, MP3, OGG, FLAC, AAC, and M4A."
            )

        return clean_type

    def transcribe(self, audio_bytes: bytes, filename: str = "recording.webm", content_type: Optional[str] = None) -> Dict[str, Any]:
        """Send audio to Gnani Prisma v3 endpoint and return the extracted transcript.

        Endpoint: POST https://api.vachana.ai/stt/v3
        Header: X-API-Key-ID: <KEY>
        """
        api_key = (self.settings.GNANI_PRISMA_API_KEY or "").strip()
        if not api_key:
            raise GnaniNotConfiguredError()

        normalized_mime = self.validate_audio(audio_bytes, filename, content_type)

        # Normalize filename extension for the API
        ext = ".wav"
        if "wav" in normalized_mime:
            ext = ".wav"
        elif "ogg" in normalized_mime:
            ext = ".ogg"
        elif "mp3" in normalized_mime or "mpeg" in normalized_mime:
            ext = ".mp3"
        elif "m4a" in normalized_mime or normalized_mime == "audio/mp4":
            ext = ".m4a"
        elif "flac" in normalized_mime:
            ext = ".flac"
        elif "aac" in normalized_mime:
            ext = ".aac"

        upload_filename = f"audio{ext}"

        endpoint_url = f"{self.settings.GNANI_PRISMA_BASE_URL.rstrip('/')}/stt/v3"
        headers = {
            "X-API-Key-ID": api_key,
        }

        form_data = {
            "model": self.settings.GNANI_PRISMA_MODEL,
            "language_code": self.settings.GNANI_PRISMA_LANGUAGE_CODE,
            "format": "transcribe",
        }

        files = {
            "audio_file": (upload_filename, audio_bytes, normalized_mime),
        }

        try:
            with httpx.Client(timeout=self.settings.GNANI_PRISMA_TIMEOUT_SECONDS) as client:
                response = client.post(
                    endpoint_url,
                    headers=headers,
                    data=form_data,
                    files=files,
                )
        except httpx.TimeoutException:
            logger.error("Gnani Prisma STT request timed out.")
            raise GnaniUpstreamError("Gnani transcription service timed out. Please try recording a shorter message.", status_code=504)
        except httpx.RequestError as exc:
            logger.error("Gnani Prisma STT connection error: %s", type(exc).__name__)
            raise GnaniUpstreamError("Unable to reach Gnani transcription service. Please check network connectivity.")

        if response.status_code == 401:
            logger.error("Gnani Prisma rejected the configured API key (HTTP 401).")
            raise GnaniAuthenticationError(
                "Gnani rejected this API key (HTTP 401). Create or copy an active Speech API key from your Gnani dashboard, update GNANI_PRISMA_API_KEY in backend/.env, and restart the backend."
            )

        if response.status_code == 403:
            logger.error("Gnani Prisma denied STT access for the configured API key (HTTP 403).")
            raise GnaniAuthenticationError(
                "This Gnani API key does not have Speech-to-Text access (HTTP 403). Enable the STT scope for the key in your Gnani account or contact Gnani support."
            )

        if response.status_code == 429:
            logger.warning("Gnani Prisma rate limit reached.")
            raise GnaniRateLimitError()

        if response.status_code >= 500:
            logger.error("Gnani Prisma upstream error (HTTP %d).", response.status_code)
            raise GnaniUpstreamError(f"Gnani transcription service error (HTTP {response.status_code}). Please try again later.")

        if response.status_code == 400:
            error_type = None
            try:
                error_payload = response.json()
                error_type = (error_payload.get("error") or {}).get("type")
            except (AttributeError, TypeError, ValueError):
                pass

            known_errors = {
                "UNSUPPORTED_AUDIO_FORMAT": "Gnani could not read this recording format. Record again and retry; the app converts recordings to WAV before upload.",
                "MAX_AUDIO_DURATION_EXCEEDED": "Gnani accepts recordings up to 30 seconds. Record a shorter description and retry.",
                "EMPTY_AUDIO": "The recording was empty. Record your description again and retry.",
            }
            message = known_errors.get(
                error_type,
                "Gnani rejected the audio (HTTP 400). The recording must be a supported audio file no longer than 30 seconds.",
            )
            raise AudioValidationError(message)

        if response.status_code != 200:
            logger.error("Gnani Prisma returned unexpected status HTTP %d.", response.status_code)
            raise GnaniUpstreamError(f"Gnani transcription service error (HTTP {response.status_code}).")

        try:
            res_json = response.json()
        except Exception:
            logger.error("Failed to parse JSON response from Gnani Prisma.")
            raise GnaniUpstreamError("Received an invalid response format from the transcription service.")

        # Extract transcript from known Gnani response formats
        transcript = ""
        if isinstance(res_json, dict):
            if not res_json.get("success", True) and "message" in res_json:
                error_msg = res_json.get("message", "Unknown error")
                raise GnaniUpstreamError(f"Transcription failed: {error_msg}")

            transcript = (
                res_json.get("transcript")
                or res_json.get("text")
                or (res_json.get("data", {}).get("transcript") if isinstance(res_json.get("data"), dict) else None)
                or (res_json.get("data", {}).get("text") if isinstance(res_json.get("data"), dict) else None)
                or ""
            )

        transcript = transcript.strip()
        if not transcript:
            raise AudioValidationError("No speech could be recognized in the recording. Please speak clearly into the microphone and try again.")

        detected_lang = res_json.get("detected_language_code") or res_json.get("language_code") or self.settings.GNANI_PRISMA_LANGUAGE_CODE
        model_used = res_json.get("model") or self.settings.GNANI_PRISMA_MODEL

        return {
            "transcript": transcript,
            "detected_language": detected_lang,
            "model": model_used,
        }
