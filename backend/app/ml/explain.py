"""Explain individual churn predictions with SHAP.

SHAP splits one customer's prediction into a contribution per feature. The
contributions are in log-odds units (not percentage points), and they add up:

    average prediction + all contributions = this customer's prediction

They show what the MODEL's estimate is based on. They do not prove why a
customer will leave, and they say nothing about support conversations.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np
import shap
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import artifacts
from app.ml.artifacts import current_model_version, load_current_model
from app.ml.features import EXTRA_PREFIX, FeatureSpec, customers_to_frame, prepare_matrix
from app.models.customer import Customer

BACKGROUND_SIZE = 300   # training customers used as the reference group
MIN_BACKGROUND = 20
TOP_FEATURES = 6        # features shown individually, the rest are combined

TYPED_LABELS = {
    "tenure_months": "Tenure (months)",
    "monthly_revenue": "Monthly revenue",
    "usage_minutes_last_30d": "Usage minutes (30 days)",
    "logins_last_30d": "Logins (30 days)",
    "active_days_last_30d": "Active days (30 days)",
    "support_ticket_count": "Support tickets",
    "unresolved_ticket_count": "Unresolved tickets",
    "payment_failures": "Payment failures",
    "subscription_plan": "Plan",
}


class ExplanationUnavailable(RuntimeError):
    """An explanation cannot be produced right now."""


@dataclass
class ExplainerBundle:
    version: str
    pipeline: Any
    spec: FeatureSpec
    explainer: Any
    groups: list[str]     # the original feature behind each model input column
    base_value: float     # average model output (log-odds) on the reference customers
    average_probability: float  # average predicted chance of leaving on those customers


def display_name(column: str) -> str:
    if column in TYPED_LABELS:
        return TYPED_LABELS[column]
    name = column[len(EXTRA_PREFIX):] if column.startswith(EXTRA_PREFIX) else column
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
    return name.strip()


def original_feature(transformed_name: str, spec: FeatureSpec) -> str:
    """Map a model input column (for example a one-hot column) back to its source feature."""
    if transformed_name.startswith("num__"):
        base = transformed_name[len("num__"):]
        if base.startswith("missingindicator_"):
            base = base[len("missingindicator_"):]
        return base
    if transformed_name.startswith("cat__"):
        base = transformed_name[len("cat__"):]
        for column in sorted(spec.categorical, key=len, reverse=True):
            if base.startswith(f"{column}_"):
                return column
    return transformed_name


def format_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Not provided"
    if isinstance(value, (float, np.floating)):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def build_explainer(bundle: dict[str, Any], background_customers: Sequence[Customer]) -> ExplainerBundle:
    if len(background_customers) < MIN_BACKGROUND:
        raise ExplanationUnavailable(
            "Too few of the customers the model learned from are still stored to explain predictions."
        )

    pipeline = bundle["pipeline"]
    spec: FeatureSpec = bundle["feature_spec"]
    prep = pipeline.named_steps["prep"]
    model = pipeline.named_steps["model"]

    reference_matrix = prepare_matrix(customers_to_frame(background_customers), spec)
    reference = prep.transform(reference_matrix)

    if bundle["metadata"]["algorithm"] == "xgboost":
        explainer = shap.TreeExplainer(model)
    else:
        explainer = shap.LinearExplainer(model, reference)

    groups = [original_feature(name, spec) for name in prep.get_feature_names_out()]
    base_value = float(np.ravel(explainer.expected_value)[0])
    return ExplainerBundle(
        version=bundle["metadata"]["version"],
        pipeline=pipeline,
        spec=spec,
        explainer=explainer,
        groups=groups,
        base_value=base_value,
        average_probability=float(pipeline.predict_proba(reference_matrix)[:, 1].mean()),
    )


def _shap_values(eb: ExplainerBundle, X: np.ndarray) -> np.ndarray:
    values = eb.explainer.shap_values(X)
    if isinstance(values, list):      # older SHAP versions: one array per class
        values = values[1]
    values = np.asarray(values)
    if values.ndim == 3:              # (rows, features, classes)
        values = values[:, :, 1]
    return values


def explain_customer(eb: ExplainerBundle, customer: Customer) -> dict[str, Any]:
    matrix = prepare_matrix(customers_to_frame([customer]), eb.spec)
    X = eb.pipeline.named_steps["prep"].transform(matrix)
    row_values = _shap_values(eb, X)[0]
    probability = float(eb.pipeline.predict_proba(matrix)[0, 1])

    totals: dict[str, float] = {}
    for group, value in zip(eb.groups, row_values):
        totals[group] = totals.get(group, 0.0) + float(value)

    ranked = sorted(
        (item for item in totals.items() if abs(item[1]) > 1e-9),
        key=lambda item: abs(item[1]),
        reverse=True,
    )
    shown, rest = ranked[:TOP_FEATURES], ranked[TOP_FEATURES:]

    return {
        "model_version": eb.version,
        "probability": probability,
        "average_probability": eb.average_probability,
        "base_log_odds": eb.base_value,
        "contributions": [
            {
                "feature": group,
                "label": display_name(group),
                "value": format_value(matrix.iloc[0][group]),
                "impact": impact,
                "direction": "raises" if impact > 0 else "lowers",
            }
            for group, impact in shown
        ],
        "other_impact": float(sum(impact for _, impact in rest)),
        "other_count": len(rest),
    }


_CACHE: dict[tuple[str, str], ExplainerBundle] = {}


def get_explainer(db: Session) -> Optional[ExplainerBundle]:
    """The explainer for the current model, built once and kept in memory."""
    version = current_model_version()
    if version is None:
        return None

    key = (str(artifacts.DEFAULT_MODELS_DIR), version)
    if key in _CACHE:
        return _CACHE[key]

    bundle = load_current_model()  # may raise ModelUnusableError
    if bundle is None:
        return None

    ids = sorted(bundle["training_customer_ids"])
    sample = random.Random(0).sample(ids, min(BACKGROUND_SIZE, len(ids)))
    customers = list(db.scalars(select(Customer).where(Customer.id.in_(sample))).all())

    explainer = build_explainer(bundle, customers)
    _CACHE[key] = explainer
    return explainer