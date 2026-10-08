from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))

    # Who the customer is
    senior_citizen: Mapped[bool]
    has_partner: Mapped[bool]
    has_dependents: Mapped[bool]

    # Subscription and billing
    tenure_months: Mapped[int]
    contract: Mapped[str] = mapped_column(String(20))
    paperless_billing: Mapped[bool]
    payment_method: Mapped[str] = mapped_column(String(40))
    monthly_charges: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    total_charges: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # Services they use
    phone_service: Mapped[bool]
    multiple_lines: Mapped[str] = mapped_column(String(25))
    internet_service: Mapped[str] = mapped_column(String(20))
    online_security: Mapped[str] = mapped_column(String(25))
    online_backup: Mapped[str] = mapped_column(String(25))
    device_protection: Mapped[str] = mapped_column(String(25))
    tech_support: Mapped[str] = mapped_column(String(25))
    streaming_tv: Mapped[str] = mapped_column(String(25))
    streaming_movies: Mapped[str] = mapped_column(String(25))

    # What actually happened
    churned: Mapped[bool]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )