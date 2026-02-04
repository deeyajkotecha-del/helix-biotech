"""
IR Website Mapping for Biopharma Companies

This file maps tickers to their Investor Relations pages where presentations are found.
Used by the automated scraper to find and download corporate presentations.

Last updated: February 2026
"""

IR_WEBSITE_MAP = {
    # ==========================================================================
    # HIGH PRIORITY COMPANIES
    # ==========================================================================

    "ASND": {
        "name": "Ascendis Pharma",
        "ir_url": "https://investors.ascendispharma.com",
        "presentations_url": "https://investors.ascendispharma.com/events-and-presentations",
        "sec_filings": "https://investors.ascendispharma.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation", "R&D Day"],
        "market_cap": "$14B",
        "priority": "HIGH"
    },

    "ARGX": {
        "name": "argenx SE",
        "ir_url": "https://www.argenx.com/investors",
        "presentations_url": "https://www.argenx.com/investors/events-presentations",
        "sec_filings": "https://www.argenx.com/investors/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Day", "R&D Day"],
        "market_cap": "$35B",
        "priority": "HIGH"
    },

    "NUVL": {
        "name": "Nuvalent",
        "ir_url": "https://ir.nuvalent.com",
        "presentations_url": "https://ir.nuvalent.com/events-and-presentations",
        "sec_filings": "https://ir.nuvalent.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$6B",
        "priority": "HIGH"
    },

    "CNTA": {
        "name": "Centessa Pharmaceuticals",
        "ir_url": "https://ir.centessa.com",
        "presentations_url": "https://ir.centessa.com/events-and-presentations",
        "sec_filings": "https://ir.centessa.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$3B",
        "priority": "HIGH"
    },

    "SLNO": {
        "name": "Soleno Therapeutics",
        "ir_url": "https://investors.soleno.life",
        "presentations_url": "https://investors.soleno.life/events-and-presentations",
        "sec_filings": "https://investors.soleno.life/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1.5B",
        "priority": "HIGH"
    },

    "EWTX": {
        "name": "Edgewise Therapeutics",
        "ir_url": "https://ir.edgewisetx.com",
        "presentations_url": "https://ir.edgewisetx.com/events-and-presentations",
        "sec_filings": "https://ir.edgewisetx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1.5B",
        "priority": "HIGH"
    },

    # ==========================================================================
    # MED-HIGH PRIORITY COMPANIES
    # ==========================================================================

    "TRML": {
        "name": "Tourmaline Bio",
        "ir_url": "https://ir.tourmalinebio.com",
        "presentations_url": "https://ir.tourmalinebio.com/events-and-presentations",
        "sec_filings": "https://ir.tourmalinebio.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1.5B",
        "priority": "MED-HIGH"
    },

    "OCUL": {
        "name": "Ocular Therapeutix",
        "ir_url": "https://ir.ocutx.com",
        "presentations_url": "https://ir.ocutx.com/events-and-presentations",
        "sec_filings": "https://ir.ocutx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MED-HIGH"
    },

    "GPCR": {
        "name": "Structure Therapeutics",
        "ir_url": "https://ir.structuretx.com",
        "presentations_url": "https://ir.structuretx.com/events-and-presentations",
        "sec_filings": "https://ir.structuretx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1.5B",
        "priority": "MED-HIGH"
    },

    "ELVN": {
        "name": "Enliven Therapeutics",
        "ir_url": "https://ir.enliventx.com",
        "presentations_url": "https://ir.enliventx.com/events-and-presentations",
        "sec_filings": "https://ir.enliventx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$500M",
        "priority": "MED-HIGH"
    },

    "SION": {
        "name": "Sionna Therapeutics",
        "ir_url": "https://investors.sionnatx.com",
        "presentations_url": "https://investors.sionnatx.com/events-and-presentations",
        "sec_filings": "https://investors.sionnatx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$3B",
        "priority": "MED-HIGH"
    },

    "NAMS": {
        "name": "NewAmsterdam Pharma",
        "ir_url": "https://ir.newamsterdampharma.com",
        "presentations_url": "https://ir.newamsterdampharma.com/events-and-presentations",
        "sec_filings": "https://ir.newamsterdampharma.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$3B",
        "priority": "MED-HIGH"
    },

    "MLYS": {
        "name": "Mineralys Therapeutics",
        "ir_url": "https://ir.mineralystx.com",
        "presentations_url": "https://ir.mineralystx.com/events-and-presentations",
        "sec_filings": "https://ir.mineralystx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$2B",
        "priority": "MED-HIGH"
    },

    "CDTX": {
        "name": "Cidara Therapeutics",
        "ir_url": "https://ir.cidara.com",
        "presentations_url": "https://ir.cidara.com/events-and-presentations",
        "sec_filings": "https://ir.cidara.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$500M",
        "priority": "MED-HIGH"
    },

    "ORKA": {
        "name": "Oruka Therapeutics",
        "ir_url": "https://ir.orukatx.com",
        "presentations_url": "https://ir.orukatx.com/events-and-presentations",
        "sec_filings": "https://ir.orukatx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$500M",
        "priority": "MED-HIGH"
    },

    # ==========================================================================
    # MEDIUM PRIORITY COMPANIES
    # ==========================================================================

    "SEPN": {
        "name": "Septerna",
        "ir_url": "https://investors.septerna.com",
        "presentations_url": "https://investors.septerna.com/events-and-presentations",
        "sec_filings": "https://investors.septerna.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MEDIUM"
    },

    "TSHA": {
        "name": "Taysha Gene Therapies",
        "ir_url": "https://ir.tayshagtx.com",
        "presentations_url": "https://ir.tayshagtx.com/events-and-presentations",
        "sec_filings": "https://ir.tayshagtx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$500M",
        "priority": "MEDIUM"
    },

    "LENZ": {
        "name": "Lenz Therapeutics",
        "ir_url": "https://ir.lenz.com",
        "presentations_url": "https://ir.lenz.com/events-and-presentations",
        "sec_filings": "https://ir.lenz.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MEDIUM"
    },

    "TYRA": {
        "name": "Tyra Biosciences",
        "ir_url": "https://ir.tyrabio.com",
        "presentations_url": "https://ir.tyrabio.com/events-and-presentations",
        "sec_filings": "https://ir.tyrabio.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$600M",
        "priority": "MEDIUM"
    },

    "IRON": {
        "name": "Disc Medicine",
        "ir_url": "https://ir.discmedicine.com",
        "presentations_url": "https://ir.discmedicine.com/events-and-presentations",
        "sec_filings": "https://ir.discmedicine.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1.5B",
        "priority": "MEDIUM"
    },

    "DNTH": {
        "name": "Dianthus Therapeutics",
        "ir_url": "https://ir.dianthustx.com",
        "presentations_url": "https://ir.dianthustx.com/events-and-presentations",
        "sec_filings": "https://ir.dianthustx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MEDIUM"
    },

    "BCAX": {
        "name": "Bicara Therapeutics",
        "ir_url": "https://ir.bicaratx.com",
        "presentations_url": "https://ir.bicaratx.com/events-and-presentations",
        "sec_filings": "https://ir.bicaratx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$500M",
        "priority": "MEDIUM"
    },

    "GHRS": {
        "name": "GH Research",
        "ir_url": "https://ir.ghres.com",
        "presentations_url": "https://ir.ghres.com/events-and-presentations",
        "sec_filings": "https://ir.ghres.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$600M",
        "priority": "MEDIUM"
    },

    "SPRY": {
        "name": "ARS Pharmaceuticals",
        "ir_url": "https://ir.ars-pharma.com",
        "presentations_url": "https://ir.ars-pharma.com/events-and-presentations",
        "sec_filings": "https://ir.ars-pharma.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MEDIUM"
    },

    # ==========================================================================
    # MED-LOW PRIORITY COMPANIES
    # ==========================================================================

    "PHVS": {
        "name": "Pharvaris",
        "ir_url": "https://ir.pharvaris.com",
        "presentations_url": "https://ir.pharvaris.com/events-and-presentations",
        "sec_filings": "https://ir.pharvaris.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MED-LOW"
    },

    "CLYM": {
        "name": "Climb Bio",
        "ir_url": "https://investors.climbbio.com",
        "presentations_url": "https://investors.climbbio.com/events-and-presentations",
        "sec_filings": "https://investors.climbbio.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$200M",
        "priority": "MED-LOW"
    },

    "PEPG": {
        "name": "PepGen",
        "ir_url": "https://ir.pepgen.com",
        "presentations_url": "https://ir.pepgen.com/events-and-presentations",
        "sec_filings": "https://ir.pepgen.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$300M",
        "priority": "MED-LOW"
    },

    "FDMT": {
        "name": "4D Molecular Therapeutics",
        "ir_url": "https://ir.4dmoleculartherapeutics.com",
        "presentations_url": "https://ir.4dmoleculartherapeutics.com/events-and-presentations",
        "sec_filings": "https://ir.4dmoleculartherapeutics.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$400M",
        "priority": "MED-LOW"
    },

    "SLDB": {
        "name": "Solid Biosciences",
        "ir_url": "https://ir.solidbio.com",
        "presentations_url": "https://ir.solidbio.com/events-and-presentations",
        "sec_filings": "https://ir.solidbio.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$300M",
        "priority": "MED-LOW"
    },

    "MTSR": {
        "name": "Metsera",
        "ir_url": "https://investors.metsera.com",
        "presentations_url": "https://investors.metsera.com/events-and-presentations",
        "sec_filings": "https://investors.metsera.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$1B",
        "priority": "MED-LOW"
    },

    "ARTV": {
        "name": "Artiva Biotherapeutics",
        "ir_url": "https://ir.artivabio.com",
        "presentations_url": "https://ir.artivabio.com/events-and-presentations",
        "sec_filings": "https://ir.artivabio.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$200M",
        "priority": "MED-LOW"
    },

    "LRMR": {
        "name": "Larimar Therapeutics",
        "ir_url": "https://ir.larimartx.com",
        "presentations_url": "https://ir.larimartx.com/events-and-presentations",
        "sec_filings": "https://ir.larimartx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$150M",
        "priority": "MED-LOW"
    },

    "NKTX": {
        "name": "Nkarta",
        "ir_url": "https://ir.nkartatx.com",
        "presentations_url": "https://ir.nkartatx.com/events-and-presentations",
        "sec_filings": "https://ir.nkartatx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$200M",
        "priority": "MED-LOW"
    },

    "TNGX": {
        "name": "Tango Therapeutics",
        "ir_url": "https://ir.tangotx.com",
        "presentations_url": "https://ir.tangotx.com/events-and-presentations",
        "sec_filings": "https://ir.tangotx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$500M",
        "priority": "MED-LOW"
    },

    "CTMX": {
        "name": "CytomX Therapeutics",
        "ir_url": "https://ir.cytomx.com",
        "presentations_url": "https://ir.cytomx.com/events-and-presentations",
        "sec_filings": "https://ir.cytomx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$300M",
        "priority": "MED-LOW"
    },

    "ACRV": {
        "name": "Acrivon Therapeutics",
        "ir_url": "https://ir.acrivon.com",
        "presentations_url": "https://ir.acrivon.com/events-and-presentations",
        "sec_filings": "https://ir.acrivon.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$150M",
        "priority": "MED-LOW"
    },

    "HOWL": {
        "name": "Werewolf Therapeutics",
        "ir_url": "https://ir.werewolftx.com",
        "presentations_url": "https://ir.werewolftx.com/events-and-presentations",
        "sec_filings": "https://ir.werewolftx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$150M",
        "priority": "MED-LOW"
    },

    "ELDN": {
        "name": "Eledon Pharmaceuticals",
        "ir_url": "https://ir.eledonpharma.com",
        "presentations_url": "https://ir.eledonpharma.com/events-and-presentations",
        "sec_filings": "https://ir.eledonpharma.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$100M",
        "priority": "MED-LOW"
    },

    "JBIO": {
        "name": "Jade Biosciences",
        "ir_url": "https://ir.jadebiosciences.com",
        "presentations_url": "https://ir.jadebiosciences.com/events-and-presentations",
        "sec_filings": "https://ir.jadebiosciences.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$300M",
        "priority": "MED-LOW"
    },

    "SRZN": {
        "name": "Surrozen",
        "ir_url": "https://ir.surrozen.com",
        "presentations_url": "https://ir.surrozen.com/events-and-presentations",
        "sec_filings": "https://ir.surrozen.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$100M",
        "priority": "MED-LOW"
    },

    "WGS": {
        "name": "GeneDx",
        "ir_url": "https://ir.genedx.com",
        "presentations_url": "https://ir.genedx.com/events-and-presentations",
        "sec_filings": "https://ir.genedx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$2B",
        "priority": "MED-LOW"
    },

    "GKOS": {
        "name": "Glaukos",
        "ir_url": "https://investors.glaukos.com",
        "presentations_url": "https://investors.glaukos.com/events-and-presentations",
        "sec_filings": "https://investors.glaukos.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$4B",
        "priority": "MED-LOW"
    },

    "INSP": {
        "name": "Inspire Medical Systems",
        "ir_url": "https://investors.inspiresleep.com",
        "presentations_url": "https://investors.inspiresleep.com/events-and-presentations",
        "sec_filings": "https://investors.inspiresleep.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation"],
        "market_cap": "$3B",
        "priority": "MED-LOW"
    },

    # ==========================================================================
    # EXISTING COMPANIES (Already have some data)
    # ==========================================================================

    "KYMR": {
        "name": "Kymera Therapeutics",
        "ir_url": "https://investors.kymeratx.com",
        "presentations_url": "https://investors.kymeratx.com/events-and-presentations",
        "sec_filings": "https://investors.kymeratx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation", "R&D Day"],
        "market_cap": "$3B",
        "priority": "HIGH",
        "status": "DATA_COMPLETE"
    },

    "ARWR": {
        "name": "Arrowhead Pharmaceuticals",
        "ir_url": "https://ir.arrowheadpharma.com",
        "presentations_url": "https://ir.arrowheadpharma.com/events-and-presentations",
        "sec_filings": "https://ir.arrowheadpharma.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Presentation", "R&D Day"],
        "market_cap": "$5B",
        "priority": "HIGH",
        "status": "PARTIAL"
    },

    # ==========================================================================
    # LARGE CAP DIVERSIFIED (For context/comparison)
    # ==========================================================================

    "REGN": {
        "name": "Regeneron Pharmaceuticals",
        "ir_url": "https://investor.regeneron.com",
        "presentations_url": "https://investor.regeneron.com/events-and-presentations",
        "sec_filings": "https://investor.regeneron.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Day", "R&D Day"],
        "market_cap": "$100B",
        "priority": "LOW",
        "notes": "Reference company for Dupixent comparisons"
    },

    "VRTX": {
        "name": "Vertex Pharmaceuticals",
        "ir_url": "https://investors.vrtx.com",
        "presentations_url": "https://investors.vrtx.com/events-and-presentations",
        "sec_filings": "https://investors.vrtx.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Day"],
        "market_cap": "$120B",
        "priority": "LOW",
        "notes": "Reference company for CF comparisons"
    },

    "ALNY": {
        "name": "Alnylam Pharmaceuticals",
        "ir_url": "https://investors.alnylam.com",
        "presentations_url": "https://investors.alnylam.com/events-and-presentations",
        "sec_filings": "https://investors.alnylam.com/sec-filings",
        "presentation_patterns": ["Corporate Presentation", "Investor Day", "R&D Day"],
        "market_cap": "$30B",
        "priority": "MEDIUM",
        "notes": "RNA therapeutics leader"
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_ir_config(ticker: str) -> dict:
    """Get the full IR configuration for a ticker."""
    return IR_WEBSITE_MAP.get(ticker.upper())


def get_ir_url(ticker: str) -> str:
    """Get the IR website URL for a ticker."""
    company = IR_WEBSITE_MAP.get(ticker.upper())
    if company:
        return company.get("ir_url")
    return None


def get_presentations_url(ticker: str) -> str:
    """Get the presentations page URL for a ticker."""
    company = IR_WEBSITE_MAP.get(ticker.upper())
    if company:
        return company.get("presentations_url")
    return None


def get_companies_by_priority(priority: str) -> list:
    """Get list of tickers by priority level."""
    return [
        ticker for ticker, data in IR_WEBSITE_MAP.items()
        if data.get("priority") == priority
    ]


def get_all_tickers() -> list:
    """Get all tickers in the map."""
    return list(IR_WEBSITE_MAP.keys())


def get_high_priority_tickers() -> list:
    """Get HIGH and MED-HIGH priority tickers."""
    return [
        ticker for ticker, data in IR_WEBSITE_MAP.items()
        if data.get("priority") in ["HIGH", "MED-HIGH"]
    ]


def get_company_info(ticker: str) -> dict:
    """Get full company info for a ticker."""
    return IR_WEBSITE_MAP.get(ticker.upper())


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def print_summary():
    """Print summary of IR website mapping."""
    priorities = {}
    for ticker, data in IR_WEBSITE_MAP.items():
        priority = data.get("priority", "UNKNOWN")
        if priority not in priorities:
            priorities[priority] = []
        priorities[priority].append(ticker)

    print("=" * 60)
    print("IR WEBSITE MAPPING SUMMARY")
    print("=" * 60)
    print(f"Total companies: {len(IR_WEBSITE_MAP)}")
    print()
    for priority in ["HIGH", "MED-HIGH", "MEDIUM", "MED-LOW", "LOW"]:
        if priority in priorities:
            print(f"{priority}: {len(priorities[priority])} companies")
            print(f"  {', '.join(sorted(priorities[priority]))}")
            print()


if __name__ == "__main__":
    print_summary()
