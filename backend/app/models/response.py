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


class ResponseProcessingStatus(str, enum.Enum):
    """Processing lifecycle statuses for a simulated provider response."""
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class SimulatedResponse(Base):
    """Persistent simulated service provider response model."""
    __tablename__ = "simulated_responses"

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
    related_action_id = Column(
        String(36),
        ForeignKey("actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_name = Column(String(255), nullable=False, default="Simulated Service Provider")
    response_text = Column(Text, nullable=False)
    source_type = Column(String(32), nullable=False, default="SIMULATION")
    status = Column(
        SQLEnum(ResponseProcessingStatus, native_enum=False),
        nullable=False,
        default=ResponseProcessingStatus.RECEIVED,
        index=True,
    )
    processing_result_json = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        index=True,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="simulated_responses")
    related_action = relationship("Action", foreign_keys=[related_action_id])

    __table_args__ = (
        Index("ix_sim_responses_case_id_created_at", "case_id", "created_at"),
    )
