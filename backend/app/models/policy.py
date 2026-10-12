import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    Index,
)
from app.database import Base


class PolicySourceType(str, enum.Enum):
    """Origin classification for policy documentation."""
    OFFICIAL = "OFFICIAL"
    ILLUSTRATIVE = "ILLUSTRATIVE"
    GUIDANCE = "GUIDANCE"


def get_utc_now() -> datetime:
    """Return current timestamp in UTC."""
    return datetime.now(timezone.utc)


class PolicySource(Base):
    """Persistent policy document and guidance model."""
    __tablename__ = "policy_sources"

    id = Column(
        String(64),
        primary_key=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    source_url = Column(String(512), nullable=True)
    source_type = Column(
        SQLEnum(PolicySourceType, native_enum=False),
        nullable=False,
        default=PolicySourceType.ILLUSTRATIVE,
    )
    jurisdiction = Column(String(64), nullable=True)
    product_category = Column(String(64), nullable=True)
    document_text = Column(Text, nullable=False)
    retrieved_at = Column(DateTime(timezone=True), nullable=True)
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

    __table_args__ = (
        Index("ix_policy_sources_category_jurisdiction", "product_category", "jurisdiction"),
    )
