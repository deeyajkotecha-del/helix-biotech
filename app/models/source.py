"""Source model for citable documents."""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Date
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Source(Base):
    """Citable document/source model."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    authors = Column(JSON, nullable=True)  # List of author names
    publication_date = Column(Date, nullable=True)
    source_type = Column(
        String(50),
        nullable=False
    )  # 'journal_article', 'sec_filing', 'conference_poster', 'internal_document', 'presentation'
    journal_name = Column(String(255), nullable=True)
    doi = Column(String(255), nullable=True, index=True)
    pmid = Column(String(50), nullable=True, index=True)
    url = Column(String(1000), nullable=True)
    pdf_path = Column(String(500), nullable=True)  # sources/{uuid}.pdf
    abstract = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    uploader = relationship("User", backref="sources")
    citations = relationship("Citation", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Source {self.title[:50]}>"
