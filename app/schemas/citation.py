"""Citation schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.source import SourceResponse


class CitationCreate(BaseModel):
    """Schema for creating a citation."""
    source_id: int
    report_ticker: str
    section_name: str
    citation_number: int
    context_text: Optional[str] = None
    pdf_page: Optional[int] = None
    pdf_highlight: Optional[str] = None


class CitationResponse(BaseModel):
    """Schema for citation response."""
    id: int
    source_id: int
    report_ticker: str
    section_name: str
    citation_number: int
    context_text: Optional[str]
    pdf_page: Optional[int]
    pdf_highlight: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CitationWithSource(BaseModel):
    """Schema for citation with full source details."""
    id: int
    source_id: int
    report_ticker: str
    section_name: str
    citation_number: int
    context_text: Optional[str]
    pdf_page: Optional[int]
    pdf_highlight: Optional[str]
    created_at: datetime
    source: SourceResponse

    class Config:
        from_attributes = True


class CitationUpdate(BaseModel):
    """Schema for updating a citation."""
    context_text: Optional[str] = None
    pdf_page: Optional[int] = None
    pdf_highlight: Optional[str] = None


class ReportCitationsResponse(BaseModel):
    """Schema for all citations in a report."""
    report_ticker: str
    citations: List[CitationWithSource]
    total: int
