"""TL1A / IBD competitive landscape data for landscape_template()."""

TL1A_DATA = {
    "meta": {
        "page_title": "TL1A / IBD Competitive Landscape | Satya Bio",
        "title": "TL1A / IBD Competitive Landscape",
        "label": "TARGET DEEP DIVE",
        "slug": "tl1a-ibd",
        "description": "Comprehensive analysis of 45+ programs targeting TL1A/TNFSF15 for inflammatory bowel disease. Three Phase 3 programs racing for first-to-market. $25B+ deal value. Updated February 12, 2026.",
        "stats": [
            {"label": "Programs", "value": "45+"},
            {"label": "Phase 3", "value": "3"},
            {"label": "Deal Value", "value": "$25B+"},
            {"label": "TAM (UC+CD)", "value": "$30B+"},
            {"label": "Peak Sales", "value": "$4-5B"},
        ],
    },
    "sections": [
        {"id": "pathway", "label": "Pathway"},
        {"id": "landscape", "label": "Landscape"},
        {"id": "thesis", "label": "Thesis"},
        {"id": "pipeline", "label": "Pipeline"},
        {"id": "efficacy", "label": "Efficacy"},
        {"id": "trials", "label": "Trials"},
        {"id": "patents", "label": "Patents"},
        {"id": "revenue", "label": "Revenue"},
        {"id": "catalysts", "label": "Catalysts"},
        {"id": "sources", "label": "Sources"},
    ],
    "pathway": {
        "heading": "Mechanism of Action: TL1A &#x2192; DR3 Pathway",
        "svg": '<svg viewBox="0 0 960 380" xmlns="http://www.w3.org/2000/svg" style="width:100%;font-family:Inter,sans-serif">'
            '<defs><marker id="ah" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="#8e99a9"/></marker></defs>'
            '<text x="30" y="25" font-size="9" fill="#8e99a9" letter-spacing="1" font-family="JetBrains Mono">LIGAND</text>'
            '<text x="230" y="25" font-size="9" fill="#8e99a9" letter-spacing="1" font-family="JetBrains Mono">RECEPTOR</text>'
            '<text x="430" y="25" font-size="9" fill="#8e99a9" letter-spacing="1" font-family="JetBrains Mono">DOWNSTREAM</text>'
            '<text x="740" y="25" font-size="9" fill="#8e99a9" letter-spacing="1" font-family="JetBrains Mono">DISEASE EFFECTS</text>'
            '<rect x="20" y="50" width="150" height="55" rx="10" fill="#1b2a4a"/><text x="95" y="76" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">TL1A</text><text x="95" y="93" text-anchor="middle" font-size="9" fill="rgba(255,255,255,.6)">TNFSF15</text>'
            '<rect x="220" y="50" width="130" height="55" rx="10" fill="#e07a5f"/><text x="285" y="76" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">DR3</text><text x="285" y="93" text-anchor="middle" font-size="9" fill="rgba(255,255,255,.6)">TNFRSF25</text>'
            '<line x1="170" y1="77" x2="220" y2="77" stroke="#1b2a4a" stroke-width="2" marker-end="url(#ah)"/>'
            '<line x1="183" y1="67" x2="200" y2="87" stroke="#e07a5f" stroke-width="3.5"/><line x1="200" y1="67" x2="183" y2="87" stroke="#e07a5f" stroke-width="3.5"/>'
            '<rect x="10" y="130" width="170" height="90" rx="8" fill="#fdf0eb" stroke="#e07a5f" stroke-dasharray="4,2"/>'
            '<text x="95" y="150" text-anchor="middle" font-size="10" font-weight="700" fill="#e07a5f">ANTI-TL1A mAbs</text>'
            '<text x="20" y="168" font-size="8.5" fill="#4a5568">&#x2022; Tulisokibart (Merck)</text>'
            '<text x="20" y="182" font-size="8.5" fill="#4a5568">&#x2022; Duvakitug (Sanofi/Teva)</text>'
            '<text x="20" y="196" font-size="8.5" fill="#4a5568">&#x2022; Afimkibart (Roche)</text>'
            '<text x="20" y="210" font-size="8.5" fill="#4a5568">&#x2022; XmAb942, SPY002...</text>'
            '<line x1="350" y1="77" x2="410" y2="59" stroke="#8e99a9" stroke-width="1.5" marker-end="url(#ah)"/>'
            '<rect x="410" y="42" width="170" height="34" rx="6" fill="#fff" stroke="#e5e0d8"/><text x="495" y="63" text-anchor="middle" font-size="10" font-weight="600" fill="#1b2a4a">Th1 / Th17 Activation</text>'
            '<line x1="350" y1="77" x2="410" y2="117" stroke="#8e99a9" stroke-width="1.5" marker-end="url(#ah)"/>'
            '<rect x="410" y="100" width="170" height="34" rx="6" fill="#fff" stroke="#e5e0d8"/><text x="495" y="121" text-anchor="middle" font-size="10" font-weight="600" fill="#1b2a4a">ILC2 Activation</text>'
            '<line x1="350" y1="77" x2="410" y2="175" stroke="#8e99a9" stroke-width="1.5" marker-end="url(#ah)"/>'
            '<rect x="410" y="158" width="170" height="34" rx="6" fill="#fff" stroke="#e5e0d8"/><text x="495" y="179" text-anchor="middle" font-size="10" font-weight="600" fill="#1b2a4a">Treg Suppression</text>'
            '<line x1="350" y1="77" x2="410" y2="235" stroke="#8e99a9" stroke-width="1.5" marker-end="url(#ah)"/>'
            '<rect x="410" y="218" width="170" height="34" rx="6" fill="#fff" stroke="#e5e0d8"/><text x="495" y="239" text-anchor="middle" font-size="10" font-weight="600" fill="#1b2a4a">Fibroblast Activation</text>'
            '<line x1="580" y1="59" x2="630" y2="59" stroke="#8e99a9" stroke-width="1" marker-end="url(#ah)"/>'
            '<rect x="630" y="42" width="80" height="34" rx="4" fill="#fef8ec" stroke="#c9963a"/><text x="670" y="63" text-anchor="middle" font-size="9" font-weight="600" fill="#c9963a">IFNg, IL-17</text>'
            '<line x1="580" y1="117" x2="630" y2="117" stroke="#8e99a9" stroke-width="1" marker-end="url(#ah)"/>'
            '<rect x="630" y="100" width="80" height="34" rx="4" fill="#fef8ec" stroke="#c9963a"/><text x="670" y="121" text-anchor="middle" font-size="9" font-weight="600" fill="#c9963a">IL-13, IL-5</text>'
            '<line x1="580" y1="175" x2="630" y2="175" stroke="#8e99a9" stroke-width="1" marker-end="url(#ah)"/>'
            '<rect x="630" y="158" width="80" height="34" rx="4" fill="#fef8ec" stroke="#c9963a"/><text x="670" y="179" text-anchor="middle" font-size="9" font-weight="600" fill="#c9963a">FoxP3 down</text>'
            '<line x1="580" y1="235" x2="630" y2="235" stroke="#8e99a9" stroke-width="1" marker-end="url(#ah)"/>'
            '<rect x="630" y="218" width="80" height="34" rx="4" fill="#fef8ec" stroke="#c9963a"/><text x="670" y="239" text-anchor="middle" font-size="9" font-weight="600" fill="#c9963a">TGF-B</text>'
            '<rect x="740" y="42" width="200" height="50" rx="8" fill="#fdf0f0" stroke="#b93b3b" stroke-width="1"/><text x="840" y="63" text-anchor="middle" font-size="11" font-weight="700" fill="#b93b3b">Intestinal Inflammation</text><text x="840" y="80" text-anchor="middle" font-size="8.5" fill="#4a5568">Mucosal damage, ulceration</text>'
            '<rect x="740" y="110" width="200" height="50" rx="8" fill="#fdf0f0" stroke="#b93b3b" stroke-width="1"/><text x="840" y="131" text-anchor="middle" font-size="11" font-weight="700" fill="#b93b3b">Immune Dysregulation</text><text x="840" y="148" text-anchor="middle" font-size="8.5" fill="#4a5568">Loss of tolerance, relapse</text>'
            '<rect x="740" y="180" width="200" height="50" rx="8" fill="#fdf0eb" stroke="#e07a5f" stroke-width="2"/><text x="840" y="201" text-anchor="middle" font-size="11" font-weight="700" fill="#e07a5f">Intestinal Fibrosis</text><text x="840" y="218" text-anchor="middle" font-size="8.5" fill="#4a5568">Strictures, surgery</text>'
            '<line x1="710" y1="59" x2="740" y2="67" stroke="#b93b3b" stroke-width="1.5"/>'
            '<line x1="710" y1="127" x2="740" y2="135" stroke="#b93b3b" stroke-width="1.5"/>'
            '<line x1="710" y1="193" x2="740" y2="201" stroke="#b93b3b" stroke-width="1.5"/>'
            '<rect x="20" y="285" width="920" height="60" rx="8" fill="#edf7f2" stroke="#2b7a5a"/>'
            '<text x="40" y="308" font-size="10" font-weight="700" fill="#2b7a5a" font-family="JetBrains Mono">KEY DIFFERENTIATOR</text>'
            '<text x="40" y="328" font-size="11" fill="#1b2a4a">TL1A uniquely drives BOTH inflammation AND fibrosis. Anti-TNF, IL-23i, JAKi only address inflammation. Anti-TL1A may alter disease progression.</text>'
            '</svg>',
    },
    "scatter_categories": ["Anti-TL1A mAb", "Bispecific", "Anti-DR3", "Oral"],
    "pipeline": [
        {"d": "Tulisokibart", "co": "Merck", "ph": "Phase 3", "cat": "Anti-TL1A mAb", "eff": "ARTEMIS-UC: 26% vs 1% remission (Wk12); APOLLO-CD: 49% endo response", "dv": "$10.8B (Prometheus acq.)", "st": "Active", "v": 10800, "tr": "ATLAS-UC, ARES-CD, SSc-ILD Ph2, HS/RA/axSpA Ph2b", "sr": "NCT06052059, NEJM 2024;391:1119"},
        {"d": "Duvakitug", "co": "Sanofi/Teva", "ph": "Phase 3", "cat": "Anti-TL1A mAb", "eff": "RELIEVE: UC 48% rem (900mg) vs 20% PBO; CD 48% endo resp vs 13%", "dv": "$1.5B + $500M milestone", "st": "Active", "v": 2000, "tr": "SUNSCAPE (UC), STARSCAPE (CD)", "sr": "Sanofi PR Feb 2025"},
        {"d": "Afimkibart", "co": "Roche", "ph": "Phase 3", "cat": "Anti-TL1A mAb", "eff": "TUSCANY-2: 30-35% remission; TUSCANY: 38% endo improvement", "dv": "$7.25B (Telavant acq.)", "st": "Active", "v": 7250, "tr": "AMETRINE-1/2 (UC), SIBERITE-2 (CD), AD Ph2, Peds UC", "sr": "Lancet GH 2025"},
        {"d": "XmAb942", "co": "Xencor", "ph": "Phase 2", "cat": "Anti-TL1A mAb", "eff": "Ph1 HV: +71d half-life, Q12W dosing, >99% TL1A suppression model", "dv": "Internal", "st": "Active", "v": 0, "tr": "XENITH-UC Ph2b (ongoing)", "sr": "Xencor Apr 2025"},
        {"d": "SPY002", "co": "Spyre", "ph": "Phase 2", "cat": "Anti-TL1A mAb", "eff": "Ph1: ~75d half-life, complete TL1A suppression 20wk+, Q3M-Q6M potential", "dv": "Internal ($526M cash)", "st": "Active", "v": 0, "tr": "SKYLINE-UC Ph2 platform", "sr": "Spyre Jun 2025"},
        {"d": "SPY072", "co": "Spyre", "ph": "Phase 2", "cat": "Anti-TL1A mAb", "eff": "Ph1: ~75d half-life, for rheumatic diseases (distinct from SPY002)", "dv": "Internal", "st": "Active", "v": 0, "tr": "SKYWAY-RD Ph2 (RA, PsA, axSpA)", "sr": "Spyre Jun 2025"},
        {"d": "ABS-101", "co": "Absci", "ph": "Phase 1", "cat": "Anti-TL1A mAb", "eff": "AI-designed candidate; first dosing 2025", "dv": "Internal", "st": "Active", "v": 0, "tr": "Ph1 HV", "sr": "Pharmaphorum Oct 2025"},
        {"d": "FG-M701", "co": "AbbVie/FutureGen", "ph": "Preclinical", "cat": "Anti-TL1A mAb", "eff": "Next-gen; STEP platform; claims best-in-class characteristics", "dv": "$150M + $1.56B milestones", "st": "Active", "v": 1710, "tr": "IND-enabling", "sr": "AbbVie PR Jun 2024"},
        {"d": "HXN-1002", "co": "Sanofi/Earendil", "ph": "Preclinical", "cat": "Bispecific", "eff": "a4b7 + TL1A bispecific; AI-designed", "dv": "Sanofi license (Apr 2025)", "st": "Active", "v": 0, "tr": "Preclinical", "sr": "Labiotech Aug 2025"},
        {"d": "HXN-1003", "co": "Sanofi/Earendil", "ph": "Preclinical", "cat": "Bispecific", "eff": "TL1A + IL-23 bispecific; dual pathway", "dv": "Sanofi license (Apr 2025)", "st": "Active", "v": 0, "tr": "Preclinical", "sr": "Labiotech Aug 2025"},
        {"d": "XmAb TL1AxIL23", "co": "Xencor", "ph": "Preclinical", "cat": "Bispecific", "eff": "TL1A + IL-23p19; matches monospecific potency", "dv": "Internal", "st": "Active", "v": 0, "tr": "FIH planned 2026", "sr": "Xencor Jan 2026"},
        {"d": "SPY120", "co": "Spyre", "ph": "Phase 2", "cat": "Bispecific", "eff": "a4b7 + TL1A combo; superior to mono in mouse colitis", "dv": "Internal", "st": "Active", "v": 0, "tr": "SKYLINE-UC Part B", "sr": "Spyre 2025"},
        {"d": "SPY230", "co": "Spyre", "ph": "Phase 2", "cat": "Bispecific", "eff": "TL1A + IL-23 combo", "dv": "Internal", "st": "Active", "v": 0, "tr": "SKYLINE-UC Part B", "sr": "Spyre 2025"},
        {"d": "BI 706321", "co": "Boehringer", "ph": "Phase 1", "cat": "Anti-DR3", "eff": "Anti-DR3 approach (blocks receptor not ligand)", "dv": "Internal (~1B EUR)", "st": "Active", "v": 1050, "tr": "Ph1", "sr": "BI pipeline"},
        {"d": "HRS-7085", "co": "Jiangsu Hansoh", "ph": "Phase 2", "cat": "Oral", "eff": "Oral TL1A inhibitor tablet", "dv": "Internal (China)", "st": "Active", "v": 0, "tr": "Ph2 IBD", "sr": "ClinicalTrials.gov"},
        {"d": "SHR-1139", "co": "Shandong Suncadia", "ph": "Phase 2", "cat": "Oral", "eff": "Oral small molecule TL1A inhibitor", "dv": "Internal (China)", "st": "Active", "v": 0, "tr": "Ph2 UC", "sr": "ClinicalTrials.gov"},
    ],
    "thesis": {
        "bull": [
            "First new biologic MOA for IBD in 5+ years; validated by 3 independent Ph2 successes",
            "Dual anti-inflammatory + anti-fibrotic \u2014 may alter CD disease progression (no other drug does this)",
            "Peak sales $4-5B tulisokibart alone; class could reach $15-20B across indications by 2034",
            "Expanding beyond IBD: SSc-ILD, atopic dermatitis, HS, RA, axSpA \u2014 massive optionality",
            "Genetic biomarker CDx (Merck) enables precision medicine \u2014 higher response rates",
            "Favorable safety across all Ph2 programs; potential for combos with IL-23i / integrin",
            "Next-gen (SPY002, XmAb942) offer Q12W-Q6M dosing \u2014 best-in-class convenience",
        ],
        "bear": [
            "Crowded: 45+ programs, 3 Ph3 \u2014 pricing erosion as competitors launch within ~2 years",
            "No Phase 3 data yet; ATLAS-UC Nov 2026 \u2014 high binary risk ahead",
            "Cross-trial comparisons unreliable: different populations, endpoints, placebo rates",
            "Fibrosis benefit unproven in humans \u2014 preclinical promise may not translate",
            "Existing SOC strong: Skyrizi ($12B+), Rinvoq ($8B+), Entyvio ($5B+) entrenched",
            "Biosimilar Humira flood \u2014 payer pressure on all branded IBD biologics",
            "Long-term safety unknown; DcR3 biology complex \u2014 potential off-target effects",
        ],
    },
    "efficacy": {
        "bars_label": "UC CLINICAL REMISSION AT WEEK 12-14 (INDUCTION)",
        "bars": [
            {"n": "Duvakitug 900mg", "v": 48, "c": "var(--coral)"},
            {"n": "Duvakitug 450mg", "v": 36, "c": "var(--coral)"},
            {"n": "Afimkibart 150mg", "v": 35, "c": "#2b5ea7"},
            {"n": "Afimkibart 450mg", "v": 32, "c": "#2b5ea7"},
            {"n": "Tulisokibart", "v": 26, "c": "var(--navy)"},
            {"n": "Skyrizi (IL-23i)", "v": 26, "c": "var(--muted)"},
            {"n": "Rinvoq 45mg", "v": 26, "c": "var(--muted)"},
            {"n": "Entyvio", "v": 17, "c": "var(--muted)"},
        ],
        "table_label": "VS ESTABLISHED IBD THERAPIES",
        "table": {
            "headers": ["Metric", "Anti-TL1A", "IL-23i", "JAKi", "Anti-TNF", "Integrin"],
            "rows": [
                ["UC Remission", "26-48%", "20-26%", "26-33%", "16-19%", "17-22%"],
                ["Anti-fibrotic", "Yes (preclinical)", "No", "No", "No", "No"],
                ["Safety", "Favorable", "Favorable", "Risk signals", "Immunosupp.", "Favorable"],
                ["Dosing (maint.)", "Q4W-Q12W", "Q8W", "Daily oral", "Q2W", "Q8W"],
                ["Biomarker CDx", "Yes (Merck)", "No", "No", "No", "No"],
            ],
        },
    },
    "trials": [
        {
            "sponsor_label": "MERCK",
            "name": "ATLAS-UC",
            "nct": "NCT06052059",
            "header_color": "var(--navy)",
            "rows": [
                ("Drug", "Tulisokibart"),
                ("N", "~720"),
                ("Arms", "4 (3 dose + PBO)"),
                ("Route", "IV induc. \u2192 SC maint"),
                ("Primary EP", "Clin. remission Wk12"),
                ("CDx", "Yes (genetic test)"),
                ("Results", "Nov 2026"),
                ("Filing", "2027"),
            ],
            "highlight_rows": ["Results"],
        },
        {
            "sponsor_label": "SANOFI / TEVA",
            "name": "SUNSCAPE",
            "nct": "Phase 3 UC",
            "header_color": "var(--coral)",
            "rows": [
                ("Drug", "Duvakitug"),
                ("N", "~800 est."),
                ("Route", "SC load \u2192 SC Q4W"),
                ("Primary EP", "Clin. remission Wk14"),
                ("Maint Data", "H1 2026 (58wk)"),
                ("Results", "2027-2028"),
                ("Filing", "2028+"),
            ],
            "highlight_rows": ["Maint Data", "Results"],
        },
        {
            "sponsor_label": "ROCHE",
            "name": "AMETRINE-1 & 2",
            "nct": "NCT06588855",
            "header_color": "#2b5ea7",
            "rows": [
                ("Drug", "Afimkibart"),
                ("N", "~500+ (2 studies)"),
                ("Route", "SC"),
                ("Primary EP", "Clin. remission (mMS)"),
                ("Also", "SIBERITE-2 (Ph3 CD)"),
                ("UC Filing", "2027"),
                ("CD Filing", "2028"),
            ],
            "highlight_rows": ["UC Filing"],
        },
    ],
    "patents": {
        "timeline": [
            {"n": "Tulisokibart", "s": 2019, "e": 2040, "c": "var(--navy)"},
            {"n": "Afimkibart", "s": 2016, "e": 2039, "c": "#2b5ea7"},
            {"n": "Duvakitug", "s": 2020, "e": 2041, "c": "var(--coral)"},
            {"n": "SPY002", "s": 2023, "e": 2044, "c": "var(--purp)"},
            {"n": "XmAb942", "s": 2023, "e": 2044, "c": "var(--warn)"},
            {"n": "FG-M701", "s": 2023, "e": 2045, "c": "var(--grn)"},
        ],
        "min_year": 2016,
        "max_year": 2046,
        "ip_notes": [
            {"drug": "Tulisokibart (Merck)", "text": "Prometheus CoM patents ~2019-2020. CDx biomarker patent extends commercial moat. Key: US10689439B2. Approved ~2028 \u2192 biosimilar ~2040."},
            {"drug": "Afimkibart (Roche)", "text": "Originally Pfizer (PF-06480605), CoM ~2016-2017 (earliest in class). Pfizer retains ex-US/Japan. Approved ~2028 \u2192 biosimilar ~2040."},
            {"drug": "Duvakitug (Sanofi/Teva)", "text": "Unique IgG1-\u03bb2, selective DR3 binding. CoM ~2020-2021. $500M Ph3 milestone paid Q4 2025."},
            {"drug": "Next-Gen (SPY002, XmAb942)", "text": "Half-life extension tech patents (Xencor Xtend, Spyre). ~75d t\u00bd vs ~20d gen-1. Engineering patents create barriers post-CoM expiry."},
        ],
    },
    "revenue": {
        "table": {
            "headers": ["Drug", "Sponsor", "Phase", "PoS", "Unadj Peak", "Risk-Adj Peak", "Launch"],
            "rows": [
                ["Tulisokibart", "Merck", "Phase 3", "55%", "$4-5B", "$2.2-2.8B", "H2 2028"],
                ["Duvakitug", "Sanofi/Teva", "Phase 3", "50%", "$3-4B", "$1.5-2.0B", "2029"],
                ["Afimkibart", "Roche", "Phase 3", "50%", "$2.5-3.5B", "$1.3-1.8B", "H2 2028"],
                ["XmAb942", "Xencor", "Phase 2", "25%", "$1.5-2.5B", "$0.4-0.6B", "2031+"],
                ["SPY002", "Spyre", "Phase 2", "25%", "$1-2B", "$0.3-0.5B", "2031+"],
                ["FG-M701", "AbbVie", "Preclinical", "10%", "$2-3B", "$0.2-0.3B", "2032+"],
            ],
            "total_row": ["Class Total", "\u2014", "\u2014", "$15-20B", "$6-8B", "2028-2032"],
        },
        "deal_scorecard": [
            {"label": "Merck \u2192 Prometheus (2023)", "value": "$10.8B"},
            {"label": "Roche \u2192 Telavant (2023)", "value": "$7.25B"},
            {"label": "AbbVie \u2192 FutureGen (2024)", "value": "$1.71B"},
            {"label": "Sanofi \u2192 Teva (2023)", "value": "$1.5B"},
            {"label": "Sanofi Ph3 milestone (Q4 2025)", "value": "$500M"},
        ],
        "deal_total": "Total: $25B+ cumulative deal value",
    },
    "deals": [
        {"n": "Merck to Prometheus", "v": 10800},
        {"n": "Roche to Telavant", "v": 7250},
        {"n": "Sanofi to Teva (+milest.)", "v": 2000},
        {"n": "AbbVie to FutureGen", "v": 1710},
        {"n": "Boehringer (internal)", "v": 1050},
        {"n": "Sanofi Ph3 milestone", "v": 500},
    ],
    "catalysts": {
        "label": "2026-2029",
        "items": [
            {"date": "H1 2026", "body": "<strong>Duvakitug 58-week maintenance data</strong> \u2014 Sanofi/Teva \u2014 long-term durability signal for Ph3 dose selection.", "critical": False},
            {"date": "Q2 2026", "body": "<strong>Spyre SKYLINE-UC Part A readouts begin</strong> \u2014 First monotherapy data for SPY001, SPY002, SPY003. Six POC readouts through year.", "critical": False},
            {"date": "H1 2026", "body": "<strong>XmAb942 Phase 1 final results</strong> \u2014 Xencor \u2014 full HV dataset for XENITH-UC Ph2b dose selection.", "critical": False},
            {"date": "NOV 2026", "body": "<strong>&#x26A1; ATLAS-UC Phase 3 Readout</strong> \u2014 Merck \u2014 FIRST PIVOTAL DATA for any anti-TL1A in UC. ~720 patients. Class-defining event.", "critical": True},
            {"date": "Q4 2026", "body": "<strong>SPY072 SKYWAY-RD readouts</strong> \u2014 Spyre \u2014 TL1A in RA, PsA, axSpA. If positive, massive TAM expansion beyond IBD.", "critical": False},
            {"date": "2027", "body": "<strong>AMETRINE-1/2 readouts + UC filing</strong> \u2014 Roche \u2014 Phase 3 UC data. Afimkibart regulatory filing targeted.", "critical": False},
            {"date": "2027", "body": "<strong>Tulisokibart Ph2b readouts</strong> \u2014 Merck \u2014 HS, RA, axSpA indication expansion data.", "critical": False},
            {"date": "2027-28", "body": "<strong>SUNSCAPE/STARSCAPE readouts</strong> \u2014 Sanofi/Teva \u2014 Phase 3 UC and CD data for duvakitug.", "critical": False},
            {"date": "2028", "body": "<strong>First anti-TL1A approval expected</strong> \u2014 Tulisokibart or afimkibart (UC). Race for first-to-market advantage.", "critical": False},
        ],
    },
    "sources": {
        "categories": [
            {
                "label": "Clinical Trials",
                "entries": [
                    {"text": 'Sands BE et al. ARTEMIS-UC. <em>NEJM</em> 2024;391:1119-29.', "url": "https://pubmed.ncbi.nlm.nih.gov/39321363/"},
                    {"text": 'TUSCANY-2 (Afimkibart Ph2b). <em>Lancet GH</em> 2025.', "url": "https://doi.org/10.1016/S2468-1253(25)00129-3"},
                    {"text": 'RELIEVE UCCD (Duvakitug Ph2b). Sanofi PR Feb 22, 2025.', "url": "https://www.sanofi.com/en/media-room/press-releases/2025/2025-02-22-07-30-00-3030764"},
                ],
            },
            {
                "label": "ClinicalTrials.gov",
                "entries": [
                    {"text": 'ATLAS-UC: NCT06052059 | ARES-CD: NCT06430801', "url": "https://clinicaltrials.gov/study/NCT06052059"},
                    {"text": 'AMETRINE-1: NCT06588855 | AMETRINE-2: NCT06589986', "url": "https://clinicaltrials.gov/study/NCT06588855"},
                    {"text": 'SKYLINE-UC: NCT07012395', "url": "https://clinicaltrials.gov/study/NCT07012395"},
                ],
            },
            {
                "label": "Corporate Disclosures",
                "entries": [
                    {"text": 'Merck tulisokibart expansion Oct 2025.', "url": "https://www.merck.com/news/merck-expands-tulisokibart-clinical-development-program-with-initiation-of-phase-2b-trials-in-three-additional-immune-mediated-inflammatory-diseases/"},
                    {"text": 'Teva Q4 2025 Earnings: Ph3 on time, maint data H1 2026, $500M milestone.', "url": None},
                    {"text": 'Spyre: 6 POC readouts 2026.', "url": "https://www.globenewswire.com/news-release/2026/01/12/3216806/0/en/"},
                    {"text": 'Xencor: XENITH-UC Ph2b, TL1AxIL23 FIH 2026.', "url": "https://investors.xencor.com/news-releases/news-release-details/xencor-highlights-corporate-priorities-and-2026-pipeline"},
                    {"text": 'AbbVie/FutureGen FG-M701 Jun 2024.', "url": "https://news.abbvie.com/2024-06-13-AbbVie-and-FutureGen-Announce-License-Agreement"},
                ],
            },
            {
                "label": "Patent",
                "entries": [
                    {"text": 'US10689439B2: Optimized anti-TL1A antibodies.', "url": "https://patents.google.com/patent/US10689439B2/en"},
                ],
            },
        ],
        "disclaimer": "Last verified: February 12, 2026. For informational purposes only \u2014 not investment advice.",
    },
}
