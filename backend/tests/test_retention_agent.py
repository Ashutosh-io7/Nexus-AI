from decimal import Decimal
from app.agent.retention_graph import run_retention_agent
from app.models.customer import Customer
from app.models.retention_action import RetentionAction


def test_retention_agent_workflow(db_session):
    customer = Customer(
        external_id="ZZP-RET-01",
        full_name="Acme Logistics",
        subscription_plan="Pro",
        tenure_months=4,
        monthly_revenue=Decimal("120.00"),
        support_ticket_count=5,
        unresolved_ticket_count=2,
        payment_failures=1,
        churned=False,
    )
    db_session.add(customer)
    db_session.flush()

    result = run_retention_agent(db_session, customer.id)
    assert not result.get("error")
    assert result.get("action_id") is not None
    assert result.get("diagnosis")
    assert result.get("action_strategy")
    assert result.get("email_subject")
    assert result.get("email_body")

    action = db_session.get(RetentionAction, result["action_id"])
    assert action is not None
    assert action.status == "proposed"
    assert action.customer_id == customer.id


def test_retention_action_status_approval_api(client, db_session):
    customer = Customer(
        external_id="ZZP-RET-02",
        full_name="Beta Corp",
        churned=False,
    )
    db_session.add(customer)
    db_session.flush()

    action = RetentionAction(
        customer_id=customer.id,
        status="proposed",
        churn_probability=0.68,
        risk_level="high",
        diagnosis="Multiple unresolved support tickets.",
        action_strategy="Assign Solutions Architect and offer 50% credit.",
        email_subject="Resolving your tickets",
        email_body="Hi Beta Corp, let us resolve your tickets.",
    )
    db_session.add(action)
    db_session.flush()

    # Approve action
    res = client.patch(
        f"/api/v1/retention/actions/{action.id}/status",
        json={"status": "approved", "csm_notes": "Reviewed with account manager."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "approved"
    assert data["approved_at"] is not None
    assert data["csm_notes"] == "Reviewed with account manager."