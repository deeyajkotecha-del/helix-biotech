"""
Biotech IR Page Configuration — Full XBI Universe

Maps 60 biotech and pharma companies to their investor relations and publications
pages for scraping. Each company has one or more pages (events, press releases,
publications) with platform hints for the scraper.

Original 13 oncology companies: URLs verified 2026-03-02 via curl-cffi probe.
Expansion to 60 companies: URLs from XBI_UNIVERSE, verified 2026-03-24.

Page types:
  - "events"       — IR events & presentations (year-filter crawled)
  - "press"        — IR press releases
  - "publications" — corporate site posters, abstracts, conference materials

Content types:
  - "documents"  — pages containing PDF/PPTX download links (scraped now)
  - "text"       — pages containing article text, no downloads (scraped later)

Platforms:
  - "standard"  — vanilla corporate IR/website page (most common)
  - "q4"        — Q4 Inc hosted IR pages (/static-files/ links)
  - "notified"  — Notified/default.aspx hosted IR pages (JS-rendered)
  - "custom"    — company-specific site layout (needs manual inspection)
"""

# TODO: text content scraper for press releases

ONCOLOGY_COMPANIES = {

    # =========================================================================
    # CORE SMALL-CAP ONCOLOGY (original 13 — URLs verified via curl-cffi)
    # =========================================================================

    "NUVL": {
        "name": "Nuvalent",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investors.nuvalent.com/events", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://investors.nuvalent.com/news", "platform": "standard", "content_type": "text"},
            {"type": "publications", "url": "https://www.nuvalent.com/publications", "platform": "standard", "content_type": "documents"},
        ],
    },
    "CELC": {
        "name": "Celcuity",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.celcuity.com/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.celcuity.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.celcuity.com/science/publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "PYXS": {
        "name": "Pyxis Oncology",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.pyxisoncology.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.pyxisoncology.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://pyxisoncology.com/clinical-programs/scientific-publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "RVMD": {
        "name": "Revolution Medicines",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.revmed.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.revmed.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.revmed.com/publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "RLAY": {
        "name": "Relay Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.relaytx.com/news-events/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.relaytx.com/news-events/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://relaytx.com/publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "IOVA": {
        "name": "Iovance Biotherapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.iovance.com/news-events/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.iovance.com/news-events/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.iovance.com/scientific-publications-presentations/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "VIR": {
        "name": "Vir Biotechnology",
        "category": "infectious_disease",
        "pages": [
            {"type": "events", "url": "https://investors.vir.bio/events-and-presentations/default.aspx", "platform": "notified", "content_type": "documents"},
            {"type": "press", "url": "https://investors.vir.bio/press-releases/default.aspx", "platform": "notified", "content_type": "text"},
            # vir.bio/science/literature-archive/ links to external journals only
        ],
        "direct_links": [],
    },
    "JANX": {
        "name": "Janux Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investors.januxrx.com/investor-media/events-and-presentations/default.aspx", "platform": "notified", "content_type": "documents"},
            {"type": "press", "url": "https://investors.januxrx.com/investor-media/news/default.aspx", "platform": "notified", "content_type": "text"},
            {"type": "publications", "url": "https://www.januxrx.com/publications/", "platform": "standard", "content_type": "documents"},
        ],
        "direct_links": [],
    },
    "CGON": {
        "name": "CG Oncology",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.cgoncology.com/news-events/events-conferences", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.cgoncology.com/news-events/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://cgoncology.com/abstracts-and-presentations/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "URGN": {
        "name": "UroGen Pharma",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investors.urogen.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.urogen.com/news-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "VSTM": {
        "name": "Verastem Oncology",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investor.verastem.com/events", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.verastem.com/news-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.verastem.com/research/resources/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "IBRX": {
        "name": "ImmunityBio",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.immunitybio.com/company/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.immunitybio.com/company/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://immunitybio.com/research/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "TNGX": {
        "name": "Tango Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.tangotx.com/news-events/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.tangotx.com/news-events/news-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.tangotx.com/science/publications-posters/", "platform": "standard", "content_type": "documents"},
        ],
    },

    # =========================================================================
    # EXPANDED SMALL/MID-CAP BIOTECH
    # =========================================================================

    "CNTA": {
        "name": "Centessa Pharmaceuticals",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://investors.centessa.com/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.centessa.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "BCYC": {
        "name": "Bicycle Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.bicycletherapeutics.com/events-and-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.bicycletherapeutics.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.bicycletherapeutics.com/media/science-publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "ARGX": {
        "name": "argenx",
        "category": "immunology",
        "pages": [
            {"type": "events", "url": "https://www.argenx.com/investors/events-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.argenx.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://argenxmedical.com/en-us/congress-materials.html", "platform": "js_rendered", "content_type": "documents"},
            {"type": "publications", "url": "https://argenxmedical.com/en-us/congress-materials/neurology.html", "platform": "js_rendered", "content_type": "documents"},
            {"type": "publications", "url": "https://argenxmedical.com/en-us/congress-materials/hematology.html", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "KYMR": {
        "name": "Kymera Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investors.kymeratx.com/news-events/presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.kymeratx.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.kymeratx.com/science-innovation/resource-library/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "ALKS": {
        "name": "Alkermes",
        "category": "neuroscience",
        "pages": [
            # Fixed: correct URL is /investor-events-presentations/ (not /events-and-presentations)
            {"type": "events", "url": "https://investor.alkermes.com/investor-events-presentations/", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.alkermes.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "VKTX": {
        "name": "Viking Therapeutics",
        "category": "metabolic",
        "pages": [
            {"type": "events", "url": "https://ir.vikingtherapeutics.com/", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.vikingtherapeutics.com/press-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "GPCR": {
        "name": "Structure Therapeutics",
        "category": "metabolic",
        "pages": [
            {"type": "events", "url": "https://ir.structuretx.com/events-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.structuretx.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.structuretx.com/publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "ORKA": {
        "name": "Oruka Therapeutics",
        "category": "dermatology",
        "pages": [
            {"type": "events", "url": "https://ir.orukatx.com/news-events/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.oruka.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "MRNA": {
        "name": "Moderna",
        "category": "infectious_disease",
        "pages": [
            {"type": "events", "url": "https://investors.modernatx.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.modernatx.com/news/news-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "ROIV": {
        "name": "Roivant Sciences",
        "category": "multi",
        "pages": [
            {"type": "events", "url": "https://investor.roivant.com/news-events/events", "platform": "standard", "content_type": "documents"},
        ],
    },
    "PCVX": {
        "name": "Vaxcyte",
        "category": "infectious_disease",
        "pages": [
            {"type": "events", "url": "https://investors.vaxcyte.com/events-and-presentations/", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.vaxcyte.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "SRPT": {
        "name": "Sarepta Therapeutics",
        "category": "rare_disease",
        "pages": [
            # Fixed: correct URL is /events-presentations (not /events-and-presentations)
            {"type": "events", "url": "https://investorrelations.sarepta.com/events-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://investorrelations.sarepta.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.sarepta.com/science", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "SMMT": {
        "name": "Summit Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://smmttx.com/investor-information/summit-presentations/", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://ir.summittx.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://smmttx.com/publications/", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "INSM": {
        "name": "Insmed",
        "category": "rare_disease",
        "pages": [
            {"type": "events", "url": "https://investor.insmed.com/events", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.insmed.com/news-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "EXAS": {
        "name": "Exact Sciences (acquired by Abbott)",
        "category": "diagnostics",
        "pages": [
            # NOTE: Exact Sciences acquired by Abbott — IR site may be transitioning
            # Events page 404s with year filter; try standard to get base page
            {"type": "events", "url": "https://investor.exactsciences.com/events-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://investor.exactsciences.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "NBIX": {
        "name": "Neurocrine Biosciences",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://neurocrine.com/investors/webcasts-presentations/", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.neurocrine.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "CRNX": {
        "name": "Crinetics Pharmaceuticals",
        "category": "endocrinology",
        "pages": [
            {"type": "events", "url": "https://ir.crinetics.com/events-and-presentations/default.aspx", "platform": "notified", "content_type": "documents"},
            {"type": "press", "url": "https://ir.crinetics.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "DAWN": {
        "name": "Day One Biopharmaceuticals",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.dayonebio.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.dayonebio.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "RCUS": {
        "name": "Arcus Biosciences",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investors.arcusbio.com/events-and-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://investors.arcusbio.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://arcusbio.com/our-science/publications/", "platform": "standard", "content_type": "documents"},
        ],
    },
    "MDGL": {
        "name": "Madrigal Pharmaceuticals",
        "category": "metabolic",
        "pages": [
            {"type": "events", "url": "https://ir.madrigalpharma.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.madrigalpharma.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "MRTI": {
        "name": "Mirati Therapeutics",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.mirati.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.mirati.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "SAGE": {
        "name": "Sage Therapeutics",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://investor.sagerx.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.sagerx.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "AXSM": {
        "name": "Axsome Therapeutics",
        "category": "neuroscience",
        "pages": [
            # Correct URL is /webcasts-and-presentations (not /events-and-presentations)
            {"type": "events", "url": "https://axsometherapeuticsinc.gcs-web.com/webcasts-and-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://axsometherapeuticsinc.gcs-web.com/press-releases", "platform": "q4", "content_type": "text"},
            # Publications are on axsome.com — requires JS to expand drug sections
            {"type": "publications", "url": "https://www.axsome.com/science/publications/", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "VRTX": {
        "name": "Vertex Pharmaceuticals",
        "category": "rare_disease",
        "pages": [
            {"type": "events", "url": "https://investors.vrtx.com/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.vrtx.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.vrtxmedical.com/us/publications", "platform": "custom", "content_type": "documents"},
        ],
    },
    "BIIB": {
        "name": "Biogen",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://investors.biogen.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.biogen.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "ALNY": {
        "name": "Alnylam Pharmaceuticals",
        "category": "rna_therapeutics",
        "pages": [
            {"type": "events", "url": "https://www.alnylam.com/investors/events-and-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://www.alnylam.com/investors/press-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "IONS": {
        "name": "Ionis Pharmaceuticals",
        "category": "rna_therapeutics",
        "pages": [
            {"type": "events", "url": "https://ir.ionis.com/events", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.ionispharma.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },

    # =========================================================================
    # BIG PHARMA (competitive landscape)
    # =========================================================================

    "PFE": {
        "name": "Pfizer",
        "category": "big_pharma",
        "pages": [
            # Pfizer restructured IR site — new path is /news-events/default.aspx
            {"type": "events", "url": "https://investors.pfizer.com/Investors/news-events/default.aspx", "platform": "notified", "content_type": "documents"},
            {"type": "press", "url": "https://investors.pfizer.com/press-releases", "platform": "q4", "content_type": "text"},
            # No dedicated publications page — media resources has scientific/clinical content
            {"type": "publications", "url": "https://www.pfizer.com/news/media-resources", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "MRK": {
        "name": "Merck",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.merck.com/investor-relations/events-and-presentations/", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.merck.com/news/", "platform": "custom", "content_type": "text"},
        ],
    },
    "AZN": {
        "name": "AstraZeneca",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.astrazeneca.com/investor-relations/presentations-and-webinars.html", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.astrazeneca.com/media-centre/press-releases.html", "platform": "custom", "content_type": "text"},
        ],
    },
    "GILD": {
        "name": "Gilead Sciences",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://investors.gilead.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.gilead.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.gilead.com/science/research/research-publications", "platform": "custom", "content_type": "documents"},
            {"type": "publications", "url": "https://www.askgileadmedical.com/publications/", "platform": "custom", "content_type": "documents"},
        ],
    },
    "LLY": {
        "name": "Eli Lilly",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://investor.lilly.com/webcasts-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.lilly.com/press-releases", "platform": "q4", "content_type": "text"},
            # medical.lilly.com has per-TA publication pages (no dropdown clicking needed)
            {"type": "publications", "url": "https://medical.lilly.com/us/science/publications/oncology", "platform": "js_rendered", "content_type": "documents"},
            {"type": "publications", "url": "https://medical.lilly.com/us/science/publications/diabetes", "platform": "js_rendered", "content_type": "documents"},
            {"type": "publications", "url": "https://medical.lilly.com/us/science/publications/immunology", "platform": "js_rendered", "content_type": "documents"},
            {"type": "publications", "url": "https://medical.lilly.com/us/science/publications/neuroscience", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "BMY": {
        "name": "Bristol-Myers Squibb",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.bms.com/investors/events-and-presentations.html", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.bms.com/media/press-releases.html", "platform": "custom", "content_type": "text"},
        ],
    },
    "ABBV": {
        "name": "AbbVie",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://investors.abbvie.com/events-and-presentations/upcoming-events", "platform": "js_rendered", "content_type": "documents"},
            {"type": "events", "url": "https://investors.abbvie.com/presentations", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://investors.abbvie.com/press-releases", "platform": "q4", "content_type": "text"},
            {"type": "publications", "url": "https://www.abbvie.com/science/publications.html", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "AMGN": {
        "name": "Amgen",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://investors.amgen.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.amgen.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "REGN": {
        "name": "Regeneron",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://investor.regeneron.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.regeneron.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "TAK": {
        "name": "Takeda",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.takeda.com/investors/events/", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.takeda.com/newsroom/", "platform": "custom", "content_type": "text"},
        ],
    },
    "JNJ": {
        "name": "Johnson & Johnson",
        "category": "big_pharma",
        "pages": [
            # default.aspx is a Notified/Q4 events page — use js_rendered for Playwright fallback
            {"type": "events", "url": "https://www.investor.jnj.com/events-and-presentations/default.aspx", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://www.investor.jnj.com/press-releases", "platform": "custom", "content_type": "text"},
            # Janssen (JNJ's pharma arm) publications
            {"type": "publications", "url": "https://www.janssen.com/scientific-publications", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "RHHBY": {
        "name": "Roche / Genentech",
        "category": "big_pharma",
        "pages": [
            # Roche /investors/downloads and /events return 0 — heavy JS site, try updates page
            {"type": "events", "url": "https://www.roche.com/investors/updates", "platform": "js_rendered", "content_type": "documents"},
            {"type": "events", "url": "https://www.roche.com/investors/downloads", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://www.roche.com/media/releases", "platform": "custom", "content_type": "text"},
            {"type": "publications", "url": "https://medically.roche.com/global/en/publication.html", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "NVS": {
        "name": "Novartis",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.novartis.com/investors/event-calendar", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.novartis.com/news/media-releases", "platform": "custom", "content_type": "text"},
            # OAK is EPrints 3 — use /cgi/latest_tool for recent pubs, /view/ to browse
            {"type": "publications", "url": "https://oak.novartis.com/cgi/latest_tool", "platform": "eprints", "content_type": "documents"},
        ],
    },
    "SNY": {
        "name": "Sanofi",
        "category": "big_pharma",
        "pages": [
            # Sanofi investor presentations — try js_rendered for heavy JS site
            {"type": "events", "url": "https://www.sanofi.com/en/investors/financial-results-and-events/investor-presentations", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://www.sanofi.com/en/media-room/press-releases", "platform": "custom", "content_type": "text"},
            # Research publications page
            {"type": "publications", "url": "https://www.sanofi.com/en/our-science/research-publications", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "GSK": {
        "name": "GSK",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.gsk.com/en-gb/investors/events-and-presentations/", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.gsk.com/en-gb/media/press-releases/", "platform": "custom", "content_type": "text"},
        ],
    },
    "NVO": {
        "name": "Novo Nordisk",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.novonordisk.com/investors/financial-results.html", "platform": "js_rendered", "content_type": "documents"},
            {"type": "events", "url": "https://www.novonordisk.com/investors/financial-calendar.html", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://www.novonordisk.com/news-and-media.html", "platform": "custom", "content_type": "text"},
            {"type": "publications", "url": "https://sciencehub.novonordisk.com/", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "DSNKY": {
        "name": "Daiichi Sankyo",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.daiichisankyo.com/investors/library/materials/", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.daiichisankyo.com/media/press-releases/", "platform": "custom", "content_type": "text"},
            {"type": "publications", "url": "https://datasourcebydaiichisankyo.com/publications", "platform": "js_rendered", "content_type": "documents"},
            {"type": "publications", "url": "https://datasourcebydaiichisankyo.com/congresses", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "ESALY": {
        "name": "Eisai",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://www.eisai.com/ir/event/index.html", "platform": "custom", "content_type": "documents"},
            {"type": "press", "url": "https://www.eisai.com/news/index.html", "platform": "custom", "content_type": "text"},
        ],
    },
    "BILH": {
        "name": "Boehringer Ingelheim",
        "category": "big_pharma",
        "pages": [
            {"type": "press", "url": "https://www.boehringer-ingelheim.com/press", "platform": "custom", "content_type": "text"},
            # Private company — no IR events page; try US medical congress library
            {"type": "publications", "url": "https://medinfo.boehringer-ingelheim.com/us/scientific-congresses/congress-library", "platform": "js_rendered", "content_type": "documents"},
            # Also try scientific publications page
            {"type": "publications", "url": "https://www.boehringer-ingelheim.com/scientific-publication", "platform": "js_rendered", "content_type": "documents"},
        ],
    },
    "AGTSY": {
        "name": "Astellas Pharma",
        "category": "big_pharma",
        "pages": [
            {"type": "events", "url": "https://www.astellas.com/en/investors/ir-library", "platform": "js_rendered", "content_type": "documents"},
            {"type": "events", "url": "https://www.astellas.com/en/investors/financial-results-library", "platform": "js_rendered", "content_type": "documents"},
            {"type": "press", "url": "https://www.astellas.com/en/news", "platform": "custom", "content_type": "text"},
        ],
    },


    # =========================================================================
    # EXPANSION — Neuro/Sleep, Immunology, Rare Disease, Oncology (added 2026-03-25)
    # =========================================================================

    "HRMY": {
        "name": "Harmony Biosciences",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://ir.harmonybiosciences.com/news-events/presentations/", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.harmonybiosciences.com/news-events/news-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "JAZZ": {
        "name": "Jazz Pharmaceuticals",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://investor.jazzpharma.com/investors/events-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://investor.jazzpharma.com/news/press-release-archive", "platform": "standard", "content_type": "text"},
        ],
    },
    "ACAD": {
        "name": "Acadia Pharmaceuticals",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://ir.acadia-pharm.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.acadia-pharm.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "ITCI": {
        "name": "Intra-Cellular Therapies",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://ir.intracellulartherapies.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.intracellulartherapies.com/news-releases/", "platform": "standard", "content_type": "text"},
        ],
    },
    "XENE": {
        "name": "Xenon Pharmaceuticals",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://investor.xenon-pharma.com/news-events/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.xenon-pharma.com/news-events/press-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "PRAX": {
        "name": "Praxis Precision Medicine",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://ir.praxismedicines.com/events-and-presentations/", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.praxismedicines.com/press-releases/", "platform": "standard", "content_type": "text"},
        ],
    },
    "SUPN": {
        "name": "Supernus Pharmaceuticals",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://ir.supernus.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.supernus.com/press-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "INCY": {
        "name": "Incyte",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://investor.incyte.com/events-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investor.incyte.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "ARVN": {
        "name": "Arvinas",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.arvinas.com/events-and-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.arvinas.com/press-releases/", "platform": "standard", "content_type": "text"},
        ],
    },
    "SNDX": {
        "name": "Syndax Pharmaceuticals",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.syndax.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.syndax.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "BPMC": {
        "name": "Blueprint Medicines",
        "category": "oncology",
        "pages": [
            {"type": "events", "url": "https://ir.blueprintmedicines.com/events-and-presentations/events-presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.blueprintmedicines.com/press-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "BMRN": {
        "name": "BioMarin Pharmaceutical",
        "category": "rare_disease",
        "pages": [
            {"type": "events", "url": "https://investors.biomarin.com/events-and-presentations/default.aspx", "platform": "notified", "content_type": "documents"},
            {"type": "press", "url": "https://investors.biomarin.com/news/default.aspx", "platform": "notified", "content_type": "text"},
        ],
    },
    "RARE": {
        "name": "Ultragenyx Pharmaceutical",
        "category": "rare_disease",
        "pages": [
            {"type": "events", "url": "https://ir.ultragenyx.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.ultragenyx.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "AUPH": {
        "name": "Aurinia Pharmaceuticals",
        "category": "immunology",
        "pages": [
            {"type": "events", "url": "https://www.auriniapharma.com/investors-and-media/news-events", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://www.auriniapharma.com/news", "platform": "standard", "content_type": "text"},
        ],
    },
    "NMRA": {
        "name": "Neumora Therapeutics",
        "category": "neuroscience",
        "pages": [
            {"type": "events", "url": "https://ir.neumoratx.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.neumoratx.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "IDIA": {
        "name": "Idorsia",
        "category": "neuroscience",
        "pages": [
            # Swiss company — daridorexant (Quviviq) maker
            {"type": "press", "url": "https://www.idorsia.com/investors/news-and-events/media-releases", "platform": "custom", "content_type": "text"},
        ],
    },

    # =========================================================================
    # DEMO PRIORITY — added 2026-04-06
    # =========================================================================

    "UTHR": {
        "name": "United Therapeutics",
        "category": "pulmonary",
        "pages": [
            {"type": "events", "url": "https://ir.unither.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://ir.unither.com/press-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "ASND": {
        "name": "Ascendis Pharma",
        "category": "endocrinology",
        "pages": [
            {"type": "events", "url": "https://investors.ascendispharma.com/events-and-presentations", "platform": "q4", "content_type": "documents"},
            {"type": "press", "url": "https://investors.ascendispharma.com/news-releases", "platform": "q4", "content_type": "text"},
        ],
    },
    "DFTX": {
        "name": "Definium Therapeutics",
        "category": "psychiatry",
        "pages": [
            # Formerly MindMed — rebranded Jan 2026, ticker changed from MNMD to DFTX
            {"type": "events", "url": "https://ir.definiumtx.com/news-events/presentations", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.definiumtx.com/news-events/press-releases", "platform": "standard", "content_type": "text"},
        ],
    },
    "LXEO": {
        "name": "Lexeo Therapeutics",
        "category": "gene_therapy",
        "pages": [
            {"type": "events", "url": "https://ir.lexeotx.com/news-events/presentations", "platform": "standard", "content_type": "documents"},
            {"type": "events", "url": "https://ir.lexeotx.com/news-events/events", "platform": "standard", "content_type": "documents"},
            {"type": "press", "url": "https://ir.lexeotx.com/news-events/news-releases", "platform": "standard", "content_type": "text"},
        ],
    },
}


def get_oncology_config(ticker: str) -> dict | None:
    """Get the IR config for a ticker, or None if not found."""
    return ONCOLOGY_COMPANIES.get(ticker.upper())


def get_all_oncology_tickers() -> list[str]:
    """Get all ticker symbols."""
    return list(ONCOLOGY_COMPANIES.keys())


def get_tickers_by_category(category: str) -> list[str]:
    """Get tickers filtered by category (oncology, big_pharma, neuroscience, etc.)."""
    return [t for t, c in ONCOLOGY_COMPANIES.items() if c.get("category") == category]
