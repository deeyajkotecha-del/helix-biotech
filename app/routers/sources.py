"""Source management endpoints."""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceResponse, SourceUpdate, SourceListResponse
from app.dependencies import get_current_user, get_optional_user
from app.config import UPLOAD_DIR

router = APIRouter()

# Ensure sources directory exists
SOURCES_DIR = UPLOAD_DIR / "sources"
SOURCES_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    title: str = Form(...),
    source_type: str = Form(...),
    authors: Optional[str] = Form(None),  # JSON string of authors list
    publication_date: Optional[str] = Form(None),
    journal_name: Optional[str] = Form(None),
    doi: Optional[str] = Form(None),
    pmid: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    is_public: bool = Form(True),
    pdf: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new source with optional PDF upload."""
    import json
    from datetime import datetime

    # Validate source type
    valid_types = ['journal_article', 'sec_filing', 'conference_poster', 'internal_document', 'presentation']
    if source_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type. Must be one of: {', '.join(valid_types)}",
        )

    # Parse authors JSON if provided
    authors_list = None
    if authors:
        try:
            authors_list = json.loads(authors)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authors format. Must be a JSON array.",
            )

    # Parse publication date if provided
    pub_date = None
    if publication_date:
        try:
            pub_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid publication_date format. Use YYYY-MM-DD.",
            )

    # Handle PDF upload
    pdf_path = None
    if pdf:
        # Validate file type
        if not pdf.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed.",
            )

        # Generate unique filename
        unique_name = f"{uuid.uuid4()}.pdf"
        file_path = SOURCES_DIR / unique_name

        # Save file
        contents = await pdf.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        pdf_path = f"sources/{unique_name}"

    # Create source record
    source = Source(
        title=title,
        authors=authors_list,
        publication_date=pub_date,
        source_type=source_type,
        journal_name=journal_name,
        doi=doi,
        pmid=pmid,
        url=url,
        pdf_path=pdf_path,
        abstract=abstract,
        uploaded_by=current_user.id,
        is_public=is_public,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return SourceResponse.model_validate(source)


@router.get("", response_model=SourceListResponse)
async def list_sources(
    skip: int = 0,
    limit: int = 50,
    source_type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """List sources with optional filters."""
    query = db.query(Source)

    # Filter by visibility
    if current_user:
        query = query.filter(
            (Source.is_public == True) | (Source.uploaded_by == current_user.id)
        )
    else:
        query = query.filter(Source.is_public == True)

    # Filter by source type
    if source_type:
        query = query.filter(Source.source_type == source_type)

    # Search by title
    if search:
        query = query.filter(Source.title.ilike(f"%{search}%"))

    # Get total count
    total = query.count()

    # Get paginated results
    sources = query.order_by(Source.created_at.desc()).offset(skip).limit(limit).all()

    return SourceListResponse(
        sources=[SourceResponse.model_validate(s) for s in sources],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get source details by ID."""
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Check access
    if not source.is_public:
        if not current_user or source.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return SourceResponse.model_validate(source)


@router.get("/{source_id}/pdf")
async def get_source_pdf(
    source_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Serve the PDF file for a source."""
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Check access
    if not source.is_public:
        if not current_user or source.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    if not source.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF available for this source",
        )

    file_path = UPLOAD_DIR / source.pdf_path

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on server",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"{source.title[:50]}.pdf",
    )


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    update_data: SourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update source metadata (admin or owner only)."""
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Check ownership or admin
    if source.uploaded_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(source, key, value)

    db.commit()
    db.refresh(source)

    return SourceResponse.model_validate(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a source and its PDF (admin or owner only)."""
    source = db.query(Source).filter(Source.id == source_id).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Check ownership or admin
    if source.uploaded_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Delete PDF file if exists
    if source.pdf_path:
        file_path = UPLOAD_DIR / source.pdf_path
        if file_path.exists():
            os.remove(file_path)

    # Delete database record (citations cascade)
    db.delete(source)
    db.commit()

    return None
