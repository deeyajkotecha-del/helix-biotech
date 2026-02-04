"""
Kymera Clinical Data with Contextual Definitions & Methods

This module includes:
1. Endpoint definitions (what is EASI, SCORAD, etc.)
2. Biomarker explanations (what is STAT6, TARC, etc.)
3. Measurement methods (Flow Cytometry, Mass Spec, etc.)
4. Clinical significance (why does this matter)

This enables the UI to show tooltips/expandable definitions.
"""

# =============================================================================
# ENDPOINT DEFINITIONS
# =============================================================================

ENDPOINT_DEFINITIONS = {
    # Atopic Dermatitis Endpoints
    "EASI": {
        "name": "EASI",
        "full_name": "Eczema Area and Severity Index",
        "category": "Clinical Efficacy",
        "description": "Physician-assessed measure of atopic dermatitis severity combining extent (body surface area) and intensity (erythema, induration, excoriation, lichenification) across 4 body regions.",
        "scoring": "0-72 scale; higher = more severe. Mild: 1-7, Moderate: 7-21, Severe: 21-50, Very Severe: >50",
        "interpretation": {
            "EASI-50": "≥50% reduction from baseline - clinically meaningful improvement",
            "EASI-75": "≥75% reduction from baseline - significant improvement, often used as primary endpoint",
            "EASI-90": "≥90% reduction from baseline - near-complete clearance"
        },
        "regulatory_status": "FDA-accepted primary endpoint for AD trials",
        "comparator_benchmarks": {
            "Dupixent": "~70-75% EASI reduction at Week 16",
            "Placebo": "~15-25% EASI reduction at Week 16"
        }
    },
    
    "SCORAD": {
        "name": "SCORAD",
        "full_name": "SCORing Atopic Dermatitis",
        "category": "Clinical Efficacy",
        "description": "Composite score combining objective physician assessment (extent, intensity) with subjective patient symptoms (itch, sleep loss).",
        "scoring": "0-103 scale. Mild: <25, Moderate: 25-50, Severe: >50",
        "components": {
            "A": "Extent (0-100) - % body surface area affected",
            "B": "Intensity (0-18) - 6 items scored 0-3 each",
            "C": "Subjective (0-20) - itch + sleep loss VAS"
        },
        "formula": "SCORAD = A/5 + 7B/2 + C",
        "interpretation": "Captures both objective disease AND patient experience; more holistic than EASI alone"
    },
    
    "vIGA-AD": {
        "name": "vIGA-AD",
        "full_name": "Validated Investigator Global Assessment for Atopic Dermatitis",
        "category": "Clinical Efficacy",
        "description": "Physician's overall assessment of AD severity on a 5-point scale.",
        "scoring": {
            "0": "Clear - no inflammatory signs",
            "1": "Almost Clear - just perceptible erythema/induration",
            "2": "Mild - slight but definite erythema/induration",
            "3": "Moderate - clearly perceptible erythema/induration",
            "4": "Severe - marked erythema/induration"
        },
        "success_definition": "vIGA-AD 0 or 1 (Clear or Almost Clear)",
        "regulatory_status": "FDA co-primary endpoint for AD (with EASI-75)"
    },
    
    "PPNRS": {
        "name": "PP-NRS",
        "full_name": "Peak Pruritus Numerical Rating Scale",
        "category": "Patient-Reported Outcome",
        "description": "Patient-reported measure of worst itch intensity in the past 24 hours.",
        "scoring": "0-10 scale; 0 = no itch, 10 = worst imaginable itch",
        "interpretation": {
            "≥4-point improvement": "Clinically meaningful itch reduction",
            "≥3-point improvement": "Moderate itch improvement"
        },
        "clinical_relevance": "Itch is the most bothersome symptom for AD patients; strongly impacts quality of life and sleep"
    },
    
    "POEM": {
        "name": "POEM",
        "full_name": "Patient-Oriented Eczema Measure",
        "category": "Patient-Reported Outcome",
        "description": "7-item questionnaire measuring AD symptoms and their frequency over the past week.",
        "scoring": "0-28; higher = more severe. Mild: 3-7, Moderate: 8-16, Severe: 17-24, Very Severe: 25-28",
        "mcid": "≥4-point improvement is Minimum Clinically Important Difference",
        "clinical_relevance": "Captures patient's experience of disease impact on daily life"
    },
    
    "DLQI": {
        "name": "DLQI",
        "full_name": "Dermatology Life Quality Index",
        "category": "Quality of Life",
        "description": "10-question validated questionnaire measuring impact of skin disease on quality of life.",
        "scoring": "0-30; higher = greater impairment. 0-1: no effect, 2-5: small, 6-10: moderate, 11-20: large, 21-30: extremely large",
        "mcid": "≥4-point improvement is Minimum Clinically Important Difference",
        "clinical_relevance": "Measures impact on work, relationships, daily activities, treatment burden"
    },
    
    # Asthma Endpoints
    "FEV1": {
        "name": "FEV1",
        "full_name": "Forced Expiratory Volume in 1 Second",
        "category": "Pulmonary Function",
        "description": "Volume of air that can be forcibly exhaled in one second. Gold standard measure of airway obstruction.",
        "measurement": "Spirometry; expressed as absolute (L) or % predicted for age/height/sex",
        "interpretation": {
            "normal": "≥80% predicted",
            "mild obstruction": "70-79% predicted",
            "moderate obstruction": "60-69% predicted",
            "severe obstruction": "<60% predicted"
        },
        "pre_vs_post_bronchodilator": "Pre-BD measures baseline obstruction; Post-BD shows reversibility",
        "regulatory_status": "FDA-accepted primary endpoint for asthma trials"
    },
    
    "ACQ-5": {
        "name": "ACQ-5",
        "full_name": "Asthma Control Questionnaire (5-item)",
        "category": "Patient-Reported Outcome",
        "description": "5-item questionnaire assessing asthma symptom control over past week.",
        "scoring": "0-6 scale; lower = better control. <0.75: well-controlled, 0.75-1.5: partly controlled, >1.5: uncontrolled",
        "mcid": "≥0.5-point improvement is clinically meaningful",
        "clinical_relevance": "Captures real-world symptom burden and control"
    },
    
    "FeNO": {
        "name": "FeNO",
        "full_name": "Fractional Exhaled Nitric Oxide",
        "category": "Biomarker",
        "description": "Measures nitric oxide in exhaled breath, a marker of eosinophilic airway inflammation.",
        "measurement": "Parts per billion (ppb) via exhaled breath analyzer",
        "interpretation": {
            "<25 ppb": "Normal/low inflammation",
            "25-50 ppb": "Intermediate",
            ">50 ppb": "High Type 2 inflammation"
        },
        "clinical_relevance": "Predicts response to IL-4/IL-13 pathway therapies; marker of Type 2 inflammation in airways"
    },
    
    # Lupus Endpoints
    "anti-dsDNA": {
        "name": "Anti-dsDNA",
        "full_name": "Anti-double-stranded DNA Antibodies",
        "category": "Biomarker/Autoantibody",
        "description": "Autoantibodies targeting double-stranded DNA; highly specific for systemic lupus erythematosus (SLE).",
        "measurement": "ELISA, Farr assay, or immunofluorescence; reported as titer or units",
        "clinical_relevance": "Elevated in 70-80% of SLE patients; correlates with disease activity and lupus nephritis risk",
        "interpretation": "Reduction indicates decreased autoimmune activity and potential disease modification"
    },
    
    # Rheumatoid Arthritis Endpoints
    "joint_swelling": {
        "name": "Joint Swelling",
        "full_name": "Swollen Joint Count",
        "category": "Clinical Efficacy",
        "description": "Number of joints with clinically detectable swelling (synovitis).",
        "measurement": "Physical examination of 66 joints (SJC66) or 28 joints (SJC28)",
        "clinical_relevance": "Direct measure of active inflammation; reduction indicates therapeutic benefit"
    }
}


# =============================================================================
# BIOMARKER DEFINITIONS
# =============================================================================

BIOMARKER_DEFINITIONS = {
    "STAT6": {
        "name": "STAT6",
        "full_name": "Signal Transducer and Activator of Transcription 6",
        "type": "Transcription Factor",
        "pathway": "IL-4/IL-13 signaling",
        "biology": "STAT6 is phosphorylated and activated when IL-4 or IL-13 binds to their receptors. Activated STAT6 translocates to the nucleus and drives transcription of genes involved in Type 2 inflammation, including those for IgE class switching, mucus production, and Th2 differentiation.",
        "role_in_disease": {
            "AD": "Drives skin barrier dysfunction, itch, and inflammation",
            "Asthma": "Promotes mucus hypersecretion, airway hyperreactivity, eosinophilia",
            "EoE": "Drives eosinophil recruitment to esophagus"
        },
        "measurement_methods": {
            "flow_cytometry": {
                "description": "Intracellular staining of STAT6 protein in blood cells",
                "sample": "Whole blood or PBMCs",
                "readout": "% STAT6+ cells or Mean Fluorescence Intensity",
                "used_for": "Blood STAT6 levels"
            },
            "targeted_mass_spectrometry": {
                "description": "Quantitative measurement of STAT6 protein in tissue",
                "sample": "Skin biopsy",
                "readout": "Absolute protein quantification",
                "used_for": "Skin STAT6 levels (target tissue)"
            },
            "immunohistochemistry": {
                "description": "Visualization of STAT6 protein in tissue sections",
                "sample": "Skin biopsy",
                "readout": "Staining intensity and distribution",
                "used_for": "Localization and semi-quantification"
            }
        },
        "clinical_significance": "STAT6 degradation >90% indicates complete pathway blockade, equivalent to biologic-level inhibition",
        "reference_drug": "Dupixent blocks IL-4Rα upstream of STAT6; STAT6 degradation achieves same pathway blockade"
    },
    
    "TARC": {
        "name": "TARC",
        "full_name": "Thymus and Activation-Regulated Chemokine (CCL17)",
        "type": "Chemokine",
        "pathway": "IL-4/IL-13 → STAT6 → TARC transcription",
        "biology": "TARC is produced by dendritic cells and keratinocytes in response to STAT6 activation. It recruits CCR4+ T cells (Th2 cells) to sites of inflammation.",
        "role_in_disease": {
            "AD": "Elevated in AD patients; correlates with disease severity; recruits inflammatory T cells to skin"
        },
        "measurement_methods": {
            "serum_elisa": {
                "description": "ELISA or MSD VPLEX assay",
                "sample": "Serum",
                "readout": "pg/mL concentration",
                "normal_range": "<450 pg/mL in healthy adults"
            }
        },
        "clinical_significance": "Serum TARC is a validated biomarker of Type 2 inflammation in AD; reduction indicates on-target activity",
        "reference_drug": "Dupixent reduces TARC ~50-70% in AD patients"
    },
    
    "Eotaxin-3": {
        "name": "Eotaxin-3",
        "full_name": "CCL26",
        "type": "Chemokine",
        "pathway": "IL-4/IL-13 → STAT6 → Eotaxin-3 transcription",
        "biology": "Eotaxin-3 is a potent eosinophil chemoattractant produced by epithelial cells in response to IL-4/IL-13. It recruits eosinophils to inflamed tissues.",
        "role_in_disease": {
            "AD": "Drives eosinophil infiltration into skin lesions",
            "Asthma": "Recruits eosinophils to airways",
            "EoE": "Key driver of esophageal eosinophilia"
        },
        "measurement_methods": {
            "serum_elisa": {
                "description": "MSD VPLEX or ELISA",
                "sample": "Serum",
                "readout": "pg/mL concentration"
            }
        },
        "clinical_significance": "Reduction indicates decreased eosinophil recruitment; predicts efficacy in eosinophilic diseases"
    },
    
    "IgE": {
        "name": "IgE",
        "full_name": "Immunoglobulin E",
        "type": "Antibody",
        "pathway": "IL-4 → STAT6 → B cell class switching to IgE",
        "biology": "IgE is produced by B cells after IL-4-driven class switching. It binds to mast cells and basophils, triggering allergic responses upon allergen exposure.",
        "role_in_disease": {
            "AD": "Elevated total IgE in ~80% of AD patients; allergen-specific IgE drives flares",
            "Asthma": "Mediates allergic asthma; target of omalizumab"
        },
        "measurement_methods": {
            "serum_immunoassay": {
                "description": "Chemiluminescent immunoassay",
                "sample": "Serum",
                "readout": "IU/mL",
                "normal_range": "<100 IU/mL in adults"
            }
        },
        "clinical_significance": "IgE reduction indicates suppression of allergic arm of Type 2 response; slower to change than TARC/Eotaxin"
    },
    
    "IL-31": {
        "name": "IL-31",
        "full_name": "Interleukin-31",
        "type": "Cytokine",
        "pathway": "Produced by activated Th2 cells",
        "biology": "IL-31 signals through IL-31RA/OSMR receptor complex on sensory neurons, keratinocytes, and immune cells. It is a key pruritogenic (itch-causing) cytokine.",
        "role_in_disease": {
            "AD": "Major driver of itch; correlates with pruritus severity; elevated in lesional skin"
        },
        "measurement_methods": {
            "serum_elisa": {
                "description": "High-sensitivity ELISA",
                "sample": "Serum",
                "readout": "pg/mL"
            }
        },
        "clinical_significance": "IL-31 reduction correlates with itch improvement; nemolizumab (anti-IL-31RA) validates this target"
    },
    
    "IRF5": {
        "name": "IRF5",
        "full_name": "Interferon Regulatory Factor 5",
        "type": "Transcription Factor",
        "pathway": "TLR/MyD88 → IRF5 activation → Type I IFN + pro-inflammatory cytokines",
        "biology": "IRF5 is a master regulator of innate immunity. Upon TLR stimulation, it is phosphorylated and translocates to the nucleus to drive transcription of Type I interferons (IFNα/β), TNFα, IL-6, IL-12, IL-23, and other pro-inflammatory mediators.",
        "role_in_disease": {
            "SLE": "IRF5 risk variants increase susceptibility; drives IFN signature and autoantibody production",
            "RA": "Drives TNFα and IL-6 in synovium",
            "Sjögren's": "IRF5 variants associated; drives glandular inflammation"
        },
        "measurement_methods": {
            "flow_cytometry": {
                "description": "Intracellular staining in PBMCs",
                "sample": "Whole blood",
                "readout": "% IRF5+ cells or MFI"
            }
        },
        "clinical_significance": "IRF5 degradation blocks multiple pathogenic pathways simultaneously - broader than single-cytokine approaches",
        "genetic_validation": "GWAS identifies IRF5 as autoimmune susceptibility gene"
    },
    
    "IRAK4": {
        "name": "IRAK4",
        "full_name": "Interleukin-1 Receptor Associated Kinase 4",
        "type": "Scaffolding Kinase",
        "pathway": "IL-1R/TLR → MyD88 → IRAK4 → TRAF6 → NF-κB → inflammation",
        "biology": "IRAK4 is an obligate signaling node downstream of IL-1R and most TLRs. It has both kinase activity AND scaffolding function in the Myddosome complex. Both functions contribute to inflammatory signaling.",
        "role_in_disease": {
            "HS": "IL-1 signaling drives neutrophilic inflammation in hair follicles",
            "AD": "IL-33 signaling contributes to Type 2 inflammation",
            "RA": "IL-1 drives synovial inflammation and joint destruction"
        },
        "measurement_methods": {
            "flow_cytometry": {
                "description": "Intracellular staining",
                "sample": "PBMCs",
                "readout": "% IRAK4+ cells"
            }
        },
        "clinical_significance": "IRAK4 degradation blocks BOTH kinase and scaffolding functions - more complete than kinase inhibitors",
        "genetic_validation": "IRAK4-null humans are healthy → validates safety of complete inhibition"
    }
}


# =============================================================================
# ENHANCED ENDPOINT DATA WITH METHODS
# =============================================================================

def get_endpoint_with_context(endpoint_name: str, result: str, method: str = None, timepoint: str = None) -> dict:
    """
    Return endpoint result with full contextual information.
    
    Example:
        get_endpoint_with_context("EASI", "-63%", timepoint="Day 29")
        
    Returns dict with result + definition + interpretation + benchmarks
    """
    definition = ENDPOINT_DEFINITIONS.get(endpoint_name, {})
    
    return {
        "endpoint": endpoint_name,
        "full_name": definition.get("full_name", endpoint_name),
        "result": result,
        "timepoint": timepoint,
        "method": method,
        "category": definition.get("category"),
        "description": definition.get("description"),
        "scoring": definition.get("scoring"),
        "interpretation": definition.get("interpretation"),
        "mcid": definition.get("mcid"),
        "regulatory_status": definition.get("regulatory_status"),
        "comparator_benchmarks": definition.get("comparator_benchmarks"),
        "clinical_relevance": definition.get("clinical_relevance")
    }


def get_biomarker_with_context(biomarker_name: str, result: str, method: str = None, 
                                tissue: str = None, timepoint: str = None) -> dict:
    """
    Return biomarker result with full contextual information.
    
    Example:
        get_biomarker_with_context("STAT6", ">90% degradation", 
                                    method="flow_cytometry", tissue="blood")
    """
    definition = BIOMARKER_DEFINITIONS.get(biomarker_name, {})
    method_info = definition.get("measurement_methods", {}).get(method, {}) if method else {}
    
    return {
        "biomarker": biomarker_name,
        "full_name": definition.get("full_name", biomarker_name),
        "result": result,
        "timepoint": timepoint,
        "tissue": tissue,
        "type": definition.get("type"),
        "pathway": definition.get("pathway"),
        "biology": definition.get("biology"),
        "role_in_disease": definition.get("role_in_disease"),
        "measurement_method": {
            "name": method,
            "description": method_info.get("description"),
            "sample": method_info.get("sample"),
            "readout": method_info.get("readout")
        } if method else None,
        "clinical_significance": definition.get("clinical_significance"),
        "reference_drug": definition.get("reference_drug")
    }


# =============================================================================
# KT-621 DATA WITH FULL CONTEXT
# =============================================================================

KT621_ENDPOINTS_WITH_CONTEXT = {
    "phase1b_efficacy": [
        get_endpoint_with_context(
            "EASI", 
            "-63%", 
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "EASI-50",
            "76% achieved",
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "EASI-75",
            "29% achieved", 
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "vIGA-AD",
            "19% achieved 0/1",
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "SCORAD",
            "-48%",
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "PPNRS",
            "-40%",
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "POEM",
            "73% responders (≥4-point improvement)",
            timepoint="Day 29"
        ),
        get_endpoint_with_context(
            "DLQI",
            "61% responders (≥4-point improvement)",
            timepoint="Day 29"
        )
    ],
    "phase1b_biomarkers": [
        get_biomarker_with_context(
            "STAT6",
            "98% degradation",
            method="flow_cytometry",
            tissue="Blood",
            timepoint="Day 29"
        ),
        get_biomarker_with_context(
            "STAT6",
            "94% degradation",
            method="targeted_mass_spectrometry",
            tissue="Skin",
            timepoint="Day 29"
        ),
        get_biomarker_with_context(
            "TARC",
            "-74% reduction",
            method="serum_elisa",
            tissue="Serum",
            timepoint="Day 29"
        ),
        get_biomarker_with_context(
            "Eotaxin-3",
            "-73% reduction",
            method="serum_elisa",
            tissue="Serum",
            timepoint="Day 29"
        ),
        get_biomarker_with_context(
            "IL-31",
            "-54% reduction",
            method="serum_elisa",
            tissue="Serum",
            timepoint="Day 29"
        ),
        get_biomarker_with_context(
            "IgE",
            "-14% reduction",
            method="serum_immunoassay",
            tissue="Serum",
            timepoint="Day 29"
        ),
        get_biomarker_with_context(
            "FeNO",
            "-56% reduction (comorbid asthma patients, n=4)",
            tissue="Exhaled breath",
            timepoint="Day 29"
        )
    ]
}


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def get_all_endpoint_definitions() -> dict:
    """Return all endpoint definitions for UI tooltips."""
    return ENDPOINT_DEFINITIONS


def get_all_biomarker_definitions() -> dict:
    """Return all biomarker definitions for UI tooltips."""
    return BIOMARKER_DEFINITIONS


def get_kt621_data_with_context() -> dict:
    """Return KT-621 data with full contextual definitions."""
    return KT621_ENDPOINTS_WITH_CONTEXT


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    import json
    
    # Example: Get EASI endpoint with context
    easi_data = get_endpoint_with_context("EASI", "-63%", timepoint="Day 29")
    print("EASI Endpoint with Context:")
    print(json.dumps(easi_data, indent=2))
    
    print("\n" + "="*60 + "\n")
    
    # Example: Get STAT6 biomarker with context
    stat6_data = get_biomarker_with_context(
        "STAT6", 
        "98% degradation",
        method="flow_cytometry",
        tissue="Blood",
        timepoint="Day 29"
    )
    print("STAT6 Biomarker with Context:")
    print(json.dumps(stat6_data, indent=2))
