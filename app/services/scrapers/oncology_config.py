"""
Oncology IR Page Configuration

Maps 13 oncology companies to their investor relations and publications pages
for scraping. Each company has one or more pages (events, press releases,
publications) with platform hints for the scraper.

URLs verified 2026-03-02 via curl-cffi probe.

Page types:
  - "events"       — IR events & presentations (year-filter crawled)
  - "press"        — IR press releases
  - "publications" — corporate site posters, abstracts, conference materials

Platforms:
  - "standard"  — vanilla corporate IR/website page (most common)
  - "q4"        — Q4 Inc hosted IR pages (/static-files/ links)
  - "notified"  — Notified/default.aspx hosted IR pages (JS-rendered)
"""

ONCOLOGY_COMPANIES = {
    "NUVL": {
        "name": "Nuvalent",
        "pages": [
            {"type": "events", "url": "https://investors.nuvalent.com/events", "platform": "standard"},
            {"type": "press", "url": "https://investors.nuvalent.com/news", "platform": "standard"},
            {"type": "publications", "url": "https://www.nuvalent.com/publications", "platform": "standard"},
        ],
    },
    "CELC": {
        "name": "Celcuity",
        "pages": [
            {"type": "events", "url": "https://ir.celcuity.com/events-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.celcuity.com/press-releases", "platform": "q4"},
            {"type": "publications", "url": "https://www.celcuity.com/science/publications/", "platform": "standard"},
        ],
    },
    "PYXS": {
        "name": "Pyxis Oncology",
        "pages": [
            {"type": "events", "url": "https://ir.pyxisoncology.com/events-and-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.pyxisoncology.com/press-releases", "platform": "q4"},
            {"type": "publications", "url": "https://pyxisoncology.com/clinical-programs/scientific-publications/", "platform": "standard"},
        ],
    },
    "RVMD": {
        "name": "Revolution Medicines",
        "pages": [
            {"type": "events", "url": "https://ir.revmed.com/events-and-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.revmed.com/press-releases", "platform": "q4"},
            # No publications page — revmed.com/publications/ is an empty stub with 0 PDFs
        ],
    },
    "RLAY": {
        "name": "Relay Therapeutics",
        "pages": [
            {"type": "events", "url": "https://ir.relaytx.com/news-events/events-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.relaytx.com/news-events/press-releases", "platform": "q4"},
            {"type": "publications", "url": "https://relaytx.com/publications/", "platform": "standard"},
        ],
    },
    "IOVA": {
        "name": "Iovance Biotherapeutics",
        "pages": [
            {"type": "events", "url": "https://ir.iovance.com/news-events/events-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.iovance.com/news-events/press-releases", "platform": "q4"},
            {"type": "publications", "url": "https://www.iovance.com/scientific-publications-presentations/", "platform": "standard"},
        ],
    },
    "VIR": {
        "name": "Vir Biotechnology",
        "pages": [
            {"type": "events", "url": "https://investors.vir.bio/events-and-presentations/default.aspx", "platform": "notified"},
            {"type": "press", "url": "https://investors.vir.bio/press-releases/default.aspx", "platform": "notified"},
            # No publications page — vir.bio/science/literature-archive/ links to external journals only
        ],
        # Notified pages use JS rendering — curl-cffi can fetch but no PDF links in HTML.
        # Paste PDF URLs here manually; the scraper processes these first.
        "direct_links": [],
    },
    "JANX": {
        "name": "Janux Therapeutics",
        "pages": [
            {"type": "events", "url": "https://investors.januxrx.com/investor-media/events-and-presentations/default.aspx", "platform": "notified"},
            {"type": "press", "url": "https://investors.januxrx.com/investor-media/news/default.aspx", "platform": "notified"},
            {"type": "publications", "url": "https://www.januxrx.com/publications/", "platform": "standard"},
        ],
        # Notified IR pages use JS rendering — curl-cffi can fetch but no PDF links in HTML.
        # Paste PDF URLs here manually; the scraper processes these first.
        "direct_links": [],
    },
    "CGON": {
        "name": "CG Oncology",
        "pages": [
            {"type": "events", "url": "https://ir.cgoncology.com/news-events/events-conferences", "platform": "q4"},
            {"type": "press", "url": "https://ir.cgoncology.com/news-events/press-releases", "platform": "q4"},
            {"type": "publications", "url": "https://cgoncology.com/abstracts-and-presentations/", "platform": "standard"},
        ],
    },
    "URGN": {
        "name": "UroGen Pharma",
        "pages": [
            {"type": "events", "url": "https://investors.urogen.com/events-and-presentations", "platform": "q4"},
            {"type": "press", "url": "https://investors.urogen.com/news-releases", "platform": "q4"},
            # No publications page — urogenmedicalaffairs.com/congress-materials is JS-rendered
        ],
    },
    "VSTM": {
        "name": "Verastem Oncology",
        "pages": [
            {"type": "events", "url": "https://investor.verastem.com/events", "platform": "q4"},
            {"type": "press", "url": "https://investor.verastem.com/news-releases", "platform": "q4"},
            {"type": "publications", "url": "https://www.verastem.com/research/resources/", "platform": "standard"},
        ],
    },
    "IBRX": {
        "name": "ImmunityBio",
        "pages": [
            {"type": "events", "url": "https://ir.immunitybio.com/company/events-and-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.immunitybio.com/company/press-releases", "platform": "q4"},
            {"type": "publications", "url": "https://immunitybio.com/research/", "platform": "standard"},
        ],
    },
    "TNGX": {
        "name": "Tango Therapeutics",
        "pages": [
            {"type": "events", "url": "https://ir.tangotx.com/news-events/events-presentations", "platform": "q4"},
            {"type": "press", "url": "https://ir.tangotx.com/news-events/news-releases", "platform": "q4"},
            {"type": "publications", "url": "https://www.tangotx.com/science/publications-posters/", "platform": "standard"},
        ],
    },
}


def get_oncology_config(ticker: str) -> dict | None:
    """Get the oncology IR config for a ticker, or None if not found."""
    return ONCOLOGY_COMPANIES.get(ticker.upper())


def get_all_oncology_tickers() -> list[str]:
    """Get all oncology ticker symbols."""
    return list(ONCOLOGY_COMPANIES.keys())
