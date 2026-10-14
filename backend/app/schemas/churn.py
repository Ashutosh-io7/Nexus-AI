from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModelMetrics(BaseModel):
    """Results on customers the model never saw while learning."""

    roc_auc: float
    pr_auc: float
    no_skill_pr_auc: float
    precision: float
    recall: float
    f1: float
    threshold: float


class ModelStatusResponse(BaseModel):
    available: bool
    message: Optional[str] = None
    version: Optional[str] = None
    algorithm: Optional[str] = None
    trained_at: Optional[datetime] = None
    labeled_customers: Optional[int] = None
    churn_rate: Optional[float] = None
    test_rows: Optional[int] = None
    test_metrics: Optional[ModelMetrics] = None
    high_risk_cutoff: Optional[float] = None
    medium_risk_cutoff: Optional[float] = None


class PredictionRunResponse(BaseModel):
    model_version: str
    scored: int
    skipped_already_left: int


class CustomerPredictionResponse(BaseModel):
    available: bool
    message: Optional[str] = None
    churn_probability: Optional[float] = None
    risk_level: Optional[str] = None
    model_version: Optional[str] = None
    predicted_at: Optional[datetime] = None
    in_training_data: Optional[bool] = None


class FeatureContribution(BaseModel):
    feature: str
    label: str
    value: str
    impact: float      # log-odds units: a bigger size means a stronger push
    direction: str     # "raises" or "lowers" this customer's estimated risk


class CustomerExplanationResponse(BaseModel):
    available: bool
    message: Optional[str] = None
    model_version: Optional[str] = None
    probability: Optional[float] = None
    average_probability: Optional[float] = None
    contributions: list[FeatureContribution] = []
    other_impact: Optional[float] = None
    other_count: Optional[int] = None