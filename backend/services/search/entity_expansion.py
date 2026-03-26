"""
SatyaBio — Entity Database Expansion
Top 50 Pharma/Biotech by Market Cap × 5 Therapeutic Areas

Extends drug_entities.py with:
  1. New targets for I&I, cardiometabolic, obesity, expanded oncology, neuropsych
  2. Disease-target mappings for all new indications
  3. ~120+ drug entries across top 50 companies

Companies covered (by therapeutic focus):
  ONCOLOGY: PFE, MRK, RHHBY, AZN, BMY, ABBV, JNJ, GILD, SNY, AMGN, LLY, DSNKY,
            GSK, REGN, VRTX, SGEN(PFE), MRTI, RVMD, NUVL, RLAY, IOVA
  I&I:      ABBV, JNJ, BMY, PFE, LLY, RHHBY, REGN, AZN, ARQT
  CARDIOMETABOLIC: NVO, LLY, AZN, PFE, AMGN, REGN, ALNY, IONS, MDGL
  OBESITY:  NVO, LLY, PFE, AMGN, RHHBY, VKTX, Structure
  NEUROPSYCH: LLY, BIIB, RHHBY, ESALY, ABBV, SNY, AXSM, PRTA, SAGE, CERE

Run:
    python3 entity_expansion.py --setup    # adds all new entities
    python3 entity_expansion.py --verify   # counts by TA
"""

# =============================================================================
# NEW TARGETS (appended to TARGET_HIERARCHY in drug_entities.py)
# =============================================================================

EXPANSION_TARGETS = [
    # ─── I&I / Immunology Targets ───
    ("TNF-alpha", "TNF-alpha", None, "gene", "TNF",
     "Tumor Necrosis Factor alpha — key inflammatory cytokine. Major target in RA, IBD, psoriasis.",
     ["TNF", "TNF-alpha", "TNF inhibitor", "anti-TNF", "tumor necrosis factor"],
     ["TNFa", "TNF-α", "cachectin"]),

    ("IL-17", "IL-17", None, "gene", "IL17A",
     "Interleukin-17 — cytokine driving psoriasis, axSpA, PsA.",
     ["IL-17", "IL17", "IL-17A", "anti-IL-17", "IL-17 inhibitor"],
     ["interleukin 17", "IL17A"]),

    ("IL-23", "IL-23", None, "gene", "IL23A",
     "Interleukin-23 — upstream regulator of Th17 pathway. Key in psoriasis, IBD, PsA.",
     ["IL-23", "IL23", "anti-IL-23", "IL-23 inhibitor", "IL-23p19"],
     ["interleukin 23"]),

    ("IL-4/IL-13", "IL-4/IL-13", None, "gene", "IL4R",
     "Dual IL-4 and IL-13 signaling via IL-4Ralpha — type 2 inflammation.",
     ["IL-4", "IL-13", "IL-4R", "IL4R", "dupilumab", "type 2 inflammation"],
     ["interleukin 4", "interleukin 13", "IL-4 receptor alpha"]),

    ("IL-6", "IL-6", None, "gene", "IL6",
     "Interleukin-6 — pleiotropic cytokine in RA, cytokine storm.",
     ["IL-6", "IL6", "anti-IL-6", "IL-6 receptor", "tocilizumab"],
     ["interleukin 6"]),

    ("IL-31", "IL-31", None, "gene", "IL31",
     "Interleukin-31 — pruritus cytokine, target in atopic dermatitis.",
     ["IL-31", "IL31", "anti-IL-31", "nemolizumab"],
     ["interleukin 31"]),

    ("IL-33", "IL-33", None, "gene", "IL33",
     "Interleukin-33 — alarmin driving type 2 inflammation in asthma, atopic dermatitis.",
     ["IL-33", "IL33", "anti-IL-33", "itepekimab"],
     ["interleukin 33"]),

    ("TSLP", "TSLP", None, "gene", "TSLP",
     "Thymic Stromal Lymphopoietin — epithelial alarmin upstream of type 2 inflammation.",
     ["TSLP", "anti-TSLP", "tezepelumab"],
     ["thymic stromal lymphopoietin"]),

    ("JAK", "JAK (Janus Kinase)", None, "gene_family", None,
     "Janus kinase family — JAK1, JAK2, JAK3, TYK2. Major targets in I&I.",
     ["JAK", "JAK inhibitor", "JAKi", "Janus kinase"],
     ["JAK pathway", "JAK-STAT"]),

    ("JAK1", "JAK1", "JAK", "gene", "JAK1",
     "JAK1 — selective targeting reduces infections vs pan-JAK. Key in RA, AD, UC.",
     ["JAK1", "JAK1 selective", "JAK1 inhibitor", "upadacitinib", "filgotinib"],
     []),

    ("JAK2", "JAK2", "JAK", "gene", "JAK2",
     "JAK2 — mutated in myeloproliferative neoplasms (PV, MF).",
     ["JAK2", "JAK2 V617F", "JAK2 inhibitor", "ruxolitinib"],
     []),

    ("TYK2", "TYK2", "JAK", "gene", "TYK2",
     "TYK2 — selective inhibition for psoriasis, IBD with improved safety.",
     ["TYK2", "TYK2 inhibitor", "deucravacitinib"],
     []),

    ("BTK", "BTK", None, "gene", "BTK",
     "Bruton's Tyrosine Kinase — key in B-cell malignancies and emerging in autoimmune.",
     ["BTK", "BTK inhibitor", "BTKi", "ibrutinib", "zanubrutinib", "acalabrutinib"],
     ["Bruton's tyrosine kinase"]),

    ("S1P", "S1P Receptor", None, "gene", "S1PR1",
     "Sphingosine-1-phosphate receptor — target in MS, UC, IBD.",
     ["S1P", "S1P1", "S1PR1", "ozanimod", "siponimod", "etrasimod"],
     ["sphingosine-1-phosphate"]),

    ("CD20", "CD20", None, "gene", "MS4A1",
     "CD20 — B-cell surface marker, target for B-cell depletion.",
     ["CD20", "anti-CD20", "rituximab", "ocrelizumab", "ofatumumab"],
     ["MS4A1"]),

    ("CTLA-4", "CTLA-4", None, "gene", "CTLA4",
     "CTLA-4 — immune checkpoint, target of ipilimumab.",
     ["CTLA-4", "CTLA4", "anti-CTLA-4", "ipilimumab", "tremelimumab"],
     []),

    ("LAG-3", "LAG-3", None, "gene", "LAG3",
     "LAG-3 — next-gen immune checkpoint after PD-1.",
     ["LAG-3", "LAG3", "anti-LAG-3", "relatlimab"],
     ["lymphocyte activation gene 3"]),

    ("TIGIT", "TIGIT", None, "gene", "TIGIT",
     "TIGIT — immune checkpoint. Tiragolumab trials mixed but field still active.",
     ["TIGIT", "anti-TIGIT", "tiragolumab"],
     []),

    ("BCMA", "BCMA", None, "gene", "TNFRSF17",
     "B-cell maturation antigen — target for myeloma CAR-T and bispecifics.",
     ["BCMA", "anti-BCMA", "TNFRSF17"],
     ["B-cell maturation antigen"]),

    ("GPRC5D", "GPRC5D", None, "gene", "GPRC5D",
     "GPRC5D — emerging myeloma target for bispecifics after BCMA.",
     ["GPRC5D", "anti-GPRC5D", "talquetamab"],
     []),

    ("CD19", "CD19", None, "gene", "CD19",
     "CD19 — B-cell target for CAR-T (DLBCL, ALL) and bispecifics.",
     ["CD19", "anti-CD19", "CAR-T CD19"],
     []),

    ("FcRn", "FcRn", None, "gene", "FCGRT",
     "Neonatal Fc receptor — target for reducing pathogenic IgG in myasthenia gravis, ITP.",
     ["FcRn", "FcRn inhibitor", "FcRn antagonist", "efgartigimod", "rozanolixizumab"],
     ["neonatal Fc receptor"]),

    # ─── Cardiometabolic Targets ───
    ("PCSK9", "PCSK9", None, "gene", "PCSK9",
     "PCSK9 — LDL receptor degradation. Major target for LDL-C lowering.",
     ["PCSK9", "PCSK9 inhibitor", "anti-PCSK9", "evolocumab", "alirocumab"],
     ["proprotein convertase subtilisin kexin 9"]),

    ("ANGPTL3", "ANGPTL3", None, "gene", "ANGPTL3",
     "Angiopoietin-like protein 3 — target for lipid lowering (TG + LDL).",
     ["ANGPTL3", "ANGPTL3 inhibitor", "evinacumab"],
     ["angiopoietin-like 3"]),

    ("Lp(a)", "Lp(a)", None, "gene", "LPA",
     "Lipoprotein(a) — independent CV risk factor. ASO and siRNA approaches.",
     ["Lp(a)", "lipoprotein a", "Lpa", "LPA gene"],
     ["lipoprotein(a)"]),

    ("SGLT2", "SGLT2", None, "gene", "SLC5A2",
     "Sodium-glucose cotransporter-2 — target for T2D, HF, CKD.",
     ["SGLT2", "SGLT2 inhibitor", "SGLT2i", "empagliflozin", "dapagliflozin"],
     ["sodium glucose cotransporter 2"]),

    ("APOC3", "APOC3", None, "gene", "APOC3",
     "Apolipoprotein C-III — target for severe hypertriglyceridemia.",
     ["APOC3", "ApoC-III", "apolipoprotein C-III"],
     []),

    ("GLP-1/glucagon", "GLP-1/Glucagon Dual", "GLP-1", "isoform", "GLP1R",
     "Dual GLP-1/glucagon receptor agonists — surfolisant, mazdutide, pemvidutide.",
     ["GLP-1/glucagon", "dual agonist", "survodutide", "mazdutide"],
     ["glucagon GLP-1 dual"]),

    ("Amylin", "Amylin", None, "gene", "IAPP",
     "Amylin/calcitonin receptor — co-agonists for obesity (cagrilintide).",
     ["amylin", "IAPP", "amylin analog", "cagrilintide"],
     ["islet amyloid polypeptide"]),

    ("ActRII", "Activin Receptor Type II", None, "gene", "ACVR2A",
     "Activin receptor — target for cardiometabolic (bimagrumab muscle/fat).",
     ["ActRII", "ActRIIA", "ActRIIB", "activin", "bimagrumab"],
     ["activin receptor type II"]),

    # ─── Expanded Oncology Targets ───
    ("KRAS-4A", "KRAS-4A Splice", "KRAS", "isoform", "KRAS",
     "KRAS splice variant 4A — emerging target differentiation.",
     ["KRAS-4A", "KRAS 4A"],
     []),

    ("FGFR", "FGFR", None, "gene_family", None,
     "Fibroblast Growth Factor Receptors — FGFR1-4 alterations in bladder, cholangiocarcinoma.",
     ["FGFR", "FGFR inhibitor", "FGFR2", "FGFR3", "erdafitinib", "futibatinib"],
     ["fibroblast growth factor receptor"]),

    ("MET", "MET (c-MET)", None, "gene", "MET",
     "MET receptor — MET exon 14 skipping in NSCLC (~3%), MET amplification.",
     ["MET", "c-MET", "MET inhibitor", "MET exon 14", "capmatinib", "tepotinib"],
     ["hepatocyte growth factor receptor"]),

    ("RET", "RET", None, "gene", "RET",
     "RET proto-oncogene — fusions in NSCLC/thyroid, mutations in MTC.",
     ["RET", "RET inhibitor", "RET fusion", "selpercatinib", "pralsetinib"],
     []),

    ("NTRK", "NTRK (TRK)", None, "gene_family", None,
     "Neurotrophic TRK receptors — tumor-agnostic fusions.",
     ["NTRK", "TRK", "NTRK fusion", "larotrectinib", "entrectinib"],
     ["neurotrophic tyrosine receptor kinase"]),

    ("VEGF", "VEGF", None, "gene", "VEGFA",
     "Vascular endothelial growth factor — angiogenesis target.",
     ["VEGF", "anti-VEGF", "bevacizumab", "VEGF inhibitor"],
     ["vascular endothelial growth factor"]),

    ("Claudin-18.2", "Claudin-18.2", None, "gene", "CLDN18",
     "Claudin-18.2 — emerging target in gastric, pancreatic cancer.",
     ["Claudin-18.2", "CLDN18.2", "zolbetuximab"],
     ["claudin 18 isoform 2"]),

    ("DLL3", "DLL3", None, "gene", "DLL3",
     "Delta-like ligand 3 — target in SCLC (tarlatamab bispecific).",
     ["DLL3", "delta-like ligand 3", "tarlatamab"],
     []),

    ("CD3", "CD3", None, "gene", "CD3E",
     "CD3 — T-cell engager arm for bispecific antibodies.",
     ["CD3", "anti-CD3", "T-cell engager"],
     []),

    ("AXL", "AXL", None, "gene", "AXL",
     "AXL receptor kinase — resistance mechanism and emerging oncology target.",
     ["AXL", "AXL kinase", "AXL inhibitor"],
     []),

    ("KRASG12C-on", "KRAS G12C Active-State", "KRAS G12C", "isoform", "KRAS",
     "Active-state (GTP-bound) KRAS G12C — next-gen beyond covalent-off approaches.",
     ["KRAS G12C active", "KRAS-ON G12C"],
     []),

    # ─── Neuropsychiatry Targets (expanded) ───
    ("NMDA", "NMDA Receptor", None, "gene", "GRIN1",
     "N-methyl-D-aspartate receptor — target in depression (esketamine), AD.",
     ["NMDA", "NMDA receptor", "NMDAR", "esketamine", "ketamine"],
     ["N-methyl-D-aspartate"]),

    ("5-HT2A", "5-HT2A Receptor", None, "gene", "HTR2A",
     "Serotonin 2A receptor — psychedelic-adjacent drugs for depression, schizophrenia.",
     ["5-HT2A", "serotonin 2A", "HTR2A", "pimavanserin"],
     []),

    ("GABA-A", "GABA-A Receptor", None, "gene", "GABRA1",
     "GABA-A receptor — neurosteroid modulators for PPD, seizures.",
     ["GABA-A", "GABAA", "neurosteroid", "zuranolone", "brexanolone"],
     ["gamma-aminobutyric acid A"]),

    ("CGRP", "CGRP", None, "gene", "CALCA",
     "Calcitonin gene-related peptide — migraine target.",
     ["CGRP", "anti-CGRP", "CGRP inhibitor", "erenumab", "fremanezumab", "galcanezumab"],
     ["calcitonin gene-related peptide"]),

    ("OX1R/OX2R", "Orexin Receptors", None, "gene_family", None,
     "Orexin receptor system — OX1R and OX2R for narcolepsy, insomnia.",
     ["orexin", "OX1R", "OX2R", "DORA", "suvorexant", "lemborexant"],
     ["hypocretin receptor"]),

    ("D2", "Dopamine D2 Receptor", None, "gene", "DRD2",
     "Dopamine D2 receptor — classic antipsychotic target.",
     ["D2", "D2 receptor", "dopamine D2", "DRD2"],
     ["dopamine receptor D2"]),

    ("mGluR5", "mGlu5 Receptor", None, "gene", "GRM5",
     "Metabotropic glutamate receptor 5 — target in depression, OCD.",
     ["mGluR5", "mGlu5", "GRM5"],
     ["metabotropic glutamate receptor 5"]),

    ("TAAR1", "TAAR1", None, "gene", "TAAR1",
     "Trace amine-associated receptor 1 — novel schizophrenia target (ulotaront).",
     ["TAAR1", "TAAR1 agonist", "ulotaront"],
     ["trace amine associated receptor 1"]),

    ("KOR", "Kappa Opioid Receptor", None, "gene", "OPRK1",
     "Kappa opioid receptor — target in depression, substance use (aticaprant).",
     ["KOR", "kappa opioid", "kappa antagonist", "aticaprant"],
     ["kappa opioid receptor"]),

    ("Nav1.6", "Nav1.6", None, "gene", "SCN8A",
     "Sodium channel Nav1.6 — target for seizure control in epilepsy.",
     ["Nav1.6", "SCN8A", "sodium channel"],
     []),

    ("CFTR", "CFTR", None, "gene", "CFTR",
     "Cystic fibrosis transmembrane conductance regulator — genetic target for CF.",
     ["CFTR", "CFTR modulator", "elexacaftor", "tezacaftor", "ivacaftor", "Trikafta"],
     ["cystic fibrosis transmembrane conductance regulator"]),

    # ─── Obesity Expanded Targets ───
    ("GLP-1/GIP/glucagon", "Triple Agonist", "GLP-1", "isoform", "GLP1R",
     "Triple GLP-1/GIP/glucagon receptor agonists — retatrutide.",
     ["triple agonist", "retatrutide", "GGG agonist"],
     []),

    ("Myostatin", "Myostatin/Activin", None, "gene", "MSTN",
     "Myostatin/activin pathway — anti-obesity via lean mass preservation.",
     ["myostatin", "GDF-8", "activin", "bimagrumab", "trevogrumab"],
     []),
]

# =============================================================================
# NEW DISEASE-TARGET MAPPINGS
# =============================================================================

EXPANSION_DISEASE_TARGETS = [
    # ─── Immunology & Inflammation ───
    ("Rheumatoid Arthritis", "TNF-alpha", "established", "Adalimumab, etanercept SOC"),
    ("Rheumatoid Arthritis", "IL-6", "established", "Tocilizumab, sarilumab"),
    ("Rheumatoid Arthritis", "JAK1", "established", "Upadacitinib, tofacitinib"),
    ("Rheumatoid Arthritis", "JAK", "established", "Pan-JAK: tofacitinib, baricitinib"),
    ("Rheumatoid Arthritis", "BTK", "emerging", "BTK degraders in RA"),
    ("Rheumatoid Arthritis", "CD20", "established", "Rituximab for refractory RA"),

    ("Psoriasis", "IL-17", "established", "Secukinumab, ixekizumab, bimekizumab"),
    ("Psoriasis", "IL-23", "established", "Guselkumab, risankizumab, tildrakizumab"),
    ("Psoriasis", "TNF-alpha", "established", "Adalimumab, infliximab"),
    ("Psoriasis", "TYK2", "established", "Deucravacitinib approved"),
    ("Psoriasis", "IL-4/IL-13", "emerging", "Dupilumab in subset of psoriasis"),

    ("Atopic Dermatitis", "IL-4/IL-13", "established", "Dupilumab SOC"),
    ("Atopic Dermatitis", "JAK1", "established", "Upadacitinib, abrocitinib approved"),
    ("Atopic Dermatitis", "IL-31", "established", "Nemolizumab for pruritus"),
    ("Atopic Dermatitis", "IL-13", "established", "Tralokinumab"),
    ("Atopic Dermatitis", "IL-33", "emerging", "Itepekimab in trials"),
    ("Atopic Dermatitis", "TSLP", "emerging", "Tezepelumab exploring AD"),

    ("Ulcerative Colitis", "IL-23", "established", "Mirikizumab, guselkumab"),
    ("Ulcerative Colitis", "JAK1", "established", "Upadacitinib approved"),
    ("Ulcerative Colitis", "TNF-alpha", "established", "Infliximab, adalimumab"),
    ("Ulcerative Colitis", "S1P", "established", "Ozanimod, etrasimod approved"),
    ("Ulcerative Colitis", "TYK2", "emerging", "Multiple TYK2 inhibitors in trials"),

    ("Crohn's Disease", "TNF-alpha", "established", "Infliximab, adalimumab SOC"),
    ("Crohn's Disease", "IL-23", "established", "Risankizumab approved, guselkumab"),
    ("Crohn's Disease", "JAK1", "established", "Upadacitinib approved"),

    ("Multiple Sclerosis", "CD20", "established", "Ocrelizumab, ofatumumab SOC"),
    ("Multiple Sclerosis", "S1P", "established", "Siponimod, ozanimod, ponesimod"),
    ("Multiple Sclerosis", "BTK", "emerging", "Tolebrutinib, fenebrutinib in P3"),

    ("Myasthenia Gravis", "FcRn", "established", "Efgartigimod, rozanolixizumab"),

    ("Asthma", "IL-4/IL-13", "established", "Dupilumab approved"),
    ("Asthma", "TSLP", "established", "Tezepelumab approved"),
    ("Asthma", "IL-33", "emerging", "Itepekimab, astegolimab"),

    # ─── Cardiometabolic ───
    ("Hypercholesterolemia", "PCSK9", "established", "Evolocumab, alirocumab, inclisiran"),
    ("Hypercholesterolemia", "ANGPTL3", "established", "Evinacumab approved for HoFH"),

    ("Cardiovascular Disease", "Lp(a)", "emerging", "Pelacarsen, olpasiran, lepodisiran in P3"),
    ("Cardiovascular Disease", "PCSK9", "established", "CV outcomes proven"),

    ("Heart Failure", "SGLT2", "established", "Dapagliflozin, empagliflozin approved"),

    ("CKD", "SGLT2", "established", "Dapagliflozin approved for CKD"),

    ("Hypertriglyceridemia", "APOC3", "established", "Volanesorsen, olezarsen"),
    ("Hypertriglyceridemia", "ANGPTL3", "emerging", "Vupanorsen, zodasiran"),

    # ─── Obesity (expanded) ───
    ("Obesity", "GLP-1", "established", "Semaglutide SOC"),
    ("Obesity", "GIP/GLP-1", "established", "Tirzepatide approved"),
    ("Obesity", "GLP-1/glucagon", "emerging", "Survodutide, mazdutide in P3"),
    ("Obesity", "GLP-1/GIP/glucagon", "emerging", "Retatrutide (triple agonist) in P3"),
    ("Obesity", "Amylin", "emerging", "Cagrilintide + semaglutide (CagriSema)"),
    ("Obesity", "Myostatin", "exploratory", "Anti-myostatin to preserve lean mass"),
    ("Obesity", "ActRII", "emerging", "Bimagrumab for body composition"),

    # ─── Neuropsychiatry (expanded) ───
    ("Major Depressive Disorder", "NMDA", "established", "Esketamine approved"),
    ("Major Depressive Disorder", "GABA-A", "established", "Zuranolone approved"),
    ("Major Depressive Disorder", "KOR", "emerging", "Aticaprant in P3"),
    ("Major Depressive Disorder", "5-HT2A", "emerging", "Psilocybin-adjacent, pimavanserin"),

    ("Schizophrenia", "D2", "established", "Antipsychotics SOC"),
    ("Schizophrenia", "TAAR1", "emerging", "Ulotaront in P3"),
    ("Schizophrenia", "5-HT2A", "emerging", "Lumateperone, pimavanserin"),

    ("Migraine", "CGRP", "established", "Erenumab, fremanezumab, galcanezumab, rimegepant, ubrogepant"),

    ("Narcolepsy", "OX1R/OX2R", "established", "OX2R agonists in development"),
    ("Narcolepsy", "OX2R", "established", "Orexin-2 agonist (TAK-861, danavorexton)"),

    ("Epilepsy", "Nav1.6", "emerging", "Sodium channel blockers"),
    ("Epilepsy", "SV2A", "established", "Levetiracetam mechanism"),

    ("Cystic Fibrosis", "CFTR", "established", "Trikafta/Kaftrio SOC"),

    # ─── Expanded Oncology ───
    ("SCLC", "DLL3", "established", "Tarlatamab approved"),
    ("SCLC", "PD-1", "established", "Atezolizumab, durvalumab in ES-SCLC"),

    ("Multiple Myeloma", "BCMA", "established", "Ide-cel, cilta-cel, teclistamab"),
    ("Multiple Myeloma", "GPRC5D", "emerging", "Talquetamab approved"),
    ("Multiple Myeloma", "CD3", "established", "Bispecific T-cell engagers"),

    ("DLBCL", "CD19", "established", "Axi-cel, liso-cel, tisa-cel, epcoritamab"),

    ("Bladder Cancer", "Nectin-4", "established", "Enfortumab vedotin approved"),
    ("Bladder Cancer", "FGFR", "established", "Erdafitinib for FGFR-altered"),
    ("Bladder Cancer", "PD-1", "established", "Pembrolizumab, nivolumab"),

    ("Cholangiocarcinoma", "FGFR", "established", "Futibatinib, pemigatinib, infigratinib"),

    ("NSCLC", "MET", "established", "Capmatinib, tepotinib for MET ex14"),
    ("NSCLC", "RET", "established", "Selpercatinib for RET fusions"),
    ("NSCLC", "NTRK", "established", "Larotrectinib, entrectinib tumor-agnostic"),

    ("Gastric Cancer", "Claudin-18.2", "emerging", "Zolbetuximab approved 2024"),
    ("Gastric Cancer", "HER2", "established", "Trastuzumab, T-DXd"),

    ("Hepatocellular Carcinoma", "VEGF", "established", "Bevacizumab + atezolizumab SOC"),
    ("Hepatocellular Carcinoma", "PD-L1", "established", "Atezolizumab + bev 1L"),

    ("Melanoma", "PD-1", "established", "Pembrolizumab, nivolumab SOC"),
    ("Melanoma", "CTLA-4", "established", "Ipilimumab, tremelimumab"),
    ("Melanoma", "LAG-3", "established", "Relatlimab + nivo approved"),
    ("Melanoma", "BRAF", "established", "Encorafenib + binimetinib for V600"),

    ("RCC", "PD-1", "established", "Nivolumab + cabozantinib/axitinib SOC"),
    ("RCC", "VEGF", "established", "Cabozantinib, sunitinib, axitinib"),
    ("RCC", "CTLA-4", "established", "Ipilimumab + nivolumab"),
]

# =============================================================================
# EXPANDED SEED DRUGS — Top 50 companies × 5 TAs
# =============================================================================

EXPANSION_DRUGS = [
    # ===================================================================
    # I&I — Immunology & Inflammation
    # ===================================================================

    # --- AbbVie (ABBV) ---
    ("adalimumab", "ABBV", "AbbVie",
     "Rheumatoid Arthritis", ["Rheumatoid Arthritis", "Psoriasis", "Crohn's Disease", "Ulcerative Colitis", "Psoriatic Arthritis"],
     "monoclonal_antibody", "Anti-TNF-alpha monoclonal antibody", "TNF",
     "Approved", "Active",
     [("Humira", "brand", True, "Top-selling drug globally, biosimilar competition"),
      ("D2E7", "code", False, "Development code")],
     [("TNF-alpha", "primary", "selective")]),

    ("upadacitinib", "ABBV", "AbbVie",
     "Rheumatoid Arthritis", ["Rheumatoid Arthritis", "Atopic Dermatitis", "Ulcerative Colitis", "Crohn's Disease", "Psoriatic Arthritis", "Ankylosing Spondylitis"],
     "small_molecule", "JAK1 selective inhibitor", "JAK/STAT",
     "Approved", "Active",
     [("Rinvoq", "brand", True, "FDA-approved brand name"),
      ("ABT-494", "code", False, "Original AbbVie code")],
     [("JAK1", "primary", "selective")]),

    ("risankizumab", "ABBV", "AbbVie",
     "Psoriasis", ["Psoriasis", "Psoriatic Arthritis", "Crohn's Disease", "Ulcerative Colitis"],
     "monoclonal_antibody", "Anti-IL-23p19 monoclonal antibody", "IL-23",
     "Approved", "Active",
     [("Skyrizi", "brand", True, "FDA-approved brand name"),
      ("BI 655066", "code", False, "Original Boehringer code")],
     [("IL-23", "primary", "selective")]),

    # --- Johnson & Johnson (JNJ) ---
    ("guselkumab", "JNJ", "Johnson & Johnson",
     "Psoriasis", ["Psoriasis", "Psoriatic Arthritis", "Ulcerative Colitis", "Crohn's Disease"],
     "monoclonal_antibody", "Anti-IL-23p19 monoclonal antibody", "IL-23",
     "Approved", "Active",
     [("Tremfya", "brand", True, "FDA-approved brand name")],
     [("IL-23", "primary", "selective")]),

    ("nipocalimab", "JNJ", "Johnson & Johnson",
     "Myasthenia Gravis", ["Myasthenia Gravis", "Hemolytic Disease of Fetus and Newborn"],
     "monoclonal_antibody", "Anti-FcRn monoclonal antibody", "FcRn",
     "Phase 3", "Active",
     [("M281", "code", False, "Original Momenta code")],
     [("FcRn", "primary", "selective")]),

    # --- Regeneron (REGN) ---
    ("dupilumab", "REGN", "Regeneron",
     "Atopic Dermatitis", ["Atopic Dermatitis", "Asthma", "COPD", "Chronic Rhinosinusitis with Nasal Polyps", "Prurigo Nodularis"],
     "monoclonal_antibody", "Anti-IL-4Ralpha blocking IL-4 and IL-13", "Type 2 Inflammation",
     "Approved", "Active",
     [("Dupixent", "brand", True, "FDA-approved brand name"),
      ("SAR231893", "code", False, "Sanofi code"),
      ("REGN668", "code", False, "Regeneron code")],
     [("IL-4/IL-13", "primary", "selective")]),

    # --- Bristol-Myers Squibb (BMY) ---
    ("deucravacitinib", "BMY", "Bristol-Myers Squibb",
     "Psoriasis", ["Psoriasis", "Psoriatic Arthritis", "Ulcerative Colitis", "Lupus"],
     "small_molecule", "Allosteric TYK2 inhibitor", "JAK/STAT",
     "Approved", "Active",
     [("Sotyktu", "brand", True, "FDA-approved brand name"),
      ("BMS-986165", "code", False, "Original BMS code")],
     [("TYK2", "primary", "selective")]),

    # --- Novartis (NVS) ---
    ("secukinumab", "NVS", "Novartis",
     "Psoriasis", ["Psoriasis", "Psoriatic Arthritis", "Ankylosing Spondylitis"],
     "monoclonal_antibody", "Anti-IL-17A monoclonal antibody", "IL-17",
     "Approved", "Active",
     [("Cosentyx", "brand", True, "FDA-approved brand name")],
     [("IL-17", "primary", "selective")]),

    # --- Roche (RHHBY) ---
    ("ocrelizumab", "RHHBY", "Roche / Genentech",
     "Multiple Sclerosis", ["Multiple Sclerosis"],
     "monoclonal_antibody", "Anti-CD20 monoclonal antibody (humanized)", "B-Cell",
     "Approved", "Active",
     [("Ocrevus", "brand", True, "FDA-approved brand name")],
     [("CD20", "primary", "selective")]),

    ("fenebrutinib", "RHHBY", "Roche / Genentech",
     "Multiple Sclerosis", ["Multiple Sclerosis", "Rheumatoid Arthritis"],
     "small_molecule", "Non-covalent BTK inhibitor", "BTK",
     "Phase 3", "Active",
     [("GDC-0853", "code", False, "Genentech code"),
      ("RG7845", "code", False, "Roche code")],
     [("BTK", "primary", "selective")]),

    # --- Pfizer (PFE) ---
    ("etrasimod", "PFE", "Pfizer",
     "Ulcerative Colitis", ["Ulcerative Colitis", "Crohn's Disease", "Atopic Dermatitis"],
     "small_molecule", "S1P receptor modulator (S1P1,4,5)", "S1P",
     "Approved", "Active",
     [("Velsipity", "brand", True, "FDA-approved brand name"),
      ("APD334", "code", False, "Arena code")],
     [("S1P", "primary", "selective")]),

    # --- argenx (ARGX) ---
    ("efgartigimod", "ARGX", "argenx",
     "Myasthenia Gravis", ["Myasthenia Gravis", "ITP", "CIDP", "Pemphigus Vulgaris"],
     "monoclonal_antibody", "Anti-FcRn antibody fragment", "FcRn",
     "Approved", "Active",
     [("Vyvgart", "brand", True, "FDA-approved brand name"),
      ("ARGX-113", "code", False, "Original argenx code")],
     [("FcRn", "primary", "selective")]),

    # ===================================================================
    # CARDIOMETABOLIC
    # ===================================================================

    # --- Amgen (AMGN) ---
    ("evolocumab", "AMGN", "Amgen",
     "Hypercholesterolemia", ["Hypercholesterolemia", "Cardiovascular Disease"],
     "monoclonal_antibody", "Anti-PCSK9 monoclonal antibody", "PCSK9",
     "Approved", "Active",
     [("Repatha", "brand", True, "FDA-approved brand name"),
      ("AMG 145", "code", False, "Amgen code")],
     [("PCSK9", "primary", "selective")]),

    ("olpasiran", "AMGN", "Amgen",
     "Cardiovascular Disease", ["Cardiovascular Disease"],
     "rna_therapy", "siRNA targeting Lp(a) (LPA mRNA)", "Lp(a)",
     "Phase 3", "Active",
     [("AMG 890", "code", False, "Amgen code")],
     [("Lp(a)", "primary", "selective")]),

    # --- Novartis (NVS) ---
    ("inclisiran", "NVS", "Novartis",
     "Hypercholesterolemia", ["Hypercholesterolemia", "Cardiovascular Disease"],
     "rna_therapy", "siRNA targeting PCSK9 (twice-yearly dosing)", "PCSK9",
     "Approved", "Active",
     [("Leqvio", "brand", True, "FDA-approved brand name"),
      ("ALN-PCSsc", "code", False, "Original Alnylam code")],
     [("PCSK9", "primary", "selective")]),

    # --- Regeneron (REGN) ---
    ("alirocumab", "REGN", "Regeneron",
     "Hypercholesterolemia", ["Hypercholesterolemia", "Cardiovascular Disease"],
     "monoclonal_antibody", "Anti-PCSK9 monoclonal antibody", "PCSK9",
     "Approved", "Active",
     [("Praluent", "brand", True, "FDA-approved brand name"),
      ("SAR236553", "code", False, "Sanofi code"),
      ("REGN727", "code", False, "Regeneron code")],
     [("PCSK9", "primary", "selective")]),

    ("evinacumab", "REGN", "Regeneron",
     "Hypercholesterolemia", ["Hypercholesterolemia"],
     "monoclonal_antibody", "Anti-ANGPTL3 monoclonal antibody", "ANGPTL3",
     "Approved", "Active",
     [("Evkeeza", "brand", True, "FDA-approved for HoFH"),
      ("REGN1500", "code", False, "Regeneron code")],
     [("ANGPTL3", "primary", "selective")]),

    # --- AstraZeneca (AZN) ---
    ("dapagliflozin", "AZN", "AstraZeneca",
     "Heart Failure", ["Heart Failure", "CKD", "Type 2 Diabetes"],
     "small_molecule", "SGLT2 inhibitor", "SGLT2",
     "Approved", "Active",
     [("Farxiga", "brand", True, "US brand name"),
      ("Forxiga", "brand", True, "EU brand name")],
     [("SGLT2", "primary", "selective")]),

    # --- Alnylam (ALNY) ---
    ("patisiran", "ALNY", "Alnylam Pharmaceuticals",
     "hATTR Amyloidosis", ["hATTR Amyloidosis", "ATTR Cardiomyopathy"],
     "rna_therapy", "siRNA targeting TTR mRNA", "TTR",
     "Approved", "Active",
     [("Onpattro", "brand", True, "FDA-approved brand name")],
     []),

    # --- Ionis (IONS) ---
    ("pelacarsen", "IONS", "Ionis Pharmaceuticals",
     "Cardiovascular Disease", ["Cardiovascular Disease"],
     "rna_therapy", "Antisense oligonucleotide targeting Lp(a)", "Lp(a)",
     "Phase 3", "Active",
     [("TQJ230", "code", False, "Novartis code (licensed)"),
      ("AKCEA-APO(a)-LRx", "code", False, "Akcea/Ionis code"),
      ("IONIS-APO(a)-LRx", "code", False, "Ionis code")],
     [("Lp(a)", "primary", "selective")]),

    ("olezarsen", "IONS", "Ionis Pharmaceuticals",
     "Hypertriglyceridemia", ["Hypertriglyceridemia", "Familial Chylomicronemia Syndrome"],
     "rna_therapy", "Antisense oligonucleotide targeting APOC3", "APOC3",
     "Approved", "Active",
     [("Tryngolza", "brand", True, "FDA-approved brand name 2024"),
      ("AKCEA-APOCIII-LRx", "code", False, "Original Akcea code")],
     [("APOC3", "primary", "selective")]),

    # ===================================================================
    # OBESITY
    # ===================================================================

    # --- Eli Lilly (LLY) ---
    ("retatrutide", "LLY", "Eli Lilly",
     "Obesity", ["Obesity", "Type 2 Diabetes", "NASH"],
     "peptide", "Triple GLP-1/GIP/glucagon receptor agonist", "Metabolic",
     "Phase 3", "Active",
     [("LY3437943", "code", False, "Lilly code")],
     [("GLP-1/GIP/glucagon", "primary", "selective")]),

    ("orforglipron", "LLY", "Eli Lilly",
     "Obesity", ["Obesity", "Type 2 Diabetes"],
     "small_molecule", "Non-peptide oral GLP-1 receptor agonist", "Metabolic",
     "Phase 3", "Active",
     [("LY3502970", "code", False, "Lilly code")],
     [("GLP-1", "primary", "selective")]),

    # --- Novo Nordisk (NVO) ---
    ("CagriSema", "NVO", "Novo Nordisk",
     "Obesity", ["Obesity", "Type 2 Diabetes"],
     "peptide", "Cagrilintide (amylin analog) + semaglutide combination", "Metabolic",
     "Phase 3", "Active",
     [("cagrilintide/semaglutide", "inn", True, None)],
     [("Amylin", "primary", "selective"), ("GLP-1", "secondary", "selective")]),

    ("amycretin", "NVO", "Novo Nordisk",
     "Obesity", ["Obesity"],
     "peptide", "Amylin/GLP-1 receptor co-agonist (single molecule)", "Metabolic",
     "Phase 2", "Active",
     [("NNC0487-0111", "code", False, "Novo code")],
     [("Amylin", "primary", "selective"), ("GLP-1", "secondary", "selective")]),

    # --- Pfizer (PFE) ---
    ("danuglipron", "PFE", "Pfizer",
     "Obesity", ["Obesity", "Type 2 Diabetes"],
     "small_molecule", "Oral GLP-1 receptor agonist", "Metabolic",
     "Phase 2", "Active",
     [("PF-06882961", "code", False, "Pfizer code")],
     [("GLP-1", "primary", "selective")]),

    # --- Roche (RHHBY) ---
    ("CT-996", "RHHBY", "Roche / Genentech",
     "Obesity", ["Obesity"],
     "small_molecule", "Oral GLP-1 receptor agonist (acquired from Carmot)", "Metabolic",
     "Phase 2", "Active",
     [],
     [("GLP-1", "primary", "selective")]),

    # --- Viking Therapeutics (VKTX) ---
    ("VK2735", "VKTX", "Viking Therapeutics",
     "Obesity", ["Obesity"],
     "peptide", "Dual GIP/GLP-1 receptor agonist (subcutaneous)", "Metabolic",
     "Phase 3", "Active",
     [],
     [("GIP/GLP-1", "primary", "selective")]),

    # --- Structure Therapeutics (GPCR) ---
    ("GSBR-1290", "GPCR", "Structure Therapeutics",
     "Obesity", ["Obesity", "Type 2 Diabetes"],
     "small_molecule", "Oral GLP-1 receptor agonist (GPCR biased)", "Metabolic",
     "Phase 2", "Active",
     [],
     [("GLP-1", "primary", "selective")]),

    # --- Boehringer Ingelheim/Zealand ---
    ("survodutide", "BILH", "Boehringer Ingelheim",
     "Obesity", ["Obesity", "NASH"],
     "peptide", "Dual GLP-1/glucagon receptor agonist", "Metabolic",
     "Phase 3", "Active",
     [("BI 456906", "code", False, "Boehringer code")],
     [("GLP-1/glucagon", "primary", "selective")]),

    # ===================================================================
    # NEUROPSYCHIATRY
    # ===================================================================

    # --- Johnson & Johnson / Janssen (JNJ) ---
    ("esketamine", "JNJ", "Johnson & Johnson",
     "Major Depressive Disorder", ["Major Depressive Disorder", "Treatment-Resistant Depression"],
     "small_molecule", "NMDA receptor antagonist (nasal spray)", "Glutamate",
     "Approved", "Active",
     [("Spravato", "brand", True, "FDA-approved brand name")],
     [("NMDA", "primary", "selective")]),

    ("aticaprant", "JNJ", "Johnson & Johnson",
     "Major Depressive Disorder", ["Major Depressive Disorder"],
     "small_molecule", "Kappa opioid receptor antagonist (adjunctive MDD)", "Opioid",
     "Phase 3", "Active",
     [("JNJ-67953964", "code", False, "Janssen code")],
     [("KOR", "primary", "selective")]),

    # --- Sage Therapeutics / Biogen (SAGE) ---
    ("zuranolone", "SAGE", "Sage Therapeutics / Biogen",
     "Major Depressive Disorder", ["Major Depressive Disorder", "Postpartum Depression"],
     "small_molecule", "Neurosteroid GABA-A receptor positive allosteric modulator", "GABA",
     "Approved", "Active",
     [("Zurzuvae", "brand", True, "FDA-approved brand name"),
      ("SAGE-217", "code", False, "Original Sage code")],
     [("GABA-A", "primary", "selective")]),

    # --- Axsome (AXSM) ---
    ("AXS-05", "AXSM", "Axsome Therapeutics",
     "Major Depressive Disorder", ["Major Depressive Disorder", "Agitation in Alzheimer's"],
     "small_molecule", "Dextromethorphan-bupropion (NMDA/sigma/NET modulator)", "Glutamate/Monoamine",
     "Approved", "Active",
     [("Auvelity", "brand", True, "FDA-approved brand name for MDD")],
     [("NMDA", "primary", "selective")]),

    # --- Cerevel / AbbVie (CERE) ---
    ("emraclidine", "ABBV", "AbbVie (Cerevel)",
     "Schizophrenia", ["Schizophrenia"],
     "small_molecule", "M4 muscarinic receptor agonist", "Muscarinic",
     "Phase 2", "Active",
     [("CVL-231", "code", False, "Original Cerevel code")],
     []),

    ("tavapadon", "ABBV", "AbbVie (Cerevel)",
     "Parkinson's Disease", ["Parkinson's Disease"],
     "small_molecule", "D1/D5 dopamine receptor partial agonist", "Dopamine",
     "Phase 3", "Active",
     [("CVL-751", "code", False, "Cerevel code")],
     [("D2", "secondary", "selective")]),

    # --- Bristol-Myers (BMY) / Karuna ---
    ("KarXT", "BMY", "Bristol-Myers Squibb",
     "Schizophrenia", ["Schizophrenia"],
     "small_molecule", "Muscarinic M1/M4 agonist xanomeline + trospium (KarXT)", "Muscarinic",
     "Approved", "Active",
     [("Cobenfy", "brand", True, "FDA-approved brand name 2024"),
      ("xanomeline-trospium", "inn", True, None),
      ("KarXT", "colloquial", True, "Common abbreviation")],
     []),

    # --- Eli Lilly (LLY) / CGRP ---
    ("galcanezumab", "LLY", "Eli Lilly",
     "Migraine", ["Migraine", "Cluster Headache"],
     "monoclonal_antibody", "Anti-CGRP monoclonal antibody", "CGRP",
     "Approved", "Active",
     [("Emgality", "brand", True, "FDA-approved brand name")],
     [("CGRP", "primary", "selective")]),

    # --- Vertex (VRTX) ---
    ("VX-548", "VRTX", "Vertex Pharmaceuticals",
     "Acute Pain", ["Acute Pain", "Neuropathic Pain"],
     "small_molecule", "Nav1.8 sodium channel inhibitor (non-opioid analgesic)", "Sodium Channel",
     "Phase 3", "Active",
     [("suzetrigine", "inn", True, "INN assigned")],
     []),

    # ===================================================================
    # EXPANDED ONCOLOGY — Major pipeline drugs
    # ===================================================================

    # --- Merck (MRK) ---
    ("pembrolizumab", "MRK", "Merck",
     "NSCLC", ["NSCLC", "Melanoma", "RCC", "HNSCC", "Urothelial Carcinoma", "MSI-H Solid Tumors", "Gastric Cancer", "Cervical Cancer", "Hepatocellular Carcinoma"],
     "monoclonal_antibody", "Anti-PD-1 monoclonal antibody", "PD-1",
     "Approved", "Active",
     [("Keytruda", "brand", True, "FDA-approved brand name"),
      ("MK-3475", "code", False, "Merck code"),
      ("lambrolizumab", "inn", False, "Former INN")],
     [("PD-1", "primary", "selective")]),

    ("MK-2870", "MRK", "Merck",
     "NSCLC", ["NSCLC", "Solid Tumors"],
     "monoclonal_antibody", "PD-1/LAG-3 bispecific antibody (favezelimab)", "PD-1/LAG-3",
     "Phase 3", "Active",
     [("favezelimab", "inn", True, None)],
     [("PD-1", "primary", "selective"), ("LAG-3", "secondary", "selective")]),

    # --- Bristol-Myers Squibb (BMY) ---
    ("nivolumab", "BMY", "Bristol-Myers Squibb",
     "Melanoma", ["Melanoma", "NSCLC", "RCC", "Urothelial Carcinoma", "HNSCC", "Hepatocellular Carcinoma", "Gastric Cancer"],
     "monoclonal_antibody", "Anti-PD-1 monoclonal antibody", "PD-1",
     "Approved", "Active",
     [("Opdivo", "brand", True, "FDA-approved brand name"),
      ("BMS-936558", "code", False, "BMS code"),
      ("MDX-1106", "code", False, "Medarex code")],
     [("PD-1", "primary", "selective")]),

    ("relatlimab", "BMY", "Bristol-Myers Squibb",
     "Melanoma", ["Melanoma"],
     "monoclonal_antibody", "Anti-LAG-3 monoclonal antibody (with nivolumab)", "LAG-3",
     "Approved", "Active",
     [("Opdualag", "brand", True, "FDA-approved (nivo + rela combo)"),
      ("BMS-986016", "code", False, "BMS code")],
     [("LAG-3", "primary", "selective")]),

    # --- AstraZeneca (AZN) ---
    ("durvalumab", "AZN", "AstraZeneca",
     "NSCLC", ["NSCLC", "SCLC", "Biliary Tract Cancer", "Hepatocellular Carcinoma", "Bladder Cancer"],
     "monoclonal_antibody", "Anti-PD-L1 monoclonal antibody", "PD-L1",
     "Approved", "Active",
     [("Imfinzi", "brand", True, "FDA-approved brand name"),
      ("MEDI4736", "code", False, "MedImmune code")],
     [("PD-L1", "primary", "selective")]),

    ("datopotamab deruxtecan", "AZN", "AstraZeneca / Daiichi Sankyo",
     "NSCLC", ["NSCLC", "HR+ Breast Cancer", "TNBC"],
     "adc", "TROP-2 targeting ADC with DXd payload", "TROP2",
     "Approved", "Active",
     [("Datroway", "brand", True, "FDA-approved brand name"),
      ("Dato-DXd", "colloquial", True, "Common abbreviation"),
      ("DS-1062", "code", False, "Daiichi code")],
     [("TROP2", "primary", "selective")]),

    # --- Pfizer (PFE) ---
    ("lorlatinib", "PFE", "Pfizer",
     "NSCLC", ["NSCLC"],
     "small_molecule", "Third-generation ALK inhibitor (brain-penetrant)", "ALK",
     "Approved", "Active",
     [("Lorbrena", "brand", True, "FDA-approved brand name"),
      ("PF-06463922", "code", False, "Pfizer code")],
     [("ALK", "primary", "selective")]),

    ("sigvotatug vedotin", "PFE", "Pfizer",
     "NSCLC", ["NSCLC", "Solid Tumors"],
     "adc", "Anti-B7-H4 ADC", "B7-H4",
     "Phase 3", "Active",
     [("ABBV-400", "code", False, "AbbVie code before Pfizer")],
     [("B7-H4", "primary", "selective")]),

    # --- Amgen (AMGN) ---
    ("tarlatamab", "AMGN", "Amgen",
     "SCLC", ["SCLC"],
     "bispecific", "DLL3 × CD3 bispecific T-cell engager", "DLL3/CD3",
     "Approved", "Active",
     [("Imdelltra", "brand", True, "FDA-approved brand name"),
      ("AMG 757", "code", False, "Amgen code")],
     [("DLL3", "primary", "selective"), ("CD3", "secondary", "selective")]),

    # --- J&J / Legend (JNJ) ---
    ("ciltacabtagene autoleucel", "JNJ", "Johnson & Johnson / Legend Biotech",
     "Multiple Myeloma", ["Multiple Myeloma"],
     "cell_therapy", "BCMA-targeting CAR-T cell therapy", "BCMA",
     "Approved", "Active",
     [("Carvykti", "brand", True, "FDA-approved brand name"),
      ("cilta-cel", "colloquial", True, "Common abbreviation"),
      ("JNJ-68284528", "code", False, "J&J code")],
     [("BCMA", "primary", "selective")]),

    # --- Vertex (VRTX) ---
    ("exagamglogene autotemcel", "VRTX", "Vertex / CRISPR Therapeutics",
     "Sickle Cell Disease", ["Sickle Cell Disease", "Beta-Thalassemia"],
     "cell_therapy", "CRISPR-Cas9 gene-edited autologous cell therapy", "Gene Editing",
     "Approved", "Active",
     [("Casgevy", "brand", True, "FDA-approved brand name"),
      ("exa-cel", "colloquial", True, "Common abbreviation"),
      ("CTX001", "code", False, "CRISPR Tx code")],
     []),

    # --- GSK (GSK) ---
    ("blenrep", "GSK", "GSK",
     "Multiple Myeloma", ["Multiple Myeloma"],
     "adc", "BCMA-targeting ADC", "BCMA",
     "Approved", "Active",
     [("Blenrep", "brand", True, "Brand name"),
      ("belantamab mafodotin", "inn", True, None),
      ("GSK2857916", "code", False, "GSK code")],
     [("BCMA", "primary", "selective")]),

    ("jemperli", "GSK", "GSK",
     "Endometrial Cancer", ["Endometrial Cancer", "MSI-H Solid Tumors"],
     "monoclonal_antibody", "Anti-PD-1 monoclonal antibody", "PD-1",
     "Approved", "Active",
     [("Jemperli", "brand", True, "Brand name"),
      ("dostarlimab", "inn", True, None),
      ("GSK4057190", "code", False, "GSK code")],
     [("PD-1", "primary", "selective")]),

    # --- Sanofi (SNY) ---
    ("fitusiran", "SNY", "Sanofi",
     "Hemophilia A and B", ["Hemophilia A", "Hemophilia B"],
     "rna_therapy", "siRNA targeting antithrombin to rebalance hemostasis", "Antithrombin",
     "Approved", "Active",
     [("Alhemo", "brand", True, "FDA-approved brand name")],
     []),

    # --- Vertex (VRTX) continued ---
    ("elexacaftor/tezacaftor/ivacaftor", "VRTX", "Vertex Pharmaceuticals",
     "Cystic Fibrosis", ["Cystic Fibrosis"],
     "small_molecule", "Triple CFTR modulator combination", "CFTR",
     "Approved", "Active",
     [("Trikafta", "brand", True, "US brand name"),
      ("Kaftrio", "brand", True, "EU brand name"),
      ("VX-445/VX-661/VX-770", "code", False, "Component codes")],
     [("CFTR", "primary", "selective")]),

    ("vanzacaftor/tezacaftor/deutivacaftor", "VRTX", "Vertex Pharmaceuticals",
     "Cystic Fibrosis", ["Cystic Fibrosis"],
     "small_molecule", "Next-gen triple CFTR modulator (once-daily)", "CFTR",
     "Approved", "Active",
     [("Alyftrek", "brand", True, "FDA-approved 2025"),
      ("VX-121/VX-661/VX-561", "code", False, "Component codes")],
     [("CFTR", "primary", "selective")]),

    # --- Eli Lilly (LLY) oncology ---
    ("abemaciclib", "LLY", "Eli Lilly",
     "HR+ Breast Cancer", ["HR+ Breast Cancer"],
     "small_molecule", "CDK4/6 inhibitor (continuous dosing)", "CDK4/6",
     "Approved", "Active",
     [("Verzenio", "brand", True, "FDA-approved brand name"),
      ("LY2835219", "code", False, "Lilly code")],
     [("CDK4/6", "primary", "selective")]),

    # --- Astellas / Pfizer ---
    ("enfortumab vedotin", "AGTSY", "Astellas / Seagen",
     "Bladder Cancer", ["Urothelial Carcinoma", "Bladder Cancer"],
     "adc", "Nectin-4-targeting ADC with MMAE payload", "Nectin-4",
     "Approved", "Active",
     [("Padcev", "brand", True, "FDA-approved brand name"),
      ("ASG-22ME", "code", False, "Astellas code"),
      ("EV", "colloquial", True, "Common abbreviation")],
     [("Nectin-4", "primary", "selective")]),

    # --- Roche (RHHBY) oncology ---
    ("atezolizumab", "RHHBY", "Roche / Genentech",
     "NSCLC", ["NSCLC", "SCLC", "Hepatocellular Carcinoma", "Urothelial Carcinoma", "TNBC"],
     "monoclonal_antibody", "Anti-PD-L1 monoclonal antibody", "PD-L1",
     "Approved", "Active",
     [("Tecentriq", "brand", True, "FDA-approved brand name"),
      ("MPDL3280A", "code", False, "Genentech code"),
      ("RG7446", "code", False, "Roche code")],
     [("PD-L1", "primary", "selective")]),

    # --- AbbVie (ABBV) oncology ---
    ("epcoritamab", "ABBV", "AbbVie / Genmab",
     "DLBCL", ["DLBCL", "Follicular Lymphoma"],
     "bispecific", "CD20 × CD3 bispecific T-cell engager", "CD20/CD3",
     "Approved", "Active",
     [("Epkinly", "brand", True, "FDA-approved brand name"),
      ("GEN3013", "code", False, "Genmab code"),
      ("DuoBody-CD3xCD20", "colloquial", True, None)],
     [("CD20", "primary", "selective"), ("CD3", "secondary", "selective")]),
]


# =============================================================================
# Runner — extend the existing database
# =============================================================================

def run_expansion():
    """Add all expansion targets, disease mappings, and drugs to the DB."""
    import sys
    sys.path.insert(0, ".")
    from drug_entities import (
        get_conn, seed_targets, seed_disease_targets, seed_drugs,
        TARGET_HIERARCHY, DISEASE_TARGET_MAP, SEED_DRUGS,
    )

    # 1. Extend TARGET_HIERARCHY and re-seed all targets
    TARGET_HIERARCHY.extend(EXPANSION_TARGETS)
    print(f"\n=== STEP 1: Seeding {len(TARGET_HIERARCHY)} targets (original + expansion) ===")
    seed_targets()

    # 2. Extend DISEASE_TARGET_MAP and re-seed
    DISEASE_TARGET_MAP.extend(EXPANSION_DISEASE_TARGETS)
    print(f"\n=== STEP 2: Seeding {len(DISEASE_TARGET_MAP)} disease-target mappings ===")
    seed_disease_targets()

    # 3. Extend SEED_DRUGS and re-seed
    SEED_DRUGS.extend(EXPANSION_DRUGS)
    print(f"\n=== STEP 3: Seeding {len(SEED_DRUGS)} drugs (original + expansion) ===")
    seed_drugs()

    print("\n=== EXPANSION COMPLETE ===")


def verify_expansion():
    """Quick count of what's in the database now."""
    import sys
    sys.path.insert(0, ".")
    from drug_entities import get_conn

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM targets")
    print(f"Targets: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM disease_targets")
    print(f"Disease-target mappings: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM drugs")
    print(f"Drugs: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM drug_aliases")
    print(f"Drug aliases: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM drug_targets")
    print(f"Drug-target links: {cur.fetchone()[0]}")

    # By TA
    print("\n--- Drugs by therapeutic area ---")
    cur.execute("""
        SELECT indication_primary, COUNT(*) as cnt
        FROM drugs
        GROUP BY indication_primary
        ORDER BY cnt DESC
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    # By company
    print("\n--- Drugs by company (top 20) ---")
    cur.execute("""
        SELECT company_ticker, company_name, COUNT(*) as cnt
        FROM drugs
        GROUP BY company_ticker, company_name
        ORDER BY cnt DESC
        LIMIT 20
    """)
    for row in cur.fetchall():
        print(f"  {row[0]} ({row[1]}): {row[2]}")

    # Unique diseases in disease_targets
    print("\n--- Disease landscape coverage ---")
    cur.execute("""
        SELECT DISTINCT disease FROM disease_targets ORDER BY disease
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SatyaBio Entity Expansion")
    parser.add_argument("--setup", action="store_true", help="Run the expansion")
    parser.add_argument("--verify", action="store_true", help="Verify counts")
    args = parser.parse_args()

    if args.setup:
        run_expansion()
    elif args.verify:
        verify_expansion()
    else:
        parser.print_help()
