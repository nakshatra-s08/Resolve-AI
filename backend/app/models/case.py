import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base


class CaseStatus(str, enum.Enum):
    """Initial lifecycle statuses for a repair case."""
    NEW = "NEW"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTION_READY = "ACTION_READY"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# Documented valid status transitions dictionary
# Each status maps to the set of allowed destination statuses.
VALID_STATUS_TRANSITIONS = {
    CaseStatus.NEW: {
        CaseStatus.COLLECTING_EVIDENCE,
        CaseStatus.UNDER_REVIEW,
        CaseStatus.CLOSED,
    },
    CaseStatus.COLLECTING_EVIDENCE: {
        CaseStatus.UNDER_REVIEW,
        CaseStatus.ACTION_READY,
        CaseStatus.CLOSED,
    },
    CaseStatus.UNDER_REVIEW: {
        CaseStatus.COLLECTING_EVIDENCE,
        CaseStatus.ACTION_READY,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    },
    CaseStatus.ACTION_READY: {
        CaseStatus.COLLECTING_EVIDENCE,
        CaseStatus.AWAITING_RESPONSE,
        CaseStatus.CLOSED,
    },
    CaseStatus.AWAITING_RESPONSE: {
        CaseStatus.FOLLOW_UP_DUE,
        CaseStatus.UNDER_REVIEW,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    },
    CaseStatus.FOLLOW_UP_DUE: {
        CaseStatus.UNDER_REVIEW,
        CaseStatus.AWAITING_RESPONSE,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    },
    CaseStatus.RESOLVED: {
        CaseStatus.UNDER_REVIEW,  # Allowed reopening when issue recurs
        CaseStatus.CLOSED,
    },
    CaseStatus.CLOSED: {
        CaseStatus.UNDER_REVIEW,  # Allowed reopening if further work needed
    },
}


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class Case(Base):
    """Persistent repair case model."""
    __tablename__ = "cases"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    title = Column(String(255), nullable=False)
    product_name = Column(String(255), nullable=False)
    issue_description = Column(Text, nullable=False)
    status = Column(
        SQLEnum(CaseStatus, native_enum=False),
        nullable=False,
        default=CaseStatus.NEW,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        onupdate=get_utc_now,
    )

    # Relationship to timeline events with cascade delete
    events = relationship(
        "CaseEvent",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseEvent.created_at.asc()",
    )
