"""
Kymera Therapeutics - Full Pipeline Clinical Data Extraction
Source: Kymera Corporate Presentation January 2026

Assets:
- KT-621 (STAT6 degrader) - Phase 2b
- KT-579 (IRF5 degrader) - Phase 1
- KT-485 (IRAK4 degrader) - Phase 1 (partnered with Sanofi)
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class ClinicalStage(Enum):
    PRECLINICAL = "Preclinical"
    IND_ENABLING = "IND-Enabling"
    PHASE_1 = "Phase 1"
    PHASE_1B = "Phase 1b"
    PHASE_2 = "Phase 2"
    PHASE_2B = "Phase 2b"
    PHASE_3 = "Phase 3"
    APPROVED = "Approved"


# =============================================================================
# KYMERA COMPANY DATA
# =============================================================================

KYMERA_COMPANY = {
    "name": "Kymera Therapeutics",
    "ticker": "KYMR",
    "headquarters": "Watertown, MA",
    "website": "https://www.kymeratx.com",
    "modalities": ["Targeted Protein Degradation", "Degrader", "Molecular Glue"],
    "therapeutic_focus": ["Immunology", "Oncology"],
    "description": """Kymera Therapeutics is pioneering targeted protein degradation (TPD) 
to address diseases driven by high-value, previously undruggable targets. Their platform 
uses small molecules (degraders) that can eliminate disease-causing proteins rather than 
just inhibiting them, potentially offering biologics-like efficacy in an oral pill.

Key differentiators:
- Industry leader in developing oral degrader medicines
- Focus on historically undrugged transcription factors (STAT6, IRF5)
- Deep expertise in target-drug interplay across tissues and cell types
- Building a fully integrated global immunology company""",
    "cash_runway": "Into 2029",
    "partnerships": [
        {
            "partner": "Sanofi",
            "asset": "KT-485/SAR447971 (IRAK4 degrader)",
            "status": "Active",
            "notes": "Sanofi to advance KT-485 into Phase 1 in 2026"
        },
        {
            "partner": "Gilead",
            "asset": "CDK2 Molecular Glue Degrader",
            "value": "Up to $750M total payments ($85M upfront + option)",
            "status": "Active",
            "notes": "Kymera leads research; Gilead has option for development/commercialization"
        }
    ]
}


# =============================================================================
# KT-621 (STAT6 DEGRADER) - LEAD ASSET
# =============================================================================

KT621_DATA = {
    "asset": {
        "name": "KT-621",
        "company": "Kymera Therapeutics",
        "ticker": "KYMR",
        "target": "STAT6",
        "target_full_name": "Signal Transducer and Activator of Transcription 6",
        "mechanism": "STAT6 degrader (targeted protein degradation)",
        "modality": "Oral small molecule degrader",
        "pathway": "IL-4/IL-13 signaling",
        "competitor_reference": "Dupilumab (Dupixent) - $13B+ annual sales"
    },
    "clinical_development": {
        "current_stage": "Phase 2b",
        "indications_in_development": [
            "Atopic Dermatitis",
            "Asthma", 
            "COPD",
            "Eosinophilic Esophagitis (EoE)",
            "Chronic Rhinosinusitis with Nasal Polyps (CRSwNP)",
            "Chronic Spontaneous Urticaria (CSU)",
            "Prurigo Nodularis (PN)",
            "Bullous Pemphigoid (BP)"
        ],
        "market_opportunity": ">140M patients; only ~1% on advanced systemic therapies; >$20B market projected by 2030"
    },
    "trials": [
        {
            "name": "KT-621 Phase 1 Healthy Volunteer Study (SAD/MAD)",
            "phase": "Phase 1",
            "status": "Completed",
            "indication": "Healthy Volunteers",
            "design": "Single and multiple ascending dose, randomized, placebo-controlled",
            "arms": [
                {"name": "Placebo", "n": 18, "duration": "14 days"},
                {"name": "KT-621 1.5mg QD", "dose": "1.5mg", "frequency": "QD", "n": 9},
                {"name": "KT-621 12.5mg QD", "dose": "12.5mg", "frequency": "QD", "n": 7},
                {"name": "KT-621 25mg QD", "dose": "25mg", "frequency": "QD", "n": 9},
                {"name": "KT-621 50mg QD", "dose": "50mg", "frequency": "QD", "n": 9},
                {"name": "KT-621 100mg QD", "dose": "100mg", "frequency": "QD", "n": 9},
                {"name": "KT-621 200mg QD", "dose": "200mg", "frequency": "QD", "n": 9}
            ],
            "endpoints": [
                {"name": "STAT6 degradation - Blood", "category": "biomarker", "result": ">90% at doses ≥25mg QD", "timepoint": "Day 14"},
                {"name": "STAT6 degradation - Skin", "category": "biomarker", "result": ">90% at doses ≥25mg QD", "timepoint": "Day 14"},
                {"name": "Serum TARC reduction", "category": "biomarker", "result": "-20 to -40%", "dose_group": "50-200mg QD", "timepoint": "Day 14"},
                {"name": "Serum Eotaxin-3 reduction", "category": "biomarker", "result": "-40 to -70%", "dose_group": "100-200mg QD", "timepoint": "Day 14"}
            ],
            "safety": "Well-tolerated; safety profile undifferentiated from placebo; no SAEs; no dose-dependent TEAEs"
        },
        {
            "name": "BroADen Phase 1b in Atopic Dermatitis",
            "phase": "Phase 1b",
            "status": "Completed",
            "indication": "Moderate-to-severe Atopic Dermatitis",
            "design": "Single arm, open label",
            "population": "Adult moderate-to-severe AD patients (EASI≥16, vIGA-AD≥3, PPNRS≥4, BSA≥10%)",
            "arms": [
                {"name": "KT-621 100mg QD", "dose": "100mg", "frequency": "QD", "n": 10, "duration": "28 days"},
                {"name": "KT-621 200mg QD", "dose": "200mg", "frequency": "QD", "n": 12, "duration": "28 days"}
            ],
            "endpoints": [
                {"name": "STAT6 degradation - Blood", "category": "biomarker", "result": "98% median", "timepoint": "Day 29"},
                {"name": "STAT6 degradation - Skin", "category": "biomarker", "result": "94%", "timepoint": "Day 29"},
                {"name": "EASI % Change", "category": "primary", "result": "-63%", "dose_group": "Overall (n=22)", "timepoint": "Day 29"},
                {"name": "EASI-50", "category": "secondary", "result": "76% achieved", "timepoint": "Day 29"},
                {"name": "EASI-75", "category": "secondary", "result": "29% achieved", "timepoint": "Day 29"},
                {"name": "vIGA-AD 0/1", "category": "secondary", "result": "19% achieved", "timepoint": "Day 29"},
                {"name": "SCORAD % Change", "category": "secondary", "result": "-48%", "timepoint": "Day 29"},
                {"name": "Peak Pruritus NRS % Change", "category": "secondary", "result": "-40%", "timepoint": "Day 29"},
                {"name": "TARC reduction", "category": "biomarker", "result": "-74%", "timepoint": "Day 29"},
                {"name": "Eotaxin-3 reduction", "category": "biomarker", "result": "-73%", "timepoint": "Day 29"},
                {"name": "IL-31 reduction", "category": "biomarker", "result": "-54%", "timepoint": "Day 29"},
                {"name": "FeNO reduction (comorbid asthma, n=4)", "category": "biomarker", "result": "-56%", "timepoint": "Day 29"},
                {"name": "ACQ-5 responders (comorbid asthma)", "category": "secondary", "result": "100% (4/4)", "timepoint": "Day 29"}
            ],
            "safety": "Well-tolerated; no SAEs; no severe AEs; no dose-dependent TEAEs; no conjunctivitis",
            "vs_dupilumab": "Results in line with or numerically exceeded published Dupilumab data at Week 4"
        },
        {
            "name": "BROADEN2 Phase 2b in Atopic Dermatitis",
            "phase": "Phase 2b",
            "status": "Ongoing",
            "indication": "Moderate-to-severe Atopic Dermatitis",
            "design": "Randomized, double-blind, placebo-controlled, dose-ranging",
            "population": "Adult & adolescent (12-75) moderate-to-severe AD",
            "n_target": 200,
            "arms": [
                {"name": "Placebo"},
                {"name": "KT-621 Dose 1"},
                {"name": "KT-621 Dose 2"},
                {"name": "KT-621 Dose 3"}
            ],
            "primary_endpoint": "Percent change from baseline in EASI score at Week 16",
            "secondary_endpoints": ["EASI-50", "EASI-75", "vIGA-AD 0/1", "Peak Pruritus NRS ≥4-point improvement"],
            "duration": "16 weeks + 52-week open label extension",
            "data_expected": "Mid-2027"
        },
        {
            "name": "BREADTH Phase 2b in Asthma",
            "phase": "Phase 2b",
            "status": "Initiated January 2026",
            "indication": "Moderate-to-severe Eosinophilic Asthma",
            "design": "Randomized, double-blind, placebo-controlled, dose-ranging",
            "population": "Adult moderate-to-severe eosinophilic asthma (EOS≥300, FeNO≥25ppb, FEV1 40-80%)",
            "n_target": 264,
            "arms": [
                {"name": "Placebo"},
                {"name": "KT-621 Dose 1"},
                {"name": "KT-621 Dose 2"},
                {"name": "KT-621 Dose 3"}
            ],
            "primary_endpoint": "Percent change from baseline in pre-bronchodilator FEV1 at Week 12",
            "secondary_endpoints": ["ACQ-5 change", "AQLQ change"],
            "duration": "12 weeks",
            "data_expected": "Late-2027"
        }
    ],
    "graph_analyses": {
        "phase1_biomarker": {
            "title": "STAT6 Degradation in Blood and Skin",
            "key_findings": [
                "Clear sigmoid dose-response: minimal at 1.5mg, steep 12.5-25mg, plateau ≥25mg",
                ">90% STAT6 degradation in both blood AND skin at doses ≥25mg",
                "Skin penetration confirmed - critical for dermatological indications",
                "TARC/Eotaxin-3 reductions suggest on-target Type 2 pathway blockade"
            ],
            "clinical_significance": "Deep target tissue engagement at well-tolerated oral doses supports Dupixent-like potential"
        },
        "phase1b_efficacy": {
            "title": "EASI and SCORAD Response Over Time",
            "key_findings": [
                "Rapid onset: significant EASI improvement by Day 8",
                "Progressive improvement without plateau at Day 29",
                "63% EASI reduction comparable to Dupixent at similar timepoint",
                "100mg and 200mg show similar efficacy - 100mg likely optimal dose",
                "Strong itch reduction (PPNRS -40%) indicates symptomatic relief"
            ],
            "clinical_significance": "Open-label data directionally supports Dupixent-like efficacy; Phase 2b will confirm with placebo control"
        }
    },
    "investment_thesis": [
        "First oral STAT6 degrader - potential to replace/complement Dupixent ($13B+ blockbuster)",
        "Phase 1b AD: 63% EASI reduction at Day 29 matches/exceeds Dupixent at Week 4",
        "Oral convenience advantage over Dupixent (injection every 2 weeks)",
        "Broad indication potential: AD, asthma, COPD, EoE, CRSwNP, CSU, PN, BP",
        "Market opportunity: >140M patients, <1% on advanced therapy, >$20B by 2030",
        "Deep target engagement: >90% STAT6 degradation in blood AND skin",
        "Favorable safety: no conjunctivitis (common Dupixent AE), no SAEs"
    ],
    "key_risks": [
        "Phase 1b was open-label - need placebo-controlled Phase 2b to confirm efficacy",
        "Only 29 days treatment - need 16-week data for proper Dupixent comparison",
        "Small sample sizes (n=22 in Phase 1b)",
        "Competitive landscape: Dupixent entrenched, other IL-4/IL-13 drugs in development",
        "Degrader class relatively new - long-term safety profile still being established"
    ],
    "upcoming_catalysts": [
        {"event": "BROADEN2 Phase 2b AD data", "timing": "Mid-2027"},
        {"event": "BREADTH Phase 2b Asthma data", "timing": "Late-2027"},
        {"event": "Phase 3 dose selection", "timing": "2027"}
    ]
}


# =============================================================================
# KT-579 (IRF5 DEGRADER)
# =============================================================================

KT579_DATA = {
    "asset": {
        "name": "KT-579",
        "company": "Kymera Therapeutics",
        "ticker": "KYMR",
        "target": "IRF5",
        "target_full_name": "Interferon Regulatory Factor 5",
        "mechanism": "IRF5 degrader (targeted protein degradation)",
        "modality": "Oral small molecule degrader",
        "pathway": "Toll-like receptor / MyD88 signaling",
        "first_in_class": True
    },
    "clinical_development": {
        "current_stage": "Phase 1",
        "indications_in_development": [
            "Systemic Lupus Erythematosus (SLE)",
            "Sjögren's Syndrome",
            "Rheumatoid Arthritis (RA)",
            "Inflammatory Bowel Disease (IBD)",
            "Systemic Sclerosis (SSc)",
            "Dermatomyositis (DM)"
        ],
        "market_opportunity": ">10M patients; systemic advanced therapies reach only 7%; >$45B market (SLE, LN, RA, IBD alone)"
    },
    "target_biology": {
        "description": """IRF5 is a genetically validated transcription factor and master regulator of immunity. 
It regulates pro-inflammatory cytokines, Type I IFN production, and autoantibody production in a 
cell and activation-specific manner.""",
        "genetic_validation": [
            "IRF5 functional risk variants associate with increased susceptibility to SLE, Sjögren's, RA, IBD, SSc",
            "IRF5 risk haplotypes in SLE patients associated with high serum IFNα, anti-dsDNA antibodies",
            "IRF5 KO mice are viable, fertile, with normal B cell development",
            "IRF5 KO protects against disease in models of SLE, SSc, RA, IBD"
        ],
        "pathway_validation": "IRF5-regulated pathways clinically validated by anti-IFN, anti-TNF, IL-6, IL-12, IL-23 antibodies, B cell targeting agents",
        "degrader_advantage": "Conventional approaches failed due to multiple activation steps and IRF family homology; TPD allows single binding event to deplete protein"
    },
    "preclinical_data": {
        "potency": {
            "description": "Exquisitely selective, picomolar IRF5 degrader",
            "dc50_pbmc": "0.8 nM",
            "dc50_b_cells": "1.0 nM",
            "dc50_monocytes": "0.6 nM",
            "dc50_pDCs": "0.9 nM",
            "dc50_mDCs": "0.9 nM",
            "selectivity": "No binding to IRF3, 4, 6, 7, 8 (Kd >10,000 nM); no degradation of IRF3/IRF7"
        },
        "functional_activity": {
            "type1_ifn_inhibition": "DC50 0.3-0.8 nM (IFNβ production via TLR7/8/9)",
            "proinflammatory_cytokines": "DC50 0.15-1.8 nM (TNFα, IL-12p40, IL-1β, IL-23)",
            "igg_reduction": "Reduces TLR9-induced IgG production in SLE-derived B cells"
        },
        "in_vivo_efficacy": {
            "mrl_lpr_lupus": {
                "description": "MRL/lpr spontaneous lupus mouse model - 63 days dosing",
                "survival": "100% (15/15) vs 67% vehicle - superior to all comparators",
                "anti_dsDNA": "Sustained reduction in serum anti-dsDNA antibodies",
                "plasmablasts": "Significant reduction in splenic plasmablasts",
                "kidney": "Reduced IgG/C3 glomerular staining; reduced total kidney lesion score",
                "vs_comparators": "Superior to Afimetoran, Deucravacitinib, Cyclophosphamide, anti-IFNAR"
            },
            "nzbw_lupus": {
                "description": "NZB.W1 spontaneous lupus mouse model - 107 days dosing",
                "proteinuria": "Decreased proteinuria",
                "anti_dsDNA": "Near complete reduction in anti-dsDNA antibodies - superior to SOC",
                "ifn_genes": "Significantly reduced OAS1, IFIT1, IF44 (interferon signature genes)"
            },
            "aia_ra": {
                "description": "Antigen-Induced Arthritis (AIA) mouse model of RA",
                "joint_swelling": "Significant reduction comparable to Tofacitinib",
                "il12p40": "Reduced circulating IL-12p40",
                "th1_cells": "Reduced synovial infiltrating IFNγ+ Th1 cells"
            }
        },
        "safety": {
            "nhp_degradation": "82-97% IRF5 degradation in NHP blood after 7 days oral QD dosing (1-30 mg/kg)",
            "toxicology": "No adverse effects at up to 200-fold predicted human efficacious exposure in NHP and rodent studies"
        }
    },
    "trials": [
        {
            "name": "KT-579 Phase 1 Healthy Volunteer Study",
            "phase": "Phase 1",
            "status": "Starting Q1 2026",
            "indication": "Healthy Volunteers",
            "design": "SAD/MAD, randomized, placebo-controlled",
            "primary_endpoint": "Safety, tolerability, PK",
            "secondary_endpoints": ["IRF5 degradation in blood", "Cytokine inhibition"],
            "data_expected": "2H 2026"
        }
    ],
    "investment_thesis": [
        "First-in-class oral IRF5 degrader - no existing drugs target this validated transcription factor",
        "Strong genetic validation: IRF5 risk variants linked to SLE, Sjögren's, RA, IBD, SSc",
        "Preclinical efficacy superior to approved/clinical-stage drugs in lupus and RA models",
        "Broad mechanism: blocks Type I IFN, pro-inflammatory cytokines, AND autoantibodies",
        "Potential for disease modification vs symptom control",
        "Large market opportunity: >$45B across SLE, RA, IBD",
        "Excellent preclinical safety at 200x human efficacious exposure"
    ],
    "key_risks": [
        "No human clinical data yet - Phase 1 starting Q1 2026",
        "IRF5 biology complex - effects may differ in humans vs preclinical models",
        "Autoimmune diseases notoriously difficult - many failures in SLE",
        "Will need to show differentiation vs existing JAK inhibitors, anti-IFN antibodies",
        "Long development timelines in autoimmune indications"
    ],
    "upcoming_catalysts": [
        {"event": "Phase 1 HV study initiation", "timing": "Q1 2026"},
        {"event": "Phase 1 HV data (safety, PK, IRF5 degradation)", "timing": "2H 2026"},
        {"event": "Patient study initiation (likely SLE)", "timing": "2027"}
    ]
}


# =============================================================================
# KT-485 (IRAK4 DEGRADER) - PARTNERED WITH SANOFI
# =============================================================================

KT485_DATA = {
    "asset": {
        "name": "KT-485",
        "alternate_names": ["SAR447971"],
        "company": "Kymera Therapeutics",
        "partner": "Sanofi",
        "ticker": "KYMR",
        "target": "IRAK4",
        "target_full_name": "Interleukin-1 Receptor Associated Kinase 4",
        "mechanism": "IRAK4 degrader (targeted protein degradation)",
        "modality": "Oral small molecule degrader",
        "pathway": "IL-1R/TLR/MyD88 signaling",
        "generation": "Second-generation (improved over KT-474)"
    },
    "clinical_development": {
        "current_stage": "IND-Enabling (Phase 1 expected 2026)",
        "indications_in_development": [
            "Hidradenitis Suppurativa (HS)",
            "Atopic Dermatitis (AD)",
            "Rheumatoid Arthritis (RA)",
            "Asthma",
            "Inflammatory Bowel Disease (IBD)"
        ],
        "market_opportunity": ">140M patients; systemic advanced therapies reach only 3%; >$55B market opportunity"
    },
    "target_biology": {
        "description": """IRAK4 is a master regulator of innate immunity with both scaffolding and kinase functions.
It is an obligate node in IL-1R/TLR signaling. IRAK4 degradation is the only approach to fully block the pathway.""",
        "genetic_validation": "Adult humans with IRAK4 null mutation are healthy",
        "pathway_validation": [
            "IL-1α/IL-1β validated in RA, CAPS, HS, AD, RP, Gout",
            "IL-18 validated in AD, Macrophage Activation Syndrome",
            "IL-36 validated in Generalized Pustular Psoriasis",
            "IL-33 validated in Asthma, COPD",
            "IRAK4 SMI showed activity in RA"
        ],
        "degrader_advantage": "Degradation eliminates both scaffolding AND kinase functions - more complete pathway blockade than kinase inhibitors"
    },
    "differentiation_vs_kt474": {
        "description": "KT-485 is a second-generation IRAK4 degrader with improvements over KT-474",
        "improvements": [
            "Increased selectivity",
            "Increased potency", 
            "Absence of any QTc signal (cardiac safety improvement)",
            "Prioritized by Sanofi for clinical development over KT-474"
        ]
    },
    "partnership": {
        "partner": "Sanofi",
        "structure": "Sanofi to advance KT-485 into Phase 1 and subsequent development",
        "economics": "Kymera receives milestones and royalties",
        "status": "Sanofi expected to initiate Phase 1 in 2026",
        "learnings": "Clinical learnings from KT-474 studies will accelerate KT-485 development"
    },
    "trials": [
        {
            "name": "KT-485 Phase 1 Study",
            "phase": "Phase 1",
            "status": "Expected to initiate 2026",
            "sponsor": "Sanofi",
            "indication": "TBD (likely HS or AD based on KT-474 experience)",
            "notes": "Sanofi leading development; Kymera provides support"
        }
    ],
    "investment_thesis": [
        "Second-generation IRAK4 degrader with improved profile over KT-474",
        "Partnered with Sanofi - validates platform and provides development capital",
        "Potential combined activity of multiple upstream biologics (anti-IL-1/18/33/36) in oral pill",
        "KT-474 clinical learnings de-risk KT-485 development",
        "No QTc signal - addresses key safety concern for IRAK4 inhibitors",
        "Large market: >140M patients across HS, AD, RA, asthma, IBD",
        "IRAK4 null humans are healthy - genetic validation for safety"
    ],
    "key_risks": [
        "Dependent on Sanofi for clinical development execution",
        "KT-474 development discontinued in favor of KT-485 - limited human data",
        "IRAK4 degradation is novel mechanism - clinical validation needed",
        "Competitive landscape includes JAK inhibitors, IL-1/IL-36 antibodies",
        "HS is a difficult indication with high placebo response"
    ],
    "upcoming_catalysts": [
        {"event": "Sanofi Phase 1 initiation", "timing": "2026"},
        {"event": "Phase 1 safety/PK data", "timing": "2027"}
    ]
}


# =============================================================================
# STAT6, IRF5, IRAK4 TARGET DATA
# =============================================================================

STAT6_TARGET = {
    "name": "STAT6",
    "full_name": "Signal Transducer and Activator of Transcription 6",
    "aliases": ["STAT-6"],
    "type": "Transcription Factor",
    "pathway": "IL-4/IL-13 signaling → Type 2 inflammation",
    "therapeutic_areas": ["Immunology", "Dermatology", "Respiratory", "GI"],
    "validation": {
        "genetic": "STAT6 GoF and heterozygous LoF alleles validate role in Type 2 inflammation",
        "clinical": "IL-4/IL-13 pathway validated by Dupixent across AD, asthma, COPD, EoE, CRSwNP, CSU, PN, BP"
    },
    "why_undrugged": "Transcription factors historically undruggable by traditional small molecules; no oral drugs selectively target this pathway",
    "companies_developing": [
        {"company": "Kymera Therapeutics", "asset": "KT-621", "stage": "Phase 2b", "mechanism": "Degrader"}
    ],
    "approved_pathway_drugs": [
        {"name": "Dupixent (dupilumab)", "company": "Regeneron/Sanofi", "mechanism": "IL-4Rα antibody", "sales": "$13B+"}
    ]
}

IRF5_TARGET = {
    "name": "IRF5",
    "full_name": "Interferon Regulatory Factor 5",
    "aliases": ["IRF-5"],
    "type": "Transcription Factor",
    "pathway": "TLR/MyD88 → Type I IFN + pro-inflammatory cytokines",
    "therapeutic_areas": ["Immunology", "Rheumatology", "GI", "Autoimmune"],
    "validation": {
        "genetic": "GWAS identifies IRF5 as autoimmune susceptibility gene for SLE, Sjögren's, RA, IBD, SSc",
        "clinical": "IRF5-regulated pathways validated by anti-IFN, anti-TNF, IL-6, IL-12/23 antibodies"
    },
    "why_undrugged": "Multiple activation steps and IRF family member homology make selective inhibition impossible; degradation is only approach",
    "companies_developing": [
        {"company": "Kymera Therapeutics", "asset": "KT-579", "stage": "Phase 1", "mechanism": "Degrader", "first_in_class": True}
    ],
    "approved_pathway_drugs": [
        {"name": "Anifrolumab (Saphnelo)", "company": "AstraZeneca", "mechanism": "Anti-IFNAR", "indication": "SLE"},
        {"name": "Various anti-TNF/IL-6/IL-12/23", "mechanism": "Cytokine antibodies", "indication": "RA, IBD, Psoriasis"}
    ]
}

IRAK4_TARGET = {
    "name": "IRAK4",
    "full_name": "Interleukin-1 Receptor Associated Kinase 4",
    "aliases": ["IRAK-4"],
    "type": "Scaffolding Kinase",
    "pathway": "IL-1R/TLR/MyD88 → Myddosome → NF-κB → inflammation",
    "therapeutic_areas": ["Immunology", "Dermatology", "Rheumatology", "Respiratory"],
    "validation": {
        "genetic": "IRAK4 null humans are healthy - validates safety of complete inhibition",
        "clinical": "IL-1/IL-18/IL-33/IL-36 pathways validated across RA, HS, AD, asthma, COPD, GPP"
    },
    "why_degrader_better": "Kinase inhibitors only block catalytic function; degraders eliminate scaffolding function too for complete pathway blockade",
    "companies_developing": [
        {"company": "Kymera/Sanofi", "asset": "KT-485", "stage": "Phase 1 (2026)", "mechanism": "Degrader"},
        {"company": "Kymera/Sanofi", "asset": "KT-474", "stage": "Phase 2 (discontinued)", "mechanism": "Degrader"}
    ]
}


# =============================================================================
# HELPER FUNCTION TO GET ALL DATA
# =============================================================================

def get_kymera_full_pipeline():
    """Return complete Kymera pipeline data for integration."""
    return {
        "company": KYMERA_COMPANY,
        "assets": {
            "KT-621": KT621_DATA,
            "KT-579": KT579_DATA,
            "KT-485": KT485_DATA
        },
        "targets": {
            "STAT6": STAT6_TARGET,
            "IRF5": IRF5_TARGET,
            "IRAK4": IRAK4_TARGET
        }
    }


def get_asset_clinical_data(asset_name: str) -> dict:
    """Get clinical data for a specific asset."""
    assets = {
        "KT-621": KT621_DATA,
        "KT-579": KT579_DATA,
        "KT-485": KT485_DATA
    }
    return assets.get(asset_name.upper(), None)


def get_target_landscape(target_name: str) -> dict:
    """Get target landscape data."""
    targets = {
        "STAT6": STAT6_TARGET,
        "IRF5": IRF5_TARGET,
        "IRAK4": IRAK4_TARGET
    }
    return targets.get(target_name.upper(), None)


if __name__ == "__main__":
    import json
    
    # Print summary
    pipeline = get_kymera_full_pipeline()
    
    print("=" * 60)
    print("KYMERA THERAPEUTICS PIPELINE SUMMARY")
    print("=" * 60)
    
    for asset_name, asset_data in pipeline["assets"].items():
        asset_info = asset_data["asset"]
        dev_info = asset_data["clinical_development"]
        print(f"\n{asset_name} ({asset_info['target']} {asset_info['mechanism'].split('(')[0].strip()})")
        print(f"  Stage: {dev_info['current_stage']}")
        print(f"  Indications: {', '.join(dev_info['indications_in_development'][:3])}...")
    
    print("\n" + "=" * 60)
    print("Targets:")
    for target_name, target_data in pipeline["targets"].items():
        print(f"  {target_name}: {target_data['full_name']}")
