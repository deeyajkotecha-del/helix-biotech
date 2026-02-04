"""
Clinical Data Extractor - PhD-level analysis of clinical trial data.

Extracts structured data from clinical presentations and generates
analysis for the Satya Bio platform.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TrialPhase(Enum):
    PHASE_1 = "Phase 1"
    PHASE_1B = "Phase 1b"
    PHASE_2 = "Phase 2"
    PHASE_2A = "Phase 2a"
    PHASE_2B = "Phase 2b"
    PHASE_3 = "Phase 3"


@dataclass
class Endpoint:
    """Clinical trial endpoint with results."""
    name: str
    category: str
    result: str
    p_value: Optional[float] = None
    confidence_interval: Optional[str] = None
    timepoint: Optional[str] = None
    dose_group: Optional[str] = None
    n: Optional[int] = None
    baseline: Optional[str] = None
    change_from_baseline: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class SafetyData:
    """Adverse event and safety data."""
    event_type: str
    incidence_drug: Optional[float] = None
    incidence_placebo: Optional[float] = None
    grade: Optional[str] = None
    serious: bool = False
    leading_to_discontinuation: bool = False
    notes: Optional[str] = None


@dataclass
class TrialArm:
    """A treatment arm in a clinical trial."""
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    n: Optional[int] = None
    duration: Optional[str] = None


@dataclass
class ClinicalTrial:
    """Complete clinical trial data structure."""
    nct_id: Optional[str] = None
    name: str = ""
    phase: Optional[TrialPhase] = None
    indication: str = ""
    population: str = ""
    design: str = ""
    arms: list[TrialArm] = field(default_factory=list)
    primary_endpoint: str = ""
    duration: str = ""
    endpoints: list[Endpoint] = field(default_factory=list)
    safety_data: list[SafetyData] = field(default_factory=list)
    data_cutoff: Optional[str] = None
    presentation_source: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "nct_id": self.nct_id,
            "name": self.name,
            "phase": self.phase.value if self.phase else None,
            "indication": self.indication,
            "population": self.population,
            "design": self.design,
            "arms": [{"name": a.name, "dose": a.dose, "frequency": a.frequency,
                      "n": a.n, "duration": a.duration} for a in self.arms],
            "primary_endpoint": self.primary_endpoint,
            "duration": self.duration,
            "endpoints": [vars(e) for e in self.endpoints],
            "safety_data": [vars(s) for s in self.safety_data],
            "data_cutoff": self.data_cutoff,
            "presentation_source": self.presentation_source
        }


@dataclass
class GraphAnalysis:
    """PhD-level analysis of a clinical data graph."""
    graph_title: str
    graph_type: str
    x_axis: str
    y_axis: str
    key_findings: list[str] = field(default_factory=list)
    dose_response: Optional[str] = None
    time_to_response: Optional[str] = None
    durability: Optional[str] = None
    plateau_observed: Optional[str] = None
    vs_placebo: Optional[str] = None
    vs_competitor: Optional[str] = None
    clinical_significance: Optional[str] = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return vars(self)


class ClinicalDataExtractor:
    """Extract and analyze clinical trial data from presentations."""

    def extract_kt621_phase1(self) -> ClinicalTrial:
        """Extract Phase 1 HV data for KT-621."""
        trial = ClinicalTrial(
            name="KT-621 Phase 1 Healthy Volunteer Study",
            phase=TrialPhase.PHASE_1,
            indication="Healthy Volunteers (HV)",
            population="Healthy adult volunteers",
            design="Single ascending dose and multiple ascending dose, randomized, placebo-controlled",
            primary_endpoint="Safety, tolerability, PK",
            duration="14 days dosing + follow-up",
            presentation_source="Kymera Corporate Presentation Jan 2026, Slide 22"
        )

        trial.arms = [
            TrialArm(name="Placebo", n=18, duration="14 days"),
            TrialArm(name="KT-621 25mg QD", dose="25mg", frequency="QD", n=9, duration="14 days"),
            TrialArm(name="KT-621 50mg QD", dose="50mg", frequency="QD", n=9, duration="14 days"),
            TrialArm(name="KT-621 100mg QD", dose="100mg", frequency="QD", n=9, duration="14 days"),
            TrialArm(name="KT-621 200mg QD", dose="200mg", frequency="QD", n=9, duration="14 days"),
        ]

        trial.endpoints = [
            Endpoint(
                name="STAT6 % Change from Baseline - Blood",
                category="biomarker",
                result=">90% degradation",
                dose_group="25-200mg QD",
                timepoint="Day 14",
                notes="Plateau at maximal degradation"
            ),
            Endpoint(
                name="STAT6 % Change from Baseline - Skin",
                category="biomarker",
                result=">90% degradation",
                dose_group="25-200mg QD",
                timepoint="Day 14",
                notes="Target tissue engagement confirmed"
            ),
            Endpoint(
                name="Serum TARC % Change from Baseline",
                category="biomarker",
                result="-20 to -40% reduction",
                dose_group="50-200mg QD",
                timepoint="Day 14",
                notes="Dose-dependent reduction in Type 2 inflammation marker"
            ),
        ]

        trial.safety_data = [
            SafetyData(
                event_type="Overall AE profile",
                notes="Well-tolerated; safety undifferentiated from placebo"
            ),
            SafetyData(
                event_type="Serious Adverse Events",
                incidence_drug=0.0,
                incidence_placebo=0.0,
                serious=True,
                notes="No SAEs reported"
            ),
        ]

        return trial

    def extract_kt621_phase2(self) -> ClinicalTrial:
        """Extract Phase 2 AD data for KT-621."""
        trial = ClinicalTrial(
            name="KT-621 Phase 2 in Moderate-to-Severe Atopic Dermatitis",
            phase=TrialPhase.PHASE_2,
            indication="Atopic Dermatitis",
            population="Moderate-to-severe atopic dermatitis (AD)",
            design="Open-label, dose-ranging",
            primary_endpoint="EASI (Eczema Area and Severity Index) change from baseline",
            duration="29 days on treatment + 14 days follow-up",
            presentation_source="Kymera Corporate Presentation Jan 2026, Slide 28"
        )

        trial.arms = [
            TrialArm(name="KT-621 100mg QD", dose="100mg", frequency="QD", n=10, duration="29 days"),
            TrialArm(name="KT-621 200mg QD", dose="200mg", frequency="QD", n=12, duration="29 days"),
        ]

        trial.endpoints = [
            Endpoint(
                name="EASI % Change from Baseline",
                category="primary",
                result="-63%",
                dose_group="Overall (n=22)",
                n=22,
                timepoint="Day 29"
            ),
            Endpoint(
                name="EASI-50 (>=50% improvement)",
                category="secondary",
                result="76% achieved",
                dose_group="Overall",
                n=22,
                timepoint="Day 29"
            ),
            Endpoint(
                name="EASI-75 (>=75% improvement)",
                category="secondary",
                result="29% achieved",
                dose_group="Overall",
                n=22,
                timepoint="Day 29",
                notes="Higher rates expected with longer treatment"
            ),
        ]

        return trial

    def analyze_phase1_graphs(self) -> list[GraphAnalysis]:
        """PhD-level analysis of Phase 1 graphs."""
        return [
            GraphAnalysis(
                graph_title="STAT6 Degradation in Blood and Skin",
                graph_type="bar",
                x_axis="Dose Group",
                y_axis="STAT6 % Change from Baseline",
                key_findings=[
                    "Clear dose-response relationship for STAT6 degradation",
                    "Blood STAT6 degradation reaches plateau (~90%) at doses >=25mg",
                    "Skin penetration confirmed - critical for dermatological indications"
                ],
                dose_response="Sigmoid dose-response: plateau at >=25mg",
                clinical_significance="90%+ STAT6 degradation suggests potential Dupixent-like efficacy",
                limitations=[
                    "Healthy volunteers - may not reflect diseased skin",
                    "Small sample sizes (n=7-9 per arm)"
                ]
            )
        ]

    def analyze_phase2_graphs(self) -> list[GraphAnalysis]:
        """PhD-level analysis of Phase 2 graphs."""
        return [
            GraphAnalysis(
                graph_title="Mean % Change from Baseline in EASI",
                graph_type="line",
                x_axis="Time (Day)",
                y_axis="Mean Percent Change from Baseline in EASI",
                key_findings=[
                    "Rapid and progressive EASI improvement: -63% at Day 29",
                    "NO apparent plateau - efficacy may still be increasing",
                    "100mg and 200mg show similar efficacy"
                ],
                dose_response="Flat between 100-200mg - 100mg may be optimal",
                time_to_response="Significant improvement by Day 8",
                plateau_observed="No plateau at Day 29",
                vs_competitor="Dupixent: ~70-75% at Week 16. KT-621 at 63% Day 29 is encouraging",
                clinical_significance="EASI-50 of 76% suggests potential for Dupixent-like efficacy",
                limitations=[
                    "Open-label design - placebo effect possible",
                    "Small sample size (n=22)",
                    "Only 29 days - need 12-16 week data"
                ]
            )
        ]


def generate_clinical_summary_for_asset(asset_name: str = "KT-621") -> dict:
    """Generate complete clinical data package for an asset."""
    extractor = ClinicalDataExtractor()

    phase1 = extractor.extract_kt621_phase1()
    phase2 = extractor.extract_kt621_phase2()
    phase1_analysis = extractor.analyze_phase1_graphs()
    phase2_analysis = extractor.analyze_phase2_graphs()

    return {
        "asset": {
            "name": asset_name,
            "company": "Kymera Therapeutics",
            "ticker": "KYMR",
            "target": "STAT6",
            "mechanism": "STAT6 degrader (targeted protein degradation)",
            "modality": "Oral small molecule degrader"
        },
        "clinical_development": {
            "current_stage": "Phase 2b",
            "indications_in_development": [
                "Atopic Dermatitis",
                "Asthma",
                "Chronic Rhinosinusitis with Nasal Polyps (CRSwNP)",
                "Prurigo Nodularis"
            ]
        },
        "trials": [phase1.to_dict(), phase2.to_dict()],
        "graph_analyses": {
            "phase1_biomarker_data": [a.to_dict() for a in phase1_analysis],
            "phase2_efficacy_data": [a.to_dict() for a in phase2_analysis]
        },
        "investment_thesis_points": [
            "First oral STAT6 degrader - potential to replace/complement Dupixent ($13B+ sales)",
            "Phase 1 HV: >90% STAT6 degradation in blood AND skin at well-tolerated doses",
            "Phase 2 AD: 63% EASI reduction at Day 29 without plateau",
            "Oral convenience advantage over Dupixent (injection every 2 weeks)",
            "Broad indication potential across Type 2 inflammatory diseases"
        ],
        "key_risks": [
            "Open-label Phase 2 - need placebo-controlled data",
            "Only 29 days treatment - need 12-16 week data",
            "Small sample sizes (n=22 in Phase 2)",
            "Competitive landscape: multiple IL-4/IL-13 pathway drugs"
        ],
        "upcoming_catalysts": [
            "Phase 2b randomized, placebo-controlled trial readout (2026)",
            "Asthma Phase 2 initiation"
        ],
        "source": "Kymera Therapeutics Corporate Presentation, January 2026"
    }
