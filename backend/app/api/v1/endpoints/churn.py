from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.artifacts import (
    ModelUnusableError,
    current_model_version,
    load_current_model,
)
from app.ml.predictor import (
    HIGH_RISK_CUTOFF,
    MEDIUM_RISK_CUTOFF,
    eligible_customers,
    score_customers,
)
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer
from app.schemas.churn import (
    CustomerPredictionResponse,
    ModelMetrics,
    ModelStatusResponse,
    PredictionRunResponse,
)

router = APIRouter()

NO_MODEL_MESSAGE = (
    "No model has been trained yet. Train one with: python -m app.ml.train_cli"
)


def _require_model() -> dict[str, Any]:
    try:
        bundle = load_current_model()
    except ModelUnusableError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if bundle is None:
        raise HTTPException(status_code=409, detail=NO_MODEL_MESSAGE)
    return bundle


@router.get(
    "/model",
    response_model=ModelStatusResponse,
    summary="Status and measured quality of the current churn model",
)
def get_model_status():
    try:
        bundle = load_current_model()
    except ModelUnusableError as exc:
        return ModelStatusResponse(available=False, message=str(exc))
    if bundle is None:
        return ModelStatusResponse(available=False, message=NO_MODEL_MESSAGE)

    meta = bundle["metadata"]
    chosen = meta["test_metrics"][meta["algorithm"]]
    return ModelStatusResponse(
        available=True,
        version=meta["version"],
        algorithm=meta["algorithm"],
        trained_at=meta["trained_at"],
        labeled_customers=meta["data"]["labeled_customers"],
        churn_rate=meta["data"]["churn_rate"],
        test_rows=meta["data"]["test_rows"],
        test_metrics=ModelMetrics(
            roc_auc=chosen["roc_auc"],
            pr_auc=chosen["pr_auc"],
            no_skill_pr_auc=chosen["churn_rate_in_test"],
            precision=chosen["precision"],
            recall=chosen["recall"],
            f1=chosen["f1"],
            threshold=chosen["threshold"],
        ),
        high_risk_cutoff=HIGH_RISK_CUTOFF,
        medium_risk_cutoff=MEDIUM_RISK_CUTOFF,
    )


@router.post(
    "/predictions",
    response_model=PredictionRunResponse,
    summary="Score every customer who has not already left",
)
def run_predictions(db: Session = Depends(get_db)):
    bundle = _require_model()
    scored = score_customers(db, eligible_customers(db), bundle)
    already_left = db.scalar(
        select(func.count()).select_from(Customer).where(Customer.churned.is_(True))
    ) or 0
    return PredictionRunResponse(
        model_version=bundle["metadata"]["version"],
        scored=scored,
        skipped_already_left=already_left,
    )


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerPredictionResponse,
    summary="Latest churn estimate for one customer",
)
def get_customer_prediction(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")

    version = current_model_version()
    if version is None:
        return CustomerPredictionResponse(available=False, message=NO_MODEL_MESSAGE)

    prediction = db.scalar(
        select(ChurnPrediction).where(
            ChurnPrediction.customer_id == customer_id,
            ChurnPrediction.model_version == version,
        )
    )
    if prediction is None:
        if customer.churned is True:
            message = "This customer has already left, so no risk estimate is made."
        else:
            message = "No estimate yet. Score customers from the Model page."
        return CustomerPredictionResponse(available=False, message=message)

    return CustomerPredictionResponse(
        available=True,
        churn_probability=prediction.churn_probability,
        risk_level=prediction.risk_level,
        model_version=prediction.model_version,
        predicted_at=prediction.predicted_at,
        in_training_data=prediction.in_training_data,
    )