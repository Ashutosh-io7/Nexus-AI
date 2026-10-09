import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.customer_import import CustomerImport
from app.schemas.customer import CustomerCreate
from app.schemas.customer_import import CSVPreviewResponse


# Canonical field aliases map: normalized source header -> model field name
FIELD_ALIASES: dict[str, str] = {
    # external_id
    "external_id": "external_id",
    "customer_id": "external_id",
    "id": "external_id",
    "client_id": "external_id",
    "user_id": "external_id",
    "account_id": "external_id",
    # full_name
    "full_name": "full_name",
    "name": "full_name",
    "customer_name": "full_name",
    "client_name": "full_name",
    # email
    "email": "email",
    "email_address": "email",
    "contact_email": "email",
    # company_name
    "company_name": "company_name",
    "company": "company_name",
    "organization": "company_name",
    "org_name": "company_name",
    "account_name": "company_name",
    # subscription_plan
    "subscription_plan": "subscription_plan",
    "plan": "subscription_plan",
    "plan_name": "subscription_plan",
    "tier": "subscription_plan",
    "package": "subscription_plan",
    # tenure_months
    "tenure_months": "tenure_months",
    "tenure": "tenure_months",
    "months_active": "tenure_months",
    "account_age_months": "tenure_months",
    # monthly_revenue
    "monthly_revenue": "monthly_revenue",
    "monthly_charges": "monthly_revenue",
    "mrr": "monthly_revenue",
    "revenue": "monthly_revenue",
    "monthly_spend": "monthly_revenue",
    # usage_minutes_last_30d
    "usage_minutes_last_30d": "usage_minutes_last_30d",
    "usage_minutes": "usage_minutes_last_30d",
    "usage": "usage_minutes_last_30d",
    "total_usage_minutes": "usage_minutes_last_30d",
    "usage_30d": "usage_minutes_last_30d",
    # logins_last_30d
    "logins_last_30d": "logins_last_30d",
    "logins": "logins_last_30d",
    "login_count": "logins_last_30d",
    "logins_30d": "logins_last_30d",
    # active_days_last_30d
    "active_days_last_30d": "active_days_last_30d",
    "active_days": "active_days_last_30d",
    "days_active": "active_days_last_30d",
    "days_active_30d": "active_days_last_30d",
    # support_ticket_count
    "support_ticket_count": "support_ticket_count",
    "ticket_count": "support_ticket_count",
    "tickets": "support_ticket_count",
    "total_tickets": "support_ticket_count",
    # unresolved_ticket_count
    "unresolved_ticket_count": "unresolved_ticket_count",
    "unresolved_tickets": "unresolved_ticket_count",
    "open_tickets": "unresolved_ticket_count",
    "pending_tickets": "unresolved_ticket_count",
    # payment_failures
    "payment_failures": "payment_failures",
    "failed_payments": "payment_failures",
    "payment_issues": "payment_failures",
    # last_active_at
    "last_active_at": "last_active_at",
    "last_active": "last_active_at",
    "last_login": "last_active_at",
    "last_activity": "last_active_at",
    # churned
    "churned": "churned",
    "churn": "churned",
    "is_churned": "churned",
    "has_churned": "churned",
    "churn_label": "churned",
}


def normalize_header(header: str) -> str:
    """Normalize column header for alias matching."""
    s = header.strip()
    # Split camelCase / PascalCase: "customerID" -> "customer_ID"
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)
    s = s.lower()
    return re.sub(r"[\s\-_]+", "_", s)


def parse_boolean(val: Any) -> Optional[bool]:
    """Parse common boolean representations."""
    if val is None or val == "":
        return None
    s = str(val).strip().lower()
    if s in ("1", "true", "t", "yes", "y"):
        return True
    if s in ("0", "false", "f", "no", "n"):
        return False
    return None


def parse_decimal(val: Any) -> Optional[Decimal]:
    """Safely parse decimal or currency string."""
    if val is None or val == "":
        return None
    s = str(val).strip().replace("$", "").replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid numeric decimal value: '{val}'")


def parse_integer(val: Any) -> Optional[int]:
    """Safely parse integer string."""
    if val is None or val == "":
        return None
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        raise ValueError(f"Invalid integer value: '{val}'")


def parse_datetime(val: Any) -> Optional[datetime]:
    """Safely parse datetime string."""
    if val is None or val == "":
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Try basic date format YYYY-MM-DD
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"Invalid date/datetime value: '{val}'. Expected ISO format (YYYY-MM-DD).")


class IngestionService:
    """Production service for customer CSV preview, validation, and database UPSERT."""

    @classmethod
    def detect_mappings(cls, headers: list[str]) -> tuple[dict[str, str], list[str]]:
        """
        Detects model field mappings for provided CSV headers.
        Returns (detected_mappings, unmapped_columns).
        """
        detected: dict[str, str] = {}
        unmapped: list[str] = []

        for h in headers:
            norm = normalize_header(h)
            if norm in FIELD_ALIASES:
                target_field = FIELD_ALIASES[norm]
                # Avoid assigning multiple CSV columns to the same model field
                if target_field not in detected.values():
                    detected[h] = target_field
                    continue
            unmapped.append(h)

        return detected, unmapped

    @classmethod
    def preview_csv(cls, content: str, max_rows: int = 5) -> CSVPreviewResponse:
        """Parse and return schema detection and preview rows from CSV text."""
        reader = csv.reader(io.StringIO(content))
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty.")

        headers = [h.strip() for h in raw_headers if h.strip()]
        if not headers:
            raise ValueError("CSV file contains no valid headers.")

        detected_mappings, unmapped_columns = cls.detect_mappings(headers)

        sample_rows: list[dict[str, Any]] = []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            if not any(row):  # skip completely blank rows
                continue
            row_dict = {}
            for col_idx, col_name in enumerate(headers):
                row_dict[col_name] = row[col_idx] if col_idx < len(row) else None
            sample_rows.append(row_dict)

        return CSVPreviewResponse(
            total_columns=len(headers),
            headers=headers,
            detected_mappings=detected_mappings,
            unmapped_columns=unmapped_columns,
            sample_rows=sample_rows
        )

    @classmethod
    def process_and_ingest(
        cls,
        db: Session,
        filename: str,
        content: str,
        custom_mappings: Optional[dict[str, str]] = None
    ) -> CustomerImport:
        """
        Validates rows and executes PostgreSQL UPSERT on the customers table.
        Records job progress in customer_imports.
        """
        reader = csv.reader(io.StringIO(content))
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty.")

        headers = [h.strip() for h in raw_headers if h.strip()]
        if not headers:
            raise ValueError("CSV file contains no valid headers.")

        # Determine mappings
        auto_mappings, auto_unmapped = cls.detect_mappings(headers)
        column_to_field: dict[str, str] = custom_mappings or auto_mappings

        # Verify external_id mapping exists
        if "external_id" not in column_to_field.values():
            raise ValueError(
                "Cannot import customer data: No column mapped to 'external_id'. "
                "Every customer record must have a unique identifier."
            )

        # Create import audit record
        import_job = CustomerImport(
            filename=filename,
            status="processing",
            total_rows=0,
            inserted_count=0,
            updated_count=0,
            failed_count=0,
            error_summary=[],
        )
        db.add(import_job)
        db.commit()
        db.refresh(import_job)

        errors: list[dict[str, Any]] = []
        valid_records: list[dict[str, Any]] = []
        row_number = 1  # 1-indexed, header was row 1

        for raw_row in reader:
            row_number += 1
            if not any(raw_row):
                continue  # skip empty lines

            row_data: dict[str, Any] = {}
            source_attributes: dict[str, Any] = {}

            # Map raw row columns
            for col_idx, col_name in enumerate(headers):
                cell_value = raw_row[col_idx].strip() if col_idx < len(raw_row) else ""
                target_field = column_to_field.get(col_name)

                if target_field:
                    row_data[target_field] = cell_value
                else:
                    if cell_value:
                        source_attributes[col_name] = cell_value

            try:
                # Coerce data types cleanly
                transformed_data: dict[str, Any] = {
                    "source_attributes": source_attributes
                }

                # external_id
                ext_id = row_data.get("external_id")
                if not ext_id:
                    raise ValueError("Missing external_id value.")
                transformed_data["external_id"] = str(ext_id)

                # Optional strings (only set when the cell has a value)
                for str_field in ("full_name", "email", "company_name", "subscription_plan"):
                    val = row_data.get(str_field)
                    if val:
                        transformed_data[str_field] = str(val).strip()

                # Integers
                for int_field in (
                    "tenure_months", "logins_last_30d", "active_days_last_30d",
                    "support_ticket_count", "unresolved_ticket_count", "payment_failures"
                ):
                    val = row_data.get(int_field)
                    if val:
                        transformed_data[int_field] = parse_integer(val)

                # Decimals
                for dec_field in ("monthly_revenue", "usage_minutes_last_30d"):
                    val = row_data.get(dec_field)
                    if val:
                        transformed_data[dec_field] = parse_decimal(val)

                # Datetime
                if row_data.get("last_active_at"):
                    transformed_data["last_active_at"] = parse_datetime(row_data["last_active_at"])

                # Churned boolean
                if row_data.get("churned"):
                    transformed_data["churned"] = parse_boolean(row_data["churned"])

                # Validate with Pydantic, keeping only the fields we actually set
                validated_model = CustomerCreate(**transformed_data)
                valid_records.append(validated_model.model_dump(exclude_unset=True))

            except Exception as exc:
                errors.append({
                    "row": row_number,
                    "error": str(exc)
                })

        # Process valid records into PostgreSQL with UPSERT
        inserted_count = 0
        updated_count = 0

        if valid_records:
            # We determine which external_ids already exist to accurately count inserted vs updated
            ext_ids = [r["external_id"] for r in valid_records]
            existing_ids_result = db.query(Customer.external_id).filter(
                Customer.external_id.in_(ext_ids)
            ).all()
            existing_set = {row[0] for row in existing_ids_result}

            for record in valid_records:
                is_update = record["external_id"] in existing_set
                
                stmt = pg_insert(Customer).values(**record)

                # On conflict, update only the columns this CSV actually provided
                update_dict = {
                    key: value
                    for key, value in record.items()
                    if key not in ("external_id", "source_attributes")
                }
                # Merge new source attributes into the existing ones
                update_dict["source_attributes"] = Customer.source_attributes.op("||")(
                    stmt.excluded.source_attributes
                )
                update_dict["updated_at"] = func.now()

                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=[Customer.external_id],
                    set_=update_dict
                )
                db.execute(upsert_stmt)

                if is_update:
                    updated_count += 1
                else:
                    inserted_count += 1
                    existing_set.add(record["external_id"])

            db.commit()

        # Update import job stats
        import_job.total_rows = len(valid_records) + len(errors)
        import_job.inserted_count = inserted_count
        import_job.updated_count = updated_count
        import_job.failed_count = len(errors)
        import_job.error_summary = errors
        import_job.status = "completed" if len(errors) == 0 else ("partial" if valid_records else "failed")
        import_job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(import_job)

        return import_job
