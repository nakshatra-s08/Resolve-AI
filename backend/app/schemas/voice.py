from typing import Optional
from pydantic import BaseModel

class TranscriptionResponse(BaseModel):
    """Schema returned after successful audio transcription."""
    transcript: str
    detected_language: Optional[str] = None
    model: Optional[str] = None
