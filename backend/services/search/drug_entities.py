"""
SatyaBio — Drug Entity Database

The foundational layer that makes landscape queries work. Creates a normalized
database of drugs with:

  1. Canonical identity — one row per drug with current name
  2. Aliases — every name a drug has ever had (codes, INN, licensed names)
  3. Targets — hierarchical (RAS → KRAS → G12C) with many-to-many drug-target links
  4. Disease-target mapping — links diseases to ALL their relevant targets so
     "AD landscape" shows amyloid, tau, neuroinflammation drugs grouped by approach
  5. Trial links — connects drugs to ClinicalTrials.gov NCT IDs
  6. PubMed search terms — auto-generated from drug biology for landscape queries

WHY THIS MATTERS:
  - RMC-6236 was renamed to daraxonrasib. Both names must resolve to the same drug.
  - A PubMed search for "KRAS inhibitor landscape" needs to find papers about
    sotorasib, adagrasib, AND daraxonrasib even if they don't mention each other.
  - A search for "Alzheimer's landscape" must show drugs grouped by biological
    approach: amyloid-beta, tau, BACE1, neuroinflammation, synaptic, etc.
  - ClinicalTrials.gov lists drugs by intervention name which may differ from
    the company's internal code.
  - When a drug gets licensed (e.g., company A → company B), the name often changes.

USAGE:
    # Create tables + seed initial data
    python3 drug_entities.py --setup

    # Add a single drug
    python3 drug_entities.py --add

    # Look up a drug by any alias
    python3 drug_entities.py --lookup "RMC-6236"
    python3 drug_entities.py --lookup "daraxonrasib"

    # Get the landscape for an indication (all drugs + PubMed search terms)
    python3 drug_entities.py --landscape "NSCLC"
    python3 drug_entities.py --landscape "Alzheimer's"

    # Get drugs by target (walks the hierarchy tree)
    python3 drug_entities.py --target "KRAS"

    # Import from module:
    from drug_entities import lookup_drug, get_landscape, get_pubmed_terms_for_landscape
"""

import os
import sys
import json
import argparse
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

if not DATABASE_URL:
    raise ImportError("NEON_DATABASE_URL not set — drug entity database disabled")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# =============================================================================
# Schema
# =============================================================================

SCHEMA_SQL = """
-- ─────────────────────────────────────────────────────────────────
-- TARGET HIERARCHY
-- A tree structure: RAS → KRAS → KRAS G12C, KRAS G12D, etc.
-- "pan-RAS" drugs link to the RAS node. "G12C-selective" drugs link
-- to the KRAS G12C leaf. Landscape queries walk the tree so
-- "KRAS landscape" finds pan-RAS + pan-KRAS + G12C + G12D + G12V.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS targets (
    target_id       SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,           -- e.g., "KRAS G12C"
    display_name    TEXT NOT NULL,                  -- e.g., "KRAS G12C"
    parent_id       INTEGER REFERENCES targets(target_id),  -- parent in hierarchy
    target_class    TEXT,                           -- gene_family, gene, mutation, isoform, receptor, pathway_node, protein
    gene_symbol     TEXT,                           -- official gene symbol if applicable (e.g., "KRAS")
    description     TEXT,
    keywords        TEXT[] DEFAULT '{}'             -- PubMed search terms for this target
);
CREATE INDEX IF NOT EXISTS idx_targets_parent ON targets (parent_id);
CREATE INDEX IF NOT EXISTS idx_targets_gene ON targets (gene_symbol);

-- Every name / synonym for a target (for lookup)
CREATE TABLE IF NOT EXISTS target_aliases (
    id          SERIAL PRIMARY KEY,
    target_id   INTEGER NOT NULL REFERENCES targets(target_id) ON DELETE CASCADE,
    alias       TEXT NOT NULL,
    UNIQUE(alias)
);
CREATE INDEX IF NOT EXISTS idx_target_aliases_lower ON target_aliases (LOWER(alias));

-- ─────────────────────────────────────────────────────────────────
-- DISEASE → TARGET MAPPING
-- Links diseases to ALL their relevant targets so landscape queries
-- can group drugs by biological approach. E.g., "Alzheimer's" maps
-- to amyloid-beta, tau, BACE1, neuroinflammation, etc.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS disease_targets (
    id              SERIAL PRIMARY KEY,
    disease         TEXT NOT NULL,                  -- e.g., "Alzheimer's Disease"
    target_id       INTEGER NOT NULL REFERENCES targets(target_id) ON DELETE CASCADE,
    relevance       TEXT DEFAULT 'established',     -- established, emerging, exploratory
    notes           TEXT,
    UNIQUE(disease, target_id)
);
CREATE INDEX IF NOT EXISTS idx_disease_targets_disease ON disease_targets (LOWER(disease));
CREATE INDEX IF NOT EXISTS idx_disease_targets_target ON disease_targets (target_id);

-- ─────────────────────────────────────────────────────────────────
-- DRUGS
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drugs (
    drug_id         SERIAL PRIMARY KEY,
    canonical_name  TEXT NOT NULL,
    company_ticker  TEXT,
    company_name    TEXT,
    indication_primary TEXT,
    indications     TEXT[] DEFAULT '{}',
    modality        TEXT,                       -- small_molecule, adc, bispecific, etc.
    mechanism       TEXT,                       -- human-readable mechanism description
    pathway         TEXT,                       -- signaling pathway (e.g., "RAS/MAPK")
    phase_highest   TEXT DEFAULT 'Preclinical',
    status          TEXT DEFAULT 'Active',
    approval_date   TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(canonical_name, company_ticker)
);

-- Many-to-many: a drug can hit MULTIPLE targets (bispecifics, multi-selective)
CREATE TABLE IF NOT EXISTS drug_targets (
    id          SERIAL PRIMARY KEY,
    drug_id     INTEGER NOT NULL REFERENCES drugs(drug_id) ON DELETE CASCADE,
    target_id   INTEGER NOT NULL REFERENCES targets(target_id) ON DELETE CASCADE,
    role        TEXT DEFAULT 'primary',         -- primary, secondary, payload_target (for ADCs)
    selectivity TEXT,                           -- selective, multi-selective, pan, allosteric
    UNIQUE(drug_id, target_id)
);
CREATE INDEX IF NOT EXISTS idx_drug_targets_drug ON drug_targets (drug_id);
CREATE INDEX IF NOT EXISTS idx_drug_targets_target ON drug_targets (target_id);

-- Every name this drug has ever had
CREATE TABLE IF NOT EXISTS drug_aliases (
    alias_id    SERIAL PRIMARY KEY,
    drug_id     INTEGER NOT NULL REFERENCES drugs(drug_id) ON DELETE CASCADE,
    alias       TEXT NOT NULL,
    alias_type  TEXT DEFAULT 'code',            -- code, inn, brand, licensed, trial_name, colloquial
    is_current  BOOLEAN DEFAULT TRUE,
    notes       TEXT,
    UNIQUE(alias)
);
CREATE INDEX IF NOT EXISTS idx_drug_aliases_lower ON drug_aliases (LOWER(alias));
CREATE INDEX IF NOT EXISTS idx_drug_aliases_drug_id ON drug_aliases (drug_id);

-- Links drugs to ClinicalTrials.gov trials
CREATE TABLE IF NOT EXISTS drug_trials (
    id          SERIAL PRIMARY KEY,
    drug_id     INTEGER NOT NULL REFERENCES drugs(drug_id) ON DELETE CASCADE,
    nct_id      TEXT NOT NULL,
    phase       TEXT,
    status      TEXT,
    enrollment  INTEGER,
    start_date  TEXT,
    title       TEXT,
    UNIQUE(drug_id, nct_id)
);
CREATE INDEX IF NOT EXISTS idx_drug_trials_nct ON drug_trials (nct_id);
CREATE INDEX IF NOT EXISTS idx_drug_trials_drug ON drug_trials (drug_id);

-- Auto-generated PubMed search terms for each drug
CREATE TABLE IF NOT EXISTS drug_pubmed_terms (
    id          SERIAL PRIMARY KEY,
    drug_id     INTEGER REFERENCES drugs(drug_id) ON DELETE CASCADE,
    indication  TEXT,
    search_term TEXT NOT NULL,
    term_type   TEXT DEFAULT 'drug',            -- drug, target, mechanism, landscape
    UNIQUE(drug_id, search_term)
);
"""


def setup_tables():
    """Create the drug entity tables in Neon."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()
    print("  ✓ Drug entity tables created")
    cur.close()
    conn.close()


# =============================================================================
# Target Hierarchy
# =============================================================================
# Structure: (name, display_name, parent_name_or_None, target_class, gene_symbol,
#             description, keywords[], aliases[])

TARGET_HIERARCHY = [
    # ─── RAS superfamily ───
    ("RAS", "RAS (superfamily)", None, "gene_family", None,
     "RAS GTPase superfamily: KRAS, NRAS, HRAS",
     ["RAS", "RAS GTPase", "RAS superfamily", "RAS oncogene", "pan-RAS"],
     ["pan-RAS", "RAS family", "RAS protein"]),

    ("KRAS", "KRAS", "RAS", "gene", "KRAS",
     "KRAS oncogene — most commonly mutated RAS isoform in cancer",
     ["KRAS", "KRAS mutation", "KRAS-mutant", "KRAS inhibitor", "Kirsten rat sarcoma"],
     ["pan-KRAS", "KRAS-mutant cancer", "KRAS oncogene"]),

    ("KRAS G12C", "KRAS G12C", "KRAS", "mutation", "KRAS",
     "KRAS G12C point mutation — glycine to cysteine at position 12. ~13% of NSCLC.",
     ["KRAS G12C", "G12C mutation", "G12C inhibitor", "KRAS G12C inhibitor", "covalent KRAS"],
     ["G12C", "KRAS p.G12C", "KRAS c.34G>T"]),

    ("KRAS G12D", "KRAS G12D", "KRAS", "mutation", "KRAS",
     "KRAS G12D — glycine to aspartic acid. Most common KRAS mutation in pancreatic cancer (~36%).",
     ["KRAS G12D", "G12D mutation", "G12D inhibitor", "KRAS G12D inhibitor"],
     ["G12D", "KRAS p.G12D"]),

    ("KRAS G12V", "KRAS G12V", "KRAS", "mutation", "KRAS",
     "KRAS G12V — glycine to valine. Common in NSCLC and pancreatic cancer.",
     ["KRAS G12V", "G12V mutation"],
     ["G12V", "KRAS p.G12V"]),

    ("KRAS G12R", "KRAS G12R", "KRAS", "mutation", "KRAS",
     "KRAS G12R — glycine to arginine. ~16% of pancreatic cancers.",
     ["KRAS G12R", "G12R mutation"],
     ["G12R", "KRAS p.G12R"]),

    ("KRAS G13D", "KRAS G13D", "KRAS", "mutation", "KRAS",
     "KRAS G13D — glycine to aspartic acid at position 13. Common in CRC.",
     ["KRAS G13D", "G13D mutation"],
     ["G13D", "KRAS p.G13D"]),

    ("KRAS multi-selective", "KRAS Multi-Selective", "KRAS", "mutation", "KRAS",
     "Drugs that inhibit multiple KRAS mutations (G12X) but not all RAS isoforms.",
     ["KRAS multi-selective", "multi-selective KRAS", "RAS(ON)", "pan-KRAS mutation"],
     ["KRAS multi-selective inhibitor", "RAS(ON) inhibitor", "RASGON"]),

    ("NRAS", "NRAS", "RAS", "gene", "NRAS",
     "NRAS oncogene — mutated in melanoma (~20%), AML, thyroid.",
     ["NRAS", "NRAS mutation", "NRAS-mutant"],
     ["NRAS oncogene"]),

    ("HRAS", "HRAS", "RAS", "gene", "HRAS",
     "HRAS oncogene — mutated in bladder, head/neck.",
     ["HRAS", "HRAS mutation"],
     ["HRAS oncogene"]),

    # ─── RAF/MEK/ERK (downstream of RAS) ───
    ("BRAF", "BRAF", None, "gene", "BRAF",
     "BRAF kinase — V600E mutation common in melanoma, CRC, NSCLC, thyroid.",
     ["BRAF", "BRAF V600E", "BRAF inhibitor", "BRAF mutation"],
     ["BRAF V600E", "BRAF V600", "BRAF-mutant"]),

    ("MEK", "MEK (MEK1/2)", None, "gene", "MAP2K1",
     "MEK1/2 kinase — downstream of RAF in the MAPK pathway.",
     ["MEK", "MEK1", "MEK2", "MEK inhibitor", "MEK1/2"],
     ["MAP2K1", "MAP2K2", "MEK inhibition"]),

    # ─── EGFR family ───
    ("EGFR", "EGFR (ErbB1)", None, "gene", "EGFR",
     "Epidermal Growth Factor Receptor — mutated in ~15% of NSCLC (Western) and ~50% (Asian).",
     ["EGFR", "EGFR mutation", "EGFR inhibitor", "ErbB1", "EGF receptor"],
     ["ErbB1", "HER1", "EGFR-mutant"]),

    ("EGFR exon19del", "EGFR Exon 19 Deletion", "EGFR", "mutation", "EGFR",
     "EGFR exon 19 deletion — most common sensitizing EGFR mutation.",
     ["EGFR exon 19", "exon 19 deletion", "del19"],
     ["EGFR del19", "exon 19 del"]),

    ("EGFR L858R", "EGFR L858R", "EGFR", "mutation", "EGFR",
     "EGFR L858R point mutation in exon 21 — second most common sensitizing mutation.",
     ["EGFR L858R", "L858R mutation"],
     ["L858R", "EGFR exon 21 L858R"]),

    ("EGFR T790M", "EGFR T790M", "EGFR", "mutation", "EGFR",
     "EGFR T790M gatekeeper mutation — resistance to 1st/2nd-gen EGFR TKIs.",
     ["EGFR T790M", "T790M resistance", "T790M mutation"],
     ["T790M"]),

    ("EGFR C797S", "EGFR C797S", "EGFR", "mutation", "EGFR",
     "EGFR C797S — resistance mutation to osimertinib (3rd-gen EGFR TKI).",
     ["EGFR C797S", "C797S resistance", "C797S mutation", "osimertinib resistance"],
     ["C797S"]),

    ("EGFR exon20ins", "EGFR Exon 20 Insertion", "EGFR", "mutation", "EGFR",
     "EGFR exon 20 insertions — historically difficult to drug.",
     ["EGFR exon 20 insertion", "exon 20 ins", "EGFR exon20ins"],
     ["exon 20 insertion", "EGFR ins20"]),

    # ─── HER2 family ───
    ("HER2", "HER2 (ErbB2)", None, "gene", "ERBB2",
     "HER2 receptor — amplified in ~20% of breast cancers, gastric, others.",
     ["HER2", "ErbB2", "ERBB2", "HER2 amplification", "HER2 overexpression"],
     ["HER2+", "HER2-positive", "HER2-amplified", "ErbB2"]),

    ("HER2-low", "HER2-Low", "HER2", "isoform", "ERBB2",
     "HER2-low expression (IHC 1+ or IHC 2+/ISH-). New targetable category.",
     ["HER2-low", "HER2 low", "IHC 1+", "IHC 2+/ISH-"],
     ["HER2 low expression"]),

    ("HER2-ultralow", "HER2-Ultralow", "HER2", "isoform", "ERBB2",
     "HER2-ultralow (IHC 0 with faint staining). Emerging targetable category.",
     ["HER2-ultralow", "HER2 ultralow", "IHC 0 faint"],
     ["HER2 ultra-low"]),

    # ─── ALK / ROS1 ───
    ("ALK", "ALK", None, "gene", "ALK",
     "Anaplastic Lymphoma Kinase — ALK fusions in ~5% of NSCLC.",
     ["ALK", "ALK fusion", "EML4-ALK", "ALK-positive", "ALK inhibitor", "anaplastic lymphoma kinase"],
     ["ALK rearrangement", "ALK-rearranged", "ALK+"]),

    ("ROS1", "ROS1", None, "gene", "ROS1",
     "ROS1 fusions in ~1-2% of NSCLC. Structurally similar to ALK.",
     ["ROS1", "ROS1 fusion", "ROS1-positive", "ROS1 inhibitor"],
     ["ROS1 rearrangement", "ROS1+"]),

    # ─── PI3K/AKT/mTOR family ───
    ("PI3K", "PI3K", None, "gene_family", None,
     "Phosphoinositide 3-kinase family — PI3Kalpha, beta, gamma, delta isoforms.",
     ["PI3K", "PI3K inhibitor", "phosphoinositide 3-kinase"],
     ["PI3K pathway", "PI3 kinase"]),

    ("PI3Kalpha", "PI3K-alpha (PIK3CA)", "PI3K", "gene", "PIK3CA",
     "PI3K-alpha — PIK3CA mutations in ~40% of HR+ breast cancer.",
     ["PI3Kalpha", "PIK3CA", "PI3K alpha", "PI3Kalpha inhibitor", "PIK3CA mutation"],
     ["PI3K-alpha", "PIK3CA-mutant", "p110alpha"]),

    ("mTOR", "mTOR", "PI3K", "gene", "MTOR",
     "Mechanistic target of rapamycin — downstream of PI3K/AKT.",
     ["mTOR", "mTOR inhibitor", "mTORC1", "mTORC2", "rapamycin"],
     ["mechanistic target of rapamycin"]),

    # ─── Immune checkpoints ───
    ("PD-1", "PD-1", None, "gene", "PDCD1",
     "Programmed Death-1 receptor — key immune checkpoint.",
     ["PD-1", "PD1", "anti-PD-1", "pembrolizumab", "nivolumab", "cemiplimab"],
     ["programmed death 1", "PDCD1"]),

    ("PD-L1", "PD-L1", None, "gene", "CD274",
     "Programmed Death-Ligand 1 — PD-1 ligand.",
     ["PD-L1", "PDL1", "anti-PD-L1", "atezolizumab", "durvalumab", "avelumab"],
     ["programmed death ligand 1", "CD274"]),

    # ─── ADC targets ───
    ("TROP2", "TROP-2", None, "gene", "TACSTD2",
     "Trophoblast cell-surface antigen 2 — target for ADCs in TNBC, UC, NSCLC.",
     ["TROP-2", "TROP2", "trophoblast cell surface antigen"],
     ["TACSTD2"]),

    ("Nectin-4", "Nectin-4", None, "gene", "NECTIN4",
     "Nectin-4 — target for enfortumab vedotin in urothelial carcinoma.",
     ["Nectin-4", "Nectin4", "PVRL4"],
     ["enfortumab target"]),

    ("B7-H4", "B7-H4", None, "gene", "VTCN1",
     "B7-H4 — emerging target for ADCs in solid tumors.",
     ["B7-H4", "B7H4", "VTCN1"],
     []),

    # ─── Metabolic targets ───
    ("GLP-1", "GLP-1 Receptor", None, "gene", "GLP1R",
     "Glucagon-like peptide-1 receptor — target for obesity, T2D, NASH drugs.",
     ["GLP-1", "GLP1", "GLP-1 receptor", "GLP-1R", "incretin", "GLP-1 agonist"],
     ["glucagon-like peptide 1", "GLP1R"]),

    ("GIP/GLP-1", "GIP/GLP-1 Dual", "GLP-1", "isoform", "GLP1R",
     "Dual GIP and GLP-1 receptor agonist (e.g., tirzepatide).",
     ["GIP/GLP-1", "dual incretin", "GIP GLP-1", "twincretin"],
     ["dual agonist"]),

    ("THR-beta", "Thyroid Hormone Receptor Beta", None, "gene", "THRB",
     "THR-beta — liver-selective target for NASH (resmetirom).",
     ["THR-beta", "THR-β", "thyroid hormone receptor beta", "THRB", "THR beta agonist"],
     ["THRB", "thyroid hormone receptor"]),

    ("FGF21", "FGF21", None, "gene", "FGF21",
     "Fibroblast Growth Factor 21 — metabolic hormone targeted in NASH.",
     ["FGF21", "FGF-21", "FGF21 analog", "fibroblast growth factor 21"],
     []),

    # ─── Other oncology targets ───
    ("OX2R", "Orexin-2 Receptor", None, "gene", "HCRTR2",
     "Orexin-2 receptor — target for narcolepsy drugs (wake-promoting).",
     ["OX2R", "orexin-2", "orexin receptor 2", "OX2R agonist", "orexin agonist"],
     ["HCRTR2", "orexin-2 receptor"]),

    ("HBsAg", "HBsAg (Hepatitis B Surface Antigen)", None, "protein", None,
     "Hepatitis B surface antigen — target for functional cure of HBV.",
     ["HBsAg", "hepatitis B surface antigen", "HBV surface antigen"],
     []),

    ("HBV RNA", "HBV RNA", None, "gene", None,
     "HBV viral RNA — target for siRNA-based therapies aiming for functional cure.",
     ["HBV RNA", "HBV mRNA", "HBV siRNA", "HBV gene silencing"],
     ["HBV transcripts"]),

    ("TIL", "Tumor-Infiltrating Lymphocytes", None, "protein", None,
     "TIL therapy — harvesting and expanding patient's own tumor-infiltrating T cells.",
     ["TIL", "tumor-infiltrating lymphocyte", "TIL therapy", "TIL cell therapy"],
     ["tumor infiltrating lymphocytes"]),

    ("CDK4/6", "CDK4/6", None, "gene", "CDK4",
     "Cyclin-dependent kinases 4 and 6 — key cell cycle regulators in HR+ breast cancer.",
     ["CDK4/6", "CDK4", "CDK6", "CDK4/6 inhibitor", "palbociclib", "ribociclib", "abemaciclib"],
     ["cyclin-dependent kinase 4/6"]),

    ("PARP", "PARP", None, "gene", "PARP1",
     "Poly(ADP-ribose) polymerase — synthetic lethality with BRCA/HRD mutations.",
     ["PARP", "PARPi", "PARP inhibitor", "olaparib", "niraparib", "rucaparib", "talazoparib"],
     ["poly ADP-ribose polymerase"]),

    # ─── Alzheimer's / Neuroscience targets ───
    ("Amyloid-beta", "Amyloid-beta (Aβ)", None, "protein", "APP",
     "Amyloid-beta peptide — central to the amyloid hypothesis of Alzheimer's disease. "
     "Aggregates into plaques in the brain.",
     ["amyloid-beta", "amyloid beta", "Aβ", "amyloid plaque", "anti-amyloid",
      "amyloid clearance", "amyloid removal"],
     ["Abeta", "A-beta", "beta-amyloid", "amyloid plaques"]),

    ("Tau", "Tau Protein", None, "protein", "MAPT",
     "Tau protein — hyperphosphorylated tau aggregates into neurofibrillary tangles in AD. "
     "Also mutated in frontotemporal dementia.",
     ["tau", "tau protein", "anti-tau", "tau aggregation", "phospho-tau", "MAPT",
      "neurofibrillary tangle", "tau inhibitor"],
     ["p-tau", "tau pathology", "tauopathy", "MAPT protein"]),

    ("BACE1", "BACE1 (Beta-Secretase)", None, "gene", "BACE1",
     "Beta-site APP cleaving enzyme 1 — cleaves APP to produce amyloid-beta. "
     "BACE inhibitor trials largely failed but concept remains important for landscape.",
     ["BACE1", "BACE", "beta-secretase", "BACE inhibitor", "beta secretase inhibitor"],
     ["beta-site APP cleaving enzyme", "BACE1 inhibitor"]),

    ("Neuroinflammation", "Neuroinflammation", None, "pathway_node", None,
     "Neuroinflammation — microglia activation, cytokine signaling, complement cascade. "
     "Emerging therapeutic area in AD, ALS, MS, and Parkinson's.",
     ["neuroinflammation", "microglia", "neuroinflammatory", "brain inflammation",
      "neuroimmune", "complement cascade"],
     ["microglial activation", "brain immune response"]),

    ("TREM2", "TREM2", "Neuroinflammation", "gene", "TREM2",
     "TREM2 — microglial receptor. Loss-of-function variants increase AD risk 2-4x. "
     "Drug target for modulating microglial phagocytosis of amyloid.",
     ["TREM2", "TREM2 agonist", "TREM2 activator", "microglial TREM2"],
     ["triggering receptor expressed on myeloid cells 2"]),

    ("CD33", "CD33 (Siglec-3)", "Neuroinflammation", "gene", "CD33",
     "CD33 — sialic acid-binding lectin on microglia. CD33 variants modulate AD risk.",
     ["CD33", "Siglec-3", "CD33 inhibitor", "anti-CD33"],
     ["SIGLEC3"]),

    ("SV2A", "SV2A (Synaptic Vesicle)", None, "gene", "SV2A",
     "Synaptic vesicle glycoprotein 2A — synaptic target. Levetiracetam binds SV2A. "
     "Emerging interest in synaptic rescue for AD.",
     ["SV2A", "synaptic vesicle protein", "SV2A modulator"],
     ["synaptic vesicle glycoprotein 2A"]),

    ("GLP-1 neuro", "GLP-1 (Neuroprotective)", "GLP-1", "isoform", "GLP1R",
     "GLP-1 receptor agonism in the brain — neuroprotective effects being explored in AD/PD.",
     ["GLP-1 neuroprotection", "GLP-1 Alzheimer's", "GLP-1 Parkinson's",
      "semaglutide Alzheimer's", "liraglutide neuroprotection"],
     ["GLP-1 brain", "incretin neuroprotection"]),

    # ─── Parkinson's Disease targets ───
    ("Alpha-synuclein", "Alpha-synuclein", None, "protein", "SNCA",
     "Alpha-synuclein — aggregates into Lewy bodies in Parkinson's disease and DLB.",
     ["alpha-synuclein", "α-synuclein", "synuclein", "anti-synuclein",
      "alpha-synuclein aggregation", "Lewy body"],
     ["SNCA", "a-synuclein", "aSyn"]),

    ("LRRK2", "LRRK2", None, "gene", "LRRK2",
     "Leucine-rich repeat kinase 2 — gain-of-function mutations cause familial Parkinson's (~5%).",
     ["LRRK2", "LRRK2 inhibitor", "LRRK2 mutation", "LRRK2 kinase"],
     ["leucine-rich repeat kinase 2", "PARK8"]),

    ("GBA1", "GBA1 (Glucocerebrosidase)", None, "gene", "GBA1",
     "Glucocerebrosidase — GBA1 mutations are the most common genetic risk factor for PD.",
     ["GBA1", "GBA", "glucocerebrosidase", "GBA1 activator", "GCase"],
     ["GBA1 Parkinson's", "glucocerebrosidase activator"]),

    # ─── Atopic Dermatitis / Immunology targets ───
    ("IL-4", "IL-4 / IL-4Rα", None, "gene", "IL4R",
     "Interleukin-4 and its receptor alpha subunit — key type 2 inflammatory cytokine. "
     "IL-4Rα blocking is the mechanism of dupilumab.",
     ["IL-4", "IL4", "IL-4R", "IL-4Rα", "IL-4 receptor", "interleukin-4", "IL-4Ra", "anti-IL-4R"],
     ["interleukin 4", "IL4R", "IL-4 receptor alpha"]),

    ("IL-13", "IL-13", "IL-4", "gene", "IL13",
     "Interleukin-13 — type 2 cytokine driving atopic inflammation, fibrosis, mucus production. "
     "Target for tralokinumab, lebrikizumab, cendakimab.",
     ["IL-13", "IL13", "anti-IL-13", "interleukin-13", "IL-13 inhibitor"],
     ["interleukin 13"]),

    ("IL-31", "IL-31", None, "gene", "IL31",
     "Interleukin-31 — 'itch cytokine' driving pruritus in atopic dermatitis. "
     "Target for nemolizumab (anti-IL-31Rα).",
     ["IL-31", "IL31", "anti-IL-31", "interleukin-31", "IL-31 receptor", "itch cytokine"],
     ["interleukin 31", "IL-31RA", "pruritus cytokine"]),

    ("OX40", "OX40 / OX40L", None, "gene", "TNFRSF4",
     "OX40 (CD134) and its ligand OX40L — T cell co-stimulatory molecules. "
     "Blocking OX40L reduces T cell activation in atopic dermatitis. Target for amlitelimab, rocatinlimab.",
     ["OX40", "OX40L", "anti-OX40", "anti-OX40L", "CD134", "TNFSF4", "OX40 ligand"],
     ["TNFRSF4", "CD134", "OX40 pathway"]),

    ("TSLP", "TSLP", None, "gene", "TSLP",
     "Thymic Stromal Lymphopoietin — upstream alarmin cytokine that initiates type 2 inflammation. "
     "Target for tezepelumab (approved in asthma, explored in AD).",
     ["TSLP", "thymic stromal lymphopoietin", "anti-TSLP", "alarmin", "TSLP inhibitor"],
     ["thymic stromal lymphopoietin"]),

    ("JAK", "JAK (Janus Kinase)", None, "gene_family", None,
     "Janus kinase family — JAK1, JAK2, JAK3, TYK2. Downstream of multiple cytokine receptors. "
     "JAK inhibitors (abrocitinib, upadacitinib, baricitinib) approved for atopic dermatitis.",
     ["JAK", "JAK inhibitor", "JAKi", "Janus kinase", "JAK1", "JAK2", "JAK3", "TYK2"],
     ["Janus kinase inhibitor", "JAK pathway"]),

    ("JAK1", "JAK1", "JAK", "gene", "JAK1",
     "Janus kinase 1 — selective JAK1 inhibitors (abrocitinib, upadacitinib) for AD. "
     "JAK1 mediates signaling from IL-4, IL-13, IL-31, TSLP receptors.",
     ["JAK1", "JAK1 inhibitor", "selective JAK1", "JAK1-selective"],
     ["Janus kinase 1"]),

    ("JAK1/2", "JAK1/JAK2", "JAK", "gene", "JAK2",
     "Non-selective JAK1/JAK2 inhibitor — baricitinib mechanism. "
     "Broader cytokine blockade but more safety signals.",
     ["JAK1/2", "JAK1/JAK2", "baricitinib mechanism", "non-selective JAK"],
     ["JAK1 JAK2 inhibitor"]),

    ("IL-22", "IL-22", None, "gene", "IL22",
     "Interleukin-22 — drives epidermal hyperplasia and barrier disruption in AD. "
     "Target for fezagepras (LEO Pharma). Th22 pathway.",
     ["IL-22", "IL22", "anti-IL-22", "interleukin-22", "Th22"],
     ["interleukin 22"]),

    ("IL-17", "IL-17", None, "gene", "IL17A",
     "Interleukin-17 — primarily psoriasis target (secukinumab, ixekizumab) but explored in AD. "
     "IL-17A and IL-17F signaling.",
     ["IL-17", "IL17", "IL-17A", "IL-17F", "anti-IL-17", "interleukin-17"],
     ["interleukin 17"]),

    ("IL-18", "IL-18", None, "gene", "IL18",
     "Interleukin-18 — inflammasome-derived cytokine, elevated in AD. "
     "Target for tadekinig alfa. IL-18 drives IFN-gamma and Th1 responses.",
     ["IL-18", "IL18", "anti-IL-18", "interleukin-18", "IL-18 binding protein"],
     ["interleukin 18"]),

    ("IL-2", "IL-2", None, "gene", "IL2",
     "Interleukin-2 — T cell growth factor. Low-dose IL-2 expands Tregs for autoimmune applications. "
     "Explored in AD via rezpegaldesleukin (IL-2 mutein).",
     ["IL-2", "IL2", "interleukin-2", "IL-2 mutein", "low-dose IL-2", "Treg expansion"],
     ["interleukin 2"]),

    ("STAT6", "STAT6", None, "gene", "STAT6",
     "Signal Transducer and Activator of Transcription 6 — downstream of IL-4/IL-13 signaling. "
     "STAT6 degraders (KT-621, Kymera) represent a novel oral approach to blocking type 2 inflammation.",
     ["STAT6", "STAT6 degrader", "STAT6 inhibitor", "STAT6 pathway"],
     ["signal transducer and activator of transcription 6"]),
]


# =============================================================================
# Disease-Target Mapping
# =============================================================================
# (disease, target_name, relevance, notes)
# This tells the system: "for this disease, these are ALL the biological
# approaches being pursued" — even when those targets are unrelated to each other.

DISEASE_TARGET_MAP = [
    # ─── Alzheimer's Disease ───
    ("Alzheimer's Disease", "Amyloid-beta", "established",
     "Amyloid hypothesis: lecanemab, donanemab, aducanumab"),
    ("Alzheimer's Disease", "Tau", "established",
     "Tau hypothesis: antisense, antibodies, aggregation inhibitors"),
    ("Alzheimer's Disease", "BACE1", "established",
     "Beta-secretase inhibitors — multiple Phase 3 failures but key to landscape"),
    ("Alzheimer's Disease", "Neuroinflammation", "emerging",
     "Microglial modulation: TREM2 agonists, CD33, complement inhibitors"),
    ("Alzheimer's Disease", "TREM2", "emerging",
     "TREM2 agonists to enhance microglial clearance of amyloid"),
    ("Alzheimer's Disease", "CD33", "exploratory",
     "CD33 modulation of microglial phagocytosis"),
    ("Alzheimer's Disease", "SV2A", "exploratory",
     "Synaptic rescue approaches"),
    ("Alzheimer's Disease", "GLP-1 neuro", "emerging",
     "GLP-1 agonists showing neuroprotective signals in AD trials"),

    # ─── Parkinson's Disease ───
    ("Parkinson's Disease", "Alpha-synuclein", "established",
     "Anti-synuclein antibodies, small molecules, ASO/siRNA"),
    ("Parkinson's Disease", "LRRK2", "established",
     "LRRK2 kinase inhibitors for genetic PD"),
    ("Parkinson's Disease", "GBA1", "established",
     "GCase activators/stabilizers for GBA-PD"),
    ("Parkinson's Disease", "Neuroinflammation", "emerging",
     "Microglial modulation approaches"),
    ("Parkinson's Disease", "GLP-1 neuro", "emerging",
     "GLP-1 agonists in PD trials (exenatide, semaglutide)"),

    # ─── NSCLC ───
    ("NSCLC", "KRAS", "established", "Most common oncogenic driver mutations"),
    ("NSCLC", "KRAS G12C", "established", "Sotorasib, adagrasib approved"),
    ("NSCLC", "EGFR", "established", "Osimertinib SOC for EGFR-mutant"),
    ("NSCLC", "ALK", "established", "ALK fusions ~5%, lorlatinib SOC"),
    ("NSCLC", "ROS1", "established", "ROS1 fusions ~1-2%"),
    ("NSCLC", "HER2", "emerging", "HER2 mutations ~2-4%"),
    ("NSCLC", "BRAF", "established", "BRAF V600E ~1-2%"),
    ("NSCLC", "MEK", "established", "MEK inhibition in BRAF combos"),
    ("NSCLC", "PD-1", "established", "Pembrolizumab, nivolumab"),
    ("NSCLC", "PD-L1", "established", "Atezolizumab, durvalumab"),
    ("NSCLC", "TROP2", "emerging", "ADC target"),

    # ─── HR+ Breast Cancer ───
    ("HR+ Breast Cancer", "PI3Kalpha", "established", "PIK3CA-mutant ~40%"),
    ("HR+ Breast Cancer", "CDK4/6", "established", "Palbociclib, ribociclib, abemaciclib SOC"),
    ("HR+ Breast Cancer", "HER2-low", "established", "T-DXd for HER2-low"),
    ("HR+ Breast Cancer", "HER2-ultralow", "emerging", "Expanding T-DXd indication"),
    ("HR+ Breast Cancer", "mTOR", "established", "Everolimus"),

    # ─── Pancreatic Cancer ───
    ("Pancreatic Cancer", "KRAS G12D", "established", "Most common mutation ~36%"),
    ("Pancreatic Cancer", "KRAS G12V", "established", "~25% of PDAC"),
    ("Pancreatic Cancer", "KRAS G12R", "established", "~16% of PDAC"),
    ("Pancreatic Cancer", "KRAS", "established", "~90% KRAS-mutant"),

    # ─── NASH/MASH ───
    ("NASH", "THR-beta", "established", "Resmetirom approved"),
    ("NASH", "GLP-1", "established", "Semaglutide in NASH trials"),
    ("NASH", "GIP/GLP-1", "emerging", "Tirzepatide in NASH trials"),
    ("NASH", "FGF21", "established", "Efruxifermin, pegozafermin"),

    # ─── HBV ───
    ("HBV", "HBsAg", "established", "Antibodies targeting surface antigen"),
    ("HBV", "HBV RNA", "established", "siRNA gene silencing approaches"),

    # ─── Atopic Dermatitis ───
    ("Atopic Dermatitis", "IL-4", "established",
     "IL-4Rα blockade: dupilumab (SOC), eblasakimab. Blocks both IL-4 and IL-13 signaling."),
    ("Atopic Dermatitis", "IL-13", "established",
     "Selective IL-13: tralokinumab (approved), lebrikizumab (approved), cendakimab"),
    ("Atopic Dermatitis", "IL-31", "established",
     "Anti-itch: nemolizumab (approved Japan, Phase 3 US). IL-31Rα blockade."),
    ("Atopic Dermatitis", "OX40", "emerging",
     "T cell modulation: amlitelimab (anti-OX40L), rocatinlimab (anti-OX40). Novel mechanism."),
    ("Atopic Dermatitis", "TSLP", "emerging",
     "Upstream alarmin: tezepelumab (approved asthma), tilrekotide. Blocks type 2 initiation."),
    ("Atopic Dermatitis", "JAK1", "established",
     "Oral small molecules: abrocitinib (approved), upadacitinib (approved). Fast onset."),
    ("Atopic Dermatitis", "JAK1/2", "established",
     "Non-selective JAK: baricitinib (approved). Broader cytokine blockade."),
    ("Atopic Dermatitis", "IL-22", "exploratory",
     "Epidermal target: fezagepras (LEO). Th22-driven barrier disruption."),
    ("Atopic Dermatitis", "IL-17", "exploratory",
     "Psoriasis crossover: secukinumab, bimekizumab explored in AD. Mixed data."),
    ("Atopic Dermatitis", "IL-18", "exploratory",
     "Inflammasome pathway: tadekinig alfa. Elevated IL-18 in severe AD."),
    ("Atopic Dermatitis", "IL-2", "emerging",
     "Treg expansion: rezpegaldesleukin (low-dose IL-2 mutein). Immune rebalancing approach."),
    ("Atopic Dermatitis", "STAT6", "emerging",
     "Oral degrader: KT-621 (Kymera). Novel TPD approach to block IL-4/IL-13 downstream signaling."),
    ("Atopic Dermatitis", "PD-1", "exploratory",
     "Immune checkpoint: some evidence of PD-1 dysregulation in severe AD. Experimental."),
]


def seed_targets():
    """Insert the target hierarchy into the database."""
    conn = get_conn()
    cur = conn.cursor()

    target_id_map = {}  # name → target_id
    count = 0

    for (name, display, parent_name, tclass, gene, desc, keywords, aliases) in TARGET_HIERARCHY:
        parent_id = target_id_map.get(parent_name) if parent_name else None

        cur.execute("""
            INSERT INTO targets (name, display_name, parent_id, target_class, gene_symbol, description, keywords)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                parent_id = EXCLUDED.parent_id,
                target_class = EXCLUDED.target_class,
                gene_symbol = EXCLUDED.gene_symbol,
                description = EXCLUDED.description,
                keywords = EXCLUDED.keywords
            RETURNING target_id
        """, (name, display, parent_id, tclass, gene, desc, keywords))

        tid = cur.fetchone()[0]
        target_id_map[name] = tid
        count += 1

        # Add aliases
        for alias in aliases:
            cur.execute("""
                INSERT INTO target_aliases (target_id, alias)
                VALUES (%s, %s)
                ON CONFLICT (alias) DO NOTHING
            """, (tid, alias))

        # Also add the name itself as an alias for lookup
        cur.execute("""
            INSERT INTO target_aliases (target_id, alias)
            VALUES (%s, %s)
            ON CONFLICT (alias) DO NOTHING
        """, (tid, name))

    conn.commit()
    print(f"  ✓ Seeded {count} targets in hierarchy")
    cur.close()
    conn.close()
    return target_id_map


def seed_disease_targets():
    """Insert disease-target mappings into the database."""
    conn = get_conn()
    cur = conn.cursor()
    count = 0

    for (disease, target_name, relevance, notes) in DISEASE_TARGET_MAP:
        # Resolve target_name → target_id
        cur.execute("SELECT target_id FROM targets WHERE name = %s", (target_name,))
        row = cur.fetchone()
        if not row:
            print(f"  ⚠ Target '{target_name}' not found for disease '{disease}', skipping")
            continue
        target_id = row[0]

        cur.execute("""
            INSERT INTO disease_targets (disease, target_id, relevance, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (disease, target_id) DO UPDATE SET
                relevance = EXCLUDED.relevance,
                notes = EXCLUDED.notes
        """, (disease, target_id, relevance, notes))
        count += 1

    conn.commit()
    print(f"  ✓ Seeded {count} disease-target mappings")
    cur.close()
    conn.close()


# =============================================================================
# Seed Data — Your tracked companies' key drugs + landscape drugs
# =============================================================================

# Each entry: (canonical_name, company_ticker, company_name, indication_primary,
#              indications[], modality, mechanism, pathway, phase_highest,
#              status, aliases[],
#              targets[])
#
# aliases is: [(alias_text, alias_type, is_current, note)]
# targets is: [(target_name, role, selectivity)]

SEED_DRUGS = [
    # --- Revolution Medicines (RVMD) ---
    ("daraxonrasib", "RVMD", "Revolution Medicines",
     "NSCLC", ["NSCLC", "Pancreatic Cancer", "Colorectal Cancer"],
     "small_molecule", "RAS(ON) multi-selective inhibitor", "RAS/MAPK",
     "Phase 3", "Active",
     [("RMC-6236", "code", False, "Original internal code, renamed to daraxonrasib"),
      ("RAS(ON) inhibitor", "colloquial", True, None),
      ("RASGON inhibitor", "colloquial", True, None)],
     [("KRAS multi-selective", "primary", "multi-selective")]),

    ("RMC-6291", "RVMD", "Revolution Medicines",
     "NSCLC", ["NSCLC"],
     "small_molecule", "RAS(ON) G12C-selective inhibitor", "RAS/MAPK",
     "Phase 2", "Active",
     [],
     [("KRAS G12C", "primary", "selective")]),

    ("RMC-9805", "RVMD", "Revolution Medicines",
     "Pancreatic Cancer", ["Pancreatic Cancer", "NSCLC", "Colorectal Cancer"],
     "small_molecule", "RAS companion inhibitor (RAS/MAPK pathway)", "RAS/MAPK",
     "Phase 1", "Active",
     [],
     [("KRAS G12D", "primary", "selective")]),

    # --- Nuvalent (NUVL) ---
    ("NVL-655", "NUVL", "Nuvalent",
     "NSCLC", ["NSCLC"],
     "small_molecule", "Brain-penetrant ALK inhibitor (all resistance mutations)", "ALK",
     "Phase 2", "Active",
     [("zidesamtinib", "inn", True, "INN assigned 2025")],
     [("ALK", "primary", "selective")]),

    ("NVL-330", "NUVL", "Nuvalent",
     "NSCLC", ["NSCLC"],
     "small_molecule", "Brain-penetrant ROS1 inhibitor", "ROS1",
     "Phase 1", "Active",
     [],
     [("ROS1", "primary", "selective")]),

    # --- Relay Therapeutics (RLAY) ---
    ("RLY-2608", "RLAY", "Relay Therapeutics",
     "HR+ Breast Cancer", ["HR+ Breast Cancer"],
     "small_molecule", "Mutant-selective PI3Kalpha inhibitor", "PI3K/AKT/mTOR",
     "Phase 2", "Active",
     [],
     [("PI3Kalpha", "primary", "selective")]),

    # --- Roche/Genentech (PI3K landscape) ---
    ("inavolisib", "RHHBY", "Roche / Genentech",
     "HR+ Breast Cancer", ["HR+ Breast Cancer", "PIK3CA-Mutant Breast Cancer"],
     "small_molecule", "Selective PI3Kalpha inhibitor (INAVO120 trial)", "PI3K/AKT/mTOR",
     "Approved", "Active",
     [("GDC-0077", "code", False, "Original Genentech code"),
      ("Itovebi", "brand", True, "FDA-approved brand name 2024"),
      ("RG6114", "code", False, "Roche code")],
     [("PI3Kalpha", "primary", "selective")]),

    ("alpelisib", "NVS", "Novartis",
     "HR+ Breast Cancer", ["HR+ Breast Cancer", "PIK3CA-Mutant Breast Cancer", "PIK3CA-Related Overgrowth Spectrum"],
     "small_molecule", "PI3Kalpha inhibitor (first-in-class, SOLAR-1 trial)", "PI3K/AKT/mTOR",
     "Approved", "Active",
     [("Piqray", "brand", True, "FDA-approved brand name"),
      ("BYL719", "code", False, "Original Novartis code"),
      ("Vijoice", "brand", True, "Brand name for PROS indication")],
     [("PI3Kalpha", "primary", "selective")]),

    # --- Iovance (IOVA) ---
    ("lifileucel", "IOVA", "Iovance Biotherapeutics",
     "Melanoma", ["Melanoma", "NSCLC", "HNSCC"],
     "til_therapy", "Tumor-infiltrating lymphocyte (TIL) cell therapy", "Immune",
     "Approved", "Active",
     [("Amtagvi", "brand", True, "FDA-approved brand name"),
      ("LN-144", "code", False, "Original development code")],
     [("TIL", "primary", None)]),

    # --- Celcuity (CELC) ---
    ("gedatolisib", "CELC", "Celcuity",
     "HR+ Breast Cancer", ["HR+ Breast Cancer"],
     "small_molecule", "Pan-PI3K/mTOR inhibitor", "PI3K/AKT/mTOR",
     "Phase 3", "Active",
     [("PF-05212384", "code", False, "Original Pfizer code before license to Celcuity")],
     [("PI3K", "primary", "pan"), ("mTOR", "secondary", "pan")]),

    # --- Pyxis Oncology (PYXS) ---
    ("PYX-201", "PYXS", "Pyxis Oncology",
     "Solid Tumors", ["Solid Tumors", "Urothelial Carcinoma"],
     "adc", "B7-H4-targeting ADC", "Immune",
     "Phase 1", "Active",
     [],
     [("B7-H4", "primary", "selective")]),

    # --- Vir Biotechnology (VIR) ---
    ("tobevibart", "VIR", "Vir Biotechnology",
     "HBV", ["Hepatitis B"],
     "monoclonal_antibody", "Anti-HBsAg neutralizing antibody", "Viral",
     "Phase 2", "Active",
     [("VIR-3434", "code", False, None)],
     [("HBsAg", "primary", "selective")]),

    ("elebsiran", "VIR", "Vir Biotechnology",
     "HBV", ["Hepatitis B"],
     "rna_therapy", "siRNA targeting HBV", "Viral",
     "Phase 2", "Active",
     [("VIR-2218", "code", False, None)],
     [("HBV RNA", "primary", "selective")]),

    # --- Major external KRAS drugs (for landscape completeness) ---
    ("sotorasib", "AMGN", "Amgen",
     "NSCLC", ["NSCLC", "Colorectal Cancer"],
     "small_molecule", "Covalent KRAS G12C inhibitor", "RAS/MAPK",
     "Approved", "Active",
     [("Lumakras", "brand", True, "FDA-approved brand name"),
      ("AMG 510", "code", False, "Original Amgen code")],
     [("KRAS G12C", "primary", "selective")]),

    ("adagrasib", "MRTI", "Mirati Therapeutics",
     "NSCLC", ["NSCLC", "Colorectal Cancer", "Pancreatic Cancer"],
     "small_molecule", "Covalent KRAS G12C inhibitor", "RAS/MAPK",
     "Approved", "Active",
     [("Krazati", "brand", True, "FDA-approved brand name"),
      ("MRTX849", "code", False, "Original Mirati code")],
     [("KRAS G12C", "primary", "selective")]),

    # --- NASH / Metabolic ---
    ("resmetirom", "MDGL", "Madrigal Pharmaceuticals",
     "NASH", ["NASH", "MASH"],
     "small_molecule", "Thyroid hormone receptor beta agonist", "Metabolic",
     "Approved", "Active",
     [("Rezdiffra", "brand", True, "FDA-approved brand name"),
      ("MGL-3196", "code", False, "Original development code")],
     [("THR-beta", "primary", "selective")]),

    ("semaglutide", "NVO", "Novo Nordisk",
     "Obesity", ["Obesity", "Type 2 Diabetes", "NASH", "MASH"],
     "peptide", "GLP-1 receptor agonist", "Metabolic",
     "Approved", "Active",
     [("Ozempic", "brand", True, "Brand name (injection for T2D)"),
      ("Wegovy", "brand", True, "Brand name (injection for obesity)"),
      ("Rybelsus", "brand", True, "Brand name (oral for T2D)")],
     [("GLP-1", "primary", "selective")]),

    ("tirzepatide", "LLY", "Eli Lilly",
     "Obesity", ["Obesity", "Type 2 Diabetes", "NASH"],
     "peptide", "Dual GIP/GLP-1 receptor agonist", "Metabolic",
     "Approved", "Active",
     [("Mounjaro", "brand", True, "Brand name (T2D)"),
      ("Zepbound", "brand", True, "Brand name (obesity)"),
      ("LY3298176", "code", False, "Original Lilly code")],
     [("GIP/GLP-1", "primary", "selective")]),

    # --- ADC landscape drugs ---
    ("trastuzumab deruxtecan", "DSNKY", "Daiichi Sankyo / AstraZeneca",
     "HER2+ Breast Cancer", ["HER2+ Breast Cancer", "HER2-Low Breast Cancer", "NSCLC", "Gastric Cancer", "Colorectal Cancer"],
     "adc", "HER2-targeting ADC with DXd payload", "HER2",
     "Approved", "Active",
     [("Enhertu", "brand", True, "FDA-approved brand name"),
      ("T-DXd", "colloquial", True, "Common abbreviation"),
      ("DS-8201", "code", False, "Original Daiichi code"),
      ("fam-trastuzumab deruxtecan-nxki", "inn", True, "Full INN")],
     [("HER2", "primary", "selective")]),

    ("sacituzumab govitecan", "GILT", "Gilead Sciences",
     "TNBC", ["TNBC", "Urothelial Carcinoma", "HR+ Breast Cancer"],
     "adc", "TROP-2-targeting ADC with SN-38 payload", "TROP2",
     "Approved", "Active",
     [("Trodelvy", "brand", True, "FDA-approved brand name"),
      ("IMMU-132", "code", False, "Original Immunomedics code")],
     [("TROP2", "primary", "selective")]),

    # --- Alzheimer's Disease drugs ---
    ("lecanemab", "ESALY", "Eisai / Biogen",
     "Alzheimer's Disease", ["Alzheimer's Disease"],
     "monoclonal_antibody", "Anti-amyloid-beta antibody (targets protofibrils)", "Amyloid",
     "Approved", "Active",
     [("Leqembi", "brand", True, "FDA-approved brand name"),
      ("BAN2401", "code", False, "Original Eisai code")],
     [("Amyloid-beta", "primary", "selective")]),

    ("donanemab", "LLY", "Eli Lilly",
     "Alzheimer's Disease", ["Alzheimer's Disease"],
     "monoclonal_antibody", "Anti-amyloid-beta antibody (targets N3pG Aβ plaques)", "Amyloid",
     "Approved", "Active",
     [("Kisunla", "brand", True, "FDA-approved brand name"),
      ("LY3002813", "code", False, "Original Lilly code")],
     [("Amyloid-beta", "primary", "selective")]),

    ("aducanumab", "BIIB", "Biogen",
     "Alzheimer's Disease", ["Alzheimer's Disease"],
     "monoclonal_antibody", "Anti-amyloid-beta antibody (targets aggregated Aβ)", "Amyloid",
     "Withdrawn", "Inactive",
     [("Aduhelm", "brand", True, "FDA brand name — withdrawn from market"),
      ("BIIB037", "code", False, "Original Biogen code")],
     [("Amyloid-beta", "primary", "selective")]),

    # --- Parkinson's Disease drugs ---
    ("prasinezumab", "RHHBY", "Roche / Prothena",
     "Parkinson's Disease", ["Parkinson's Disease"],
     "monoclonal_antibody", "Anti-alpha-synuclein antibody", "Synuclein",
     "Phase 2", "Active",
     [("PRX002", "code", False, "Original Prothena code"),
      ("RO7046015", "code", False, "Roche code")],
     [("Alpha-synuclein", "primary", "selective")]),

    ("BIIB122", "BIIB", "Biogen / Denali",
     "Parkinson's Disease", ["Parkinson's Disease"],
     "small_molecule", "LRRK2 kinase inhibitor", "LRRK2",
     "Phase 2", "Active",
     [("DNL151", "code", False, "Original Denali code")],
     [("LRRK2", "primary", "selective")]),

    ("venglustat", "SNY", "Sanofi",
     "Parkinson's Disease", ["Parkinson's Disease", "Gaucher Disease"],
     "small_molecule", "GBA1 substrate reduction therapy (GCS inhibitor)", "GBA/Lysosomal",
     "Phase 2", "Active",
     [("GZ402671", "code", False, "Sanofi code"),
      ("ibiglustat", "inn", True, "INN name")],
     [("GBA1", "primary", "selective")]),

    # --- Atopic Dermatitis drugs ---
    # IL-4Rα / IL-13 blockers (type 2 cytokine blockade)
    ("dupilumab", "REGN", "Regeneron / Sanofi",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Asthma", "CRSwNP", "Prurigo Nodularis", "COPD", "EoE"],
     "monoclonal_antibody", "Anti-IL-4Rα monoclonal antibody — blocks both IL-4 and IL-13 signaling", "Type 2 Inflammation",
     "Approved", "Active",
     [("Dupixent", "brand", True, "Brand name"),
      ("REGN668", "code", False, "Regeneron code"),
      ("SAR231893", "code", False, "Sanofi code")],
     [("IL-4", "primary", "selective")]),

    ("tralokinumab", "LEO.CO", "LEO Pharma / AstraZeneca",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-IL-13 monoclonal antibody — selective IL-13 neutralization", "Type 2 Inflammation",
     "Approved", "Active",
     [("Adbry", "brand", True, "US brand name"),
      ("Adtralza", "brand", True, "EU brand name"),
      ("CAT-354", "code", False, "Original code")],
     [("IL-13", "primary", "selective")]),

    ("lebrikizumab", "LLY", "Eli Lilly",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-IL-13 monoclonal antibody — high-affinity IL-13 neutralization", "Type 2 Inflammation",
     "Approved", "Active",
     [("Ebglyss", "brand", True, "EU brand name"),
      ("LY3650150", "code", False, "Lilly code")],
     [("IL-13", "primary", "selective")]),

    ("cendakimab", "ABBV", "AbbVie",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Eosinophilic Esophagitis"],
     "monoclonal_antibody", "Anti-IL-13 monoclonal antibody", "Type 2 Inflammation",
     "Phase 3", "Active",
     [("ABT-308", "code", False, "AbbVie code"),
      ("RPC4046", "code", False, "Original code")],
     [("IL-13", "primary", "selective")]),

    ("eblasakimab", "ABBV", "AbbVie",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-IL-13R monoclonal antibody — blocks IL-13 receptor", "Type 2 Inflammation",
     "Phase 2", "Active",
     [("ABBV-323", "code", False, "AbbVie code")],
     [("IL-13", "primary", "selective")]),

    # IL-31 (anti-itch)
    ("nemolizumab", "GMAB", "Galderma",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Prurigo Nodularis"],
     "monoclonal_antibody", "Anti-IL-31Rα monoclonal antibody — blocks itch cytokine IL-31", "IL-31 / Pruritus",
     "Approved", "Active",
     [("Nemluvio", "brand", True, "Brand name"),
      ("CIM331", "code", False, "Original Chugai code")],
     [("IL-31", "primary", "selective")]),

    # OX40 / OX40L (T cell co-stimulation blockade)
    ("rocatinlimab", "AMGN", "Amgen",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-OX40 monoclonal antibody — depletes OX40+ pathogenic T cells", "T Cell Modulation",
     "Phase 3", "Active",
     [("AMG 451", "code", False, "Amgen code"),
      ("KHK4083", "code", False, "Kyowa Kirin code")],
     [("OX40", "primary", "selective")]),

    ("amlitelimab", "SNY", "Sanofi",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Asthma"],
     "monoclonal_antibody", "Anti-OX40L non-depleting monoclonal antibody — blocks T cell co-stimulation without depletion", "T Cell Modulation",
     "Phase 3", "Active",
     [("SAR445229", "code", False, "Sanofi code"),
      ("KY1005", "code", False, "Kymab code")],
     [("OX40", "primary", "selective")]),

    # TSLP (upstream alarmin)
    ("tezepelumab", "AZN", "AstraZeneca / Amgen",
     "Asthma", ["Asthma", "COPD", "Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-TSLP monoclonal antibody — blocks upstream alarmin signaling", "Alarmin / Type 2",
     "Approved", "Active",
     [("Tezspire", "brand", True, "Brand name"),
      ("AMG 157", "code", False, "Amgen code"),
      ("MEDI9929", "code", False, "MedImmune code")],
     [("TSLP", "primary", "selective")]),

    # JAK inhibitors (oral small molecules)
    ("abrocitinib", "PFE", "Pfizer",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "small_molecule", "Selective JAK1 inhibitor — oral", "JAK/STAT",
     "Approved", "Active",
     [("Cibinqo", "brand", True, "Brand name"),
      ("PF-04965842", "code", False, "Pfizer code")],
     [("JAK1", "primary", "selective")]),

    ("upadacitinib", "ABBV", "AbbVie",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Rheumatoid Arthritis", "Psoriatic Arthritis", "Ulcerative Colitis", "Crohn's Disease"],
     "small_molecule", "Selective JAK1 inhibitor — oral", "JAK/STAT",
     "Approved", "Active",
     [("Rinvoq", "brand", True, "Brand name"),
      ("ABT-494", "code", False, "AbbVie code")],
     [("JAK1", "primary", "selective")]),

    ("baricitinib", "LLY", "Eli Lilly",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Rheumatoid Arthritis", "Alopecia Areata"],
     "small_molecule", "JAK1/JAK2 inhibitor — oral", "JAK/STAT",
     "Approved", "Active",
     [("Olumiant", "brand", True, "Brand name"),
      ("LY3009104", "code", False, "Lilly code"),
      ("INCB028050", "code", False, "Incyte code")],
     [("JAK1/2", "primary", "multi-selective")]),

    # IL-2 (Treg expansion)
    ("rezpegaldesleukin", "SNY", "Sanofi",
     "Atopic Dermatitis", ["Atopic Dermatitis", "SLE", "Alopecia Areata"],
     "biologic", "PEGylated IL-2 mutein — low-dose Treg expansion", "Immune Regulation",
     "Phase 2", "Active",
     [("SAR444336", "code", False, "Sanofi code"),
      ("THOR-707", "code", False, "Synthorx code")],
     [("IL-2", "primary", "selective")]),

    # IL-22
    ("fezagepras", "LEO.CO", "LEO Pharma",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "small_molecule", "Oral PGD2/DP2 antagonist", "Prostaglandin / Type 2",
     "Phase 2", "Active",
     [("LEO 39652", "code", False, "LEO code")],
     [("IL-22", "secondary", "multi-selective")]),

    # STAT6 degrader (novel oral)
    ("KT-621", "KYMR", "Kymera Therapeutics",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "small_molecule", "STAT6 targeted protein degrader — oral, blocks IL-4/IL-13 signaling downstream", "TPD / Type 2",
     "Phase 2", "Active",
     [("KT621", "code", False, "No hyphen variant")],
     [("STAT6", "primary", "selective")]),

    # IL-17 (psoriasis crossover)
    ("secukinumab", "NVS", "Novartis",
     "Psoriasis", ["Psoriasis", "Psoriatic Arthritis", "Ankylosing Spondylitis", "Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-IL-17A monoclonal antibody", "IL-17 / Th17",
     "Approved", "Active",
     [("Cosentyx", "brand", True, "Brand name"),
      ("AIN457", "code", False, "Novartis code")],
     [("IL-17", "primary", "selective")]),

    # IL-18
    ("tadekinig alfa", None, "AB2 Bio",
     "Atopic Dermatitis", ["Atopic Dermatitis", "AOSD"],
     "biologic", "IL-18 binding protein — neutralizes free IL-18", "IL-18 / Inflammasome",
     "Phase 2", "Active",
     [],
     [("IL-18", "primary", "selective")]),

    # Bispecifics in AD
    ("IMG-007", "IMGN", "ImmunoGen / Sanofi",
     "Atopic Dermatitis", ["Atopic Dermatitis"],
     "monoclonal_antibody", "Anti-OX40L monoclonal antibody", "T Cell Modulation",
     "Phase 2", "Active",
     [],
     [("OX40", "primary", "selective")]),

    # ==========================================================================
    # NARCOLEPSY / SLEEP DISORDERS — Competitive Landscape
    # ==========================================================================

    # --- Alkermes (ALKS) ---
    ("alixorexton", "ALKS", "Alkermes",
     "Narcolepsy Type 2", ["Narcolepsy Type 1", "Narcolepsy Type 2", "Idiopathic Hypersomnia"],
     "small_molecule", "Oral orexin-2 receptor agonist — once-daily dosing. First OX2R agonist with Phase 2 efficacy in NT2.",
     "Orexin / Wakefulness",
     "Phase 3", "Active",
     ["ALKS 2680", "ALKS-2680", "alixorexton"],
     [("OX2R", "primary", "selective")]),

    # --- Takeda (TAK) ---
    ("oveporexton", "TAK", "Takeda",
     "Narcolepsy Type 1", ["Narcolepsy Type 1", "Narcolepsy Type 2"],
     "small_molecule", "Oral orexin-2 receptor agonist — twice-daily dosing. Most advanced OX2R agonist program, Phase 3 in NT1.",
     "Orexin / Wakefulness",
     "Phase 3", "Active",
     ["TAK-861", "TAK861", "oveporexton"],
     [("OX2R", "primary", "selective")]),

    # --- Centessa (CNTA) ---
    ("mazindol ER", "CNTA", "Centessa Pharmaceuticals",
     "Narcolepsy", ["Narcolepsy Type 1", "Narcolepsy Type 2", "Idiopathic Hypersomnia"],
     "small_molecule", "Extended-release mazindol — triple monoamine reuptake inhibitor with orexin receptor activity. Oral, once-daily.",
     "Orexin / Wakefulness",
     "Phase 3", "Active",
     ["LNP-023-mazindol", "mazindol", "NLS-1 Pharma", "SWS101"],
     [("OX2R", "secondary", "non-selective")]),

    # --- Harmony Biosciences (HRMY) ---
    ("pitolisant", "HRMY", "Harmony Biosciences",
     "Narcolepsy", ["Narcolepsy Type 1", "Narcolepsy Type 2", "Excessive Daytime Sleepiness"],
     "small_molecule", "Histamine H3 receptor inverse agonist/antagonist — enhances histamine release to promote wakefulness. APPROVED (Wakix).",
     "Histamine / Wakefulness",
     "Approved", "Marketed",
     ["Wakix", "pitolisant", "BF2.649"],
     [("H3R", "primary", "selective")]),

    # --- Jazz Pharmaceuticals (JAZZ) ---
    ("sodium oxybate", "JAZZ", "Jazz Pharmaceuticals",
     "Narcolepsy", ["Narcolepsy Type 1", "Narcolepsy Type 2", "Cataplexy", "Idiopathic Hypersomnia"],
     "small_molecule", "GHB-based GABA-B agonist — the standard of care for narcolepsy with cataplexy. Twice-nightly dosing (Xyrem) or once-nightly (Xywav).",
     "GABA / Sleep Regulation",
     "Approved", "Marketed",
     ["Xyrem", "Xywav", "sodium oxybate", "calcium/magnesium/potassium/sodium oxybates", "JZP-258", "lower-sodium oxybate"],
     [("GABA-B", "primary", "non-selective")]),

    # --- Jazz Pharmaceuticals (JAZZ) ---
    ("solriamfetol", "JAZZ", "Jazz Pharmaceuticals",
     "Excessive Daytime Sleepiness", ["Narcolepsy", "Obstructive Sleep Apnea", "Excessive Daytime Sleepiness"],
     "small_molecule", "Dopamine/norepinephrine reuptake inhibitor — promotes wakefulness. APPROVED (Sunosi).",
     "Dopamine / Wakefulness",
     "Approved", "Marketed",
     ["Sunosi", "solriamfetol", "JZP-110", "R228060"],
     [("DAT", "primary", "non-selective"), ("NET", "primary", "non-selective")]),

    # --- Eisai ---
    ("lemborexant", "ESALY", "Eisai",
     "Insomnia", ["Insomnia", "Irregular Sleep-Wake Rhythm Disorder"],
     "small_molecule", "Dual orexin receptor antagonist (DORA) — blocks OX1R and OX2R to promote sleep. APPROVED (Dayvigo). Opposite mechanism to OX2R agonists.",
     "Orexin / Sleep Regulation",
     "Approved", "Marketed",
     ["Dayvigo", "lemborexant", "E2006"],
     [("OX1R", "primary", "non-selective"), ("OX2R", "primary", "non-selective")]),

    # --- Avadel Pharmaceuticals (AVDL) ---
    ("lumryz", "AVDL", "Avadel Pharmaceuticals",
     "Narcolepsy", ["Narcolepsy Type 1", "Narcolepsy Type 2", "Cataplexy"],
     "small_molecule", "Once-nightly sodium oxybate formulation using Micropump extended-release technology. APPROVED.",
     "GABA / Sleep Regulation",
     "Approved", "Marketed",
     ["Lumryz", "FT218", "once-nightly sodium oxybate"],
     [("GABA-B", "primary", "non-selective")]),
]


def seed_drugs():
    """Insert seed drug data into the database."""
    conn = get_conn()
    cur = conn.cursor()

    count_new = 0
    count_skip = 0

    for entry in SEED_DRUGS:
        (name, ticker, company, ind_primary, inds, modality,
         mechanism, pathway, phase, status, aliases, targets) = entry

        # Insert drug (no target column — targets go in drug_targets table)
        cur.execute("""
            INSERT INTO drugs (canonical_name, company_ticker, company_name,
                indication_primary, indications, modality, mechanism,
                pathway, phase_highest, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (canonical_name, company_ticker) DO UPDATE SET
                indication_primary = EXCLUDED.indication_primary,
                indications = EXCLUDED.indications,
                modality = EXCLUDED.modality,
                mechanism = EXCLUDED.mechanism,
                pathway = EXCLUDED.pathway,
                phase_highest = EXCLUDED.phase_highest,
                status = EXCLUDED.status,
                updated_at = NOW()
            RETURNING drug_id, (xmax = 0) AS is_new
        """, (name, ticker, company, ind_primary, inds, modality,
              mechanism, pathway, phase, status))

        row = cur.fetchone()
        drug_id = row[0]
        is_new = row[1]
        if is_new:
            count_new += 1
        else:
            count_skip += 1

        # Always add canonical name as an alias
        cur.execute("""
            INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current)
            VALUES (%s, %s, 'canonical', TRUE)
            ON CONFLICT (alias) DO NOTHING
        """, (drug_id, name))

        # Add other aliases
        for (alias_text, alias_type, is_current, note) in aliases:
            cur.execute("""
                INSERT INTO drug_aliases (drug_id, alias, alias_type, is_current, notes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (alias) DO NOTHING
            """, (drug_id, alias_text, alias_type, is_current, note))

        # Link drug to targets via drug_targets junction table
        for (target_name, role, selectivity) in targets:
            cur.execute("SELECT target_id FROM targets WHERE name = %s", (target_name,))
            trow = cur.fetchone()
            if trow:
                cur.execute("""
                    INSERT INTO drug_targets (drug_id, target_id, role, selectivity)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (drug_id, target_id) DO UPDATE SET
                        role = EXCLUDED.role,
                        selectivity = EXCLUDED.selectivity
                """, (drug_id, trow[0], role, selectivity))
            else:
                print(f"  ⚠ Target '{target_name}' not found for drug '{name}'")

        # Auto-generate PubMed search terms from targets
        _generate_pubmed_terms(cur, drug_id, name, targets, mechanism, pathway, ind_primary, aliases)

    conn.commit()
    print(f"  ✓ Seeded {count_new} new drugs, updated {count_skip} existing")
    cur.close()
    conn.close()


def _generate_pubmed_terms(cur, drug_id, name, targets, mechanism, pathway, indication, aliases):
    """
    Auto-generate PubMed search terms from a drug's biology.

    This is the key insight: for landscape queries, we don't search PubMed by
    drug name alone. We also search by:
      - Target name + "inhibitor" (e.g., "KRAS G12C inhibitor")
      - Target keywords from the hierarchy (e.g., "covalent KRAS")
      - Mechanism (e.g., "RAS(ON) inhibitor")
      - Pathway + indication (e.g., "RAS/MAPK pathway NSCLC")
      - Target + indication (e.g., "KRAS G12C NSCLC clinical trial")
    """
    terms = []

    # Drug-specific terms
    terms.append((drug_id, None, f'"{name}"', "drug"))
    for (alias_text, _, _, _) in aliases:
        if len(alias_text) > 3:  # Skip very short aliases that produce noise
            terms.append((drug_id, None, f'"{alias_text}"', "drug"))

    # Target-level terms (pulled from targets hierarchy)
    for (target_name, role, _selectivity) in targets:
        # Get target info including keywords
        cur.execute("""
            SELECT t.name, t.display_name, t.keywords, t.gene_symbol,
                   p.name AS parent_name, p.keywords AS parent_keywords
            FROM targets t
            LEFT JOIN targets p ON t.parent_id = p.target_id
            WHERE t.name = %s
        """, (target_name,))
        trow = cur.fetchone()
        if trow:
            t_name, t_display, t_keywords, t_gene, parent_name, parent_keywords = trow

            # Target + inhibitor/modulator
            terms.append((drug_id, indication,
                          f"{t_name} inhibitor clinical trial", "target"))
            terms.append((drug_id, indication,
                          f"{t_name} inhibitor {indication}", "target"))

            # Gene symbol if available
            if t_gene and len(t_gene) > 2:
                terms.append((drug_id, indication,
                              f"{t_gene} drug development", "target"))

            # Parent target (walk up the tree for broader landscape coverage)
            if parent_name:
                terms.append((drug_id, indication,
                              f"{parent_name} inhibitor {indication}", "target"))

    # Mechanism-level terms
    if mechanism and len(mechanism) > 5:
        terms.append((drug_id, indication, f"{mechanism} clinical", "mechanism"))

    # Pathway + indication (broad landscape)
    if pathway and indication:
        terms.append((drug_id, indication,
                      f"{pathway} pathway {indication} treatment", "landscape"))

    for (did, ind, term, ttype) in terms:
        cur.execute("""
            INSERT INTO drug_pubmed_terms (drug_id, indication, search_term, term_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (drug_id, search_term) DO NOTHING
        """, (did, ind, term, ttype))


# =============================================================================
# Hierarchy Walking Helpers
# =============================================================================

def _get_target_subtree_ids(cur, target_id) -> list:
    """
    Walk DOWN the target tree: given a target_id, return it plus ALL descendant IDs.
    E.g., for "KRAS" → returns IDs for KRAS, G12C, G12D, G12V, G12R, G13D, multi-selective.
    Uses a recursive CTE in Postgres.
    """
    cur.execute("""
        WITH RECURSIVE subtree AS (
            SELECT target_id FROM targets WHERE target_id = %s
            UNION ALL
            SELECT t.target_id FROM targets t
            JOIN subtree s ON t.parent_id = s.target_id
        )
        SELECT target_id FROM subtree
    """, (target_id,))
    return [row["target_id"] if isinstance(row, dict) else row[0] for row in cur.fetchall()]


def _get_target_ancestor_ids(cur, target_id) -> list:
    """
    Walk UP the target tree: given a target_id, return ALL ancestor IDs.
    E.g., for "KRAS G12C" → returns IDs for KRAS, RAS.
    """
    cur.execute("""
        WITH RECURSIVE ancestors AS (
            SELECT parent_id FROM targets WHERE target_id = %s AND parent_id IS NOT NULL
            UNION ALL
            SELECT t.parent_id FROM targets t
            JOIN ancestors a ON t.target_id = a.parent_id
            WHERE t.parent_id IS NOT NULL
        )
        SELECT parent_id AS target_id FROM ancestors
    """, (target_id,))
    return [row["target_id"] if isinstance(row, dict) else row[0] for row in cur.fetchall()]


def _resolve_target(cur, name: str):
    """Resolve a target name/alias to target_id (case-insensitive)."""
    # Try exact match on targets table
    cur.execute("SELECT target_id FROM targets WHERE LOWER(name) = LOWER(%s)", (name,))
    row = cur.fetchone()
    if row:
        return row["target_id"] if isinstance(row, dict) else row[0]

    # Try alias lookup
    cur.execute("SELECT target_id FROM target_aliases WHERE LOWER(alias) = LOWER(%s)", (name,))
    row = cur.fetchone()
    if row:
        return row["target_id"] if isinstance(row, dict) else row[0]

    # Try LIKE match
    cur.execute("SELECT target_id FROM target_aliases WHERE LOWER(alias) LIKE LOWER(%s) LIMIT 1",
                (f"%{name}%",))
    row = cur.fetchone()
    if row:
        return row["target_id"] if isinstance(row, dict) else row[0]
    return None


# =============================================================================
# Lookup Functions (used by the query router)
# =============================================================================

def lookup_drug(name: str) -> Optional[dict]:
    """
    Look up a drug by ANY name (canonical, alias, code, brand).
    Returns the full drug record with all aliases, targets, and PubMed terms.
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Try exact match on alias (case-insensitive)
    cur.execute("""
        SELECT d.*, da.alias AS matched_alias
        FROM drugs d
        JOIN drug_aliases da ON d.drug_id = da.drug_id
        WHERE LOWER(da.alias) = LOWER(%s)
    """, (name,))
    row = cur.fetchone()

    if not row:
        # Try LIKE match for partial names
        cur.execute("""
            SELECT d.*, da.alias AS matched_alias
            FROM drugs d
            JOIN drug_aliases da ON d.drug_id = da.drug_id
            WHERE LOWER(da.alias) LIKE LOWER(%s)
            LIMIT 1
        """, (f"%{name}%",))
        row = cur.fetchone()

    if row:
        drug_id = row["drug_id"]

        # Get all aliases
        cur.execute("""
            SELECT alias, alias_type, is_current, notes
            FROM drug_aliases WHERE drug_id = %s
        """, (drug_id,))
        row["aliases"] = [dict(a) for a in cur.fetchall()]

        # Get targets (via junction table, with hierarchy info)
        cur.execute("""
            SELECT t.name AS target_name, t.display_name, t.target_class,
                   t.gene_symbol, dt.role, dt.selectivity,
                   p.name AS parent_target
            FROM drug_targets dt
            JOIN targets t ON dt.target_id = t.target_id
            LEFT JOIN targets p ON t.parent_id = p.target_id
            WHERE dt.drug_id = %s
        """, (drug_id,))
        row["targets"] = [dict(t) for t in cur.fetchall()]

        # Get PubMed terms
        cur.execute("""
            SELECT search_term, term_type, indication
            FROM drug_pubmed_terms WHERE drug_id = %s
        """, (drug_id,))
        row["pubmed_terms"] = [dict(t) for t in cur.fetchall()]

    cur.close()
    conn.close()
    return dict(row) if row else None


def get_landscape(indication: str) -> list[dict]:
    """
    Get ALL drugs in development for a given indication.
    Returns drugs grouped by phase, with target info from drug_targets.

    This powers landscape queries like:
    "What is the competitive landscape in NASH?"
    "Show me all drugs in development for Alzheimer's"
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Search by indication (check both primary and array)
    cur.execute("""
        SELECT d.*,
            ARRAY_AGG(DISTINCT da.alias) FILTER (WHERE da.alias IS NOT NULL) AS all_aliases,
            ARRAY_AGG(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) AS target_names,
            ARRAY_AGG(DISTINCT t.display_name) FILTER (WHERE t.display_name IS NOT NULL) AS target_displays
        FROM drugs d
        LEFT JOIN drug_aliases da ON d.drug_id = da.drug_id
        LEFT JOIN drug_targets dt ON d.drug_id = dt.drug_id
        LEFT JOIN targets t ON dt.target_id = t.target_id
        WHERE LOWER(d.indication_primary) LIKE LOWER(%s)
           OR EXISTS (SELECT 1 FROM unnest(d.indications) AS ind WHERE LOWER(ind) LIKE LOWER(%s))
        GROUP BY d.drug_id
        ORDER BY
            CASE d.phase_highest
                WHEN 'Approved' THEN 1
                WHEN 'Phase 3' THEN 2
                WHEN 'Phase 2' THEN 3
                WHEN 'Phase 2b' THEN 3
                WHEN 'Phase 1/2' THEN 4
                WHEN 'Phase 1' THEN 5
                WHEN 'Preclinical' THEN 6
                ELSE 7
            END,
            d.canonical_name
    """, (f"%{indication}%", f"%{indication}%"))

    drugs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return drugs


def get_drugs_by_target(target_name: str) -> list[dict]:
    """
    Find all drugs targeting a specific target — WALKS THE HIERARCHY.

    "KRAS" → finds pan-RAS drugs + pan-KRAS + G12C-selective + G12D + G12V + etc.
    "KRAS G12C" → finds G12C-selective drugs + also includes pan-KRAS and pan-RAS
                   drugs (since they also cover G12C).

    The logic:
      1. Resolve target_name to target_id
      2. Walk DOWN to get all children (e.g., KRAS → G12C, G12D, ...)
      3. Walk UP to get ancestors (e.g., KRAS G12C → KRAS, RAS)
      4. Find all drugs linked to ANY of these target IDs
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Resolve target
    target_id = _resolve_target(cur, target_name)
    if not target_id:
        cur.close()
        conn.close()
        return []

    # Get all relevant target IDs (subtree + ancestors)
    subtree_ids = _get_target_subtree_ids(cur, target_id)
    ancestor_ids = _get_target_ancestor_ids(cur, target_id)
    all_target_ids = list(set(subtree_ids + ancestor_ids))

    if not all_target_ids:
        cur.close()
        conn.close()
        return []

    # Find all drugs linked to any of these targets
    cur.execute("""
        SELECT d.*,
            ARRAY_AGG(DISTINCT da.alias) FILTER (WHERE da.alias IS NOT NULL) AS all_aliases,
            ARRAY_AGG(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) AS target_names,
            ARRAY_AGG(DISTINCT t.display_name) FILTER (WHERE t.display_name IS NOT NULL) AS target_displays,
            ARRAY_AGG(DISTINCT dt.selectivity) FILTER (WHERE dt.selectivity IS NOT NULL) AS selectivities
        FROM drugs d
        JOIN drug_targets dt ON d.drug_id = dt.drug_id
        JOIN targets t ON dt.target_id = t.target_id
        LEFT JOIN drug_aliases da ON d.drug_id = da.drug_id
        WHERE dt.target_id = ANY(%s::uuid[])
        GROUP BY d.drug_id
        ORDER BY
            CASE d.phase_highest
                WHEN 'Approved' THEN 1
                WHEN 'Phase 3' THEN 2
                WHEN 'Phase 2' THEN 3
                ELSE 4
            END
    """, (all_target_ids,))

    drugs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return drugs


def get_disease_target_landscape(disease: str) -> dict:
    """
    Get the full target landscape for a disease.

    Returns a dict with:
      - disease: the disease name
      - target_groups: list of {target_name, display_name, relevance, notes, drugs: [...]}

    This is what powers queries like "What is the Alzheimer's drug landscape?"
    — it shows drugs GROUPED BY their biological approach (amyloid, tau, neuro, etc.)
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Find matching disease-target mappings (fuzzy match on disease name)
    cur.execute("""
        SELECT dt.disease, t.name AS target_name, t.display_name,
               dt.relevance, dt.notes,
               t.target_id
        FROM disease_targets dt
        JOIN targets t ON dt.target_id = t.target_id
        WHERE LOWER(dt.disease) LIKE LOWER(%s)
        ORDER BY
            CASE dt.relevance
                WHEN 'established' THEN 1
                WHEN 'emerging' THEN 2
                WHEN 'exploratory' THEN 3
                ELSE 4
            END,
            t.name
    """, (f"%{disease}%",))

    mappings = [dict(r) for r in cur.fetchall()]

    if not mappings:
        cur.close()
        conn.close()
        return {"disease": disease, "target_groups": []}

    actual_disease = mappings[0]["disease"]
    target_groups = []

    for m in mappings:
        # For each target, find drugs (walking the subtree)
        subtree_ids = _get_target_subtree_ids(cur, m["target_id"])

        cur.execute("""
            SELECT d.canonical_name, d.company_name, d.company_ticker,
                   d.modality, d.mechanism, d.phase_highest, d.status,
                   t.name AS specific_target, dt.selectivity
            FROM drugs d
            JOIN drug_targets dt ON d.drug_id = dt.drug_id
            JOIN targets t ON dt.target_id = t.target_id
            WHERE dt.target_id = ANY(%s::uuid[])
              AND (LOWER(d.indication_primary) LIKE LOWER(%s)
                   OR EXISTS (SELECT 1 FROM unnest(d.indications) AS ind
                              WHERE LOWER(ind) LIKE LOWER(%s)))
            ORDER BY
                CASE d.phase_highest
                    WHEN 'Approved' THEN 1 WHEN 'Phase 3' THEN 2
                    WHEN 'Phase 2' THEN 3 WHEN 'Phase 1' THEN 4
                    ELSE 5
                END
        """, (subtree_ids, f"%{actual_disease}%", f"%{actual_disease}%"))

        drugs = [dict(r) for r in cur.fetchall()]

        target_groups.append({
            "target_name": m["target_name"],
            "display_name": m["display_name"],
            "relevance": m["relevance"],
            "notes": m["notes"],
            "drugs": drugs,
        })

    cur.close()
    conn.close()
    return {"disease": actual_disease, "target_groups": target_groups}


def get_pubmed_terms_for_landscape(indication: str) -> list[str]:
    """
    Get all PubMed search terms relevant to a landscape/indication.

    Aggregates terms from ALL drugs in that indication, giving comprehensive
    PubMed coverage.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT dpt.search_term
        FROM drug_pubmed_terms dpt
        JOIN drugs d ON dpt.drug_id = d.drug_id
        WHERE LOWER(d.indication_primary) LIKE LOWER(%s)
           OR EXISTS (SELECT 1 FROM unnest(d.indications) AS ind WHERE LOWER(ind) LIKE LOWER(%s))
           OR LOWER(dpt.indication) LIKE LOWER(%s)
        ORDER BY dpt.search_term
    """, (f"%{indication}%", f"%{indication}%", f"%{indication}%"))

    terms = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return terms


def format_landscape_for_claude(drugs: list[dict], indication: str = "") -> str:
    """
    Format landscape data as context for Claude synthesis.
    Used by the query router when answering landscape questions.
    Now includes target info from drug_targets instead of flat target column.
    """
    if not drugs:
        return ""

    parts = [f"=== DRUG LANDSCAPE: {indication or 'All'} ==="]
    parts.append(f"Total drugs found: {len(drugs)}\n")

    # Group by phase
    phases = {}
    for d in drugs:
        phase = d.get("phase_highest", "Unknown")
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(d)

    for phase in ["Approved", "Phase 3", "Phase 2b", "Phase 2", "Phase 1/2", "Phase 1", "Preclinical"]:
        if phase not in phases:
            continue
        parts.append(f"\n--- {phase} ---")
        for d in phases[phase]:
            aliases = d.get("all_aliases", [])
            alias_str = f" (also: {', '.join(a for a in (aliases or [])[:3] if a != d['canonical_name'])})" if aliases else ""
            parts.append(f"  {d['canonical_name']}{alias_str}")
            parts.append(f"    Company: {d.get('company_name', '?')} ({d.get('company_ticker', '?')})")

            # Targets from drug_targets join
            target_names = d.get("target_names") or d.get("target_displays") or []
            target_str = ", ".join(target_names) if target_names else "?"
            parts.append(f"    Target(s): {target_str} | Modality: {d.get('modality', '?')}")

            parts.append(f"    Mechanism: {d.get('mechanism', '?')}")
            parts.append(f"    Status: {d.get('status', '?')}")
            inds = d.get("indications", [])
            if inds:
                parts.append(f"    Indications: {', '.join(inds)}")
            parts.append("")

    return "\n".join(parts)


def format_disease_landscape_for_claude(landscape: dict) -> str:
    """
    Format a disease-target landscape for Claude synthesis.
    Groups drugs by biological approach (target) within a disease.
    """
    if not landscape.get("target_groups"):
        return ""

    disease = landscape["disease"]
    parts = [f"=== DISEASE LANDSCAPE: {disease} ==="]
    parts.append(f"Biological approaches: {len(landscape['target_groups'])}\n")

    for group in landscape["target_groups"]:
        relevance_tag = f"[{group['relevance'].upper()}]"
        parts.append(f"\n─── {group['display_name']} {relevance_tag} ───")
        if group.get("notes"):
            parts.append(f"  Context: {group['notes']}")

        if group["drugs"]:
            for d in group["drugs"]:
                parts.append(f"  • {d['canonical_name']} ({d.get('company_name', '?')})")
                parts.append(f"    Phase: {d.get('phase_highest', '?')} | Modality: {d.get('modality', '?')}")
                parts.append(f"    Mechanism: {d.get('mechanism', '?')}")
        else:
            parts.append("  (No drugs currently seeded for this approach)")
        parts.append("")

    return "\n".join(parts)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SatyaBio Drug Entity Database")
    parser.add_argument("--setup", action="store_true", help="Create tables + seed data")
    parser.add_argument("--lookup", type=str, help="Look up a drug by name/alias")
    parser.add_argument("--landscape", type=str, help="Get landscape for an indication")
    parser.add_argument("--disease", type=str, help="Get disease-target landscape (grouped by biological approach)")
    parser.add_argument("--target", type=str, help="Get all drugs for a target (walks hierarchy)")
    parser.add_argument("--pubmed-terms", type=str, help="Get PubMed search terms for an indication")
    args = parser.parse_args()

    if args.setup:
        print("Setting up drug entity database...")
        setup_tables()
        print("Seeding targets hierarchy...")
        seed_targets()
        print("Seeding disease-target mappings...")
        seed_disease_targets()
        print("Seeding initial drug data...")
        seed_drugs()
        print("\nDone! Run --lookup, --landscape, --disease, or --target to query.\n")

    elif args.lookup:
        drug = lookup_drug(args.lookup)
        if drug:
            print(f"\n  Found: {drug['canonical_name']} ({drug['company_ticker']})")
            print(f"  Matched via: {drug.get('matched_alias', drug['canonical_name'])}")
            targets = drug.get("targets", [])
            if targets:
                tstr = ", ".join(f"{t['target_name']} ({t['role']}, {t.get('selectivity', '?')})" for t in targets)
                print(f"  Target(s): {tstr}")
            print(f"  Modality: {drug.get('modality')}")
            print(f"  Mechanism: {drug.get('mechanism')}")
            print(f"  Phase: {drug.get('phase_highest')} | Status: {drug.get('status')}")
            print(f"  Indications: {', '.join(drug.get('indications', []))}")
            print(f"\n  Aliases ({len(drug.get('aliases', []))}):")
            for a in drug.get("aliases", []):
                current = " (current)" if a.get("is_current") else " (former)"
                print(f"    - {a['alias']} [{a['alias_type']}]{current}")
            print(f"\n  PubMed terms ({len(drug.get('pubmed_terms', []))}):")
            for t in drug.get("pubmed_terms", []):
                print(f"    - [{t['term_type']}] {t['search_term']}")
        else:
            print(f"\n  No drug found for: {args.lookup}")

    elif args.landscape:
        drugs = get_landscape(args.landscape)
        if drugs:
            print(f"\n  Landscape: {args.landscape} ({len(drugs)} drugs)\n")
            print(format_landscape_for_claude(drugs, args.landscape))
        else:
            print(f"\n  No drugs found for indication: {args.landscape}")

    elif args.disease:
        result = get_disease_target_landscape(args.disease)
        if result.get("target_groups"):
            print(f"\n  Disease-Target Landscape: {result['disease']}\n")
            print(format_disease_landscape_for_claude(result))
        else:
            print(f"\n  No disease-target mapping found for: {args.disease}")

    elif args.target:
        drugs = get_drugs_by_target(args.target)
        if drugs:
            print(f"\n  Drugs targeting {args.target} ({len(drugs)} found):\n")
            for d in drugs:
                targets = d.get("target_names", [])
                tstr = ", ".join(targets) if targets else "?"
                print(f"    {d['canonical_name']} ({d.get('company_ticker', '?')}) — {d.get('phase_highest')} — {tstr} — {d.get('mechanism')}")
        else:
            print(f"\n  No drugs found for target: {args.target}")

    elif args.pubmed_terms:
        terms = get_pubmed_terms_for_landscape(args.pubmed_terms)
        if terms:
            print(f"\n  PubMed search terms for {args.pubmed_terms} ({len(terms)} terms):\n")
            for t in terms:
                print(f"    - {t}")
        else:
            print(f"\n  No PubMed terms for: {args.pubmed_terms}")

    else:
        parser.print_help()
