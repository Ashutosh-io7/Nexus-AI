"""Prediction service tests. Customers here are made-up test data."""

from decimal import Decimal

import numpy as np
import pandas as pd

from app.ml import artifacts
from app.ml.artifacts import load_current_model, save_model
from app.ml.features import customers_to_frame
from app.ml.predictor import eligible_customers, risk_level, score_customers
from app.ml.training import train_churn_model
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer


def make_customers(n=360):
    """Made-up customers where short tenure + month-to-month contracts leave more."""
    rng = np.random.default_rng(3)
    customers = []
    for i in range(n):
        tenure = int(rng.integers(0, 72))
        month_to_month = bool(rng.random() < 0.5)
        chance = 1 / (1 + np.exp(-(-1.0 - 0.04 * tenure + 1.5 * month_to_month)))
        customers.append(
            Customer(
                external_id=f"ZZP-{i:04d}",
                tenure_months=tenure,
                monthly_revenue=Decimal(str(round(float(rng.uniform(20, 100)), 2))),
                source_attributes={
                    "Contract": "Month-to-month" if month_to_month else "Two year"
                },
                churned=bool(rng.random() < chance),
            )
        )
    return customers


def labels_of(customers):
    return pd.Series([1 if c.churned else 0 for c in customers])


def test_risk_level_cutoffs():
    assert risk_level(0.05) == "low"
    assert risk_level(0.30) == "medium"
    assert risk_level(0.49) == "medium"
    assert risk_level(0.50) == "high"


def test_customers_who_already_left_are_not_scored(db_session):
    left = Customer(external_id="ZZP-LEFT", churned=True)
    stayed = Customer(external_id="ZZP-STAYED", churned=False)
    unknown = Customer(external_id="ZZP-UNKNOWN")
    db_session.add_all([left, stayed, unknown])
    db_session.flush()

    ids = {c.id for c in eligible_customers(db_session)}
    assert left.id not in ids
    assert stayed.id in ids and unknown.id in ids


def test_scoring_stores_one_prediction_per_customer(db_session, tmp_path):
    labeled = make_customers()
    unlabeled = [
        Customer(
            external_id=f"ZZP-U{i}",
            tenure_months=3 + i,
            source_attributes={"Contract": "Month-to-month"},
        )
        for i in range(5)
    ]
    db_session.add_all(labeled + unlabeled)
    db_session.flush()

    result = train_churn_model(customers_to_frame(labeled), labels_of(labeled))
    save_model(result, base_dir=tmp_path)
    bundle = load_current_model(tmp_path)

    targets = unlabeled + labeled[:5]
    assert score_customers(db_session, targets, bundle) == 10
    assert score_customers(db_session, targets, bundle) == 10  # again: no duplicates

    stored = (
        db_session.query(ChurnPrediction)
        .filter(ChurnPrediction.customer_id.in_([c.id for c in targets]))
        .all()
    )
    assert len(stored) == 10
    assert all(0.0 <= row.churn_probability <= 1.0 for row in stored)

    by_customer = {row.customer_id: row for row in stored}
    assert all(by_customer[c.id].in_training_data is False for c in unlabeled)
    trained = set(result.training_customer_ids)
    for customer in labeled[:5]:
        assert by_customer[customer.id].in_training_data == (customer.id in trained)


def test_churn_endpoints_without_a_model(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "DEFAULT_MODELS_DIR", tmp_path)  # empty: no model
    customer = Customer(external_id="ZZP-NOMODEL")
    db_session.add(customer)
    db_session.flush()

    status = client.get("/api/v1/churn/model").json()
    assert status["available"] is False
    assert "No model" in status["message"]

    assert client.post("/api/v1/churn/predictions").status_code == 409

    body = client.get(f"/api/v1/churn/customers/{customer.id}").json()
    assert body["available"] is False
    assert client.get("/api/v1/churn/customers/999999999").status_code == 404


def test_model_status_reports_real_metrics(client, monkeypatch, tmp_path):
    customers = make_customers()
    for position, customer in enumerate(customers, start=1):
        customer.id = position  # never stored in the database, only used to train
    result = train_churn_model(customers_to_frame(customers), labels_of(customers))
    save_model(result, base_dir=tmp_path)
    monkeypatch.setattr(artifacts, "DEFAULT_MODELS_DIR", tmp_path)

    body = client.get("/api/v1/churn/model").json()
    assert body["available"] is True
    assert body["version"] == result.metadata["version"]
    assert body["labeled_customers"] == 360
    assert 0.0 <= body["test_metrics"]["roc_auc"] <= 1.0