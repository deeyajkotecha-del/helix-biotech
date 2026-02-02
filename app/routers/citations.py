"""Citation management endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.user import User
from app.models.source import Source
from app.models.citation import Citation
from app.schemas.citation import (
    CitationCreate,
    CitationResponse,
    CitationWithSource,
    CitationUpdate,
    ReportCitationsResponse,
)
from app.dependencies import get_current_user, get_optional_user

router = APIRouter()


@router.post("", response_model=CitationResponse, status_code=status.HTTP_201_CREATED)
async def create_citation(
    citation_data: CitationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new citation (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Verify source exists
    source = db.query(Source).filter(Source.id == citation_data.source_id).first()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Check for duplicate citation number in same location
    existing = db.query(Citation).filter(
        Citation.report_ticker == citation_data.report_ticker,
        Citation.section_name == citation_data.section_name,
        Citation.citation_number == citation_data.citation_number,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Citation [{citation_data.citation_number}] already exists in {citation_data.report_ticker}/{citation_data.section_name}",
        )

    # Create citation
    citation = Citation(
        source_id=citation_data.source_id,
        report_ticker=citation_data.report_ticker.upper(),
        section_name=citation_data.section_name,
        citation_number=citation_data.citation_number,
        context_text=citation_data.context_text,
        pdf_page=citation_data.pdf_page,
        pdf_highlight=citation_data.pdf_highlight,
    )

    db.add(citation)
    db.commit()
    db.refresh(citation)

    return CitationResponse.model_validate(citation)


@router.get("/report/{ticker}", response_model=ReportCitationsResponse)
async def get_report_citations(
    ticker: str,
    section: Optional[str] = None,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get all citations for a report, optionally filtered by section."""
    query = db.query(Citation).options(
        joinedload(Citation.source)
    ).filter(
        Citation.report_ticker == ticker.upper()
    )

    if section:
        query = query.filter(Citation.section_name == section)

    # Filter out non-public sources for non-authenticated users
    citations = query.order_by(
        Citation.section_name,
        Citation.citation_number
    ).all()

    # Filter based on source visibility
    visible_citations = []
    for citation in citations:
        if citation.source.is_public or (current_user and citation.source.uploaded_by == current_user.id):
            visible_citations.append(citation)

    return ReportCitationsResponse(
        report_ticker=ticker.upper(),
        citations=[CitationWithSource.model_validate(c) for c in visible_citations],
        total=len(visible_citations),
    )


@router.get("/{citation_id}", response_model=CitationWithSource)
async def get_citation(
    citation_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get citation with full source details."""
    citation = db.query(Citation).options(
        joinedload(Citation.source)
    ).filter(Citation.id == citation_id).first()

    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citation not found",
        )

    # Check source visibility
    if not citation.source.is_public:
        if not current_user or citation.source.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return CitationWithSource.model_validate(citation)


@router.patch("/{citation_id}", response_model=CitationResponse)
async def update_citation(
    citation_id: int,
    update_data: CitationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a citation (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    citation = db.query(Citation).filter(Citation.id == citation_id).first()

    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citation not found",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(citation, key, value)

    db.commit()
    db.refresh(citation)

    return CitationResponse.model_validate(citation)


@router.delete("/{citation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_citation(
    citation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a citation (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    citation = db.query(Citation).filter(Citation.id == citation_id).first()

    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citation not found",
        )

    db.delete(citation)
    db.commit()

    return None
