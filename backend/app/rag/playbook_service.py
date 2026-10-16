"""PDF chunking, Gemini text-embedding-004, and pgvector retrieval."""
from __future__ import annotations
import hashlib
import io
import os
from typing import Any, Optional
import google.generativeai as genai
import numpy as np
import pypdf
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.models.playbook import EMBEDDING_DIM, PlaybookChunk, PlaybookDocument
from app.core.config import settings
import re 


def get_embedding(text_to_embed: str, api_key: Optional[str] = None) -> list[float]:
    """
    Computes a 768-dim normalized vector using Google Gemini text-embedding-004.
    If GEMINI_API_KEY is not set or offline, uses a deterministic unit vector
    so local development and tests run seamlessly without crashing.
    """
    api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if api_key: 
        try:
            genai.configure(api_key=api_key)
            result = genai.embed_content(
                model=settings.gemini_embedding_model,
                content=text_to_embed,
                output_dimensionality=EMBEDDING_DIM, 
            )
            return result["embedding"]
        except Exception as exc:
            print(f"[Warning] Gemini API call failed ({exc}), using local fallback.") 


    # Deterministic local unit vector fallback (768-dim) for tests / offline dev
    rng = np.random.RandomState(int(hashlib.sha256(text_to_embed.encode("utf-8")).hexdigest()[:8], 16))
    vec = rng.randn(EMBEDDING_DIM).astype(np.float32) 
    norm = np.linalg.norm(vec) 
    if norm > 0:
        vec /= norm 
    return vec.tolist()


def extract_chunks_from_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extracts text from PDF and splits into focused policy section chunks."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    chunks = []
    chunk_idx = 0

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        
        # Split by "Section X:" headers
        sections = re.split(r"(?=(?:Section\s+\d+:))", raw_text)
        
        for sec in sections:
            sec = sec.strip()
            if len(sec) < 30:
                continue
            first_line = sec.split("\n")[0][:80].replace("•", "").strip()
            title = f"Page {page_num}: {first_line}"
            
            chunks.append({
                "chunk_index": chunk_idx,
                "section_title": title,
                "content": sec,
                "metadata": {"page": page_num},
            })
            chunk_idx += 1

    return chunks 


def ingest_playbook_pdf(
        db: Session,
        filename: str,
        pdf_bytes: bytes,
        title: str = "Nexus Retention & Save Playbook",
        version: str = "2.4",
) -> PlaybookDocument: 
    """Ingests a PDF file, calculates Gemini embeddings, and stores chunks in pgvector."""
    parsed_chunks = extract_chunks_from_pdf(pdf_bytes)
    if not parsed_chunks:
        raise ValueError("Could not extract any readable policy text from the provided PDF.")

    doc = db.scalar(select(PlaybookDocument).where(PlaybookDocument.title == title))
    if not doc:
        doc = PlaybookDocument(
            title=title,
            category="retention_policy",
            description=f"Standard corporate save guidelines parsed from {filename}.",
            version=version, 
        )
        db.add(doc)
        db.flush() 
    else:
        db.query(PlaybookChunk).filter(PlaybookChunk.document_id == doc.id).delete() 
        db.flush() 


    for item in parsed_chunks:
        full_text = f"{item['section_title']}\n{item['content']}"
        vector = get_embedding(full_text)

        chunk = PlaybookChunk(
            document_id=doc.id,
            chunk_index=item["chunk_index"],
            section_title=item["section_title"],
            content=item["content"],
            embedding=vector,
            metadata_=item.get("metadata", {}),
        )
        db.add(chunk) 

    db.commit()
    db.refresh(doc)
    return doc 


def search_playbook(
    db: Session,
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Retrieves relevant policy passages using pgvector cosine similarity."""
    query_vector = get_embedding(query)
    vector_literal = "[" + ",".join(f"{x:.6f}" for x in query_vector) + "]"
    sql = text("""
        SELECT 
            id, 
            document_id, 
            section_title, 
            content,
            COALESCE((metadata->>'page')::int, 1) AS page_number,
            1 - (embedding <=> CAST(:vec AS vector)) AS similarity
        FROM playbook_chunks
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :top_k;
    """)
    results = db.execute(sql, {"vec": vector_literal, "top_k": top_k}).fetchall()
    return [
        {
            "chunk_id": row.id,
            "section_title": row.section_title,
            "page_number": row.page_number,
            "content": row.content,
            "similarity": round(float(row.similarity), 4),
        }
        for row in results
    ]