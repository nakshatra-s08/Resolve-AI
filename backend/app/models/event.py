import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class EventType(str, enum.Enum):
    """Supported timeline event types."""
    CASE_CREATED = "CASE_CREATED"
    CASE_UPDATED = "CASE_UPDATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    NOTE_ADDED = "NOTE_ADDED"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    EVIDENCE_DELETED = "EVIDENCE_DELETED"
    ACTION_CREATED = "ACTION_CREATED"
    ACTION_UPDATED = "ACTION_UPDATED"
    ACTION_APPROVED = "ACTION_APPROVED"
    ACTION_REJECTED = "ACTION_REJECTED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_FAILED = "ACTION_FAILED"
    SIMULATED_RESPONSE_RECEIVED = "SIMULATED_RESPONSE_RECEIVED"
    RESPONSE_PROCESSED = "RESPONSE_PROCESSED"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class EventSource(str, enum.Enum):
    """Supported origin types for timeline events."""
    USER = "USER"
    SYSTEM = "SYSTEM"
    SIMULATION = "SIMULATION"


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class CaseEvent(Base):
    """Persistent chronological case event model."""
    __tablename__ = "case_events"

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
    event_type = Column(
        SQLEnum(EventType, native_enum=False),
        nullable=False,
    )
    description = Column(Text, nullable=False)
    source_type = Column(
        SQLEnum(EventSource, native_enum=False),
        nullable=False,
        default=EventSource.SYSTEM,
    )
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        index=True,
    )

    # Relationship back to parent case
    case = relationship("Case", back_populates="events")

    __table_args__ = (
        Index("ix_case_events_case_id_created_at", "case_id", "created_at"),
    )
