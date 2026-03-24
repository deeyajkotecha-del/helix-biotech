"""
SatyaBio Company Universe — 60 biotech & pharma companies

Imported from satya-pipeline/configs/oncology_config.py
Contains IR page URLs, publication pages, and platform metadata
for the document scraper.

Categories: oncology, big_pharma, neuroscience, metabolic, rare_disease,
immunology, infectious_disease, rna_therapeutics, endocrinology, diagnostics,
dermatology, multi
"""

COMPANY_UNIVERSE = {
    "NUVL": {
        "name": "Nuvalent",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.nuvalent.com/events",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.nuvalent.com/news",
                "platform": "standard",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.nuvalent.com/publications",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "CELC": {
        "name": "Celcuity",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.celcuity.com/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.celcuity.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.celcuity.com/science/publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "PYXS": {
        "name": "Pyxis Oncology",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.pyxisoncology.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.pyxisoncology.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://pyxisoncology.com/clinical-programs/scientific-publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "RVMD": {
        "name": "Revolution Medicines",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.revmed.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.revmed.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.revmed.com/publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "RLAY": {
        "name": "Relay Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.relaytx.com/news-events/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.relaytx.com/news-events/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://relaytx.com/publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "IOVA": {
        "name": "Iovance Biotherapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.iovance.com/news-events/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.iovance.com/news-events/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.iovance.com/scientific-publications-presentations/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "VIR": {
        "name": "Vir Biotechnology",
        "category": "infectious_disease",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.vir.bio/events-and-presentations/default.aspx",
                "platform": "notified",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.vir.bio/press-releases/default.aspx",
                "platform": "notified",
                "content_type": "text"
            }
        ],
        "direct_links": []
    },
    "JANX": {
        "name": "Janux Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.januxrx.com/investor-media/events-and-presentations/default.aspx",
                "platform": "notified",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.januxrx.com/investor-media/news/default.aspx",
                "platform": "notified",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.januxrx.com/publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ],
        "direct_links": []
    },
    "CGON": {
        "name": "CG Oncology",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.cgoncology.com/news-events/events-conferences",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.cgoncology.com/news-events/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://cgoncology.com/abstracts-and-presentations/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "URGN": {
        "name": "UroGen Pharma",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.urogen.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.urogen.com/news-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "VSTM": {
        "name": "Verastem Oncology",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.verastem.com/events",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.verastem.com/news-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.verastem.com/research/resources/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "IBRX": {
        "name": "ImmunityBio",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.immunitybio.com/company/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.immunitybio.com/company/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://immunitybio.com/research/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "TNGX": {
        "name": "Tango Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.tangotx.com/news-events/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.tangotx.com/news-events/news-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.tangotx.com/science/publications-posters/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "CNTA": {
        "name": "Centessa Pharmaceuticals",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.centessa.com/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.centessa.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "BCYC": {
        "name": "Bicycle Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.bicycletherapeutics.com/events-and-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.bicycletherapeutics.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.bicycletherapeutics.com/media/science-publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "ARGX": {
        "name": "argenx",
        "category": "immunology",
        "pages": [
            {
                "type": "events",
                "url": "https://www.argenx.com/investors/events-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.argenx.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://argenxmedical.com/en-us/congress-materials.html",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://argenxmedical.com/en-us/congress-materials/neurology.html",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://argenxmedical.com/en-us/congress-materials/hematology.html",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "KYMR": {
        "name": "Kymera Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.kymeratx.com/news-events/presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.kymeratx.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.kymeratx.com/science-innovation/resource-library/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "ALKS": {
        "name": "Alkermes",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.alkermes.com/investor-events-presentations/",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.alkermes.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "VKTX": {
        "name": "Viking Therapeutics",
        "category": "metabolic",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.vikingtherapeutics.com/",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.vikingtherapeutics.com/press-releases",
                "platform": "standard",
                "content_type": "text"
            }
        ]
    },
    "GPCR": {
        "name": "Structure Therapeutics",
        "category": "metabolic",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.structuretx.com/events-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.structuretx.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.structuretx.com/publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "ORKA": {
        "name": "Oruka Therapeutics",
        "category": "dermatology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.orukatx.com/news-events/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.oruka.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "MRNA": {
        "name": "Moderna",
        "category": "infectious_disease",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.modernatx.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.modernatx.com/news/news-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "ROIV": {
        "name": "Roivant Sciences",
        "category": "multi",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.roivant.com/news-events/events",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "PCVX": {
        "name": "Vaxcyte",
        "category": "infectious_disease",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.vaxcyte.com/events-and-presentations/",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.vaxcyte.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "SRPT": {
        "name": "Sarepta Therapeutics",
        "category": "rare_disease",
        "pages": [
            {
                "type": "events",
                "url": "https://investorrelations.sarepta.com/events-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investorrelations.sarepta.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.sarepta.com/science",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "SMMT": {
        "name": "Summit Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://smmttx.com/investor-information/summit-presentations/",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.summittx.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://smmttx.com/publications/",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "INSM": {
        "name": "Insmed",
        "category": "rare_disease",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.insmed.com/events",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.insmed.com/news-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "EXAS": {
        "name": "Exact Sciences (acquired by Abbott)",
        "category": "diagnostics",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.exactsciences.com/events-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.exactsciences.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "NBIX": {
        "name": "Neurocrine Biosciences",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://neurocrine.com/investors/webcasts-presentations/",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.neurocrine.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "CRNX": {
        "name": "Crinetics Pharmaceuticals",
        "category": "endocrinology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.crinetics.com/events-and-presentations/default.aspx",
                "platform": "notified",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.crinetics.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "DAWN": {
        "name": "Day One Biopharmaceuticals",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.dayonebio.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.dayonebio.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "RCUS": {
        "name": "Arcus Biosciences",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.arcusbio.com/events-and-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.arcusbio.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://arcusbio.com/our-science/publications/",
                "platform": "standard",
                "content_type": "documents"
            }
        ]
    },
    "MDGL": {
        "name": "Madrigal Pharmaceuticals",
        "category": "metabolic",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.madrigalpharma.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.madrigalpharma.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "MRTI": {
        "name": "Mirati Therapeutics",
        "category": "oncology",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.mirati.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.mirati.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "SAGE": {
        "name": "Sage Therapeutics",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.sagerx.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.sagerx.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "AXSM": {
        "name": "Axsome Therapeutics",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://axsometherapeuticsinc.gcs-web.com/webcasts-and-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://axsometherapeuticsinc.gcs-web.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.axsome.com/science/publications/",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "VRTX": {
        "name": "Vertex Pharmaceuticals",
        "category": "rare_disease",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.vrtx.com/events-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.vrtx.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.vrtxmedical.com/us/publications",
                "platform": "custom",
                "content_type": "documents"
            }
        ]
    },
    "BIIB": {
        "name": "Biogen",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.biogen.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.biogen.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "ALNY": {
        "name": "Alnylam Pharmaceuticals",
        "category": "rna_therapeutics",
        "pages": [
            {
                "type": "events",
                "url": "https://www.alnylam.com/investors/events-and-presentations",
                "platform": "standard",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.alnylam.com/investors/press-releases",
                "platform": "standard",
                "content_type": "text"
            }
        ]
    },
    "IONS": {
        "name": "Ionis Pharmaceuticals",
        "category": "rna_therapeutics",
        "pages": [
            {
                "type": "events",
                "url": "https://ir.ionis.com/events",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://ir.ionispharma.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "PFE": {
        "name": "Pfizer",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.pfizer.com/Investors/news-events/default.aspx",
                "platform": "notified",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.pfizer.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.pfizer.com/news/media-resources",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "MRK": {
        "name": "Merck",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.merck.com/investor-relations/events-and-presentations/",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.merck.com/news/",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    },
    "AZN": {
        "name": "AstraZeneca",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.astrazeneca.com/investor-relations/presentations-and-webinars.html",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.astrazeneca.com/media-centre/press-releases.html",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    },
    "GILD": {
        "name": "Gilead Sciences",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.gilead.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.gilead.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.gilead.com/science/research/research-publications",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://www.askgileadmedical.com/publications/",
                "platform": "custom",
                "content_type": "documents"
            }
        ]
    },
    "LLY": {
        "name": "Eli Lilly",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.lilly.com/webcasts-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.lilly.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://medical.lilly.com/us/science/publications/oncology",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://medical.lilly.com/us/science/publications/diabetes",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://medical.lilly.com/us/science/publications/immunology",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://medical.lilly.com/us/science/publications/neuroscience",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "BMY": {
        "name": "Bristol-Myers Squibb",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.bms.com/investors/events-and-presentations.html",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.bms.com/media/press-releases.html",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    },
    "ABBV": {
        "name": "AbbVie",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.abbvie.com/events-and-presentations/upcoming-events",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "events",
                "url": "https://investors.abbvie.com/presentations",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.abbvie.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.abbvie.com/science/publications.html",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "AMGN": {
        "name": "Amgen",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://investors.amgen.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investors.amgen.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "REGN": {
        "name": "Regeneron",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://investor.regeneron.com/events-and-presentations",
                "platform": "q4",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://investor.regeneron.com/press-releases",
                "platform": "q4",
                "content_type": "text"
            }
        ]
    },
    "TAK": {
        "name": "Takeda",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.takeda.com/investors/events/",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.takeda.com/newsroom/",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    },
    "JNJ": {
        "name": "Johnson & Johnson",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.investor.jnj.com/events-and-presentations/default.aspx",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.investor.jnj.com/press-releases",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.janssen.com/scientific-publications",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "RHHBY": {
        "name": "Roche / Genentech",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.roche.com/investors/updates",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "events",
                "url": "https://www.roche.com/investors/downloads",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.roche.com/media/releases",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://medically.roche.com/global/en/publication.html",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "NVS": {
        "name": "Novartis",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.novartis.com/investors/event-calendar",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.novartis.com/news/media-releases",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://oak.novartis.com/cgi/latest_tool",
                "platform": "eprints",
                "content_type": "documents"
            }
        ]
    },
    "SNY": {
        "name": "Sanofi",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.sanofi.com/en/investors/financial-results-and-events/investor-presentations",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.sanofi.com/en/media-room/press-releases",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://www.sanofi.com/en/our-science/research-publications",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "GSK": {
        "name": "GSK",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.gsk.com/en-gb/investors/events-and-presentations/",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.gsk.com/en-gb/media/press-releases/",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    },
    "NVO": {
        "name": "Novo Nordisk",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.novonordisk.com/investors/financial-results.html",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "events",
                "url": "https://www.novonordisk.com/investors/financial-calendar.html",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.novonordisk.com/news-and-media.html",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://sciencehub.novonordisk.com/",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "DSNKY": {
        "name": "Daiichi Sankyo",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.daiichisankyo.com/investors/library/materials/",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.daiichisankyo.com/media/press-releases/",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://datasourcebydaiichisankyo.com/publications",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://datasourcebydaiichisankyo.com/congresses",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "ESALY": {
        "name": "Eisai",
        "category": "neuroscience",
        "pages": [
            {
                "type": "events",
                "url": "https://www.eisai.com/ir/event/index.html",
                "platform": "custom",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.eisai.com/news/index.html",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    },
    "BILH": {
        "name": "Boehringer Ingelheim",
        "category": "big_pharma",
        "pages": [
            {
                "type": "press",
                "url": "https://www.boehringer-ingelheim.com/press",
                "platform": "custom",
                "content_type": "text"
            },
            {
                "type": "publications",
                "url": "https://medinfo.boehringer-ingelheim.com/us/scientific-congresses/congress-library",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "publications",
                "url": "https://www.boehringer-ingelheim.com/scientific-publication",
                "platform": "js_rendered",
                "content_type": "documents"
            }
        ]
    },
    "AGTSY": {
        "name": "Astellas Pharma",
        "category": "big_pharma",
        "pages": [
            {
                "type": "events",
                "url": "https://www.astellas.com/en/investors/ir-library",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "events",
                "url": "https://www.astellas.com/en/investors/financial-results-library",
                "platform": "js_rendered",
                "content_type": "documents"
            },
            {
                "type": "press",
                "url": "https://www.astellas.com/en/news",
                "platform": "custom",
                "content_type": "text"
            }
        ]
    }
}


# Category display names
CATEGORY_LABELS = {
    "big_pharma": "Big Pharma",
    "dermatology": "Dermatology",
    "diagnostics": "Diagnostics",
    "endocrinology": "Endocrinology",
    "immunology": "Immunology",
    "infectious_disease": "Infectious Disease",
    "metabolic": "Metabolic",
    "multi": "Multi",
    "neuroscience": "Neuroscience",
    "oncology": "Oncology",
    "rare_disease": "Rare Disease",
    "rna_therapeutics": "Rna Therapeutics",
}


def get_companies_by_category():
    """Return companies grouped by category."""
    grouped = {}
    for ticker, data in sorted(COMPANY_UNIVERSE.items()):
        cat = data["category"]
        if cat not in grouped:
            grouped[cat] = []
        doc_pages = [p for p in data["pages"] if p.get("content_type") == "documents"]
        grouped[cat].append({
            "ticker": ticker,
            "name": data["name"],
            "category": cat,
            "doc_page_count": len(doc_pages),
            "total_page_count": len(data["pages"]),
            "pages": data["pages"],
        })
    return grouped


def get_all_companies_flat():
    """Return flat list of all companies with metadata."""
    companies = []
    for ticker, data in sorted(COMPANY_UNIVERSE.items()):
        doc_pages = [p for p in data["pages"] if p.get("content_type") == "documents"]
        companies.append({
            "ticker": ticker,
            "name": data["name"],
            "category": data["category"],
            "category_label": CATEGORY_LABELS.get(data["category"], data["category"]),
            "doc_page_count": len(doc_pages),
            "total_page_count": len(data["pages"]),
            "ir_url": next((p["url"] for p in data["pages"] if p["type"] == "events"), None),
            "publications_url": next((p["url"] for p in data["pages"] if p["type"] == "publications"), None),
        })
    return companies
