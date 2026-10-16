from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.playbook import PlaybookChunk, PlaybookDocument
from app.rag.playbook_service import ingest_playbook_pdf, search_playbook
from app.schemas.playbook import (
    PlaybookSearchResponse,
    PlaybookStatusResponse,
    PlaybookUploadResponse,
)

router = APIRouter()


@router.get(
    "/status",
    response_model=PlaybookStatusResponse,
    summary="Status of vectorized retention policy documents",
)
def get_playbook_status(db: Session = Depends(get_db)):
    doc = db.scalar(select(PlaybookDocument).order_by(PlaybookDocument.updated_at.desc()))
    if not doc:
        return PlaybookStatusResponse(
            available=False,
            message="No retention playbook PDF has been uploaded yet.",
        )

    chunk_count = db.scalar(
        select(func.count(PlaybookChunk.id)).where(PlaybookChunk.document_id == doc.id)
    ) or 0

    return PlaybookStatusResponse(
        available=True,
        document_title=doc.title,
        version=doc.version,
        chunks_stored=chunk_count,
        message="Active retention policy loaded in pgvector.",
    )


@router.post(
    "/upload",
    response_model=PlaybookUploadResponse,
    summary="Upload and vectorize a Retention Playbook PDF into pgvector",
)
async def upload_playbook_pdf(
    file: UploadFile = File(..., description="Corporate Retention Policy PDF"),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files (.pdf) are supported for the Retention Playbook.",
        )

    try:
        pdf_bytes = await file.read()
        doc = ingest_playbook_pdf(
            db=db,
            filename=file.filename,
            pdf_bytes=pdf_bytes,
            title=file.filename,
        )
        chunk_count = db.scalar(
            select(func.count(PlaybookChunk.id)).where(PlaybookChunk.document_id == doc.id)
        ) or 0

        return PlaybookUploadResponse(
            document_id=doc.id,
            filename=doc.title,
            version=doc.version,
            chunks_stored=chunk_count,
            message=f"Successfully extracted {chunk_count} policy passages from PDF and indexed in pgvector.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(exc)}")


@router.get(
    "/search",
    response_model=PlaybookSearchResponse,
    summary="Search company policy using pgvector cosine similarity",
)
def search_playbook_policy(
    query: str = Query(..., min_length=2, description="Question or situation (e.g. 'what discount is allowed for high mrr')"),
    top_k: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    matches = search_playbook(db, query=query, top_k=top_k)
    return PlaybookSearchResponse(query=query, matches=matches)