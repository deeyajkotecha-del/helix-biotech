"""Source schemas for request/response validation."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class SourceCreate(BaseModel):
    """Schema for creating a source (metadata, file uploaded separately)."""
    title: str
    authors: Optional[List[str]] = None
    publication_date: Optional[date] = None
    source_type: str  # 'journal_article', 'sec_filing', 'conference_poster', 'internal_document', 'presentation'
    journal_name: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    is_public: bool = True


class SourceResponse(BaseModel):
    """Schema for source response."""
    id: int
    title: str
    authors: Optional[List[str]]
    publication_date: Optional[date]
    source_type: str
    journal_name: Optional[str]
    doi: Optional[str]
    pmid: Optional[str]
    url: Optional[str]
    pdf_path: Optional[str]
    abstract: Optional[str]
    uploaded_by: int
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceUpdate(BaseModel):
    """Schema for updating source metadata."""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publication_date: Optional[date] = None
    source_type: Optional[str] = None
    journal_name: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    is_public: Optional[bool] = None


class SourceListResponse(BaseModel):
    """Schema for listing sources with pagination."""
    sources: List[SourceResponse]
    total: int
    skip: int
    limit: int
