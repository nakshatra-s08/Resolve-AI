from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.case import CaseStatus


class CaseCreate(BaseModel):
    """Schema for creating a new repair case."""
    title: str = Field(
        ...,
        description="Title summarizing the repair case.",
        min_length=1,
        max_length=255,
    )
    product_name: str = Field(
        ...,
        description="Name of the product experiencing defects.",
        min_length=1,
        max_length=255,
    )
    issue_description: str = Field(
        ...,
        description="Detailed description of the issue or recurring fault.",
        min_length=1,
    )

    @field_validator("title", "product_name", "issue_description")
    @classmethod
    def validate_not_whitespace(cls, value: str, info) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty or whitespace only")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Repeated laptop repair failure",
                "product_name": "Laptop",
                "issue_description": "The same fault returned after two repairs.",
            }
        }
    )


class CaseRead(BaseModel):
    """Schema for returning case details."""
    id: str
    title: str
    product_name: str
    issue_description: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "e3a89047-36e2-45e0-8bc2-a279144ce10e",
                "title": "Repeated laptop repair failure",
                "product_name": "Laptop",
                "issue_description": "The same fault returned after two repairs.",
                "status": "NEW",
                "created_at": "2026-10-12T10:00:00Z",
                "updated_at": "2026-10-12T10:00:00Z",
            }
        },
    )
