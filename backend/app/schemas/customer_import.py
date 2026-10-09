from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImportErrorDetail(BaseModel):
    row: int
    field: Optional[str] = None
    value: Optional[str] = None
    error: str


class CustomerImportResponse(BaseModel):
    id: int
    filename: str
    total_rows: int
    inserted_count: int
    updated_count: int
    failed_count: int
    status: str
    error_summary: list[dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CSVPreviewResponse(BaseModel):
    total_columns: int
    headers: list[str]
    detected_mappings: dict[str, str] = Field(
        ...,
        description="Source column header mapped to target Customer model field"
    )
    unmapped_columns: list[str] = Field(
        ...,
        description="Columns that will be preserved in source_attributes JSONB"
    )
    sample_rows: list[dict[str, Any]] = Field(
        ...,
        description="First few parsed preview rows"
    )
