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


class ActionType(str, enum.Enum):
    """Supported agent and case action types."""
    SEND_MESSAGE = "SEND_MESSAGE"
    SCHEDULE_FOLLOW_UP = "SCHEDULE_FOLLOW_UP"


class ActionStatus(str, enum.Enum):
    """Lifecycle statuses for case actions."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class Action(Base):
    """Persistent action and approval model."""
    __tablename__ = "actions"

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
    action_type = Column(
        SQLEnum(ActionType, native_enum=False),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(
        SQLEnum(ActionStatus, native_enum=False),
        nullable=False,
        default=ActionStatus.PENDING_APPROVAL,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        onupdate=get_utc_now,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    execution_result_json = Column(JSON, nullable=True)
    error_message = Column(String(512), nullable=True)

    # Relationship back to parent case
    case = relationship("Case", back_populates="actions")

    __table_args__ = (
        Index("ix_actions_case_id_status", "case_id", "status"),
    )
