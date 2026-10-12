"""Score customers with the current churn model and store the predictions."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ml.features import customers_to_frame, prepare_matrix
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer

# Default cutoffs, chosen from the training report's threshold trade-off table:
# 0.5 favours precision, 0.3 catches many more customers who go on to leave.
HIGH_RISK_CUTOFF = 0.5
MEDIUM_RISK_CUTOFF = 0.3

BATCH_SIZE = 1000


def risk_level(probability: float) -> str:
    if probability >= HIGH_RISK_CUTOFF:
        return "high"
    if probability >= MEDIUM_RISK_CUTOFF:
        return "medium"
    return "low"


def eligible_customers(db: Session) -> list[Customer]:
    """Customers who have not already left (outcome unknown, or stayed)."""
    return list(
        db.scalars(
            select(Customer).where(
                or_(Customer.churned.is_(None), Customer.churned.is_(False))
            )
        ).all()
    )


def score_customers(
    db: Session, customers: Sequence[Customer], bundle: dict[str, Any]
) -> int:
    """Predict and store one row per customer for the current model version."""
    if not customers:
        return 0

    frame = customers_to_frame(customers)
    matrix = prepare_matrix(frame, bundle["feature_spec"])
    probabilities = bundle["pipeline"].predict_proba(matrix)[:, 1]

    version = bundle["metadata"]["version"]
    training_ids = bundle["training_customer_ids"]

    rows = [
        {
            "customer_id": customer.id,
            "model_version": version,
            "churn_probability": float(probability),
            "risk_level": risk_level(float(probability)),
            # Customers the model learned from get optimistic estimates.
            "in_training_data": customer.id in training_ids,
        }
        for customer, probability in zip(customers, probabilities)
    ]

    for start in range(0, len(rows), BATCH_SIZE):
        statement = pg_insert(ChurnPrediction).values(rows[start:start + BATCH_SIZE])
        statement = statement.on_conflict_do_update(
            constraint="uq_churn_predictions_customer_model",
            set_={
                "churn_probability": statement.excluded.churn_probability,
                "risk_level": statement.excluded.risk_level,
                "in_training_data": statement.excluded.in_training_data,
                "predicted_at": func.now(),
            },
        )
        db.execute(statement)

    db.commit()
    return len(rows)