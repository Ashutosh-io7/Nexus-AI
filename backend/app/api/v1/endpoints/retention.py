"""API endpoints for agentic retention actions and human-in-the-loop approvals."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.retention_graph import run_retention_agent
from app.db.session import get_db
from app.models.customer import Customer
from app.models.retention_action import RetentionAction
from app.schemas.retention import (
    RetentionActionGenerateResponse,
    RetentionActionResponse,
    RetentionStatusUpdateRequest,
)

router = APIRouter()


@router.post(
    "/customers/{customer_id}/generate",
    response_model=RetentionActionGenerateResponse,
    summary="Trigger the LangGraph agent to synthesize a policy-grounded retention plan",
)
def generate_customer_retention_action(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    if customer.churned is True:
        return RetentionActionGenerateResponse(
            available=False,
            message="Customer has already left, so no retention action can be generated.",
        )

    result = run_retention_agent(db, customer_id)
    if result.get("error"):
        return RetentionActionGenerateResponse(
            available=False,
            message=result["error"],
        )

    action_id = result.get("action_id")
    if not action_id:
        return RetentionActionGenerateResponse(
            available=False,
            message="Failed to persist retention action.",
        )

    action = db.get(RetentionAction, action_id)
    return RetentionActionGenerateResponse(
        available=True,
        action=RetentionActionResponse.model_validate(action, from_attributes=True),
    )


@router.get(
    "/customers/{customer_id}",
    response_model=RetentionActionGenerateResponse,
    summary="Get the latest proposed or approved retention plan for a customer",
)
def get_customer_retention_action(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    action = db.scalar(
        select(RetentionAction)
        .where(RetentionAction.customer_id == customer_id)
        .order_by(RetentionAction.id.desc())
    )

    if not action:
        return RetentionActionGenerateResponse(
            available=False,
            message="No retention plan generated yet for this customer.",
        )

    return RetentionActionGenerateResponse(
        available=True,
        action=RetentionActionResponse.model_validate(action, from_attributes=True),
    )


@router.patch(
    "/actions/{action_id}/status",
    response_model=RetentionActionResponse,
    summary="Approve, edit, or reject a proposed retention plan (Human-in-the-Loop)",
)
def update_retention_action_status(
    action_id: int,
    payload: RetentionStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    action = db.get(RetentionAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Retention action not found.")

    action.status = payload.status
    if payload.status == "approved":
        action.approved_at = datetime.now(timezone.utc)

    if payload.email_subject is not None:
        action.email_subject = payload.email_subject
    if payload.email_body is not None:
        action.email_body = payload.email_body
    if payload.csm_notes is not None:
        action.csm_notes = payload.csm_notes

    db.commit()
    db.refresh(action)
    return RetentionActionResponse.model_validate(action, from_attributes=True)