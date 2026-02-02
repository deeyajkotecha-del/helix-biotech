"""Citation model for linking sources to report locations."""
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Citation(Base):
    """Citation linking a source to a specific location in a report."""

    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    report_ticker = Column(String(20), nullable=False, index=True)
    section_name = Column(String(100), nullable=False)  # e.g., 'bluf', 'pipeline', 'clinical'
    citation_number = Column(Integer, nullable=False)  # Per-page [1], [2], [3]
    context_text = Column(Text, nullable=True)  # The text being cited
    pdf_page = Column(Integer, nullable=True)  # Page to open in PDF viewer
    pdf_highlight = Column(String(500), nullable=True)  # Text to highlight in PDF
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint: one citation number per section per report
    __table_args__ = (
        UniqueConstraint('report_ticker', 'section_name', 'citation_number', name='uq_citation_location'),
    )

    # Relationships
    source = relationship("Source", back_populates="citations")

    def __repr__(self):
        return f"<Citation [{self.citation_number}] for {self.report_ticker}/{self.section_name}>"
