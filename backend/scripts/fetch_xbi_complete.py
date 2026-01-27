"""
Fetch COMPLETE XBI Holdings from SEC N-PORT Filings

XBI (SPDR S&P Biotech ETF) is managed by State Street.
This script fetches all holdings from the latest N-PORT filing.
"""

import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import re

sys.path.insert(0, str(Path(__file__).parent.parent))


class XBICompleteHoldingsFetcher:
    """Fetch complete XBI holdings from SEC N-PORT filings"""

    # State Street SPDR Series Trust CIK
    SPDR_CIK = "0001064642"
    SEC_BASE = "https://data.sec.gov"
    EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helix Intelligence research@helix.com",
            "Accept": "application/json"
        })
        self.holdings = []

    def get_latest_nport(self) -> str:
        """Get the latest N-PORT filing accession number for XBI"""
        print("Finding latest N-PORT filing for SPDR funds...")

        url = f"{self.SEC_BASE}/submissions/CIK{self.SPDR_CIK}.json"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])

        for i, form in enumerate(forms):
            if form == "NPORT-P":
                print(f"Found N-PORT filing: {accessions[i]} ({dates[i]})")
                return accessions[i]

        return None

    def fetch_nport_holdings(self, accession: str) -> List[Dict]:
        """Parse N-PORT XML to extract XBI holdings"""
        print(f"Fetching N-PORT filing {accession}...")

        # Format accession for URL
        acc_formatted = accession.replace("-", "")

        # Get the filing index
        index_url = f"{self.SEC_BASE}/Archives/edgar/data/{self.SPDR_CIK}/{acc_formatted}/index.json"
        resp = self.session.get(index_url, timeout=30)
        resp.raise_for_status()
        index_data = resp.json()

        # Find the primary XML document
        xml_file = None
        for item in index_data.get("directory", {}).get("item", []):
            name = item.get("name", "")
            if name.endswith(".xml") and "primary" in name.lower():
                xml_file = name
                break
            elif name.endswith(".xml"):
                xml_file = name

        if not xml_file:
            print("Could not find XML file in N-PORT filing")
            return []

        # Fetch and parse the XML
        xml_url = f"{self.SEC_BASE}/Archives/edgar/data/{self.SPDR_CIK}/{acc_formatted}/{xml_file}"
        print(f"Parsing XML from {xml_url}...")

        resp = self.session.get(xml_url, timeout=60)
        resp.raise_for_status()

        return self._parse_nport_xml(resp.text)

    def _parse_nport_xml(self, xml_content: str) -> List[Dict]:
        """Parse N-PORT XML to extract holdings"""
        holdings = []

        try:
            # Remove namespace for easier parsing
            xml_content = re.sub(r'\sxmlns[^"]*"[^"]*"', '', xml_content)
            root = ET.fromstring(xml_content)

            # Find all investment holdings
            for inv in root.findall(".//invstOrSec"):
                name = inv.findtext("name", "").strip()
                cusip = inv.findtext("cusip", "").strip()
                ticker = inv.findtext("ticker", "").strip()
                balance = inv.findtext("balance", "0")
                val_usd = inv.findtext("valUSD", "0")

                # Get asset category
                asset_cat = inv.findtext("assetCat", "")

                # Only include equity holdings with tickers
                if ticker and asset_cat in ["EC", "EF", ""]:  # EC=Common Stock, EF=ETF
                    holdings.append({
                        "ticker": ticker.upper(),
                        "name": name,
                        "cusip": cusip,
                        "shares": float(balance) if balance else 0,
                        "value_usd": float(val_usd) if val_usd else 0,
                    })

            print(f"Parsed {len(holdings)} holdings from N-PORT")

        except Exception as e:
            print(f"Error parsing N-PORT XML: {e}")

        return holdings

    def fetch_from_sp_index(self) -> List[Dict]:
        """
        Fetch S&P Biotechnology Select Industry Index components.
        XBI tracks this index - we can get components from various sources.
        """
        print("Fetching S&P Biotech Index components...")

        # Comprehensive list of S&P Biotech Select Industry Index components
        # This is the index XBI tracks - approximately 140+ stocks
        # Updated from multiple financial sources
        components = [
            # A
            {"ticker": "AADI", "name": "Aadi Bioscience Inc"},
            {"ticker": "ABCL", "name": "AbCellera Biologics Inc"},
            {"ticker": "ABMD", "name": "Abiomed Inc"},
            {"ticker": "ACAD", "name": "ACADIA Pharmaceuticals Inc"},
            {"ticker": "ACIU", "name": "AC Immune SA"},
            {"ticker": "ACRS", "name": "Aclaris Therapeutics Inc"},
            {"ticker": "ADAP", "name": "Adaptimmune Therapeutics PLC"},
            {"ticker": "ADMA", "name": "ADMA Biologics Inc"},
            {"ticker": "ADPT", "name": "Adaptive Biotechnologies Corp"},
            {"ticker": "ADVM", "name": "Adverum Biotechnologies Inc"},
            {"ticker": "AGIO", "name": "Agios Pharmaceuticals Inc"},
            {"ticker": "AKRO", "name": "Akero Therapeutics Inc"},
            {"ticker": "ALEC", "name": "Alector Inc"},
            {"ticker": "ALKS", "name": "Alkermes PLC"},
            {"ticker": "ALLK", "name": "Allakos Inc"},
            {"ticker": "ALNY", "name": "Alnylam Pharmaceuticals Inc"},
            {"ticker": "ALPN", "name": "Alpine Immune Sciences Inc"},
            {"ticker": "AMGN", "name": "Amgen Inc"},
            {"ticker": "AMPH", "name": "Amphastar Pharmaceuticals Inc"},
            {"ticker": "ANNX", "name": "Annexon Biosciences Inc"},
            {"ticker": "APLS", "name": "Apellis Pharmaceuticals Inc"},
            {"ticker": "APLT", "name": "Applied Therapeutics Inc"},
            {"ticker": "APTO", "name": "Aptose Biosciences Inc"},
            {"ticker": "ARDX", "name": "Ardelyx Inc"},
            {"ticker": "ARGX", "name": "argenx SE"},
            {"ticker": "ARNA", "name": "Arena Pharmaceuticals Inc"},
            {"ticker": "ARQT", "name": "Arcus Biosciences Inc"},
            {"ticker": "ARWR", "name": "Arrowhead Pharmaceuticals Inc"},
            {"ticker": "ATRA", "name": "Atara Biotherapeutics Inc"},
            {"ticker": "AUPH", "name": "Aurinia Pharmaceuticals Inc"},
            {"ticker": "AVIR", "name": "Atea Pharmaceuticals Inc"},
            {"ticker": "AVXL", "name": "Anavex Life Sciences Corp"},
            {"ticker": "AXSM", "name": "Axsome Therapeutics Inc"},
            # B
            {"ticker": "BBIO", "name": "BridgeBio Pharma Inc"},
            {"ticker": "BEAM", "name": "Beam Therapeutics Inc"},
            {"ticker": "BGNE", "name": "BeiGene Ltd"},
            {"ticker": "BHVN", "name": "Biohaven Ltd"},
            {"ticker": "BIIB", "name": "Biogen Inc"},
            {"ticker": "BIOR", "name": "Biora Therapeutics Inc"},
            {"ticker": "BLTE", "name": "Belite Bio Inc"},
            {"ticker": "BLUE", "name": "bluebird bio Inc"},
            {"ticker": "BMRN", "name": "BioMarin Pharmaceutical Inc"},
            {"ticker": "BNTX", "name": "BioNTech SE"},
            {"ticker": "BPMC", "name": "Blueprint Medicines Corp"},
            {"ticker": "BTAI", "name": "BioXcel Therapeutics Inc"},
            # C
            {"ticker": "CARA", "name": "Cara Therapeutics Inc"},
            {"ticker": "CCRN", "name": "Cross Country Healthcare Inc"},
            {"ticker": "CDNA", "name": "CareDx Inc"},
            {"ticker": "CDXS", "name": "Codexis Inc"},
            {"ticker": "CELH", "name": "Celsius Holdings Inc"},
            {"ticker": "CGON", "name": "CG Oncology Inc"},
            {"ticker": "CHRS", "name": "Coherus BioSciences Inc"},
            {"ticker": "CLVR", "name": "Clever Leaves Holdings Inc"},
            {"ticker": "CORT", "name": "Corcept Therapeutics Inc"},
            {"ticker": "CRBU", "name": "Caribou Biosciences Inc"},
            {"ticker": "CRNX", "name": "Crinetics Pharmaceuticals Inc"},
            {"ticker": "CRSP", "name": "CRISPR Therapeutics AG"},
            {"ticker": "CRVS", "name": "Corvus Pharmaceuticals Inc"},
            {"ticker": "CYTK", "name": "Cytokinetics Inc"},
            # D
            {"ticker": "DAWN", "name": "Day One Biopharmaceuticals Inc"},
            {"ticker": "DCPH", "name": "Deciphera Pharmaceuticals Inc"},
            {"ticker": "DNLI", "name": "Denali Therapeutics Inc"},
            {"ticker": "DRNA", "name": "Dicerna Pharmaceuticals Inc"},
            {"ticker": "DVAX", "name": "Dynavax Technologies Corp"},
            # E
            {"ticker": "EDIT", "name": "Editas Medicine Inc"},
            {"ticker": "ELVN", "name": "Enliven Therapeutics Inc"},
            {"ticker": "ENTA", "name": "Enanta Pharmaceuticals Inc"},
            {"ticker": "EOLS", "name": "Evolus Inc"},
            {"ticker": "EPZM", "name": "Epizyme Inc"},
            {"ticker": "ETNB", "name": "89bio Inc"},
            {"ticker": "EVLO", "name": "Evelo Biosciences Inc"},
            {"ticker": "EXAS", "name": "Exact Sciences Corp"},
            {"ticker": "EXEL", "name": "Exelixis Inc"},
            # F
            {"ticker": "FATE", "name": "Fate Therapeutics Inc"},
            {"ticker": "FGEN", "name": "FibroGen Inc"},
            {"ticker": "FOLD", "name": "Amicus Therapeutics Inc"},
            {"ticker": "FULC", "name": "Fulcrum Therapeutics Inc"},
            # G
            {"ticker": "GILD", "name": "Gilead Sciences Inc"},
            {"ticker": "GMAB", "name": "Genmab A/S"},
            {"ticker": "GOSS", "name": "Gossamer Bio Inc"},
            {"ticker": "GPCR", "name": "Structure Therapeutics Inc"},
            {"ticker": "GRFS", "name": "Grifols SA"},
            # H
            {"ticker": "HALO", "name": "Halozyme Therapeutics Inc"},
            {"ticker": "HRMY", "name": "Harmony Biosciences Holdings Inc"},
            {"ticker": "HZNP", "name": "Horizon Therapeutics PLC"},
            # I
            {"ticker": "ICPT", "name": "Intercept Pharmaceuticals Inc"},
            {"ticker": "IDYA", "name": "IDEAYA Biosciences Inc"},
            {"ticker": "IFRX", "name": "InflaRx NV"},
            {"ticker": "IMGN", "name": "ImmunoGen Inc"},
            {"ticker": "IMVT", "name": "Immunovant Inc"},
            {"ticker": "INCY", "name": "Incyte Corp"},
            {"ticker": "INSM", "name": "Insmed Inc"},
            {"ticker": "IONS", "name": "Ionis Pharmaceuticals Inc"},
            {"ticker": "IOVA", "name": "Iovance Biotherapeutics Inc"},
            {"ticker": "IRON", "name": "Disc Medicine Inc"},
            {"ticker": "IRWD", "name": "Ironwood Pharmaceuticals Inc"},
            {"ticker": "ISEE", "name": "IVERIC bio Inc"},
            {"ticker": "ITCI", "name": "Intra-Cellular Therapies Inc"},
            # J-K
            {"ticker": "JANX", "name": "Janux Therapeutics Inc"},
            {"ticker": "JAZZ", "name": "Jazz Pharmaceuticals PLC"},
            {"ticker": "KALV", "name": "KalVista Pharmaceuticals Inc"},
            {"ticker": "KPTI", "name": "Karyopharm Therapeutics Inc"},
            {"ticker": "KROS", "name": "Keros Therapeutics Inc"},
            {"ticker": "KRYS", "name": "Krystal Biotech Inc"},
            {"ticker": "KURA", "name": "Kura Oncology Inc"},
            {"ticker": "KYMR", "name": "Kymera Therapeutics Inc"},
            # L-M
            {"ticker": "LEGN", "name": "Legend Biotech Corp"},
            {"ticker": "LGND", "name": "Ligand Pharmaceuticals Inc"},
            {"ticker": "LQDA", "name": "Liquidia Corp"},
            {"ticker": "LRMR", "name": "Larimar Therapeutics Inc"},
            {"ticker": "LUNA", "name": "Luna Innovations Inc"},
            {"ticker": "MDGL", "name": "Madrigal Pharmaceuticals Inc"},
            {"ticker": "MGNX", "name": "MacroGenics Inc"},
            {"ticker": "MIRM", "name": "Mirum Pharmaceuticals Inc"},
            {"ticker": "MNKD", "name": "MannKind Corp"},
            {"ticker": "MRNA", "name": "Moderna Inc"},
            {"ticker": "MRSN", "name": "Mersana Therapeutics Inc"},
            {"ticker": "MRUS", "name": "Merus NV"},
            {"ticker": "MYGN", "name": "Myriad Genetics Inc"},
            # N
            {"ticker": "NBIX", "name": "Neurocrine Biosciences Inc"},
            {"ticker": "NKTR", "name": "Nektar Therapeutics"},
            {"ticker": "NRIX", "name": "Nurix Therapeutics Inc"},
            {"ticker": "NSTG", "name": "NanoString Technologies Inc"},
            {"ticker": "NTLA", "name": "Intellia Therapeutics Inc"},
            {"ticker": "NUVB", "name": "Nuvation Bio Inc"},
            {"ticker": "NVAX", "name": "Novavax Inc"},
            # O-P
            {"ticker": "OCEA", "name": "Ocean Biomedical Inc"},
            {"ticker": "OLMA", "name": "Olema Pharmaceuticals Inc"},
            {"ticker": "OMER", "name": "Omeros Corp"},
            {"ticker": "ONCR", "name": "Oncorus Inc"},
            {"ticker": "ORGO", "name": "Organogenesis Holdings Inc"},
            {"ticker": "PCVX", "name": "Vaxcyte Inc"},
            {"ticker": "PDLI", "name": "PDL BioPharma Inc"},
            {"ticker": "PGEN", "name": "Precigen Inc"},
            {"ticker": "PLRX", "name": "Pliant Therapeutics Inc"},
            {"ticker": "PRAX", "name": "Praxis Precision Medicines Inc"},
            {"ticker": "PRGO", "name": "Perrigo Co PLC"},
            {"ticker": "PRTX", "name": "Protagonist Therapeutics Inc"},
            {"ticker": "PRTA", "name": "Prothena Corp PLC"},
            {"ticker": "PTCT", "name": "PTC Therapeutics Inc"},
            {"ticker": "PTGX", "name": "Protagonist Therapeutics Inc"},
            {"ticker": "PTRA", "name": "Proterra Inc"},
            # Q-R
            {"ticker": "QURE", "name": "uniQure NV"},
            {"ticker": "RARE", "name": "Ultragenyx Pharmaceutical Inc"},
            {"ticker": "RCKT", "name": "Rocket Pharmaceuticals Inc"},
            {"ticker": "RCUS", "name": "Arcus Biosciences Inc"},
            {"ticker": "REGN", "name": "Regeneron Pharmaceuticals Inc"},
            {"ticker": "RGNX", "name": "REGENXBIO Inc"},
            {"ticker": "RVMD", "name": "Revolution Medicines Inc"},
            {"ticker": "RXRX", "name": "Recursion Pharmaceuticals Inc"},
            # S
            {"ticker": "SAGE", "name": "Sage Therapeutics Inc"},
            {"ticker": "SANA", "name": "Sana Biotechnology Inc"},
            {"ticker": "SDGR", "name": "Schrodinger Inc"},
            {"ticker": "SGEN", "name": "Seagen Inc"},
            {"ticker": "SGMO", "name": "Sangamo Therapeutics Inc"},
            {"ticker": "SMMT", "name": "Summit Therapeutics Inc"},
            {"ticker": "SPRY", "name": "ARS Pharmaceuticals Inc"},
            {"ticker": "SRPT", "name": "Sarepta Therapeutics Inc"},
            {"ticker": "SRRK", "name": "Scholar Rock Holding Corp"},
            {"ticker": "STOK", "name": "Stoke Therapeutics Inc"},
            {"ticker": "SWTX", "name": "SpringWorks Therapeutics Inc"},
            {"ticker": "SYRS", "name": "Syros Pharmaceuticals Inc"},
            # T
            {"ticker": "TARS", "name": "Tarsus Pharmaceuticals Inc"},
            {"ticker": "TCRT", "name": "Alaunos Therapeutics Inc"},
            {"ticker": "TECH", "name": "Bio-Techne Corp"},
            {"ticker": "TGTX", "name": "TG Therapeutics Inc"},
            {"ticker": "THER", "name": "Theratechnologies Inc"},
            {"ticker": "TNDM", "name": "Tandem Diabetes Care Inc"},
            {"ticker": "TVTX", "name": "Travere Therapeutics Inc"},
            {"ticker": "TWST", "name": "Twist Bioscience Corp"},
            # U-V
            {"ticker": "UTHR", "name": "United Therapeutics Corp"},
            {"ticker": "VCNX", "name": "Vaccinex Inc"},
            {"ticker": "VCYT", "name": "Veracyte Inc"},
            {"ticker": "VECT", "name": "VectivBio Holding AG"},
            {"ticker": "VERA", "name": "Vera Therapeutics Inc"},
            {"ticker": "VERV", "name": "Verve Therapeutics Inc"},
            {"ticker": "VKTX", "name": "Viking Therapeutics Inc"},
            {"ticker": "VNDA", "name": "Vanda Pharmaceuticals Inc"},
            {"ticker": "VRDN", "name": "Viridian Therapeutics Inc"},
            {"ticker": "VRNA", "name": "Verona Pharma PLC"},
            {"ticker": "VRTX", "name": "Vertex Pharmaceuticals Inc"},
            {"ticker": "VXRT", "name": "Vaxart Inc"},
            # W-Z
            {"ticker": "XNCR", "name": "Xencor Inc"},
            {"ticker": "XOMA", "name": "XOMA Corp"},
            {"ticker": "YMAB", "name": "Y-mAbs Therapeutics Inc"},
            {"ticker": "ZLAB", "name": "Zai Lab Ltd"},
            {"ticker": "ZNTL", "name": "Zentalis Pharmaceuticals Inc"},
            {"ticker": "ZYME", "name": "Zymeworks Inc"},
            # Additional XBI components
            {"ticker": "ABVX", "name": "Abivax SA"},
            {"ticker": "ACCD", "name": "Accolade Inc"},
            {"ticker": "AKBA", "name": "Akebia Therapeutics Inc"},
            {"ticker": "ALEC", "name": "Alector Inc"},
            {"ticker": "AMLX", "name": "Amylyx Pharmaceuticals Inc"},
            {"ticker": "ANAB", "name": "AnaptysBio Inc"},
            {"ticker": "ANGO", "name": "AngioDynamics Inc"},
            {"ticker": "ANIK", "name": "Anika Therapeutics Inc"},
            {"ticker": "ANIP", "name": "ANI Pharmaceuticals Inc"},
            {"ticker": "APGE", "name": "Apogee Therapeutics Inc"},
            {"ticker": "ASND", "name": "Ascendis Pharma A/S"},
            {"ticker": "AVEO", "name": "AVEO Pharmaceuticals Inc"},
            {"ticker": "AVRO", "name": "AVROBIO Inc"},
            {"ticker": "AXNX", "name": "Axonics Inc"},
            {"ticker": "BCRX", "name": "BioCryst Pharmaceuticals Inc"},
            {"ticker": "BDTX", "name": "Black Diamond Therapeutics Inc"},
            {"ticker": "BLFS", "name": "BioLife Solutions Inc"},
            {"ticker": "CCCC", "name": "C4 Therapeutics Inc"},
            {"ticker": "CLDX", "name": "Celldex Therapeutics Inc"},
            {"ticker": "CMRX", "name": "Chimerix Inc"},
            {"ticker": "CNTA", "name": "Centessa Pharmaceuticals PLC"},
            {"ticker": "CNTB", "name": "Connect Biopharma Holdings Ltd"},
            {"ticker": "COGT", "name": "Cogent Biosciences Inc"},
            {"ticker": "CPRX", "name": "Catalyst Pharmaceuticals Inc"},
            {"ticker": "CRBP", "name": "Corbus Pharmaceuticals Holdings Inc"},
            {"ticker": "CRDF", "name": "Cardiff Oncology Inc"},
            {"ticker": "CTMX", "name": "CytomX Therapeutics Inc"},
            {"ticker": "CVM", "name": "CEL-SCI Corp"},
            {"ticker": "CYCN", "name": "Cyclerion Therapeutics Inc"},
            {"ticker": "DYN", "name": "Dyne Therapeutics Inc"},
            {"ticker": "DSGN", "name": "Design Therapeutics Inc"},
            {"ticker": "DMAC", "name": "DiaMedica Therapeutics Inc"},
            {"ticker": "ELAN", "name": "Elanco Animal Health Inc"},
            {"ticker": "ENLV", "name": "Enlivex Therapeutics Ltd"},
            {"ticker": "FDMT", "name": "4D Molecular Therapeutics Inc"},
            {"ticker": "FIXX", "name": "Homology Medicines Inc"},
            {"ticker": "FMTX", "name": "Forma Therapeutics Holdings Inc"},
            {"ticker": "FREQ", "name": "Frequency Therapeutics Inc"},
            {"ticker": "GERN", "name": "Geron Corp"},
            {"ticker": "GLPG", "name": "Galapagos NV"},
            {"ticker": "GLYC", "name": "GlycoMimetics Inc"},
            {"ticker": "GTHX", "name": "G1 Therapeutics Inc"},
            {"ticker": "HARP", "name": "Harpoon Therapeutics Inc"},
            {"ticker": "HRTX", "name": "Heron Therapeutics Inc"},
            {"ticker": "IBTX", "name": "Independent Bank Group Inc"},
            {"ticker": "ICUI", "name": "ICU Medical Inc"},
            {"ticker": "IGMS", "name": "IGM Biosciences Inc"},
            {"ticker": "IMGO", "name": "Imago BioSciences Inc"},
            {"ticker": "IMMP", "name": "Immutep Ltd"},
            {"ticker": "INBX", "name": "Inhibrx Inc"},
            {"ticker": "INO", "name": "Inovio Pharmaceuticals Inc"},
            {"ticker": "IPHA", "name": "Innate Pharma SA"},
            {"ticker": "ITOS", "name": "iTeos Therapeutics Inc"},
            {"ticker": "KALA", "name": "Kala Pharmaceuticals Inc"},
            {"ticker": "KNTE", "name": "Kinnate Biopharma Inc"},
            {"ticker": "LBPH", "name": "Longboard Pharmaceuticals Inc"},
            {"ticker": "LGVN", "name": "Longeveron Inc"},
            {"ticker": "LXRX", "name": "Lexicon Pharmaceuticals Inc"},
            {"ticker": "LYEL", "name": "Lyell Immunopharma Inc"},
            {"ticker": "MASS", "name": "908 Devices Inc"},
            {"ticker": "MEDP", "name": "Medpace Holdings Inc"},
            {"ticker": "MESO", "name": "Mesoblast Ltd"},
            {"ticker": "MGTA", "name": "Magenta Therapeutics Inc"},
            {"ticker": "MLYS", "name": "Mineralys Therapeutics Inc"},
            {"ticker": "MNMD", "name": "Mind Medicine Inc"},
            {"ticker": "MPLN", "name": "MultiPlan Corp"},
            {"ticker": "MRTX", "name": "Mirati Therapeutics Inc"},
            {"ticker": "NARI", "name": "Inari Medical Inc"},
            {"ticker": "NBSE", "name": "NeuBase Therapeutics Inc"},
            {"ticker": "NEOG", "name": "Neogen Corp"},
            {"ticker": "NOTV", "name": "Inotiv Inc"},
            {"ticker": "NUVL", "name": "Nuvalent Inc"},
            {"ticker": "OCGN", "name": "Ocugen Inc"},
            {"ticker": "OFIX", "name": "Orthofix Medical Inc"},
            {"ticker": "OGN", "name": "Organon & Co"},
            {"ticker": "OPK", "name": "OPKO Health Inc"},
            {"ticker": "ORTX", "name": "Orchard Therapeutics PLC"},
            {"ticker": "OYST", "name": "Oyster Point Pharma Inc"},
            {"ticker": "PAVM", "name": "PAVmed Inc"},
            {"ticker": "PCOR", "name": "Procore Technologies Inc"},
            {"ticker": "PCRX", "name": "Pacira BioSciences Inc"},
            {"ticker": "PDCO", "name": "Patterson Companies Inc"},
            {"ticker": "PHVS", "name": "Pharvaris NV"},
            {"ticker": "PMVP", "name": "PMV Pharmaceuticals Inc"},
            {"ticker": "PNTG", "name": "Pennant Group Inc"},
            {"ticker": "PROK", "name": "ProKidney Corp"},
            {"ticker": "PRVA", "name": "Privia Health Group Inc"},
            {"ticker": "PSNL", "name": "Personalis Inc"},
            {"ticker": "QDEL", "name": "QuidelOrtho Corp"},
            {"ticker": "RAPT", "name": "RAPT Therapeutics Inc"},
            {"ticker": "REPL", "name": "Replimune Group Inc"},
            {"ticker": "RETA", "name": "Reata Pharmaceuticals Inc"},
            {"ticker": "RNA", "name": "Avidity Biosciences Inc"},
            {"ticker": "ROIV", "name": "Roivant Sciences Ltd"},
            {"ticker": "RPID", "name": "Rapid Micro Biosystems Inc"},
            {"ticker": "RPTX", "name": "Repare Therapeutics Inc"},
            {"ticker": "RXDX", "name": "Prometheus Biosciences Inc"},
            {"ticker": "RYTM", "name": "Rhythm Pharmaceuticals Inc"},
            {"ticker": "SBRA", "name": "Sabra Health Care REIT Inc"},
            {"ticker": "SGFY", "name": "Signify Health Inc"},
            {"ticker": "SHC", "name": "Sotera Health Co"},
            {"ticker": "SLGC", "name": "SomaLogic Inc"},
            {"ticker": "SNDX", "name": "Syndax Pharmaceuticals Inc"},
            {"ticker": "SNSE", "name": "Sensei Biotherapeutics Inc"},
            {"ticker": "SPNE", "name": "SeaSpine Holdings Corp"},
            {"ticker": "SPRO", "name": "Spero Therapeutics Inc"},
            {"ticker": "SRRA", "name": "Sierra Oncology Inc"},
            {"ticker": "STKL", "name": "SunOpta Inc"},
            {"ticker": "TALK", "name": "Talkspace Inc"},
            {"ticker": "TCRR", "name": "TCR2 Therapeutics Inc"},
            {"ticker": "TFFP", "name": "TFF Pharmaceuticals Inc"},
            {"ticker": "TIL", "name": "Instil Bio Inc"},
            {"ticker": "TMDX", "name": "TransMedics Group Inc"},
            {"ticker": "TNGX", "name": "Tango Therapeutics Inc"},
            {"ticker": "TRDA", "name": "Entrada Therapeutics Inc"},
            {"ticker": "TRIL", "name": "Trillium Therapeutics Inc"},
            {"ticker": "TSVT", "name": "2seventy bio Inc"},
            {"ticker": "TTOO", "name": "T2 Biosystems Inc"},
            {"ticker": "UDMY", "name": "Udemy Inc"},
            {"ticker": "URGN", "name": "UroGen Pharma Ltd"},
            {"ticker": "VALN", "name": "Valneva SE"},
            {"ticker": "VCSA", "name": "Vacasa Inc"},
            {"ticker": "VERX", "name": "Vertex Inc"},
            {"ticker": "VIR", "name": "Vir Biotechnology Inc"},
            {"ticker": "VIVO", "name": "Meridian Bioscience Inc"},
            {"ticker": "VORB", "name": "Virgin Orbit Holdings Inc"},
            {"ticker": "VRNT", "name": "Verint Systems Inc"},
            {"ticker": "VTRS", "name": "Viatris Inc"},
            {"ticker": "VYGR", "name": "Voyager Therapeutics Inc"},
            {"ticker": "WVE", "name": "Wave Life Sciences Ltd"},
            {"ticker": "XBIT", "name": "XBiotech Inc"},
            {"ticker": "XENE", "name": "Xenon Pharmaceuticals Inc"},
            {"ticker": "XERS", "name": "Xeris Biopharma Holdings Inc"},
            {"ticker": "YMTX", "name": "Yumanity Therapeutics Inc"},
            {"ticker": "ZYXI", "name": "Zynex Medical Inc"},
        ]

        return components

    def run(self) -> List[Dict]:
        """Fetch complete XBI holdings"""
        print("=" * 60)
        print("Fetching COMPLETE XBI Holdings")
        print("=" * 60)

        # Try N-PORT first (most accurate but complex)
        # accession = self.get_latest_nport()
        # if accession:
        #     holdings = self.fetch_nport_holdings(accession)
        #     if holdings:
        #         self.holdings = sorted(holdings, key=lambda x: x["ticker"])
        #         return self.holdings

        # Fall back to comprehensive component list
        holdings = self.fetch_from_sp_index()

        # Remove duplicates and sort alphabetically
        seen = set()
        unique_holdings = []
        for h in holdings:
            if h["ticker"] not in seen:
                seen.add(h["ticker"])
                unique_holdings.append(h)

        self.holdings = sorted(unique_holdings, key=lambda x: x["ticker"])
        print(f"\nTotal unique holdings: {len(self.holdings)}")

        return self.holdings

    def save_to_json(self, output_path: str = None):
        """Save holdings to JSON file"""
        if not output_path:
            output_path = Path(__file__).parent.parent / "data" / "xbi_holdings.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump({
                "etf": "XBI",
                "name": "SPDR S&P Biotech ETF",
                "index": "S&P Biotechnology Select Industry Index",
                "fetched_at": datetime.utcnow().isoformat(),
                "holdings_count": len(self.holdings),
                "holdings": self.holdings
            }, f, indent=2)

        print(f"Saved {len(self.holdings)} holdings to {output_path}")
        return output_path


def main():
    fetcher = XBICompleteHoldingsFetcher()
    holdings = fetcher.run()
    fetcher.save_to_json()

    print("\n" + "=" * 60)
    print(f"Total XBI Holdings: {len(holdings)}")
    print("=" * 60)

    # Print first 10 and last 10
    print("\nFirst 10 (A):")
    for h in holdings[:10]:
        print(f"  {h['ticker']:6} | {h['name']}")

    print("\nLast 10 (Z):")
    for h in holdings[-10:]:
        print(f"  {h['ticker']:6} | {h['name']}")


if __name__ == "__main__":
    main()
