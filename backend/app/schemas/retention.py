from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PolicyCitation(BaseModel):
    section_title: str
    page_number: int
    rule_summary: str


class RetentionActionResponse(BaseModel):
    id: int
    customer_id: int
    status: str  # "proposed", "approved", "rejected"
    churn_probability: float
    risk_level: str
    risk_drivers: list[dict[str, Any]] = []
    cohort_summary: Optional[dict[str, Any]] = None
    diagnosis: str
    action_strategy: str
    policy_citations: list[dict[str, Any]] = []
    email_subject: str
    email_body: str
    csm_notes: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RetentionActionGenerateResponse(BaseModel):
    available: bool
    message: Optional[str] = None
    action: Optional[RetentionActionResponse] = None


class RetentionStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(proposed|approved|rejected)$")
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    csm_notes: Optional[str] = None