import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
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


class WorkflowStage(str, enum.Enum):
    """Lifecycle stages for agentic case orchestration."""
    INTAKE = "INTAKE"
    EVIDENCE_GATHERING = "EVIDENCE_GATHERING"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTION_PENDING = "ACTION_PENDING"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class WorkflowWaitState(str, enum.Enum):
    """Wait condition governing the orchestrator lifecycle."""
    NONE = "NONE"
    WAITING_FOR_USER_INPUT = "WAITING_FOR_USER_INPUT"
    WAITING_FOR_ACTION_APPROVAL = "WAITING_FOR_ACTION_APPROVAL"
    WAITING_FOR_EXTERNAL_RESPONSE = "WAITING_FOR_EXTERNAL_RESPONSE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class CaseWorkflowState(Base):
    """Persistent agentic workflow state model for a repair case."""
    __tablename__ = "case_workflow_states"

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
        unique=True,
        index=True,
    )
    goal = Column(
        String(500),
        nullable=False,
        default="Obtain warranty repair, replacement, or refund for repeated product defects.",
    )
    stage = Column(
        SQLEnum(WorkflowStage, native_enum=False),
        nullable=False,
        default=WorkflowStage.INTAKE,
    )
    wait_state = Column(
        SQLEnum(WorkflowWaitState, native_enum=False),
        nullable=False,
        default=WorkflowWaitState.NONE,
    )
    latest_recommendation = Column(Text, nullable=True)
    pending_evidence = Column(JSON, nullable=False, default=list)
    outstanding_commitments = Column(JSON, nullable=False, default=list)
    active_action_id = Column(
        String(36),
        ForeignKey("actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_reassessed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        onupdate=get_utc_now,
    )

    # Relationships
    case = relationship("Case", back_populates="workflow_state")
    active_action = relationship("Action", foreign_keys=[active_action_id])
