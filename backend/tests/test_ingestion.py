from decimal import Decimal
import pytest
from app.models.customer import Customer
from app.models.customer_import import CustomerImport
from app.services.ingestion import (
    IngestionService,
    normalize_header,
    parse_boolean,
    parse_decimal,
    parse_integer,
)


def test_header_normalization_and_detection():
    headers = ["Customer_ID", "Full Name", "MRR", "Subscription-Plan", "Custom_Flag"]
    detected, unmapped = IngestionService.detect_mappings(headers)

    assert detected["Customer_ID"] == "external_id"
    assert detected["Full Name"] == "full_name"
    assert detected["MRR"] == "monthly_revenue"
    assert detected["Subscription-Plan"] == "subscription_plan"
    assert "Custom_Flag" in unmapped


def test_parsers():
    # Decimal parser with currency and commas
    assert parse_decimal("$1,250.50") == Decimal("1250.50")
    assert parse_decimal("0") == Decimal("0")
    assert parse_decimal("") is None

    # Boolean parser
    assert parse_boolean("yes") is True
    assert parse_boolean("TRUE") is True
    assert parse_boolean("1") is True
    assert parse_boolean("no") is False
    assert parse_boolean("0") is False
    assert parse_boolean("") is None

    # Integer parser
    assert parse_integer("42") == 42
    assert parse_integer("1,000") == 1000
    assert parse_integer("") is None

    with pytest.raises(ValueError):
        parse_decimal("not-a-number")


def test_csv_preview():
    csv_content = """customer_id,name,mrr,plan,custom_note
cust_101,Acme Corp,250.00,Enterprise,High potential
cust_102,Beta LLC,99.00,Pro,Needs follow-up
"""
    preview = IngestionService.preview_csv(csv_content, max_rows=5)

    assert preview.total_columns == 5
    assert preview.detected_mappings["customer_id"] == "external_id"
    assert preview.detected_mappings["name"] == "full_name"
    assert preview.detected_mappings["mrr"] == "monthly_revenue"
    assert preview.detected_mappings["plan"] == "subscription_plan"
    assert "custom_note" in preview.unmapped_columns
    assert len(preview.sample_rows) == 2
    assert preview.sample_rows[0]["customer_id"] == "cust_101"


def test_csv_ingestion_and_upsert(db_session):
    # 1. Initial Import
    initial_csv = """customer_id,full_name,email,monthly_revenue,churned,vip_status
CUST-001,Alice Smith,alice@example.com,120.00,false,gold
CUST-002,Bob Jones,bob@example.com,75.50,true,silver
"""
    job = IngestionService.process_and_ingest(
        db=db_session,
        filename="customers_batch1.csv",
        content=initial_csv
    )

    assert job.status == "completed"
    assert job.total_rows == 2
    assert job.inserted_count == 2
    assert job.updated_count == 0
    assert job.failed_count == 0

    c1 = db_session.query(Customer).filter_by(external_id="CUST-001").first()
    assert c1 is not None
    assert c1.full_name == "Alice Smith"
    assert c1.monthly_revenue == Decimal("120.00")
    assert c1.churned is False
    assert c1.source_attributes.get("vip_status") == "gold"

    # 2. Second Import with UPSERT (Updating CUST-001, adding CUST-003)
    update_csv = """customer_id,full_name,email,monthly_revenue,churned,vip_status
CUST-001,Alice Smith-Updated,alice@example.com,150.00,false,platinum
CUST-003,Charlie Brown,charlie@example.com,50.00,,bronze
"""
    job2 = IngestionService.process_and_ingest(
        db=db_session,
        filename="customers_batch2.csv",
        content=update_csv
    )

    assert job2.status == "completed"
    assert job2.total_rows == 2
    assert job2.inserted_count == 1  # CUST-003
    assert job2.updated_count == 1   # CUST-001
    assert job2.failed_count == 0

    c1_updated = db_session.query(Customer).filter_by(external_id="CUST-001").first()
    assert c1_updated.full_name == "Alice Smith-Updated"
    assert c1_updated.monthly_revenue == Decimal("150.00")
    assert c1_updated.source_attributes.get("vip_status") == "platinum"

    c3 = db_session.query(Customer).filter_by(external_id="CUST-003").first()
    assert c3 is not None
    assert c3.churned is None  # Unknown outcome preserved as None


def test_csv_ingestion_with_invalid_rows(db_session):
    bad_csv = """customer_id,monthly_revenue
VALID-01,99.99
INVALID-02,not-a-valid-revenue
VALID-03,49.00
"""
    job = IngestionService.process_and_ingest(
        db=db_session,
        filename="bad_batch.csv",
        content=bad_csv
    )

    assert job.status == "partial"
    assert job.inserted_count == 2
    assert job.failed_count == 1
    assert len(job.error_summary) == 1
    assert job.error_summary[0]["row"] == 3
    assert "Invalid numeric decimal value" in job.error_summary[0]["error"] 


def test_camel_case_headers_are_recognized():
    assert normalize_header("customerID") == "customer_id"
    assert normalize_header("MonthlyCharges") == "monthly_charges"
    assert normalize_header("MRR") == "mrr"  # all-caps names stay in one piece

    headers = ["customerID", "MonthlyCharges", "SubscriptionPlan", "LastLogin"]
    detected, unmapped = IngestionService.detect_mappings(headers)

    assert detected["customerID"] == "external_id"
    assert detected["MonthlyCharges"] == "monthly_revenue"
    assert detected["SubscriptionPlan"] == "subscription_plan"
    assert detected["LastLogin"] == "last_active_at"
    assert unmapped == [] 

def test_reimport_does_not_erase_existing_values(db_session):
    first = """customer_id,full_name,email,monthly_revenue,churned,vip_status
CUST-100,Dana Lee,dana@example.com,80.00,true,gold
"""
    IngestionService.process_and_ingest(
        db=db_session, filename="first.csv", content=first
    )

    # Fewer columns, an empty email cell, and one brand-new extra column
    second = """customer_id,monthly_revenue,email,region
CUST-100,95.00,,west
"""
    job = IngestionService.process_and_ingest(
        db=db_session, filename="second.csv", content=second
    )
    assert job.updated_count == 1

    c = db_session.query(Customer).filter_by(external_id="CUST-100").one()
    assert c.monthly_revenue == Decimal("95.00")  # updated
    assert c.full_name == "Dana Lee"              # column missing -> kept
    assert c.email == "dana@example.com"          # empty cell -> kept
    assert c.churned is True                      # column missing -> kept
    assert c.source_attributes == {"vip_status": "gold", "region": "west"}  # merged


def test_strict_value_parsing():
    with pytest.raises(ValueError):
        parse_boolean("maybe")
    with pytest.raises(ValueError):
        parse_integer("3.7")
    with pytest.raises(ValueError):
        parse_decimal("NaN")
    assert parse_integer("1e3") == 1000


def test_invalid_churn_and_duplicate_ids_are_reported(db_session):
    csv_text = """customer_id,monthly_revenue,churned
D-1,10.00,yes
D-2,20.00,maybe
D-1,30.00,no
"""
    job = IngestionService.process_and_ingest(
        db=db_session, filename="dupes.csv", content=csv_text
    )
    assert job.inserted_count == 1
    assert job.failed_count == 2

    errors = {item["row"]: item["error"] for item in job.error_summary}
    assert "yes/no" in errors[3].lower()          # D-2 with "maybe"
    assert "Duplicate customer ID 'D-1'" in errors[4]

    saved = db_session.query(Customer).filter_by(external_id="D-1").one()
    assert saved.monthly_revenue == Decimal("10.00")  # first row wins
