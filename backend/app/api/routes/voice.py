from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.schemas.voice import TranscriptionResponse
from app.services.gnani_stt import GnaniSTTService, GnaniSTTError

router = APIRouter(prefix="/voice", tags=["Voice Intake"])


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe recorded speech to text using Gnani Prisma STT",
    description=(
        "Accepts recorded browser audio in memory, submits it to the Gnani Prisma STT API "
        "via server-side credentials, and returns the machine-generated transcript for user review. "
        "Audio is processed in memory and never persisted."
    ),
)
async def transcribe_voice(
    file: UploadFile = File(..., description="Browser-recorded audio converted to WAV before upload"),
) -> TranscriptionResponse:
    service = GnaniSTTService()

    try:
        audio_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded audio stream: {str(exc)}",
        )

    try:
        result = service.transcribe(
            audio_bytes=audio_bytes,
            filename=file.filename or "recording.webm",
            content_type=file.content_type,
        )
    except GnaniSTTError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected error during transcription: {str(exc)}",
        )

    return TranscriptionResponse(
        transcript=result["transcript"],
        detected_language=result.get("detected_language"),
        model=result.get("model"),
    )
