"""Database model for storing AI-generated, policy-grounded retention actions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RetentionAction(Base):
    __tablename__ = "retention_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status lifecycle: "proposed" -> "approved" / "rejected" -> "executed"
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="proposed",
    )

    # Signals at time of generation
    churn_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_drivers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    cohort_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Agent output grounded in playbook
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    action_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    policy_citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Draft outreach
    email_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_body: Mapped[str] = mapped_column(Text, nullable=False)
    csm_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Human-in-the-loop audit timestamps
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer = relationship("Customer")