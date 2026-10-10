import json
from typing import Literal, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.customer import Customer
from app.models.customer_import import CustomerImport
from app.schemas.customer_import import CSVPreviewResponse, CustomerImportResponse
from app.schemas.customer import CustomerListResponse, CustomerResponse
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post(
    "/upload-preview",
    response_model=CSVPreviewResponse,
    summary="Preview customer CSV and detect column mappings"
)
async def preview_customer_csv(
    file: UploadFile = File(..., description="Customer CSV file")
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are supported."
        )

    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8-sig")  # handle UTF-8 with BOM if present
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode file. Ensure the CSV is encoded in UTF-8."
        )

    try:
        return IngestionService.preview_csv(content=content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)
        )


@router.post(
    "/upload",
    response_model=CustomerImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Validate and ingest customer CSV records with UPSERT"
)
async def upload_customers_csv(
    file: UploadFile = File(..., description="Customer CSV file"),
    mappings_json: Optional[str] = Form(None, description="Optional custom column mappings JSON string"),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are supported."
        )

    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode file. Ensure the CSV is encoded in UTF-8."
        )

    custom_mappings = None
    if mappings_json:
        try:
            custom_mappings = json.loads(mappings_json)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for mappings_json parameter."
            )

    try:
        import_job = IngestionService.process_and_ingest(
            db=db,
            filename=file.filename,
            content=content,
            custom_mappings=custom_mappings
        )
        return import_job
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process ingestion: {str(exc)}"
        )


@router.get(
    "/imports",
    response_model=list[CustomerImportResponse],
    summary="List all past customer import audit logs"
)
def list_import_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    imports = (
        db.query(CustomerImport)
        .order_by(CustomerImport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return imports


@router.get(
    "/imports/{import_id}",
    response_model=CustomerImportResponse,
    summary="Get details and error summary for a specific customer import"
)
def get_import_job(
    import_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(CustomerImport).filter(CustomerImport.id == import_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import job with ID {import_id} not found."
        )
    return job


SortField = Literal[
    "external_id", "full_name", "company_name", "subscription_plan",
    "tenure_months", "monthly_revenue", "last_active_at", "created_at",
]

SORTABLE_COLUMNS = {
    "external_id": Customer.external_id,
    "full_name": Customer.full_name,
    "company_name": Customer.company_name,
    "subscription_plan": Customer.subscription_plan,
    "tenure_months": Customer.tenure_months,
    "monthly_revenue": Customer.monthly_revenue,
    "last_active_at": Customer.last_active_at,
    "created_at": Customer.created_at,
}


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers with search, sorting and paging"
)
def list_customers(
    search: Optional[str] = Query(None, max_length=100, description="Matches ID, name, email or company"),
    sort_by: SortField = "created_at",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    filters = []
    term = (search or "").strip()
    if term:
        # Treat % and _ typed by the user as plain text, not LIKE wildcards
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(or_(
            Customer.external_id.ilike(pattern, escape="\\"),
            Customer.full_name.ilike(pattern, escape="\\"),
            Customer.email.ilike(pattern, escape="\\"),
            Customer.company_name.ilike(pattern, escape="\\"),
        ))

    column = SORTABLE_COLUMNS[sort_by]
    ordering = column.asc().nulls_last() if sort_dir == "asc" else column.desc().nulls_last()

    total = db.scalar(select(func.count()).select_from(Customer).where(*filters)) or 0
    rows = db.scalars(
        select(Customer)
        .where(*filters)
        .order_by(ordering, Customer.id)  # id breaks ties so paging is stable
        .limit(limit)
        .offset(offset)
    ).all()

    return CustomerListResponse(
        items=[CustomerResponse.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )