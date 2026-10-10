from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerBase(BaseModel):
    external_id: str = Field(..., max_length=100, description="Stable unique identifier from source system")
    full_name: Optional[str] = Field(None, max_length=120)
    email: Optional[str] = Field(None, max_length=255)
    company_name: Optional[str] = Field(None, max_length=160)
    subscription_plan: Optional[str] = Field(None, max_length=80)
    tenure_months: Optional[int] = Field(None, ge=0)
    monthly_revenue: Optional[Decimal] = Field(None, ge=0)
    usage_minutes_last_30d: Optional[Decimal] = Field(None, ge=0)
    logins_last_30d: Optional[int] = Field(None, ge=0)
    active_days_last_30d: Optional[int] = Field(None, ge=0, le=31)
    support_ticket_count: Optional[int] = Field(None, ge=0)
    unresolved_ticket_count: Optional[int] = Field(None, ge=0)
    payment_failures: Optional[int] = Field(None, ge=0)
    last_active_at: Optional[datetime] = None
    churned: Optional[bool] = None
    source_attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("external_id")
    @classmethod
    def validate_external_id(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("external_id cannot be blank.")
        return trimmed

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    subscription_plan: Optional[str] = None
    tenure_months: Optional[int] = Field(None, ge=0)
    monthly_revenue: Optional[Decimal] = Field(None, ge=0)
    usage_minutes_last_30d: Optional[Decimal] = Field(None, ge=0)
    logins_last_30d: Optional[int] = Field(None, ge=0)
    active_days_last_30d: Optional[int] = Field(None, ge=0, le=31)
    support_ticket_count: Optional[int] = Field(None, ge=0)
    unresolved_ticket_count: Optional[int] = Field(None, ge=0)
    payment_failures: Optional[int] = Field(None, ge=0)
    last_active_at: Optional[datetime] = None
    churned: Optional[bool] = None
    source_attributes: Optional[dict[str, Any]] = None


class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    limit: int
    offset: int
