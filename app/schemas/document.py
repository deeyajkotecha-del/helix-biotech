"""Document schemas for request/response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentCreate(BaseModel):
    """Schema for creating a document (metadata only, file uploaded separately)."""
    title: str
    description: Optional[str] = None
    is_public: bool = False


class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: int
    title: str
    description: Optional[str]
    file_type: str
    original_filename: str
    file_size: Optional[int]
    uploaded_by: int
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
