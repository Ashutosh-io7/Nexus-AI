from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    # Internal database ID
    id: Mapped[int] = mapped_column(primary_key=True)

    # Stable identifier supplied by the source system
    external_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    # Basic customer information
    full_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    company_name: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    # Subscription and revenue
    subscription_plan: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )
    tenure_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    monthly_revenue: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # Customer engagement
    usage_minutes_last_30d: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    logins_last_30d: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    active_days_last_30d: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Support and billing signals
    support_ticket_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    unresolved_ticket_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    payment_failures: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Historical outcome label for supervised ML training.
    # None means the outcome is unknown, not that the customer stayed.
    churned: Mapped[bool | None] = mapped_column(
        nullable=True,
    )

    # Preserve additional source columns without losing their values.
    source_attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )