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
from app.ml.explain import build_explainer, explain_customer
from app.ml.cohort import build_cohort_index, find_similar_cohort


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


def test_explanations_add_up_to_the_prediction(tmp_path):
    customers = make_customers()
    for position, customer in enumerate(customers, start=1):
        customer.id = position  # never stored in the database, only used to train
    result = train_churn_model(customers_to_frame(customers), labels_of(customers))
    save_model(result, base_dir=tmp_path)
    explainer = build_explainer(load_current_model(tmp_path), customers[:100])

    for customer in customers[:30]:
        out = explain_customer(explainer, customer)
        total = (
            out["base_log_odds"]
            + sum(item["impact"] for item in out["contributions"])
            + out["other_impact"]
        )
        logit = float(np.log(out["probability"] / (1 - out["probability"])))
        assert abs(total - logit) < 1e-4  # SHAP contributions add up to the prediction
        assert all(item["direction"] in ("raises", "lowers") for item in out["contributions"])

    # A short-tenure, month-to-month customer: tenure or contract should lead
    risky = Customer(
        id=9001,
        tenure_months=2,
        monthly_revenue=Decimal("60"),
        source_attributes={"Contract": "Month-to-month"},
    )
    top = explain_customer(explainer, risky)["contributions"][0]
    assert top["label"] in ("Tenure (months)", "Contract")
    assert top["direction"] == "raises"


def test_explanation_endpoint(client, db_session, monkeypatch, tmp_path):
    customers = make_customers()
    db_session.add_all(customers)
    db_session.flush()
    result = train_churn_model(customers_to_frame(customers), labels_of(customers))
    save_model(result, base_dir=tmp_path)
    monkeypatch.setattr(artifacts, "DEFAULT_MODELS_DIR", tmp_path)

    stayed = next(c for c in customers if not c.churned)
    url = f"/api/v1/churn/customers/{stayed.id}/explanation"

    body = client.get(url).json()  # not scored yet: nothing to explain
    assert body["available"] is False
    assert "No estimate yet" in body["message"]

    score_customers(db_session, [stayed], load_current_model(tmp_path))
    body = client.get(url).json()
    assert body["available"] is True
    assert body["contributions"]
    assert 0.0 <= body["probability"] <= 1.0

    left = next(c for c in customers if c.churned)
    body = client.get(f"/api/v1/churn/customers/{left.id}/explanation").json()
    assert body["available"] is False
    assert "already left" in body["message"]


def test_explanation_without_a_model(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "DEFAULT_MODELS_DIR", tmp_path)  # empty: no model
    customer = Customer(external_id="ZZP-NOEXPLAIN")
    db_session.add(customer)
    db_session.flush()

    body = client.get(f"/api/v1/churn/customers/{customer.id}/explanation").json()
    assert body["available"] is False
    assert "No model" in body["message"]




def test_similar_cohort_calculation(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, "DEFAULT_MODELS_DIR", tmp_path)

    # train_churn_model requires at least 200 customers
    customers = make_customers(360)
    db_session.add_all(customers)
    db_session.flush()

    df = customers_to_frame(customers)
    y = labels_of(customers)
    result = train_churn_model(df, y, random_state=42)
    save_model(result, base_dir=tmp_path)

    # Pick one customer to find peers for
    target = customers[0]
    cohort_data = find_similar_cohort(db_session, target, k=10)

    assert cohort_data["available"] is True
    assert cohort_data["total_similar"] == 10
    assert cohort_data["churned_count"] + cohort_data["retained_count"] == 10
    assert 0.0 <= cohort_data["historical_churn_rate"] <= 1.0
    assert len(cohort_data["similar_customers"]) == 10
    # Make sure target is not comparing to itself
    assert all(c["id"] != target.id for c in cohort_data["similar_customers"])


def test_cohort_endpoint_without_model(client, db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "DEFAULT_MODELS_DIR", tmp_path)
    customer = Customer(external_id="ZZP-TEST", churned=False)
    db_session.add(customer)
    db_session.flush()

    response = client.get(f"/api/v1/churn/customers/{customer.id}/cohort")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert "No model has been trained yet" in data["message"]