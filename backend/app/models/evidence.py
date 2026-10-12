import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class EvidenceType(str, enum.Enum):
    """Supported evidence categories."""
    INVOICE = "INVOICE"
    WARRANTY = "WARRANTY"
    REPAIR_RECEIPT = "REPAIR_RECEIPT"
    SERVICE_COMMUNICATION = "SERVICE_COMMUNICATION"
    OTHER = "OTHER"


class ExtractionStatus(str, enum.Enum):
    """Text extraction result statuses."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    NO_TEXT_FOUND = "NO_TEXT_FOUND"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class Evidence(Base):
    """Persistent repair case evidence model."""
    __tablename__ = "evidence"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    case_id = Column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename = Column(String(255), nullable=False)
    storage_filename = Column(String(255), nullable=False, unique=True)
    relative_storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_extension = Column(String(16), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    evidence_type = Column(
        SQLEnum(EvidenceType, native_enum=False),
        nullable=False,
        default=EvidenceType.OTHER,
    )
    extracted_text = Column(Text, nullable=True)
    extraction_status = Column(
        SQLEnum(ExtractionStatus, native_enum=False),
        nullable=False,
        default=ExtractionStatus.PENDING,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        index=True,
    )

    # Relationship back to parent case
    case = relationship("Case", back_populates="evidence")

    __table_args__ = (
        Index("ix_evidence_case_id_created_at", "case_id", "created_at"),
    )
