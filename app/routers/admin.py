"""Admin endpoints for user and content management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.document import DocumentResponse
from app.dependencies import get_current_admin
from app.services.storage import delete_file

router = APIRouter()


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics."""
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_documents = db.query(func.count(Document.id)).scalar()
    public_documents = db.query(func.count(Document.id)).filter(Document.is_public == True).scalar()

    # Documents by type
    docs_by_type = (
        db.query(Document.file_type, func.count(Document.id))
        .group_by(Document.file_type)
        .all()
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
        },
        "documents": {
            "total": total_documents,
            "public": public_documents,
            "by_type": {t: c for t, c in docs_by_type},
        },
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all users."""
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get a specific user."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a user (activate/deactivate, promote to admin, etc.)."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion from admin
    if user.id == current_user.id and update_data.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Delete user's documents first
    user_docs = db.query(Document).filter(Document.uploaded_by == user_id).all()
    for doc in user_docs:
        delete_file(doc.file_path)
        db.delete(doc)

    # Delete user
    db.delete(user)
    db.commit()

    return None


@router.get("/documents", response_model=list[DocumentResponse])
async def list_all_documents(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all documents (admin view)."""
    documents = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_document(
    document_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete any document (admin only)."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete file from filesystem
    delete_file(document.file_path)

    # Delete database record
    db.delete(document)
    db.commit()

    return None
