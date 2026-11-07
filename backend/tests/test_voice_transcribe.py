import io
import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.config import get_settings


def test_transcribe_missing_api_key(client, monkeypatch):
    """When GNANI_PRISMA_API_KEY is not configured, the endpoint returns HTTP 503."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", None)

    fake_audio = b"RIFF" + b"\x00" * 200
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}

    response = client.post("/api/voice/transcribe", files=files)
    assert response.status_code == 503
    assert "Gnani Prisma API key is not configured" in response.json()["detail"]
    assert "GNANI_PRISMA_API_KEY in your backend/.env file" in response.json()["detail"]


def test_transcribe_empty_audio(client, monkeypatch):
    """When uploaded audio is empty or too small, returns HTTP 400."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    files = {"file": ("recording.wav", io.BytesIO(b"tiny"), "audio/wav")}
    response = client.post("/api/voice/transcribe", files=files)
    assert response.status_code == 400
    assert "empty or too short" in response.json()["detail"]


def test_transcribe_unsupported_format(client, monkeypatch):
    """When uploaded file is not a supported audio MIME type, returns HTTP 400."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_text = b"This is plain text and not audio." * 10
    files = {"file": ("notes.txt", io.BytesIO(fake_text), "text/plain")}
    response = client.post("/api/voice/transcribe", files=files)
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]


def test_transcribe_webm_rejected_before_upstream(client, monkeypatch):
    """Browser WebM must be converted to a Gnani-supported format first."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_audio = b"WEBM" + b"\x00" * 200
    files = {"file": ("recording.webm", io.BytesIO(fake_audio), "audio/webm")}
    response = client.post("/api/voice/transcribe", files=files)

    assert response.status_code == 400
    assert "Gnani supports WAV, MP3, OGG, FLAC, AAC, and M4A" in response.json()["detail"]


def test_transcribe_oversized_audio(client, monkeypatch):
    """When uploaded audio exceeds MAX_UPLOAD_SIZE_BYTES, returns HTTP 400."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 500)

    large_audio = b"\x00" * 600
    files = {"file": ("recording.wav", io.BytesIO(large_audio), "audio/wav")}
    response = client.post("/api/voice/transcribe", files=files)
    assert response.status_code == 400
    assert "exceeds the maximum allowed size" in response.json()["detail"]


def test_transcribe_success_mocked(client, monkeypatch):
    """When Gnani API responds with a successful transcript, returns 200 with transcript text."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_audio = b"RIFF" + b"\x00" * 250
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "success": True,
        "transcript": "Laptop thermal shutdown after motherboard replacement",
        "detected_language_code": "en-IN",
        "model": "prisma-v3.0",
    }

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch("app.services.gnani_stt.httpx.Client", return_value=mock_client_instance):
        response = client.post("/api/voice/transcribe", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["transcript"] == "Laptop thermal shutdown after motherboard replacement"
        assert data["detected_language"] == "en-IN"
        assert data["model"] == "prisma-v3.0"

        # Verify call parameters sent to Gnani
        mock_client_instance.post.assert_called_once()
        args, kwargs = mock_client_instance.post.call_args
        assert kwargs["headers"]["X-API-Key-ID"] == "test-gnani-key-12345"
        assert kwargs["data"]["model"] == "prisma-v3.0"
        assert kwargs["data"]["language_code"] == "indic-auto"


def test_transcribe_auth_failure(client, monkeypatch):
    """A rejected API key returns HTTP 502 with the key-renewal next step."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "invalid-key")

    fake_audio = b"RIFF" + b"\x00" * 250
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch("app.services.gnani_stt.httpx.Client", return_value=mock_client_instance):
        response = client.post("/api/voice/transcribe", files=files)
        assert response.status_code == 502
        assert "Gnani rejected this API key" in response.json()["detail"]
        assert "active Speech API key" in response.json()["detail"]


def test_transcribe_forbidden_scope(client, monkeypatch):
    """A key without the STT scope returns a distinct actionable message."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_audio = b"RIFF" + b"\x00" * 250
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}

    mock_resp = MagicMock()
    mock_resp.status_code = 403

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch("app.services.gnani_stt.httpx.Client", return_value=mock_client_instance):
        response = client.post("/api/voice/transcribe", files=files)
        assert response.status_code == 502
        assert "does not have Speech-to-Text access" in response.json()["detail"]


def test_transcribe_upstream_audio_error_is_explained(client, monkeypatch):
    """Gnani's unsupported audio response is translated into a useful client error."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_audio = b"RIFF" + b"\x00" * 250
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "success": False,
        "error": {"type": "UNSUPPORTED_AUDIO_FORMAT", "message": "Unsupported audio format."},
    }

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch("app.services.gnani_stt.httpx.Client", return_value=mock_client_instance):
        response = client.post("/api/voice/transcribe", files=files)

    assert response.status_code == 400
    assert "app converts recordings to WAV" in response.json()["detail"]


def test_transcribe_timeout(client, monkeypatch):
    """When Gnani API times out, returns HTTP 504."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_audio = b"RIFF" + b"\x00" * 250
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.side_effect = httpx.TimeoutException("Timeout")

    with patch("app.services.gnani_stt.httpx.Client", return_value=mock_client_instance):
        response = client.post("/api/voice/transcribe", files=files)
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"].lower()


def test_transcribe_empty_transcript_returned(client, monkeypatch):
    """When Gnani API returns success but empty transcript, returns HTTP 400."""
    settings = get_settings()
    monkeypatch.setattr(settings, "GNANI_PRISMA_API_KEY", "test-gnani-key-12345")

    fake_audio = b"RIFF" + b"\x00" * 250
    files = {"file": ("recording.wav", io.BytesIO(fake_audio), "audio/wav")}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "success": True,
        "transcript": "   ",
    }

    mock_client_instance = MagicMock()
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.post.return_value = mock_resp

    with patch("app.services.gnani_stt.httpx.Client", return_value=mock_client_instance):
        response = client.post("/api/voice/transcribe", files=files)
        assert response.status_code == 400
        assert "No speech could be recognized" in response.json()["detail"]
