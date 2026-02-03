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
</head>
<body>
    {get_nav_html("companies")}
    <main class="main">
        <div class="page-header">
            <h1 class="page-title">Companies</h1>
            <p class="page-subtitle">{len(ALL_COMPANIES)} biotech companies with real-time catalyst tracking</p>
        </div>
        <nav class="category-nav">
            <div class="category-pills">{pills_html}</div>
        </nav>
        {sections_html}
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''

def generate_targets_page():
    targets = [
        {"name": "GLP-1 / Incretin", "assets": 25, "approved": 6, "phase3": 7, "deals": "$22.8B", "hot": True},
        {"name": "TL1A / TNFSF15", "assets": 11, "approved": 0, "phase3": 3, "deals": "$2.1B", "hot": True},
        {"name": "PCSK9", "assets": 8, "approved": 2, "phase3": 2, "deals": "$3.5B", "hot": False},
        {"name": "CD20", "assets": 15, "approved": 5, "phase3": 4, "deals": "$5.0B", "hot": False},
        {"name": "PD-1 / PD-L1", "assets": 30, "approved": 8, "phase3": 10, "deals": "$15B+", "hot": False},
        {"name": "KRAS G12C", "assets": 12, "approved": 2, "phase3": 5, "deals": "$4.2B", "hot": True},
        {"name": "B7-H3", "assets": 8, "approved": 0, "phase3": 2, "deals": "$1.5B", "hot": True},
        {"name": "Claudin 18.2", "assets": 10, "approved": 0, "phase3": 4, "deals": "$2.8B", "hot": True},
    ]

    cards_html = ""
    for t in targets:
        hot_badge = '<span class="hot-badge">Hot Target</span>' if t["hot"] else ""
        cards_html += f'''
        <div class="target-card">
            <div class="target-header">
                <h3>{t["name"]}</h3>
                {hot_badge}
            </div>
            <div class="target-stats">
                <div class="target-stat"><span class="stat-value">{t["assets"]}</span><span class="stat-label">Assets</span></div>
                <div class="target-stat"><span class="stat-value">{t["approved"]}</span><span class="stat-label">Approved</span></div>
                <div class="target-stat"><span class="stat-value">{t["phase3"]}</span><span class="stat-label">Phase 3</span></div>
                <div class="target-stat"><span class="stat-value">{t["deals"]}</span><span class="stat-label">Deal Value</span></div>
            </div>
        </div>
        '''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Targets | Satya Bio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .targets-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; }}
        .target-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; }}
        .target-card:hover {{ border-color: var(--accent); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
        .target-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .target-header h3 {{ font-size: 1.2rem; color: var(--navy); }}
        .hot-badge {{ background: linear-gradient(135deg, var(--accent), #d06a4f); color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }}
        .target-stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
        .target-stat {{ text-align: center; padding: 12px; background: var(--bg); border-radius: 8px; }}
        .target-stat .stat-value {{ font-size: 1.5rem; font-weight: 700; color: var(--navy); }}
        .target-stat .stat-label {{ font-size: 0.75rem; color: var(--text-muted); }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <div class="page-header">
            <h1 class="page-title">Target Landscapes</h1>
            <p class="page-subtitle">Competitive intelligence for the hottest therapeutic targets</p>
        </div>
        <div class="targets-grid">{cards_html}</div>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
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

        <a href="/companies" style="display: inline-block; margin-top: 24px; color: var(--accent);">← Back to Companies</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''
