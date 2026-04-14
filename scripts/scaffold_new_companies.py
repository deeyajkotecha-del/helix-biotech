#!/usr/bin/env python3
"""
Scaffold new company data directories for Helix Biotech.

Creates company.json files with real company information for each ticker,
sets up the directory structure, and updates the index and IR mapping.
"""

import json
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data" / "companies"

# ============================================================================
# Company definitions — real data for each new ticker
# ============================================================================

NEW_COMPANIES = {
    "AUTL": {
        "name": "Autolus Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "London, UK",
        "website": "https://www.autolus.com",
        "ir_url": "https://ir.autolus.com",
        "presentations_url": "https://ir.autolus.com/events-and-presentations",
        "sec_filings": "https://ir.autolus.com/sec-filings",
        "one_liner": "Next-gen CAR-T cell therapy company with obe-cel (Aucatzyl) approved for r/r adult ALL",
        "description": "Autolus is a clinical-stage biopharmaceutical company developing next-generation programmed T cell therapies. Lead program obe-cel (Aucatzyl) received FDA approval for relapsed/refractory adult B-cell ALL in November 2024, becoming one of few CAR-T therapies with a manageable safety profile enabling outpatient administration.",
        "core_thesis": "Autolus is commercializing obe-cel (Aucatzyl), a differentiated CAR-T with best-in-class CRS/ICANS safety in adult ALL, and expanding into autoimmune diseases with a next-gen platform that could unlock a massive new market for cell therapy.",
        "key_value_drivers": [
            "Aucatzyl approved for adult ALL — only CAR-T with low-grade CRS enabling outpatient dosing",
            "Autoimmune expansion: AUTO1/22 dual-targeting CD19/BCMA in lupus and other autoimmune diseases",
            "Platform generates next-gen constructs with enhanced persistence and reduced toxicity",
            "Commercial ramp in ALL with potential to capture significant share from Tecartus"
        ],
        "pipeline": [
            {"asset": "Obe-cel (Aucatzyl)", "target": "CD19", "stage": "Approved/Commercial", "indications": "Adult ALL", "ownership": "Wholly-owned", "next_catalyst": "Commercial launch ramp + label expansion"},
            {"asset": "AUTO1/22", "target": "CD19/BCMA", "stage": "Phase 1", "indications": "Lupus, autoimmune", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data 2026"},
            {"asset": "AUTO6NG", "target": "GD2", "stage": "Phase 1", "indications": "Neuroblastoma", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data"}
        ],
        "modality": "cell_therapy",
        "therapeutic_area": "oncology_autoimmune",
        "market_cap_mm": "$2B",
        "priority": "high"
    },

    "ANNX": {
        "name": "Annexon Biosciences",
        "exchange": "NASDAQ",
        "headquarters": "South San Francisco, CA",
        "website": "https://www.annexonbio.com",
        "ir_url": "https://ir.annexonbio.com",
        "presentations_url": "https://ir.annexonbio.com/events-and-presentations",
        "sec_filings": "https://ir.annexonbio.com/sec-filings",
        "one_liner": "Complement C1q inhibitor targeting geographic atrophy and autoimmune diseases",
        "description": "Annexon Biosciences is developing ANX007, a monoclonal antibody that inhibits C1q, the initiating molecule of the classical complement pathway. Lead program is in geographic atrophy (GA) secondary to AMD, with differentiated data showing structural preservation beyond lesion growth reduction.",
        "core_thesis": "Annexon's ANX007 targets C1q upstream of existing complement therapies, potentially offering superior efficacy in geographic atrophy by preserving photoreceptors and RPE structure — not just slowing lesion growth — in a $5B+ market dominated by Apellis and Astellas.",
        "key_value_drivers": [
            "ANX007: Phase 3 ARCHER in GA — differentiated endpoint of structural preservation",
            "C1q inhibition works upstream of C3/C5, potentially more complete pathway blockade",
            "Phase 2 data showed photoreceptor preservation + lesion growth reduction",
            "Warm autoimmune hemolytic anemia (wAIHA) Phase 2 expansion"
        ],
        "pipeline": [
            {"asset": "ANX007", "target": "C1q", "stage": "Phase 3", "indications": "Geographic atrophy", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 ARCHER interim data"},
            {"asset": "ANX007", "target": "C1q", "stage": "Phase 2", "indications": "wAIHA", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 data"},
            {"asset": "ANX005", "target": "C1q (IV)", "stage": "Phase 2", "indications": "GBS, CIDP", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 GBS data"}
        ],
        "modality": "antibody",
        "therapeutic_area": "ophthalmology_autoimmune",
        "market_cap_mm": "$1.5B",
        "priority": "high"
    },

    "PRAX": {
        "name": "Praxis Precision Medicine",
        "exchange": "NASDAQ",
        "headquarters": "Cambridge, MA",
        "website": "https://www.praxismedicines.com",
        "ir_url": "https://ir.praxismedicines.com",
        "presentations_url": "https://ir.praxismedicines.com/events-and-presentations",
        "sec_filings": "https://ir.praxismedicines.com/sec-filings",
        "one_liner": "Developing T-type calcium channel modulators for essential tremor and epilepsy",
        "description": "Praxis Precision Medicine is a neuroscience company developing therapies for neurological disorders. Lead asset ulixacaltamide (PRAX-944) is a selective T-type calcium channel modulator in Phase 2/3 for essential tremor with pivotal data expected, and expanded into focal epilepsy.",
        "core_thesis": "Praxis is developing ulixacaltamide, a first-in-class T-type calcium channel blocker for essential tremor — a massive underserved market with 7M+ US patients and no new drug class in decades. Phase 2b TEMPO data showed significant tremor reduction vs placebo.",
        "key_value_drivers": [
            "Ulixacaltamide (PRAX-944): Phase 2/3 pivotal in essential tremor, 7M+ patient market",
            "Phase 2b TEMPO showed statistically significant tremor reduction",
            "First new mechanism for ET since propranolol — blockbuster potential if Phase 3 succeeds",
            "PRAX-562: NaV1.2 activator for SCN2A-related epilepsy (genetic precision approach)"
        ],
        "pipeline": [
            {"asset": "Ulixacaltamide (PRAX-944)", "target": "T-type calcium channel", "stage": "Phase 2/3", "indications": "Essential tremor", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 TEMPO-3 data 2026"},
            {"asset": "PRAX-944", "target": "T-type calcium channel", "stage": "Phase 2", "indications": "Focal epilepsy", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 data"},
            {"asset": "PRAX-562", "target": "NaV1.2", "stage": "Phase 1", "indications": "SCN2A epilepsy", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data"}
        ],
        "modality": "small_molecule",
        "therapeutic_area": "neuroscience",
        "market_cap_mm": "$3B",
        "priority": "high"
    },

    "CLDX": {
        "name": "Celldex Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "Hampton, NJ",
        "website": "https://www.celldex.com",
        "ir_url": "https://ir.celldex.com",
        "presentations_url": "https://ir.celldex.com/events-and-presentations",
        "sec_filings": "https://ir.celldex.com/sec-filings",
        "one_liner": "Bispecific antibodies targeting mast cell-driven diseases including chronic urticaria",
        "description": "Celldex Therapeutics is developing barzolvolimab, a KIT-targeting antibody that depletes mast cells. Breakthrough Phase 2 data in chronic spontaneous urticaria (CSU) showed near-complete resolution of hives and itch in patients refractory to standard therapy.",
        "core_thesis": "Celldex's barzolvolimab is the most compelling new mechanism in chronic urticaria since omalizumab (Xolair), with Phase 2 data showing unprecedented complete response rates in CSU. If Phase 3 confirms, this is a multi-billion dollar asset in a $5B+ market.",
        "key_value_drivers": [
            "Barzolvolimab: Anti-KIT mast cell depleter with complete response rates >50% in CSU Phase 2",
            "Phase 3 CELESTE-1 and CELESTE-2 in CSU enrolling — pivotal data expected 2026-2027",
            "Mast cell depletion approach: potential beyond CSU into CIndU, prurigo nodularis, mastocytosis",
            "Xolair patent cliff + incomplete efficacy creates a massive switching opportunity"
        ],
        "pipeline": [
            {"asset": "Barzolvolimab", "target": "KIT", "stage": "Phase 3", "indications": "Chronic spontaneous urticaria", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 CELESTE data 2026-2027"},
            {"asset": "Barzolvolimab", "target": "KIT", "stage": "Phase 2", "indications": "CIndU, prurigo nodularis", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 expansion data"},
            {"asset": "CDX-527", "target": "PD-L1 x CD27", "stage": "Phase 1", "indications": "Solid tumors", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data"}
        ],
        "modality": "antibody",
        "therapeutic_area": "immunology_dermatology",
        "market_cap_mm": "$4B",
        "priority": "high"
    },

    "AXSM": {
        "name": "Axsome Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "New York, NY",
        "website": "https://www.axsome.com",
        "ir_url": "https://ir.axsome.com",
        "presentations_url": "https://ir.axsome.com/events-and-presentations",
        "sec_filings": "https://ir.axsome.com/sec-filings",
        "one_liner": "Commercial-stage CNS company with Auvelity (MDD) and pipeline across migraine, narcolepsy, Alzheimer's agitation",
        "description": "Axsome Therapeutics is a commercial-stage biopharmaceutical company focused on CNS disorders. Lead product Auvelity (dextromethorphan-bupropion) is approved for MDD with a rapid-onset mechanism. Pipeline includes AXS-07 (migraine), AXS-12 (narcolepsy), and AXS-05 for Alzheimer's agitation.",
        "core_thesis": "Axsome is building a CNS franchise around Auvelity's commercial ramp in MDD — the only rapid-acting oral antidepressant — while advancing a pipeline that could deliver multiple additional products in migraine, narcolepsy, and Alzheimer's agitation, each addressing massive underserved markets.",
        "key_value_drivers": [
            "Auvelity: Rapid-onset oral antidepressant, only NMDA modulator approved for MDD — commercial ramp accelerating",
            "AXS-07 (MoSEIC): NDA under review for acute migraine, differentiated oral formulation",
            "AXS-05: Phase 3 in Alzheimer's agitation — a market with no approved oral therapy",
            "AXS-12 (reboxetine): Phase 3 for narcolepsy, potential best-in-class wake-promoting agent"
        ],
        "pipeline": [
            {"asset": "Auvelity", "target": "NMDA/sigma-1", "stage": "Approved/Commercial", "indications": "MDD", "ownership": "Wholly-owned", "next_catalyst": "Commercial ramp + line extensions"},
            {"asset": "AXS-07 (MoSEIC)", "target": "CGRP/5-HT", "stage": "NDA Filed", "indications": "Acute migraine", "ownership": "Wholly-owned", "next_catalyst": "FDA decision"},
            {"asset": "AXS-05", "target": "NMDA/sigma-1", "stage": "Phase 3", "indications": "Alzheimer's agitation", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 data"},
            {"asset": "AXS-12 (reboxetine)", "target": "NRI", "stage": "Phase 3", "indications": "Narcolepsy", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 data"}
        ],
        "modality": "small_molecule",
        "therapeutic_area": "neuroscience",
        "market_cap_mm": "$5B",
        "priority": "high"
    },

    "DYN": {
        "name": "Dyne Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "Waltham, MA",
        "website": "https://www.dfrx.com",
        "ir_url": "https://ir.dfrx.com",
        "presentations_url": "https://ir.dfrx.com/events-and-presentations",
        "sec_filings": "https://ir.dfrx.com/sec-filings",
        "one_liner": "FORCE platform delivering oligonucleotide therapies to muscle — lead programs in DM1 and Duchenne",
        "description": "Dyne Therapeutics is developing muscle-targeted RNA therapeutics using its FORCE (Fab-Oligonucleotide Conjugate for Effective delivery) platform. The platform conjugates antibody fragments to oligonucleotides for enhanced muscle delivery. Lead programs target myotonic dystrophy type 1 (DM1) and Duchenne muscular dystrophy (DMD).",
        "core_thesis": "Dyne's FORCE platform solves the oligonucleotide muscle delivery problem that has limited prior RNA therapies. If DYNE-101 confirms Phase 1/2 splicing correction and functional improvement in DM1, this platform could dominate muscle genetic diseases — a space with minimal competition and high unmet need.",
        "key_value_drivers": [
            "DYNE-101: FORCE-conjugated antisense for DM1 — Phase 1/2 showing meaningful splicing correction",
            "DYNE-251: FORCE-conjugated exon-skipping for DMD — competing with Sarepta's gene therapy approach",
            "FORCE platform: antibody-oligonucleotide conjugates achieve 10-30x greater muscle exposure than naked oligos",
            "Large rare disease markets: DM1 (~80K US patients), DMD (~15K US) with few effective treatments"
        ],
        "pipeline": [
            {"asset": "DYNE-101", "target": "DMPK (antisense)", "stage": "Phase 1/2", "indications": "Myotonic dystrophy type 1", "ownership": "Wholly-owned", "next_catalyst": "Phase 1/2 updated data 2026"},
            {"asset": "DYNE-251", "target": "Dystrophin exon 51", "stage": "Phase 1/2", "indications": "Duchenne muscular dystrophy", "ownership": "Wholly-owned", "next_catalyst": "Phase 1/2 data 2026"},
            {"asset": "DYNE-302", "target": "DMPK (next-gen)", "stage": "Preclinical", "indications": "DM1", "ownership": "Wholly-owned", "next_catalyst": "IND filing"}
        ],
        "modality": "rna_therapeutics",
        "therapeutic_area": "rare_disease_neuromuscular",
        "market_cap_mm": "$2.5B",
        "priority": "high"
    },

    "MBX": {
        "name": "MBX Biosciences",
        "exchange": "NASDAQ",
        "headquarters": "Carmel, IN",
        "website": "https://www.mbxbio.com",
        "ir_url": "https://ir.mbxbio.com",
        "presentations_url": "https://ir.mbxbio.com/events-and-presentations",
        "sec_filings": "https://ir.mbxbio.com/sec-filings",
        "one_liner": "Precision endocrinology company developing long-acting peptide therapies for hypoparathyroidism and obesity",
        "description": "MBX Biosciences is a precision endocrinology company developing novel peptide therapeutics using its proprietary Precision Endocrine Peptide (PEP) platform. Lead program MBX 2109 is a long-acting PTH prodrug for hypoparathyroidism, with MBX 1416 (GLP-1/glucagon dual agonist) in obesity.",
        "core_thesis": "MBX 2109 is designed to be a best-in-class long-acting PTH replacement for hypoparathyroidism — an underserved endocrine disorder affecting ~200K patients. If Phase 2 data confirms sustained calcium normalization with weekly dosing, MBX could compete directly with Ascendis' TransCon PTH (Yorvipath).",
        "key_value_drivers": [
            "MBX 2109: Weekly PTH prodrug for hypoparathyroidism — competing with Yorvipath (daily dosing)",
            "Phase 2 data showing sustained normalization of serum calcium with convenient weekly dosing",
            "MBX 1416: GLP-1/glucagon dual agonist for obesity with potential for body composition benefits",
            "PEP platform enables extended half-life for endocrine peptides — pipeline expansion potential"
        ],
        "pipeline": [
            {"asset": "MBX 2109", "target": "PTH receptor", "stage": "Phase 2", "indications": "Hypoparathyroidism", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 data 2026"},
            {"asset": "MBX 1416", "target": "GLP-1R/GCGR", "stage": "Phase 1", "indications": "Obesity", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data 2026"}
        ],
        "modality": "peptide",
        "therapeutic_area": "endocrinology_metabolic",
        "market_cap_mm": "$1.5B",
        "priority": "high"
    },

    "RAPT": {
        "name": "RAPT Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "South San Francisco, CA",
        "website": "https://www.rapt.com",
        "ir_url": "https://ir.rapt.com",
        "presentations_url": "https://ir.rapt.com/events-and-presentations",
        "sec_filings": "https://ir.rapt.com/sec-filings",
        "one_liner": "Oral CCR4 antagonist zelnecirnon in Phase 3 for atopic dermatitis — competing in the oral inflammation space",
        "description": "RAPT Therapeutics is developing zelnecirnon (RPT193), an oral CCR4 antagonist for atopic dermatitis and other Type 2 inflammatory diseases. CCR4 is a chemokine receptor critical for Th2 cell migration. Phase 2 data showed significant improvement in EASI scores in moderate-to-severe AD.",
        "core_thesis": "RAPT's zelnecirnon is a differentiated oral small molecule targeting CCR4, a novel mechanism in atopic dermatitis. If Phase 3 confirms Phase 2 efficacy, zelnecirnon could be a convenient oral alternative to injectable biologics in a $15B+ AD market.",
        "key_value_drivers": [
            "Zelnecirnon (RPT193): Phase 3 in moderate-to-severe atopic dermatitis",
            "Novel CCR4 mechanism — blocks Th2 cell trafficking, complementary to existing therapies",
            "Phase 2 data showed dose-dependent EASI-75 improvement vs placebo",
            "Oral dosing advantage over injectable Dupixent/Adbry in a massive market"
        ],
        "pipeline": [
            {"asset": "Zelnecirnon (RPT193)", "target": "CCR4", "stage": "Phase 3", "indications": "Atopic dermatitis", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 data 2026-2027"},
            {"asset": "RPT193", "target": "CCR4", "stage": "Phase 2", "indications": "Asthma, EoE", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 expansion data"}
        ],
        "modality": "small_molecule",
        "therapeutic_area": "immunology_dermatology",
        "market_cap_mm": "$2B",
        "priority": "high"
    },

    "AGIO": {
        "name": "Agios Pharmaceuticals",
        "exchange": "NASDAQ",
        "headquarters": "Cambridge, MA",
        "website": "https://www.agios.com",
        "ir_url": "https://investor.agios.com",
        "presentations_url": "https://investor.agios.com/events-and-presentations",
        "sec_filings": "https://investor.agios.com/sec-filings",
        "one_liner": "Rare genetic disease company with Pyrukynd (mitapivat) approved for pyruvate kinase deficiency and expanding into thalassemia/SCD",
        "description": "Agios Pharmaceuticals is focused on genetically defined diseases. Lead product Pyrukynd (mitapivat) is the first approved oral treatment for pyruvate kinase deficiency. The company is expanding mitapivat into thalassemia and sickle cell disease — massive markets with limited treatment options.",
        "core_thesis": "Agios is expanding Pyrukynd from the niche PKD market into thalassemia and sickle cell disease, where oral PKR activation could reduce transfusion burden and hemolysis. The thalassemia Phase 3 ENERGIZE data is pivotal — success unlocks a multi-billion dollar franchise.",
        "key_value_drivers": [
            "Pyrukynd (mitapivat): Approved for PKD, expanding into thalassemia and SCD",
            "Phase 3 ENERGIZE/ENERGIZE-T in thalassemia — pivotal data expected",
            "Phase 2/3 in sickle cell disease — oral PKR activation could complement gene therapy",
            "Oral mechanism addressing hemolysis at the root cause (PKR activation in red blood cells)"
        ],
        "pipeline": [
            {"asset": "Pyrukynd (mitapivat)", "target": "PKR activator", "stage": "Approved/Commercial", "indications": "Pyruvate kinase deficiency", "ownership": "Wholly-owned", "next_catalyst": "Commercial ramp + label expansion"},
            {"asset": "Mitapivat", "target": "PKR activator", "stage": "Phase 3", "indications": "Thalassemia", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 ENERGIZE data"},
            {"asset": "Mitapivat", "target": "PKR activator", "stage": "Phase 2/3", "indications": "Sickle cell disease", "ownership": "Wholly-owned", "next_catalyst": "Phase 2/3 data"}
        ],
        "modality": "small_molecule",
        "therapeutic_area": "rare_disease_hematology",
        "market_cap_mm": "$3B",
        "priority": "high"
    },

    "IMVT": {
        "name": "Immunovant",
        "exchange": "NASDAQ",
        "headquarters": "New York, NY",
        "website": "https://www.immunovant.com",
        "ir_url": "https://ir.immunovant.com",
        "presentations_url": "https://ir.immunovant.com/events-and-presentations",
        "sec_filings": "https://ir.immunovant.com/sec-filings",
        "one_liner": "Anti-FcRn antibody batoclimab in Phase 3 across multiple autoimmune diseases including MG, TED, and CIDP",
        "description": "Immunovant is developing batoclimab, a subcutaneous anti-FcRn antibody that reduces pathogenic IgG antibodies. The company is running a broad Phase 3 program across myasthenia gravis, thyroid eye disease, CIDP, and warm autoimmune hemolytic anemia. Roivant Sciences is the majority shareholder.",
        "core_thesis": "Immunovant's batoclimab is positioned to be a leading anti-FcRn therapy, competing with argenx's Vyvgart but with subcutaneous convenience and a broader indication strategy. Multiple Phase 3 readouts in 2026-2027 could establish batoclimab as a multi-billion dollar franchise across IgG-mediated autoimmune diseases.",
        "key_value_drivers": [
            "Batoclimab: SC anti-FcRn with Phase 3 programs in MG, TED, CIDP, wAIHA",
            "Competing with argenx Vyvgart but with convenient SC dosing and potential best-in-class IgG reduction",
            "Phase 3 MYALL (MG) data expected — could enable first NDA filing",
            "Roivant backing provides commercial infrastructure and funding through multiple readouts"
        ],
        "pipeline": [
            {"asset": "Batoclimab", "target": "FcRn", "stage": "Phase 3", "indications": "Myasthenia gravis", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 MYALL data 2026"},
            {"asset": "Batoclimab", "target": "FcRn", "stage": "Phase 3", "indications": "Thyroid eye disease", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 data"},
            {"asset": "Batoclimab", "target": "FcRn", "stage": "Phase 3", "indications": "CIDP", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 data"},
            {"asset": "Batoclimab", "target": "FcRn", "stage": "Phase 2/3", "indications": "wAIHA", "ownership": "Wholly-owned", "next_catalyst": "Phase 2/3 data"}
        ],
        "modality": "antibody",
        "therapeutic_area": "autoimmune",
        "market_cap_mm": "$5B",
        "priority": "high"
    },

    "ALKS": {
        "name": "Alkermes",
        "exchange": "NASDAQ",
        "headquarters": "Dublin, Ireland",
        "website": "https://www.alkermes.com",
        "ir_url": "https://investor.alkermes.com",
        "presentations_url": "https://investor.alkermes.com/events-and-presentations",
        "sec_filings": "https://investor.alkermes.com/sec-filings",
        "one_liner": "Profitable CNS/oncology company with Vivitrol, Aristada, Lybalvi, and nemvaleukin in immuno-oncology",
        "description": "Alkermes is a profitable biopharmaceutical company with a commercial CNS franchise (Vivitrol for opioid dependence, Aristada for schizophrenia, Lybalvi for schizophrenia/bipolar) and an oncology pipeline centered on nemvaleukin alfa, an engineered IL-2 variant in development for solid tumors.",
        "core_thesis": "Alkermes is an underappreciated profitable biopharma with a stable CNS franchise generating $1.5B+ revenue and a free optionality play on nemvaleukin in oncology. Lybalvi's rapid commercial uptake in schizophrenia and the potential for nemvaleukin in combination IO regimens offer upside catalysts.",
        "key_value_drivers": [
            "Lybalvi: Rapid commercial ramp in schizophrenia — olanzapine without metabolic side effects",
            "Vivitrol + Aristada: Stable long-acting injectable franchise in addiction and schizophrenia",
            "Profitable and cash-generating — FCF supports buybacks and pipeline investment",
            "Nemvaleukin alfa: Engineered IL-2 in Phase 2/3 for ovarian cancer and melanoma"
        ],
        "pipeline": [
            {"asset": "Lybalvi", "target": "D2/5-HT2A + opioid", "stage": "Approved/Commercial", "indications": "Schizophrenia, bipolar I", "ownership": "Wholly-owned", "next_catalyst": "Commercial ramp"},
            {"asset": "Vivitrol", "target": "Opioid antagonist", "stage": "Approved/Commercial", "indications": "Opioid/alcohol dependence", "ownership": "Wholly-owned", "next_catalyst": "Steady revenue"},
            {"asset": "Nemvaleukin alfa", "target": "IL-2", "stage": "Phase 2/3", "indications": "Ovarian cancer, melanoma", "ownership": "Wholly-owned", "next_catalyst": "Phase 3 data"}
        ],
        "modality": "small_molecule_biologics",
        "therapeutic_area": "cns_oncology",
        "market_cap_mm": "$6B",
        "priority": "high"
    },

    "FOLD": {
        "name": "Amicus Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "Philadelphia, PA",
        "website": "https://www.amicusrx.com",
        "ir_url": "https://ir.amicusrx.com",
        "presentations_url": "https://ir.amicusrx.com/events-and-presentations",
        "sec_filings": "https://ir.amicusrx.com/sec-filings",
        "one_liner": "Rare disease leader with Galafold (Fabry) and Pombiliti+Opfolda (Pompe) — approaching profitability",
        "description": "Amicus Therapeutics is a rare disease biotechnology company with two commercial products: Galafold (migalastat) for Fabry disease and Pombiliti + Opfolda (cipaglucosidase alfa + miglustat) for Pompe disease. The company is approaching profitability with a growing revenue base.",
        "core_thesis": "Amicus is approaching a profitability inflection point with two growing rare disease franchises. Galafold is the only oral therapy for Fabry disease, and Pombiliti+Opfolda offers best-in-class ERT for Pompe. Revenue growth + operating leverage should drive the P&L crossover to sustained profitability.",
        "key_value_drivers": [
            "Galafold: Only oral Fabry disease therapy, growing globally with strong patient retention",
            "Pombiliti+Opfolda: Next-gen ERT for Pompe disease, head-to-head superior to Lumizyme in PROPEL study",
            "Profitability inflection: Company approaching cash flow breakeven with dual revenue streams",
            "Gene therapy pipeline: AT-GAA next-gen and Fabry gene therapy in preclinical"
        ],
        "pipeline": [
            {"asset": "Galafold (migalastat)", "target": "GLA chaperone", "stage": "Approved/Commercial", "indications": "Fabry disease", "ownership": "Wholly-owned", "next_catalyst": "Revenue growth + new markets"},
            {"asset": "Pombiliti + Opfolda", "target": "GAA ERT + chaperone", "stage": "Approved/Commercial", "indications": "Pompe disease", "ownership": "Wholly-owned", "next_catalyst": "Market penetration vs Lumizyme"},
            {"asset": "AT-GAA gene therapy", "target": "GAA gene", "stage": "Preclinical", "indications": "Pompe disease", "ownership": "Wholly-owned", "next_catalyst": "IND filing"}
        ],
        "modality": "small_molecule_biologics",
        "therapeutic_area": "rare_disease",
        "market_cap_mm": "$4B",
        "priority": "high"
    },

    "HRMY": {
        "name": "Harmony Biosciences",
        "exchange": "NASDAQ",
        "headquarters": "Plymouth Meeting, PA",
        "website": "https://www.harmonybiosciences.com",
        "ir_url": "https://ir.harmonybiosciences.com",
        "presentations_url": "https://ir.harmonybiosciences.com/events-and-presentations",
        "sec_filings": "https://ir.harmonybiosciences.com/sec-filings",
        "one_liner": "Commercial-stage sleep medicine company with Wakix (pitolisant) for narcolepsy and expanding into new indications",
        "description": "Harmony Biosciences is a commercial-stage CNS company focused on sleep disorders. Lead product Wakix (pitolisant) is the first and only histamine-3 receptor inverse agonist approved for excessive daytime sleepiness and cataplexy in narcolepsy. The company is expanding Wakix into new indications including idiopathic hypersomnia and Prader-Willi syndrome.",
        "core_thesis": "Harmony is a profitable, growing rare neurology company with Wakix generating $600M+ annual revenue in narcolepsy. Label expansion into idiopathic hypersomnia and Prader-Willi syndrome could significantly expand the addressable market, and the company's strong cash flow supports M&A.",
        "key_value_drivers": [
            "Wakix: $600M+ revenue with continued narcolepsy market penetration",
            "Idiopathic hypersomnia sNDA filed — potential to nearly double addressable market",
            "Prader-Willi syndrome Phase 3 — unmet need with no approved treatments for sleepiness",
            "Highly profitable with strong FCF — well-positioned for BD/M&A"
        ],
        "pipeline": [
            {"asset": "Wakix (pitolisant)", "target": "H3R inverse agonist", "stage": "Approved/Commercial", "indications": "Narcolepsy (EDS + cataplexy)", "ownership": "Licensed (Bioprojet)", "next_catalyst": "Revenue growth"},
            {"asset": "Pitolisant", "target": "H3R inverse agonist", "stage": "sNDA Filed", "indications": "Idiopathic hypersomnia", "ownership": "Licensed", "next_catalyst": "FDA decision"},
            {"asset": "Pitolisant", "target": "H3R inverse agonist", "stage": "Phase 3", "indications": "Prader-Willi syndrome", "ownership": "Licensed", "next_catalyst": "Phase 3 data"}
        ],
        "modality": "small_molecule",
        "therapeutic_area": "neuroscience_sleep",
        "market_cap_mm": "$3.5B",
        "priority": "high"
    },

    "KRYS": {
        "name": "Krystal Biotech",
        "exchange": "NASDAQ",
        "headquarters": "Pittsburgh, PA",
        "website": "https://www.krystalbio.com",
        "ir_url": "https://ir.krystalbio.com",
        "presentations_url": "https://ir.krystalbio.com/events-and-presentations",
        "sec_filings": "https://ir.krystalbio.com/sec-filings",
        "one_liner": "Gene therapy company with Vyjuvek (beremagene geperpavec) approved for dystrophic epidermolysis bullosa, expanding into aesthetics",
        "description": "Krystal Biotech is a gene therapy company using its redosable HSV-1 vector platform. Lead product Vyjuvek is the first FDA-approved gene therapy for dystrophic epidermolysis bullosa (DEB). The company is expanding into cystic fibrosis (inhaled KB407) and aesthetics (KB707 for skin rejuvenation).",
        "core_thesis": "Krystal's redosable HSV-1 vector platform is differentiated — unlike AAV gene therapies, Krystal's approach allows repeat dosing. Vyjuvek is commercializing in DEB with strong uptake, while KB407 (inhaled gene therapy for CF) and the aesthetics pipeline (KB707) offer large-market expansion opportunities.",
        "key_value_drivers": [
            "Vyjuvek: First gene therapy for DEB, commercial ramp with strong early uptake",
            "Redosable HSV-1 platform: No anti-drug antibody barrier to repeat dosing — unique advantage",
            "KB407: Inhaled CFTR gene therapy for cystic fibrosis — addressing all CF mutations, not just specific genotypes",
            "KB707: Aesthetics (skin rejuvenation) — massive market potential if clinical data supports"
        ],
        "pipeline": [
            {"asset": "Vyjuvek", "target": "COL7A1 gene", "stage": "Approved/Commercial", "indications": "Dystrophic EB", "ownership": "Wholly-owned", "next_catalyst": "Revenue ramp + label expansion"},
            {"asset": "KB407", "target": "CFTR gene", "stage": "Phase 1/2", "indications": "Cystic fibrosis", "ownership": "Wholly-owned", "next_catalyst": "Phase 1/2 data 2026"},
            {"asset": "KB707", "target": "COL7A1 (aesthetics)", "stage": "Phase 1", "indications": "Skin rejuvenation", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data"}
        ],
        "modality": "gene_therapy",
        "therapeutic_area": "rare_disease_dermatology",
        "market_cap_mm": "$5B",
        "priority": "high"
    },

    "MPLT": {
        "name": "Maplight Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "San Diego, CA",
        "website": "https://www.maplighttherapeutics.com",
        "ir_url": "https://ir.maplighttherapeutics.com",
        "presentations_url": "https://ir.maplighttherapeutics.com/events-and-presentations",
        "sec_filings": "https://ir.maplighttherapeutics.com/sec-filings",
        "one_liner": "Developing ML-007 (5-HT2A agonist) for neuropsychiatric disorders including schizophrenia and treatment-resistant depression",
        "description": "Maplight Therapeutics is a clinical-stage neuroscience company developing ML-007, a selective 5-HT2A receptor agonist for neuropsychiatric disorders. The approach leverages psychedelic-inspired pharmacology without hallucinogenic effects for potential use in schizophrenia negative symptoms and treatment-resistant depression.",
        "core_thesis": "Maplight is developing next-generation serotonergic therapies that capture the neuroplasticity benefits of psychedelic-class compounds without the hallucinogenic burden. If ML-007 demonstrates efficacy in schizophrenia negative symptoms — an area with zero approved treatments — this would be a transformative first-in-class therapy.",
        "key_value_drivers": [
            "ML-007: Selective 5-HT2A agonist — psychedelic-inspired but non-hallucinogenic",
            "Targeting schizophrenia negative symptoms — no approved treatments exist",
            "Phase 2 readout could validate a new class of serotonergic neuroplastogens",
            "Treatment-resistant depression expansion — large market if mechanism validates"
        ],
        "pipeline": [
            {"asset": "ML-007", "target": "5-HT2A", "stage": "Phase 2", "indications": "Schizophrenia (negative symptoms)", "ownership": "Wholly-owned", "next_catalyst": "Phase 2 data 2026"},
            {"asset": "ML-007", "target": "5-HT2A", "stage": "Phase 1", "indications": "Treatment-resistant depression", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data"}
        ],
        "modality": "small_molecule",
        "therapeutic_area": "neuroscience",
        "market_cap_mm": "$500M",
        "priority": "medium"
    },

    "SLN": {
        "name": "Silence Therapeutics",
        "exchange": "NASDAQ",
        "headquarters": "London, UK",
        "website": "https://www.silence-therapeutics.com",
        "ir_url": "https://ir.silence-therapeutics.com",
        "presentations_url": "https://ir.silence-therapeutics.com/events-and-presentations",
        "sec_filings": "https://ir.silence-therapeutics.com/sec-filings",
        "one_liner": "mRNAi GOLD platform delivering GalNAc-siRNA therapies — lead program zerlasiran for cardiovascular Lp(a) reduction",
        "description": "Silence Therapeutics is developing short interfering RNA (siRNA) therapeutics using its mRNAi GOLD GalNAc conjugate platform. Lead program zerlasiran targets lipoprotein(a) for cardiovascular risk reduction, competing with Novartis' pelacarsen and Amgen's olpasiran in the Lp(a) lowering space.",
        "core_thesis": "Silence's zerlasiran is a GalNAc-siRNA targeting Lp(a) with potential best-in-class dosing convenience (quarterly SC injection). The Lp(a) space is poised to become a blockbuster market if CVOT data confirms Lp(a) lowering reduces cardiovascular events. AstraZeneca's licensing deal validates the platform.",
        "key_value_drivers": [
            "Zerlasiran: GalNAc-siRNA for Lp(a) reduction — quarterly dosing, deep Lp(a) lowering >90%",
            "AstraZeneca partnership: Licensed zerlasiran for up to $4B+ in milestones",
            "Lp(a) market: If CVOTs confirm event reduction, addressable population is 60M+ globally",
            "mRNAi GOLD platform: Pipeline expansion into complement (SLN360), PCSK9, and undisclosed targets"
        ],
        "pipeline": [
            {"asset": "Zerlasiran", "target": "LPA (Lp(a))", "stage": "Phase 3", "indications": "Cardiovascular (Lp(a) lowering)", "ownership": "Partnered (AstraZeneca)", "next_catalyst": "Phase 3 data + AZ-led development"},
            {"asset": "SLN360", "target": "Complement", "stage": "Phase 1", "indications": "Complement-mediated diseases", "ownership": "Wholly-owned", "next_catalyst": "Phase 1 data"},
            {"asset": "Undisclosed", "target": "PCSK9", "stage": "Preclinical", "indications": "Hypercholesterolemia", "ownership": "Wholly-owned", "next_catalyst": "IND filing"}
        ],
        "modality": "rna_therapeutics",
        "therapeutic_area": "cardiovascular",
        "market_cap_mm": "$1B",
        "priority": "high"
    }
}


def create_company_json(ticker: str, info: dict) -> dict:
    """Build a company.json from our info dict, matching the v2.0 schema."""
    return {
        "_metadata": {
            "version": "2.0",
            "ticker": ticker,
            "company_name": info["name"],
            "data_source": "Scaffold — awaiting IR presentation extraction",
            "extraction_date": datetime.now().strftime("%Y-%m-%d")
        },
        "company": {
            "name": info["name"],
            "ticker": ticker,
            "exchange": info["exchange"],
            "headquarters": info["headquarters"],
            "website": info["website"],
            "ir_contact": f"investors@{info['website'].replace('https://www.', '').replace('https://', '')}",
            "one_liner": info["one_liner"],
            "company_description": info["description"]
        },
        "investment_thesis_summary": {
            "core_thesis": info["core_thesis"],
            "key_value_drivers": info["key_value_drivers"]
        },
        "investment_analysis": {
            "bull_case": info["key_value_drivers"][:3],
            "bear_case": ["Awaiting detailed extraction from IR presentations"],
            "key_debates": []
        },
        "pipeline_summary": {
            "total_programs": len(info["pipeline"]),
            "clinical_stage": sum(1 for p in info["pipeline"] if "Phase" in p.get("stage", "") or "Approved" in p.get("stage", "")),
            "programs": info["pipeline"]
        },
        "platform": {
            "name": info.get("modality", ""),
            "description": info["description"][:200]
        },
        "financials": {
            "cash_position": "Awaiting extraction",
            "cash_runway": "Awaiting extraction"
        },
        "market_opportunity": {},
        "competitive_positioning": {},
        "management": {},
        "catalysts_2026": [],
        "catalysts_2027": [],
        "risks": [],
        "sources": []
    }


def create_ir_mapping_entry(ticker: str, info: dict) -> dict:
    """Build an IR website mapping entry."""
    return {
        "name": info["name"],
        "ir_url": info["ir_url"],
        "presentations_url": info["presentations_url"],
        "sec_filings": info["sec_filings"],
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation", "R&D Day"],
        "market_cap": info["market_cap_mm"],
        "priority": "HIGH"
    }


def main():
    created = []
    skipped = []

    for ticker, info in NEW_COMPANIES.items():
        company_dir = DATA_DIR / ticker
        company_file = company_dir / "company.json"

        if company_file.exists():
            print(f"  ⏭  {ticker} — company.json already exists, skipping")
            skipped.append(ticker)
            continue

        # Create directory
        company_dir.mkdir(parents=True, exist_ok=True)

        # Create sources directory
        (company_dir / "sources").mkdir(exist_ok=True)

        # Write company.json
        company_data = create_company_json(ticker, info)
        with open(company_file, 'w') as f:
            json.dump(company_data, f, indent=2)

        # Write sources/index.json
        sources_index = {
            "ticker": ticker,
            "sources": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Scaffold — awaiting IR presentation scraping"
        }
        with open(company_dir / "sources" / "index.json", 'w') as f:
            json.dump(sources_index, f, indent=2)

        created.append(ticker)
        print(f"  ✅ {ticker} ({info['name']}) — created")

    print(f"\n{'='*60}")
    print(f"Created: {len(created)} companies")
    print(f"Skipped: {len(skipped)} (already existed)")
    print(f"Tickers: {', '.join(created)}")

    # Print IR mapping entries for adding to ir_website_mapping.py
    print(f"\n{'='*60}")
    print("IR MAPPING ENTRIES (paste into ir_website_mapping.py):")
    print(f"{'='*60}\n")
    for ticker in created + skipped:
        info = NEW_COMPANIES[ticker]
        entry = create_ir_mapping_entry(ticker, info)
        print(f'    "{ticker}": {json.dumps(entry, indent=8)},\n')


if __name__ == "__main__":
    main()
