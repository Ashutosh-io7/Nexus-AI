"""Empirical cohort similarity: find historical accounts with closest behavioral profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml import artifacts
from app.ml.artifacts import current_model_version, load_current_model
from app.ml.features import FeatureSpec, customers_to_frame, prepare_matrix
from app.models.customer import Customer

MIN_HISTORICAL_CANDIDATES = 3
DEFAULT_COHORT_SIZE = 15


@dataclass
class CohortIndex:
    version: str
    customer_ids: list[int]
    customers: list[Customer]
    matrix: np.ndarray  # shape (N, D) preprocessed feature vectors
    spec: FeatureSpec
    prep: Any


_COHORT_CACHE: dict[tuple[str, str, int, int], CohortIndex] = {}


def build_cohort_index(
    bundle: dict[str, Any], candidates: Sequence[Customer]
) -> CohortIndex:
    if len(candidates) < MIN_HISTORICAL_CANDIDATES:
        raise ValueError(
            "Not enough historical labeled customers with known outcomes."
        )

    pipeline = bundle["pipeline"]
    spec: FeatureSpec = bundle["feature_spec"]
    prep = pipeline.named_steps["prep"]

    matrix_df = prepare_matrix(customers_to_frame(candidates), spec)
    transformed_matrix = prep.transform(matrix_df)

    return CohortIndex(
        version=bundle["metadata"]["version"],
        customer_ids=[c.id for c in candidates],
        customers=list(candidates),
        matrix=transformed_matrix,
        spec=spec,
        prep=prep,
    )


def get_cohort_index(db: Session) -> Optional[CohortIndex]:
    """Retrieve or build the cached feature matrix for all labeled historical customers."""
    version = current_model_version()
    if version is None:
        return None

    # Count labeled historical customers to auto-invalidate cache on imports
    stats = db.execute(
        select(
            func.count(Customer.id),
            func.coalesce(func.max(Customer.id), 0),
        ).where(Customer.churned.is_not(None))
    ).first()

    count, max_id = (stats[0], stats[1]) if stats else (0, 0)
    if count < MIN_HISTORICAL_CANDIDATES:
        return None

    key = (str(artifacts.DEFAULT_MODELS_DIR), version, int(count), int(max_id))
    if key in _COHORT_CACHE:
        return _COHORT_CACHE[key]

    bundle = load_current_model()
    if bundle is None:
        return None

    candidates = list(
        db.scalars(
            select(Customer)
            .where(Customer.churned.is_not(None))
            .order_by(Customer.id.asc())
        ).all()
    )

    index = build_cohort_index(bundle, candidates)
    _COHORT_CACHE[key] = index
    return index


def find_similar_cohort(
    db: Session,
    customer: Customer,
    k: int = DEFAULT_COHORT_SIZE,
    index: Optional[CohortIndex] = None,
) -> dict[str, Any]:
    """Find the top k most similar historical customers with known churn outcomes."""
    if index is None:
        index = get_cohort_index(db)

    if index is None:
        return {
            "available": False,
            "message": "Not enough historical labeled customers with known outcomes.",
        }

    # Transform target customer into the normalized model space
    target_df = customers_to_frame([customer])
    target_matrix = prepare_matrix(target_df, index.spec)
    target_vector = index.prep.transform(target_matrix)  # shape: (1, D)

    # Compute Euclidean distance to all historical candidate vectors
    diffs = index.matrix - target_vector
    dists = np.linalg.norm(diffs, axis=1)

    dim = target_vector.shape[1]
    # Similarity score scaled monotonically in (0, 1]
    similarities = 1.0 / (1.0 + (dists / np.sqrt(max(dim, 1))))

    # Exclude the target customer itself if they have a known outcome
    results = []
    for cand, dist, sim in zip(index.customers, dists, similarities):
        if cand.id == customer.id:
            continue
        results.append((cand, float(dist), float(sim)))

    if not results:
        return {
            "available": False,
            "message": "No other historical customers available for comparison.",
        }

    # Sort by distance ascending (closest first)
    results.sort(key=lambda item: item[1])
    top_matches = results[:k]

    churned_count = sum(1 for c, _, _ in top_matches if c.churned is True)
    retained_count = sum(1 for c, _, _ in top_matches if c.churned is False)
    total = len(top_matches)
    churn_rate = round(churned_count / total, 4) if total > 0 else 0.0

    tenures = [c.tenure_months for c, _, _ in top_matches if c.tenure_months is not None]
    avg_tenure = round(float(np.mean(tenures)), 1) if tenures else None

    mrrs = [float(c.monthly_revenue) for c, _, _ in top_matches if c.monthly_revenue is not None]
    avg_mrr = round(float(np.mean(mrrs)), 2) if mrrs else None

    similar_customers = [
        {
            "id": c.id,
            "external_id": c.external_id,
            "name": c.full_name or c.company_name or c.external_id,
            "subscription_plan": c.subscription_plan,
            "tenure_months": c.tenure_months,
            "monthly_revenue": float(c.monthly_revenue) if c.monthly_revenue is not None else None,
            "churned": c.churned,
            "similarity_score": round(sim, 4),
        }
        for c, dist, sim in top_matches
    ]

    return {
        "available": True,
        "total_similar": total,
        "churned_count": churned_count,
        "retained_count": retained_count,
        "historical_churn_rate": churn_rate,
        "avg_tenure_months": avg_tenure,
        "avg_monthly_revenue": avg_mrr,
        "similar_customers": similar_customers,
    }