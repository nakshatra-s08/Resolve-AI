import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
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
