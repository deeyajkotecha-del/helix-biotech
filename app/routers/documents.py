"""Document upload and management endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentUpdate
from app.dependencies import get_current_user, get_optional_user
from app.services.storage import validate_file, save_file, delete_file, get_file_path

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a new document."""
    # Validate file
    is_valid, result = validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result,
        )

    file_type = result

    # Save file
    try:
        relative_path, file_size = await save_file(file, file_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Create document record
    document = Document(
        title=title,
        description=description,
        file_type=file_type,
        file_path=relative_path,
        original_filename=file.filename,
        file_size=file_size,
        uploaded_by=current_user.id,
        is_public=is_public,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    file_type: Optional[str] = None,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """List documents. Shows public docs and user's own docs if authenticated."""
    query = db.query(Document)

    if current_user:
        # Show public docs + user's own docs
        query = query.filter(
            (Document.is_public == True) | (Document.uploaded_by == current_user.id)
        )
    else:
        # Only show public docs
        query = query.filter(Document.is_public == True)

    if file_type:
        query = query.filter(Document.file_type == file_type)

    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get document metadata."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check access
    if not document.is_public:
        if not current_user or document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Download a document file."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check access
    if not document.is_public:
        if not current_user or document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    file_path = get_file_path(document.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server",
        )

    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type="application/octet-stream",
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update document metadata."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check ownership (or admin)
    if document.uploaded_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(document, key, value)

    db.commit()
    db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check ownership (or admin)
    if document.uploaded_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Delete file from filesystem
    delete_file(document.file_path)

    # Delete database record
    db.delete(document)
    db.commit()

    return None
