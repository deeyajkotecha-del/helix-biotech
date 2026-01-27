"""Document model for uploaded files."""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    """Uploaded document model."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=False)  # excel, presentation, article
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    uploader = relationship("User", backref="documents")

    def __repr__(self):
        return f"<Document {self.title}>"
