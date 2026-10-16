"""Database models for company retention playbooks and vector chunks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Standard embedding dimension for Google Gemini (text-embedding-004)
EMBEDDING_DIM = 768


class PlaybookDocument(Base):
    __tablename__ = "playbook_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="retention_policy")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list[PlaybookChunk]] = relationship(
        "PlaybookChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="PlaybookChunk.chunk_index",
    )


class PlaybookChunk(Base):
    __tablename__ = "playbook_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("playbook_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Section hierarchy for attribution (e.g. "Section 3.2: Discount Limits")
    section_title: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # The actual readable policy text retrieved for the LLM
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # pgvector embedding column
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=False,
    )

    # Optional metadata (rules, allowed_actions, tags)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default="{}",
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document: Mapped[PlaybookDocument] = relationship(
        "PlaybookDocument",
        back_populates="chunks",
    )