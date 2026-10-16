from typing import Optional
from pydantic import BaseModel


class PlaybookChunkMatch(BaseModel):
    chunk_id: int
    section_title: str
    page_number: int
    content: str
    similarity: float


class PlaybookSearchResponse(BaseModel):
    query: str
    matches: list[PlaybookChunkMatch]


class PlaybookUploadResponse(BaseModel):
    document_id: int
    filename: str
    version: str
    chunks_stored: int
    message: str


class PlaybookStatusResponse(BaseModel):
    available: bool
    document_title: Optional[str] = None
    version: Optional[str] = None
    chunks_stored: int = 0
    message: Optional[str] = None