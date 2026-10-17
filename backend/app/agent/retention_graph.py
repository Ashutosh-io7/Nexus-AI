"""LangGraph Agentic Retention Strategy & Action Engine."""


from __future__ import annotations

import json
import logging
from typing import Any, Optional, TypedDict

import google.generativeai as genai
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.artifacts import load_current_model
from app.ml.cohort import find_similar_cohort
from app.ml.explain import explain_customer, get_explainer
from app.ml.predictor import risk_level, score_customers
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer
from app.models.retention_action import RetentionAction
from app.rag.playbook_service import search_playbook

logger = logging.getLogger("nexus.agent")



class RetentionAgentState(TypedDict, total=False):
    db: Session
    customer_id: int
    customer: Optional[Customer]
    customer_summary: dict[str, Any]
    churn_probability: float
    risk_level: str 
    risk_drivers: list[dict[str, Any]]
    cohort_summary: dict[str, Any]
    retrieved_policies: list[dict[str, Any]]
    diagnosis: str
    action_strategy: str
    policy_citations: list[dict[str, Any]]
    email_subject: str
    email_body: str
    action_id: Optional[int]
    error: Optional[str]


def node_gather_signals(state: RetentionAgentState) -> dict[str, Any]:
    """Gather customer data, XGBoost risk score, SHAP drivers, and cohort matches."""
    db = state["db"]
    customer_id = state["customer_id"]

    customer = db.get(Customer, customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}
    if customer.churned is True:
        return {"error": "Customer has already left, so no retention action is applicable."}

    # Retrieve or score risk prediction
    bundle = load_current_model()
    prob = 0.5
    r_level = "medium"
    if bundle:
        version = bundle["metadata"]["version"]
        pred = db.scalar(
            select(ChurnPrediction).where(
                ChurnPrediction.customer_id == customer_id,
                ChurnPrediction.model_version == version,
            )
        )
        if not pred:
            score_customers(db, [customer], bundle)
            db.flush()
            pred = db.scalar(
                select(ChurnPrediction).where(
                    ChurnPrediction.customer_id == customer_id,
                    ChurnPrediction.model_version == version,
                )
            )
        if pred:
            prob = pred.churn_probability
            r_level = pred.risk_level

    # Compute SHAP explanation drivers 
    drivers: list[dict[str, Any]] = []
    try: 
        explainer = get_explainer(db)
        if explainer:
            exp = explain_customer(explainer, customer)
            drivers = [
                {
                    "feature": c["feature"],
                    "label": c["label"],
                    "value": c["value"],
                    "direction": c["direction"],
                    "impact": c["impact"],
                }
                for c in exp.get("contributions", [])
                if c.get("direction") == "raises"
            ]

    except Exception as e:
        logger.warning("Could not compute SHAP explanation: %s", e)


    # Compute lookalike cohort matches
    cohort: dict[str, Any] = {}
    try:
        cohort = find_similar_cohort(db, customer, k=15)
    except Exception as e:
        logger.warning("Could not compute cohort: %s", e)
    summary = {
        "id": customer.id,
        "external_id": customer.external_id,
        "name": customer.full_name or customer.company_name or customer.external_id,
        "plan": customer.subscription_plan or "Standard",
        "tenure_months": customer.tenure_months or 0,
        "monthly_revenue": float(customer.monthly_revenue or 0),
        "support_tickets": customer.support_ticket_count or 0,
        "unresolved_tickets": customer.unresolved_ticket_count or 0,
        "payment_failures": customer.payment_failures or 0,
        "usage_minutes_last_30d": float(customer.usage_minutes_last_30d or 0),
    }


    return {
        "customer": customer,
        "customer_summary": summary,
        "churn_probability": prob,
        "risk_level": r_level,
        "risk_drivers": drivers,
        "cohort_summary": cohort,
    }


def node_retrieve_policies(state: RetentionAgentState) -> dict[str, Any]:
    """Formulate targeted queries and retrieve matching company policies via pgvector."""
    if state.get("error"):
        return {}
    db = state["db"]
    summary = state.get("customer_summary", {})
    drivers = state.get("risk_drivers", [])
    queries = [
        "Pricing Authority Maximum Allowed Discounts contract restructuring save strategy",
    ]
    if summary.get("unresolved_tickets", 0) > 0 or any("ticket" in d.get("label", "").lower() for d in drivers):
        queries.append("Unresolved Support Tickets SLA Breaches Dedicated Solutions Architect 50% service credit")
    if summary.get("payment_failures", 0) > 0 or any("payment" in d.get("label", "").lower() for d in drivers):
        queries.append("Consecutive payment failures Net-30 payment buffer ACH verification")
    if (summary.get("tenure_months", 0) < 6) or any("contract" in d.get("label", "").lower() for d in drivers):
        queries.append("Month-to-month save strategy 10% discount 6-month commitment")
    chunks_by_id = {}
    for q in queries:
        try:
            matches = search_playbook(db, q, top_k=2)
            for m in matches:
                chunks_by_id[m["chunk_id"]] = m
        except Exception as e:
            logger.warning("Policy retrieval error for query '%s': %s", q, e)
    return {"retrieved_policies": list(chunks_by_id.values())}



def node_synthesize_retention(state: RetentionAgentState) -> dict[str, Any]:
    """Reason across signals + policies and generate a grounded action & email."""
    if state.get("error"):
        return {}
    summary = state["customer_summary"]
    prob = state["churn_probability"]
    r_level = state["risk_level"]
    drivers = state.get("risk_drivers", [])
    cohort = state.get("cohort_summary", {})
    policies = state.get("retrieved_policies", [])
    # Format lookalike cohort text
    cohort_str = "No historical cohort available."
    if cohort.get("available") and cohort.get("total_similar"):
        cohort_str = (
            f"Of {cohort['total_similar']} most similar historical accounts, "
            f"{cohort['churned_count']} churned ({round(cohort['historical_churn_rate'] * 100)}% churn rate). "
            f"Avg cohort tenure was {cohort.get('avg_tenure_months', 'N/A')} months."
        )
    # Format retrieved policy passages with section titles and page numbers
    policy_texts = []
    for p in policies:
        policy_texts.append(
            f"[{p['section_title']} - Page {p['page_number']}]\n{p['content']}"
        )
    policy_corpus = "\n\n".join(policy_texts) or "Standard retention guidelines apply."
    system_prompt = (
        "You are Nexus AI's Senior Customer Retention Strategist. "
        "Your role is to analyze customer churn signals and company retention policy to produce a grounded, "
        "policy-compliant retention action and personalized email.\n\n"
        "STRICT COMPLIANCE RULES:\n"
        "1. GROUNDING: The diagnosis must directly address the customer's actual SHAP risk drivers and cohort precedent.\n"
        "2. POLICY BOUNDARIES: Any offer (discounts, pauses, service credits) MUST strictly comply with the retrieved company policy.\n"
        "   - Month-to-Month contracts: Max 10% discount for 3 months with a 6-month commitment.\n"
        "   - High-Value accounts (MRR > $100 or Tenure > 12 Months): Authorized for up to 15% discount for 6 months or 1 month free credit with annual commitment.\n"
        "   - Enterprise Exceptions: Max 20% discount on annual commitment (requires VP approval).\n"
        "   - Technical/Support friction: Mandate dedicated Solutions Architect review + 1-month 50% service credit.\n"
        "   - Payment friction: Verify ACH/card and offer Net-30 payment buffer before service suspension.\n"
        "   - NEVER offer discounts exceeding authorized limits.\n"
        "3. CITATIONS: In 'policy_citations', cite the exact section title and page number for every rule utilized.\n"
        "4. DRAFT EMAIL: Write an empathetic, professional email from the Customer Success Manager to the customer proposing these solutions. "
        "Do NOT mention internal risk models, churn probabilities, or AI in the email body.\n"
        "5. Respond with a valid JSON object matching the requested schema."
    )
    user_prompt = f"""Customer Profile:
- Name: {summary['name']} (External ID: {summary['external_id']})
- Plan: {summary['plan']}
- Tenure: {summary['tenure_months']} months
- Monthly Revenue: ${summary['monthly_revenue']:.2f}
- Support Tickets: {summary['support_tickets']} (Unresolved: {summary['unresolved_tickets']})
- Payment Failures: {summary['payment_failures']}
Predictive Risk & Signals:
- Model Churn Probability: {prob * 100:.1f}% ({r_level.upper()} RISK)
- Primary SHAP Risk Drivers: {', '.join(d['label'] + ' (' + str(d['value']) + ')' for d in drivers) or 'Standard activity trends'}
- Lookalike Historical Cohort: {cohort_str}
Retrieved Company Playbook Policies:
{policy_corpus}
Return a JSON object with this exact structure:
{{
  "diagnosis": "Root cause analysis referencing the customer's specific friction points and historical cohort precedent.",
  "action_strategy": "Concrete retention plan and remedies strictly complying with company guidelines.",
  "policy_citations": [
    {{"section_title": "Section Name", "page_number": 1, "rule_summary": "Summary of rule applied"}}
  ],
  "email_subject": "Engaging, professional subject line",
  "email_body": "Complete, empathetic draft email ready to send."
}}"""
    # If Gemini is configured, use LLM generation
    if settings.gemini_api_key:
        try:
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(
                settings.gemini_llm_model,
                system_instruction=system_prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            response = model.generate_content(user_prompt)
            data = json.loads(response.text)
            return {
                "diagnosis": data.get("diagnosis", ""),
                "action_strategy": data.get("action_strategy", ""),
                "policy_citations": data.get("policy_citations", []),
                "email_subject": data.get("email_subject", "Checking in on your account experience"),
                "email_body": data.get("email_body", ""),
            }
        except Exception as e:
            logger.error("Gemini retention synthesis failed, using fallback: %s", e)
    # Deterministic fallback when Gemini is offline or during tests
    citations = []
    if policies:
        first = policies[0]
        citations.append({
            "section_title": first.get("section_title", "Section 2: Pricing Authority"),
            "page_number": first.get("page_number", 1),
            "rule_summary": "Authorized retention restructuring terms.",
        })
    diagnosis = (
        f"Customer is flagged at {r_level} risk ({prob * 100:.1f}% probability). "
        f"Key friction drivers: {', '.join(d['label'] for d in drivers) or 'usage decline'}. {cohort_str}"
    )
    strategy = (
        f"Initiate priority account review. Align contract terms per policy guidelines with up to "
        f"{'15%' if summary['monthly_revenue'] > 100 else '10%'} authorized discount in exchange for commitment Restatement."
    )
    email_subject = f"Reviewing your {summary['plan']} subscription and account setup"
    email_body = (
        f"Hi {summary['name']},\n\n"
        f"I wanted to personally reach out from the Customer Success team. We noticed some recent challenges with your "
        f"account usage and support tickets, and we want to ensure you're getting maximum value from our platform.\n\n"
        f"I would welcome 15 minutes this week to discuss custom contract options and ensure our team resolves any outstanding issues.\n\n"
        f"Best regards,\nYour Customer Success Team"
    )
    return {
        "diagnosis": diagnosis,
        "action_strategy": strategy,
        "policy_citations": citations,
        "email_subject": email_subject,
        "email_body": email_body,
    }


def node_persist_action(state: RetentionAgentState) -> dict[str, Any]:
    """Upsert the generated retention plan into the retention_actions table."""
    if state.get("error"):
        return {}
    db = state["db"]
    customer_id = state["customer_id"]
    # Check for existing proposed action to update or insert fresh
    action = db.scalar(
        select(RetentionAction)
        .where(
            RetentionAction.customer_id == customer_id,
            RetentionAction.status == "proposed",
        )
        .order_by(RetentionAction.id.desc())
    )
    if not action:
        action = RetentionAction(
            customer_id=customer_id,
            status="proposed",
            churn_probability=state["churn_probability"],
            risk_level=state["risk_level"],
            risk_drivers=state.get("risk_drivers", []),
            cohort_summary=state.get("cohort_summary"),
            diagnosis=state["diagnosis"],
            action_strategy=state["action_strategy"],
            policy_citations=state.get("policy_citations", []),
            email_subject=state["email_subject"],
            email_body=state["email_body"],
        )
        db.add(action)
    else:
        action.churn_probability = state["churn_probability"]
        action.risk_level = state["risk_level"]
        action.risk_drivers = state.get("risk_drivers", [])
        action.cohort_summary = state.get("cohort_summary")
        action.diagnosis = state["diagnosis"]
        action.action_strategy = state["action_strategy"]
        action.policy_citations = state.get("policy_citations", [])
        action.email_subject = state["email_subject"]
        action.email_body = state["email_body"]
    db.commit()
    db.refresh(action)
    return {"action_id": action.id}


# Compile the LangGraph state graph
def build_retention_graph():

    builder = StateGraph(RetentionAgentState)
    builder.add_node("gather_signals", node_gather_signals)
    builder.add_node("retrieve_policies", node_retrieve_policies)
    builder.add_node("synthesize_retention", node_synthesize_retention)
    builder.add_node("persist_action", node_persist_action)
    builder.set_entry_point("gather_signals")
    builder.add_edge("gather_signals", "retrieve_policies")
    builder.add_edge("retrieve_policies", "synthesize_retention")
    builder.add_edge("synthesize_retention", "persist_action")
    builder.add_edge("persist_action", END)

    return builder.compile()

retention_agent_graph = build_retention_graph()


def run_retention_agent(db: Session, customer_id: int) -> dict[str, Any]:
    """Execute the compiled LangGraph agent for a single customer."""
    initial_state: RetentionAgentState = {
        "db": db,
        "customer_id": customer_id,
    }
    final_state = retention_agent_graph.invoke(initial_state)
    return final_state