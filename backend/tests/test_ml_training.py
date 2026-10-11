"""ML pipeline tests. They use small made-up data (test data only, no database)."""

import numpy as np
import pandas as pd
import pytest

from app.ml.artifacts import load_current_model, save_model
from app.ml.features import infer_feature_spec, prepare_matrix
from app.ml.training import TrainingDataError, train_churn_model


def make_data(n=600, seed=0):
    """Made-up customers where short tenure + month-to-month contracts leave more."""
    rng = np.random.default_rng(seed)
    tenure = rng.integers(0, 72, n)
    contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.5, 0.3, 0.2])
    logit = -1.0 - 0.04 * tenure + 1.5 * (contract == "Month-to-month")
    left = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

    frame = pd.DataFrame({
        "customer_id": range(n),
        "tenure_months": tenure.astype(float),
        "monthly_revenue": rng.normal(60, 20, n).clip(5),
        "subscription_plan": rng.choice(["Basic", "Pro"], n),
        "extra__Contract": contract,
        "extra__Notes": [f"free text {i}" for i in range(n)],
        "extra__Constant": "x",
    })
    return frame, pd.Series(left)


def test_feature_spec_drops_ids_text_and_constants():
    frame, _ = make_data()
    spec = infer_feature_spec(frame)

    assert "tenure_months" in spec.numeric
    assert "extra__Contract" in spec.categorical
    assert "subscription_plan" in spec.categorical
    assert "extra__Notes" in spec.dropped      # looks like free text
    assert "extra__Constant" in spec.dropped   # same value everywhere
    assert "customer_id" not in spec.columns   # an ID is never a feature


def test_missing_values_stay_missing_not_zero():
    frame, _ = make_data()
    spec = infer_feature_spec(frame)
    frame.loc[0, "monthly_revenue"] = np.nan
    frame = frame.drop(columns=["extra__Contract"])  # column absent at prediction time

    matrix = prepare_matrix(frame, spec)
    assert np.isnan(matrix.loc[0, "monthly_revenue"])
    assert matrix["extra__Contract"].isna().all()


def test_training_reports_honest_metrics():
    frame, labels = make_data()
    result = train_churn_model(frame, labels)
    meta = result.metadata

    assert meta["algorithm"] in ("logistic_regression", "xgboost")
    assert meta["data"]["train_rows"] + meta["data"]["test_rows"] == 600
    for scores in meta["cross_validation"].values():  # no model may be silently skipped
        assert np.isfinite(scores["pr_auc_mean"]) and np.isfinite(scores["roc_auc_mean"])
    chosen = meta["test_metrics"][meta["algorithm"]]
    assert chosen["roc_auc"] > 0.6  # the made-up data has real signal
    assert sum(chosen["confusion"].values()) == meta["data"]["test_rows"]


def test_training_refuses_too_little_or_one_sided_data():
    frame, labels = make_data(n=100)
    with pytest.raises(TrainingDataError):
        train_churn_model(frame, labels)

    frame, labels = make_data()
    with pytest.raises(TrainingDataError):
        train_churn_model(frame, pd.Series(np.zeros(len(frame), dtype=int)))


def test_save_load_and_predict_on_new_data(tmp_path):
    frame, labels = make_data()
    result = train_churn_model(frame, labels)

    assert load_current_model(tmp_path) is None  # nothing trained yet
    save_model(result, base_dir=tmp_path)
    loaded = load_current_model(tmp_path)

    matrix = prepare_matrix(frame, loaded["feature_spec"])
    original = result.pipeline.predict_proba(prepare_matrix(frame, result.spec))[:, 1]
    assert np.allclose(loaded["pipeline"].predict_proba(matrix)[:, 1], original)

    # An unseen category and a missing column must not crash prediction
    new_customers = frame.head(5).copy()
    new_customers["extra__Contract"] = "Weekly"
    new_customers = new_customers.drop(columns=["monthly_revenue"])
    proba = loaded["pipeline"].predict_proba(
        prepare_matrix(new_customers, loaded["feature_spec"])
    )[:, 1]
    assert ((proba >= 0) & (proba <= 1)).all()