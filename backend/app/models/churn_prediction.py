from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChurnPrediction(Base):
    """One churn estimate for one customer from one model version."""

    __tablename__ = "churn_predictions"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "model_version", name="uq_churn_predictions_customer_model"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    churn_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    # True when the model learned from this customer, so the estimate is optimistic.
    in_training_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )