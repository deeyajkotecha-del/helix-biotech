"""
Static pages for SatyaBio - Companies, Targets, KOL Finder
Generated from cli/src/commands/serve.ts data
"""

from datetime import datetime

# Company data - 145 XBI companies in 11 categories
COMPANIES = [
    # Large Cap Biotech
    {"ticker": "GILD", "name": "Gilead Sciences", "platform": "Small Molecule", "description": "HIV, Oncology, Liver. Key products: Biktarvy, Trodelvy, Livdelzi.", "market_cap": "$95B+", "pipeline": "50+", "phase3": "15+", "approved": "25+", "catalyst": "Lenacapavir HIV data (2026)", "tags": ["HIV", "Oncology", "Liver"], "category": "largecap"},
    {"ticker": "AMGN", "name": "Amgen", "platform": "Biologics", "description": "Oncology, I&I, Bone. Key products: Repatha, Prolia, Lumakras.", "market_cap": "$150B+", "pipeline": "40+", "phase3": "10+", "approved": "20+", "catalyst": "MariTide obesity Ph3 (2026)", "tags": ["Oncology", "I&I", "Bone"], "category": "largecap"},
    {"ticker": "VRTX", "name": "Vertex Pharmaceuticals", "platform": "Small Molecule", "description": "Rare Disease (CF), Pain, Gene Therapy. Key products: Trikafta, JOURNAVX, Casgevy.", "market_cap": "$120B+", "pipeline": "20+", "phase3": "5", "approved": "5", "catalyst": "VX-548 pain Ph3 (2026)", "tags": ["Rare Disease", "Pain", "Gene Therapy"], "category": "largecap"},
    {"ticker": "REGN", "name": "Regeneron Pharmaceuticals", "platform": "Antibody", "description": "I&I, Ophthalmology, Oncology. Key products: Dupixent, EYLEA HD, Libtayo.", "market_cap": "$90B+", "pipeline": "35+", "phase3": "10+", "approved": "8", "catalyst": "Dupixent COPD Ph3 (2026)", "tags": ["I&I", "Ophthalmology", "Oncology"], "category": "largecap"},
    {"ticker": "BIIB", "name": "Biogen", "platform": "Antibody", "description": "Neuropsychiatry. Key products: Leqembi, Spinraza, Tysabri.", "market_cap": "$25B", "pipeline": "20+", "phase3": "5", "approved": "8", "catalyst": "Leqembi expansion (2026)", "tags": ["Neuropsychiatry", "MS", "SMA"], "category": "largecap"},
    {"ticker": "ABBV", "name": "AbbVie", "platform": "Small Molecule", "description": "I&I, Oncology, Neuro. Key products: Humira, Skyrizi, Rinvoq.", "market_cap": "$300B+", "pipeline": "50+", "phase3": "15+", "approved": "30+", "catalyst": "Skyrizi/Rinvoq growth (2026)", "tags": ["I&I", "Oncology", "Neuro"], "category": "largecap"},
    {"ticker": "BMRN", "name": "BioMarin Pharmaceutical", "platform": "Enzyme", "description": "Rare Disease. Key products: Voxzogo, Palynziq, Roctavian.", "market_cap": "$12B", "pipeline": "10+", "phase3": "2", "approved": "7", "catalyst": "Roctavian expansion (2026)", "tags": ["Rare Disease", "Enzyme"], "category": "largecap"},

    # Platform / Genetic Medicines
    {"ticker": "ALNY", "name": "Alnylam Pharmaceuticals", "platform": "RNAi", "description": "Rare Disease (RNAi). Key products: Amvuttra, Onpattro, Givlaari.", "market_cap": "$28.5B", "pipeline": "12", "phase3": "3", "approved": "5", "catalyst": "Vutrisiran ATTR-CM (2026)", "tags": ["Rare Disease", "RNAi", "Cardiometabolic"], "category": "platform"},
    {"ticker": "MRNA", "name": "Moderna", "platform": "mRNA", "description": "Vaccines, Oncology, Rare. COVID/RSV vaccines platform.", "market_cap": "$15B", "pipeline": "45+", "phase3": "8", "approved": "2", "catalyst": "mRNA-1283 COVID (2026)", "tags": ["Vaccines", "Oncology", "Rare Disease"], "category": "platform"},
    {"ticker": "IONS", "name": "Ionis Pharmaceuticals", "platform": "Antisense", "description": "Neuro, Cardio, Rare. Key products: SPINRAZA, WAINUA.", "market_cap": "$7.8B", "pipeline": "40+", "phase3": "5", "approved": "4", "catalyst": "Olezarsen sNDA (2026)", "tags": ["Neuro", "Cardio", "Rare"], "category": "platform"},
    {"ticker": "ARWR", "name": "Arrowhead Pharmaceuticals", "platform": "RNAi", "description": "Liver, Cardio, Pulmonary. Key product: Plozasiran.", "market_cap": "$4.2B", "pipeline": "15", "phase3": "3", "approved": "1", "catalyst": "ARO-INHBE obesity (2026)", "tags": ["Liver", "Cardio", "Pulmonary"], "category": "platform"},
    {"ticker": "CRSP", "name": "CRISPR Therapeutics", "platform": "Gene Editing", "description": "Rare Disease (Gene Editing). Key product: Casgevy.", "market_cap": "$3.5B", "pipeline": "8", "phase3": "2", "approved": "1", "catalyst": "CTX112 CAR-T (2026)", "tags": ["Rare Disease", "Gene Editing", "Hematology"], "category": "platform"},
    {"ticker": "RNA", "name": "Avidity Biosciences", "platform": "AOC", "description": "Neuromuscular, Cardio. Lead: del-desiran (Ph3).", "market_cap": "$3.0B", "pipeline": "5", "phase3": "2", "approved": "", "catalyst": "del-desiran DM1 Ph3 (2026)", "tags": ["Neuromuscular", "Cardio", "AOC"], "category": "platform"},
    {"ticker": "BEAM", "name": "Beam Therapeutics", "platform": "Base Editing", "description": "Rare Disease (Gene Editing). Lead: BEAM-101 (Ph1/2).", "market_cap": "$3.1B", "pipeline": "5", "phase3": "1", "approved": "", "catalyst": "BEAM-302 AATD (2026)", "tags": ["Gene Editing", "Sickle Cell", "Liver"], "category": "platform"},
    {"ticker": "NTLA", "name": "Intellia Therapeutics", "platform": "CRISPR", "description": "Rare Disease (Gene Editing). Lead: NTLA-2001 (Ph3).", "market_cap": "$2.8B", "pipeline": "6", "phase3": "2", "approved": "", "catalyst": "NTLA-2001 ATTR Ph3 (2026)", "tags": ["Gene Editing", "ATTR", "HAE"], "category": "platform"},
    {"ticker": "SANA", "name": "Sana Biotechnology", "platform": "Cell Therapy", "description": "Cell Engineering platform for hypoimmune cells.", "market_cap": "$1.2B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "SC291 Ph1 (2026)", "tags": ["Cell Therapy", "Hypoimmune", "Platform"], "category": "platform"},
    {"ticker": "PRME", "name": "Prime Medicine", "platform": "Gene Editing", "description": "Prime Editing platform. Lead: PM359 (Ph1).", "market_cap": "$0.8B", "pipeline": "3", "phase3": "0", "approved": "", "catalyst": "PM359 IND (2026)", "tags": ["Gene Editing", "Rare Disease", "Platform"], "category": "platform"},
    {"ticker": "RGNX", "name": "Regenxbio", "platform": "Gene Therapy", "description": "AAV gene therapy platform. Multiple programs.", "market_cap": "$0.6B", "pipeline": "8", "phase3": "2", "approved": "", "catalyst": "RGX-314 wet AMD (2026)", "tags": ["Gene Therapy", "Ophthalmology", "Platform"], "category": "platform"},
    {"ticker": "HALO", "name": "Halozyme Therapeutics", "platform": "Drug Delivery", "description": "Drug Delivery. ENHANZE royalties.", "market_cap": "$7.2B", "pipeline": "20+", "phase3": "N/A", "approved": "8", "catalyst": "New ENHANZE deals (2026)", "tags": ["Drug Delivery", "Royalties", "Platform"], "category": "platform"},
    {"ticker": "KRYS", "name": "Krystal Biotech", "platform": "Gene Therapy", "description": "Rare - Dermatology. Key product: Vyjuvek.", "market_cap": "$7B", "pipeline": "6", "phase3": "2", "approved": "1", "catalyst": "KB408 AATD (2026)", "tags": ["Rare Disease", "Dermatology", "Gene Therapy"], "category": "platform"},

    # Rare Disease
    {"ticker": "MIRM", "name": "Mirum Pharmaceuticals", "platform": "Small Molecule", "description": "Rare - Liver. Key product: Livmarli.", "market_cap": "$4.5B", "pipeline": "4", "phase3": "2", "approved": "3", "catalyst": "Volixibat PSC (2026)", "tags": ["Rare Disease", "Liver", "Cholestasis"], "category": "rare"},
    {"ticker": "FOLD", "name": "Amicus Therapeutics", "platform": "Enzyme", "description": "Rare - Lysosomal. Key products: Galafold, Pombiliti.", "market_cap": "$3.2B", "pipeline": "4", "phase3": "1", "approved": "2", "catalyst": "Pombiliti expansion (2026)", "tags": ["Rare Disease", "Lysosomal", "Metabolic"], "category": "rare"},
    {"ticker": "PTCT", "name": "PTC Therapeutics", "platform": "Small Molecule", "description": "Rare Disease. Key products: Translarna, Evrysdi royalties.", "market_cap": "$2.5B", "pipeline": "6", "phase3": "2", "approved": "3", "catalyst": "Sepiapterin Ph3 (2026)", "tags": ["Rare Disease", "Neuromuscular", "PKU"], "category": "rare"},
    {"ticker": "RARE", "name": "Ultragenyx Pharmaceutical", "platform": "Biologics", "description": "Rare Disease. Key products: Crysvita, Evkeeza.", "market_cap": "$4.5B", "pipeline": "15+", "phase3": "3", "approved": "4", "catalyst": "GTX-102 Angelman (2026)", "tags": ["Rare Disease", "Metabolic", "Gene Therapy"], "category": "rare"},
    {"ticker": "BCRX", "name": "BioCryst Pharmaceuticals", "platform": "Small Molecule", "description": "Rare Disease. Key product: Orladeyo.", "market_cap": "$3.5B", "pipeline": "4", "phase3": "1", "approved": "1", "catalyst": "Orladeyo HAE (2026)", "tags": ["Rare Disease", "HAE", "Oral"], "category": "rare"},
    {"ticker": "AGIO", "name": "Agios Pharmaceuticals", "platform": "Small Molecule", "description": "Rare - Hematology. Key product: Pyrukynd.", "market_cap": "$3.0B", "pipeline": "3", "phase3": "1", "approved": "1", "catalyst": "Pyrukynd expansion (2026)", "tags": ["Rare Disease", "Hematology", "PK Deficiency"], "category": "rare"},
    {"ticker": "INSM", "name": "Insmed", "platform": "Biologics", "description": "Rare - Pulmonary. Key products: Arikayce, Brinsupri.", "market_cap": "$34.7B", "pipeline": "6", "phase3": "3", "approved": "2", "catalyst": "Brensocatib launch (2026)", "tags": ["Rare Disease", "Pulmonary", "Anti-infective"], "category": "rare"},
    {"ticker": "UTHR", "name": "United Therapeutics", "platform": "Biologics", "description": "Rare - PAH. Key product: Tyvaso DPI.", "market_cap": "$14B", "pipeline": "8", "phase3": "2", "approved": "5", "catalyst": "Tyvaso DPI expansion (2026)", "tags": ["Rare Disease", "PAH", "Pulmonary"], "category": "rare"},
    {"ticker": "TVTX", "name": "Travere Therapeutics", "platform": "Small Molecule", "description": "Rare - Nephrology. Key product: Filspari.", "market_cap": "$3.0B", "pipeline": "3", "phase3": "1", "approved": "2", "catalyst": "Filspari FSGS (2026)", "tags": ["Rare Disease", "Nephrology", "IgAN"], "category": "rare"},

    # Neuropsychiatry
    {"ticker": "ALKS", "name": "Alkermes", "platform": "Small Molecule", "description": "Neuropsychiatry. Key products: Vivitrol, Aristada.", "market_cap": "$5.0B", "pipeline": "6", "phase3": "2", "approved": "4", "catalyst": "ALKS 2680 narcolepsy (2026)", "tags": ["Neuropsychiatry", "Addiction", "Schizophrenia"], "category": "neuro"},
    {"ticker": "NBIX", "name": "Neurocrine Biosciences", "platform": "Small Molecule", "description": "Neuropsychiatry. Key product: Ingrezza.", "market_cap": "$14B", "pipeline": "12", "phase3": "3", "approved": "2", "catalyst": "NBI-1065845 MDD (2026)", "tags": ["Neuropsychiatry", "Movement Disorders", "Psychiatry"], "category": "neuro"},
    {"ticker": "ACAD", "name": "Acadia Pharmaceuticals", "platform": "Small Molecule", "description": "Neuropsychiatry. Key products: Nuplazid, Daybue.", "market_cap": "$4.5B", "pipeline": "4", "phase3": "2", "approved": "2", "catalyst": "Daybue growth (2026)", "tags": ["Neuropsychiatry", "Rett Syndrome", "Parkinson"], "category": "neuro"},
    {"ticker": "CPRX", "name": "Catalyst Pharmaceuticals", "platform": "Small Molecule", "description": "Neuropsychiatry. Key product: Firdapse.", "market_cap": "$2.5B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Firdapse SMA (2026)", "tags": ["Neuropsychiatry", "LEMS", "Rare Disease"], "category": "neuro"},
    {"ticker": "AXSM", "name": "Axsome Therapeutics", "platform": "Small Molecule", "description": "Neuropsychiatry. Key products: Auvelity, Sunosi.", "market_cap": "$4.0B", "pipeline": "5", "phase3": "2", "approved": "2", "catalyst": "AXS-12 narcolepsy (2026)", "tags": ["Neuropsychiatry", "Depression", "Sleep"], "category": "neuro"},
    {"ticker": "SAGE", "name": "Sage Therapeutics", "platform": "Small Molecule", "description": "Neuropsychiatry. Key product: Zurzuvae.", "market_cap": "$0.8B", "pipeline": "4", "phase3": "1", "approved": "1", "catalyst": "Zurzuvae MDD (2026)", "tags": ["Neuropsychiatry", "Depression", "PPD"], "category": "neuro"},
    {"ticker": "PRAX", "name": "Praxis Precision Medicines", "platform": "Small Molecule", "description": "Neuropsychiatry - Genetic CNS.", "market_cap": "$0.5B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "PRAX-628 SCN2A (2026)", "tags": ["Neuropsychiatry", "Epilepsy", "Genetic"], "category": "neuro"},

    # Oncology
    {"ticker": "EXEL", "name": "Exelixis", "platform": "Small Molecule", "description": "Oncology. Key product: Cabometyx.", "market_cap": "$8B", "pipeline": "10+", "phase3": "4", "approved": "2", "catalyst": "Zanzalintinib Ph3 (2026)", "tags": ["Oncology", "Kidney Cancer", "Liver Cancer"], "category": "oncology"},
    {"ticker": "INCY", "name": "Incyte", "platform": "Small Molecule", "description": "Oncology, I&I. Key products: Jakafi, Opzelura.", "market_cap": "$14B", "pipeline": "20+", "phase3": "5", "approved": "4", "catalyst": "Povorcitinib AD (2026)", "tags": ["Oncology", "I&I", "Dermatology"], "category": "oncology"},
    {"ticker": "SRPT", "name": "Sarepta Therapeutics", "platform": "Gene Therapy", "description": "Neuromuscular (DMD). Key product: Elevidys.", "market_cap": "$8B", "pipeline": "10+", "phase3": "3", "approved": "4", "catalyst": "Elevidys Ph3 (2026)", "tags": ["Rare Disease", "DMD", "Gene Therapy"], "category": "oncology"},
    {"ticker": "IMVT", "name": "Immunovant", "platform": "Antibody", "description": "I&I (FcRn). Lead: batoclimab (Ph3).", "market_cap": "$5.0B", "pipeline": "4", "phase3": "3", "approved": "", "catalyst": "Batoclimab MG (2026)", "tags": ["I&I", "Autoimmune", "FcRn"], "category": "oncology"},
    {"ticker": "RYTM", "name": "Rhythm Pharmaceuticals", "platform": "Small Molecule", "description": "Metabolic - Obesity. Key product: Imcivree.", "market_cap": "$3.5B", "pipeline": "3", "phase3": "2", "approved": "1", "catalyst": "Setmelanotide expansion (2026)", "tags": ["Metabolic", "Obesity", "Rare"], "category": "oncology"},
    {"ticker": "LQDA", "name": "Liquidia Technologies", "platform": "Small Molecule", "description": "Rare - PAH. Key product: Yutrepia.", "market_cap": "$1.5B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Yutrepia growth (2026)", "tags": ["Rare Disease", "PAH", "Pulmonary"], "category": "oncology"},
    {"ticker": "XENE", "name": "Xenon Pharmaceuticals", "platform": "Small Molecule", "description": "Neuropsychiatry - Epilepsy. Lead: azetukalner.", "market_cap": "$3.0B", "pipeline": "4", "phase3": "2", "approved": "", "catalyst": "X-TOLE2 Ph3 (2026)", "tags": ["Neuropsychiatry", "Epilepsy", "Pain"], "category": "oncology"},
    {"ticker": "JANX", "name": "Janux Therapeutics", "platform": "Bispecific", "description": "Oncology - T cell engagers. Lead: JANX007.", "market_cap": "$2.0B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "JANX007 PSMA (2026)", "tags": ["Oncology", "Bispecific", "Prostate"], "category": "oncology"},
    {"ticker": "TALK", "name": "Talkspace", "platform": "Digital", "description": "Mental Health - Digital therapeutics.", "market_cap": "$0.3B", "pipeline": "2", "phase3": "N/A", "approved": "1", "catalyst": "Expansion (2026)", "tags": ["Digital", "Mental Health", "Telehealth"], "category": "oncology"},

    # Immunology & Inflammation
    {"ticker": "TGTX", "name": "TG Therapeutics", "platform": "Antibody", "description": "I&I (MS). Key product: Briumvi.", "market_cap": "$4.5B", "pipeline": "3", "phase3": "1", "approved": "1", "catalyst": "Briumvi growth (2026)", "tags": ["I&I", "MS", "Autoimmune"], "category": "ii"},
    {"ticker": "ADMA", "name": "ADMA Biologics", "platform": "Biologics", "description": "I&I (Immunoglobulins). Key product: ASCENIV.", "market_cap": "$3.0B", "pipeline": "2", "phase3": "N/A", "approved": "1", "catalyst": "ASCENIV expansion (2026)", "tags": ["I&I", "Immunoglobulins", "Plasma"], "category": "ii"},
    {"ticker": "APLS", "name": "Apellis Pharmaceuticals", "platform": "Small Molecule", "description": "Ophthalmology. Key product: Syfovre.", "market_cap": "$5.0B", "pipeline": "4", "phase3": "2", "approved": "1", "catalyst": "Syfovre growth (2026)", "tags": ["Ophthalmology", "AMD", "Complement"], "category": "ii"},
    {"ticker": "ANAB", "name": "AnaptysBio", "platform": "Antibody", "description": "I&I - Dermatology. Lead: rosnilimab.", "market_cap": "$2.5B", "pipeline": "4", "phase3": "2", "approved": "", "catalyst": "Rosnilimab AD (2026)", "tags": ["I&I", "Dermatology", "Atopic"], "category": "ii"},
    {"ticker": "KROS", "name": "Keros Therapeutics", "platform": "Biologics", "description": "Hematology. Lead: elritercept.", "market_cap": "$1.5B", "pipeline": "3", "phase3": "2", "approved": "", "catalyst": "Elritercept MDS (2026)", "tags": ["Hematology", "MDS", "Anemia"], "category": "ii"},
    {"ticker": "RLAY", "name": "Relay Therapeutics", "platform": "Small Molecule", "description": "Oncology - precision medicine. Lead: RLY-2608.", "market_cap": "$1.2B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "RLY-2608 PI3K (2026)", "tags": ["Oncology", "Precision", "PI3K"], "category": "ii"},

    # Metabolic
    {"ticker": "MDGL", "name": "Madrigal Pharmaceuticals", "platform": "Small Molecule", "description": "Metabolic - MASH. Key product: Rezdiffra.", "market_cap": "$6.8B", "pipeline": "1", "phase3": "1", "approved": "1", "catalyst": "Rezdiffra launch (2026)", "tags": ["Metabolic", "MASH", "Liver"], "category": "metabolic"},
    {"ticker": "CYTK", "name": "Cytokinetics", "platform": "Small Molecule", "description": "Cardiovascular. Key product: Myqorzo.", "market_cap": "$5.5B", "pipeline": "3", "phase3": "2", "approved": "1", "catalyst": "Aficamten HCM (2026)", "tags": ["Cardiovascular", "HCM", "Heart Failure"], "category": "metabolic"},
    {"ticker": "ARDX", "name": "Ardelyx", "platform": "Small Molecule", "description": "Nephrology, GI. Key products: Ibsrela, Xphozah.", "market_cap": "$1.5B", "pipeline": "3", "phase3": "1", "approved": "2", "catalyst": "Xphozah growth (2026)", "tags": ["Nephrology", "GI", "Hyperphosphatemia"], "category": "metabolic"},
    {"ticker": "VKTX", "name": "Viking Therapeutics", "platform": "Small Molecule", "description": "Metabolic - Obesity/MASH. Lead: VK2735.", "market_cap": "$6.0B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "VK2735 oral Ph2 (2026)", "tags": ["Metabolic", "Obesity", "GLP-1"], "category": "metabolic"},
    {"ticker": "TERN", "name": "Terns Pharmaceuticals", "platform": "Small Molecule", "description": "Metabolic - MASH. Lead: TERN-501.", "market_cap": "$0.5B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "TERN-501 MASH (2026)", "tags": ["Metabolic", "MASH", "Liver"], "category": "metabolic"},
    {"ticker": "AKRO", "name": "Akero Therapeutics", "platform": "Biologics", "description": "Metabolic - MASH. Lead: efruxifermin.", "market_cap": "$2.5B", "pipeline": "2", "phase3": "2", "approved": "", "catalyst": "EFX MASH Ph3 (2026)", "tags": ["Metabolic", "MASH", "FGF21"], "category": "metabolic"},
    {"ticker": "PCVX", "name": "Vaxcyte", "platform": "Vaccine", "description": "Vaccines - Pneumococcal. Lead: VAX-31.", "market_cap": "$12B", "pipeline": "4", "phase3": "2", "approved": "", "catalyst": "VAX-31 Ph3 (2026)", "tags": ["Vaccines", "Pneumococcal", "Infectious"], "category": "metabolic"},

    # Diagnostics & Tools
    {"ticker": "EXAS", "name": "Exact Sciences", "platform": "Diagnostics", "description": "Dx - Oncology. Key products: Cologuard, Oncotype DX.", "market_cap": "$19.4B", "pipeline": "5", "phase3": "N/A", "approved": "3", "catalyst": "Cologuard Plus (2026)", "tags": ["Diagnostics", "Oncology", "Screening"], "category": "tools"},
    {"ticker": "NTRA", "name": "Natera", "platform": "Diagnostics", "description": "Dx - Oncology, Prenatal. Key products: Signatera, Panorama.", "market_cap": "$33B", "pipeline": "8", "phase3": "N/A", "approved": "4", "catalyst": "Signatera expansion (2026)", "tags": ["Diagnostics", "Oncology", "Prenatal"], "category": "tools"},
    {"ticker": "GRAL", "name": "Grail", "platform": "Diagnostics", "description": "Dx - Oncology. Key product: Galleri.", "market_cap": "$2.0B", "pipeline": "2", "phase3": "N/A", "approved": "1", "catalyst": "Galleri Medicare (2026)", "tags": ["Diagnostics", "Oncology", "Screening"], "category": "tools"},
    {"ticker": "VCYT", "name": "Veracyte", "platform": "Diagnostics", "description": "Dx - Oncology. Key products: Decipher, Afirma.", "market_cap": "$2.0B", "pipeline": "4", "phase3": "N/A", "approved": "3", "catalyst": "Prosigna expansion (2026)", "tags": ["Diagnostics", "Oncology", "Genomics"], "category": "tools"},
    {"ticker": "CDNA", "name": "CareDx", "platform": "Diagnostics", "description": "Dx - Transplant. Key product: AlloSure.", "market_cap": "$0.8B", "pipeline": "3", "phase3": "N/A", "approved": "2", "catalyst": "AlloSure expansion (2026)", "tags": ["Diagnostics", "Transplant", "Rejection"], "category": "tools"},
    {"ticker": "GH", "name": "Guardant Health", "platform": "Diagnostics", "description": "Dx - Oncology. Key products: Guardant360, Shield.", "market_cap": "$4.0B", "pipeline": "5", "phase3": "N/A", "approved": "3", "catalyst": "Shield CRC (2026)", "tags": ["Diagnostics", "Oncology", "Liquid Biopsy"], "category": "tools"},
    {"ticker": "TWST", "name": "Twist Bioscience", "platform": "Tools", "description": "Tools - DNA synthesis platform.", "market_cap": "$2.5B", "pipeline": "N/A", "phase3": "N/A", "approved": "N/A", "catalyst": "Biopharma growth (2026)", "tags": ["Tools", "DNA Synthesis", "Platform"], "category": "tools"},
    {"ticker": "BNTX", "name": "BioNTech", "platform": "mRNA", "description": "mRNA vaccines and oncology.", "market_cap": "$25B", "pipeline": "20+", "phase3": "5", "approved": "1", "catalyst": "Oncology mRNA (2026)", "tags": ["mRNA", "Oncology", "Vaccines"], "category": "tools"},

    # Vaccines
    {"ticker": "NVAX", "name": "Novavax", "platform": "Vaccine", "description": "Vaccines. COVID vaccine.", "market_cap": "$1.2B", "pipeline": "5", "phase3": "2", "approved": "1", "catalyst": "CIC flu combo (2026)", "tags": ["Vaccines", "COVID", "Influenza"], "category": "vaccines"},
    {"ticker": "DVAX", "name": "Dynavax Technologies", "platform": "Vaccine", "description": "Vaccines. Key product: Heplisav-B.", "market_cap": "$1.5B", "pipeline": "3", "phase3": "1", "approved": "1", "catalyst": "Heplisav-B growth (2026)", "tags": ["Vaccines", "Hepatitis B", "Adjuvant"], "category": "vaccines"},
    {"ticker": "VIR", "name": "Vir Biotechnology", "platform": "Antibody", "description": "Infectious Disease. Key product: Xofluza partnership.", "market_cap": "$1.0B", "pipeline": "6", "phase3": "2", "approved": "1", "catalyst": "VIR-2218 HBV (2026)", "tags": ["Infectious", "HBV", "Antibody"], "category": "vaccines"},
    {"ticker": "IOVA", "name": "Iovance Biotherapeutics", "platform": "Cell Therapy", "description": "Oncology - TIL therapy. Key product: Amtagvi.", "market_cap": "$3.0B", "pipeline": "4", "phase3": "2", "approved": "1", "catalyst": "Amtagvi expansion (2026)", "tags": ["Oncology", "Cell Therapy", "TIL"], "category": "vaccines"},

    # Nephrology
    {"ticker": "CRNX", "name": "Crinetics Pharmaceuticals", "platform": "Small Molecule", "description": "Endocrinology. Lead: paltusotine.", "market_cap": "$4.0B", "pipeline": "4", "phase3": "2", "approved": "", "catalyst": "Paltusotine acromegaly (2026)", "tags": ["Endocrinology", "Acromegaly", "Oral"], "category": "nephro"},
    {"ticker": "ETNB", "name": "89bio", "platform": "Biologics", "description": "Metabolic - MASH. Lead: pegozafermin.", "market_cap": "$1.5B", "pipeline": "2", "phase3": "2", "approved": "", "catalyst": "Pegozafermin MASH (2026)", "tags": ["Metabolic", "MASH", "FGF21"], "category": "nephro"},
    {"ticker": "REGN", "name": "Regeneron Pharmaceuticals", "platform": "Antibody", "description": "I&I, Ophthalmology, Oncology. Key products: Dupixent, EYLEA HD, Libtayo.", "market_cap": "$90B+", "pipeline": "35+", "phase3": "10+", "approved": "8", "catalyst": "Dupixent COPD Ph3 (2026)", "tags": ["I&I", "Ophthalmology", "Oncology"], "category": "nephro"},

    # Commercial Stage
    {"ticker": "VCEL", "name": "Vericel", "platform": "Regenerative", "description": "Regenerative. Key products: MACI, Epicel.", "market_cap": "$2.5B", "pipeline": "3", "phase3": "1", "approved": "2", "catalyst": "NexoBrid launch (2026)", "tags": ["Regenerative", "Orthopedics", "Burn"], "category": "commercial"},
    {"ticker": "MNKD", "name": "MannKind", "platform": "Inhalation", "description": "Diabetes, Pulmonary. Key products: Afrezza, Tyvaso DPI.", "market_cap": "$1.0B", "pipeline": "3", "phase3": "1", "approved": "2", "catalyst": "V-Go growth (2026)", "tags": ["Diabetes", "Pulmonary", "Inhalation"], "category": "commercial"},
    {"ticker": "SUPN", "name": "Supernus Pharmaceuticals", "platform": "Small Molecule", "description": "Neuropsychiatry. Key products: Qelbree, Trokendi XR.", "market_cap": "$2.0B", "pipeline": "4", "phase3": "1", "approved": "3", "catalyst": "Qelbree growth (2026)", "tags": ["Neuropsychiatry", "ADHD", "Epilepsy"], "category": "commercial"},
    {"ticker": "RCKT", "name": "Rocket Pharmaceuticals", "platform": "Gene Therapy", "description": "Gene Therapy. Key product: Kresladi.", "market_cap": "$2.0B", "pipeline": "5", "phase3": "2", "approved": "1", "catalyst": "Kresladi launch (2026)", "tags": ["Gene Therapy", "Rare Disease", "LAD-I"], "category": "commercial"},
    {"ticker": "RVMD", "name": "Revolution Medicines", "platform": "Small Molecule", "description": "Oncology - RAS inhibitors. Lead: RMC-6236.", "market_cap": "$8.0B", "pipeline": "4", "phase3": "2", "approved": "", "catalyst": "RMC-6236 PDAC (2026)", "tags": ["Oncology", "KRAS", "Precision"], "category": "commercial"},
    {"ticker": "SMMT", "name": "Summit Therapeutics", "platform": "Antibody", "description": "Oncology - PD-1. Lead: ivonescimab.", "market_cap": "$15B", "pipeline": "2", "phase3": "3", "approved": "", "catalyst": "Ivonescimab NSCLC (2026)", "tags": ["Oncology", "PD-1", "Bispecific"], "category": "commercial"},
    {"ticker": "DNLI", "name": "Denali Therapeutics", "platform": "Biologics", "description": "Neurodegeneration. Lead: DNL310.", "market_cap": "$4.0B", "pipeline": "8", "phase3": "1", "approved": "", "catalyst": "DNL310 Hunter (2026)", "tags": ["Neuro", "Lysosomal", "BBB"], "category": "commercial"},
    {"ticker": "MRUS", "name": "Merus", "platform": "Bispecific", "description": "Oncology - bispecific antibodies. Lead: zenocutuzumab.", "market_cap": "$4.0B", "pipeline": "5", "phase3": "2", "approved": "", "catalyst": "Zeno NRG1 (2026)", "tags": ["Oncology", "Bispecific", "NRG1"], "category": "commercial"},
    {"ticker": "ROIV", "name": "Roivant Sciences", "platform": "Diversified", "description": "Diversified biotech. Multiple Vants.", "market_cap": "$8.0B", "pipeline": "20+", "phase3": "5", "approved": "2", "catalyst": "Vant spinoffs (2026)", "tags": ["Diversified", "Platform", "Vants"], "category": "commercial"},
    {"ticker": "LEGN", "name": "Legend Biotech", "platform": "Cell Therapy", "description": "Oncology - CAR-T. Key product: Carvykti.", "market_cap": "$10B", "pipeline": "6", "phase3": "3", "approved": "1", "catalyst": "Carvykti expansion (2026)", "tags": ["Oncology", "CAR-T", "Myeloma"], "category": "commercial"},
    {"ticker": "VRTX", "name": "Vertex Pharmaceuticals", "platform": "Small Molecule", "description": "Rare Disease (CF), Pain, Gene Therapy. Key products: Trikafta, JOURNAVX, Casgevy.", "market_cap": "$120B+", "pipeline": "20+", "phase3": "5", "approved": "5", "catalyst": "VX-548 pain Ph3 (2026)", "tags": ["Rare Disease", "Pain", "Gene Therapy"], "category": "commercial"},
    {"ticker": "ABBV", "name": "AbbVie", "platform": "Small Molecule", "description": "I&I, Oncology, Neuro. Key products: Humira, Skyrizi, Rinvoq.", "market_cap": "$300B+", "pipeline": "50+", "phase3": "15+", "approved": "30+", "catalyst": "Skyrizi/Rinvoq growth (2026)", "tags": ["I&I", "Oncology", "Neuro"], "category": "commercial"},
]

# Additional companies to reach 145
ADDITIONAL_COMPANIES = [
    {"ticker": "ALEC", "name": "Alector", "platform": "Antibody", "description": "Neurodegeneration - immuno-neurology.", "market_cap": "$0.8B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "AL002 Alzheimer (2026)", "tags": ["Neuro", "Alzheimer", "TREM2"], "category": "neuro"},
    {"ticker": "ANNX", "name": "Annexon Biosciences", "platform": "Antibody", "description": "Neuro - complement C1q.", "market_cap": "$0.5B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "ANX005 GBS (2026)", "tags": ["Neuro", "Complement", "Autoimmune"], "category": "neuro"},
    {"ticker": "APGE", "name": "Apogee Therapeutics", "platform": "Antibody", "description": "I&I - next-gen biologics.", "market_cap": "$2.5B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "APG777 AD (2026)", "tags": ["I&I", "Dermatology", "Atopic"], "category": "ii"},
    {"ticker": "ARVN", "name": "Arvinas", "platform": "PROTAC", "description": "Oncology - protein degraders.", "market_cap": "$2.0B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "Vepdegestrant BC (2026)", "tags": ["Oncology", "PROTAC", "Breast"], "category": "oncology"},
    {"ticker": "ACLX", "name": "Arcellx", "platform": "Cell Therapy", "description": "Oncology - CAR-T.", "market_cap": "$3.5B", "pipeline": "3", "phase3": "2", "approved": "", "catalyst": "Anito-cel myeloma (2026)", "tags": ["Oncology", "CAR-T", "Myeloma"], "category": "oncology"},
    {"ticker": "ABUS", "name": "Arbutus Biopharma", "platform": "RNAi", "description": "Infectious - HBV cure.", "market_cap": "$0.3B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "Imdusiran HBV (2026)", "tags": ["Infectious", "HBV", "RNAi"], "category": "vaccines"},
    {"ticker": "AKBA", "name": "Akebia Therapeutics", "platform": "Small Molecule", "description": "Nephrology - anemia.", "market_cap": "$0.2B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Vafseo growth (2026)", "tags": ["Nephrology", "Anemia", "HIF"], "category": "nephro"},
    {"ticker": "ALT", "name": "Altimmune", "platform": "Biologics", "description": "Metabolic - obesity.", "market_cap": "$0.8B", "pipeline": "2", "phase3": "1", "approved": "", "catalyst": "Pemvidutide Ph2 (2026)", "tags": ["Metabolic", "Obesity", "GLP-1"], "category": "metabolic"},
    {"ticker": "BHVN", "name": "Biohaven", "platform": "Small Molecule", "description": "Neuropsychiatry. Lead: taldefgrobep.", "market_cap": "$3.0B", "pipeline": "6", "phase3": "2", "approved": "", "catalyst": "Taldefgrobep SMA (2026)", "tags": ["Neuropsychiatry", "SMA", "Myostatin"], "category": "neuro"},
    {"ticker": "BLUE", "name": "bluebird bio", "platform": "Gene Therapy", "description": "Gene Therapy. Key products: Zynteglo, Lyfgenia.", "market_cap": "$0.3B", "pipeline": "3", "phase3": "1", "approved": "2", "catalyst": "Launch growth (2026)", "tags": ["Gene Therapy", "Sickle Cell", "Beta-Thal"], "category": "platform"},
    {"ticker": "CALT", "name": "Calliditas Therapeutics", "platform": "Small Molecule", "description": "Rare - IgAN. Key product: Tarpeyo.", "market_cap": "$1.5B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Tarpeyo growth (2026)", "tags": ["Rare Disease", "IgAN", "Nephrology"], "category": "rare"},
    {"ticker": "CBAY", "name": "CymaBay Therapeutics", "platform": "Small Molecule", "description": "Metabolic - PBC. Key product: seladelpar.", "market_cap": "$2.5B", "pipeline": "2", "phase3": "1", "approved": "", "catalyst": "Seladelpar PBC (2026)", "tags": ["Metabolic", "PBC", "Liver"], "category": "metabolic"},
    {"ticker": "COGT", "name": "Cogent Biosciences", "platform": "Small Molecule", "description": "Oncology - KIT inhibitor.", "market_cap": "$2.0B", "pipeline": "2", "phase3": "2", "approved": "", "catalyst": "Bezuclastinib GIST (2026)", "tags": ["Oncology", "KIT", "GIST"], "category": "oncology"},
    {"ticker": "DAWN", "name": "Day One Biopharmaceuticals", "platform": "Small Molecule", "description": "Oncology - pediatric. Key product: Ojemda.", "market_cap": "$1.5B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Ojemda expansion (2026)", "tags": ["Oncology", "Pediatric", "RAF"], "category": "oncology"},
    {"ticker": "DYN", "name": "Dyne Therapeutics", "platform": "AOC", "description": "Neuromuscular - AOC platform.", "market_cap": "$2.0B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "DYNE-101 DM1 (2026)", "tags": ["Neuromuscular", "AOC", "DM1"], "category": "platform"},
    {"ticker": "EDIT", "name": "Editas Medicine", "platform": "CRISPR", "description": "Gene Editing - in vivo.", "market_cap": "$0.3B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "EDIT-101 LCA (2026)", "tags": ["Gene Editing", "Ophthalmology", "CRISPR"], "category": "platform"},
    {"ticker": "FATE", "name": "Fate Therapeutics", "platform": "Cell Therapy", "description": "iPSC-derived cell therapy.", "market_cap": "$0.3B", "pipeline": "5", "phase3": "1", "approved": "", "catalyst": "FT522 lymphoma (2026)", "tags": ["Cell Therapy", "iPSC", "CAR-NK"], "category": "platform"},
    {"ticker": "FGEN", "name": "FibroGen", "platform": "Small Molecule", "description": "Fibrosis, Anemia. Lead: pamrevlumab.", "market_cap": "$0.2B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "Pamrevlumab IPF (2026)", "tags": ["Fibrosis", "Anemia", "HIF"], "category": "rare"},
    {"ticker": "FULC", "name": "Fulcrum Therapeutics", "platform": "Small Molecule", "description": "Rare Disease. Lead: losmapimod.", "market_cap": "$0.5B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "Losmapimod FSHD (2026)", "tags": ["Rare Disease", "FSHD", "Epigenetic"], "category": "rare"},
    {"ticker": "GERN", "name": "Geron Corporation", "platform": "Small Molecule", "description": "Oncology - telomerase. Key product: Rytelo.", "market_cap": "$3.0B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Rytelo growth (2026)", "tags": ["Oncology", "MDS", "Telomerase"], "category": "oncology"},
    {"ticker": "HIMS", "name": "Hims & Hers Health", "platform": "Digital", "description": "Telehealth - consumer health.", "market_cap": "$5.0B", "pipeline": "N/A", "phase3": "N/A", "approved": "N/A", "catalyst": "Expansion (2026)", "tags": ["Digital", "Telehealth", "Consumer"], "category": "tools"},
    {"ticker": "IDYA", "name": "IDEAYA Biosciences", "platform": "Small Molecule", "description": "Oncology - synthetic lethality.", "market_cap": "$2.5B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "Darovasertib UM (2026)", "tags": ["Oncology", "Precision", "Synthetic Lethality"], "category": "oncology"},
    {"ticker": "IGMS", "name": "IGM Biosciences", "platform": "Antibody", "description": "Oncology - IgM antibodies.", "market_cap": "$0.5B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "Imvotamab DLBCL (2026)", "tags": ["Oncology", "IgM", "Bispecific"], "category": "oncology"},
    {"ticker": "IMGN", "name": "ImmunoGen", "platform": "ADC", "description": "Oncology - ADC. Key product: Elahere.", "market_cap": "$0B", "pipeline": "3", "phase3": "2", "approved": "1", "catalyst": "Acquired by Abbvie", "tags": ["Oncology", "ADC", "Ovarian"], "category": "oncology"},
    {"ticker": "IMTX", "name": "Immatics", "platform": "Cell Therapy", "description": "Oncology - TCR-T.", "market_cap": "$1.5B", "pipeline": "5", "phase3": "1", "approved": "", "catalyst": "IMA203 solid tumors (2026)", "tags": ["Oncology", "TCR-T", "Cell Therapy"], "category": "oncology"},
    {"ticker": "IOVA", "name": "Iovance Biotherapeutics", "platform": "Cell Therapy", "description": "Oncology - TIL therapy. Key product: Amtagvi.", "market_cap": "$3.0B", "pipeline": "4", "phase3": "2", "approved": "1", "catalyst": "Amtagvi expansion (2026)", "tags": ["Oncology", "Cell Therapy", "TIL"], "category": "oncology"},
    {"ticker": "IRWD", "name": "Ironwood Pharmaceuticals", "platform": "Small Molecule", "description": "GI. Key product: Linzess.", "market_cap": "$1.0B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "Linzess growth (2026)", "tags": ["GI", "IBS", "Constipation"], "category": "metabolic"},
    {"ticker": "ITCI", "name": "Intra-Cellular Therapies", "platform": "Small Molecule", "description": "Neuropsychiatry. Key product: Caplyta.", "market_cap": "$8.0B", "pipeline": "4", "phase3": "2", "approved": "1", "catalyst": "Caplyta MDD (2026)", "tags": ["Neuropsychiatry", "Schizophrenia", "Depression"], "category": "neuro"},
    {"ticker": "KALA", "name": "Kala Pharmaceuticals", "platform": "Small Molecule", "description": "Ophthalmology. Key product: Eysuvis.", "market_cap": "$0.1B", "pipeline": "2", "phase3": "1", "approved": "1", "catalyst": "KPI-012 cornea (2026)", "tags": ["Ophthalmology", "Dry Eye", "Inflammation"], "category": "ii"},
    {"ticker": "KALV", "name": "KalVista Pharmaceuticals", "platform": "Small Molecule", "description": "Rare - HAE. Lead: sebetralstat.", "market_cap": "$2.5B", "pipeline": "2", "phase3": "1", "approved": "", "catalyst": "Sebetralstat HAE (2026)", "tags": ["Rare Disease", "HAE", "Oral"], "category": "rare"},
    {"ticker": "KYMR", "name": "Kymera Therapeutics", "platform": "PROTAC", "description": "I&I - protein degraders.", "market_cap": "$2.5B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "KT-474 AD (2026)", "tags": ["I&I", "PROTAC", "IRAK4"], "category": "ii"},
    {"ticker": "LNTH", "name": "Lantheus Holdings", "platform": "Radiopharmaceutical", "description": "Diagnostics - radiopharmaceuticals.", "market_cap": "$6.0B", "pipeline": "5", "phase3": "2", "approved": "3", "catalyst": "Pylarify growth (2026)", "tags": ["Diagnostics", "Radiopharmaceutical", "Oncology"], "category": "tools"},
    {"ticker": "LYEL", "name": "Lyell Immunopharma", "platform": "Cell Therapy", "description": "Oncology - next-gen T cell.", "market_cap": "$0.5B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "LYL797 solid tumors (2026)", "tags": ["Oncology", "Cell Therapy", "T Cell"], "category": "oncology"},
    {"ticker": "MDXH", "name": "MDxHealth", "platform": "Diagnostics", "description": "Dx - Urology.", "market_cap": "$0.3B", "pipeline": "3", "phase3": "N/A", "approved": "2", "catalyst": "SelectMDx growth (2026)", "tags": ["Diagnostics", "Urology", "Prostate"], "category": "tools"},
    {"ticker": "MRVI", "name": "Maravai LifeSciences", "platform": "Tools", "description": "Tools - nucleic acid production.", "market_cap": "$1.5B", "pipeline": "N/A", "phase3": "N/A", "approved": "N/A", "catalyst": "mRNA supply (2026)", "tags": ["Tools", "mRNA", "Manufacturing"], "category": "tools"},
    {"ticker": "MYGN", "name": "Myriad Genetics", "platform": "Diagnostics", "description": "Dx - Oncology, Women's Health.", "market_cap": "$2.0B", "pipeline": "4", "phase3": "N/A", "approved": "4", "catalyst": "GeneSight growth (2026)", "tags": ["Diagnostics", "Oncology", "Genetic"], "category": "tools"},
    {"ticker": "NUVB", "name": "Nuvation Bio", "platform": "Small Molecule", "description": "Oncology - targeted therapies.", "market_cap": "$0.8B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "NUV-868 BC (2026)", "tags": ["Oncology", "Targeted", "BET"], "category": "oncology"},
    {"ticker": "OGN", "name": "Organon", "platform": "Diversified", "description": "Women's Health, Biosimilars.", "market_cap": "$5.0B", "pipeline": "10+", "phase3": "3", "approved": "20+", "catalyst": "Biosimilar launches (2026)", "tags": ["Women's Health", "Biosimilar", "Diversified"], "category": "commercial"},
    {"ticker": "OMER", "name": "Omeros Corporation", "platform": "Small Molecule", "description": "Complement. Lead: narsoplimab.", "market_cap": "$0.3B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "Narsoplimab HSCT-TMA (2026)", "tags": ["Complement", "Rare", "MASP-2"], "category": "rare"},
    {"ticker": "PCRX", "name": "Pacira BioSciences", "platform": "Drug Delivery", "description": "Pain management. Key product: Exparel.", "market_cap": "$1.5B", "pipeline": "3", "phase3": "1", "approved": "2", "catalyst": "Exparel growth (2026)", "tags": ["Pain", "Surgery", "Drug Delivery"], "category": "commercial"},
    {"ticker": "PTGX", "name": "Protagonist Therapeutics", "platform": "Peptide", "description": "GI, Hematology. Lead: rusfertide.", "market_cap": "$3.5B", "pipeline": "3", "phase3": "2", "approved": "", "catalyst": "Rusfertide PV (2026)", "tags": ["Hematology", "GI", "Peptide"], "category": "metabolic"},
    {"ticker": "QURE", "name": "uniQure", "platform": "Gene Therapy", "description": "Gene Therapy. Key product: Hemgenix.", "market_cap": "$0.5B", "pipeline": "4", "phase3": "1", "approved": "1", "catalyst": "AMT-130 HD (2026)", "tags": ["Gene Therapy", "Hemophilia", "Huntington"], "category": "platform"},
    {"ticker": "RCUS", "name": "Arcus Biosciences", "platform": "Small Molecule", "description": "Oncology - immuno-oncology.", "market_cap": "$2.5B", "pipeline": "8", "phase3": "3", "approved": "", "catalyst": "Domvanalimab NSCLC (2026)", "tags": ["Oncology", "IO", "TIGIT"], "category": "oncology"},
    {"ticker": "REPL", "name": "Replimune Group", "platform": "Oncolytic Virus", "description": "Oncology - oncolytic immunotherapy.", "market_cap": "$0.8B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "RP1 melanoma (2026)", "tags": ["Oncology", "Oncolytic", "Immunotherapy"], "category": "oncology"},
    {"ticker": "RXRX", "name": "Recursion Pharmaceuticals", "platform": "AI", "description": "AI-driven drug discovery.", "market_cap": "$3.0B", "pipeline": "5", "phase3": "1", "approved": "", "catalyst": "REC-994 NF2 (2026)", "tags": ["AI", "Platform", "Drug Discovery"], "category": "tools"},
    {"ticker": "SGMO", "name": "Sangamo Therapeutics", "platform": "Gene Therapy", "description": "Gene Therapy, Gene Editing.", "market_cap": "$0.2B", "pipeline": "5", "phase3": "1", "approved": "", "catalyst": "Giroctocogene (2026)", "tags": ["Gene Therapy", "Hemophilia", "Editing"], "category": "platform"},
    {"ticker": "SRRK", "name": "Scholar Rock Holding", "platform": "Antibody", "description": "Neuromuscular. Lead: apitegromab.", "market_cap": "$1.5B", "pipeline": "2", "phase3": "1", "approved": "", "catalyst": "Apitegromab SMA (2026)", "tags": ["Neuromuscular", "SMA", "Myostatin"], "category": "neuro"},
    {"ticker": "STOK", "name": "Stoke Therapeutics", "platform": "Antisense", "description": "Rare - genetic epilepsies.", "market_cap": "$0.8B", "pipeline": "3", "phase3": "1", "approved": "", "catalyst": "STK-001 Dravet (2026)", "tags": ["Rare Disease", "Epilepsy", "Antisense"], "category": "rare"},
    {"ticker": "TARS", "name": "Tarsus Pharmaceuticals", "platform": "Small Molecule", "description": "Ophthalmology. Key product: Xdemvy.", "market_cap": "$2.5B", "pipeline": "3", "phase3": "1", "approved": "1", "catalyst": "Xdemvy growth (2026)", "tags": ["Ophthalmology", "Demodex", "Inflammation"], "category": "ii"},
    {"ticker": "TCRT", "name": "Alaunos Therapeutics", "platform": "Cell Therapy", "description": "Oncology - TCR-T cell therapy.", "market_cap": "$0.1B", "pipeline": "2", "phase3": "1", "approved": "", "catalyst": "TCR-T solid tumors (2026)", "tags": ["Oncology", "Cell Therapy", "TCR-T"], "category": "oncology"},
    {"ticker": "VERA", "name": "Vera Therapeutics", "platform": "Antibody", "description": "Nephrology - IgAN. Lead: atacicept.", "market_cap": "$3.0B", "pipeline": "2", "phase3": "2", "approved": "", "catalyst": "Atacicept IgAN (2026)", "tags": ["Nephrology", "IgAN", "BAFF/APRIL"], "category": "nephro"},
    {"ticker": "VERV", "name": "Verve Therapeutics", "platform": "Base Editing", "description": "Cardiovascular - gene editing.", "market_cap": "$0.5B", "pipeline": "2", "phase3": "1", "approved": "", "catalyst": "VERVE-101 HeFH (2026)", "tags": ["Cardiovascular", "Gene Editing", "PCSK9"], "category": "platform"},
    {"ticker": "VXRT", "name": "Vaxart", "platform": "Vaccine", "description": "Oral vaccines platform.", "market_cap": "$0.2B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "Oral norovirus (2026)", "tags": ["Vaccines", "Oral", "Norovirus"], "category": "vaccines"},
    {"ticker": "WVE", "name": "Wave Life Sciences", "platform": "Oligonucleotide", "description": "Genetic medicines - stereopure.", "market_cap": "$1.0B", "pipeline": "4", "phase3": "1", "approved": "", "catalyst": "WVE-006 AATD (2026)", "tags": ["Genetic", "Oligonucleotide", "AATD"], "category": "platform"},
    {"ticker": "XNCR", "name": "Xencor", "platform": "Antibody", "description": "Oncology - bispecific antibodies.", "market_cap": "$2.0B", "pipeline": "8", "phase3": "2", "approved": "", "catalyst": "Plamotamab DLBCL (2026)", "tags": ["Oncology", "Bispecific", "CD20xCD3"], "category": "oncology"},
    {"ticker": "YMAB", "name": "Y-mAbs Therapeutics", "platform": "Antibody", "description": "Oncology - pediatric. Key product: Danyelza.", "market_cap": "$0.5B", "pipeline": "3", "phase3": "1", "approved": "1", "catalyst": "Danyelza expansion (2026)", "tags": ["Oncology", "Pediatric", "Neuroblastoma"], "category": "oncology"},
    {"ticker": "ZLAB", "name": "Zai Lab", "platform": "Diversified", "description": "China-focused biotech.", "market_cap": "$3.0B", "pipeline": "20+", "phase3": "5", "approved": "5", "catalyst": "China launches (2026)", "tags": ["Diversified", "China", "Oncology"], "category": "commercial"},
]

# Combine all companies
ALL_COMPANIES = COMPANIES + ADDITIONAL_COMPANIES

# Categories
CATEGORIES = {
    "largecap": "Large Cap",
    "platform": "Platform / Genetic Medicines",
    "rare": "Rare Disease",
    "neuro": "Neuropsychiatry",
    "oncology": "Oncology",
    "ii": "Immunology & Inflammation",
    "metabolic": "Metabolic & Cardiovascular",
    "tools": "Diagnostics & Tools",
    "vaccines": "Vaccines & Infectious",
    "nephro": "Nephrology & Endocrine",
    "commercial": "Commercial Stage",
}

def get_nav_html(active=""):
    return f'''
    <header class="header">
        <div class="header-inner">
            <a href="/" class="logo">Satya<span>Bio</span></a>
            <nav class="nav-links">
                <a href="/targets" {"class='active'" if active == "targets" else ""}>Targets</a>
                <a href="/companies" {"class='active'" if active == "companies" else ""}>Companies</a>
                <a href="/kols" {"class='active'" if active == "kols" else ""}>KOL Finder</a>
                <a href="/about" {"class='active'" if active == "about" else ""}>About</a>
            </nav>
            <div class="nav-cta">
                <a href="mailto:hello@satyabio.com?subject=Early%20Access%20Request" class="btn-primary">Get Started</a>
            </div>
        </div>
    </header>
    '''

def get_base_styles():
    return '''
    <style>
        :root {
            --navy: #1a2b3c;
            --navy-light: #2d4a6f;
            --accent: #e07a5f;
            --accent-hover: #d06a4f;
            --accent-light: #fef5f3;
            --bg: #fafaf8;
            --surface: #ffffff;
            --border: #e5e5e0;
            --text: #1a1d21;
            --text-secondary: #5f6368;
            --text-muted: #9aa0a6;
            --catalyst-bg: #fef9c3;
            --catalyst-border: #fde047;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }

        .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 64px; position: sticky; top: 0; z-index: 100; }
        .header-inner { max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
        .logo { font-size: 1.25rem; font-weight: 700; color: var(--navy); text-decoration: none; }
        .logo span { color: var(--accent); }
        .nav-links { display: flex; gap: 28px; }
        .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; }
        .nav-links a:hover, .nav-links a.active { color: var(--navy); }
        .nav-cta { display: flex; gap: 12px; }
        .btn-primary { padding: 8px 18px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 6px; font-size: 0.9rem; }
        .btn-primary:hover { background: var(--accent-hover); }

        .main { max-width: 1400px; margin: 0 auto; padding: 32px; }
        .page-header { margin-bottom: 24px; }
        .page-title { font-size: 1.75rem; font-weight: 700; color: var(--navy); margin-bottom: 8px; }
        .page-subtitle { color: var(--text-secondary); font-size: 0.95rem; }

        .category-nav { position: sticky; top: 64px; background: var(--bg); padding: 16px 0; z-index: 50; border-bottom: 1px solid var(--border); margin-bottom: 32px; }
        .category-pills { display: flex; gap: 10px; flex-wrap: wrap; }
        .category-pill { padding: 8px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; font-size: 0.85rem; font-weight: 500; color: var(--text-secondary); cursor: pointer; text-decoration: none; }
        .category-pill:hover { border-color: var(--navy); color: var(--navy); }
        .category-pill.active { background: var(--navy); border-color: var(--navy); color: white; }

        .section { margin-bottom: 48px; scroll-margin-top: 140px; }
        .section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section-title { font-size: 1.25rem; font-weight: 700; color: var(--navy); }
        .section-count { background: var(--navy); color: white; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; }

        .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }

        .company-card { display: block; text-decoration: none; color: inherit; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: all 0.2s; }
        .company-card:hover { border-color: var(--accent); box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-2px); }

        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
        .card-ticker-row { display: flex; align-items: center; gap: 8px; }
        .card-ticker { font-size: 1rem; font-weight: 700; color: var(--navy); }
        .card-name { font-size: 0.8rem; color: var(--text-secondary); }
        .platform-badge { padding: 3px 8px; background: var(--accent-light); color: var(--accent); font-size: 0.65rem; font-weight: 600; border-radius: 10px; text-transform: uppercase; }

        .card-description { color: var(--text-secondary); font-size: 0.8rem; line-height: 1.5; margin-bottom: 12px; }

        .stats-row { display: flex; gap: 12px; margin-bottom: 12px; padding: 10px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
        .stat { display: flex; flex-direction: column; }
        .stat-value { font-weight: 700; font-size: 0.85rem; color: var(--navy); }
        .stat-label { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; }

        .catalyst-box { background: var(--catalyst-bg); border: 1px solid var(--catalyst-border); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; }
        .catalyst-label { font-size: 0.65rem; font-weight: 600; color: #92400e; text-transform: uppercase; margin-bottom: 2px; }
        .catalyst-text { font-size: 0.8rem; color: #78350f; font-weight: 500; }

        .tags-row { display: flex; flex-wrap: wrap; gap: 6px; }
        .tag { padding: 4px 10px; background: #f3f4f6; color: var(--text-secondary); font-size: 0.75rem; border-radius: 12px; }

        .footer { background: var(--navy); color: rgba(255,255,255,0.7); padding: 32px; text-align: center; margin-top: 64px; }
        .footer p { font-size: 0.85rem; }

        @media (max-width: 768px) {
            .nav-links { display: none; }
            .main { padding: 20px 16px; }
            .cards-grid { grid-template-columns: 1fr; }
        }
    </style>
    '''

def generate_company_card(company):
    tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in company.get("tags", [])[:3]])
    approved_stat = f'<div class="stat"><span class="stat-value">{company["approved"]}</span><span class="stat-label">Approved</span></div>' if company.get("approved") else ""

    return f'''
    <a href="/api/company/{company["ticker"]}/html" class="company-card">
        <div class="card-header">
            <div>
                <div class="card-ticker-row">
                    <span class="card-ticker">{company["ticker"]}</span>
                    <span class="card-name">{company["name"]}</span>
                </div>
            </div>
            <span class="platform-badge">{company["platform"]}</span>
        </div>
        <p class="card-description">{company["description"]}</p>
        <div class="stats-row">
            <div class="stat"><span class="stat-value">{company["market_cap"]}</span><span class="stat-label">Market Cap</span></div>
            <div class="stat"><span class="stat-value">{company["pipeline"]}</span><span class="stat-label">Pipeline</span></div>
            <div class="stat"><span class="stat-value">{company["phase3"]}</span><span class="stat-label">Phase 3</span></div>
            {approved_stat}
        </div>
        <div class="catalyst-box">
            <div class="catalyst-label">Next Catalyst</div>
            <div class="catalyst-text">{company["catalyst"]}</div>
        </div>
        <div class="tags-row">{tags_html}</div>
    </a>
    '''

def generate_companies_page():
    # Group by category
    by_category = {}
    for company in ALL_COMPANIES:
        cat = company.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(company)

    # Category pills
    pills_html = '<a href="#all" class="category-pill active">All</a>'
    for cat_id, cat_name in CATEGORIES.items():
        count = len(by_category.get(cat_id, []))
        if count > 0:
            pills_html += f'<a href="#{cat_id}" class="category-pill">{cat_name} ({count})</a>'

    # Sections
    sections_html = ""
    for cat_id, cat_name in CATEGORIES.items():
        companies = by_category.get(cat_id, [])
        if not companies:
            continue
        cards_html = ''.join([generate_company_card(c) for c in companies])
        sections_html += f'''
        <section class="section" id="{cat_id}">
            <div class="section-header">
                <h2 class="section-title">{cat_name}</h2>
                <span class="section-count">{len(companies)}</span>
            </div>
            <div class="cards-grid">{cards_html}</div>
        </section>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Companies | Satya Bio</title>
    <meta name="description" content="Browse {len(ALL_COMPANIES)} biotech companies with pipeline data and catalyst tracking.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .search-box {{ margin-bottom: 16px; }}
        .search-input {{ width: 100%; max-width: 500px; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; }}
        .search-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }}
        .results-count {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px; }}
    </style>
</head>
<body>
    {get_nav_html("companies")}
    <main class="main">
        <div class="page-header">
            <h1 class="page-title">Companies</h1>
            <p class="page-subtitle">{len(ALL_COMPANIES)} biotech companies with real-time catalyst tracking</p>
        </div>
        <div class="search-box">
            <input type="text" id="company-search" class="search-input" placeholder="Search by ticker, company name, or therapeutic area...">
        </div>
        <p class="results-count" id="results-count">Showing {len(ALL_COMPANIES)} companies</p>
        <nav class="category-nav">
            <div class="category-pills">{pills_html}</div>
        </nav>
        {sections_html}
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>

    <script>
        let activeCategory = 'all';

        function filterCompanies() {{
            const q = document.getElementById('company-search').value.toLowerCase();
            const cards = document.querySelectorAll('.company-card');
            const sections = document.querySelectorAll('.section');
            let total = 0;

            sections.forEach(section => {{
                const sectionId = section.id;
                const matchCategory = activeCategory === 'all' || sectionId === activeCategory;
                let sectionCount = 0;

                section.querySelectorAll('.company-card').forEach(card => {{
                    const text = card.textContent.toLowerCase();
                    const matchSearch = !q || text.includes(q);
                    if (matchCategory && matchSearch) {{
                        card.style.display = '';
                        sectionCount++;
                        total++;
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});

                section.style.display = sectionCount > 0 ? '' : 'none';
                const countBadge = section.querySelector('.section-count');
                if (countBadge) countBadge.textContent = sectionCount;
            }});

            document.getElementById('results-count').textContent = 'Showing ' + total + ' companies';
        }}

        document.querySelectorAll('.category-pill').forEach(pill => {{
            pill.addEventListener('click', (e) => {{
                e.preventDefault();
                document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                const href = pill.getAttribute('href');
                activeCategory = href === '#all' ? 'all' : href.replace('#', '');
                filterCompanies();
            }});
        }});

        document.getElementById('company-search').addEventListener('input', filterCompanies);

        // Check for search query in URL hash
        const hash = window.location.hash;
        if (hash.includes('search=')) {{
            const query = decodeURIComponent(hash.split('search=')[1]);
            document.getElementById('company-search').value = query;
            filterCompanies();
        }}
    </script>
</body>
</html>'''

def generate_targets_page():
    """Generate the targets page with category filters and search."""

    # All targets with full data from CLI
    targets = [
        # Oncology
        {"name": "KRAS G12C", "category": "oncology", "slug": "kras", "status": "Approved Drug Exists",
         "leader": {"company": "Amgen", "ticker": "AMGN", "drug": "Lumakras", "phase": "Approved"},
         "challenger": {"company": "Revolution", "ticker": "RVMD", "drug": "RMC-6236", "phase": "Phase 3"},
         "count": "8+", "desc": "Amgen, Mirati approved. Next-gen focus on combos."},
        {"name": "RAS(ON) Multi", "category": "oncology", "slug": "kras", "status": "Race to First",
         "leader": {"company": "Revolution", "ticker": "RVMD", "drug": "Daraxonrasib", "phase": "Phase 3"},
         "challenger": {"company": "Mirati/BMS", "ticker": "BMY", "drug": "MRTX1133", "phase": "Phase 1"},
         "count": "4", "desc": "First multi-RAS inhibitor; BTD granted."},
        {"name": "Menin-MLL", "category": "oncology", "slug": None, "status": "Approved Drug Exists",
         "leader": {"company": "Syndax", "ticker": "SNDX", "drug": "Revuforj", "phase": "Approved"},
         "challenger": {"company": "Kura", "ticker": "KURA", "drug": "Ziftomenib", "phase": "Phase 3"},
         "count": "3", "desc": "First-in-class for KMT2A AML."},
        {"name": "TIGIT", "category": "oncology", "slug": None, "status": "Race to First",
         "leader": {"company": "Arcus/Gilead", "ticker": "RCUS", "drug": "Domvanalimab", "phase": "Phase 3"},
         "challenger": {"company": "Merck", "ticker": "MRK", "drug": "Vibostolimab", "phase": "Phase 3"},
         "count": "10+", "desc": "Crowded checkpoint. Fc design matters."},
        {"name": "B7-H3", "category": "oncology", "slug": "b7h3-adc", "status": "Race to First",
         "leader": {"company": "Daiichi/Merck", "ticker": "DSNKY", "drug": "I-DXd", "phase": "Phase 3"},
         "challenger": {"company": "GSK", "ticker": "GSK", "drug": "HS-20093", "phase": "Phase 2"},
         "count": "23", "desc": "Highly expressed in solid tumors with limited normal tissue."},

        # Immunology
        {"name": "TL1A", "category": "immunology", "slug": "tl1a-ibd", "status": "Race to First",
         "leader": {"company": "Merck", "ticker": "MRK", "drug": "Tulisokibart", "phase": "Phase 3"},
         "challenger": {"company": "Sanofi", "ticker": "SNY", "drug": "Duvakitug", "phase": "Phase 3"},
         "count": "9", "desc": "Hot IBD target with anti-fibrotic potential."},
        {"name": "FcRn", "category": "immunology", "slug": None, "status": "Approved Drug Exists",
         "leader": {"company": "argenx", "ticker": "ARGX", "drug": "VYVGART", "phase": "Approved"},
         "challenger": {"company": "Immunovant", "ticker": "IMVT", "drug": "IMVT-1402", "phase": "Phase 3"},
         "count": "5", "desc": "$4B+ market. MG, CIDP, ITP."},
        {"name": "IL-4Ra / IL-13", "category": "immunology", "slug": None, "status": "Approved Drug Exists",
         "leader": {"company": "Regeneron", "ticker": "REGN", "drug": "Dupixent", "phase": "Approved"},
         "challenger": {"company": "Apogee", "ticker": "APGE", "drug": "APG777", "phase": "Phase 2"},
         "count": "4", "desc": "$13B+ blockbuster. Q12W dosing goal."},
        {"name": "KIT (mast cell)", "category": "immunology", "slug": None, "status": "Race to First",
         "leader": {"company": "Celldex", "ticker": "CLDX", "drug": "Barzolvolimab", "phase": "Phase 3"},
         "challenger": {"company": "Allakos", "ticker": "ALLK", "drug": "Various", "phase": "Phase 2"},
         "count": "3", "desc": "Mast cell depletion for urticaria."},

        # Metabolic
        {"name": "GLP-1/GIP dual", "category": "metabolic", "slug": "glp1-obesity", "status": "Approved Drug Exists",
         "leader": {"company": "Eli Lilly", "ticker": "LLY", "drug": "Mounjaro", "phase": "Approved"},
         "challenger": {"company": "Viking", "ticker": "VKTX", "drug": "VK2735", "phase": "Phase 3"},
         "count": "10+", "desc": "$50B+ market. Oral formulation key."},

        # Cardiovascular
        {"name": "Aldosterone synth", "category": "cardiovascular", "slug": None, "status": "Race to First",
         "leader": {"company": "Mineralys", "ticker": "MLYS", "drug": "Lorundrostat", "phase": "Phase 3"},
         "challenger": {"company": "Alnylam", "ticker": "ALNY", "drug": "Zilebesiran", "phase": "Phase 3"},
         "count": "3", "desc": "CYP11B2 for resistant HTN."},

        # Rare Disease
        {"name": "DMD gene therapy", "category": "rare", "slug": None, "status": "Approved Drug Exists",
         "leader": {"company": "Sarepta", "ticker": "SRPT", "drug": "Elevidys", "phase": "Approved"},
         "challenger": {"company": "Solid Bio", "ticker": "SLDB", "drug": "SGT-003", "phase": "Phase 1/2"},
         "count": "4", "desc": "First DMD gene therapy approved."},
        {"name": "Hepcidin mimetic", "category": "rare", "slug": None, "status": "Race to First",
         "leader": {"company": "Protagonist", "ticker": "PTGX", "drug": "Rusfertide", "phase": "NDA Filed"},
         "challenger": {"company": "Disc Med", "ticker": "IRON", "drug": "Various", "phase": "Phase 2"},
         "count": "2", "desc": "First-in-class for PV. Takeda partner."},

        # Neuropsychiatry
        {"name": "Nav1.6 / SCN8A", "category": "neuro", "slug": None, "status": "Early Stage",
         "leader": {"company": "Praxis", "ticker": "PRAX", "drug": "Relutrigine", "phase": "Phase 2/3"},
         "challenger": {"company": "None", "ticker": "-", "drug": "-", "phase": "-"},
         "count": "1", "desc": "BTD for SCN8A epilepsy. Low competition."},
        {"name": "T-type Ca2+ channel", "category": "neuro", "slug": None, "status": "Race to First",
         "leader": {"company": "Xenon", "ticker": "XENE", "drug": "Azetukalner", "phase": "Phase 3"},
         "challenger": {"company": "Idorsia", "ticker": "IDIA", "drug": "Various", "phase": "Phase 2"},
         "count": "2", "desc": "Kv7 mechanism for epilepsy."},
    ]

    # Category colors and labels
    category_styles = {
        "oncology": {"bg": "#fef2f2", "color": "#dc2626", "label": "Oncology"},
        "immunology": {"bg": "#f0fdf4", "color": "#16a34a", "label": "I&I"},
        "metabolic": {"bg": "#fef9c3", "color": "#ca8a04", "label": "Metabolic"},
        "cardiovascular": {"bg": "#eff6ff", "color": "#2563eb", "label": "Cardiovascular"},
        "rare": {"bg": "#faf5ff", "color": "#7c3aed", "label": "Rare Disease"},
        "neuro": {"bg": "#fef3c7", "color": "#92400e", "label": "Neuro"},
    }

    # Status colors
    status_styles = {
        "Approved Drug Exists": {"bg": "#dcfce7", "color": "#166534"},
        "Race to First": {"bg": "#fef9c3", "color": "#854d0e"},
        "Early Stage": {"bg": "#f3f4f6", "color": "#4b5563"},
    }

    # Build target cards
    cards_html = ""
    for t in targets:
        cat = category_styles.get(t["category"], {"bg": "#f3f4f6", "color": "#4b5563", "label": "Other"})
        status = status_styles.get(t["status"], {"bg": "#f3f4f6", "color": "#4b5563"})
        phase_colors = {"Approved": "#22c55e", "Phase 3": "#3b82f6", "Phase 2": "#f59e0b", "Phase 2/3": "#f59e0b", "Phase 1": "#6b7280", "Phase 1/2": "#6b7280", "NDA Filed": "#22c55e"}
        leader_phase_color = phase_colors.get(t["leader"]["phase"], "#6b7280")
        challenger_phase_color = phase_colors.get(t["challenger"]["phase"], "#6b7280")

        view_btn = f'<a href="/targets/{t["slug"]}" class="view-btn">View Full Landscape &rarr;</a>' if t["slug"] else ""

        cards_html += f'''
        <div class="target-card" data-category="{t["category"]}">
            <div class="target-header">
                <div class="target-name">{t["name"]}</div>
                <span class="area-badge" style="background:{cat["bg"]};color:{cat["color"]};">{cat["label"]}</span>
            </div>
            <div class="market-status" style="background:{status["bg"]};color:{status["color"]};">{t["status"]}</div>
            <div class="competitor-section">
                <div class="competitor-row">
                    <span class="competitor-label">{"Market Leader" if "Approved" in t["status"] else "Frontrunner"}</span>
                    <span class="competitor-info">
                        <span class="competitor-text"><span class="company">{t["leader"]["company"]}</span> (<span class="ticker">{t["leader"]["ticker"]}</span>) - {t["leader"]["drug"]}</span>
                        <span class="stage-pill" style="background:{leader_phase_color};">{t["leader"]["phase"]}</span>
                    </span>
                </div>
                <div class="competitor-row">
                    <span class="competitor-label">{"Challenger" if "Approved" in t["status"] else "Fast Follower"}</span>
                    <span class="competitor-info">
                        <span class="competitor-text"><span class="company">{t["challenger"]["company"]}</span> {f'(<span class="ticker">{t["challenger"]["ticker"]}</span>)' if t["challenger"]["ticker"] != "-" else ""} {f'- {t["challenger"]["drug"]}' if t["challenger"]["drug"] != "-" else ""}</span>
                        {f'<span class="stage-pill" style="background:{challenger_phase_color};">{t["challenger"]["phase"]}</span>' if t["challenger"]["phase"] != "-" else ""}
                    </span>
                </div>
            </div>
            <div class="target-footer">
                <div class="companies-count"><strong>{t["count"]}</strong> companies pursuing</div>
                <p class="target-desc">{t["desc"]}</p>
                {view_btn}
            </div>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Explore Drug Targets | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .targets-layout {{ display: grid; grid-template-columns: 240px 1fr; gap: 32px; }}
        @media (max-width: 900px) {{ .targets-layout {{ grid-template-columns: 1fr; }} }}

        /* Sidebar */
        .filters-sidebar {{ position: sticky; top: 80px; height: fit-content; }}
        .filter-section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }}
        .filter-section h4 {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 12px; }}
        .filter-option {{ display: flex; align-items: center; gap: 8px; padding: 8px 0; cursor: pointer; font-size: 0.9rem; color: var(--text-secondary); }}
        .filter-option:hover {{ color: var(--navy); }}
        .filter-option input {{ display: none; }}
        .filter-dot {{ width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--border); }}
        .filter-option.active .filter-dot {{ background: var(--accent); border-color: var(--accent); }}
        .filter-option.active {{ color: var(--navy); font-weight: 500; }}

        /* Search */
        .search-box {{ margin-bottom: 24px; }}
        .search-input {{ width: 100%; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; }}
        .search-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }}

        /* Targets grid */
        .targets-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
        .targets-meta {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 16px; }}

        /* Target card */
        .target-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; transition: all 0.2s; }}
        .target-card:hover {{ border-color: var(--accent); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
        .target-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }}
        .target-name {{ font-size: 1.1rem; font-weight: 700; color: var(--navy); }}
        .area-badge {{ padding: 4px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }}
        .market-status {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; }}

        .competitor-section {{ margin-bottom: 12px; }}
        .competitor-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.85rem; }}
        .competitor-row:last-child {{ border-bottom: none; }}
        .competitor-label {{ color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; min-width: 90px; }}
        .competitor-info {{ display: flex; align-items: center; gap: 8px; flex: 1; justify-content: flex-end; text-align: right; }}
        .competitor-text {{ color: var(--text-secondary); }}
        .competitor-text .company {{ color: var(--navy); font-weight: 500; }}
        .competitor-text .ticker {{ color: var(--accent); }}
        .stage-pill {{ padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; color: white; }}

        .target-footer {{ padding-top: 12px; }}
        .companies-count {{ font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px; }}
        .target-desc {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 10px; }}
        .view-btn {{ display: inline-block; color: var(--accent); font-weight: 600; font-size: 0.85rem; text-decoration: none; }}
        .view-btn:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <div class="page-header">
            <h1 class="page-title">Explore Drug Targets</h1>
            <p class="page-subtitle">Deep-dive research on validated and emerging therapeutic targets with competitive landscapes, clinical data, and deal activity.</p>
        </div>

        <div class="search-box">
            <input type="text" id="target-search" class="search-input" placeholder="Search by target name, gene, or therapeutic area...">
        </div>

        <div class="targets-layout">
            <aside class="filters-sidebar">
                <div class="filter-section">
                    <h4>Therapeutic Area</h4>
                    <label class="filter-option active" data-filter="all">
                        <span class="filter-dot"></span>
                        All Targets
                    </label>
                    <label class="filter-option" data-filter="oncology">
                        <span class="filter-dot" style="border-color:#dc2626;"></span>
                        Oncology
                    </label>
                    <label class="filter-option" data-filter="immunology">
                        <span class="filter-dot" style="border-color:#16a34a;"></span>
                        Immunology
                    </label>
                    <label class="filter-option" data-filter="metabolic">
                        <span class="filter-dot" style="border-color:#ca8a04;"></span>
                        Metabolic
                    </label>
                    <label class="filter-option" data-filter="cardiovascular">
                        <span class="filter-dot" style="border-color:#2563eb;"></span>
                        Cardiovascular
                    </label>
                    <label class="filter-option" data-filter="rare">
                        <span class="filter-dot" style="border-color:#7c3aed;"></span>
                        Rare Disease
                    </label>
                    <label class="filter-option" data-filter="neuro">
                        <span class="filter-dot" style="border-color:#92400e;"></span>
                        Neuropsychiatry
                    </label>
                </div>
            </aside>

            <section class="targets-section">
                <p class="targets-meta" id="targets-count">Showing {len(targets)} targets</p>
                <div class="targets-grid" id="targets-grid">
                    {cards_html}
                </div>
            </section>
        </div>
    </main>

    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>

    <script>
        let activeFilter = 'all';

        function applyFilters() {{
            const cards = document.querySelectorAll('.target-card');
            const q = document.getElementById('target-search').value.toLowerCase();
            let count = 0;
            cards.forEach(card => {{
                const cat = card.dataset.category || '';
                const text = card.textContent.toLowerCase();
                const matchCategory = activeFilter === 'all' || cat === activeFilter;
                const matchSearch = !q || text.includes(q);
                if (matchCategory && matchSearch) {{
                    card.style.display = '';
                    count++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            document.getElementById('targets-count').textContent = 'Showing ' + count + ' targets';
        }}

        document.querySelectorAll('.filter-option').forEach(option => {{
            option.addEventListener('click', (e) => {{
                e.preventDefault();
                document.querySelectorAll('.filter-option').forEach(o => o.classList.remove('active'));
                option.classList.add('active');
                activeFilter = option.dataset.filter;
                applyFilters();
            }});
        }});

        document.getElementById('target-search').addEventListener('input', applyFilters);
    </script>
</body>
</html>'''

def generate_kols_page():
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KOL Finder | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .search-section {{ max-width: 700px; margin: 0 auto 48px; text-align: center; }}
        .search-box {{ position: relative; margin-top: 24px; }}
        .search-input {{ width: 100%; padding: 18px 24px; border: 2px solid var(--border); border-radius: 14px; font-size: 1.1rem; outline: none; }}
        .search-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 4px rgba(224,122,95,0.15); }}
        .search-hint {{ margin-top: 12px; color: var(--text-muted); font-size: 0.9rem; }}
        .examples {{ margin-top: 48px; }}
        .example-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 24px; }}
        .example-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; cursor: pointer; }}
        .example-card:hover {{ border-color: var(--accent); }}
        .example-card h4 {{ color: var(--navy); margin-bottom: 8px; }}
        .example-card p {{ color: var(--text-secondary); font-size: 0.85rem; }}
    </style>
</head>
<body>
    {get_nav_html("kols")}
    <main class="main">
        <div class="search-section">
            <h1 class="page-title">Find Key Opinion Leaders</h1>
            <p class="page-subtitle">Search by target, disease, or therapeutic area</p>
            <div class="search-box">
                <input type="text" class="search-input" placeholder="e.g., GLP-1 obesity, KRAS oncology, TL1A IBD...">
            </div>
            <p class="search-hint">Search connects to PubMed and ClinicalTrials.gov for real KOL data</p>
        </div>
        <div class="examples">
            <h2 style="text-align: center; color: var(--navy);">Popular Searches</h2>
            <div class="example-grid">
                <div class="example-card">
                    <h4>GLP-1 Obesity</h4>
                    <p>Key researchers in incretin-based obesity therapeutics</p>
                </div>
                <div class="example-card">
                    <h4>KRAS G12C Oncology</h4>
                    <p>Leaders in RAS-targeted cancer therapy development</p>
                </div>
                <div class="example-card">
                    <h4>TL1A Inflammatory Bowel Disease</h4>
                    <p>Experts in next-gen IBD biologics</p>
                </div>
                <div class="example-card">
                    <h4>Gene Therapy Rare Disease</h4>
                    <p>Pioneers in AAV and gene editing therapeutics</p>
                </div>
            </div>
        </div>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''

def generate_about_page():
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .about-content {{ max-width: 700px; margin: 0 auto; }}
        .about-content h1 {{ font-size: 2.5rem; margin-bottom: 24px; }}
        .about-content p {{ font-size: 1.1rem; line-height: 1.8; margin-bottom: 24px; color: var(--text-secondary); }}
        .about-content h2 {{ font-size: 1.5rem; margin: 48px 0 16px; color: var(--navy); }}
        .feature-list {{ list-style: none; padding: 0; }}
        .feature-list li {{ padding: 12px 0; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }}
        .feature-list li::before {{ content: "✓"; color: var(--accent); font-weight: bold; }}
    </style>
</head>
<body>
    {get_nav_html("about")}
    <main class="main">
        <div class="about-content">
            <h1>Biotech Intelligence for the Buy Side</h1>
            <p>Satya Bio provides institutional investors with comprehensive biotech competitive intelligence. We track 145+ public biotech companies, monitor catalyst timelines, and analyze competitive landscapes across therapeutic areas.</p>

            <h2>What We Track</h2>
            <ul class="feature-list">
                <li>Pipeline data for 145+ biotech companies</li>
                <li>Real-time catalyst monitoring and alerts</li>
                <li>Competitive landscapes for hot targets (GLP-1, TL1A, KRAS, etc.)</li>
                <li>Key Opinion Leader identification via PubMed</li>
                <li>SEC filing analysis and ownership tracking</li>
                <li>Clinical trial data from ClinicalTrials.gov</li>
            </ul>

            <h2>Contact</h2>
            <p>For early access or inquiries: <a href="mailto:hello@satyabio.com" style="color: var(--accent);">hello@satyabio.com</a></p>
        </div>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''

def generate_glp1_report():
    """Generate the GLP-1 / Obesity competitive landscape report."""

    # Approved drugs data
    approved_drugs = [
        {"name": "Wegovy", "generic": "semaglutide", "company": "Novo Nordisk", "mechanism": "GLP-1 agonist", "route": "SC weekly", "approval": "2021", "indication": "Obesity", "weight_loss": "~15%", "revenue_2024": "$6.2B"},
        {"name": "Zepbound", "generic": "tirzepatide", "company": "Eli Lilly", "mechanism": "GLP-1/GIP dual", "route": "SC weekly", "approval": "2023", "indication": "Obesity", "weight_loss": "~21%", "revenue_2024": "$1.2B"},
        {"name": "Ozempic", "generic": "semaglutide", "company": "Novo Nordisk", "mechanism": "GLP-1 agonist", "route": "SC weekly", "approval": "2017", "indication": "T2D (off-label obesity)", "weight_loss": "~12%", "revenue_2024": "$18.4B"},
        {"name": "Mounjaro", "generic": "tirzepatide", "company": "Eli Lilly", "mechanism": "GLP-1/GIP dual", "route": "SC weekly", "approval": "2022", "indication": "T2D", "weight_loss": "~18%", "revenue_2024": "$7.4B"},
        {"name": "Saxenda", "generic": "liraglutide", "company": "Novo Nordisk", "mechanism": "GLP-1 agonist", "route": "SC daily", "approval": "2014", "indication": "Obesity", "weight_loss": "~8%", "revenue_2024": "$0.8B"},
        {"name": "Rybelsus", "generic": "semaglutide", "company": "Novo Nordisk", "mechanism": "GLP-1 agonist", "route": "Oral daily", "approval": "2019", "indication": "T2D", "weight_loss": "~10%", "revenue_2024": "$2.8B"},
    ]

    # Pipeline drugs data
    pipeline_drugs = [
        {"asset": "VK2735 (SC)", "company": "Viking Therapeutics", "ticker": "VKTX", "mechanism": "GLP-1/GIP dual", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "14.7% (13 wks)", "catalyst": "Ph3 VENTURE interim Q1 2026", "differentiation": "Potentially best-in-class efficacy"},
        {"asset": "VK2735 (Oral)", "company": "Viking Therapeutics", "ticker": "VKTX", "mechanism": "GLP-1/GIP dual", "phase": "Phase 2b", "route": "Oral daily", "weight_loss": "8.2% (28 days)", "catalyst": "Ph2b data H1 2026", "differentiation": "Oral convenience + dual agonism"},
        {"asset": "MariTide (AMG 133)", "company": "Amgen", "ticker": "AMGN", "mechanism": "GLP-1 agonist / GIPR antagonist", "phase": "Phase 3", "route": "SC monthly", "weight_loss": "14.5% (12 wks)", "catalyst": "Ph3 data H1 2026", "differentiation": "Monthly dosing, sustained effect after discontinuation"},
        {"asset": "Orforglipron", "company": "Eli Lilly", "ticker": "LLY", "mechanism": "GLP-1 agonist (small molecule)", "phase": "Phase 3", "route": "Oral daily", "weight_loss": "14.7% (36 wks)", "catalyst": "Ph3 ATTAIN-3 Q2 2026", "differentiation": "Oral small molecule, easier manufacturing"},
        {"asset": "Retatrutide", "company": "Eli Lilly", "ticker": "LLY", "mechanism": "GLP-1/GIP/Glucagon triple", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "24.2% (48 wks)", "catalyst": "FDA submission Q1 2026", "differentiation": "Best-in-class weight loss, triple agonism"},
        {"asset": "CagriSema", "company": "Novo Nordisk", "ticker": "NVO", "mechanism": "Semaglutide + Amylin", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~25% (est)", "catalyst": "FDA submission Q2 2026", "differentiation": "Best-in-class efficacy, amylin synergy"},
        {"asset": "Survodutide", "company": "Boehringer / Zealand", "ticker": "Private", "mechanism": "GLP-1/Glucagon dual", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "18.7% (46 wks)", "catalyst": "Ph3 SYNCHRONIZE-2 H2 2026", "differentiation": "Glucagon component may improve MASH"},
        {"asset": "Pemvidutide", "company": "Altimmune", "ticker": "ALT", "mechanism": "GLP-1/Glucagon dual", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "15.6% (48 wks)", "catalyst": "Ph3 data 2026", "differentiation": "MASH + obesity dual indication"},
        {"asset": "Ecnoglutide", "company": "Sciwind Biosciences", "ticker": "Private", "mechanism": "GLP-1 agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~15%", "catalyst": "China NDA 2026", "differentiation": "China-focused development"},
        {"asset": "HRS9531", "company": "Jiangsu Hengrui", "ticker": "600276.SS", "mechanism": "GLP-1/GIP dual", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "16.8% (24 wks)", "catalyst": "China NDA H2 2026", "differentiation": "Leading Chinese GLP-1"},
        {"asset": "ARO-INHBE", "company": "Arrowhead Pharma", "ticker": "ARWR", "mechanism": "RNAi (INHBE silencing)", "phase": "Phase 2", "route": "SC quarterly", "weight_loss": "TBD", "catalyst": "Ph2 initiation H2 2026", "differentiation": "RNAi approach, infrequent dosing"},
        {"asset": "Petrelintide", "company": "Novo Nordisk", "ticker": "NVO", "mechanism": "Long-acting amylin analog", "phase": "Phase 2", "route": "SC weekly", "weight_loss": "~10%", "catalyst": "Ph2 combo data 2026", "differentiation": "Potential combo with semaglutide"},
    ]

    # Build approved drugs table
    approved_rows = ""
    for drug in approved_drugs:
        approved_rows += f'''
        <tr>
            <td><strong>{drug["name"]}</strong><br><span style="color: var(--text-muted); font-size: 0.8rem;">{drug["generic"]}</span></td>
            <td>{drug["company"]}</td>
            <td>{drug["mechanism"]}</td>
            <td>{drug["route"]}</td>
            <td><strong style="color: var(--accent);">{drug["weight_loss"]}</strong></td>
            <td>{drug["revenue_2024"]}</td>
        </tr>
        '''

    # Build pipeline drugs table
    pipeline_rows = ""
    for drug in pipeline_drugs:
        phase_color = "#22c55e" if "Phase 3" in drug["phase"] else "#f59e0b" if "Phase 2" in drug["phase"] else "#6b7280"
        pipeline_rows += f'''
        <tr>
            <td><strong>{drug["asset"]}</strong></td>
            <td>{drug["company"]}<br><span style="color: var(--accent); font-size: 0.8rem;">{drug["ticker"]}</span></td>
            <td>{drug["mechanism"]}</td>
            <td><span style="background: {phase_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">{drug["phase"]}</span></td>
            <td><strong>{drug["weight_loss"]}</strong></td>
            <td>{drug["catalyst"]}</td>
        </tr>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GLP-1 / Obesity Competitive Landscape | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .report-header {{
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }}
        .report-header h1 {{ font-size: 2.25rem; margin-bottom: 8px; }}
        .report-header p {{ opacity: 0.85; max-width: 700px; font-size: 1.1rem; }}
        .report-meta {{ display: flex; gap: 24px; margin-top: 24px; }}
        .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }}
        .meta-item .label {{ font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }}
        .meta-item .value {{ font-size: 1.25rem; font-weight: 700; }}

        .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
        .section h2 {{ color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}
        .section h3 {{ color: var(--navy); font-size: 1.1rem; margin: 24px 0 16px; }}

        .market-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 24px 0; }}
        .market-stat {{ background: var(--bg); padding: 24px; border-radius: 12px; text-align: center; }}
        .market-stat .value {{ font-size: 2rem; font-weight: 700; color: var(--accent); }}
        .market-stat .label {{ color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; }}

        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th {{ background: var(--navy); color: white; padding: 14px 12px; text-align: left; font-weight: 600; }}
        td {{ padding: 14px 12px; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background: var(--bg); }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 12px; }}
        .bull-box {{ background: #ecfdf5; border: 1px solid #10b981; }}
        .bear-box {{ background: #fef2f2; border: 1px solid #ef4444; }}
        .bull-box h3 {{ color: #059669; }}
        .bear-box h3 {{ color: #dc2626; }}
        .thesis-list {{ list-style: none; padding: 0; margin-top: 16px; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }}
        .thesis-list li:last-child {{ border-bottom: none; }}
        .thesis-list li::before {{ content: "\\2192"; font-weight: bold; }}

        .catalyst-timeline {{ margin-top: 20px; }}
        .catalyst-item {{ display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }}
        .catalyst-date {{ min-width: 100px; font-weight: 700; color: var(--accent); }}
        .catalyst-content strong {{ color: var(--navy); }}

        .back-link {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <div class="report-header">
            <h1>GLP-1 / Obesity Competitive Landscape</h1>
            <p>Comprehensive analysis of the incretin-based therapeutics market for obesity and type 2 diabetes. The GLP-1 class represents the largest commercial opportunity in pharma history.</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Market Size (2030E)</div><div class="value">$150B+</div></div>
                <div class="meta-item"><div class="label">Patient Population</div><div class="value">800M+ globally</div></div>
                <div class="meta-item"><div class="label">Assets in Development</div><div class="value">25+</div></div>
                <div class="meta-item"><div class="label">Approved Drugs</div><div class="value">6</div></div>
            </div>
        </div>

        <!-- Market Overview -->
        <div class="section">
            <h2>Market Overview</h2>
            <div class="market-stats">
                <div class="market-stat"><div class="value">$50B</div><div class="label">2024 GLP-1 Market</div></div>
                <div class="market-stat"><div class="value">42%</div><div class="label">Adult Obesity Rate (US)</div></div>
                <div class="market-stat"><div class="value">537M</div><div class="label">Global Diabetics</div></div>
                <div class="market-stat"><div class="value">~15-25%</div><div class="label">Weight Loss Range</div></div>
            </div>
            <p style="color: var(--text-secondary); line-height: 1.7;">
                The GLP-1 receptor agonist class has transformed obesity treatment, achieving weight loss previously only possible with bariatric surgery.
                The market is dominated by <strong>Novo Nordisk</strong> (Wegovy, Ozempic) and <strong>Eli Lilly</strong> (Zepbound, Mounjaro), with combined 2024 revenues exceeding $35B.
                Supply constraints persist, driving urgency for next-generation therapies. Key differentiators include: oral vs. injectable, dosing frequency,
                weight loss efficacy, GI tolerability, and cardiometabolic benefits beyond weight.
            </p>

            <h3>Key Market Dynamics</h3>
            <ul style="color: var(--text-secondary); line-height: 1.9; padding-left: 20px;">
                <li><strong>Supply shortage:</strong> Demand far exceeds manufacturing capacity; Novo and Lilly investing $10B+ in capacity expansion</li>
                <li><strong>Payer coverage:</strong> Medicare currently excludes obesity drugs; legislation pending to change this (Treat & Reduce Obesity Act)</li>
                <li><strong>Beyond obesity:</strong> CV outcomes (SELECT trial), MASH, CKD, sleep apnea indications expanding addressable market</li>
                <li><strong>Oral competition:</strong> First oral small molecule GLP-1s (orforglipron, oral semaglutide) could expand market 2-3x</li>
            </ul>
        </div>

        <!-- Approved Drugs -->
        <div class="section">
            <h2>Approved Drugs</h2>
            <table>
                <thead>
                    <tr>
                        <th>Drug</th>
                        <th>Company</th>
                        <th>Mechanism</th>
                        <th>Route</th>
                        <th>Weight Loss</th>
                        <th>2024 Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {approved_rows}
                </tbody>
            </table>
        </div>

        <!-- Pipeline -->
        <div class="section">
            <h2>Pipeline Assets</h2>
            <table>
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Company</th>
                        <th>Mechanism</th>
                        <th>Phase</th>
                        <th>Weight Loss</th>
                        <th>Next Catalyst</th>
                    </tr>
                </thead>
                <tbody>
                    {pipeline_rows}
                </tbody>
            </table>
        </div>

        <!-- Bull/Bear Thesis -->
        <div class="section">
            <h2>Investment Thesis</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>Market size could reach $150B+ by 2030, larger than any therapeutic class in history</li>
                        <li>Medicare coverage (Treat & Reduce Obesity Act) would add 30M+ addressable patients</li>
                        <li>Beyond obesity: MASH, CKD, heart failure, sleep apnea expand TAM 2-3x</li>
                        <li>Oral formulations remove injection barrier, massively expanding uptake</li>
                        <li>Monthly dosing (Amgen's MariTide) improves compliance vs. weekly</li>
                        <li>Weight maintenance after stopping less concerning with newer agents</li>
                        <li>Chronic therapy model = multi-decade revenue streams</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>GI side effects (nausea, vomiting) limit tolerability; 10-15% discontinuation</li>
                        <li>Muscle loss concerns may require combination with exercise/protein</li>
                        <li>Insurance coverage gaps; $1,000+/month cash pay limits adoption</li>
                        <li>Compounding pharmacies eroding brand pricing power</li>
                        <li>Long-term safety unknowns (thyroid cancer signals in rodents)</li>
                        <li>Lilly and Novo duopoly may squeeze out smaller players</li>
                        <li>Weight regain after discontinuation (15-20% regain at 1 year)</li>
                        <li>Manufacturing complexity limits rapid capacity expansion</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Catalysts -->
        <div class="section">
            <h2>Upcoming Catalysts (2026)</h2>
            <div class="catalyst-timeline">
                <div class="catalyst-item">
                    <div class="catalyst-date">Q1 2026</div>
                    <div class="catalyst-content"><strong>Viking (VKTX):</strong> VK2735 Phase 3 VENTURE interim efficacy data (obesity)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">Q1 2026</div>
                    <div class="catalyst-content"><strong>Eli Lilly (LLY):</strong> Retatrutide FDA submission for obesity (triple agonist)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">Q2 2026</div>
                    <div class="catalyst-content"><strong>Novo Nordisk (NVO):</strong> CagriSema FDA submission expected (semaglutide + amylin)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">Q2 2026</div>
                    <div class="catalyst-content"><strong>Eli Lilly (LLY):</strong> Orforglipron Phase 3 ATTAIN-3 data (oral small molecule GLP-1)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H1 2026</div>
                    <div class="catalyst-content"><strong>Amgen (AMGN):</strong> MariTide Phase 3 data readout; monthly dosing differentiation</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H1 2026</div>
                    <div class="catalyst-content"><strong>Viking (VKTX):</strong> Oral VK2735 Phase 2b full data readout</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H2 2026</div>
                    <div class="catalyst-content"><strong>Boehringer/Zealand:</strong> Survodutide Phase 3 SYNCHRONIZE-2 topline (GLP-1/glucagon)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H2 2026</div>
                    <div class="catalyst-content"><strong>Arrowhead (ARWR):</strong> ARO-INHBE Phase 2 initiation (RNAi approach for obesity)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2026</div>
                    <div class="catalyst-content"><strong>Eli Lilly (LLY):</strong> Retatrutide potential FDA approval (best-in-class 24% weight loss)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2026</div>
                    <div class="catalyst-content"><strong>Regulatory:</strong> Medicare Part D obesity drug coverage decision (Treat & Reduce Obesity Act)</div>
                </div>
            </div>
        </div>

        <!-- Key Companies -->
        <div class="section">
            <h2>Key Companies to Watch</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 20px;">
                <a href="/api/company/VKTX/html" style="display: block; background: var(--bg); padding: 20px; border-radius: 12px; text-decoration: none; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: var(--navy);">Viking Therapeutics</strong>
                        <span style="color: var(--accent);">VKTX</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">Best-in-class Ph2 data; oral + SC in development</p>
                </a>
                <a href="/api/company/AMGN/html" style="display: block; background: var(--bg); padding: 20px; border-radius: 12px; text-decoration: none; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: var(--navy);">Amgen</strong>
                        <span style="color: var(--accent);">AMGN</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">MariTide monthly dosing; weight maintenance</p>
                </a>
                <a href="/api/company/ALT/html" style="display: block; background: var(--bg); padding: 20px; border-radius: 12px; text-decoration: none; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: var(--navy);">Altimmune</strong>
                        <span style="color: var(--accent);">ALT</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">Pemvidutide for obesity + MASH dual play</p>
                </a>
                <a href="/api/company/ARWR/html" style="display: block; background: var(--bg); padding: 20px; border-radius: 12px; text-decoration: none; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: var(--navy);">Arrowhead Pharma</strong>
                        <span style="color: var(--accent);">ARWR</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">RNAi approach (ARO-INHBE); quarterly dosing</p>
                </a>
            </div>
        </div>

        <a href="/targets" class="back-link">← Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


def generate_tl1a_report():
    """Generate the TL1A / IBD competitive landscape report."""

    # TL1A Assets data
    assets = [
        {"asset": "Tulisokibart (PRA023)", "company": "Merck (via Prometheus)", "ticker": "MRK", "phase": "Phase 3", "indication": "UC, CD", "deal": "$10.8B acquisition", "efficacy": "26% remission (TL1A-high)", "catalyst": "ARTEMIS-CD Ph3 H2 2025"},
        {"asset": "Duvakitug (TEV-48574)", "company": "Sanofi / Teva", "ticker": "SNY", "phase": "Phase 3", "indication": "UC, CD", "deal": "$1B+ partnership", "efficacy": "47.8% remission (1000mg)", "catalyst": "Ph3 UC initiation Q1 2025"},
        {"asset": "Afimkibart (RVT-3101)", "company": "Roche (via Telavant)", "ticker": "RHHBY", "phase": "Phase 3", "indication": "UC, CD", "deal": "$7.25B acquisition", "efficacy": "35% remission", "catalyst": "Ph3 UC data 2026"},
        {"asset": "SAR443765", "company": "Sanofi", "ticker": "SNY", "phase": "Phase 2", "indication": "UC, CD", "deal": "Internal", "efficacy": "Bispecific (TL1A + IL-23)", "catalyst": "Ph2 data 2025"},
        {"asset": "PF-07258669", "company": "Pfizer", "ticker": "PFE", "phase": "Phase 1", "indication": "IBD", "deal": "Internal", "efficacy": "Early stage", "catalyst": "Ph1 data 2025"},
        {"asset": "ABBV-261", "company": "AbbVie", "ticker": "ABBV", "phase": "Phase 1", "indication": "IBD", "deal": "Internal", "efficacy": "Early stage", "catalyst": "Ph1 data 2025"},
    ]

    # Efficacy comparison data
    efficacy_data = [
        {"drug": "Duvakitug 1000mg", "trial": "RELIEVE UCCD", "endpoint": "Clinical Remission", "result": "47.8%", "placebo": "20.4%", "delta": "+27.4%", "population": "All comers"},
        {"drug": "Duvakitug 500mg", "trial": "RELIEVE UCCD", "endpoint": "Clinical Remission", "result": "32.6%", "placebo": "20.4%", "delta": "+12.2%", "population": "All comers"},
        {"drug": "Tulisokibart", "trial": "ARTEMIS-UC", "endpoint": "Clinical Remission", "result": "26%", "placebo": "1%", "delta": "+25%", "population": "TL1A-high only"},
        {"drug": "Tulisokibart", "trial": "ARTEMIS-UC", "endpoint": "Endoscopic Improvement", "result": "49%", "placebo": "13%", "delta": "+36%", "population": "TL1A-high only"},
        {"drug": "Afimkibart", "trial": "Phase 2", "endpoint": "Clinical Remission", "result": "35%", "placebo": "12%", "delta": "+23%", "population": "All comers"},
    ]

    # Build assets table
    assets_rows = ""
    for a in assets:
        phase_color = "#22c55e" if "Phase 3" in a["phase"] else "#f59e0b" if "Phase 2" in a["phase"] else "#6b7280"
        assets_rows += f'''
        <tr>
            <td><strong>{a["asset"]}</strong></td>
            <td>{a["company"]}<br><span style="color: var(--accent); font-size: 0.8rem;">{a["ticker"]}</span></td>
            <td><span style="background: {phase_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">{a["phase"]}</span></td>
            <td>{a["indication"]}</td>
            <td style="color: var(--accent); font-weight: 600;">{a["deal"]}</td>
            <td>{a["catalyst"]}</td>
        </tr>
        '''

    # Build efficacy table
    efficacy_rows = ""
    for e in efficacy_data:
        efficacy_rows += f'''
        <tr>
            <td><strong>{e["drug"]}</strong></td>
            <td>{e["trial"]}</td>
            <td>{e["endpoint"]}</td>
            <td>{e["result"]}</td>
            <td>{e["placebo"]}</td>
            <td style="color: #22c55e; font-weight: 700;">{e["delta"]}</td>
            <td>{e["population"]}</td>
        </tr>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TL1A / IBD Competitive Landscape | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .report-header {{
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }}
        .report-header h1 {{ font-size: 2.25rem; margin-bottom: 8px; }}
        .report-header p {{ opacity: 0.85; max-width: 700px; font-size: 1.1rem; }}
        .report-meta {{ display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }}
        .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }}
        .meta-item .label {{ font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }}
        .meta-item .value {{ font-size: 1.25rem; font-weight: 700; }}

        .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
        .section h2 {{ color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}

        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background: var(--bg); }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 12px; }}
        .bull-box {{ background: #ecfdf5; border: 1px solid #10b981; }}
        .bear-box {{ background: #fef2f2; border: 1px solid #ef4444; }}
        .bull-box h3 {{ color: #059669; }}
        .bear-box h3 {{ color: #dc2626; }}
        .thesis-list {{ list-style: none; padding: 0; margin-top: 16px; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }}
        .thesis-list li:last-child {{ border-bottom: none; }}
        .thesis-list li::before {{ content: "\\2192"; font-weight: bold; }}

        .mechanism-box {{ background: var(--bg); padding: 20px; border-radius: 12px; margin-top: 16px; }}
        .mechanism-box h4 {{ color: var(--navy); margin-bottom: 8px; }}
        .mechanism-box p {{ color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; }}

        .catalyst-timeline {{ margin-top: 20px; }}
        .catalyst-item {{ display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }}
        .catalyst-date {{ min-width: 100px; font-weight: 700; color: var(--accent); }}

        .back-link {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <div class="report-header">
            <h1>TL1A / IBD Competitive Landscape</h1>
            <p>TL1A (TNFSF15) is the hottest target in inflammatory bowel disease with $22B+ in M&A activity. Unique dual mechanism addresses both inflammation AND fibrosis.</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Total Deal Value</div><div class="value">$22B+</div></div>
                <div class="meta-item"><div class="label">Assets in Development</div><div class="value">9+</div></div>
                <div class="meta-item"><div class="label">Phase 3 Programs</div><div class="value">3</div></div>
                <div class="meta-item"><div class="label">Patient Population</div><div class="value">3.5M (US/EU)</div></div>
            </div>
        </div>

        <!-- Investment Thesis -->
        <div class="section">
            <h2>Investment Thesis</h2>
            <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 20px;">
                <strong style="color: var(--navy);">TL1A is the most significant new target in IBD since anti-TNF biologics.</strong>
                The target is genetically validated through GWAS studies showing TNFSF15 variants are associated with Crohn's disease risk.
                Unlike existing therapies that only address inflammation, TL1A inhibition blocks BOTH inflammatory cytokine production AND intestinal fibrosis —
                addressing the key unmet need of stricturing/fistulizing disease that affects 30-50% of Crohn's patients.
            </p>

            <div class="mechanism-box">
                <h4>Why TL1A is Unique</h4>
                <p>TL1A binds DR3 (death receptor 3), promoting Th1/Th17 differentiation and activating fibroblasts. Blocking TL1A interrupts both the inflammatory cascade AND the fibrotic pathway. Existing therapies (anti-TNF, anti-IL-23, JAKi) only target inflammation, leaving fibrosis/strictures unaddressed.</p>
            </div>
        </div>

        <!-- Competitive Landscape -->
        <div class="section">
            <h2>Competitive Landscape</h2>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">
                The investment landscape is unprecedented: Merck acquired Prometheus for <strong>$10.8B</strong>, and Roche acquired Telavant for <strong>$7.25B</strong>.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Company</th>
                        <th>Phase</th>
                        <th>Indication</th>
                        <th>Deal</th>
                        <th>Next Catalyst</th>
                    </tr>
                </thead>
                <tbody>
                    {assets_rows}
                </tbody>
            </table>
        </div>

        <!-- Efficacy Comparison -->
        <div class="section">
            <h2>Efficacy Comparison (Phase 2 Data)</h2>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">Cross-trial comparison is challenging but directionally informative. Duvakitug shows highest absolute numbers; Tulisokibart uses biomarker selection.</p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Drug</th>
                            <th>Trial</th>
                            <th>Endpoint</th>
                            <th>Result</th>
                            <th>Placebo</th>
                            <th>Delta</th>
                            <th>Population</th>
                        </tr>
                    </thead>
                    <tbody>
                        {efficacy_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Bull/Bear -->
        <div class="section">
            <h2>Bull vs Bear</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>Genetic validation: TNFSF15 variants in GWAS = high probability of success</li>
                        <li>Dual mechanism (inflammation + fibrosis) is unique vs. all other IBD drugs</li>
                        <li>$22B+ already committed = pharma conviction in the target</li>
                        <li>Best-in-class efficacy: 27% placebo-adjusted remission (duvakitug)</li>
                        <li>$25B IBD market growing to $35B by 2030; 40% inadequate response to current therapies</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Crowded landscape: 3+ Phase 3 assets racing; differentiation unclear</li>
                        <li>Cross-trial comparison challenges: different endpoints, populations</li>
                        <li>Payer resistance if not clearly better than existing biologics</li>
                        <li>Long development timelines: Phase 3 readouts 2025-2026</li>
                        <li>Fibrosis benefit still theoretical; not proven in humans yet</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Catalysts -->
        <div class="section">
            <h2>Upcoming Catalysts</h2>
            <div class="catalyst-timeline">
                <div class="catalyst-item">
                    <div class="catalyst-date">Q1 2025</div>
                    <div><strong>Sanofi/Teva:</strong> Duvakitug Phase 3 initiation in UC</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H2 2025</div>
                    <div><strong>Merck:</strong> Tulisokibart ARTEMIS-CD Phase 3 readout (Crohn's Disease)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H2 2025</div>
                    <div><strong>Sanofi/Teva:</strong> Duvakitug Phase 2 data in Crohn's Disease</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">H1 2026</div>
                    <div><strong>Merck:</strong> Tulisokibart ARTEMIS-UC Phase 3 readout (Ulcerative Colitis)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2026</div>
                    <div><strong>Roche:</strong> Afimkibart Phase 3 readout in UC</div>
                </div>
            </div>
        </div>

        <a href="/targets" class="back-link">← Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


def generate_b7h3_report():
    """Generate the B7-H3 / ADC competitive landscape report."""

    # B7-H3 Assets data
    assets = [
        {"asset": "Ifinatamab deruxtecan (DS-7300)", "company": "Daiichi Sankyo / Merck", "ticker": "DSNKY/MRK", "phase": "Phase 3", "modality": "ADC (DXd)", "indication": "SCLC, NSCLC, Solid tumors", "deal": "$22B partnership", "orr": "52% (ES-SCLC)", "catalyst": "TROPION-Lung08 H2 2025"},
        {"asset": "HS-20093", "company": "GSK (via Hansoh)", "ticker": "GSK", "phase": "Phase 2", "modality": "ADC", "indication": "SCLC", "deal": "$1.7B", "orr": "75% (ES-SCLC 2L+)", "catalyst": "Ph2 expansion 2025"},
        {"asset": "AZD8205", "company": "AstraZeneca", "ticker": "AZN", "phase": "Phase 2", "modality": "ADC (Topo I)", "indication": "Solid tumors", "deal": "Internal", "orr": "Early data", "catalyst": "Ph2 data 2025"},
        {"asset": "BNT324", "company": "BioNTech", "ticker": "BNTX", "phase": "Phase 1/2", "modality": "ADC", "indication": "Solid tumors", "deal": "Internal", "orr": "Early stage", "catalyst": "Ph1 data 2025"},
        {"asset": "Omburtamab", "company": "Y-mAbs", "ticker": "YMAB", "phase": "Approved", "modality": "Radioconjugate", "indication": "CNS tumors", "deal": "Internal", "orr": "N/A", "catalyst": "Label expansion"},
        {"asset": "MGC018", "company": "MacroGenics", "ticker": "MGNX", "phase": "Phase 2", "modality": "ADC (vcMMAE)", "indication": "Solid tumors", "deal": "Internal", "orr": "Early data", "catalyst": "Ph2 data 2025"},
    ]

    # Build assets table
    assets_rows = ""
    for a in assets:
        phase_color = "#22c55e" if "Phase 3" in a["phase"] or "Approved" in a["phase"] else "#f59e0b" if "Phase 2" in a["phase"] else "#6b7280"
        assets_rows += f'''
        <tr>
            <td><strong>{a["asset"]}</strong></td>
            <td>{a["company"]}<br><span style="color: var(--accent); font-size: 0.8rem;">{a["ticker"]}</span></td>
            <td><span style="background: {phase_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">{a["phase"]}</span></td>
            <td>{a["modality"]}</td>
            <td>{a["indication"]}</td>
            <td style="font-weight: 600;">{a["orr"]}</td>
            <td>{a["catalyst"]}</td>
        </tr>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B7-H3 / ADC Competitive Landscape | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .report-header {{
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }}
        .report-header h1 {{ font-size: 2.25rem; margin-bottom: 8px; }}
        .report-header p {{ opacity: 0.85; max-width: 700px; font-size: 1.1rem; }}
        .report-meta {{ display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }}
        .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }}
        .meta-item .label {{ font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }}
        .meta-item .value {{ font-size: 1.25rem; font-weight: 700; }}

        .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
        .section h2 {{ color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}

        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background: var(--bg); }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 12px; }}
        .bull-box {{ background: #ecfdf5; border: 1px solid #10b981; }}
        .bear-box {{ background: #fef2f2; border: 1px solid #ef4444; }}
        .bull-box h3 {{ color: #059669; }}
        .bear-box h3 {{ color: #dc2626; }}
        .thesis-list {{ list-style: none; padding: 0; margin-top: 16px; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }}
        .thesis-list li:last-child {{ border-bottom: none; }}
        .thesis-list li::before {{ content: "\\2192"; font-weight: bold; }}

        .highlight-box {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 1px solid #f59e0b; border-radius: 12px; padding: 20px; margin: 20px 0; }}
        .highlight-box h4 {{ color: #92400e; margin-bottom: 8px; }}
        .highlight-box p {{ color: #78350f; font-size: 0.9rem; }}

        .catalyst-timeline {{ margin-top: 20px; }}
        .catalyst-item {{ display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }}
        .catalyst-date {{ min-width: 100px; font-weight: 700; color: var(--accent); }}

        .back-link {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <div class="report-header">
            <h1>B7-H3 / ADC Competitive Landscape</h1>
            <p>B7-H3 (CD276) is the premier next-generation ADC target with the largest partnership deal in history. High tumor expression + minimal normal tissue = ideal therapeutic window.</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Largest Deal</div><div class="value">$22B (MRK/DSK)</div></div>
                <div class="meta-item"><div class="label">Assets in Development</div><div class="value">23+</div></div>
                <div class="meta-item"><div class="label">Best ORR</div><div class="value">75% (ES-SCLC)</div></div>
                <div class="meta-item"><div class="label">Modalities</div><div class="value">ADC, CAR-T, RIT</div></div>
            </div>
        </div>

        <!-- Mega Deal Highlight -->
        <div class="highlight-box">
            <h4>Merck-Daiichi Sankyo Partnership (Oct 2023)</h4>
            <p>The <strong>$22 billion</strong> collaboration is the largest ADC deal in history, validating B7-H3 as a high-conviction oncology target. Merck paid $4B upfront + $18B in milestones for global co-development and commercialization rights to ifinatamab deruxtecan (DS-7300).</p>
        </div>

        <!-- Why B7-H3 -->
        <div class="section">
            <h2>Why B7-H3 is the Premier ADC Target</h2>
            <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 20px;">
                B7-H3 is an immune checkpoint protein that is <strong>overexpressed in >70% of solid tumors</strong> while showing
                minimal expression on normal tissues. This creates an ideal therapeutic window for cytotoxic payloads like the DXd topoisomerase I inhibitor used in Enhertu.
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                <div style="background: var(--bg); padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--accent);">70%+</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Tumor expression rate</div>
                </div>
                <div style="background: var(--bg); padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--accent);">Low</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Normal tissue expression</div>
                </div>
                <div style="background: var(--bg); padding: 16px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--accent);">Pan-tumor</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Broad applicability</div>
                </div>
            </div>
        </div>

        <!-- Competitive Landscape -->
        <div class="section">
            <h2>Competitive Landscape</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Company</th>
                            <th>Phase</th>
                            <th>Modality</th>
                            <th>Indication</th>
                            <th>Best ORR</th>
                            <th>Next Catalyst</th>
                        </tr>
                    </thead>
                    <tbody>
                        {assets_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Bull/Bear -->
        <div class="section">
            <h2>Bull vs Bear</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>$22B Merck deal = largest ADC partnership ever; major pharma conviction</li>
                        <li>52% ORR in ES-SCLC is best-in-class for a tumor with no targeted therapy</li>
                        <li>Ideal target biology: high tumor, low normal tissue expression</li>
                        <li>Multiple modalities (ADC, CAR-T, radioconjugate) = diversified bet on target</li>
                        <li>Enhertu-style DXd payload has proven safety and efficacy track record</li>
                        <li>Pan-solid tumor applicability = massive market opportunity ($80B+ oncology)</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Merck/Daiichi dominance may crowd out smaller players</li>
                        <li>Competition from other ADC targets (TROP2, HER3, Nectin-4)</li>
                        <li>ADC class toxicities (ILD, cytopenias) may limit use</li>
                        <li>Registration trials still ongoing; approval not guaranteed</li>
                        <li>High price of ADCs may face payer pushback</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Catalysts -->
        <div class="section">
            <h2>Upcoming Catalysts</h2>
            <div class="catalyst-timeline">
                <div class="catalyst-item">
                    <div class="catalyst-date">H2 2025</div>
                    <div><strong>Daiichi/Merck:</strong> TROPION-Lung08 Phase 3 readout (NSCLC 1L)</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025</div>
                    <div><strong>Daiichi/Merck:</strong> Potential accelerated approval in ES-SCLC</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025</div>
                    <div><strong>GSK:</strong> HS-20093 Phase 2 expansion data</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025</div>
                    <div><strong>AstraZeneca:</strong> AZD8205 Phase 2 monotherapy and combo data</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2026</div>
                    <div><strong>Daiichi/Merck:</strong> Additional Phase 3 readouts in prostate, breast</div>
                </div>
            </div>
        </div>

        <a href="/targets" class="back-link">← Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


def generate_kras_report():
    """Generate the KRAS competitive landscape report."""

    # KRAS Assets data
    assets = [
        {"asset": "Sotorasib (Lumakras)", "company": "Amgen", "ticker": "AMGN", "phase": "Approved", "mutation": "G12C", "indication": "NSCLC", "approval": "May 2021", "orr": "37%", "notes": "First KRAS inhibitor approved"},
        {"asset": "Adagrasib (Krazati)", "company": "Mirati (BMS)", "ticker": "BMY", "phase": "Approved", "mutation": "G12C", "indication": "NSCLC", "approval": "Dec 2022", "orr": "43%", "notes": "Longer half-life, CNS penetration"},
        {"asset": "Divarasib (GDC-6036)", "company": "Roche/Genentech", "ticker": "RHHBY", "phase": "Phase 3", "mutation": "G12C", "indication": "NSCLC, CRC", "approval": "-", "orr": "53%", "notes": "Best ORR in NSCLC; CRC combo"},
        {"asset": "Glecirasib (JAB-21822)", "company": "Jacobio", "ticker": "Private", "phase": "Phase 3", "mutation": "G12C", "indication": "NSCLC, CRC", "approval": "-", "orr": "50%+", "notes": "China leader; AZ partnership"},
        {"asset": "Opnurasib (RMC-6291)", "company": "Revolution Medicines", "ticker": "RVMD", "phase": "Phase 2", "mutation": "G12C (ON)", "indication": "Solid tumors", "approval": "-", "orr": "48%", "notes": "Active-state (ON) inhibitor"},
        {"asset": "RMC-6236", "company": "Revolution Medicines", "ticker": "RVMD", "phase": "Phase 3", "mutation": "Multi-KRAS", "indication": "PDAC", "approval": "-", "orr": "20%+ PDAC", "notes": "Pan-RAS inhibitor; PDAC focus"},
        {"asset": "MRTX1133", "company": "Mirati (BMS)", "ticker": "BMY", "phase": "Phase 1/2", "mutation": "G12D", "indication": "PDAC", "approval": "-", "orr": "Early", "notes": "First G12D inhibitor in clinic"},
        {"asset": "RMC-9805", "company": "Revolution Medicines", "ticker": "RVMD", "phase": "Phase 1", "mutation": "G12D (ON)", "indication": "PDAC", "approval": "-", "orr": "Early", "notes": "Active-state G12D inhibitor"},
    ]

    # Build assets table
    assets_rows = ""
    for a in assets:
        phase_color = "#22c55e" if "Approved" in a["phase"] else "#3b82f6" if "Phase 3" in a["phase"] else "#f59e0b" if "Phase 2" in a["phase"] else "#6b7280"
        assets_rows += f'''
        <tr>
            <td><strong>{a["asset"]}</strong></td>
            <td>{a["company"]}<br><span style="color: var(--accent); font-size: 0.8rem;">{a["ticker"]}</span></td>
            <td><span style="background: {phase_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">{a["phase"]}</span></td>
            <td><strong>{a["mutation"]}</strong></td>
            <td>{a["indication"]}</td>
            <td style="font-weight: 600;">{a["orr"]}</td>
            <td style="font-size: 0.8rem; color: var(--text-secondary);">{a["notes"]}</td>
        </tr>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KRAS Inhibitor Landscape | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .report-header {{
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }}
        .report-header h1 {{ font-size: 2.25rem; margin-bottom: 8px; }}
        .report-header p {{ opacity: 0.85; max-width: 700px; font-size: 1.1rem; }}
        .report-meta {{ display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }}
        .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }}
        .meta-item .label {{ font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }}
        .meta-item .value {{ font-size: 1.25rem; font-weight: 700; }}

        .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
        .section h2 {{ color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}

        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background: var(--bg); }}

        .mutation-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 24px 0; }}
        .mutation-card {{ background: var(--bg); padding: 20px; border-radius: 12px; border-left: 4px solid var(--accent); }}
        .mutation-card h4 {{ color: var(--navy); margin-bottom: 8px; }}
        .mutation-card .pct {{ font-size: 1.5rem; font-weight: 700; color: var(--accent); }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 12px; }}
        .bull-box {{ background: #ecfdf5; border: 1px solid #10b981; }}
        .bear-box {{ background: #fef2f2; border: 1px solid #ef4444; }}
        .bull-box h3 {{ color: #059669; }}
        .bear-box h3 {{ color: #dc2626; }}
        .thesis-list {{ list-style: none; padding: 0; margin-top: 16px; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }}
        .thesis-list li:last-child {{ border-bottom: none; }}
        .thesis-list li::before {{ content: "\\2192"; font-weight: bold; }}

        .catalyst-timeline {{ margin-top: 20px; }}
        .catalyst-item {{ display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }}
        .catalyst-date {{ min-width: 100px; font-weight: 700; color: var(--accent); }}

        .back-link {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }}
        .back-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <div class="report-header">
            <h1>KRAS Inhibitor Landscape</h1>
            <p>From "undruggable" to FDA-approved in under a decade. KRAS mutations drive ~25% of all cancers. G12C is cracked; G12D and pan-KRAS are next.</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Approved Drugs</div><div class="value">2</div></div>
                <div class="meta-item"><div class="label">Phase 3 Assets</div><div class="value">5+</div></div>
                <div class="meta-item"><div class="label">Target Mutations</div><div class="value">G12C, G12D, Multi</div></div>
                <div class="meta-item"><div class="label">Key Company</div><div class="value">RVMD</div></div>
            </div>
        </div>

        <!-- KRAS Mutation Overview -->
        <div class="section">
            <h2>KRAS Mutations in Cancer</h2>
            <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 20px;">
                KRAS is mutated in approximately <strong>25% of all human cancers</strong>, making it one of the most important oncology targets.
                For decades it was considered "undruggable" due to the protein's smooth surface and high affinity for GTP. The breakthrough came with covalent inhibitors targeting the G12C mutation's unique cysteine.
            </p>
            <div class="mutation-grid">
                <div class="mutation-card">
                    <h4>KRAS G12C</h4>
                    <div class="pct">~13%</div>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">of NSCLC; targetable with approved drugs (sotorasib, adagrasib)</p>
                </div>
                <div class="mutation-card">
                    <h4>KRAS G12D</h4>
                    <div class="pct">~40%</div>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">of PDAC; next frontier (MRTX1133, RMC-9805 in Phase 1)</p>
                </div>
                <div class="mutation-card">
                    <h4>KRAS G12V</h4>
                    <div class="pct">~20%</div>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">of PDAC/CRC; targeted by pan-RAS inhibitors</p>
                </div>
                <div class="mutation-card">
                    <h4>Pan-KRAS/RAS</h4>
                    <div class="pct">All</div>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">Multi-mutation approaches (RMC-6236) for broad coverage</p>
                </div>
            </div>
        </div>

        <!-- Competitive Landscape -->
        <div class="section">
            <h2>Competitive Landscape</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Company</th>
                            <th>Phase</th>
                            <th>Mutation</th>
                            <th>Indication</th>
                            <th>ORR</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {assets_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Next-Gen Approaches -->
        <div class="section">
            <h2>Next-Generation Approaches</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                <div style="background: var(--bg); padding: 20px; border-radius: 12px;">
                    <h4 style="color: var(--navy); margin-bottom: 8px;">Active-State (ON) Inhibitors</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">Revolution Medicines' approach targets KRAS in its active GTP-bound state, potentially overcoming resistance to GDP-state (OFF) inhibitors like sotorasib.</p>
                </div>
                <div style="background: var(--bg); padding: 20px; border-radius: 12px;">
                    <h4 style="color: var(--navy); margin-bottom: 8px;">Pan-RAS Inhibitors</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">RMC-6236 targets multiple KRAS mutations plus NRAS/HRAS, enabling treatment regardless of specific mutation.</p>
                </div>
                <div style="background: var(--bg); padding: 20px; border-radius: 12px;">
                    <h4 style="color: var(--navy); margin-bottom: 8px;">G12D Inhibitors</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">MRTX1133 and RMC-9805 target the most common mutation in pancreatic cancer, a $5B+ market opportunity.</p>
                </div>
                <div style="background: var(--bg); padding: 20px; border-radius: 12px;">
                    <h4 style="color: var(--navy); margin-bottom: 8px;">Combinations</h4>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">KRAS + SHP2, KRAS + SOS1, KRAS + checkpoint inhibitors to address resistance and improve durability.</p>
                </div>
            </div>
        </div>

        <!-- Bull/Bear -->
        <div class="section">
            <h2>Bull vs Bear</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>KRAS is mutated in 25% of all cancers = massive TAM</li>
                        <li>G12C approved drugs prove the target is druggable</li>
                        <li>G12D opportunity (PDAC) could be larger than G12C</li>
                        <li>Next-gen inhibitors (ON-state, pan-RAS) address resistance</li>
                        <li>Revolution Medicines (RVMD) has multiple shots on goal</li>
                        <li>Combinations with SHP2/SOS1 could improve durability</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Rapid resistance development limits durability (~6mo PFS)</li>
                        <li>Approved drugs have modest ORR (37-43%) vs. targeted therapies in other settings</li>
                        <li>G12D is more challenging than G12C (no cysteine handle)</li>
                        <li>PDAC is notoriously hard; microenvironment challenges</li>
                        <li>Competition intensifying with many players</li>
                        <li>Mirati acquisition by BMS = fewer pure-play options</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Catalysts -->
        <div class="section">
            <h2>Upcoming Catalysts</h2>
            <div class="catalyst-timeline">
                <div class="catalyst-item">
                    <div class="catalyst-date">H1 2025</div>
                    <div><strong>Roche:</strong> Divarasib Phase 3 data in NSCLC</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025</div>
                    <div><strong>Revolution (RVMD):</strong> RMC-6236 Phase 3 readout in PDAC</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025</div>
                    <div><strong>Revolution (RVMD):</strong> Opnurasib (RMC-6291) Phase 2 expansion data</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025</div>
                    <div><strong>BMS/Mirati:</strong> MRTX1133 (G12D) Phase 1/2 dose expansion</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2025-26</div>
                    <div><strong>Jacobio/AZ:</strong> Glecirasib Phase 3 readout; potential China approval</div>
                </div>
                <div class="catalyst-item">
                    <div class="catalyst-date">2026</div>
                    <div><strong>Revolution (RVMD):</strong> RMC-9805 (G12D ON) Phase 1 data</div>
                </div>
            </div>
        </div>

        <!-- Key Companies -->
        <div class="section">
            <h2>Key Companies</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                <a href="/api/company/RVMD/html" style="display: block; background: var(--bg); padding: 20px; border-radius: 12px; text-decoration: none; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: var(--navy);">Revolution Medicines</strong>
                        <span style="color: var(--accent);">RVMD</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">Multi-RAS leader with G12C (ON), G12D, and pan-RAS programs</p>
                </a>
                <a href="/api/company/AMGN/html" style="display: block; background: var(--bg); padding: 20px; border-radius: 12px; text-decoration: none; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong style="color: var(--navy);">Amgen</strong>
                        <span style="color: var(--accent);">AMGN</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 8px;">First-to-market with Lumakras (sotorasib)</p>
                </a>
            </div>
        </div>

        <a href="/targets" class="back-link">← Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


def generate_company_detail(ticker: str):
    company = None
    for c in ALL_COMPANIES:
        if c["ticker"].upper() == ticker.upper():
            company = c
            break

    if not company:
        return f'''<!DOCTYPE html>
<html><head><title>Company Not Found</title></head>
<body><h1>Company {ticker} not found</h1><a href="/companies">Back to Companies</a></body>
</html>'''

    tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in company.get("tags", [])])

    # ARWR thesis section (only shown for ARWR)
    arwr_thesis_section = ""
    if company["ticker"] == "ARWR":
        arwr_thesis_section = '''
        <div class="detail-section" style="background: linear-gradient(135deg, #fef5f3 0%, #fff 100%); border-color: var(--accent);">
            <h2>Investment Analysis</h2>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">Deep-dive thesis with pipeline analysis, competitive positioning, and catalyst timeline.</p>
            <a href="/api/company/ARWR/thesis/html" style="display: inline-block; padding: 12px 24px; background: var(--accent); color: white; border-radius: 8px; font-weight: 600; text-decoration: none;">View Full Thesis &rarr;</a>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company["ticker"]} - {company["name"]} | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .company-header {{ background: linear-gradient(135deg, var(--navy), #2d4a6f); color: white; padding: 48px 32px; margin: -32px -32px 32px; }}
        .company-header h1 {{ font-size: 2rem; margin-bottom: 8px; }}
        .company-header .ticker {{ background: var(--accent); padding: 8px 16px; border-radius: 8px; font-weight: 700; display: inline-block; margin-bottom: 16px; }}
        .company-header p {{ opacity: 0.9; max-width: 600px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 24px 0; }}
        .stat-box {{ background: rgba(255,255,255,0.15); padding: 20px; border-radius: 12px; text-align: center; }}
        .stat-box .value {{ font-size: 2rem; font-weight: 700; }}
        .stat-box .label {{ font-size: 0.85rem; opacity: 0.8; }}
        .detail-section {{ background: var(--surface); border-radius: 16px; padding: 24px; margin-bottom: 24px; border: 1px solid var(--border); }}
        .detail-section h2 {{ color: var(--navy); margin-bottom: 16px; }}
    </style>
</head>
<body>
    {get_nav_html()}
    <main class="main">
        <div class="company-header">
            <span class="ticker">{company["ticker"]}</span>
            <h1>{company["name"]}</h1>
            <p>{company["description"]}</p>
            <div class="stats-grid">
                <div class="stat-box"><div class="value">{company["market_cap"]}</div><div class="label">Market Cap</div></div>
                <div class="stat-box"><div class="value">{company["pipeline"]}</div><div class="label">Pipeline</div></div>
                <div class="stat-box"><div class="value">{company["phase3"]}</div><div class="label">Phase 3</div></div>
                <div class="stat-box"><div class="value">{company.get("approved", "—")}</div><div class="label">Approved</div></div>
            </div>
        </div>

        <div class="detail-section">
            <h2>Platform</h2>
            <span class="platform-badge" style="font-size: 0.9rem; padding: 8px 16px;">{company["platform"]}</span>
        </div>

        <div class="detail-section">
            <h2>Next Catalyst</h2>
            <div class="catalyst-box">
                <div class="catalyst-text" style="font-size: 1rem;">{company["catalyst"]}</div>
            </div>
        </div>

        <div class="detail-section">
            <h2>Therapeutic Areas</h2>
            <div class="tags-row" style="gap: 10px;">{tags_html}</div>
        </div>

        {arwr_thesis_section}

        <a href="/companies" style="display: inline-block; margin-top: 24px; color: var(--accent);">← Back to Companies</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


def generate_arwr_thesis():
    """Generate the ARWR investment thesis page."""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARWR Investment Thesis | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .report-header {{
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }}
        .report-header h1 {{ font-size: 2.25rem; margin-bottom: 8px; }}
        .report-header p {{ opacity: 0.85; max-width: 700px; font-size: 1.1rem; }}
        .report-meta {{ display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }}
        .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }}
        .meta-item .label {{ font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }}
        .meta-item .value {{ font-size: 1.25rem; font-weight: 700; }}

        .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
        .section h2 {{ color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}

        .thesis-headline {{ font-size: 1.2rem; font-weight: 600; color: var(--navy); margin-bottom: 16px; padding: 16px; background: linear-gradient(135deg, #fef5f3 0%, #fff 100%); border-radius: 8px; border-left: 4px solid var(--accent); }}

        .pipeline-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        .pipeline-table th {{ background: var(--navy); color: white; padding: 12px; text-align: left; }}
        .pipeline-table td {{ padding: 12px; border-bottom: 1px solid var(--border); }}
        .pipeline-table tr:hover {{ background: var(--bg); }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 12px; }}
        .bull-box {{ background: #ecfdf5; border: 1px solid #10b981; }}
        .bear-box {{ background: #fef2f2; border: 1px solid #ef4444; }}
        .bull-box h3 {{ color: #059669; }}
        .bear-box h3 {{ color: #dc2626; }}
        .thesis-list {{ list-style: none; padding: 0; margin-top: 16px; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; }}
        .thesis-list li:last-child {{ border-bottom: none; }}

        .catalyst-timeline {{ margin-top: 20px; }}
        .catalyst-item {{ display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }}
        .catalyst-date {{ min-width: 100px; font-weight: 700; color: var(--accent); }}

        .back-link {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }}
    </style>
</head>
<body>
    {get_nav_html()}
    <main class="main">
        <div class="report-header">
            <h1>Arrowhead Pharmaceuticals (ARWR)</h1>
            <p>RNAi platform company with deep pipeline across liver, cardio, and pulmonary diseases. Key asset Plozasiran (Ionis partnership) approaching commercialization.</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Market Cap</div><div class="value">$4.2B</div></div>
                <div class="meta-item"><div class="label">Pipeline Assets</div><div class="value">15+</div></div>
                <div class="meta-item"><div class="label">Phase 3</div><div class="value">3</div></div>
                <div class="meta-item"><div class="label">Platform</div><div class="value">RNAi (TRiM)</div></div>
            </div>
        </div>

        <div class="section">
            <h2>Investment Thesis</h2>
            <div class="thesis-headline">
                Arrowhead's TRiM platform enables extra-hepatic RNAi delivery, differentiating from Alnylam's liver-focused approach. Near-term catalysts in obesity (ARO-INHBE) and approved Plozasiran provide multiple shots on goal.
            </div>
            <ul style="color: var(--text-secondary); line-height: 1.8; padding-left: 20px;">
                <li><strong>Platform differentiation:</strong> TRiM enables delivery to lung, muscle, and adipose tissue — not just liver</li>
                <li><strong>Obesity play:</strong> ARO-INHBE targets INHBE gene, a validated obesity pathway; Phase 1 data showed meaningful weight loss</li>
                <li><strong>Plozasiran near approval:</strong> Best-in-class triglyceride reduction; partnership with Ionis for commercialization</li>
                <li><strong>Pulmonary expansion:</strong> ARO-MUC5AC for COPD/asthma; lung delivery is significant technical achievement</li>
                <li><strong>Amgen partnership:</strong> Cardiovascular programs with strong pharma partner</li>
            </ul>
        </div>

        <div class="section">
            <h2>Key Pipeline Assets</h2>
            <table class="pipeline-table">
                <thead>
                    <tr><th>Asset</th><th>Target</th><th>Indication</th><th>Phase</th><th>Partner</th><th>Next Catalyst</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Plozasiran</strong></td><td>APOC3</td><td>Severe hypertriglyceridemia</td><td style="color:#22c55e;font-weight:600;">NDA Filed</td><td>Ionis</td><td>FDA decision 2025</td></tr>
                    <tr><td><strong>ARO-INHBE</strong></td><td>INHBE</td><td>Obesity</td><td style="color:#f59e0b;font-weight:600;">Phase 1</td><td>Internal</td><td>Ph1 data H2 2025</td></tr>
                    <tr><td><strong>ARO-ANG3</strong></td><td>ANGPTL3</td><td>Dyslipidemia</td><td style="color:#3b82f6;font-weight:600;">Phase 3</td><td>Amgen</td><td>Ph3 data 2026</td></tr>
                    <tr><td><strong>ARO-APOC3</strong></td><td>APOC3</td><td>Cardiovascular</td><td style="color:#3b82f6;font-weight:600;">Phase 3</td><td>Amgen</td><td>Ph3 data 2026</td></tr>
                    <tr><td><strong>ARO-MUC5AC</strong></td><td>MUC5AC</td><td>COPD/Asthma</td><td style="color:#f59e0b;font-weight:600;">Phase 1/2</td><td>Internal</td><td>Ph1/2 data 2025</td></tr>
                    <tr><td><strong>ARO-DUX4</strong></td><td>DUX4</td><td>FSHD</td><td style="color:#f59e0b;font-weight:600;">Phase 1/2</td><td>Internal</td><td>Ph1/2 data 2025</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Bull vs Bear</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>TRiM platform enables extra-hepatic delivery — differentiated from Alnylam</li>
                        <li>ARO-INHBE is novel obesity approach; RNAi could disrupt GLP-1 market</li>
                        <li>Plozasiran best-in-class triglyceride reduction; approval imminent</li>
                        <li>Amgen partnership validates cardiovascular programs</li>
                        <li>Deep pipeline provides multiple chances for success</li>
                        <li>Pulmonary delivery opens large COPD/asthma market</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Alnylam dominates RNAi space with established commercial infrastructure</li>
                        <li>ARO-INHBE obesity data still early; unclear if competitive with GLP-1s</li>
                        <li>Cash burn remains elevated with multiple Phase 3 trials</li>
                        <li>Execution risk on extra-hepatic delivery claims</li>
                        <li>Partner concentration (Amgen, Ionis) creates dependency</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Upcoming Catalysts</h2>
            <div class="catalyst-timeline">
                <div class="catalyst-item"><div class="catalyst-date">H1 2025</div><div><strong>Plozasiran:</strong> FDA decision for severe hypertriglyceridemia</div></div>
                <div class="catalyst-item"><div class="catalyst-date">H2 2025</div><div><strong>ARO-INHBE:</strong> Phase 1 obesity data readout</div></div>
                <div class="catalyst-item"><div class="catalyst-date">2025</div><div><strong>ARO-MUC5AC:</strong> Phase 1/2 pulmonary data</div></div>
                <div class="catalyst-item"><div class="catalyst-date">2026</div><div><strong>ARO-ANG3:</strong> Phase 3 cardiovascular data (Amgen)</div></div>
                <div class="catalyst-item"><div class="catalyst-date">2026</div><div><strong>ARO-APOC3:</strong> Phase 3 cardiovascular data (Amgen)</div></div>
            </div>
        </div>

        <a href="/api/company/ARWR/html" class="back-link">← Back to ARWR Profile</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''
