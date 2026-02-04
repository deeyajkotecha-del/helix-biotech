"""Clinical trial models for structured data storage."""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Float, Text, Boolean, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
import enum

from app.database import Base


class TrialPhaseEnum(enum.Enum):
    PHASE_1 = "Phase 1"
    PHASE_1A = "Phase 1a"
    PHASE_1B = "Phase 1b"
    PHASE_2 = "Phase 2"
    PHASE_2A = "Phase 2a"
    PHASE_2B = "Phase 2b"
    PHASE_3 = "Phase 3"


class EndpointCategoryEnum(enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPLORATORY = "exploratory"
    BIOMARKER = "biomarker"
    SAFETY = "safety"


class ClinicalTrialModel(Base):
    """Clinical trial with protocol and results data."""
    __tablename__ = "clinical_trials"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    asset_name = Column(String(100), nullable=False, index=True)
    nct_id = Column(String(20), unique=True, index=True, nullable=True)
    trial_name = Column(String(500))
    phase = Column(String(20))
    indication = Column(String(200), index=True)
    population_description = Column(Text)
    design_type = Column(String(100))
    primary_endpoint = Column(Text)
    enrollment_actual = Column(Integer)
    treatment_duration = Column(String(50))
    data_source = Column(String(200))
    arms = Column(JSON, default=list)
    endpoints = Column(JSON, default=list)
    safety_data = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ClinicalTrial {self.ticker}/{self.asset_name} - {self.trial_name}>"


class GraphAnalysisModel(Base):
    """PhD-level analysis of clinical data visualizations."""
    __tablename__ = "graph_analyses"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    asset_name = Column(String(100), nullable=False, index=True)
    trial_id = Column(Integer, ForeignKey("clinical_trials.id"), nullable=True)
    graph_title = Column(String(500))
    graph_type = Column(String(50))
    source_slide = Column(String(200))
    x_axis_label = Column(String(200))
    y_axis_label = Column(String(200))
    key_findings = Column(JSON, default=list)
    dose_response_analysis = Column(Text)
    clinical_significance = Column(Text)
    vs_competitor_analysis = Column(Text)
    limitations = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GraphAnalysis {self.ticker}/{self.asset_name} - {self.graph_title}>"
