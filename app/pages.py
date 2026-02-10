"""
Static pages for SatyaBio - Companies, Targets, KOL Finder
Generated from cli/src/commands/serve.ts data
"""

from datetime import datetime
from pathlib import Path
import json

# Load companies from index.json
def load_companies_from_index():
    """Load companies from data/companies/index.json"""
    index_path = Path(__file__).parent.parent / "data" / "companies" / "index.json"
    if index_path.exists():
        with open(index_path) as f:
            data = json.load(f)
            return data.get("companies", [])
    return []

# Load targets from index.json
def load_targets_index():
    """Load targets from data/targets/index.json"""
    index_path = Path(__file__).parent.parent / "data" / "targets" / "index.json"
    if index_path.exists():
        with open(index_path) as f:
            data = json.load(f)
            return data.get("targets", []), data.get("categories", {})
    return [], {}

def load_target_data(slug: str):
    """Load individual target data from data/targets/{slug}.json"""
    target_path = Path(__file__).parent.parent / "data" / "targets" / f"{slug}.json"
    if target_path.exists():
        with open(target_path) as f:
            return json.load(f)
    return None

# Stage display labels
STAGE_LABELS = {
    "large_cap_diversified": "Large Cap",
    "commercial_stage": "Commercial",
    "late_clinical": "Late Clinical",
    "mid_clinical": "Mid Clinical",
    "early_clinical": "Early Clinical",
    "preclinical": "Preclinical",
}

# Modality display labels
MODALITY_LABELS = {
    "small_molecule": "Small Molecule",
    "antibody_biologics": "Antibody/Biologics",
    "rna_therapeutics": "RNA Therapeutics",
    "cell_gene_therapy": "Cell/Gene Therapy",
    "radiopharmaceutical": "Radiopharm",
    "platform_diversified": "Platform",
    "mixed": "Multi-modality",
}

# Categories (legacy - kept for reference)
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
                <a href="/extract/" {"class='active'" if active == "extract" else ""}>Extract</a>
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
        .company-card.acquired { opacity: 0.7; background: #f9fafb; }
        .company-card.acquired:hover { opacity: 0.85; }
        .acquired-badge { display: inline-block; padding: 3px 8px; background: #6b7280; color: white; font-size: 0.65rem; font-weight: 600; border-radius: 10px; text-transform: uppercase; margin-left: 8px; }
        .acquisition-details { font-size: 0.75rem; color: #6b7280; margin-top: 4px; font-style: italic; }

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

        /* Shared badge styles - consistent neutral gray for ALL phases */
        .phase-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: #e5e7eb; color: #374151; }
        .ticker-small { color: #6b7280; font-size: 0.8rem; }
        .deal-value { color: var(--navy); font-weight: 600; }
        .data-highlight { font-weight: 600; color: var(--navy); }
        .delta-positive { color: var(--navy); font-weight: 700; }
        .notes-text { font-size: 0.8rem; color: var(--text-secondary); }

        .footer { background: var(--navy); color: rgba(255,255,255,0.7); padding: 32px; text-align: center; margin-top: 64px; }
        .footer p { font-size: 0.85rem; }

        @media (max-width: 768px) {
            .nav-links { display: none; }
            .main { padding: 20px 16px; }
            .cards-grid { grid-template-columns: 1fr; }
        }
    </style>
    '''

def generate_company_card(company, locked=False):
    """Generate a company card - supports both legacy format and index.json format."""
    ticker = company.get("ticker", "")
    name = company.get("name", ticker)

    # Check for legacy format (has platform/description/tags)
    if company.get("platform"):
        # Legacy format with rich data
        tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in company.get("tags", [])[:3]])
        approved_stat = f'<div class="stat"><span class="stat-value">{company["approved"]}</span><span class="stat-label">Approved</span></div>' if company.get("approved") else ""

        is_acquired = company.get("acquired", False)
        card_class = "company-card acquired" if is_acquired else "company-card"
        acquired_badge = '<span class="acquired-badge">Acquired</span>' if is_acquired else ""
        acquisition_details = f'<div class="acquisition-details">{company.get("acquisition", "")}</div>' if is_acquired and company.get("acquisition") else ""

        if locked:
            card_class += " locked-card"

        inner = f'''
            <div class="card-header">
                <div>
                    <div class="card-ticker-row">
                        <span class="card-ticker">{ticker}</span>
                        <span class="card-name">{name}</span>
                        {acquired_badge}
                    </div>
                    {acquisition_details}
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
        '''

        if locked:
            return f'''
            <div class="{card_class}" onclick="showGateModal(event)">
                <div class="locked-blur">{inner}</div>
                <div class="locked-overlay">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    <span>Unlock Profile</span>
                </div>
            </div>
            '''
        else:
            return f'''
            <a href="/api/clinical/companies/{ticker}/html" class="{card_class}">
                {inner}
            </a>
            '''
    else:
        # index.json format - simpler card
        stage = company.get("development_stage", "")
        stage_label = STAGE_LABELS.get(stage, stage.replace("_", " ").title() if stage else "")
        modality = company.get("modality", "")
        modality_label = MODALITY_LABELS.get(modality, modality.replace("_", " ").title() if modality else "")
        therapeutic = company.get("therapeutic_area", "")
        therapeutic_label = therapeutic.replace("_", " ").title() if therapeutic else ""

        has_data = company.get("has_data", False)
        priority = company.get("priority", "").lower()
        market_cap = company.get("market_cap_mm", "")
        notes = company.get("notes", "")

        # Priority badge
        priority_class = f"priority-{priority}" if priority else ""
        priority_badge = f'<span class="priority-badge {priority_class}">{priority.upper()}</span>' if priority else ""

        # Data badge - shows checkmark for companies with detailed asset pages
        data_badge = '<span class="data-badge">✓ Detailed</span>' if has_data else ""

        # Tags
        tags = []
        if modality_label:
            tags.append(modality_label)
        if therapeutic_label:
            tags.append(therapeutic_label)
        tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in tags[:3]])

        card_class = "company-card"
        if locked:
            card_class += " locked-card"

        inner = f'''
            <div class="card-header">
                <div>
                    <div class="card-ticker-row">
                        <span class="card-ticker">{ticker}</span>
                        <span class="card-name">{name}</span>
                        {data_badge}
                    </div>
                </div>
                {f'<span class="platform-badge">{stage_label}</span>' if stage_label else ''}
            </div>
            {f'<p class="card-description">{notes}</p>' if notes else '<p class="card-description" style="color: #999;">No description available</p>'}
            <div class="stats-row">
                {f'<div class="stat"><span class="stat-value">{market_cap}</span><span class="stat-label">Market Cap</span></div>' if market_cap else ''}
                {priority_badge}
            </div>
            <div class="tags-row">{tags_html}</div>
        '''

        if locked:
            return f'''
            <div class="{card_class}" onclick="showGateModal(event)">
                <div class="locked-blur">{inner}</div>
                <div class="locked-overlay">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    <span>Unlock Profile</span>
                </div>
            </div>
            '''
        else:
            return f'''
            <a href="/api/clinical/companies/{ticker}/html" class="{card_class}">
                {inner}
            </a>
            '''

def generate_companies_page():
    # Load companies from index.json - SINGLE SOURCE OF TRUTH
    companies = load_companies_from_index()

    # Sort by: 1) has_data first, 2) priority, 3) ticker
    # Companies with detailed asset data appear at top
    priority_order = {"high": 0, "medium": 1, "low": 2, "": 3}
    companies.sort(key=lambda c: (
        0 if c.get("has_data", False) else 1,  # has_data first
        priority_order.get(c.get("priority", "").lower(), 3),  # then priority
        c.get("ticker", "")  # then alphabetical
    ))

    # Group by development stage
    stage_categories = {
        "large_cap_diversified": "Large Cap",
        "commercial_stage": "Commercial Stage",
        "platform": "Platform / Genetic Medicines",
        "late_clinical": "Late Clinical (Phase 3)",
        "mid_clinical": "Mid Clinical (Phase 2)",
        "early_clinical": "Early Clinical (Phase 1)",
        "preclinical": "Preclinical",
    }

    # Also group by legacy categories if present
    by_stage = {}
    by_legacy_cat = {}

    for company in companies:
        # Index.json grouping by stage
        stage = company.get("development_stage", "other")
        if stage not in by_stage:
            by_stage[stage] = []
        by_stage[stage].append(company)

        # Legacy grouping by category
        cat = company.get("category", "")
        if cat:
            if cat not in by_legacy_cat:
                by_legacy_cat[cat] = []
            by_legacy_cat[cat].append(company)

    # Build pills - use stage categories first, then legacy
    pills_html = '<a href="#all" class="category-pill active">All</a>'
    pills_html += '<a href="#has-data" class="category-pill">Has Data</a>'
    pills_html += '<a href="#high-priority" class="category-pill">High Priority</a>'

    for stage_id, stage_name in stage_categories.items():
        count = len(by_stage.get(stage_id, []))
        if count > 0:
            pills_html += f'<a href="#{stage_id}" class="category-pill">{stage_name} ({count})</a>'

    # Calculate total before building sections (companies gets reassigned in loop)
    total_count = len(companies)

    # Build sections starting with "Has Detailed Data" at top
    sections_html = ""

    # FIRST: Featured section for companies with detailed data (always unlocked)
    detailed_companies = [c for c in companies if c.get("has_data", False)]
    if detailed_companies:
        cards_html = ''.join([generate_company_card(c, locked=False) for c in detailed_companies])
        sections_html += f'''
        <section class="section" id="has-detailed-data">
            <div class="section-header">
                <h2 class="section-title">Featured: Detailed Analysis Available</h2>
                <span class="section-count">{len(detailed_companies)}</span>
            </div>
            <div class="cards-grid">{cards_html}</div>
        </section>
        '''

    # THEN: Regular sections by stage (gated - locked by default, unlocked via JS if subscribed)
    for stage_id, stage_name in stage_categories.items():
        stage_companies = by_stage.get(stage_id, [])
        if not stage_companies:
            continue
        cards_html = ''.join([generate_company_card(c, locked=True) for c in stage_companies])
        sections_html += f'''
        <section class="section gated-section" id="{stage_id}">
            <div class="section-header">
                <h2 class="section-title">{stage_name}</h2>
                <span class="section-count">{len(stage_companies)}</span>
            </div>
            <div class="cards-grid">{cards_html}</div>
        </section>
        '''

    # Add "other" section for companies without a stage (also gated)
    other_companies = by_stage.get("other", []) + by_stage.get("", [])
    if other_companies:
        cards_html = ''.join([generate_company_card(c, locked=True) for c in other_companies])
        sections_html += f'''
        <section class="section gated-section" id="other">
            <div class="section-header">
                <h2 class="section-title">Other</h2>
                <span class="section-count">{len(other_companies)}</span>
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
    <meta name="description" content="Browse {total_count} biotech companies with pipeline data and catalyst tracking.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    {get_base_styles()}
    <style>
        .search-box {{ margin-bottom: 16px; }}
        .search-input {{ width: 100%; max-width: 500px; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; }}
        .search-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }}
        .results-count {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px; }}
        /* Badges - consistent neutral styling */
        .data-badge {{ background: var(--navy); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; margin-left: 8px; }}
        .priority-badge {{ padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: #e5e7eb; color: #374151; }}
        .priority-badge.priority-high {{ background: var(--navy); color: white; }}
        .priority-badge.priority-medium {{ background: #e5e7eb; color: #374151; }}
        .priority-badge.priority-low {{ background: #f3f4f6; color: #6b7280; }}

        /* Email gate - locked card styles */
        .locked-card {{ display: block; position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; cursor: pointer; transition: all 0.2s; overflow: hidden; }}
        .locked-card:hover {{ border-color: var(--accent); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .locked-blur {{ filter: blur(4px); pointer-events: none; user-select: none; }}
        .locked-overlay {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; background: rgba(255,255,255,0.6); color: var(--navy); font-weight: 600; font-size: 0.85rem; }}
        .locked-overlay svg {{ opacity: 0.7; }}

        /* Gate modal */
        .gate-backdrop {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }}
        .gate-backdrop.visible {{ display: flex; }}
        .gate-modal {{ background: white; border-radius: 16px; padding: 40px; max-width: 440px; width: 90%; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.15); position: relative; }}
        .gate-modal h2 {{ font-size: 1.35rem; font-weight: 700; color: var(--navy); margin-bottom: 8px; line-height: 1.3; }}
        .gate-modal .gate-sub {{ color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 24px; }}
        .gate-modal input[type="email"] {{ width: 100%; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; margin-bottom: 12px; }}
        .gate-modal input[type="email"]:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }}
        .gate-modal .gate-btn {{ width: 100%; padding: 14px; background: var(--accent); color: white; font-weight: 700; font-size: 1rem; border: none; border-radius: 10px; cursor: pointer; transition: background 0.2s; }}
        .gate-modal .gate-btn:hover {{ background: var(--accent-hover); }}
        .gate-modal .gate-btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
        .gate-modal .gate-fine {{ color: var(--text-muted); font-size: 0.8rem; margin-top: 16px; }}
        .gate-modal .gate-close {{ position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 1.25rem; color: var(--text-muted); cursor: pointer; }}
        .gate-modal .gate-error {{ color: #dc2626; font-size: 0.85rem; margin-top: 8px; display: none; }}
        .gate-modal .gate-success {{ color: #16a34a; font-size: 0.85rem; margin-top: 8px; display: none; }}

        /* Unlocked state - applied via JS when user is subscribed */
        body.unlocked .locked-card {{ cursor: default; }}
        body.unlocked .locked-blur {{ filter: none; pointer-events: auto; user-select: auto; }}
        body.unlocked .locked-overlay {{ display: none; }}
    </style>
</head>
<body>
    {get_nav_html("companies")}
    <main class="main">
        <div class="page-header">
            <h1 class="page-title">Companies</h1>
            <p class="page-subtitle">{total_count} biotech companies with clinical data</p>
        </div>
        <div class="search-box">
            <input type="text" id="company-search" class="search-input" placeholder="Search by ticker, company name, or therapeutic area...">
        </div>
        <p class="results-count" id="results-count">Showing {total_count} companies</p>
        <nav class="category-nav">
            <div class="category-pills">{pills_html}</div>
        </nav>
        {sections_html}
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>

    <!-- Email gate modal -->
    <div class="gate-backdrop" id="gate-backdrop">
        <div class="gate-modal">
            <button class="gate-close" onclick="hideGateModal()">&times;</button>
            <h2>Get Full Access to 180+ Company Profiles</h2>
            <p class="gate-sub">Free during beta. Enter your email for instant access.</p>
            <form id="gate-form" onsubmit="submitGateEmail(event)">
                <input type="email" id="gate-email" placeholder="you@example.com" required>
                <button type="submit" class="gate-btn" id="gate-btn">Get Free Access</button>
            </form>
            <p class="gate-error" id="gate-error"></p>
            <p class="gate-success" id="gate-success"></p>
            <p class="gate-fine">No spam. Unsubscribe anytime.</p>
        </div>
    </div>

    <script>
        // --- Email gate logic ---
        function isUnlocked() {{
            const ts = localStorage.getItem('satyabio_unlocked');
            if (!ts) return false;
            const expires = parseInt(ts, 10);
            if (Date.now() > expires) {{
                localStorage.removeItem('satyabio_unlocked');
                localStorage.removeItem('satyabio_email');
                return false;
            }}
            return true;
        }}

        function unlockPage() {{
            document.body.classList.add('unlocked');
            // Convert locked divs to proper links
            document.querySelectorAll('.locked-card').forEach(card => {{
                const ticker = card.querySelector('.card-ticker');
                if (ticker) {{
                    const link = document.createElement('a');
                    link.href = '/api/clinical/companies/' + ticker.textContent.trim() + '/html';
                    link.className = 'company-card';
                    link.innerHTML = card.querySelector('.locked-blur').innerHTML;
                    card.replaceWith(link);
                }}
            }});
        }}

        function showGateModal(e) {{
            if (isUnlocked()) return;
            e.preventDefault();
            e.stopPropagation();
            document.getElementById('gate-backdrop').classList.add('visible');
            document.getElementById('gate-email').focus();
        }}

        function hideGateModal() {{
            document.getElementById('gate-backdrop').classList.remove('visible');
            document.getElementById('gate-error').style.display = 'none';
            document.getElementById('gate-success').style.display = 'none';
        }}

        async function submitGateEmail(e) {{
            e.preventDefault();
            const email = document.getElementById('gate-email').value.trim();
            const btn = document.getElementById('gate-btn');
            const errorEl = document.getElementById('gate-error');
            const successEl = document.getElementById('gate-success');

            errorEl.style.display = 'none';
            successEl.style.display = 'none';
            btn.disabled = true;
            btn.textContent = 'Submitting...';

            try {{
                const resp = await fetch('/api/subscribe', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ email }})
                }});
                const data = await resp.json();
                if (resp.ok) {{
                    // Store unlock for 30 days
                    const thirtyDays = 30 * 24 * 60 * 60 * 1000;
                    localStorage.setItem('satyabio_unlocked', String(Date.now() + thirtyDays));
                    localStorage.setItem('satyabio_email', email);
                    successEl.textContent = 'You\\'re in! Unlocking all profiles...';
                    successEl.style.display = 'block';
                    setTimeout(() => {{
                        hideGateModal();
                        unlockPage();
                    }}, 800);
                }} else {{
                    errorEl.textContent = data.detail || 'Something went wrong. Please try again.';
                    errorEl.style.display = 'block';
                }}
            }} catch (err) {{
                errorEl.textContent = 'Network error. Please try again.';
                errorEl.style.display = 'block';
            }} finally {{
                btn.disabled = false;
                btn.textContent = 'Get Free Access';
            }}
        }}

        // Close modal on backdrop click
        document.getElementById('gate-backdrop').addEventListener('click', function(e) {{
            if (e.target === this) hideGateModal();
        }});

        // Check unlock on page load
        if (isUnlocked()) {{
            unlockPage();
        }}

        let activeCategory = 'all';

        function filterCompanies() {{
            const q = document.getElementById('company-search').value.toLowerCase();
            const cards = document.querySelectorAll('.company-card');
            const sections = document.querySelectorAll('.section');
            let total = 0;

            sections.forEach(section => {{
                const sectionId = section.id;
                let sectionCount = 0;

                section.querySelectorAll('.company-card').forEach(card => {{
                    const text = card.textContent.toLowerCase();
                    const matchSearch = !q || text.includes(q);

                    // Handle special filters
                    let matchCategory = true;
                    if (activeCategory === 'all') {{
                        matchCategory = true;
                    }} else if (activeCategory === 'has-data') {{
                        matchCategory = card.querySelector('.data-badge') !== null;
                    }} else if (activeCategory === 'high-priority') {{
                        matchCategory = card.querySelector('.priority-badge.priority-high') !== null;
                    }} else {{
                        matchCategory = sectionId === activeCategory;
                    }}

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

    # Load targets from index.json
    index_targets, categories = load_targets_index()

    # Map index.json targets to display format
    targets = []
    for t in index_targets:
        slug = t.get("slug", "")
        market_status = t.get("market_status", "race_to_first")
        status_map = {"approved": "Approved Drug Exists", "race_to_first": "Race to First", "early": "Early Stage"}
        status = status_map.get(market_status, "Race to First")

        # Get leader/challenger from lead_companies list
        lead_companies = t.get("lead_companies", [])
        leader = {"company": lead_companies[0] if len(lead_companies) > 0 else "-", "ticker": "-", "drug": "-", "phase": "-"}
        challenger = {"company": lead_companies[1] if len(lead_companies) > 1 else "-", "ticker": "-", "drug": "-", "phase": "-"}

        # Load detailed data if available
        detail = load_target_data(slug)
        if detail:
            assets = detail.get("assets", [])
            if len(assets) > 0:
                a = assets[0]
                leader = {"company": a.get("company", "-"), "ticker": a.get("ticker", "-"), "drug": a.get("drug", a.get("name", "-")), "phase": a.get("stage", "-")}
            if len(assets) > 1:
                a = assets[1]
                challenger = {"company": a.get("company", "-"), "ticker": a.get("ticker", "-"), "drug": a.get("drug", a.get("name", "-")), "phase": a.get("stage", "-")}

        # Use legacy_slug for backwards compatible URLs, otherwise use slug
        url_slug = t.get("legacy_slug", slug)

        targets.append({
            "name": t.get("name", slug),
            "category": t.get("category", "other"),
            "slug": url_slug,
            "status": status,
            "leader": leader,
            "challenger": challenger,
            "count": str(t.get("total_assets", "?")),
            "desc": t.get("description", ""),
            "hot": t.get("hot_target", False)
        })

    # Add any hardcoded targets not in index.json
    existing_slugs = {t.get("slug") for t in targets if t.get("slug")}
    hardcoded_extras = [
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
        {"name": "IL-4Ra / IL-13", "category": "immunology", "slug": None, "status": "Approved Drug Exists",
         "leader": {"company": "Regeneron", "ticker": "REGN", "drug": "Dupixent", "phase": "Approved"},
         "challenger": {"company": "Apogee", "ticker": "APGE", "drug": "APG777", "phase": "Phase 2"},
         "count": "4", "desc": "$13B+ blockbuster. Q12W dosing goal."},

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
    # Add hardcoded extras that aren't already in targets from index.json
    targets.extend(hardcoded_extras)

    # Category colors and labels - consistent gray styling
    category_styles = {
        "oncology": {"bg": "#f0f0f0", "color": "#6b7280", "label": "Oncology"},
        "immunology": {"bg": "#f0f0f0", "color": "#6b7280", "label": "I&I"},
        "metabolic": {"bg": "#f0f0f0", "color": "#6b7280", "label": "Metabolic"},
        "cardiovascular": {"bg": "#f0f0f0", "color": "#6b7280", "label": "Cardiovascular"},
        "rare": {"bg": "#f0f0f0", "color": "#6b7280", "label": "Rare Disease"},
        "neuro": {"bg": "#f0f0f0", "color": "#6b7280", "label": "Neuro"},
    }

    # Status colors - consistent navy styling for all
    status_styles = {
        "Approved Drug Exists": {"bg": "#1a2b3c", "color": "#ffffff"},
        "Race to First": {"bg": "#1a2b3c", "color": "#ffffff"},
        "Early Stage": {"bg": "#1a2b3c", "color": "#ffffff"},
    }

    # Build target cards
    cards_html = ""
    for t in targets:
        cat = category_styles.get(t["category"], {"bg": "#f0f0f0", "color": "#6b7280", "label": "Other"})
        status = status_styles.get(t["status"], {"bg": "#1a2b3c", "color": "#ffffff"})

        view_btn = f'<a href="/targets/{t["slug"]}" class="view-btn">View Full Landscape &rarr;</a>' if t["slug"] else ""

        # Build clean competitor text - handle missing data
        def format_competitor(comp):
            parts = []
            company = comp.get("company", "-")
            ticker = comp.get("ticker", "-")
            drug = comp.get("drug", "-")

            if company and company != "-":
                parts.append(f'<span class="company">{company}</span>')
                if ticker and ticker != "-":
                    parts.append(f'<span class="ticker">({ticker})</span>')

            if drug and drug != "-":
                if parts:
                    parts.append(f'— {drug}')
                else:
                    parts.append(drug)

            return ' '.join(parts) if parts else '<span class="text-muted">TBD</span>'

        leader_text = format_competitor(t["leader"])
        challenger_text = format_competitor(t["challenger"])

        # Only show phase pill if there's a valid phase
        leader_phase = t["leader"]["phase"]
        challenger_phase = t["challenger"]["phase"]
        leader_pill = f'<span class="stage-pill">{leader_phase}</span>' if leader_phase and leader_phase != "-" else ""
        challenger_pill = f'<span class="stage-pill">{challenger_phase}</span>' if challenger_phase and challenger_phase != "-" else ""

        cards_html += f'''
        <div class="target-card" data-category="{t["category"]}">
            <div class="target-header">
                <div class="target-name">{t["name"]}</div>
                <span class="area-badge">{cat["label"]}</span>
            </div>
            <div class="market-status">{t["status"]}</div>
            <div class="competitor-section">
                <div class="competitor-row">
                    <span class="competitor-label">{"Market Leader" if "Approved" in t["status"] else "Frontrunner"}</span>
                    <span class="competitor-info">
                        <span class="competitor-text">{leader_text}</span>
                        {leader_pill}
                    </span>
                </div>
                <div class="competitor-row">
                    <span class="competitor-label">{"Challenger" if "Approved" in t["status"] else "Fast Follower"}</span>
                    <span class="competitor-info">
                        <span class="competitor-text">{challenger_text}</span>
                        {challenger_pill}
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
        /* Category badge - consistent neutral styling */
        .area-badge {{ padding: 4px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 500; background: transparent; border: 1px solid #d1d5db; color: #6b7280; }}
        /* Status pill - navy background for all statuses */
        .market-status {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; background: #1a2b3c; color: #ffffff; }}

        .competitor-section {{ margin-bottom: 12px; }}
        .competitor-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.85rem; }}
        .competitor-row:last-child {{ border-bottom: none; }}
        .competitor-label {{ color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; min-width: 90px; }}
        .competitor-info {{ display: flex; align-items: center; gap: 8px; flex: 1; justify-content: flex-end; text-align: right; }}
        .competitor-text {{ color: var(--text-secondary); }}
        .competitor-text .company {{ color: var(--navy); font-weight: 500; }}
        /* Ticker - subtle gray, not coral */
        .competitor-text .ticker {{ color: #6b7280; font-size: 0.85em; }}
        /* Phase pill - consistent neutral gray for ALL phases */
        .stage-pill {{ padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; background: #e5e7eb; color: #374151; }}

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
                        <span class="filter-dot"></span>
                        Oncology
                    </label>
                    <label class="filter-option" data-filter="immunology">
                        <span class="filter-dot"></span>
                        Immunology
                    </label>
                    <label class="filter-option" data-filter="metabolic">
                        <span class="filter-dot"></span>
                        Metabolic
                    </label>
                    <label class="filter-option" data-filter="cardiovascular">
                        <span class="filter-dot"></span>
                        Cardiovascular
                    </label>
                    <label class="filter-option" data-filter="rare">
                        <span class="filter-dot"></span>
                        Rare Disease
                    </label>
                    <label class="filter-option" data-filter="neuro">
                        <span class="filter-dot"></span>
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

        // Check for search query in URL hash
        const hash = window.location.hash;
        if (hash.includes('search=')) {{
            const query = decodeURIComponent(hash.split('search=')[1]);
            document.getElementById('target-search').value = query;
            applyFilters();
        }}
    </script>
</body>
</html>'''

def generate_target_detail_page(slug: str):
    """Generate a detailed target page from JSON data."""
    data = load_target_data(slug)
    if not data:
        return None

    target_name = data.get("name", slug)
    full_name = data.get("full_name", target_name)
    category = data.get("category", "other")
    description = data.get("description", "")
    total_assets = data.get("total_assets", 0)
    market_status = data.get("market_status", "race_to_first")

    # Category styling
    category_styles = {
        "oncology": {"bg": "#fef2f2", "color": "#dc2626", "label": "Oncology"},
        "immunology": {"bg": "#f0fdf4", "color": "#16a34a", "label": "I&I"},
        "metabolic": {"bg": "#fef9c3", "color": "#ca8a04", "label": "Metabolic"},
        "cardiovascular": {"bg": "#eff6ff", "color": "#2563eb", "label": "Cardiovascular"},
        "rare": {"bg": "#faf5ff", "color": "#7c3aed", "label": "Rare Disease"},
        "neuro": {"bg": "#fef3c7", "color": "#92400e", "label": "Neuro"},
    }
    cat_style = category_styles.get(category, {"bg": "#f3f4f6", "color": "#4b5563", "label": category.title()})

    # Build assets table
    assets = data.get("assets", [])
    assets_html = ""
    for asset in assets:
        phase = asset.get("stage", asset.get("phase", ""))
        company = asset.get("company", "")
        ticker = asset.get("ticker", "")
        drug = asset.get("drug", asset.get("name", ""))
        deal_value = asset.get("deal_value", "")
        deal_info = f'<span class="deal-value">${deal_value}M</span>' if deal_value else ""

        assets_html += f'''
        <tr>
            <td><strong>{drug}</strong></td>
            <td><a href="/api/clinical/companies/{ticker}/html" class="company-link">{company}</a> <span class="ticker">({ticker})</span></td>
            <td><span class="phase-badge">{phase}</span></td>
            <td>{deal_info}</td>
        </tr>
        '''

    # Investment thesis
    thesis = data.get("investment_thesis", {})
    bull_points = thesis.get("bull_case", [])
    bear_points = thesis.get("bear_case", thesis.get("key_risks", []))

    bull_html = "".join([f'<li>{point}</li>' for point in bull_points]) if bull_points else "<li>No bull case data available</li>"
    bear_html = "".join([f'<li>{point}</li>' for point in bear_points]) if bear_points else "<li>No bear case data available</li>"

    # Key metrics
    total_committed = data.get("total_committed", 0)
    phase_3_assets = data.get("phase_3_assets", 0)
    approved_assets = data.get("approved_assets", 0)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{target_name} Target Landscape | Satya Bio</title>
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
        .report-header .subtitle {{ opacity: 0.85; font-size: 1rem; margin-bottom: 8px; }}
        .report-header p {{ opacity: 0.7; max-width: 700px; font-size: 0.95rem; }}
        .report-meta {{ display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }}
        .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }}
        .meta-item .label {{ font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }}
        .meta-item .value {{ font-size: 1.25rem; font-weight: 700; }}
        .category-badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; margin-bottom: 12px; }}

        .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }}
        .section h2 {{ color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }}

        .assets-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        .assets-table th {{ background: var(--navy); color: white; padding: 12px; text-align: left; }}
        .assets-table td {{ padding: 12px; border-bottom: 1px solid var(--border); }}
        .assets-table tr:hover {{ background: var(--bg); }}
        .phase-badge {{ padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; color: white; }}
        .company-link {{ color: var(--navy); text-decoration: none; font-weight: 500; }}
        .company-link:hover {{ color: var(--accent); }}
        .ticker {{ color: var(--text-muted); font-size: 0.8rem; }}
        .deal-value {{ color: #059669; font-weight: 600; }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }}
        .bull-box {{ border-left: 3px solid #e07a5f; }}
        .bear-box {{ border-left: 3px solid #1a2b3c; }}
        .bull-box h3 {{ color: #e07a5f; margin-bottom: 16px; }}
        .bear-box h3 {{ color: #1a2b3c; margin-bottom: 16px; }}
        .thesis-list {{ list-style: none; padding: 0; margin: 0; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; }}
        .thesis-list li:last-child {{ border-bottom: none; }}

        .back-link {{ display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-bottom: 24px; font-weight: 500; }}
    </style>
</head>
<body>
    {get_nav_html("targets")}
    <main class="main">
        <a href="/targets" class="back-link">← Back to All Targets</a>

        <div class="report-header">
            <span class="category-badge" style="background:{cat_style['bg']};color:{cat_style['color']};">{cat_style['label']}</span>
            <h1>{target_name}</h1>
            <p class="subtitle">{full_name}</p>
            <p>{description}</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Total Assets</div><div class="value">{total_assets}</div></div>
                <div class="meta-item"><div class="label">Phase 3+</div><div class="value">{phase_3_assets + approved_assets}</div></div>
                {f'<div class="meta-item"><div class="label">Deal Activity</div><div class="value">${total_committed:,}M</div></div>' if total_committed else ''}
            </div>
        </div>

        <div class="section">
            <h2>Competitive Landscape ({len(assets)} Assets)</h2>
            <table class="assets-table">
                <thead>
                    <tr><th>Drug</th><th>Company</th><th>Stage</th><th>Deal Value</th></tr>
                </thead>
                <tbody>
                    {assets_html}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Investment Thesis</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">{bull_html}</ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case / Key Risks</h3>
                    <ul class="thesis-list">{bear_html}</ul>
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
        pipeline_rows += f'''
        <tr>
            <td><strong>{drug["asset"]}</strong></td>
            <td>{drug["company"]}<br><span class="ticker-small">{drug["ticker"]}</span></td>
            <td>{drug["mechanism"]}</td>
            <td><span class="phase-badge">{drug["phase"]}</span></td>
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
        .bull-box, .bear-box {{ padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }}
        .bull-box {{ border-left: 3px solid #e07a5f; }}
        .bear-box {{ border-left: 3px solid #1a2b3c; }}
        .bull-box h3 {{ color: #e07a5f; }}
        .bear-box h3 {{ color: #1a2b3c; }}
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


def _parse_catalyst_date(date_str: str):
    """Parse a machine-readable date string (YYYY-MM-DD or YYYY-MM) into a date object for comparison."""
    from datetime import date as _date
    parts = date_str.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) >= 2 else 1
        day = int(parts[2]) if len(parts) >= 3 else 1
        return _date(year, month, day)
    except (ValueError, IndexError):
        return _date(9999, 1, 1)  # unparseable dates sort to end


def render_catalyst_section(slug: str, admin: bool = False) -> str:
    """Load catalysts from data/targets/{slug}/catalysts.json and render completed + upcoming sections.

    Catalysts with date < today are completed; date >= today are upcoming.
    Completed sorted by date descending (most recent first).
    Upcoming sorted by date ascending (soonest first).
    """
    catalysts_path = Path(__file__).parent.parent / "data" / "targets" / slug / "catalysts.json"
    if not catalysts_path.exists():
        return ""
    with open(catalysts_path) as f:
        data = json.load(f)

    catalysts = data.get("catalysts", [])
    last_reviewed = data.get("last_reviewed", "")

    from datetime import date as _date
    today = _date.today()

    # Split by date
    completed = []
    upcoming = []
    for c in catalysts:
        parsed = _parse_catalyst_date(c.get("date", ""))
        if parsed < today:
            completed.append((parsed, c))
        else:
            upcoming.append((parsed, c))

    # Sort: completed descending (most recent first), upcoming ascending (soonest first)
    completed.sort(key=lambda x: x[0], reverse=True)
    upcoming.sort(key=lambda x: x[0])

    # Staleness banner (admin only)
    staleness_html = ""
    if admin and last_reviewed:
        try:
            reviewed_date = _date.fromisoformat(last_reviewed)
            days_ago = (today - reviewed_date).days
            if days_ago > 30:
                staleness_html = f'''
        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 0.85rem; color: #92400e;">
            Catalysts last verified {last_reviewed} ({days_ago} days ago). Some dates may have changed.
        </div>'''
        except ValueError:
            pass

    # Render completed
    completed_html = ""
    if completed:
        items = ""
        for _, c in completed:
            display = c.get("date_display", c.get("date", ""))
            outcome = f'<div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">{c["outcome"]}</div>' if c.get("outcome") else ""
            asset_label = f' ({c["asset"]})' if c.get("asset") else ""
            items += f'''
                <div class="catalyst-item">
                    <div class="catalyst-date" style="color: #16a34a;">{display}</div>
                    <div>
                        <strong>{c["company"]}{asset_label}:</strong> {c["description"]}
                        {outcome}
                    </div>
                </div>'''
        completed_html = f'''
        <div class="section">
            <h2>Completed Catalysts</h2>
            <div class="catalyst-timeline">{items}
            </div>
        </div>'''

    # Render upcoming
    upcoming_html = ""
    if upcoming:
        items = ""
        for _, c in upcoming:
            display = c.get("date_display", c.get("date", ""))
            asset_label = f' ({c["asset"]})' if c.get("asset") else ""
            items += f'''
                <div class="catalyst-item">
                    <div class="catalyst-date">{display}</div>
                    <div><strong>{c["company"]}{asset_label}:</strong> {c["description"]}</div>
                </div>'''
        upcoming_html = f'''
        <div class="section">
            <h2>Upcoming Catalysts</h2>
            <div class="catalyst-timeline">{items}
            </div>
        </div>'''

    return staleness_html + completed_html + upcoming_html


def generate_tl1a_report(admin: bool = False):
    """Generate the TL1A / IBD competitive landscape report."""

    # TL1A Assets data
    assets = [
        {"asset": "Tulisokibart (PRA023)", "company": "Merck (via Prometheus)", "ticker": "MRK", "phase": "Phase 3", "indication": "UC, CD", "deal": "$10.8B acquisition", "efficacy": "26% remission (TL1A-high)", "catalyst": "ATLAS-UC Ph3 data H2 2026"},
        {"asset": "Duvakitug (TEV-48574)", "company": "Sanofi / Teva", "ticker": "SNY", "phase": "Phase 3", "indication": "UC, CD", "deal": "$500M+ partnership", "efficacy": "47.8% remission (1000mg)", "catalyst": "SUNSCAPE Ph3 enrolling 2026"},
        {"asset": "Afimkibart (RVT-3101)", "company": "Roche (via Telavant)", "ticker": "RHHBY", "phase": "Phase 3", "indication": "UC, CD", "deal": "$7.25B acquisition", "efficacy": "35% remission", "catalyst": "Ph3 UC data 2026"},
        {"asset": "SAR443765", "company": "Sanofi", "ticker": "SNY", "phase": "Phase 2", "indication": "UC, CD", "deal": "Internal", "efficacy": "Bispecific (TL1A + IL-23)", "catalyst": "Ph2 data ongoing"},
        {"asset": "PF-07258669", "company": "Pfizer", "ticker": "PFE", "phase": "Phase 1", "indication": "IBD", "deal": "Internal", "efficacy": "Early stage", "catalyst": "Ph1 data ongoing"},
        {"asset": "ABBV-261", "company": "AbbVie", "ticker": "ABBV", "phase": "Phase 1", "indication": "IBD", "deal": "Internal", "efficacy": "Early stage", "catalyst": "Ph1 data ongoing"},
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
        assets_rows += f'''
        <tr>
            <td><strong>{a["asset"]}</strong></td>
            <td>{a["company"]}<br><span class="ticker-small">{a["ticker"]}</span></td>
            <td><span class="phase-badge">{a["phase"]}</span></td>
            <td>{a["indication"]}</td>
            <td class="deal-value">{a["deal"]}</td>
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
            <td class="delta-positive">{e["delta"]}</td>
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
        .bull-box, .bear-box {{ padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }}
        .bull-box {{ border-left: 3px solid #e07a5f; }}
        .bear-box {{ border-left: 3px solid #1a2b3c; }}
        .bull-box h3 {{ color: #e07a5f; }}
        .bear-box h3 {{ color: #1a2b3c; }}
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

        <!-- Catalysts (data-driven from catalysts.json) -->
        {render_catalyst_section("tl1a-ibd", admin=admin)}

        <a href="/targets" class="back-link">← Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


def generate_b7h3_report(admin: bool = False):
    """Generate the B7-H3 / ADC competitive landscape report."""

    # B7-H3 Assets data — updated Feb 2026
    assets = [
        {"asset": "Ifinatamab deruxtecan (I-DXd)", "company": "Daiichi Sankyo / Merck", "ticker": "DSNKY/MRK", "phase": "Phase 3", "modality": "ADC (DXd)", "indication": "SCLC, NSCLC, mCRPC, ESCC", "orr": "48.2% (ES-SCLC)", "catalyst": "IDeate-Lung02 Ph3 data ~2028; potential accel. approval 2027"},
        {"asset": "HS-20093 / GSK'227", "company": "GSK (via Hansoh)", "ticker": "GSK", "phase": "Phase 1/2/3", "modality": "ADC (TOPOi)", "indication": "SCLC, Osteosarcoma", "orr": "61% (ES-SCLC 8mg/kg)", "catalyst": "GSK global data H1 2026; Ph3 SCLC enrolling"},
        {"asset": "AZD8205", "company": "AstraZeneca", "ticker": "AZN", "phase": "Phase 2", "modality": "ADC (Topo I)", "indication": "Solid tumors", "orr": "Early data", "catalyst": "Ph2 data ongoing"},
        {"asset": "BNT324", "company": "BioNTech", "ticker": "BNTX", "phase": "Phase 1/2", "modality": "ADC", "indication": "Solid tumors", "orr": "Early stage", "catalyst": "Ph1 data ongoing"},
        {"asset": "Omburtamab", "company": "Y-mAbs", "ticker": "YMAB", "phase": "Approved", "modality": "Radioconjugate", "indication": "CNS tumors", "orr": "N/A", "catalyst": "Label expansion"},
        {"asset": "Vobramitamab duocarmazine (MGC018)", "company": "MacroGenics", "ticker": "MGNX", "phase": "Phase 1/2", "modality": "ADC (vcMMAE)", "indication": "CRC, SCLC, Solid tumors", "orr": "Early data", "catalyst": "Ph2 data TBD"},
    ]

    # Build assets table
    assets_rows = ""
    for a in assets:
        assets_rows += f'''
        <tr>
            <td><strong>{a["asset"]}</strong></td>
            <td>{a["company"]}<br><span class="ticker-small">{a["ticker"]}</span></td>
            <td><span class="phase-badge">{a["phase"]}</span></td>
            <td>{a["modality"]}</td>
            <td>{a["indication"]}</td>
            <td class="data-highlight">{a["orr"]}</td>
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
        .section h3 {{ color: var(--navy); font-size: 1.1rem; margin: 20px 0 12px; }}

        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background: var(--bg); }}

        .thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .thesis-grid {{ grid-template-columns: 1fr; }} }}
        .bull-box, .bear-box {{ padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }}
        .bull-box {{ border-left: 3px solid #e07a5f; }}
        .bear-box {{ border-left: 3px solid #1a2b3c; }}
        .bull-box h3 {{ color: #e07a5f; }}
        .bear-box h3 {{ color: #1a2b3c; }}
        .thesis-list {{ list-style: none; padding: 0; margin-top: 16px; }}
        .thesis-list li {{ padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }}
        .thesis-list li:last-child {{ border-bottom: none; }}
        .thesis-list li::before {{ content: "\\2192"; font-weight: bold; }}

        .highlight-box {{ background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 1px solid #f59e0b; border-radius: 12px; padding: 20px; margin: 20px 0; }}
        .highlight-box h4 {{ color: #92400e; margin-bottom: 8px; }}
        .highlight-box p {{ color: #78350f; font-size: 0.9rem; }}

        .note-box {{ background: var(--bg); border-left: 3px solid var(--accent); padding: 16px 20px; margin-top: 16px; border-radius: 0 8px 8px 0; }}
        .note-box p {{ color: var(--text-secondary); font-size: 0.85rem; line-height: 1.6; margin: 0; }}

        .bio-point {{ display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }}
        .bio-point:last-child {{ border-bottom: none; }}
        .bio-icon {{ min-width: 28px; height: 28px; background: var(--navy); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }}
        .bio-icon.risk {{ background: #dc2626; }}
        .bio-text {{ font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; }}
        .bio-text strong {{ color: var(--text); }}

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
                <div class="meta-item"><div class="label">Best ORR</div><div class="value">61% (ES-SCLC)</div></div>
                <div class="meta-item"><div class="label">Modalities</div><div class="value">ADC, CAR-T, RIT</div></div>
            </div>
        </div>

        <!-- Mega Deal Highlight -->
        <div class="highlight-box">
            <h4>Merck-Daiichi Sankyo Partnership (Oct 2023)</h4>
            <p>The <strong>$22 billion</strong> collaboration is the largest ADC deal in history, validating B7-H3 as a high-conviction oncology target. Merck paid $4B upfront + $18B in milestones for global co-development and commercialization rights to ifinatamab deruxtecan (I-DXd).</p>
        </div>

        <!-- Target Biology -->
        <div class="section">
            <h2>Target Biology</h2>
            <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 20px;">
                B7-H3 (CD276) is a type I transmembrane protein in the B7 immune checkpoint family, encoded by the <em>CD276</em> gene.
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
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
            <div class="bio-point">
                <div class="bio-icon">1</div>
                <div class="bio-text"><strong>Expressed in >70% of solid tumors</strong> with minimal expression in normal tissues — this is the key therapeutic window that makes B7-H3 an ideal ADC target.</div>
            </div>
            <div class="bio-point">
                <div class="bio-icon">2</div>
                <div class="bio-text"><strong>Dual role: immune checkpoint + tumor promoter.</strong> Unlike PD-L1/CTLA-4, B7-H3 has both immune checkpoint suppression AND direct tumor-promoting functions (promotes migration, invasion, angiogenesis).</div>
            </div>
            <div class="bio-point">
                <div class="bio-icon risk">!</div>
                <div class="bio-text"><strong>Receptor still debated.</strong> TLT-2 has been proposed but remains controversial; the precise mechanism of B7-H3 immune suppression is not fully resolved. This is a scientific risk, though it does not impact ADC delivery.</div>
            </div>
            <div class="bio-point">
                <div class="bio-icon">3</div>
                <div class="bio-text"><strong>Expression does NOT clearly predict ADC response.</strong> Current trials are NOT selecting patients by B7-H3 expression level. This is different from HER2 ADCs where expression matters — B7-H3 ADCs rely on high prevalence across tumor types.</div>
            </div>
        </div>

        <!-- ADC Technology Comparison -->
        <div class="section">
            <h2>ADC Technology Comparison</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Feature</th>
                            <th>I-DXd (Merck/Daiichi)</th>
                            <th>HS-20093 (GSK/Hansoh)</th>
                            <th>MGC018 (MacroGenics)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>Antibody</strong></td><td>Humanized IgG1</td><td>Fully human IgG1</td><td>Humanized IgG1</td></tr>
                        <tr><td><strong>Payload</strong></td><td>DXd (Topo I inhibitor)</td><td>TOPOi (proprietary)</td><td>vcMMAE (microtubule)</td></tr>
                        <tr><td><strong>Linker</strong></td><td>Tetrapeptide cleavable</td><td>Proprietary cleavable</td><td>Cleavable</td></tr>
                        <tr><td><strong>DAR</strong></td><td>~4</td><td>TBD</td><td>~4</td></tr>
                        <tr><td><strong>Bystander effect</strong></td><td>Yes (membrane permeable)</td><td>Yes</td><td>Limited</td></tr>
                        <tr><td><strong>Key toxicity</strong></td><td>Nausea, neutropenia, ILD risk</td><td>Neutropenia (39% Gr3+), thrombocytopenia</td><td>Typical MMAE profile</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="note-box">
                <p><strong>Why payload matters:</strong> DXd and TOPOi payloads have bystander killing effects, meaning they can kill neighboring tumor cells even without B7-H3 expression. This is clinically important for heterogeneous tumors. MMAE payloads are less membrane-permeable and have a different toxicity profile.</p>
            </div>
        </div>

        <!-- Deal Landscape -->
        <div class="section">
            <h2>Deal Landscape</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Deal</th>
                            <th>Parties</th>
                            <th>Date</th>
                            <th>Total Value</th>
                            <th>Structure</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>I-DXd co-development</strong></td>
                            <td>Merck + Daiichi Sankyo</td>
                            <td>Oct 2023</td>
                            <td class="deal-value">$22B</td>
                            <td>$4B upfront + $18B milestones</td>
                        </tr>
                        <tr>
                            <td><strong>HS-20093 (B7-H3 ADC)</strong></td>
                            <td>GSK + Hansoh</td>
                            <td>Dec 2023</td>
                            <td class="deal-value">$1.71B</td>
                            <td>$185M upfront + $1.525B milestones</td>
                        </tr>
                        <tr>
                            <td><strong>HS-20089 (B7-H4 ADC)</strong></td>
                            <td>GSK + Hansoh</td>
                            <td>Oct 2023</td>
                            <td class="deal-value">$1.585B</td>
                            <td>$85M upfront + $1.5B milestones</td>
                        </tr>
                    </tbody>
                </table>
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

        <!-- Registration Strategy -->
        <div class="section">
            <h2>Registration Strategy — Active Phase 3 Trials</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Trial</th>
                            <th>Asset</th>
                            <th>Indication</th>
                            <th>Phase</th>
                            <th>Patients</th>
                            <th>Expected Completion</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>IDeate-Lung02</strong></td><td>I-DXd</td><td>2L ES-SCLC</td><td><span class="phase-badge">Phase 3</span></td><td>~540</td><td>2028</td></tr>
                        <tr><td><strong>IDeate-Lung03</strong></td><td>I-DXd</td><td>1L ES-SCLC (combo)</td><td><span class="phase-badge">Phase 3</span></td><td>TBD</td><td>TBD</td></tr>
                        <tr><td><strong>IDeate-Prostate01</strong></td><td>I-DXd</td><td>mCRPC</td><td><span class="phase-badge">Phase 3</span></td><td>~1440</td><td>Jun 2028</td></tr>
                        <tr><td><strong>IDeate-Esophageal01</strong></td><td>I-DXd</td><td>ESCC</td><td><span class="phase-badge">Phase 3</span></td><td>TBD</td><td>TBD</td></tr>
                        <tr><td><strong>TROPION-Lung08</strong></td><td>I-DXd</td><td>1L NSCLC</td><td><span class="phase-badge">Phase 3</span></td><td>TBD</td><td>TBD</td></tr>
                        <tr><td><strong>GSK'227 Ph3</strong></td><td>HS-20093</td><td>SCLC</td><td><span class="phase-badge">Phase 3</span></td><td>TBD</td><td>TBD</td></tr>
                        <tr><td><strong>GSK'227 Ph3</strong></td><td>HS-20093</td><td>Osteosarcoma</td><td><span class="phase-badge">Phase 3</span></td><td>TBD</td><td>TBD</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Market Opportunity -->
        <div class="section">
            <h2>Market Opportunity by Indication</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Indication</th>
                            <th>Addressable Market</th>
                            <th>Key Competitors</th>
                            <th>B7-H3 Advantage</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>ES-SCLC (2L+)</strong></td><td>$2-3B</td><td>Lurbinectedin, tarlatamab</td><td>48% ORR, durable responses, BTD</td></tr>
                        <tr><td><strong>NSCLC (1L)</strong></td><td>$30B+</td><td>Keytruda combos, Tagrisso</td><td>Combo potential, broad expression</td></tr>
                        <tr><td><strong>mCRPC</strong></td><td>$8-10B</td><td>Enzalutamide, Xtandi, Pluvicto</td><td>Novel mechanism, post-ARPI</td></tr>
                        <tr><td><strong>ESCC</strong></td><td>$2-3B</td><td>Keytruda, Opdivo</td><td>Unmet need in 2L+</td></tr>
                        <tr><td><strong>Osteosarcoma</strong></td><td>&lt;$500M (orphan)</td><td>Limited options</td><td>High unmet need, orphan pricing</td></tr>
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
                        <li>48% ORR in ES-SCLC with BTD — best-in-class for a tumor with limited targeted therapy</li>
                        <li>Ideal target biology: high tumor, low normal tissue expression</li>
                        <li>5+ registrational Phase 3 trials across SCLC, NSCLC, prostate, esophageal</li>
                        <li>Multiple modalities (ADC, CAR-T, radioconjugate) = diversified bet on target</li>
                        <li>Pan-solid tumor applicability = $40B+ addressable market across indications</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>B7-H3 receptor mechanism not fully understood — scientific risk</li>
                        <li>Expression does not predict response — no biomarker-driven patient selection</li>
                        <li>Merck/Daiichi dominance may crowd out smaller players</li>
                        <li>ADC class toxicities (ILD, cytopenias) may limit combination strategies</li>
                        <li>Registration trials still enrolling; Phase 3 data not expected until 2027-2028</li>
                        <li>Competition from other ADC targets (TROP2, HER3, Nectin-4, B7-H4)</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Catalysts (data-driven from catalysts.json) -->
        {render_catalyst_section("b7h3-adc", admin=admin)}

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
        assets_rows += f'''
        <tr>
            <td><strong>{a["asset"]}</strong></td>
            <td>{a["company"]}<br><span class="ticker-small">{a["ticker"]}</span></td>
            <td><span class="phase-badge">{a["phase"]}</span></td>
            <td><strong>{a["mutation"]}</strong></td>
            <td>{a["indication"]}</td>
            <td class="data-highlight">{a["orr"]}</td>
            <td class="notes-text">{a["notes"]}</td>
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
        .bull-box, .bear-box {{ padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }}
        .bull-box {{ border-left: 3px solid #e07a5f; }}
        .bear-box {{ border-left: 3px solid #1a2b3c; }}
        .bull-box h3 {{ color: #e07a5f; }}
        .bear-box h3 {{ color: #1a2b3c; }}
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
    # Load companies from index.json
    companies = load_companies_from_index()
    company = None
    for c in companies:
        if c.get("ticker", "").upper() == ticker.upper():
            company = c
            break

    if not company:
        return f'''<!DOCTYPE html>
<html><head><title>Company Not Found</title></head>
<body><h1>Company {ticker} not found</h1><a href="/companies">Back to Companies</a></body>
</html>'''

    tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in company.get("tags", [])])

    # Detailed analysis section (for companies with has_data: true)
    detailed_analysis_section = ""
    if company.get("has_data", False) or company["ticker"] in ["ARWR", "KYMR"]:
        detailed_analysis_section = f'''
        <div class="detail-section" style="background: linear-gradient(135deg, #fef5f3 0%, #fff 100%); border-color: var(--accent);">
            <h2>Detailed Asset Analysis</h2>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">Deep-dive with pipeline analysis, clinical data, competitive positioning, and catalyst timeline.</p>
            <a href="/api/clinical/companies/{company["ticker"]}/html" style="display: inline-block; padding: 12px 24px; background: var(--accent); color: white; border-radius: 8px; font-weight: 600; text-decoration: none;">View Full Analysis &rarr;</a>
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

        {detailed_analysis_section}

        <a href="/companies" style="display: inline-block; margin-top: 24px; color: var(--accent);">← Back to Companies</a>
    </main>
    <footer class="footer">
        <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
    </footer>
</body>
</html>'''


# Note: Legacy generate_arwr_thesis function removed - ARWR now uses standard clinical asset rendering via /api/clinical/companies/ARWR/html
