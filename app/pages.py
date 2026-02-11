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

def _render_nav(active=""):
    """Canonical nav bar used on every page. Uses f-strings with triple double quotes
    for Python 3.11 compat (can be called from f'''...''' templates)."""
    def _cls(name):
        return 'class="active"' if active == name else ''
    return f"""
    <header class="header">
        <div class="header-inner">
            <a href="/" class="logo">Satya<span>Bio</span></a>
            <button class="hamburger" onclick="this.classList.toggle('open');document.querySelector('.nav-links').classList.toggle('open');" aria-label="Menu">
                <span></span><span></span><span></span>
            </button>
            <nav class="nav-links">
                <a href="/targets" {_cls("targets")}>Targets</a>
                <a href="/companies" {_cls("companies")}>Companies</a>
                <a href="/extract/" {_cls("extract")}>Extract</a>
                <a href="/about" {_cls("about")}>About</a>
                <a href="mailto:contact@satyabio.com?subject=Early%20Access%20Request" class="btn-primary nav-cta-mobile">Get Started</a>
            </nav>
            <div class="nav-cta">
                <a href="mailto:contact@satyabio.com?subject=Early%20Access%20Request" class="btn-primary">Get Started</a>
            </div>
        </div>
    </header>
    """


def _render_head(title, extra_styles="", extra_head=""):
    """Canonical <head> used on every page. Returns <!DOCTYPE html> through <body>.
    Uses f-strings with triple double quotes for Python 3.11 compat."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700;9..144,900&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    {extra_head}
    <style>
        :root {{
            --navy: #1a2b3c;
            --navy-light: #2d4a5e;
            --accent: #e07a5f;
            --accent-hover: #d06a4f;
            --accent-light: #fef5f3;
            --bg: #fdfcfa;
            --surface: #ffffff;
            --border: #e5e5e0;
            --text: #1a2b3c;
            --text-secondary: #5f6368;
            --text-muted: #9aa0a6;
            --highlight: #fef08a;
            --secondary: #a8d5e5;
            /* Legacy aliases for clinical.py compat */
            --primary: var(--navy);
            --primary-light: var(--navy-light);
            --coral: var(--accent);
            --catalyst-bg: #f5f5f0;
            --catalyst-border: #e0ddd8;
            --card-bg: var(--surface);
            --white: #ffffff;
            --gray-light: var(--bg);
            --gray-border: var(--border);
            --gray-text: var(--text-muted);
            --text-primary: var(--text-secondary);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'DM Sans', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        h1, h2, h3, h4 {{ font-family: 'Fraunces', serif; }}

        /* Nav */
        .header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 64px; position: sticky; top: 0; z-index: 100; }}
        .header-inner {{ max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }}
        .logo {{ font-family: 'Fraunces', serif; font-size: 1.25rem; font-weight: 700; color: var(--navy); text-decoration: none; }}
        .logo span {{ color: var(--accent); }}
        .nav-links {{ display: flex; gap: 28px; align-items: center; }}
        .nav-links a {{ color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; }}
        .nav-links a:hover, .nav-links a.active {{ color: var(--navy); }}
        .nav-cta {{ display: flex; gap: 12px; }}
        .btn-primary {{ padding: 8px 18px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 6px; font-size: 0.9rem; }}
        .btn-primary:hover {{ background: var(--accent-hover); }}

        /* Hamburger */
        .hamburger {{ display: none; background: none; border: none; cursor: pointer; padding: 4px; }}
        .hamburger span {{ display: block; width: 22px; height: 2px; background: var(--navy); margin: 5px 0; transition: 0.3s; }}
        .hamburger.open span:nth-child(1) {{ transform: rotate(45deg) translate(5px, 5px); }}
        .hamburger.open span:nth-child(2) {{ opacity: 0; }}
        .hamburger.open span:nth-child(3) {{ transform: rotate(-45deg) translate(5px, -5px); }}
        .nav-cta-mobile {{ display: none; }}

        /* Layout */
        .main {{ max-width: 1400px; margin: 0 auto; padding: 32px; }}
        .page-header {{ margin-bottom: 24px; }}
        .page-title {{ font-size: 1.75rem; font-weight: 700; color: var(--navy); margin-bottom: 8px; }}
        .page-subtitle {{ color: var(--text-secondary); font-size: 0.95rem; }}
        .footer {{ background: var(--navy); color: rgba(255,255,255,0.7); padding: 32px; text-align: center; margin-top: 64px; }}
        .footer p {{ font-size: 0.85rem; }}

        /* Mobile */
        @media (max-width: 768px) {{
            .hamburger {{ display: block; }}
            .nav-links {{ display: none; position: absolute; top: 64px; left: 0; right: 0; background: var(--surface); flex-direction: column; padding: 16px 32px; gap: 16px; border-bottom: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.08); z-index: 99; }}
            .nav-links.open {{ display: flex; }}
            .nav-cta {{ display: none; }}
            .nav-cta-mobile {{ display: inline-block !important; align-self: flex-start; }}
            .main {{ padding: 20px 16px; }}
            .header {{ padding: 0 16px; }}
        }}

        {extra_styles}
    </style>
</head>
<body>
"""


# DEPRECATED — use _render_head/_render_nav
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
                <a href="mailto:contact@satyabio.com?subject=Early%20Access%20Request" class="btn-primary">Get Started</a>
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
            --catalyst-bg: #f5f3f0;
            --catalyst-border: #e0ddd8;
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
        .catalyst-label { font-size: 0.65rem; font-weight: 600; color: #1B2838; text-transform: uppercase; margin-bottom: 2px; }
        .catalyst-text { font-size: 0.8rem; color: #374151; font-weight: 500; }

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

def generate_homepage():
    """Generate the homepage with hero, catalysts, deals, targets, value prop."""
    from datetime import date as _date

    today = _date.today()
    today_display = today.strftime("%b %d, %Y")

    # --- Load upcoming catalysts from ALL targets ---
    targets_dir = Path(__file__).parent.parent / "data" / "targets"
    upcoming_catalysts = []
    for cat_file in sorted(targets_dir.glob("*/catalysts.json")):
        with open(cat_file) as f:
            cat_data = json.load(f)
        target_name = cat_data.get("target", cat_file.parent.name)
        for c in cat_data.get("catalysts", []):
            date_str = c.get("date", "")
            parts = date_str.split("-")
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) >= 2 else 1
                day = int(parts[2]) if len(parts) >= 3 else 1
                c_date = _date(year, month, day)
            except (ValueError, IndexError):
                continue
            if c_date >= today:
                upcoming_catalysts.append({
                    "date": c_date,
                    "date_display": c.get("date_display", date_str),
                    "target": target_name,
                    "company": c.get("company", ""),
                    "asset": c.get("asset", ""),
                    "description": c.get("description", ""),
                })

    upcoming_catalysts.sort(key=lambda x: x["date"])
    upcoming_catalysts = upcoming_catalysts[:8]

    catalyst_rows = ""
    for c in upcoming_catalysts:
        catalyst_rows += f'''
        <tr>
            <td class="cal-date">{c["date_display"]}</td>
            <td class="cal-company">{c["company"]}</td>
            <td class="cal-desc">{c["description"][:100]}{"..." if len(c["description"]) > 100 else ""}</td>
        </tr>'''

    # --- Load targets for spotlight ---
    targets, categories = load_targets_index()
    full_page_targets = [t for t in targets if t.get("has_full_page")]

    target_cards = ""
    for t in full_page_targets[:7]:
        slug = t.get("slug", "")
        legacy_slug = t.get("legacy_slug", slug)
        name = t.get("name", slug)
        desc = t.get("description", "")[:80]
        cat = t.get("category", "")
        cat_info = categories.get(cat, {})
        cat_color = cat_info.get("color", "#6b7280")
        cat_name = cat_info.get("name", cat.title())
        hot = ' <span class="hot-badge">HOT</span>' if t.get("hot_target") else ""

        lead_html = ""
        leads = t.get("lead_companies", [])[:3]
        if leads:
            lead_html = '<div class="target-leads">' + " ".join([f'<span class="lead-pill">{l}</span>' for l in leads]) + '</div>'

        stats_html = ""
        if t.get("total_assets"):
            stats_html += f'<span class="target-stat">{t["total_assets"]} assets</span>'
        if t.get("phase_3_assets"):
            stats_html += f'<span class="target-stat">P3: {t["phase_3_assets"]}</span>'
        if t.get("approved_assets"):
            stats_html += f'<span class="target-stat">Approved: {t["approved_assets"]}</span>'

        target_cards += f'''
        <a href="/targets/{legacy_slug}" class="spotlight-card">
            <div class="spotlight-header">
                <span class="spotlight-cat" style="background:{cat_color}">{cat_name}</span>
                {hot}
            </div>
            <h3 class="spotlight-name">{name}</h3>
            <p class="spotlight-desc">{desc}</p>
            <div class="spotlight-stats">{stats_html}</div>
            {lead_html}
        </a>'''

    # --- Recent deals (hardcoded — curated) ---
    deals_html = """
        <tr><td class="deal-date">Feb 9</td><td class="deal-parties">Lilly / Orna</td><td class="deal-value">$2.4B</td><td class="deal-desc">In vivo CAR-T for autoimmune</td></tr>
        <tr><td class="deal-date">Jan 29</td><td class="deal-parties">Formation / CTFH</td><td class="deal-value">$500M</td><td class="deal-desc">miR-124 activator license</td></tr>
        <tr><td class="deal-date">Dec 2025</td><td class="deal-parties">Sanofi / Recludix</td><td class="deal-value">$1.3B</td><td class="deal-desc">STAT6 inhibitor REX-2787</td></tr>
        <tr><td class="deal-date">Oct 2025</td><td class="deal-parties">BMS / Orbital</td><td class="deal-value">$1.5B</td><td class="deal-desc">Circular RNA in vivo cell therapy</td></tr>
        <tr><td class="deal-date">Oct 2025</td><td class="deal-parties">Gilead / Interius</td><td class="deal-value">Undiscl.</td><td class="deal-desc">In vivo CAR-T</td></tr>
        <tr><td class="deal-date">Jun 2025</td><td class="deal-parties">AbbVie / Capstan</td><td class="deal-value">$2.1B</td><td class="deal-desc">LNP in vivo CAR-T</td></tr>
        <tr><td class="deal-date">Jan 2025</td><td class="deal-parties">Gilead / LEO</td><td class="deal-value">$1.7B</td><td class="deal-desc">Oral STAT6 degraders</td></tr>
        <tr><td class="deal-date">2025</td><td class="deal-parties">Roche / Zealand</td><td class="deal-value">$5.3B</td><td class="deal-desc">Petrelintide (amylin)</td></tr>
    """

    # --- Build search index for autocomplete ---
    all_companies = load_companies_from_index()
    search_index = []
    for c in all_companies:
        ta = c.get("therapeutic_area", "")
        ta_label = {"oncology": "Oncology", "immunology": "I&I", "metabolic": "Metabolic", "rare_disease": "Rare Disease", "mixed": "Multi-area"}.get(ta, ta.title() if ta else "")
        search_index.append({
            "t": "company",
            "ticker": c.get("ticker", ""),
            "name": c.get("name", ""),
            "ta": ta_label,
            "notes": (c.get("notes", "") or "")[:80],
            "url": f'/api/clinical/companies/{c.get("ticker", "")}/html',
            "hd": c.get("has_data", False),
        })
    for t in targets:
        slug = t.get("legacy_slug", t.get("slug", ""))
        search_index.append({
            "t": "target",
            "name": t.get("name", ""),
            "full_name": t.get("full_name", ""),
            "desc": (t.get("description", "") or t.get("tagline", ""))[:80],
            "cat": categories.get(t.get("category", ""), {}).get("name", t.get("category", "")),
            "url": f'/targets/{slug}',
            "slug": slug,
            "fp": t.get("has_full_page", False),
        })
    search_index_json = json.dumps(search_index, separators=(',', ':'))

    hp_structured_data = json.dumps({
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "Satya Bio",
      "url": "https://satyabio.com",
      "logo": "https://satyabio.com/static/satya-bio-icon.svg",
      "description": "Biotech intelligence platform for buy-side investment professionals. Competitive landscapes, catalyst tracking, and pipeline analytics across 181 public biotechs.",
      "foundingDate": "2025",
      "sameAs": [],
      "contactPoint": {
        "@type": "ContactPoint",
        "contactType": "sales",
        "url": "https://satyabio.com/#cta"
      }
    }, indent=2)
    hp_extra_head = f'<meta name="description" content="Satya Bio provides biotech competitive intelligence for institutional investors. Track 181 companies, 1000+ clinical assets, and competitive landscapes across drug targets. Built for hedge funds and pharma BD teams.">\n    <meta name="keywords" content="Satya Bio, biotech intelligence, competitive landscape, clinical data, hedge fund biotech, pharma analytics, drug target analysis, TL1A, GLP-1, biotech investment research">\n    <script type="application/ld+json">\n    {hp_structured_data}\n    </script>'

    hp_extra_styles = """
        /* Homepage additions */
        :root { --surface-alt: #f5f5f3; --border-light: #eeeeea; }

        /* ===== HERO ===== */
        .hero { padding: 80px 32px 64px; text-align: center; position: relative; overflow: visible; background: linear-gradient(180deg, var(--bg) 0%, #f0ede8 100%); }
        .hero-content { position: relative; z-index: 2; max-width: 800px; margin: 0 auto; }
        .hero h1 {
            font-size: 3.8rem;
            font-weight: 800;
            color: var(--navy);
            margin-bottom: 20px;
            letter-spacing: -0.04em;
            line-height: 1.08;
        }
        .hero-subtitle { color: var(--text-secondary); font-size: 1.2rem; margin-bottom: 36px; line-height: 1.6; max-width: 600px; margin-left: auto; margin-right: auto; }
        .hero-search { max-width: 540px; margin: 0 auto 20px; position: relative; }
        .hero-search input {
            width: 100%;
            padding: 18px 24px 18px 52px;
            border: 2px solid var(--border);
            border-radius: 14px;
            font-size: 1.05rem;
            font-family: inherit;
            background: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            outline: none;
            transition: all 0.3s;
        }
        .hero-search input:focus { border-color: var(--accent); box-shadow: 0 8px 32px rgba(0,0,0,0.1), 0 0 0 3px rgba(212,101,74,0.12); }
        .hero-search input::placeholder { color: var(--text-muted); }
        .hero-search-icon { position: absolute; left: 20px; top: 50%; transform: translateY(-50%); width: 20px; height: 20px; color: var(--text-muted); }
        .search-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid var(--border); border-top: none; border-radius: 0 0 14px 14px; box-shadow: 0 12px 40px rgba(0,0,0,0.12); max-height: 380px; overflow-y: auto; z-index: 200; display: none; }
        .search-dropdown.open { display: block; }
        .hero-search.dropdown-open input { border-radius: 14px 14px 0 0; }
        .search-result { display: flex; align-items: center; gap: 12px; padding: 12px 20px; text-decoration: none; color: var(--text); transition: background 0.15s; cursor: pointer; border-bottom: 1px solid var(--border-light); }
        .search-result:last-child { border-bottom: none; }
        .search-result:hover, .search-result.active { background: var(--accent-light); }
        .search-result-type { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
        .search-result-type.company { background: var(--navy); color: white; }
        .search-result-type.target { background: var(--accent); color: white; }
        .search-result-info { flex: 1; min-width: 0; }
        .search-result-name { font-weight: 600; font-size: 0.92rem; color: var(--text); }
        .search-result-name .ticker { color: var(--accent); font-weight: 700; margin-right: 4px; }
        .search-result-detail { font-size: 0.78rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .search-result-arrow { color: var(--text-muted); font-size: 0.8rem; flex-shrink: 0; }
        .search-no-results { padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.9rem; }
        .hero-meta { font-size: 0.82rem; color: var(--text-muted); margin-top: 16px; }
        .hero-meta span { background: rgba(212,101,74,0.1); color: var(--accent); padding: 3px 10px; border-radius: 10px; font-weight: 600; }

        /* Section headers */
        .section-wrap { max-width: 1200px; margin: 0 auto; padding: 0 32px; }
        .hp-section { padding: 56px 0; }
        .hp-section-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 24px; }
        .hp-section-title { font-size: 1.5rem; font-weight: 700; color: var(--navy); }
        .hp-section-link { color: var(--accent); text-decoration: none; font-size: 0.85rem; font-weight: 600; }
        .hp-section-link:hover { text-decoration: underline; }

        /* Two-column grid */
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
        .col-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
        .col-card-header { padding: 16px 20px; border-bottom: 1px solid var(--border-light); display: flex; justify-content: space-between; align-items: center; }
        .col-card-title { font-size: 1.15rem; font-weight: 700; color: var(--navy); }
        .col-card-badge { padding: 3px 10px; background: rgba(212,101,74,0.1); color: var(--accent); font-size: 0.7rem; font-weight: 700; border-radius: 10px; text-transform: uppercase; }

        /* Catalyst table */
        .cal-table { width: 100%; border-collapse: collapse; }
        .cal-table tr { border-bottom: 1px solid var(--border-light); }
        .cal-table tr:last-child { border-bottom: none; }
        .cal-table td { padding: 10px 16px; font-size: 0.82rem; vertical-align: top; }
        .cal-date { color: var(--accent); font-weight: 600; white-space: nowrap; width: 80px; }
        .cal-company { font-weight: 600; color: var(--navy); white-space: nowrap; width: 100px; }
        .cal-desc { color: var(--text-secondary); }

        /* Deals table */
        .deal-table { width: 100%; border-collapse: collapse; }
        .deal-table tr { border-bottom: 1px solid var(--border-light); }
        .deal-table tr:last-child { border-bottom: none; }
        .deal-table td { padding: 10px 16px; font-size: 0.82rem; vertical-align: top; }
        .deal-date { color: var(--text-muted); font-size: 0.78rem; white-space: nowrap; width: 75px; }
        .deal-parties { font-weight: 600; color: var(--navy); white-space: nowrap; }
        .deal-value { color: var(--accent); font-weight: 700; white-space: nowrap; width: 70px; }
        .deal-desc { color: var(--text-secondary); }

        /* Target spotlight */
        .spotlight-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; }
        .spotlight-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            text-decoration: none;
            color: inherit;
            transition: all 0.25s;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .spotlight-card:hover { border-color: var(--accent); box-shadow: 0 8px 24px rgba(0,0,0,0.08); transform: translateY(-3px); }
        .spotlight-header { display: flex; align-items: center; gap: 8px; }
        .spotlight-cat { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.65rem; font-weight: 700; color: white; text-transform: uppercase; letter-spacing: 0.5px; }
        .hot-badge { padding: 2px 7px; background: var(--accent); color: #ffffff; font-size: 0.6rem; font-weight: 700; border-radius: 4px; text-transform: uppercase; }
        .spotlight-name { font-size: 1.15rem; font-weight: 700; color: var(--navy); }
        .spotlight-desc { font-size: 0.82rem; color: var(--text-secondary); line-height: 1.4; }
        .spotlight-stats { display: flex; gap: 10px; flex-wrap: wrap; }
        .target-stat { font-size: 0.72rem; font-weight: 600; color: var(--navy); background: #f3f4f6; padding: 2px 8px; border-radius: 4px; }
        .target-leads { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
        .lead-pill { font-size: 0.68rem; color: var(--text-muted); background: var(--bg); border: 1px solid var(--border-light); padding: 2px 8px; border-radius: 10px; }

        /* Value prop */
        .value-strip { background: var(--navy); padding: 56px 32px; }
        .value-inner { max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px; text-align: center; }
        .value-stat-num { font-size: 2.5rem; font-weight: 800; color: white; letter-spacing: -0.02em; }
        .value-stat-label { font-size: 0.88rem; color: rgba(255,255,255,0.6); margin-top: 4px; }

        /* CTA */
        .cta-section { padding: 64px 32px; background: var(--surface-alt); }
        .cta-inner { max-width: 520px; margin: 0 auto; text-align: center; }
        .cta-inner h2 { font-size: 1.8rem; color: var(--navy); margin-bottom: 10px; }
        .cta-inner p { color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 28px; }
        .cta-form { display: flex; gap: 10px; max-width: 440px; margin: 0 auto 14px; }
        .cta-form input { flex: 1; padding: 13px 16px; border: 2px solid var(--border); border-radius: 10px; font-size: 0.95rem; font-family: inherit; outline: none; transition: border-color 0.2s; }
        .cta-form input:focus { border-color: var(--accent); }
        .cta-form button { padding: 13px 24px; background: var(--accent); color: white; border: none; border-radius: 10px; font-size: 0.95rem; font-weight: 700; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
        .cta-form button:hover { background: var(--accent-hover); }
        .cta-note { font-size: 0.82rem; color: var(--text-muted); }

        /* Mobile homepage */
        @media (max-width: 768px) {
            .hero { padding: 56px 20px 44px; }
            .hero h1 { font-size: 2.4rem; }
            .hero-subtitle { font-size: 1rem; margin-bottom: 28px; }
            .hero-search input { padding: 15px 18px 15px 46px; font-size: 0.95rem; }
            .two-col { grid-template-columns: 1fr; }
            .spotlight-grid { grid-template-columns: 1fr; }
            .value-inner { grid-template-columns: 1fr; gap: 24px; }
            .value-stat-num { font-size: 2rem; }
            .section-wrap { padding: 0 16px; }
            .hp-section { padding: 40px 0; }
            .cta-form { flex-direction: column; }
        }
    """

    return f'''{_render_head("Satya Bio | Biotech Intelligence for the Buy Side", hp_extra_styles, hp_extra_head)}
    {_render_nav()}

    <!-- HERO -->
    <section class="hero">
        <div class="hero-content">
            <h1>Biotech Intelligence<br>for the Buy Side</h1>
            <p class="hero-subtitle">Competitive landscapes, catalyst tracking, and pipeline analytics — built for investment professionals</p>
            <div class="hero-search" id="search-container">
                <svg class="hero-search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                <input type="text" id="hero-search-input" placeholder="Search targets, companies, or therapeutic areas..." autocomplete="off">
                <div class="search-dropdown" id="search-dropdown"></div>
            </div>
            <div class="hero-meta">Data updated <span>{today_display}</span></div>
        </div>
    </section>

    <!-- TWO-COLUMN: Catalyst Calendar + Deal Tracker -->
    <section class="hp-section">
        <div class="section-wrap">
            <div class="two-col">
                <div class="col-card">
                    <div class="col-card-header">
                        <span class="col-card-title">Upcoming Catalysts</span>
                        <span class="col-card-badge">Live</span>
                    </div>
                    <table class="cal-table">
                        {catalyst_rows}
                    </table>
                </div>
                <div class="col-card">
                    <div class="col-card-header">
                        <span class="col-card-title">Recent Deals</span>
                        <span class="col-card-badge">2025-26</span>
                    </div>
                    <table class="deal-table">
                        {deals_html}
                    </table>
                </div>
            </div>
        </div>
    </section>

    <!-- TARGET SPOTLIGHT -->
    <section class="hp-section" style="background:var(--surface)">
        <div class="section-wrap">
            <div class="hp-section-header">
                <span class="hp-section-title">Featured Target Landscapes</span>
                <a href="/targets" class="hp-section-link">View all targets &rarr;</a>
            </div>
            <div class="spotlight-grid">
                {target_cards}
            </div>
        </div>
    </section>

    <!-- VALUE PROP / AT A GLANCE -->
    <section class="value-strip">
        <div class="value-inner">
            <div>
                <div class="value-stat-num">181</div>
                <div class="value-stat-label">biotech companies</div>
            </div>
            <div>
                <div class="value-stat-num">1,000+</div>
                <div class="value-stat-label">assets tracked</div>
            </div>
            <div>
                <div class="value-stat-num">$30B+</div>
                <div class="value-stat-label">deal value tracked</div>
            </div>
        </div>
    </section>

    <!-- CTA -->
    <section class="cta-section" id="cta">
        <div class="cta-inner">
            <h2>Request Access</h2>
            <p>Currently in private beta with select funds</p>
            <form class="cta-form" id="subscribe-form" onsubmit="handleSubscribe(event)">
                <input type="email" id="subscribe-email" placeholder="work@fund.com" required>
                <button type="submit">Request Access</button>
            </form>
            <p class="cta-note" id="subscribe-note">We'll be in touch within 24 hours</p>
        </div>
    </section>

    <!-- FOOTER -->
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>

    <script>
    var _si = {search_index_json};
    var _dd = document.getElementById('search-dropdown');
    var _sc = document.getElementById('search-container');
    var _inp = document.getElementById('hero-search-input');
    var _activeIdx = -1;

    function doSearch() {{
        var q = _inp.value.trim().toLowerCase();
        if (q.length < 1) {{ closeDropdown(); return; }}
        var results = [];
        for (var i = 0; i < _si.length; i++) {{
            var item = _si[i];
            var haystack = '';
            if (item.t === 'company') {{
                haystack = (item.ticker + ' ' + item.name + ' ' + item.ta + ' ' + item.notes).toLowerCase();
            }} else {{
                haystack = (item.name + ' ' + item.full_name + ' ' + item.desc + ' ' + item.cat + ' ' + (item.slug || '')).toLowerCase();
            }}
            if (haystack.indexOf(q) !== -1) {{
                // Score: ticker/name exact start gets priority
                var score = 10;
                if (item.t === 'company') {{
                    if (item.ticker.toLowerCase().indexOf(q) === 0) score = 1;
                    else if (item.name.toLowerCase().indexOf(q) === 0) score = 2;
                    else if (item.ticker.toLowerCase().indexOf(q) !== -1) score = 3;
                    if (item.hd) score -= 0.5;
                }} else {{
                    if (item.name.toLowerCase().indexOf(q) === 0) score = 1;
                    else if (item.full_name.toLowerCase().indexOf(q) !== -1) score = 4;
                    if (item.fp) score -= 0.5;
                }}
                results.push({{item: item, score: score}});
            }}
        }}
        results.sort(function(a, b) {{ return a.score - b.score; }});
        results = results.slice(0, 8);
        _activeIdx = -1;

        if (results.length === 0) {{
            _dd.innerHTML = '<div class="search-no-results">No results for &ldquo;' + q.replace(/</g,'&lt;') + '&rdquo;</div>';
        }} else {{
            var html = '';
            for (var j = 0; j < results.length; j++) {{
                var r = results[j].item;
                if (r.t === 'company') {{
                    html += '<a href="' + r.url + '" class="search-result" data-idx="' + j + '">'
                        + '<span class="search-result-type company">Company</span>'
                        + '<div class="search-result-info">'
                        + '<div class="search-result-name"><span class="ticker">' + r.ticker + '</span> ' + r.name + '</div>'
                        + '<div class="search-result-detail">' + (r.ta || '') + (r.notes ? ' · ' + r.notes : '') + '</div>'
                        + '</div><span class="search-result-arrow">&rarr;</span></a>';
                }} else {{
                    html += '<a href="' + r.url + '" class="search-result" data-idx="' + j + '">'
                        + '<span class="search-result-type target">Target</span>'
                        + '<div class="search-result-info">'
                        + '<div class="search-result-name">' + r.name + (r.full_name && r.full_name !== r.name ? ' <span style="font-weight:400;color:var(--text-secondary)">(' + r.full_name + ')</span>' : '') + '</div>'
                        + '<div class="search-result-detail">' + (r.cat || '') + (r.desc ? ' · ' + r.desc : '') + '</div>'
                        + '</div><span class="search-result-arrow">&rarr;</span></a>';
                }}
            }}
            _dd.innerHTML = html;
        }}
        _dd.classList.add('open');
        _sc.classList.add('dropdown-open');
    }}

    function closeDropdown() {{
        _dd.classList.remove('open');
        _sc.classList.remove('dropdown-open');
        _activeIdx = -1;
    }}

    _inp.addEventListener('input', doSearch);
    _inp.addEventListener('keydown', function(e) {{
        var items = _dd.querySelectorAll('.search-result');
        if (!items.length) return;
        if (e.key === 'ArrowDown') {{
            e.preventDefault();
            _activeIdx = Math.min(_activeIdx + 1, items.length - 1);
            items.forEach(function(el, i) {{ el.classList.toggle('active', i === _activeIdx); }});
            items[_activeIdx].scrollIntoView({{block: 'nearest'}});
        }} else if (e.key === 'ArrowUp') {{
            e.preventDefault();
            _activeIdx = Math.max(_activeIdx - 1, 0);
            items.forEach(function(el, i) {{ el.classList.toggle('active', i === _activeIdx); }});
            items[_activeIdx].scrollIntoView({{block: 'nearest'}});
        }} else if (e.key === 'Enter') {{
            e.preventDefault();
            if (_activeIdx >= 0 && items[_activeIdx]) {{
                window.location.href = items[_activeIdx].getAttribute('href');
            }} else if (items.length > 0) {{
                window.location.href = items[0].getAttribute('href');
            }}
        }} else if (e.key === 'Escape') {{
            closeDropdown();
            _inp.blur();
        }}
    }});
    document.addEventListener('click', function(e) {{
        if (!_sc.contains(e.target)) closeDropdown();
    }});
    _inp.addEventListener('focus', function() {{
        if (_inp.value.trim().length >= 1) doSearch();
    }});
    function handleSubscribe(e) {{
        e.preventDefault();
        var email = document.getElementById('subscribe-email').value.trim();
        if (!email) return;
        fetch('/api/subscribe', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{email: email}})
        }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
            document.getElementById('subscribe-note').textContent = 'Subscribed! We\\'ll be in touch.';
            document.getElementById('subscribe-email').value = '';
        }}).catch(function() {{
            document.getElementById('subscribe-note').textContent = 'Something went wrong. Try again.';
        }});
    }}
    </script>
</body>
</html>'''


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

    companies_extra_head = '<meta name="description" content="Browse 181 biotech companies with clinical data, pipeline analysis, and investment thesis. Satya Bio tracks KYMR, ARGX, NUVL, EWTX and more.">'
    companies_styles = """
        /* Category nav / filter pills */
        .category-nav { position: sticky; top: 64px; background: var(--bg); padding: 16px 0; z-index: 50; border-bottom: 1px solid var(--border); margin-bottom: 32px; }
        .category-pills { display: flex; gap: 10px; flex-wrap: wrap; }
        .category-pill { padding: 8px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; font-size: 0.85rem; font-weight: 500; color: var(--text-secondary); cursor: pointer; text-decoration: none; }
        .category-pill:hover { border-color: var(--navy); color: var(--navy); }
        .category-pill.active { background: var(--navy); border-color: var(--navy); color: white; }

        /* Sections */
        .section { margin-bottom: 48px; scroll-margin-top: 140px; }
        .section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section-title { font-size: 1.25rem; font-weight: 700; color: var(--navy); }
        .section-count { background: var(--navy); color: white; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; }

        /* Card grid */
        .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }

        /* Company cards */
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
        .catalyst-label { font-size: 0.65rem; font-weight: 600; color: #1B2838; text-transform: uppercase; margin-bottom: 2px; }
        .catalyst-text { font-size: 0.8rem; color: #374151; font-weight: 500; }

        .tags-row { display: flex; flex-wrap: wrap; gap: 6px; }
        .tag { padding: 4px 10px; background: #f3f4f6; color: var(--text-secondary); font-size: 0.75rem; border-radius: 12px; }

        .phase-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: #e5e7eb; color: #374151; }
        .ticker-small { color: #6b7280; font-size: 0.8rem; }
        .notes-text { font-size: 0.8rem; color: var(--text-secondary); }

        @media (max-width: 768px) {
            .cards-grid { grid-template-columns: 1fr; }
        }

        /* Search */
        .search-box { margin-bottom: 16px; }
        .search-input { width: 100%; max-width: 500px; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; }
        .search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }
        .results-count { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px; }
        .data-badge { background: var(--navy); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; margin-left: 8px; }
        .priority-badge { padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: #e5e7eb; color: #374151; }
        .priority-badge.priority-high { background: var(--navy); color: white; }
        .priority-badge.priority-medium { background: #e5e7eb; color: #374151; }
        .priority-badge.priority-low { background: #f3f4f6; color: #6b7280; }
        .locked-card { display: block; position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; cursor: pointer; transition: all 0.2s; overflow: hidden; }
        .locked-card:hover { border-color: var(--accent); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .locked-blur { filter: blur(4px); pointer-events: none; user-select: none; }
        .locked-overlay { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; background: rgba(255,255,255,0.6); color: var(--navy); font-weight: 600; font-size: 0.85rem; }
        .locked-overlay svg { opacity: 0.7; }
        .gate-backdrop { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }
        .gate-backdrop.visible { display: flex; }
        .gate-modal { background: white; border-radius: 16px; padding: 40px; max-width: 440px; width: 90%; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.15); position: relative; }
        .gate-modal h2 { font-size: 1.35rem; font-weight: 700; color: var(--navy); margin-bottom: 8px; line-height: 1.3; }
        .gate-modal .gate-sub { color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 24px; }
        .gate-modal input[type="email"] { width: 100%; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; margin-bottom: 12px; }
        .gate-modal input[type="email"]:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }
        .gate-modal .gate-btn { width: 100%; padding: 14px; background: var(--accent); color: white; font-weight: 700; font-size: 1rem; border: none; border-radius: 10px; cursor: pointer; transition: background 0.2s; }
        .gate-modal .gate-btn:hover { background: var(--accent-hover); }
        .gate-modal .gate-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .gate-modal .gate-fine { color: var(--text-muted); font-size: 0.8rem; margin-top: 16px; }
        .gate-modal .gate-close { position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 1.25rem; color: var(--text-muted); cursor: pointer; }
        .gate-modal .gate-error { color: #D4654A; font-size: 0.85rem; margin-top: 8px; display: none; }
        .gate-modal .gate-success { color: #1B2838; font-size: 0.85rem; margin-top: 8px; display: none; }
        body.unlocked .locked-card { cursor: default; }
        body.unlocked .locked-blur { filter: none; pointer-events: auto; user-select: auto; }
        body.unlocked .locked-overlay { display: none; }
    """
    return f'''{_render_head("Biotech Companies | Satya Bio - 181 Companies Tracked", companies_styles, companies_extra_head)}
    {_render_nav("companies")}
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
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
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

    targets_styles = """
        .targets-layout { display: grid; grid-template-columns: 240px 1fr; gap: 32px; }
        @media (max-width: 900px) { .targets-layout { grid-template-columns: 1fr; } }
        .filters-sidebar { position: sticky; top: 80px; height: fit-content; }
        .filter-section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .filter-section h4 { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 12px; }
        .filter-option { display: flex; align-items: center; gap: 8px; padding: 8px 0; cursor: pointer; font-size: 0.9rem; color: var(--text-secondary); }
        .filter-option:hover { color: var(--navy); }
        .filter-option input { display: none; }
        .filter-dot { width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--border); }
        .filter-option.active .filter-dot { background: var(--accent); border-color: var(--accent); }
        .filter-option.active { color: var(--navy); font-weight: 500; }
        .search-box { margin-bottom: 24px; }
        .search-input { width: 100%; padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 0.95rem; outline: none; }
        .search-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(224,122,95,0.1); }
        .targets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
        .targets-meta { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 16px; }
        .target-card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; transition: all 0.2s; }
        .target-card:hover { border-color: var(--accent); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
        .target-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
        .target-name { font-size: 1.1rem; font-weight: 700; color: var(--navy); }
        .area-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 500; background: transparent; border: 1px solid #d1d5db; color: #6b7280; }
        .market-status { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; background: #1a2b3c; color: #ffffff; }
        .competitor-section { margin-bottom: 12px; }
        .competitor-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.85rem; }
        .competitor-row:last-child { border-bottom: none; }
        .competitor-label { color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; min-width: 90px; }
        .competitor-info { display: flex; align-items: center; gap: 8px; flex: 1; justify-content: flex-end; text-align: right; }
        .competitor-text { color: var(--text-secondary); }
        .competitor-text .company { color: var(--navy); font-weight: 500; }
        .competitor-text .ticker { color: #6b7280; font-size: 0.85em; }
        .stage-pill { padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; background: #e5e7eb; color: #374151; }
        .target-footer { padding-top: 12px; }
        .companies-count { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px; }
        .target-desc { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 10px; }
        .view-btn { display: inline-block; color: var(--accent); font-weight: 600; font-size: 0.85rem; text-decoration: none; }
        .view-btn:hover { text-decoration: underline; }
    """
    targets_extra_head = '<meta name="description" content="Competitive landscapes for hot biotech drug targets including TL1A, GLP-1, KRAS, B7-H3. Compare assets, clinical data, and catalysts. By Satya Bio.">'
    return f'''{_render_head("Drug Target Landscapes | Satya Bio", targets_styles, targets_extra_head)}
    {_render_nav("targets")}
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
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
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
        "oncology": {"bg": "#f0eeeb", "color": "#1B2838", "label": "Oncology"},
        "immunology": {"bg": "#f0eeeb", "color": "#1B2838", "label": "I&I"},
        "metabolic": {"bg": "#f0eeeb", "color": "#1B2838", "label": "Metabolic"},
        "cardiovascular": {"bg": "#f0eeeb", "color": "#1B2838", "label": "Cardiovascular"},
        "rare": {"bg": "#f0eeeb", "color": "#1B2838", "label": "Rare Disease"},
        "neuro": {"bg": "#f0eeeb", "color": "#1B2838", "label": "Neuro"},
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

    detail_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white; padding: 48px 32px; margin: -32px -32px 32px; border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header .subtitle { opacity: 0.85; font-size: 1rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.7; max-width: 700px; font-size: 0.95rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }
        .category-badge { display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; margin-bottom: 12px; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .assets-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        .assets-table th { background: var(--navy); color: white; padding: 12px; text-align: left; }
        .assets-table td { padding: 12px; border-bottom: 1px solid var(--border); }
        .assets-table tr:hover { background: var(--bg); }
        .phase-badge { padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; color: white; }
        .company-link { color: var(--navy); text-decoration: none; font-weight: 500; }
        .company-link:hover { color: var(--accent); }
        .ticker { color: var(--text-muted); font-size: 0.8rem; }
        .deal-value { color: var(--navy); font-weight: 600; }
        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; margin-bottom: 16px; }
        .bear-box h3 { color: #1a2b3c; margin-bottom: 16px; }
        .thesis-list { list-style: none; padding: 0; margin: 0; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; }
        .thesis-list li:last-child { border-bottom: none; }
        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-bottom: 24px; font-weight: 500; }
    """
    detail_title = f"{target_name} Target Landscape | Satya Bio Analysis"
    return f'''{_render_head(detail_title, detail_styles)}
    {_render_nav("targets")}
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
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''

def generate_about_page():
    about_styles = """
        .about-content { max-width: 700px; margin: 0 auto; }
        .about-content h1 { font-size: 2.5rem; margin-bottom: 24px; }
        .about-content p { font-size: 1.1rem; line-height: 1.8; margin-bottom: 24px; color: var(--text-secondary); }
        .about-content h2 { font-size: 1.5rem; margin: 48px 0 16px; color: var(--navy); }
        .feature-list { list-style: none; padding: 0; }
        .feature-list li { padding: 12px 0; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
        .feature-list li::before { content: "\\2713"; color: var(--accent); font-weight: bold; }
    """
    return f'''{_render_head("About | Satya Bio", about_styles)}
    {_render_nav("about")}
    <main class="main">
        <div class="about-content">
            <h1>Biotech Intelligence for the Buy Side</h1>
            <p>Satya Bio provides institutional investors with comprehensive biotech competitive intelligence. We track 181 public biotech companies, monitor catalyst timelines, and analyze competitive landscapes across therapeutic areas.</p>

            <h2>What We Track</h2>
            <ul class="feature-list">
                <li>Pipeline data for 181 biotech companies</li>
                <li>Real-time catalyst monitoring and alerts</li>
                <li>Competitive landscapes for hot targets (GLP-1, TL1A, KRAS, etc.)</li>
                <li>Key Opinion Leader identification via PubMed</li>
                <li>SEC filing analysis and ownership tracking</li>
                <li>Clinical trial data from ClinicalTrials.gov</li>
            </ul>

            <h2>Contact</h2>
            <p>For early access or inquiries: <a href="mailto:contact@satyabio.com" style="color: var(--accent);">contact@satyabio.com</a></p>
        </div>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''

def generate_glp1_report(admin: bool = False):
    """Generate the GLP-1 / Obesity competitive landscape report."""

    # Approved drugs data — weight loss is placebo-adjusted from pivotal trials
    approved_drugs = [
        {"name": "Wegovy", "generic": "semaglutide 2.4mg", "company": "Novo Nordisk", "mechanism": "GLP-1 mono-agonist", "route": "SC weekly", "approval": "2021", "indication": "Obesity", "weight_loss": "~12.4%", "trial": "STEP 1", "revenue_2024": "$6.2B"},
        {"name": "Zepbound", "generic": "tirzepatide 15mg", "company": "Eli Lilly", "mechanism": "GLP-1/GIP dual agonist", "route": "SC weekly", "approval": "2023", "indication": "Obesity", "weight_loss": "~18.4%", "trial": "SURMOUNT-1", "revenue_2024": "$1.2B"},
        {"name": "Ozempic", "generic": "semaglutide 1mg", "company": "Novo Nordisk", "mechanism": "GLP-1 mono-agonist", "route": "SC weekly", "approval": "2017", "indication": "T2D (off-label obesity)", "weight_loss": "~10%", "trial": "SUSTAIN", "revenue_2024": "$18.4B"},
        {"name": "Mounjaro", "generic": "tirzepatide 15mg", "company": "Eli Lilly", "mechanism": "GLP-1/GIP dual agonist", "route": "SC weekly", "approval": "2022", "indication": "T2D", "weight_loss": "~15%", "trial": "SURPASS", "revenue_2024": "$7.4B"},
        {"name": "Saxenda", "generic": "liraglutide 3mg", "company": "Novo Nordisk", "mechanism": "GLP-1 mono-agonist", "route": "SC daily", "approval": "2014", "indication": "Obesity", "weight_loss": "~5.4%", "trial": "SCALE", "revenue_2024": "$0.8B"},
        {"name": "Rybelsus", "generic": "semaglutide 14mg", "company": "Novo Nordisk", "mechanism": "GLP-1 mono-agonist", "route": "Oral daily", "approval": "2019", "indication": "T2D", "weight_loss": "~7%", "trial": "PIONEER", "revenue_2024": "$2.8B"},
    ]

    # Pipeline drugs data — mechanism names only, no Gen labels
    pipeline_drugs = [
        {"asset": "Retatrutide", "company": "Eli Lilly", "ticker": "LLY", "mechanism": "GLP-1/GIP/GCG triple agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~22.1%*", "trial": "Phase 2", "catalyst": "FDA submission Q1 2026"},
        {"asset": "MariTide (maridebart cafraglutide)", "company": "Amgen", "ticker": "AMGN", "mechanism": "GIP antagonist / GLP-1 agonist", "phase": "Phase 2 \u2192 3", "route": "SC monthly", "weight_loss": "~20%*", "trial": "Phase 2, 52 wks", "catalyst": "Ph3 data H1 2026"},
        {"asset": "CagriSema", "company": "Novo Nordisk", "ticker": "NVO", "mechanism": "GLP-1 + amylin combination", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~15-17%\u2020", "trial": "REDEFINE-1", "catalyst": "FDA submission Q2 2026"},
        {"asset": "Survodutide", "company": "Boehringer / Zealand", "ticker": "Private", "mechanism": "GLP-1/GCG dual agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~16%*", "trial": "Phase 2", "catalyst": "Ph3 SYNCHRONIZE-2 H2 2026"},
        {"asset": "Orforglipron", "company": "Eli Lilly", "ticker": "LLY", "mechanism": "GLP-1 mono-agonist (oral small molecule)", "phase": "Phase 3", "route": "Oral daily", "weight_loss": "~14.7%*", "trial": "Phase 2, 36 wks", "catalyst": "FDA filing Q2 2026"},
        {"asset": "VK2735 (SC)", "company": "Viking Therapeutics", "ticker": "VKTX", "mechanism": "GLP-1/GIP dual agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "14.7% (13 wks)", "trial": "Phase 2", "catalyst": "Ph3 VENTURE interim Q1 2026"},
        {"asset": "VK2735 (Oral)", "company": "Viking Therapeutics", "ticker": "VKTX", "mechanism": "GLP-1/GIP dual agonist", "phase": "Phase 2b", "route": "Oral daily", "weight_loss": "8.2% (28 days)", "trial": "Phase 1b", "catalyst": "Ph2b data H1 2026"},
        {"asset": "Pemvidutide", "company": "Altimmune", "ticker": "ALT", "mechanism": "GLP-1/GCG dual agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~15.6%", "trial": "Phase 2, 48 wks", "catalyst": "Ph3 data 2026"},
        {"asset": "Ecnoglutide", "company": "Sciwind Biosciences", "ticker": "Private", "mechanism": "GLP-1 mono-agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "~15%", "trial": "Phase 2", "catalyst": "China NDA 2026"},
        {"asset": "HRS9531", "company": "Jiangsu Hengrui", "ticker": "600276.SS", "mechanism": "GLP-1/GIP dual agonist", "phase": "Phase 3", "route": "SC weekly", "weight_loss": "16.8% (24 wks)", "trial": "Phase 2", "catalyst": "China NDA H2 2026"},
        {"asset": "Petrelintide", "company": "Novo Nordisk", "ticker": "NVO", "mechanism": "Long-acting amylin analog", "phase": "Phase 2", "route": "SC weekly", "weight_loss": "~10%", "trial": "Phase 1/2", "catalyst": "Ph2 combo data 2026"},
        {"asset": "Amycretin", "company": "Novo Nordisk", "ticker": "NVO", "mechanism": "GLP-1 + amylin dual agonist (oral)", "phase": "Phase 2", "route": "Oral daily", "weight_loss": "~13% (12 wks)", "trial": "Phase 1", "catalyst": "Ph2 data 2027"},
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
            <td><strong style="color: var(--accent);">{drug["weight_loss"]}</strong><br><span style="color: var(--text-muted); font-size: 0.75rem;">{drug["trial"]}</span></td>
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
            <td><strong>{drug["weight_loss"]}</strong><br><span style="color: var(--text-muted); font-size: 0.75rem;">{drug["trial"]}</span></td>
            <td>{drug["catalyst"]}</td>
        </tr>
        '''

    # Catalyst section from shared system
    catalyst_html = render_catalyst_section("glp1-obesity", admin=admin)

    glp1_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section h3 { color: var(--navy); font-size: 1.1rem; margin: 24px 0 16px; }

        .market-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 24px 0; }
        .market-stat { background: var(--bg); padding: 24px; border-radius: 12px; text-align: center; }
        .market-stat .value { font-size: 2rem; font-weight: 700; color: var(--accent); }
        .market-stat .label { color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; }

        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th { background: var(--navy); color: white; padding: 14px 12px; text-align: left; font-weight: 600; }
        td { padding: 14px 12px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }
        .table-footnote { font-size: 0.8rem; color: var(--text-secondary); margin-top: 12px; font-style: italic; line-height: 1.5; }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .bio-box { background: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box h3 { color: #1e40af; margin-top: 0; }
        .bio-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }
        .bio-point { padding: 8px 0; border-bottom: 1px solid #dbeafe; font-size: 0.9rem; color: #374151; }
        .bio-point:last-child { border-bottom: none; }
        .bio-point strong { color: #1e40af; }

        .pipeline-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 6px 0; font-size: 0.85rem; }
        .pipeline-flow .arrow { color: var(--text-secondary); }
        .pipeline-flow .drug { background: var(--bg); padding: 3px 10px; border-radius: 6px; border: 1px solid var(--border); }
        .pipeline-flow .drug.approved { background: #f0eeeb; border-color: #1B2838; }
        .pipeline-flow .drug.filing { background: #f5f3f0; border-color: #e0ddd8; }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }
        .catalyst-content strong { color: var(--navy); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }

        .source-list { list-style: decimal; padding-left: 24px; font-size: 0.85rem; color: var(--text-secondary); line-height: 2; }
        .source-list a { color: var(--accent); }
    """

    return f'''{_render_head("GLP-1 / Obesity Competitive Landscape | Satya Bio", glp1_styles)}
    {_render_nav("targets")}
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
                <div class="market-stat"><div class="value">~12-22%</div><div class="label">Placebo-Adj. WL Range</div></div>
            </div>
            <p style="color: var(--text-secondary); line-height: 1.7;">
                The GLP-1 receptor agonist class has transformed obesity treatment, achieving weight loss previously only possible with bariatric surgery.
                The market is dominated by <strong>Novo Nordisk</strong> (Wegovy, Ozempic) and <strong>Eli Lilly</strong> (Zepbound, Mounjaro), with combined 2024 revenues exceeding $35B.
                Supply constraints are easing but demand continues to accelerate. Key differentiators include: oral vs. injectable, dosing frequency,
                weight loss efficacy, GI tolerability, and cardiometabolic benefits beyond weight.
            </p>

            <h3>Key Market Dynamics</h3>
            <ul style="color: var(--text-secondary); line-height: 1.9; padding-left: 20px;">
                <li><strong>Supply catch-up:</strong> Novo and Lilly investing $10B+ in capacity expansion; compounding pharmacies filling short-term gap</li>
                <li><strong>Medicare coverage:</strong> Treat and Reduce Obesity Act enacted Jan 2025 — Part D now covers anti-obesity meds, adding ~15-20M addressable lives</li>
                <li><strong>Beyond obesity:</strong> CV outcomes (SELECT), MASH, CKD, sleep apnea, HFpEF expanding addressable market 2-3x</li>
                <li><strong>Oral competition:</strong> Orforglipron and oral semaglutide 50mg could expand market by removing injection barrier</li>
                <li><strong>Monthly dosing:</strong> Amgen's MariTide (monthly SC) could improve adherence vs. weekly injections</li>
            </ul>
        </div>

        <!-- GIP Agonism vs Antagonism Biology Box -->
        <div class="section">
            <h2>GIP Agonism vs. Antagonism: The Unresolved Paradox</h2>
            <div class="bio-box">
                <p>A central puzzle in incretin biology: <strong>tirzepatide</strong> (a GIP receptor <em>agonist</em>) and <strong>MariTide</strong> (a GIP receptor <em>antagonist</em>) both produce &gt;15% placebo-adjusted weight loss.
                This paradox has major implications for target selection and mechanism-based drug design.</p>
                <div style="margin-top: 16px;">
                    <div class="bio-point"><strong>The paradox:</strong> GIP agonism (tirzepatide ~18.4% WL) and GIP antagonism (MariTide ~20% WL) both work through incretin pathways, yet have opposite effects on the GIP receptor.</div>
                    <div class="bio-point"><strong>Functional selectivity:</strong> GIP agonists may engage biased signaling cascades distinct from those blocked by antagonists, resulting in convergent metabolic outcomes through different intracellular pathways.</div>
                    <div class="bio-point"><strong>Receptor desensitization:</strong> Chronic GIP agonism may functionally desensitize the receptor, making sustained agonism and antagonism phenotypically similar over time.</div>
                    <div class="bio-point"><strong>Tissue-specific effects:</strong> GIP agonism and antagonism may have different effects in adipose tissue, pancreas, and CNS — net weight loss may result from different tissue contributions.</div>
                    <div class="bio-point"><strong>Investment implication:</strong> The paradox means the GLP-1 component may be the primary driver of weight loss in both cases. If so, pure GLP-1 agonists (semaglutide, orforglipron) may be closer to ceiling efficacy than assumed.</div>
                </div>
                <p style="font-size: 0.8rem; margin-top: 12px; color: #6b7280;">Ref: Lu et al., <em>Cell Metabolism</em> 2024; Killion et al., <em>Nature Metabolism</em> 2024</p>
            </div>
        </div>

        <!-- Approved Drugs -->
        <div class="section">
            <h2>Approved Drugs</h2>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Drug</th>
                        <th>Company</th>
                        <th>Mechanism</th>
                        <th>Route</th>
                        <th>Placebo-Adj. WL</th>
                        <th>2024 Revenue</th>
                    </tr>
                </thead>
                <tbody>
                    {approved_rows}
                </tbody>
            </table>
            </div>
            <p class="table-footnote">All weight loss figures are placebo-adjusted from pivotal trials at highest approved dose. Cross-trial comparisons are directionally informative only &mdash; populations, trial designs, and durations differ.</p>
        </div>

        <!-- Pipeline -->
        <div class="section">
            <h2>Pipeline Assets</h2>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Company</th>
                        <th>Mechanism</th>
                        <th>Phase</th>
                        <th>Placebo-Adj. WL</th>
                        <th>Next Catalyst</th>
                    </tr>
                </thead>
                <tbody>
                    {pipeline_rows}
                </tbody>
            </table>
            </div>
            <p class="table-footnote">* Placebo-adjusted estimate from Phase 2 data. Phase 3 may differ. &dagger; CagriSema: ~15-17% placebo-adjusted; REDEFINE-1 primary results were nuanced &mdash; strong absolute WL (~22.7%) but co-primary vs. semaglutide endpoint was not met. Cross-trial comparisons are directionally informative only.</p>
        </div>

        <!-- Safety Comparison -->
        <div class="section">
            <h2>Safety Comparison</h2>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Drug</th>
                        <th>Nausea</th>
                        <th>Vomiting</th>
                        <th>Discontinuation (GI)</th>
                        <th>Serious AE of Note</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Semaglutide 2.4mg</strong></td>
                        <td>~44%</td>
                        <td>~24%</td>
                        <td>~7%</td>
                        <td>Gallbladder, pancreatitis (rare)</td>
                    </tr>
                    <tr>
                        <td><strong>Tirzepatide 15mg</strong></td>
                        <td>~31%</td>
                        <td>~12%</td>
                        <td>~5%</td>
                        <td>Lower GI AEs than sema at similar WL</td>
                    </tr>
                    <tr>
                        <td><strong>Retatrutide 12mg</strong></td>
                        <td>~45%</td>
                        <td>~23%</td>
                        <td>~6%</td>
                        <td>Phase 2 only; Phase 3 will clarify</td>
                    </tr>
                    <tr>
                        <td><strong>Orforglipron</strong></td>
                        <td>~35-40%</td>
                        <td>~15-20%</td>
                        <td>TBD</td>
                        <td>Oral &mdash; GI profile may differ</td>
                    </tr>
                    <tr>
                        <td><strong>MariTide</strong></td>
                        <td>~20-25%</td>
                        <td>TBD</td>
                        <td>Low</td>
                        <td>Monthly dosing may reduce GI peaks</td>
                    </tr>
                </tbody>
            </table>
            </div>
            <p class="table-footnote">All GLP-1 RAs carry class labeling for thyroid C-cell tumors (rodent signal), pancreatitis, and gallbladder events. Rates are approximate from published trial data and may vary by dose titration schedule.</p>
        </div>

        <!-- Weight Regain & Durability -->
        <div class="section">
            <h2>Weight Regain &amp; Durability</h2>
            <div class="bio-box" style="background: #f5f3f0; border-color: #e0ddd8;">
                <h3 style="color: #1B2838;">THE key question for revenue modeling</h3>
                <p style="color: #374151;">If patients must stay on therapy permanently, peak sales estimates roughly double. Weight regain data is therefore the most commercially significant dataset in the class.</p>
            </div>
            <div style="margin-top: 16px;">
                <div class="bio-point"><strong>STEP 1 extension data:</strong> ~2/3 of weight lost was regained within 1 year of stopping semaglutide 2.4mg. Cardiometabolic improvements also reversed.</div>
                <div class="bio-point"><strong>Implication:</strong> Anti-obesity medications are likely lifetime therapies for most patients &mdash; analogous to statins for cardiovascular risk. This transforms revenue models from episodic to chronic.</div>
                <div class="bio-point"><strong>MariTide differentiation:</strong> Phase 2 data suggested more sustained weight loss after discontinuation vs. GLP-1 RAs. If confirmed in Phase 3, this would be a major differentiator &mdash; but could also mean shorter treatment duration (bear case for Amgen revenue).</div>
                <div class="bio-point"><strong>Key upcoming data:</strong> TRIUMPH-6 (retatrutide maintenance study) and REDEFINE maintenance arms will be critical for modeling treatment duration and lifetime revenue per patient.</div>
                <div class="bio-point"><strong>Muscle loss concern:</strong> GLP-1 RA-induced weight loss includes ~25-40% lean mass. Combination with bimagrumab (anti-activin type II receptor) or exercise programs may be needed for long-term health outcomes.</div>
            </div>
        </div>

        <!-- Beyond Obesity: Expanding Indications -->
        <div class="section">
            <h2>Beyond Obesity: Expanding Indications</h2>
            <p style="color: var(--text-secondary); line-height: 1.7; margin-bottom: 20px;">
                GLP-1 RAs are showing broad cardiometabolic benefits that extend far beyond weight loss. These indication expansions could multiply the addressable market 3-5x.
            </p>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Indication</th>
                        <th>Key Trial</th>
                        <th>Drug</th>
                        <th>Result</th>
                        <th>Market Impact</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>CV risk reduction</strong></td>
                        <td>SELECT</td>
                        <td>Semaglutide 2.4mg</td>
                        <td>20% MACE reduction</td>
                        <td>Label expansion; massive payer argument for coverage</td>
                    </tr>
                    <tr>
                        <td><strong>CKD</strong></td>
                        <td>FLOW</td>
                        <td>Semaglutide</td>
                        <td>24% reduction in kidney disease progression</td>
                        <td>New indication filed</td>
                    </tr>
                    <tr>
                        <td><strong>MASH/NASH</strong></td>
                        <td>Phase 2/3</td>
                        <td>Survodutide, semaglutide, retatrutide</td>
                        <td>62% MASH improvement (survodutide Ph2)</td>
                        <td>$30B+ market; GLP-1/GCG duals may have advantage</td>
                    </tr>
                    <tr>
                        <td><strong>Sleep apnea</strong></td>
                        <td>SURMOUNT-OSA</td>
                        <td>Tirzepatide</td>
                        <td>~60% AHI reduction</td>
                        <td>Label expansion for Zepbound</td>
                    </tr>
                    <tr>
                        <td><strong>Heart failure</strong></td>
                        <td>STEP-HFpEF</td>
                        <td>Semaglutide</td>
                        <td>Improved symptoms, exercise capacity</td>
                        <td>HFpEF is huge unmet need (~3M US patients)</td>
                    </tr>
                    <tr>
                        <td><strong>Alzheimer's</strong></td>
                        <td>EVOKE / EVOKE+</td>
                        <td>Oral semaglutide</td>
                        <td>Phase 3 ongoing</td>
                        <td>High-risk, high-reward; neuroprotective hypothesis</td>
                    </tr>
                    <tr>
                        <td><strong>Addiction</strong></td>
                        <td>Observational</td>
                        <td>GLP-1 class</td>
                        <td>Reduced alcohol, nicotine use signals</td>
                        <td>Very early; mostly observational and preclinical</td>
                    </tr>
                </tbody>
            </table>
            </div>
        </div>

        <!-- Payer & Market Access -->
        <div class="section">
            <h2>Payer &amp; Market Access</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px;">
                <div style="background: var(--bg); padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent);">~15-20M</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">New US lives via Medicare Part D (2025)</div>
                </div>
                <div style="background: var(--bg); padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent);">~$1,350/mo</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">Wegovy list price</div>
                </div>
                <div style="background: var(--bg); padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent);">~$1,060/mo</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">Zepbound list price</div>
                </div>
                <div style="background: var(--bg); padding: 20px; border-radius: 12px; text-align: center;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent);">2030+</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">Semaglutide generics expected</div>
                </div>
            </div>
            <ul style="color: var(--text-secondary); line-height: 1.9; padding-left: 20px;">
                <li><strong>Medicare Part D:</strong> Treat and Reduce Obesity Act enacted Jan 2025 — obesity coverage began, expanding addressable US population by ~15-20M lives</li>
                <li><strong>Net price erosion:</strong> Significant rebating and PBM negotiations are compressing net prices well below list. Net-to-gross for Wegovy estimated at ~50-60%.</li>
                <li><strong>Compounding threat:</strong> Compounding pharmacies offering semaglutide at ~$200-400/month. FDA enforcement actions ongoing; Novo litigation active.</li>
                <li><strong>Generic liraglutide:</strong> Available since 2024 at ~$300/month for Saxenda equivalent. Limited market impact given efficacy gap vs. semaglutide.</li>
                <li><strong>Employer coverage:</strong> Growing rapidly — large self-insured employers adding GLP-1 coverage due to CV benefit data (SELECT trial) and productivity arguments.</li>
                <li><strong>Global expansion:</strong> EU, UK, Japan approvals creating second wave of growth. China market nascent but high-potential via domestic players (Hengrui, Innovent).</li>
            </ul>
        </div>

        <!-- Company Pipeline Overview -->
        <div class="section">
            <h2>Company Pipeline Overview</h2>

            <h3>Novo Nordisk (NVO)</h3>
            <div class="pipeline-flow">
                <span class="drug approved">Wegovy (approved)</span>
                <span class="arrow">&rarr;</span>
                <span class="drug filing">Oral sema 50mg (filing)</span>
                <span class="arrow">&rarr;</span>
                <span class="drug filing">CagriSema (Phase 3)</span>
                <span class="arrow">&rarr;</span>
                <span class="drug">Amycretin (Phase 2)</span>
            </div>

            <h3>Eli Lilly (LLY)</h3>
            <div class="pipeline-flow">
                <span class="drug approved">Zepbound (approved)</span>
                <span class="arrow">&rarr;</span>
                <span class="drug filing">Orforglipron (filing 2026)</span>
                <span class="arrow">&rarr;</span>
                <span class="drug filing">Retatrutide (Phase 3)</span>
                <span class="arrow">&rarr;</span>
                <span class="drug">Bimagrumab combo (Phase 2)</span>
            </div>

            <h3>Amgen (AMGN)</h3>
            <div class="pipeline-flow">
                <span class="drug filing">MariTide (Phase 2 &rarr; Phase 3)</span>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">GIP antagonist / GLP-1 agonist bispecific. Monthly SC dosing. ~20% WL at 52 weeks.</p>

            <h3>Viking Therapeutics (VKTX)</h3>
            <div class="pipeline-flow">
                <span class="drug filing">VK2735 SC (Phase 3)</span>
                <span class="arrow">+</span>
                <span class="drug">VK2735 Oral (Phase 2b)</span>
            </div>

            <h3>Structure Therapeutics (GPCR)</h3>
            <div class="pipeline-flow">
                <span class="drug">GSBR-1290 oral GLP-1 (Phase 2)</span>
            </div>

            <h3>Altimmune (ALT)</h3>
            <div class="pipeline-flow">
                <span class="drug filing">Pemvidutide (Phase 3)</span>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">GLP-1/GCG dual agonist. Obesity + MASH dual indication strategy.</p>

            <h3>Boehringer Ingelheim</h3>
            <div class="pipeline-flow">
                <span class="drug filing">Survodutide (Phase 3)</span>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">GLP-1/GCG dual agonist. MASH data strongest in class (62% improvement). SYNCHRONIZE Phase 3 program.</p>
        </div>

        <!-- Bull/Bear Thesis -->
        <div class="section">
            <h2>Investment Thesis</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>Market size could reach $150B+ by 2030, larger than any therapeutic class in history</li>
                        <li>Medicare Part D coverage (enacted 2025) adds ~15-20M addressable lives</li>
                        <li>Beyond obesity: MASH, CKD, heart failure, sleep apnea, Alzheimer's expand TAM 3-5x</li>
                        <li>Oral formulations (orforglipron, oral semaglutide 50mg) remove injection barrier</li>
                        <li>Monthly dosing (MariTide) improves compliance vs. weekly</li>
                        <li>Chronic therapy model = multi-decade revenue streams per patient</li>
                        <li>CV benefit data (SELECT) transforms payer willingness to cover</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>GI side effects (nausea, vomiting) limit tolerability; 5-7% GI discontinuation</li>
                        <li>Muscle loss (~25-40% of weight lost is lean mass) — long-term health impact unclear</li>
                        <li>Weight regain: ~2/3 regained within 1 year of stopping (STEP 1 extension)</li>
                        <li>Compounding pharmacies eroding brand pricing; FDA enforcement inconsistent</li>
                        <li>Long-term safety unknowns: thyroid C-cell tumors (rodent), pancreatitis</li>
                        <li>Lilly and Novo duopoly may squeeze out smaller players on manufacturing scale</li>
                        <li>Net price erosion from PBM negotiations and Medicare rebating</li>
                        <li>Manufacturing complexity limits rapid capacity expansion</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Catalysts (shared system) -->
        {catalyst_html}

        <!-- Sources -->
        <div class="section">
            <h2>Key Sources</h2>
            <ol class="source-list">
                <li>Wilding JPH et al. "Once-Weekly Semaglutide in Adults with Overweight or Obesity" (STEP 1). <em>NEJM</em> 2021; 384:989-1002. <a href="https://pubmed.ncbi.nlm.nih.gov/33567185/" target="_blank">PubMed</a></li>
                <li>Jastreboff AM et al. "Tirzepatide Once Weekly for the Treatment of Obesity" (SURMOUNT-1). <em>NEJM</em> 2022; 387:205-216. <a href="https://pubmed.ncbi.nlm.nih.gov/35658024/" target="_blank">PubMed</a></li>
                <li>Jastreboff AM et al. "Triple-Hormone-Receptor Agonist Retatrutide for Obesity" (Phase 2). <em>NEJM</em> 2023; 389:514-526. <a href="https://pubmed.ncbi.nlm.nih.gov/37385337/" target="_blank">PubMed</a></li>
                <li>Lincoff AM et al. "Semaglutide and Cardiovascular Outcomes in Obesity without Diabetes" (SELECT). <em>NEJM</em> 2023; 389:2221-2232. <a href="https://pubmed.ncbi.nlm.nih.gov/37952131/" target="_blank">PubMed</a></li>
                <li>Perkovic V et al. "Effects of Semaglutide on CKD in T2D" (FLOW). <em>NEJM</em> 2024; 391:109-121. <a href="https://pubmed.ncbi.nlm.nih.gov/38785209/" target="_blank">PubMed</a></li>
                <li>Wilding JPH et al. "Weight regain and cardiometabolic effects after withdrawal of semaglutide" (STEP 1 extension). <em>Diabetes Obes Metab</em> 2022; 24:1553-1564. <a href="https://pubmed.ncbi.nlm.nih.gov/35441470/" target="_blank">PubMed</a></li>
                <li>Kosiborod MN et al. "Semaglutide in HFpEF and Obesity" (STEP-HFpEF). <em>NEJM</em> 2023; 389:1069-1084. <a href="https://pubmed.ncbi.nlm.nih.gov/37622681/" target="_blank">PubMed</a></li>
                <li>Malhotra A et al. "Tirzepatide for the Treatment of Obstructive Sleep Apnea" (SURMOUNT-OSA). <em>NEJM</em> 2024; 391:1288-1298. <a href="https://pubmed.ncbi.nlm.nih.gov/38912654/" target="_blank">PubMed</a></li>
                <li>Sanyal AJ et al. "Survodutide for MASH" (Phase 2). <em>NEJM</em> 2024; 391:311-319. <a href="https://pubmed.ncbi.nlm.nih.gov/38847460/" target="_blank">PubMed</a></li>
                <li>Frias JP et al. "Orforglipron for Obesity" (Phase 2). <em>NEJM</em> 2023; 389:877-888. <a href="https://pubmed.ncbi.nlm.nih.gov/37351564/" target="_blank">PubMed</a></li>
                <li>Killion EA et al. "Anti-obesity effects of GIPR antagonism." <em>Nature Metabolism</em> 2024. <a href="https://pubmed.ncbi.nlm.nih.gov/38378898/" target="_blank">PubMed</a></li>
                <li>Lu SC et al. "GIP receptor biology in obesity." <em>Cell Metabolism</em> 2024. <a href="https://pubmed.ncbi.nlm.nih.gov/38959862/" target="_blank">PubMed</a></li>
                <li>Novo Nordisk. "CagriSema REDEFINE-1 Phase 3 Topline Results." Press release, Dec 2024.</li>
                <li>Amgen. "MariTide Phase 2 52-week Data." Investor presentation, Jul 2024.</li>
                <li>Treat and Reduce Obesity Act. U.S. Congress, enacted Jan 2025.</li>
                <li>Viking Therapeutics. "VK2735 Phase 2 Topline Results." Press release, Feb 2024.</li>
            </ol>
        </div>

        <a href="/targets" class="back-link">&larr; Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
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
        <div style="background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 0.85rem; color: #1B2838;">
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
                    <div class="catalyst-date" style="color: #D4654A;">{display}</div>
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

    tl1a_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }

        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th { background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .mechanism-box { background: var(--bg); padding: 20px; border-radius: 12px; margin-top: 16px; }
        .mechanism-box h4 { color: var(--navy); margin-bottom: 8px; }
        .mechanism-box p { color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }
    """

    return f'''{_render_head("TL1A / IBD Competitive Landscape | Satya Bio", tl1a_styles)}
    {_render_nav("targets")}
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
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
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

    b7h3_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section h3 { color: var(--navy); font-size: 1.1rem; margin: 20px 0 12px; }

        table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        th { background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .highlight-box { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 20px; margin: 20px 0; }
        .highlight-box h4 { color: #1B2838; margin-bottom: 8px; }
        .highlight-box p { color: #374151; font-size: 0.9rem; }

        .note-box { background: var(--bg); border-left: 3px solid var(--accent); padding: 16px 20px; margin-top: 16px; border-radius: 0 8px 8px 0; }
        .note-box p { color: var(--text-secondary); font-size: 0.85rem; line-height: 1.6; margin: 0; }

        .bio-point { display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
        .bio-point:last-child { border-bottom: none; }
        .bio-icon { min-width: 28px; height: 28px; background: var(--navy); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; flex-shrink: 0; }
        .bio-icon.risk { background: #D4654A; }
        .bio-text { font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6; }
        .bio-text strong { color: var(--text); }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }
    """

    return f'''{_render_head("B7-H3 / ADC Competitive Landscape | Satya Bio", b7h3_styles)}
    {_render_nav("targets")}
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
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''


def generate_kras_report(admin: bool = False):
    """Generate the KRAS competitive landscape report — analyst-grade."""

    # Catalyst section from shared system
    catalyst_html = render_catalyst_section("kras", admin=admin)

    kras_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section h3 { color: var(--navy); font-size: 1.1rem; margin: 24px 0 16px; }

        table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        th { background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }
        .table-footnote { font-size: 0.8rem; color: var(--text-secondary); margin-top: 12px; font-style: italic; line-height: 1.5; }

        .mutation-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin: 24px 0; }
        .mutation-card { background: var(--bg); padding: 20px; border-radius: 12px; border-left: 4px solid var(--accent); }
        .mutation-card h4 { color: var(--navy); margin-bottom: 8px; }
        .mutation-card .pct { font-size: 1.5rem; font-weight: 700; color: var(--accent); }

        .bio-box { background: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box h3 { color: #1e40af; margin-top: 0; }
        .bio-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }
        .bio-point { padding: 8px 0; border-bottom: 1px solid #dbeafe; font-size: 0.9rem; color: #374151; }
        .bio-point:last-child { border-bottom: none; }
        .bio-point strong { color: #1e40af; }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .deal-table td:nth-child(3) { font-weight: 600; color: var(--accent); }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }
        .catalyst-content strong { color: var(--navy); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }

        .source-list { list-style: decimal; padding-left: 24px; font-size: 0.85rem; color: var(--text-secondary); line-height: 2; }
        .source-list a { color: var(--accent); }
    """

    return f'''{_render_head("KRAS Inhibitor Landscape | Satya Bio", kras_styles)}
    {_render_nav("targets")}
    <main class="main">
        <div class="report-header">
            <h1>KRAS Inhibitor Landscape</h1>
            <p>From "undruggable" to three approved drugs and a $24B acquisition target. KRAS mutations drive ~25% of all cancers. G12C is solved; G12D and pan-RAS are the new frontier. Revolution Medicines (RVMD) is the central name.</p>
            <div class="report-meta">
                <div class="meta-item"><div class="label">Approved Drugs</div><div class="value">3</div></div>
                <div class="meta-item"><div class="label">Phase 3 Assets</div><div class="value">7+</div></div>
                <div class="meta-item"><div class="label">Target Mutations</div><div class="value">G12C, G12D, Pan-RAS</div></div>
                <div class="meta-item"><div class="label">Key Company</div><div class="value">RVMD ($24B)</div></div>
            </div>
        </div>

        <!-- Section 1: RAS Biology & the OFF vs. ON Paradigm -->
        <div class="section">
            <h2>RAS Biology &amp; the OFF vs. ON Paradigm</h2>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                KRAS (Kirsten Rat Sarcoma viral oncogene) is the most frequently mutated oncogene in human cancer, present in ~20% of all cancers. KRAS mutations are particularly prevalent in pancreatic (&gt;90%), colorectal (~40%), and lung (~25%) cancers.
            </p>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                KRAS cycles between an active GTP-bound &ldquo;ON&rdquo; state and an inactive GDP-bound &ldquo;OFF&rdquo; state. GEFs (mainly SOS1) activate KRAS by loading GTP. GAPs (mainly NF1) inactivate it by stimulating GTP hydrolysis. Oncogenic mutations impair GTP hydrolysis, locking KRAS in the ON state.
            </p>
            <div class="bio-box">
                <h3>OFF-State Inhibitors</h3>
                <p>OFF-state inhibitors (sotorasib, adagrasib, divarasib, olomorasib, calderasib) bind a pocket that only exists when KRAS is GDP-bound (OFF). They must wait for the GTPase cycle to bring KRAS back to the inactive state. This creates a vulnerability: upstream RTK signaling pushes KRAS to the ON state, reducing target engagement.</p>
            </div>
            <div class="bio-box" style="background: #f5f3f0; border-color: #e0ddd8;">
                <h3 style="color: #1B2838;">ON-State Inhibitors (Revolution Medicines Platform)</h3>
                <p style="color: #374151;">ON-state inhibitors (daraxonrasib, elironrasib, zoldonrasib) use a novel <strong>tri-complex mechanism</strong>. The drug binds to cyclophilin A (a ubiquitous human protein), and this drug&ndash;cyclophilin complex then selectively recognizes and locks active GTP-bound KRAS. This is mechanistically analogous to how immunomodulatory drugs (lenalidomide) work through cereblon &mdash; a molecular chaperone recruitment approach.</p>
                <p style="color: #374151; margin-top: 12px;"><strong>Why ON-state matters:</strong> Because they target active KRAS directly, ON-state inhibitors don&rsquo;t depend on the GDP/GTP cycle and may be inherently more resistant to adaptive resistance (which pushes KRAS toward the GTP state).</p>
            </div>
            <div class="bio-box" style="background: #f5f3f0; border-color: #e0ddd8;">
                <h3 style="color: #1B2838;">Degraders: A Third Modality</h3>
                <p style="color: #374151;">Degraders (Astellas setidegrasib/ASP3082) destroy the KRAS G12D protein entirely via targeted protein degradation using a VHL E3 ligase. The protein is eliminated rather than inhibited. Astellas is also developing ASP4396, a backup degrader using cereblon as the E3 ligase.</p>
            </div>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-top: 16px;">
                <strong>Pan-KRAS vs. Pan-RAS:</strong> Pan-KRAS inhibitors target multiple KRAS mutations (G12C, G12D, G12V, etc.) but not NRAS or HRAS. Pan-RAS inhibitors (like daraxonrasib) additionally block wild-type NRAS and HRAS, which matters for resistance since cancer cells can escape through WT RAS activation.
            </p>
        </div>

        <!-- Section 2: Competitive Pipeline by Mutation -->
        <div class="section">
            <h2>Competitive Pipeline by Mutation</h2>

            <!-- G12C -->
            <h3>KRAS G12C (NSCLC-dominant: ~12% NSCLC, ~3-4% CRC, ~1-2% PDAC)</h3>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Drug</th><th>Company</th><th>Mechanism</th><th>Phase</th><th>Key Efficacy</th><th>Differentiator</th><th>Next Catalyst</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Sotorasib (Lumakras)</strong></td><td>Amgen</td><td>G12C OFF covalent</td><td>Approved</td><td>41% ORR, 6.3mo PFS (NSCLC)</td><td>First-in-class. Now approved + panitumumab in CRC</td><td>Mature product &mdash; limited expansion</td></tr>
                    <tr><td><strong>Adagrasib (Krazati)</strong></td><td>BMS</td><td>G12C OFF covalent</td><td>Approved</td><td>43% ORR, 6.9mo PFS (NSCLC)</td><td>23hr half-life, BBB penetration</td><td>KRYSTAL-10 (CRC, H1 2026), KRYSTAL-7 (1L NSCLC, 2028)</td></tr>
                    <tr><td><strong>Divarasib</strong></td><td>Roche</td><td>G12C OFF covalent (next-gen)</td><td>Phase 3</td><td>59% ORR, 15.3mo PFS (NSCLC)</td><td>5-20x more potent than sotorasib</td><td>KRASCENDO-1 (vs soto/ada, ~2027), KRASCENDO-2 (1L + pembro)</td></tr>
                    <tr><td><strong>Olomorasib</strong></td><td>Eli Lilly</td><td>G12C OFF covalent (next-gen)</td><td>Phase 3</td><td>35% ORR (solid tumors), 41% ORR post-G12Ci</td><td>Activity AFTER prior G12C failure (unique)</td><td>SUNRAY-01 (1L + pembro), SUNRAY-02 (resectable)</td></tr>
                    <tr><td><strong>Calderasib (MK-1084)</strong></td><td>Merck</td><td>G12C OFF covalent (next-gen)</td><td>Phase 3</td><td>38% ORR NSCLC, 38% CRC (Ph1)</td><td>Combo with Keytruda Qlex</td><td>KANDLELIT-007 (1L + Keytruda, just started Jan 2026)</td></tr>
                    <tr><td><strong>Glecirasib</strong></td><td>Jacobio / Innovent</td><td>G12C OFF covalent</td><td>Phase 3 (China)</td><td>China-focused development</td><td>Regional play</td><td>China data expected 2026</td></tr>
                    <tr><td><strong>Elironrasib (RMC-6291)</strong></td><td>Revolution Medicines</td><td>G12C ON tri-complex</td><td>Phase 1/2</td><td>BTD granted</td><td>Only ON-state G12C inhibitor. Designed for post-G12Ci relapse.</td><td>Combo with daraxonrasib (NCT06128551)</td></tr>
                </tbody>
            </table>
            </div>

            <!-- G12D -->
            <h3 style="margin-top: 32px;">KRAS G12D (PDAC-dominant: ~40% PDAC, ~12% CRC, ~4% NSCLC) &mdash; ZERO APPROVED DRUGS</h3>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Drug</th><th>Company</th><th>Mechanism</th><th>Phase</th><th>Key Efficacy</th><th>Differentiator</th><th>Next Catalyst</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Zoldonrasib (RMC-9805)</strong></td><td>Revolution Medicines</td><td>G12D ON tri-complex</td><td>Phase 1 (pivotal-enabling)</td><td>61% ORR NSCLC (n=18), 30% ORR PDAC (n=40)</td><td>First-ever BTD for G12D (Jan 2026). Tri-complex with cyclophilin A.</td><td>Pivotal data; potential accelerated filing</td></tr>
                    <tr><td><strong>Setidegrasib (ASP3082)</strong></td><td>Astellas</td><td>G12D degrader (VHL E3 ligase)</td><td>Phase 1 &rarr; Phase 3 planned</td><td>58% ORR + chemo in 1L PDAC (n=12); 23% ORR mono NSCLC</td><td>First-in-class degrader. Eliminates protein entirely.</td><td>Phase 3 1L PDAC (setidegrasib + mFOLFIRINOX) starting 2026</td></tr>
                    <tr><td><strong>ASP4396</strong></td><td>Astellas</td><td>G12D degrader (cereblon ligase)</td><td>Phase 1</td><td>Early</td><td>Backup degrader with different E3 ligase</td><td>Phase 1 data</td></tr>
                    <tr><td><strong>HRS-4642</strong></td><td>Jiangsu HengRui</td><td>G12D inhibitor</td><td>Phase 3 (China)</td><td>China-focused</td><td>Regional play</td><td>Pivotal study China</td></tr>
                    <tr><td><strong>VS-7375 (GFH375)</strong></td><td>Verastem / GenFleet</td><td>G12D inhibitor</td><td>Phase 3 (China)</td><td>China 2L PDAC</td><td>Verastem-partnered</td><td>Ph3 China data</td></tr>
                    <tr><td><strong>ARV-806</strong></td><td>Arvinas</td><td>G12D degrader</td><td>Phase 1</td><td>Early &mdash; data expected 2026</td><td>Third degrader entrant</td><td>Ph1 data 2026</td></tr>
                </tbody>
            </table>
            </div>

            <!-- Pan-KRAS / Pan-RAS -->
            <h3 style="margin-top: 32px;">Pan-KRAS / Pan-RAS (Broadest Coverage &mdash; All KRAS Mutations)</h3>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Drug</th><th>Company</th><th>Mechanism</th><th>Phase</th><th>Key Efficacy</th><th>Differentiator</th><th>Next Catalyst</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Daraxonrasib (RMC-6236)</strong></td><td>Revolution Medicines</td><td>Pan-RAS ON multi-selective</td><td>Phase 3</td><td>~35% ORR PDAC (Ph1/2). BTD for PDAC.</td><td>Only pan-RAS(ON) inhibitor. Covers G12C/D/V, G13, Q61 + WT NRAS/HRAS.</td><td>RASolute-302 (2L PDAC, late 2026) &mdash; THE event of the year. RASolute-303 (1L PDAC, enrolling 2026).</td></tr>
                    <tr><td><strong>JAB-23E73</strong></td><td>AstraZeneca / Jacobio</td><td>Pan-KRAS (not pan-RAS)</td><td>Phase 1/2</td><td>Early</td><td>AZ paid $100M upfront Jan 2026. 600+ patients enrolling.</td><td>Ph1/2 data 2026-2027</td></tr>
                    <tr><td><strong>ERAS-4001</strong></td><td>Erasca / Joyo</td><td>Pan-KRAS</td><td>Phase 1</td><td>Early</td><td>$12.5M upfront deal</td><td>Ph1 data</td></tr>
                    <tr><td><strong>GFH276</strong></td><td>GenFleet</td><td>Pan-RAS</td><td>Phase 1</td><td>Early</td><td>One of few pan-RAS after RVMD</td><td>Ph1 data</td></tr>
                </tbody>
            </table>
            </div>

            <!-- Other Mutations -->
            <h3 style="margin-top: 32px;">Other Mutations (Expanding the Addressable Market)</h3>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Drug</th><th>Company</th><th>Mutation</th><th>Phase</th><th>Status</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>RMC-5127</strong></td><td>Revolution Medicines</td><td>G12V ON</td><td>Phase 1</td><td>Covers ~30% PDAC, ~7% NSCLC</td></tr>
                    <tr><td><strong>RMC-0708</strong></td><td>Revolution Medicines</td><td>Q61H ON</td><td>Preclinical</td><td>Expanding mutation coverage</td></tr>
                    <tr><td><strong>RMC-8839</strong></td><td>Revolution Medicines</td><td>G13C ON</td><td>Preclinical</td><td>Expanding mutation coverage</td></tr>
                </tbody>
            </table>
            </div>
        </div>

        <!-- Section 3: Revolution Medicines Platform Deep-Dive -->
        <div class="section">
            <h2>Revolution Medicines Platform Deep-Dive</h2>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                RVMD is unique in oncology: the <strong>only company with an ON-state RAS platform</strong> covering 6+ mutations across clinical and preclinical stages. It holds 3 FDA Breakthrough Therapy Designations across 3 different drugs (daraxonrasib for PDAC, elironrasib for G12C NSCLC, zoldonrasib for G12D NSCLC) &mdash; unprecedented for a pre-revenue company.
            </p>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                <strong>Platform economics:</strong> The tri-complex technology is modular. The same cyclophilin A chaperone recruitment mechanism is used with different warheads for different mutations. Each new drug leverages existing chemistry and manufacturing knowledge, compressing development timelines.
            </p>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 20px;">
                <strong>Financial position:</strong> ~$2B cash, pre-revenue, $24B market cap post-Merck collapse. The stock was ~$16B pre-M&amp;A speculation, spiked to ~$28B during talks, and settled ~$24B after collapse.
            </p>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Asset</th><th>Target</th><th>Phase</th><th>Key Data</th><th>BTD</th><th>Next Catalyst</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Daraxonrasib (RMC-6236)</strong></td><td>Pan-RAS(ON)</td><td>Phase 3</td><td>~35% ORR PDAC (Ph1/2)</td><td>Yes (PDAC)</td><td>RASolute-302 late 2026</td></tr>
                    <tr><td><strong>Zoldonrasib (RMC-9805)</strong></td><td>G12D(ON)</td><td>Phase 1 (pivotal)</td><td>61% ORR NSCLC; 30% ORR PDAC</td><td>Yes (G12D NSCLC)</td><td>Pivotal data + accel. filing</td></tr>
                    <tr><td><strong>Elironrasib (RMC-6291)</strong></td><td>G12C(ON)</td><td>Phase 1/2</td><td>Post-G12Ci activity</td><td>Yes (G12C NSCLC)</td><td>Combo w/ daraxonrasib</td></tr>
                    <tr><td><strong>RMC-5127</strong></td><td>G12V(ON)</td><td>Phase 1</td><td>Early</td><td>&mdash;</td><td>Ph1 data</td></tr>
                    <tr><td><strong>RMC-0708</strong></td><td>Q61H(ON)</td><td>Preclinical</td><td>&mdash;</td><td>&mdash;</td><td>IND</td></tr>
                    <tr><td><strong>RMC-8839</strong></td><td>G13C(ON)</td><td>Preclinical</td><td>&mdash;</td><td>&mdash;</td><td>IND</td></tr>
                </tbody>
            </table>
            </div>
            <div class="bio-box" style="background: #f5f3f0; border-color: #e0ddd8; margin-top: 20px;">
                <h3 style="color: #1B2838;">The Merck Saga (January 2026)</h3>
                <p style="color: #374151; line-height: 1.7;">
                    <strong>Jan 7:</strong> WSJ reports AbbVie in acquisition talks (&gt;$20B). RVMD +30%. AbbVie denies.<br>
                    <strong>Jan 8:</strong> Zoldonrasib receives BTD for G12D NSCLC &mdash; RVMD&rsquo;s 3rd BTD.<br>
                    <strong>Jan 9:</strong> FT reports Merck in talks at $28-32B. Multiple outlets confirm.<br>
                    <strong>Jan 12:</strong> JPM Healthcare Conference &mdash; intense speculation.<br>
                    <strong>Jan 26:</strong> Talks collapse. RVMD -20%, settles ~$24B market cap.<br><br>
                    Management chose independence, signaling confidence that RASolute-302 data will justify a higher valuation. CEO Mark Goldsmith MD/PhD: <em>&ldquo;It&rsquo;s not our goal to build something big. It&rsquo;s our goal to build something impactful.&rdquo;</em>
                </p>
            </div>
            <div class="thesis-grid" style="margin-top: 20px;">
                <div class="bull-box">
                    <h3>RVMD Bull Case</h3>
                    <ul class="thesis-list">
                        <li>If RASolute-302 positive in PDAC, daraxonrasib becomes the first-ever targeted therapy in pancreatic cancer</li>
                        <li>RVMD re-rates to $40B+ and renewed bidding war from multiple Big Pharma</li>
                        <li>Platform covers ~3.4M new KRAS-mutant cancer patients/year worldwide</li>
                        <li>3 BTDs across 3 drugs with modular platform chemistry &mdash; pipeline depth is unmatched</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>RVMD Bear Case</h3>
                    <ul class="thesis-list">
                        <li>PDAC has been a graveyard for targeted therapies &mdash; decades of failures</li>
                        <li>Pan-RAS inhibition of WT KRAS may have a narrow therapeutic window (WT KRAS is essential for normal development)</li>
                        <li>Small datasets with unconfirmed responses (6/11 NSCLC responses for zoldonrasib were unconfirmed)</li>
                        <li>$24B valuation for a pre-revenue company with no approved products</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Section 4: Resistance Biology -->
        <div class="section">
            <h2>Resistance Biology</h2>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                <strong>Adaptive resistance (hours):</strong> When you inhibit mutant KRAS, ERK-mediated negative feedback is relieved. This reactivates the RAS-MAPK pathway through WT NRAS and HRAS via RTK &rarr; SOS1 signaling. This is the fundamental problem with ALL KRAS inhibitors.
            </p>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                <strong>Why OFF-state inhibitors are especially vulnerable:</strong> Adaptive resistance pushes KRAS toward the GTP-bound ON state, which <em>reduces</em> the target available for OFF-state drugs to bind. The drug literally has less target to work with.
            </p>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                <strong>Why ON-state inhibitors may be more durable:</strong> They bind GTP-bound KRAS directly. Feedback that pushes KRAS to the ON state may paradoxically <em>increase</em> target engagement (more ON-state KRAS = more binding sites).
            </p>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 16px;">
                <strong>Tissue-specific differences:</strong> CRC has much stronger RTK (especially EGFR) feedback than NSCLC, explaining why KRAS monotherapy ORR is ~30% in CRC vs ~40-55% in NSCLC. This is why sotorasib + panitumumab (anti-EGFR) was developed specifically for CRC.
            </p>
            <div class="bio-box">
                <h3>Acquired Resistance Mutations</h3>
                <p>Y96D, Y96S alter the Switch II pocket, blocking covalent binding. Some confer cross-resistance to both sotorasib and adagrasib. Others remain sensitive to the alternative G12C inhibitor. Pathway bypass through BRAF amplification, MET amplification, PIK3CA mutation, or histologic transformation (NSCLC &rarr; SCLC) represents a distinct resistance category.</p>
            </div>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-top: 16px;">
                <strong>Implication:</strong> Monotherapy will inevitably fail. Combinations that block upstream feedback (SHP2i, SOS1i, EGFRi) or downstream bypass (MEKi, CDK4/6i) are necessary for durable responses.
            </p>
        </div>

        <!-- Section 5: Combination Therapy Landscape -->
        <div class="section">
            <h2>Combination Therapy Landscape</h2>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Strategy</th><th>Rationale</th><th>Key Trials</th><th>Status</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>G12C + anti-PD-1 (1L NSCLC)</strong></td><td>Expand to frontline, largest commercial market</td><td>Olomorasib+pembro (SUNRAY-01), divarasib+pembro (KRASCENDO-2), calderasib+Keytruda Qlex (KANDLELIT-007)</td><td>Multiple Phase 3s enrolling &mdash; THE commercial prize</td></tr>
                    <tr><td><strong>G12C + EGFRi (CRC)</strong></td><td>Block EGFR-driven feedback in CRC</td><td>Soto+panitumumab (FDA approved), divarasib+cetuximab (62% ORR Ph1b)</td><td>Validated in CRC &mdash; soto+pani already approved</td></tr>
                    <tr><td><strong>G12C + SHP2i</strong></td><td>Block convergent RTK feedback upstream of SOS1</td><td>JDQ443+TNO155 (KontRASt-01)</td><td>Tolerability challenges &mdash; some programs discontinued</td></tr>
                    <tr><td><strong>G12C + SOS1i</strong></td><td>Alternative to SHP2i, block RAS activation directly</td><td>BI-1701963+BI 1823911</td><td>Early clinical; mixed results</td></tr>
                    <tr><td><strong>G12D + chemo (1L PDAC)</strong></td><td>Frontline PDAC &mdash; highest unmet need</td><td>Setidegrasib+mFOLFIRINOX (Phase 3 planned 2026)</td><td>58% ORR in Phase 1 is attention-getting</td></tr>
                    <tr><td><strong>Pan-RAS + G12C-selective</strong></td><td>Deep RAS suppression by blocking both mutant AND WT RAS</td><td>Daraxonrasib+elironrasib (NCT06128551)</td><td>Phase 1/2 &mdash; rational but unproven</td></tr>
                </tbody>
            </table>
            </div>
        </div>

        <!-- Section 6: Big Pharma Oncology Gaps & KRAS M&A Logic -->
        <div class="section">
            <h2>Big Pharma Oncology Gaps &amp; KRAS M&amp;A Logic</h2>
            <p style="color: var(--text-secondary); line-height: 1.8; margin-bottom: 20px;">
                Understanding who needs KRAS assets and why is critical for anticipating M&amp;A. Most large pharma companies face patent cliffs on blockbuster drugs within 2-4 years. KRAS is one of the few areas with sufficient market size ($7-8B by 2034) and clinical momentum to replace lost revenue.
            </p>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Company</th><th>Key LOE Drug</th><th>LOE Date</th><th>Revenue at Risk</th><th>KRAS Asset</th><th>Strategic Gap</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Merck</strong></td><td>Keytruda</td><td>2028</td><td>~$30B/yr</td><td>Calderasib (G12C OFF, Ph3)</td><td>No G12D, no pan-RAS. Tried RVMD at $30B &mdash; failed. $70B opportunity target by mid-2030s.</td></tr>
                    <tr><td><strong>BMS</strong></td><td>Eliquis + Opdivo</td><td>2026/2028</td><td>~$16B combined</td><td>Krazati (G12C OFF, approved)</td><td>Gen 1 product being surpassed. No G12D. Cannot afford mega-deal.</td></tr>
                    <tr><td><strong>AstraZeneca</strong></td><td>Farxiga</td><td>2026</td><td>~$7.7B</td><td>JAB-23E73 (pan-KRAS, Ph1/2)</td><td>Late entrant, $100M bolt-on. Playing catch-up.</td></tr>
                    <tr><td><strong>Eli Lilly</strong></td><td>(No major onc LOE)</td><td>&mdash;</td><td>&mdash;</td><td>Olomorasib (G12C OFF, Ph3)</td><td>Strongest position &mdash; can build internally. No G12D or pan-RAS.</td></tr>
                    <tr><td><strong>Roche</strong></td><td>(Diverse)</td><td>Gradual</td><td>&mdash;</td><td>Divarasib (G12C OFF, Ph3)</td><td>Best-in-class G12C (59% ORR). No G12D or pan-RAS.</td></tr>
                    <tr><td><strong>Pfizer</strong></td><td>Ibrance/Xtandi</td><td>2027</td><td>~$8B</td><td>None</td><td>Complete KRAS gap. Focused on ADCs post-Seagen.</td></tr>
                    <tr><td><strong>Astellas</strong></td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td>Setidegrasib (G12D degrader)</td><td>Only degrader company &mdash; could be acquired itself.</td></tr>
                </tbody>
            </table>
            </div>
            <div class="bio-box" style="margin-top: 20px;">
                <p>Every major pharma with a KRAS asset has a G12C OFF-state inhibitor. <strong>None except RVMD has a viable ON-state platform or pan-RAS coverage.</strong> G12D has ZERO approved drugs. This is why RVMD commanded a $30B valuation &mdash; it is the only company with ON-state mechanism + pan-RAS + G12D + G12C + G12V coverage. If RASolute-302 data are positive, expect a renewed bidding war. If data disappoint, the G12C OFF-state companies (Roche, Lilly, Merck) become dominant and RVMD&rsquo;s $24B valuation becomes untenable.</p>
            </div>
        </div>

        <!-- Section 7: Market Opportunity by Indication & Mutation -->
        <div class="section">
            <h2>Market Opportunity by Indication &amp; Mutation</h2>
            <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr><th>Cancer Type</th><th>US Annual Incidence</th><th>% KRAS Mutated</th><th>Dominant Mutations</th><th>Addressable Market</th><th>Current SOC</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>NSCLC</strong></td><td>~236,000</td><td>~25%</td><td>G12C (12%), G12V (7%), G12D (4%)</td><td>$10-15B (1L combos)</td><td>Keytruda &plusmn; chemo</td></tr>
                    <tr><td><strong>PDAC</strong></td><td>~64,000</td><td>&gt;90%</td><td>G12D (40%), G12V (30%), G12R (15%)</td><td>$5-8B</td><td>FOLFIRINOX, gem/nab-P. No targeted therapy EVER worked.</td></tr>
                    <tr><td><strong>CRC</strong></td><td>~153,000</td><td>~40%</td><td>G12D (12%), G12V (8%), G12C (3-4%), G13D (7%)</td><td>$3-5B</td><td>Chemo + biologics</td></tr>
                    <tr><td><strong>LGSOC</strong></td><td>Rare subset</td><td>KRAS mutated</td><td>Various</td><td>&lt;$1B</td><td>Avutometinib+defactinib (approved May 2025)</td></tr>
                </tbody>
            </table>
            </div>
            <p class="table-footnote">Total KRAS-mutant cancer worldwide: ~3.4 million new patients per year. KRAS inhibitors market projected to grow from ~$526M (2025) to ~$7.8B by 2034 at 35% CAGR.</p>
            <div class="bio-box" style="background: #f5f3f0; border-color: #e0ddd8; margin-top: 20px;">
                <h3 style="color: #1B2838;">Pancreatic Cancer Context</h3>
                <p style="color: #374151; line-height: 1.7;">5-year survival ~12%. Third leading cause of cancer death in the US. Despite 40+ years of trials, the standard of care remains cytotoxic chemotherapy. There has <strong>never</strong> been a successful targeted therapy in PDAC. If daraxonrasib or zoldonrasib show meaningful Phase 3 activity, it would be the first time any targeted drug works in this disease. This is why the market prices RVMD at $24B pre-revenue.</p>
            </div>
        </div>

        <!-- Section 8: Deal Landscape -->
        <div class="section">
            <h2>Deal Landscape</h2>
            <div style="overflow-x: auto;">
            <table class="deal-table">
                <thead>
                    <tr><th>Deal</th><th>Parties</th><th>Date</th><th>Value</th><th>Significance</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Merck-RVMD (collapsed)</strong></td><td>Merck + Revolution Medicines</td><td>Jan 2026</td><td>$28-32B range</td><td>Largest attempted biotech deal of 2026. Collapsed Jan 26 &mdash; RVMD chose independence.</td></tr>
                    <tr><td><strong>AZ-Jacobio</strong></td><td>AstraZeneca + Jacobio</td><td>Jan 2026</td><td>$100M upfront</td><td>Pan-KRAS bolt-on. Signals Big Pharma consensus on KRAS.</td></tr>
                    <tr><td><strong>BMS-Mirati</strong></td><td>BMS acquired Mirati</td><td>2024</td><td>$4.8B</td><td>For adagrasib (Krazati). Now looks modest vs RVMD valuations.</td></tr>
                    <tr><td><strong>RVMD-Royalty Pharma</strong></td><td>Revolution Medicines + RP</td><td>2025</td><td>$2B</td><td>Royalty financing &mdash; RVMD monetized future royalties to fund pipeline.</td></tr>
                    <tr><td><strong>Bayer-Kumquat</strong></td><td>Bayer + Kumquat Biosciences</td><td>2025</td><td>Undisclosed</td><td>KRAS G12D partnership.</td></tr>
                    <tr><td><strong>Verastem-GenFleet</strong></td><td>Verastem + GenFleet</td><td>2024</td><td>Undisclosed</td><td>VS-7375 G12D partnership.</td></tr>
                </tbody>
            </table>
            </div>
        </div>

        <!-- Section 9: Catalysts (shared system) -->
        {catalyst_html}

        <!-- Section 10: Sources -->
        <div class="section">
            <h2>Key Sources</h2>
            <ol class="source-list">
                <li>Sacher A et al. &ldquo;Single-Agent Divarasib (GDC-6036) in Solid Tumors with a KRAS G12C Mutation.&rdquo; <em>NEJM</em> 2023; 389:710-721. <a href="https://clinicaltrials.gov/ct2/show/NCT04449874" target="_blank">NCT04449874</a></li>
                <li>Skoulidis F et al. &ldquo;Sotorasib for Lung Cancers with KRAS p.G12C Mutation.&rdquo; (CodeBreaK 100) <em>NEJM</em> 2021; 384:2371-2381. <a href="https://pubmed.ncbi.nlm.nih.gov/34096690/" target="_blank">PubMed</a></li>
                <li>Li BT et al. &ldquo;Adagrasib in Patients with KRAS G12C-Mutated NSCLC.&rdquo; (KRYSTAL-1 updated) <em>NEJM</em> 2024. <a href="https://pubmed.ncbi.nlm.nih.gov/35658005/" target="_blank">PubMed</a></li>
                <li>Strickler JH et al. &ldquo;Sotorasib plus Panitumumab in KRAS G12C CRC.&rdquo; (CodeBreaK 300) <em>NEJM</em> 2023; 389:2125-2139. <a href="https://pubmed.ncbi.nlm.nih.gov/37870976/" target="_blank">PubMed</a></li>
                <li>Revolution Medicines. &ldquo;Zoldonrasib AACR 2025 &mdash; 61% ORR in G12D NSCLC.&rdquo; <a href="https://doi.org/10.1158/1538-7445.AM2025-CT019" target="_blank">doi:10.1158/1538-7445.AM2025-CT019</a></li>
                <li>Astellas. &ldquo;Setidegrasib + mFOLFIRINOX in 1L PDAC.&rdquo; ASCO-GI 2026 presentation.</li>
                <li>&ldquo;Emerging landscape of KRAS inhibitors.&rdquo; (Comprehensive review) <em>Cancer Cell</em> Jan 2026.</li>
                <li>Hofmann MH et al. &ldquo;Expanding biology of SOS1 in KRAS-driven cancers.&rdquo; <em>Nature Cancer</em> 2024.</li>
                <li>&ldquo;Astra enters the pan-KRAS game.&rdquo; ApexOnco / OncologyPipeline, Jan 2026.</li>
                <li>KANDLELIT-007 Phase 3 design. <a href="https://clinicaltrials.gov/ct2/show/NCT07190248" target="_blank">NCT07190248</a></li>
                <li>RASolute-302 Phase 3. <a href="https://clinicaltrials.gov/" target="_blank">ClinicalTrials.gov</a></li>
                <li>Sacher A et al. &ldquo;Divarasib long-term follow-up &mdash; 59% ORR, 15.3mo PFS.&rdquo; <em>JCO</em> 2025.</li>
            </ol>
        </div>

        <a href="/targets" class="back-link">&larr; Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''


def generate_mir124_report(admin: bool = False):
    """Generate the miR-124 / obefazimod landscape report — analyst-grade."""

    # Catalyst section from shared system
    catalyst_html = render_catalyst_section("mir-124", admin=admin)

    mir124_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section h3 { color: var(--navy); font-size: 1.1rem; margin: 24px 0 16px; }

        table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        th { background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }
        .table-footnote { font-size: 0.8rem; color: var(--text-secondary); margin-top: 12px; font-style: italic; line-height: 1.5; }

        .bio-box { background: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box h3 { color: #1e40af; margin-top: 0; }
        .bio-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-green { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-green h3 { color: #1B2838; margin-top: 0; }
        .bio-box-green p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-amber { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-amber h3 { color: #1B2838; margin-top: 0; }
        .bio-box-amber p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }
        .catalyst-content strong { color: var(--navy); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }

        .source-list { list-style: decimal; padding-left: 24px; font-size: 0.85rem; color: var(--text-secondary); line-height: 2; }
        .source-list a { color: var(--accent); }

        .callout-box { background: #fef5f3; border: 1px solid #e07a5f; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .callout-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }
        .callout-box strong { color: var(--accent); }

        .highlight-row { background: #fef5f3 !important; }
    """

    return f'''{_render_head("miR-124: Obefazimod & the MicroRNA Reset | Satya Bio", mir124_styles)}
    {_render_nav("targets")}
    <main class="main">

        <!-- Header -->
        <div class="report-header">
            <h1>miR-124 &mdash; The MicroRNA Reset</h1>
            <p>Obefazimod hit in both Phase 3 UC induction trials. Formation Bio licensed a second miR-124 activator 12 days ago. A novel mechanism that resets immune balance rather than blocking a single cytokine.</p>
            <div class="report-meta">
                <div class="meta-item">
                    <div class="label">Lead Asset</div>
                    <div class="value">Obefazimod (Ph3)</div>
                </div>
                <div class="meta-item">
                    <div class="label">ABTECT Pooled Remission</div>
                    <div class="value">16.4% pbo-adj</div>
                </div>
                <div class="meta-item">
                    <div class="label">Pivotal Readout</div>
                    <div class="value">Maintenance Q2 2026</div>
                </div>
                <div class="meta-item">
                    <div class="label">UC Market (2030E)</div>
                    <div class="value">&gt;$15B</div>
                </div>
            </div>
        </div>

        <!-- Section 1: The MicroRNA That Resets Immune Balance -->
        <div class="section">
            <h2>1. miR-124 &mdash; The MicroRNA That Resets Immune Balance</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                MicroRNA-124 (miR-124) is a small non-coding RNA that acts as a natural anti-inflammatory brake in the body. miR-124 levels are reduced in patients with inflammatory bowel disease, rheumatoid arthritis, multiple sclerosis, and other chronic inflammatory conditions. When miR-124 is depleted, pro-inflammatory pathways run unchecked.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Unlike drugs that block individual cytokines (anti-TNF, anti-IL-23, anti-IL-4R&alpha;), miR-124 operates upstream &mdash; it simultaneously downregulates multiple pro-inflammatory pathways including IL-6/STAT3, AREG, and CDK6, while promoting anti-inflammatory regulatory T-cell function. As David Rubin, MD (University of Chicago) described obefazimod&rsquo;s mechanism: <em>&ldquo;Rather than targeting specific active inflammation, it shuts it off at the source, resetting a balance of the immune system.&rdquo;</em>
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                This makes miR-124 enhancers fundamentally different from every other drug in the IBD landscape. They don&rsquo;t block one pathway &mdash; they restore the body&rsquo;s natural regulatory machinery.
            </p>

            <div class="bio-box-green">
                <h3>Obefazimod (ABX464) &mdash; First-in-Class</h3>
                <p>Obefazimod is a first-in-class oral small molecule that enhances miR-124 expression by binding the cap-binding complex (CBC/ARS2), promoting the biogenesis of miR-124 from its precursor. Originally discovered in HIV research, Abivax pivoted to IBD after observing potent anti-inflammatory effects. It is the <strong>only miR-124-directed drug to have completed Phase 3 clinical trials</strong>.</p>
            </div>
        </div>

        <!-- Section 2: The Phase 3 Story -->
        <div class="section">
            <h2>2. Obefazimod &mdash; The Phase 3 Story</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Obefazimod&rsquo;s clinical journey has been methodical: a positive Phase 2a (2020), a strong Phase 2b with 48-week durability (2023), and then two massive parallel Phase 3 induction trials &mdash; ABTECT-1 and ABTECT-2 &mdash; enrolling 1,275 patients across 600+ sites in 36 countries. This was one of the largest Phase 3 UC programs ever conducted.
            </p>

            <h3>ABTECT Phase 3 Induction Results (Jul 22, 2025)</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 12px;">
                The 50mg dose met the primary endpoint of clinical remission at Week 8 in both trials:
            </p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Endpoint</th>
                            <th>ABTECT-1</th>
                            <th>ABTECT-2</th>
                            <th>Pooled</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Clinical remission (pbo-adj)</strong></td>
                            <td><strong>19.3%</strong> (p&lt;0.0001)</td>
                            <td><strong>13.4%</strong> (p=0.0001)</td>
                            <td><strong>16.4%</strong></td>
                        </tr>
                        <tr>
                            <td>Endoscopic improvement</td>
                            <td>Met (p&lt;0.0001)</td>
                            <td>Met</td>
                            <td>Met</td>
                        </tr>
                        <tr>
                            <td>Clinical response</td>
                            <td>Met</td>
                            <td>Met</td>
                            <td>Met</td>
                        </tr>
                        <tr>
                            <td>Symptomatic remission</td>
                            <td>Met</td>
                            <td>Met</td>
                            <td>Met</td>
                        </tr>
                        <tr>
                            <td>Prior advanced therapy failure</td>
                            <td colspan="3">47.3% of patients had failed prior advanced therapy including JAK inhibitors</td>
                        </tr>
                        <tr>
                            <td>Safety</td>
                            <td colspan="3">Adverse events comparable to placebo. No new safety signals at any dose.</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h3>Patient-Reported Outcomes (Sep 2025)</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                37% of 50mg patients reported <strong>no bowel urgency</strong> at Week 8 vs 18.1% placebo (p&lt;0.0001). Significant improvements in quality of life, sleep, and work productivity. For UC patients, bowel urgency resolution is among the most meaningful outcomes.
            </p>

            <div class="bio-box">
                <h3>Safety &mdash; The Competitive Edge</h3>
                <p>The most important feature of obefazimod may be its safety. Across all studies &mdash; Phase 1 through Phase 3, including 96-week open-label extension &mdash; adverse events were comparable to placebo. No new safety signals at any dose or duration. The Dec 2025 DSMB review of the maintenance trial (&gt;80% completion) confirmed no safety concerns. For a field where JAK inhibitors carry <strong>boxed warnings for cardiovascular events, malignancy, and thrombosis</strong>, a clean safety profile is a major competitive advantage.</p>
            </div>

            <h3>What&rsquo;s Next: Maintenance (Q2 2026)</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                678 patients are enrolled in the 44-week ABTECT maintenance trial. Topline results expected Q2 2026 &mdash; this is the <strong>make-or-break readout</strong>. If positive, Abivax plans NDA submission in H2 2026 with potential FDA approval in 2027.
            </p>
        </div>

        <!-- Section 3: miR-124 Competitive Landscape -->
        <div class="section">
            <h2>3. Competitive Landscape &mdash; miR-124 Activators</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Drug</th>
                            <th>Company</th>
                            <th>Mechanism</th>
                            <th>Phase</th>
                            <th>Lead Indication</th>
                            <th>Key Data</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="highlight-row">
                            <td><strong>Obefazimod (ABX464)</strong></td>
                            <td>Abivax</td>
                            <td>Oral miR-124 enhancer (binds CBC/ARS2 complex)</td>
                            <td>Phase 3 (UC), Phase 2b (CD)</td>
                            <td>UC (NDA-track), Crohn&rsquo;s disease</td>
                            <td>Phase 3 induction positive. Maintenance data Q2 2026.</td>
                            <td>First-in-class. NDA planned H2 2026.</td>
                        </tr>
                        <tr>
                            <td><strong>FHND5032</strong></td>
                            <td>Formation Bio / Kenmare Bio (licensed from CTFH)</td>
                            <td>Oral miR-124 activator (small molecule)</td>
                            <td>Preclinical &rarr; Phase 1 planned 2026</td>
                            <td>Autoimmune diseases (UC studied preclinically)</td>
                            <td>Preclinical only. &ldquo;Well-characterized molecule with compelling preclinical profile.&rdquo;</td>
                            <td>Licensed Jan 29, 2026 for up to $500M. AI-driven development via Forge platform.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">The miR-124 space is currently a two-company landscape. Abivax is 5+ years ahead clinically with Phase 3 data in hand. Formation Bio&rsquo;s FHND5032 provides competitive validation of the mechanism and may eventually expand the market if it differentiates on indication, dosing, or combination potential.</p>
        </div>

        <!-- Section 4: IBD Competitive Landscape -->
        <div class="section">
            <h2>4. The IBD Competitive Landscape &mdash; Where miR-124 Fits</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Drug</th>
                            <th>Company</th>
                            <th>Mechanism</th>
                            <th>Route</th>
                            <th>Status in UC</th>
                            <th>Key Advantage</th>
                            <th>Key Limitation</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Infliximab (Remicade)</td>
                            <td>J&amp;J &rarr; biosimilars</td>
                            <td>Anti-TNF</td>
                            <td>IV</td>
                            <td>Approved (generic)</td>
                            <td>Long track record, cheap biosimilars</td>
                            <td>Loss of response, immunogenicity, infections</td>
                        </tr>
                        <tr>
                            <td>Adalimumab (Humira)</td>
                            <td>AbbVie &rarr; biosimilars</td>
                            <td>Anti-TNF</td>
                            <td>SC</td>
                            <td>Approved (generic)</td>
                            <td>Convenient SC, cheap biosimilars</td>
                            <td>Same anti-TNF limitations</td>
                        </tr>
                        <tr>
                            <td>Vedolizumab (Entyvio)</td>
                            <td>Takeda</td>
                            <td>&alpha;4&beta;7 integrin</td>
                            <td>IV/SC</td>
                            <td>Approved</td>
                            <td>Gut-selective, clean safety</td>
                            <td>Slower onset, modest efficacy vs newer agents</td>
                        </tr>
                        <tr>
                            <td>Tofacitinib (Xeljanz)</td>
                            <td>Pfizer</td>
                            <td>JAK inhibitor (pan-JAK)</td>
                            <td>Oral</td>
                            <td>Approved</td>
                            <td>Oral, fast onset</td>
                            <td>Boxed warning: CV, malignancy, thrombosis</td>
                        </tr>
                        <tr>
                            <td>Upadacitinib (Rinvoq)</td>
                            <td>AbbVie</td>
                            <td>JAK1-selective inhibitor</td>
                            <td>Oral</td>
                            <td>Approved</td>
                            <td>Oral, highest remission rates in UC</td>
                            <td>Same JAK class safety concerns</td>
                        </tr>
                        <tr>
                            <td>Risankizumab (Skyrizi)</td>
                            <td>AbbVie</td>
                            <td>Anti-IL-23 (p19)</td>
                            <td>IV &rarr; SC</td>
                            <td>Approved</td>
                            <td>Strong efficacy, clean safety</td>
                            <td>Injectable</td>
                        </tr>
                        <tr>
                            <td>Guselkumab (Tremfya)</td>
                            <td>J&amp;J</td>
                            <td>Anti-IL-23 (p19)</td>
                            <td>SC</td>
                            <td>Approved UC 2025</td>
                            <td>Dual mechanism (IL-23 + CD64)</td>
                            <td>Injectable</td>
                        </tr>
                        <tr>
                            <td>Mirikizumab (Omvoh)</td>
                            <td>Eli Lilly</td>
                            <td>Anti-IL-23 (p19)</td>
                            <td>IV &rarr; SC</td>
                            <td>Approved</td>
                            <td>Strong maintenance data</td>
                            <td>Injectable, IV induction</td>
                        </tr>
                        <tr>
                            <td>Tulisokibart</td>
                            <td>Merck</td>
                            <td>Anti-TL1A</td>
                            <td>SC</td>
                            <td>Phase 3</td>
                            <td>Novel mechanism (TL1A), strong Phase 2</td>
                            <td>Injectable, still in Phase 3</td>
                        </tr>
                        <tr>
                            <td>Duvakitug</td>
                            <td>Sanofi/Teva</td>
                            <td>Anti-TL1A</td>
                            <td>SC</td>
                            <td>Phase 3</td>
                            <td>Novel mechanism, Phase 3 enrolling</td>
                            <td>Injectable, still in Phase 3</td>
                        </tr>
                        <tr class="highlight-row">
                            <td><strong>Obefazimod</strong></td>
                            <td><strong>Abivax</strong></td>
                            <td><strong>miR-124 enhancer</strong></td>
                            <td><strong>Oral</strong></td>
                            <td><strong>Phase 3 (NDA planned H2 2026)</strong></td>
                            <td><strong>Novel MOA, oral, clean safety, works post-JAKi failure</strong></td>
                            <td><strong>Moderate remission rates vs JAKi; maintenance data pending</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Obefazimod&rsquo;s competitive advantage is the combination of oral administration, novel mechanism (works in JAK-failure patients &mdash; 47.3% of ABTECT population), and an exceptionally clean safety profile. In a field where the two best oral options (tofacitinib, upadacitinib) carry boxed warnings, a safe oral therapy with efficacy in advanced-therapy-experienced patients fills a clear unmet need.</p>
        </div>

        <!-- Section 5: Formation Bio -->
        <div class="section">
            <h2>5. Formation Bio &amp; Kenmare Bio &mdash; The AI-Pharma Entrant</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Formation Bio is a $1.7B AI-native pharmaceutical company backed by Sanofi and a16z. Their model: license clinical-stage or near-clinical assets, then develop them faster using AI &mdash; the Forge platform for trial design and operations, and Muse (in partnership with OpenAI) for drug candidate selection.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                On January 29, 2026, Formation licensed FHND5032 from Chia Tai Feng Hai (CTFH) for worldwide rights ex-China. They created a new subsidiary, <strong>Kenmare Bio</strong>, to house the asset. Deal terms include an undisclosed upfront payment, an equity stake to CTFH, milestones up to $500M, and royalties.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                FHND5032 is an oral small molecule miR-124 activator studied preclinically in ulcerative colitis models. Formation plans to enter the clinic in 2026 across &ldquo;a range of autoimmune diseases&rdquo; &mdash; potentially expanding the miR-124 thesis beyond IBD.
            </p>

            <div class="bio-box-amber">
                <h3>What This Deal Validates</h3>
                <p>The Formation Bio deal validates two things: (1) the miR-124 mechanism has value beyond Abivax &mdash; a $1.7B company with sophisticated drug-picking AI chose this mechanism, and (2) Formation sees enough whitespace to develop a second-in-class, potentially in indications beyond IBD where Abivax has not yet ventured.</p>
            </div>
        </div>

        <!-- Section 6: Anti-Fibrotic Signal -->
        <div class="section">
            <h2>6. The Anti-Fibrotic Signal &mdash; A Potential Game-Changer for Crohn&rsquo;s</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                At ECCO 2026 (February 21 &mdash; 11 days from now), Abivax is presenting an oral presentation titled <em>&ldquo;Obefazimod shows first evidence of anti-fibrotic activity in preclinical models of inflammatory bowel disease.&rdquo;</em> This is accompanied by 21 additional abstracts with expanded ABTECT data.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Intestinal fibrosis is a major complication of Crohn&rsquo;s disease that <strong>no current therapy adequately addresses</strong>. Fibrosis leads to strictures, bowel obstruction, and the need for surgery. Anti-TNFs, IL-23 inhibitors, and JAK inhibitors all reduce active inflammation but do not reverse established fibrosis. If obefazimod has anti-fibrotic properties on top of its anti-inflammatory activity, it would be meaningfully differentiated from every other IBD drug on the market or in development.
            </p>

            <div class="callout-box">
                <p><strong>Important caveat:</strong> This is a preclinical finding and must be confirmed in human studies. The ENHANCE-CD Phase 2b trial in Crohn&rsquo;s disease (initiated Oct 2024) may provide the first clinical signal. But if the anti-fibrotic effect translates, it opens a potentially massive additional market in stricturing Crohn&rsquo;s disease &mdash; a population with no effective medical therapy today.</p>
            </div>
        </div>

        <!-- Section 7: Bull/Bear -->
        <div class="section">
            <h2>7. Bull/Bear Case</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>Phase 3 induction data positive in both ABTECT-1 and ABTECT-2. NDA-track.</li>
                        <li>Novel mechanism &mdash; works in patients who failed JAK inhibitors (47.3% of trial population)</li>
                        <li>Oral administration with placebo-like safety profile across all studies</li>
                        <li>Anti-fibrotic signal could differentiate in Crohn&rsquo;s disease</li>
                        <li>Maintenance DSMB review clean (&gt;80% completion, no safety signals) &mdash; positive predictor</li>
                        <li>Formation Bio deal validates mechanism beyond a single company</li>
                        <li>IBD market expanding rapidly: UC market projected &gt;$15B by 2030</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Abivax is severely cash-constrained (~$71M as of Jun 2025). Required fundraising to reach maintenance data. Dilution risk ongoing.</li>
                        <li>16.4% placebo-adjusted remission is modest vs. upadacitinib (26.1% in U-ACHIEVE-1) and risankizumab (~20% in INSPIRE)</li>
                        <li>ABTECT-2 50mg (13.4%) was weaker than ABTECT-1 (19.3%) &mdash; inconsistency raises questions about true effect size</li>
                        <li>Maintenance data Q2 2026 is existential &mdash; if negative, entire program collapses</li>
                        <li>Crohn&rsquo;s disease Phase 2b hasn&rsquo;t read out. Crohn&rsquo;s is historically harder to treat than UC.</li>
                        <li>Competitive landscape is fierce: AbbVie (Rinvoq + Skyrizi), J&amp;J (Tremfya), Merck (tulisokibart), Sanofi (duvakitug) all advancing</li>
                        <li>miRNA-based therapies have a troubled history (MRX34 withdrawn). While obefazimod upregulates endogenous miR-124 (not a mimic), the association may concern investors.</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Section 8: Catalysts (shared system) -->
        {catalyst_html}

        <!-- Section 9: Sources -->
        <div class="section">
            <h2>Key Sources</h2>
            <ol class="source-list">
                <li>Abivax. &ldquo;ABTECT Phase 3 Induction Results in Ulcerative Colitis.&rdquo; Press release, Jul 22, 2025.</li>
                <li>Abivax. 2026 Corporate Outlook. Press release, Jan 2026.</li>
                <li>Abivax. &ldquo;22 Abstracts Accepted at ECCO 2026.&rdquo; Press release, Dec 17, 2025.</li>
                <li>Formation Bio. &ldquo;Formation Bio Licenses FHND5032 miR-124 Activator.&rdquo; Press release, Jan 29, 2026.</li>
                <li>FierceBiotech. &ldquo;Abivax aces pair of phase 3 ulcerative colitis trials.&rdquo; Jul 2025.</li>
                <li>FierceBiotech. &ldquo;Formation Bio&rsquo;s China shopping spree continues with miR-124 deal.&rdquo; Feb 2026.</li>
                <li>Vermeire S et al. &ldquo;Obefazimod 96-week open-label maintenance data in UC.&rdquo; <em>JCC</em> 2025.</li>
                <li>BioSpace. &ldquo;6 Biotechs That Could Be Big Pharma&rsquo;s Next M&amp;A Target.&rdquo; Dec 2025 (Abivax profile).</li>
            </ol>
        </div>

        <a href="/targets" class="back-link">&larr; Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''


def generate_stat6_report(admin: bool = False):
    """Generate the STAT6 degrader/inhibitor landscape report — analyst-grade."""

    # Catalyst section from shared system
    catalyst_html = render_catalyst_section("stat6", admin=admin)

    stat6_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section h3 { color: var(--navy); font-size: 1.1rem; margin: 24px 0 16px; }

        table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        th { background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }
        .table-footnote { font-size: 0.8rem; color: var(--text-secondary); margin-top: 12px; font-style: italic; line-height: 1.5; }

        .bio-box { background: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box h3 { color: #1e40af; margin-top: 0; }
        .bio-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-green { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-green h3 { color: #1B2838; margin-top: 0; }
        .bio-box-green p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-amber { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-amber h3 { color: #1B2838; margin-top: 0; }
        .bio-box-amber p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .deal-table td:nth-child(4) { font-weight: 600; color: var(--accent); }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }
        .catalyst-content strong { color: var(--navy); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }

        .source-list { list-style: decimal; padding-left: 24px; font-size: 0.85rem; color: var(--text-secondary); line-height: 2; }
        .source-list a { color: var(--accent); }

        .callout-box { background: #fef5f3; border: 1px solid #e07a5f; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .callout-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }
        .callout-box strong { color: var(--accent); }

        .data-table td:first-child { font-weight: 600; color: var(--navy); }
    """

    return f'''{_render_head("STAT6 Degraders & Inhibitors | Satya Bio", stat6_styles)}
    {_render_nav("targets")}
    <main class="main">

        <!-- Header -->
        <div class="report-header">
            <h1>STAT6 Degraders &amp; Inhibitors</h1>
            <p>The &ldquo;undruggable&rdquo; transcription factor that targeted protein degradation cracked open. Kymera&rsquo;s KT-621 matched dupilumab biomarkers from an oral pill. Sanofi, Gilead, and J&amp;J have all placed bets.</p>
            <div class="report-meta">
                <div class="meta-item">
                    <div class="label">Total Deal Value</div>
                    <div class="value">~$3.8B+</div>
                </div>
                <div class="meta-item">
                    <div class="label">Lead Asset</div>
                    <div class="value">KT-621 (Phase 2b)</div>
                </div>
                <div class="meta-item">
                    <div class="label">Dupilumab Revenue</div>
                    <div class="value">$13.6B (2024)</div>
                </div>
                <div class="meta-item">
                    <div class="label">Pivotal Readout</div>
                    <div class="value">Mid-2027</div>
                </div>
            </div>
        </div>

        <!-- Section 1: The Undruggable Target -->
        <div class="section">
            <h2>1. STAT6 &mdash; The Undruggable Target That Targeted Protein Degradation Cracked Open</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                STAT6 (Signal Transducer and Activator of Transcription 6) is the specific transcription factor downstream of IL-4 and IL-13 signaling &mdash; the central driver of Type 2 (Th2) inflammation. When IL-4 or IL-13 binds its receptor, JAK1/JAK3 or JAK1/TYK2 phosphorylate STAT6, which dimerizes, translocates to the nucleus, and drives transcription of the genes responsible for IgE class-switching, mucus production, eosinophil recruitment, and fibrosis. <strong>STAT6 is the bottleneck of the entire Type 2 pathway.</strong>
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Unlike JAK inhibitors (which block JAK1/2/3 broadly, affecting dozens of cytokine pathways and carrying boxed warnings for cardiovascular events, malignancy, and thrombosis), STAT6 is <strong>only used by IL-4 and IL-13</strong>. No other cytokines signal through STAT6. This means a STAT6-targeted drug could deliver the specificity of dupilumab (which blocks IL-4R&alpha;) but in an oral pill &mdash; without the broad immunosuppression that limits JAK inhibitors.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                For decades, STAT6 was considered &ldquo;undruggable.&rdquo; Transcription factors lack the deep hydrophobic pockets that small molecule inhibitors need. There is no enzymatic active site to block. The SH2 domain &mdash; the critical dimerization interface &mdash; is shallow and electrostatically charged, resisting conventional drug design.
            </p>

            <div class="bio-box-green">
                <h3>The Breakthrough: Targeted Protein Degradation</h3>
                <p>PROTACs (proteolysis-targeting chimeras) and molecular glues don&rsquo;t need to <em>inhibit</em> a protein &mdash; they just need to <em>bind</em> it and recruit an E3 ubiquitin ligase (such as cereblon/CRBN) to tag it for destruction by the proteasome. This opened STAT6 to drug development for the first time. Kymera&rsquo;s KT-621 is the <strong>first STAT6-directed drug to ever enter human clinical testing</strong>. Its Phase 1b data in December 2025 showed biologics-like activity from an oral pill &mdash; a potential paradigm shift for the $13.6B dupilumab franchise and the entire Type 2 inflammation field.</p>
            </div>
        </div>

        <!-- Section 2: The Dupilumab Benchmark -->
        <div class="section">
            <h2>2. The Dupilumab Benchmark &mdash; What STAT6 Drugs Are Trying to Replace</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Dupilumab (Dupixent, Sanofi/Regeneron) blocks IL-4R&alpha; upstream of STAT6. It is the most successful biologic in immunology: <strong>$13.6B+ revenue in 2024</strong>, approved across six indications &mdash; atopic dermatitis, asthma, CRSwNP, EoE, prurigo nodularis, and COPD. The COPD approval in 2024 alone added millions of potential patients. Dupilumab&rsquo;s clinical track record over 8+ years is exceptional: clean safety, durable efficacy, broad label expansion.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                But dupilumab is an injectable biologic: subcutaneous injection every 2 weeks, cold-chain storage, $36K+/year list price, and injection-site reactions in ~10% of patients. An oral STAT6 degrader with comparable efficacy would be transformative: easier administration, better patient adherence, lower manufacturing cost, no cold chain, and potential for broader market penetration &mdash; especially in pediatric populations, elderly patients, and developing markets where cold-chain biologics are impractical.
            </p>

            <div class="bio-box-amber">
                <h3>The Addressable Market Is Enormous</h3>
                <p>Type 2 inflammatory diseases affect <strong>&gt;140 million patients globally</strong>. Atopic dermatitis: ~230M globally. Asthma: ~300M (25M+ moderate-to-severe). CRSwNP: 30M+. EoE: growing recognition. Many of these patients are managed with topical steroids, inhalers, or no treatment at all. Only a fraction currently receive biologics. An oral pill with dupilumab-like efficacy could unlock the vast undertreated population that injectables cannot reach.</p>
            </div>
        </div>

        <!-- Section 3: Competitive Landscape -->
        <div class="section">
            <h2>3. Competitive Landscape</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Drug</th>
                            <th>Company</th>
                            <th>Modality</th>
                            <th>Target</th>
                            <th>Phase</th>
                            <th>Key Data</th>
                            <th>Differentiator</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>KT-621</strong></td>
                            <td>Kymera Therapeutics</td>
                            <td>Oral PROTAC degrader</td>
                            <td>STAT6 (via CRBN E3 ligase)</td>
                            <td>Phase 2b (AD + asthma)</td>
                            <td>Phase 1b: 94% STAT6 degradation skin, 98% blood; 63% EASI reduction; TARC &minus;74%; dupilumab-comparable at 4 wks. FDA Fast Track.</td>
                            <td><strong>FIRST-IN-CLASS.</strong> Only STAT6 drug with human clinical data. Oral once-daily. Two parallel Phase 2b trials.</td>
                        </tr>
                        <tr>
                            <td><strong>NX-3911</strong></td>
                            <td>Nurix / Sanofi</td>
                            <td>Oral PROTAC degrader</td>
                            <td>STAT6</td>
                            <td>Preclinical</td>
                            <td>Undisclosed</td>
                            <td>Sanofi partnership ($465M milestones). Nurix has multiple STAT6 candidates.</td>
                        </tr>
                        <tr>
                            <td><strong>REX-2787</strong></td>
                            <td>Recludix / Sanofi</td>
                            <td>Oral inhibitor (not degrader)</td>
                            <td>STAT6 (SH2 domain)</td>
                            <td>Preclinical &rarr; Phase 1 planned</td>
                            <td>Undisclosed. Uses phosphotyrosine mimetic chemistry.</td>
                            <td>$125M upfront, $1.2B milestones. Inhibitor approach (different from degrader). Sanofi takes over at Phase 2.</td>
                        </tr>
                        <tr>
                            <td><strong>Gilead / LEO program</strong></td>
                            <td>Gilead (systemic) + LEO (derm)</td>
                            <td>Oral degrader + inhibitor</td>
                            <td>STAT6</td>
                            <td>Preclinical</td>
                            <td>Undisclosed</td>
                            <td>$250M upfront, $1.7B total. Gilead gets systemic (asthma, COPD), LEO gets dermatology.</td>
                        </tr>
                        <tr>
                            <td><strong>KP-723</strong></td>
                            <td>J&amp;J / Kaken Pharmaceuticals</td>
                            <td>Oral inhibitor</td>
                            <td>STAT6</td>
                            <td>Preclinical/Phase 1</td>
                            <td>Undisclosed</td>
                            <td>J&amp;J licensed from Kaken. Inhibitor, not degrader.</td>
                        </tr>
                        <tr>
                            <td><strong>AK-1690</strong></td>
                            <td>Arkuda Therapeutics (tool)</td>
                            <td>Heterobifunctional degrader</td>
                            <td>STAT6</td>
                            <td>Research tool</td>
                            <td>Published in <em>J Med Chem</em> 2025 as highly potent, selective tool compound</td>
                            <td>Academic/tool &mdash; validates degrader approach</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Kymera is the only company with human clinical data. All competitors are preclinical or early Phase 1 at best. This ~2-year lead is significant in a field where Sanofi, Gilead, J&amp;J, and multiple biotechs are racing to enter.</p>
        </div>

        <!-- Section 4: Deal Landscape -->
        <div class="section">
            <h2>4. Deal Landscape &mdash; Big Pharma All-In on STAT6</h2>
            <div style="overflow-x: auto;">
                <table class="deal-table">
                    <thead>
                        <tr>
                            <th>Deal</th>
                            <th>Parties</th>
                            <th>Date</th>
                            <th>Value</th>
                            <th>Structure</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Gilead&ndash;LEO Pharma</td>
                            <td>Gilead + LEO Pharma</td>
                            <td>Jan 2025</td>
                            <td>Up to $1.7B ($250M upfront)</td>
                            <td>Gilead: systemic indications. LEO: dermatology. Both degraders and inhibitors.</td>
                        </tr>
                        <tr>
                            <td>Nurix&ndash;Sanofi</td>
                            <td>Nurix + Sanofi</td>
                            <td>Jun 2025</td>
                            <td>$15M upfront + $465M milestones</td>
                            <td>Sanofi funds NX-3911 development. Nurix retains other STAT6 candidates.</td>
                        </tr>
                        <tr>
                            <td>Sanofi&ndash;Recludix</td>
                            <td>Sanofi + Recludix</td>
                            <td>Oct 2025</td>
                            <td>$125M upfront + $1.2B milestones + royalties</td>
                            <td>Sanofi gets STAT6 inhibitor. Recludix develops through Phase 2, then Sanofi takes over.</td>
                        </tr>
                        <tr>
                            <td>J&amp;J&ndash;Kaken</td>
                            <td>J&amp;J + Kaken Pharmaceuticals</td>
                            <td>2025</td>
                            <td>Undisclosed</td>
                            <td>J&amp;J licenses KP-723 STAT6 inhibitor from Kaken.</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="callout-box">
                <p><strong>Sanofi&rsquo;s dual hedge:</strong> Sanofi has placed TWO separate STAT6 bets &mdash; a degrader (Nurix, $465M milestones) and an inhibitor (Recludix, $1.2B+ milestones) &mdash; totaling up to <strong>$1.68B</strong> in potential milestones. This is the clearest signal of conviction: Sanofi makes dupilumab ($13.6B/year) and is hedging against its own franchise by investing in the oral small molecule that could replace it. Gilead and J&amp;J have also entered. Only Kymera has clinical data.</p>
            </div>
        </div>

        <!-- Section 5: Degrader vs Inhibitor -->
        <div class="section">
            <h2>5. Degrader vs. Inhibitor &mdash; The Modality Debate</h2>

            <div class="bio-box-green">
                <h3>Degraders (KT-621, NX-3911, Gilead program)</h3>
                <p>Destroy the entire STAT6 protein via the proteasome. Act catalytically &mdash; one drug molecule can degrade multiple STAT6 proteins before being recycled. Don&rsquo;t need high-affinity binding to a functional pocket; they just need enough affinity to form a ternary complex with an E3 ligase. Result: potentially <strong>more complete pathway blockade</strong> than occupancy-based inhibition.</p>
            </div>

            <div class="bio-box">
                <h3>Inhibitors (REX-2787, KP-723)</h3>
                <p>Block STAT6&rsquo;s SH2 domain to prevent phosphorylation and dimerization. Must maintain high occupancy to be effective &mdash; the drug must continuously outcompete the natural phosphotyrosine ligand. STAT6&rsquo;s SH2 domain is shallow and electrostatically charged, historically resisting conventional small molecule design. Recludix used phosphotyrosine mimetic chemistry to overcome this challenge.</p>
            </div>

            <h3>Why Degraders May Win</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                STAT6 exists in large unphosphorylated pools in the cell. Inhibitors only block signaling when STAT6 is actively phosphorylated &mdash; they cannot address the reservoir of inactive protein that can be rapidly activated upon cytokine stimulation. Degraders eliminate <strong>all STAT6 &mdash; active and inactive pools</strong> &mdash; for more complete pathway shutdown. KT-621&rsquo;s clinical data support this thesis: 94&ndash;98% protein elimination is extraordinarily difficult to achieve with occupancy-based inhibition alone.
            </p>

            <h3>Why Inhibitors May Still Matter</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                Simpler medicinal chemistry. Potentially faster development timelines. No dependence on cereblon (CRBN) E3 ligase biology &mdash; avoiding theoretical risks of cereblon modulation with chronic dosing. If partial STAT6 blockade is sufficient for clinical efficacy, inhibitors could have a better therapeutic window. The field will ultimately be settled by clinical data.
            </p>
        </div>

        <!-- Section 6: KT-621 Deep Dive -->
        <div class="section">
            <h2>6. KT-621 Deep Dive &mdash; The Data That Changed the Field</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                On December 8, 2025, Kymera reported BroADen Phase 1b results in patients with moderate-to-severe atopic dermatitis. The data exceeded expectations and triggered a stock surge, an upsized $602M offering, and FDA Fast Track designation within 3 days.
            </p>
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Endpoint</th>
                            <th>KT-621 (100mg + 200mg pooled)</th>
                            <th>Context vs. Dupilumab at 4 Weeks</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>STAT6 degradation (skin)</td>
                            <td><strong>94%</strong> median reduction</td>
                            <td>N/A &mdash; dupilumab does not degrade STAT6</td>
                        </tr>
                        <tr>
                            <td>STAT6 degradation (blood)</td>
                            <td><strong>98%</strong> median reduction</td>
                            <td>N/A</td>
                        </tr>
                        <tr>
                            <td>TARC (key Type 2 biomarker)</td>
                            <td><strong>&minus;74%</strong> median</td>
                            <td>Comparable to dupilumab at 4 weeks</td>
                        </tr>
                        <tr>
                            <td>Eotaxin-3</td>
                            <td>Significant reduction</td>
                            <td>Comparable</td>
                        </tr>
                        <tr>
                            <td>IgE</td>
                            <td>Significant reduction</td>
                            <td>Comparable</td>
                        </tr>
                        <tr>
                            <td>IL-31 (itch mediator)</td>
                            <td>First-ever demonstration of IL-31 reduction via IL-4/13 pathway blockade in AD</td>
                            <td>Novel finding</td>
                        </tr>
                        <tr>
                            <td>FeNO (comorbid asthma)</td>
                            <td><strong>&minus;56%</strong> median in asthma patients</td>
                            <td>Comparable to dupilumab</td>
                        </tr>
                        <tr>
                            <td>EASI score</td>
                            <td><strong>&minus;63%</strong> mean reduction</td>
                            <td>In line with dupilumab at 4 weeks</td>
                        </tr>
                        <tr>
                            <td>Peak pruritus NRS (itch)</td>
                            <td><strong>&minus;40%</strong> mean reduction</td>
                            <td>In line</td>
                        </tr>
                        <tr>
                            <td>Safety</td>
                            <td>Favorable, no new signals</td>
                            <td>Safety profile undifferentiated from placebo in Phase 1</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Cross-trial comparisons are directionally informative only. KT-621 BroADen was a small, open-label Phase 1b study &mdash; not a randomized controlled trial. The true test is BROADEN2 (Phase 2b, randomized, placebo-controlled, ~200 patients, 16 weeks, data expected mid-2027).</p>
        </div>

        <!-- Section 7: Market Opportunity -->
        <div class="section">
            <h2>7. Market Opportunity</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Indication</th>
                            <th>Global Prevalence</th>
                            <th>Current SOC</th>
                            <th>KT-621 Status</th>
                            <th>Peak Sales Potential</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Atopic Dermatitis</strong></td>
                            <td>~230M globally</td>
                            <td>Dupilumab, JAKi (upadacitinib), topicals</td>
                            <td>Phase 2b (BROADEN2, data mid-2027)</td>
                            <td>$5&ndash;10B+ (oral dupilumab equivalent)</td>
                        </tr>
                        <tr>
                            <td><strong>Asthma (moderate-severe)</strong></td>
                            <td>~300M globally, ~25M moderate-severe</td>
                            <td>Dupilumab, tezepelumab, mepolizumab</td>
                            <td>Phase 2b (BREADTH, data late 2027)</td>
                            <td>$3&ndash;5B+</td>
                        </tr>
                        <tr>
                            <td><strong>COPD (Type 2 high)</strong></td>
                            <td>~380M globally</td>
                            <td>Dupilumab (approved 2024)</td>
                            <td>Planned</td>
                            <td>$2&ndash;4B+</td>
                        </tr>
                        <tr>
                            <td><strong>EoE</strong></td>
                            <td>~160K diagnosed US</td>
                            <td>Dupilumab</td>
                            <td>Planned</td>
                            <td>$1&ndash;2B</td>
                        </tr>
                        <tr>
                            <td><strong>CRSwNP</strong></td>
                            <td>~30M globally</td>
                            <td>Dupilumab</td>
                            <td>Planned</td>
                            <td>$1&ndash;2B</td>
                        </tr>
                        <tr>
                            <td><strong>CSU, PN, BP</strong></td>
                            <td>Millions combined</td>
                            <td>Various biologics</td>
                            <td>Planned</td>
                            <td>$1&ndash;3B combined</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Kymera has stated its strategy is to select doses from BROADEN2 and BREADTH for subsequent PARALLEL Phase 3 registration studies across multiple indications simultaneously. A single Phase 2b readout could unlock 3&ndash;5 indications in parallel &mdash; the leverage is enormous.</p>
        </div>

        <!-- Section 8: Bull/Bear -->
        <div class="section">
            <h2>8. Bull/Bear Case</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>KT-621 Phase 1b data matched dupilumab at 4 weeks &mdash; from an oral pill</li>
                        <li>Only company with human clinical data. 2+ year lead over all competitors.</li>
                        <li>$602M raised Dec 2025, funded through mid-2027 data readouts</li>
                        <li>FDA Fast Track granted</li>
                        <li>Sanofi&rsquo;s dual STAT6 bets ($1.68B in milestones) validate the target and the opportunity</li>
                        <li>If BROADEN2 confirms Phase 1b signal, KT-621 becomes the most valuable oral immunology asset in development. Peak sales potential &gt;$10B across indications.</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Phase 1b was open-label, small (n=~30&ndash;40), 28-day dosing only. Phase 2b (randomized, 16-week, placebo-controlled) is the real test.</li>
                        <li>STAT6 degradation &ne; clinical efficacy. Need to prove dose-response and durability.</li>
                        <li>Safety over longer exposure is unknown. PROTAC degraders are a new modality &mdash; long-term effects of chronic STAT6 elimination are unstudied.</li>
                        <li>Dupilumab&rsquo;s safety record over 8+ years is extremely clean. KT-621 must match this bar.</li>
                        <li>Competition is real: Sanofi, Gilead, J&amp;J all developing STAT6 drugs. First-mover advantage may erode.</li>
                        <li>Kymera market cap ~$7&ndash;8B &mdash; significant de-rating risk if BROADEN2 disappoints.</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Section 9: Catalysts (shared system) -->
        {catalyst_html}

        <!-- Section 10: Sources -->
        <div class="section">
            <h2>Key Sources</h2>
            <ol class="source-list">
                <li>Kymera Therapeutics. &ldquo;BroADen Phase 1b Positive Results in Atopic Dermatitis.&rdquo; Press release, Dec 8, 2025.</li>
                <li>Kymera Therapeutics. &ldquo;FDA Grants Fast Track Designation for KT-621 in Moderate-to-Severe Atopic Dermatitis.&rdquo; Press release, Dec 11, 2025.</li>
                <li>Kymera Therapeutics. &ldquo;BREADTH Phase 2b Trial in Asthma &mdash; First Patient Dosed.&rdquo; Press release, Jan 29, 2026.</li>
                <li>Kymera Therapeutics. 2026 Corporate Outlook. Jan 2026.</li>
                <li>Gilead Sciences &amp; LEO Pharma. &ldquo;Global Agreement for Oral STAT6 Degraders and Inhibitors.&rdquo; Jan 2025.</li>
                <li>Sanofi &amp; Recludix Pharma. &ldquo;License Agreement for REX-2787 Oral STAT6 Inhibitor.&rdquo; Oct 2025.</li>
                <li>&ldquo;Turning Off STAT6 with a Targeted Degrader&rdquo; (AK-1690 tool compound). <em>J Med Chem</em> 2025.</li>
                <li>Labiotech.eu. &ldquo;From undruggable to oral therapy: The rise of STAT6 degraders.&rdquo; Jun 2025.</li>
            </ol>
        </div>

        <a href="/targets" class="back-link">&larr; Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''


def generate_cell_therapy_report(admin: bool = False):
    """Generate the Cell Therapy / In Vivo CAR-T landscape report — analyst-grade."""

    # Catalyst section from shared system
    catalyst_html = render_catalyst_section("cell-therapy", admin=admin)

    cell_therapy_styles = """
        .report-header {
            background: linear-gradient(135deg, #1a2b3c 0%, #2d4a6f 100%);
            color: white;
            padding: 48px 32px;
            margin: -32px -32px 32px;
            border-radius: 0 0 24px 24px;
        }
        .report-header h1 { font-size: 2.25rem; margin-bottom: 8px; }
        .report-header p { opacity: 0.85; max-width: 700px; font-size: 1.1rem; }
        .report-meta { display: flex; gap: 24px; margin-top: 24px; flex-wrap: wrap; }
        .meta-item { background: rgba(255,255,255,0.15); padding: 12px 20px; border-radius: 8px; }
        .meta-item .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; }
        .meta-item .value { font-size: 1.25rem; font-weight: 700; }

        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; margin-bottom: 24px; }
        .section h2 { color: var(--navy); font-size: 1.35rem; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
        .section h3 { color: var(--navy); font-size: 1.1rem; margin: 24px 0 16px; }

        table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
        th { background: var(--navy); color: white; padding: 12px 10px; text-align: left; font-weight: 600; }
        td { padding: 12px 10px; border-bottom: 1px solid var(--border); }
        tr:hover { background: var(--bg); }
        .table-footnote { font-size: 0.8rem; color: var(--text-secondary); margin-top: 12px; font-style: italic; line-height: 1.5; }

        .bio-box { background: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box h3 { color: #1e40af; margin-top: 0; }
        .bio-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-green { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-green h3 { color: #1B2838; margin-top: 0; }
        .bio-box-green p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-amber { background: #f5f3f0; border: 1px solid #e0ddd8; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-amber h3 { color: #1B2838; margin-top: 0; }
        .bio-box-amber p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .bio-box-red { background: #f5f3f0; border: 1px solid #D4654A; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .bio-box-red h3 { color: #1B2838; margin-top: 0; }
        .bio-box-red p { color: #374151; font-size: 0.9rem; line-height: 1.7; }

        .thesis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        @media (max-width: 768px) { .thesis-grid { grid-template-columns: 1fr; } }
        .bull-box, .bear-box { padding: 24px; border-radius: 0; background: #ffffff; border: 1px solid #e5e5e0; }
        .bull-box { border-left: 3px solid #e07a5f; }
        .bear-box { border-left: 3px solid #1a2b3c; }
        .bull-box h3 { color: #e07a5f; }
        .bear-box h3 { color: #1a2b3c; }
        .thesis-list { list-style: none; padding: 0; margin-top: 16px; }
        .thesis-list li { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); font-size: 0.9rem; display: flex; align-items: flex-start; gap: 10px; }
        .thesis-list li:last-child { border-bottom: none; }
        .thesis-list li::before { content: "\\2192"; font-weight: bold; }

        .deal-table td:nth-child(4) { font-weight: 600; color: var(--accent); }

        .catalyst-timeline { margin-top: 20px; }
        .catalyst-item { display: flex; align-items: flex-start; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--border); }
        .catalyst-date { min-width: 100px; font-weight: 700; color: var(--accent); }
        .catalyst-content strong { color: var(--navy); }

        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--accent); text-decoration: none; margin-top: 24px; font-weight: 500; }
        .back-link:hover { text-decoration: underline; }

        .source-list { list-style: decimal; padding-left: 24px; font-size: 0.85rem; color: var(--text-secondary); line-height: 2; }
        .source-list a { color: var(--accent); }

        .callout-box { background: #fef5f3; border: 1px solid #e07a5f; border-radius: 12px; padding: 24px; margin: 20px 0; }
        .callout-box p { color: #374151; font-size: 0.9rem; line-height: 1.7; }
        .callout-box strong { color: var(--accent); }
    """

    return f'''{_render_head("Cell Therapy: Ex Vivo vs In Vivo | Satya Bio", cell_therapy_styles)}
    {_render_nav("targets")}
    <main class="main">

        <!-- Header -->
        <div class="report-header">
            <h1>Cell Therapy: The In Vivo Revolution</h1>
            <p>Five Big Pharma companies have spent $7B+ acquiring in vivo cell therapy companies in 12 months. Ex vivo CAR-T economics are broken for chronic disease. The modality is shifting.</p>
            <div class="report-meta">
                <div class="meta-item">
                    <div class="label">In Vivo M&amp;A (12mo)</div>
                    <div class="value">~$7B+</div>
                </div>
                <div class="meta-item">
                    <div class="label">Approved Ex Vivo CAR-Ts</div>
                    <div class="value">6 products</div>
                </div>
                <div class="meta-item">
                    <div class="label">Key Inflection</div>
                    <div class="value">Lilly&ndash;Orna $2.4B</div>
                </div>
                <div class="meta-item">
                    <div class="label">Latest Deal</div>
                    <div class="value">Feb 9, 2026</div>
                </div>
            </div>
        </div>

        <!-- Section 1: The Modality Shift -->
        <div class="section">
            <h2>1. The Modality Shift: Why Big Pharma Is Abandoning Ex Vivo and Betting $7B+ on In Vivo</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                In the past 12 months, the cell therapy field has undergone a dramatic inflection. Three companies &mdash; Takeda, Novo Nordisk, and Galapagos &mdash; divested from cell therapy programs entirely. Gilead, the commercial leader in ex vivo CAR-T, reported declining sales for Yescarta and Tecartus. And yet, in the same period, <strong>five Big Pharma companies collectively spent over $7 billion acquiring in vivo cell therapy companies</strong>.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                This is not a rejection of cell therapy. It is a rejection of the <em>ex vivo modality&rsquo;s economics and logistics</em> for chronic disease. The therapeutic principle &mdash; targeted depletion of pathogenic cell populations &mdash; remains powerful. What&rsquo;s changing is <strong>how</strong> that depletion is achieved.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                The pattern is unmistakable: AstraZeneca&ndash;EsoBiotec ($1B, Jan 2025), AbbVie&ndash;Capstan ($2.1B, Jun 2025), Gilead&ndash;Interius (2025), BMS&ndash;Orbital ($1.5B, Oct 2025), and Eli Lilly&ndash;Orna ($2.4B, Feb 9, 2026). Every deal targets the same thesis: <em>in vivo</em> genetic reprogramming of a patient&rsquo;s own T-cells, bypassing the manufacturing bottleneck that has constrained ex vivo CAR-T since its inception.
            </p>

            <div class="callout-box">
                <p><strong>Yesterday&rsquo;s deal (Feb 9, 2026):</strong> Eli Lilly announced the acquisition of Orna Therapeutics for up to $2.4 billion. Orna&rsquo;s platform uses engineered circular RNA (oRNA) delivered via lipid nanoparticles to transiently express CAR constructs on a patient&rsquo;s T-cells <em>in vivo</em>. Lead asset ORN-252 (CD19) is described as &ldquo;clinical-trial ready&rdquo; for B-cell-mediated autoimmune diseases. This is Lilly&rsquo;s first major move into cell therapy &mdash; and the fifth in vivo deal in 12 months.</p>
            </div>
        </div>

        <!-- Section 2: Ex Vivo CAR-T Broken Economics -->
        <div class="section">
            <h2>2. Ex Vivo CAR-T: Transformative Science, Broken Economics</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Approved ex vivo CAR-T products have transformed hematologic oncology. Six FDA-approved products are now on the market, delivering complete response rates of 40&ndash;70% in malignancies that previously had no effective options. For patients with relapsed/refractory large B-cell lymphoma or multiple myeloma, CAR-T therapy has been genuinely curative in a meaningful fraction.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                But the modality is fundamentally constrained by four interlocking problems:
            </p>

            <div class="bio-box-red">
                <h3>Manufacturing</h3>
                <p>Each treatment is a bespoke, patient-specific manufacturing process. Leukapheresis &rarr; shipping &rarr; viral vector transduction &rarr; expansion &rarr; quality testing &rarr; shipping back &rarr; infusion. Vein-to-vein time: <strong>3&ndash;6 weeks</strong>. Some patients progress and die while waiting for their cells.</p>
            </div>
            <div class="bio-box-red">
                <h3>Cost</h3>
                <p>$373K&ndash;$475K per treatment for the CAR-T product alone. Add hospitalization, lymphodepleting chemotherapy, CRS/ICANS management, and the total cost often exceeds <strong>$500K per patient</strong>. Payers are reluctant to expand coverage beyond last-line hematologic malignancies.</p>
            </div>
            <div class="bio-box-red">
                <h3>Safety</h3>
                <p>Cytokine release syndrome (CRS) in 60&ndash;90% of patients. Immune effector cell-associated neurotoxicity syndrome (ICANS) in 20&ndash;60%. Grade 3+ CRS in 5&ndash;20%. Requires inpatient monitoring, often ICU-level. In November 2023, <strong>FDA added a boxed warning</strong> for secondary T-cell malignancies across all approved CAR-T products.</p>
            </div>
            <div class="bio-box-amber">
                <h3>Scalability &amp; Commercial Reality</h3>
                <p>Manufacturing infrastructure cannot scale to meet demand. Treatment slots are rationed. Total ex vivo CAR-T market is ~$4&ndash;5B globally in 2025, well below initial projections. Gilead&rsquo;s Yescarta/Tecartus are declining ~10&ndash;15% YoY. BMS&rsquo;s Abecma is being cannibalized by J&amp;J&rsquo;s Carvykti. <strong>Carvykti is the only product with strong growth trajectory.</strong></p>
            </div>
        </div>

        <!-- Section 3: The Autoimmune Opportunity -->
        <div class="section">
            <h2>3. The Autoimmune Opportunity Changes Everything</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                The catalyst for the in vivo revolution came from an unexpected direction: autoimmune disease. In 2022, Mackensen et al. published landmark data in the <em>New England Journal of Medicine</em> showing that CD19 CAR-T therapy achieved <strong>complete B-cell depletion and drug-free remission</strong> in patients with severe systemic lupus erythematosus. Patients went off all immunosuppressive medication &mdash; unprecedented in rheumatology.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Subsequent studies confirmed the same pattern in systemic sclerosis, myasthenia gravis, and inflammatory myopathy. The immunological reset provided by deep B-cell depletion appeared to break the cycle of autoimmunity in ways that chronic immunosuppression never could.
            </p>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                But the risk-benefit calculus is entirely different in autoimmune disease vs. oncology. Cancer patients accept lymphodepleting chemotherapy, weeks of hospitalization, CRS risk, and T-cell malignancy warnings because the alternative is death. Autoimmune patients have chronic, manageable disease. <strong>They will not accept $500K, 3&ndash;6 weeks inpatient, chemotherapy conditioning, and T-cell malignancy risk for a disease they can manage with existing drugs.</strong>
            </p>

            <div class="bio-box-green">
                <h3>Why In Vivo CAR-T Is Essential for Autoimmune</h3>
                <p>The autoimmune market is <strong>10&ndash;100x larger</strong> than hematologic malignancies. Lupus alone: ~200K patients in the US. Rheumatoid arthritis: 1.3M. Multiple sclerosis: 1M. But this market is only addressable with a modality that is: off-the-shelf, outpatient, requires no lymphodepletion or leukapheresis, is redosable, and is affordable. Total addressable autoimmune market for cell therapies: estimated <strong>$50&ndash;100B+</strong> if the modality works.</p>
            </div>
        </div>

        <!-- Section 4: In Vivo CAR-T How It Works -->
        <div class="section">
            <h2>4. In Vivo CAR-T: How It Works</h2>
            <p style="font-size: 0.95rem; line-height: 1.8; color: #374151; margin-bottom: 16px;">
                Three main approaches to in vivo cell therapy are being pursued, each with distinct trade-offs:
            </p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Approach</th>
                            <th>How It Works</th>
                            <th>Key Companies</th>
                            <th>Advantages</th>
                            <th>Risks</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>LNP + mRNA/circRNA</strong></td>
                            <td>Lipid nanoparticles deliver mRNA or circular RNA encoding CAR construct. Patient&rsquo;s own T-cells transiently express CAR.</td>
                            <td>Orna (Lilly), Capstan (AbbVie), Orbital (BMS)</td>
                            <td>Off-the-shelf, no genomic integration, redosable, transient expression (safety advantage)</td>
                            <td>Transient = may need redosing. LNP tropism challenges (getting to T-cells, not liver).</td>
                        </tr>
                        <tr>
                            <td><strong>Lentiviral in vivo</strong></td>
                            <td>Engineered lentiviral vectors delivered IV that selectively transduce T-cells in vivo, integrating CAR gene permanently.</td>
                            <td>Umoja Biopharma, EsoBiotec (AZ)</td>
                            <td>Permanent integration (one-shot potential), proven vector biology</td>
                            <td>Insertional mutagenesis risk (like ex vivo). Manufacturing complexity of viral vectors.</td>
                        </tr>
                        <tr>
                            <td><strong>T-cell engagers (alternative)</strong></td>
                            <td>Bispecific antibodies that redirect T-cells to target (e.g., CD19&times;CD3) without any genetic modification.</td>
                            <td>Regeneron, multiple companies</td>
                            <td>Off-the-shelf, simple IV infusion, no genetic modification, proven modality</td>
                            <td>Continuous dosing required, no T-cell memory, CRS still occurs, not true cell therapy.</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="bio-box">
                <h3>Circular RNA: Orna&rsquo;s Key Differentiator</h3>
                <p>Orna&rsquo;s platform uses engineered circular RNA (oRNA), which forms a covalently closed loop that is significantly more stable than linear mRNA. Linear mRNA is degraded by exonucleases within hours; circular RNA lacks free 5&prime; and 3&prime; ends, making it resistant to this degradation. This means <strong>longer protein expression from each dose</strong> &mdash; potentially bridging the gap between transient mRNA (hours-to-days) and permanent viral integration (forever). For autoimmune disease, where the goal is a transient B-cell depletion that allows immune reconstitution, this &ldquo;Goldilocks&rdquo; duration may be ideal.</p>
            </div>
        </div>

        <!-- Section 5: M&A Deal Landscape -->
        <div class="section">
            <h2>5. The $7B+ In Vivo M&amp;A Wave &mdash; Deal Landscape</h2>
            <div style="overflow-x: auto;">
                <table class="deal-table">
                    <thead>
                        <tr>
                            <th>Deal</th>
                            <th>Buyer</th>
                            <th>Target</th>
                            <th>Value</th>
                            <th>Date</th>
                            <th>Technology</th>
                            <th>Lead Program</th>
                            <th>Target Indication</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>AZ&ndash;EsoBiotec</td>
                            <td>AstraZeneca</td>
                            <td>EsoBiotec</td>
                            <td>~$1B ($425M upfront)</td>
                            <td>Early 2025</td>
                            <td>Lentiviral in vivo</td>
                            <td>CD19 CAR-T</td>
                            <td>Autoimmune</td>
                        </tr>
                        <tr>
                            <td>AbbVie&ndash;Capstan</td>
                            <td>AbbVie</td>
                            <td>Capstan Therapeutics</td>
                            <td>$2.1B</td>
                            <td>Jun 2025</td>
                            <td>LNP-delivered in vivo CAR-T</td>
                            <td>CD19 in vivo CAR-T</td>
                            <td>Autoimmune</td>
                        </tr>
                        <tr>
                            <td>Gilead&ndash;Interius</td>
                            <td>Gilead</td>
                            <td>Interius BioTherapeutics</td>
                            <td>Undisclosed</td>
                            <td>2025</td>
                            <td>In vivo CAR-T</td>
                            <td>Undisclosed</td>
                            <td>Autoimmune (likely)</td>
                        </tr>
                        <tr>
                            <td>BMS&ndash;Orbital</td>
                            <td>BMS</td>
                            <td>Orbital Therapeutics</td>
                            <td>$1.5B</td>
                            <td>Oct 2025</td>
                            <td>Circular RNA platform</td>
                            <td>Engineered RNA cell therapies</td>
                            <td>Autoimmune + Oncology</td>
                        </tr>
                        <tr>
                            <td><strong>Lilly&ndash;Orna</strong></td>
                            <td><strong>Eli Lilly</strong></td>
                            <td><strong>Orna Therapeutics</strong></td>
                            <td><strong>Up to $2.4B</strong></td>
                            <td><strong>Feb 9, 2026</strong></td>
                            <td><strong>Circular RNA + LNP</strong></td>
                            <td><strong>ORN-252 (CD19 in vivo CAR-T)</strong></td>
                            <td><strong>B-cell autoimmune</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Every major pharma is now placing a bet in this space. AstraZeneca, AbbVie, Gilead, BMS, and Lilly have collectively deployed ~$7B+ in 12 months on in vivo cell therapy acquisitions. Notably, Gilead &mdash; the largest ex vivo CAR-T commercial player (Yescarta, Tecartus) &mdash; also acquired an in vivo company, signaling that even the incumbent recognizes the modality shift.</p>
        </div>

        <!-- Section 6: Competitive Landscape -->
        <div class="section">
            <h2>6. Competitive Landscape &mdash; Who Has What</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Approach</th>
                            <th>Key Asset</th>
                            <th>Target</th>
                            <th>Stage</th>
                            <th>RNA Type</th>
                            <th>Delivery</th>
                            <th>Autoimmune Focus</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Eli Lilly (Orna)</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>ORN-252</td>
                            <td>CD19</td>
                            <td>Phase 1-ready (IND exp H1 2026)</td>
                            <td>Circular RNA (oRNA)</td>
                            <td>Proprietary LNP</td>
                            <td>Yes &mdash; B-cell autoimmune</td>
                        </tr>
                        <tr>
                            <td><strong>AbbVie (Capstan)</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>Undisclosed</td>
                            <td>CD19 (likely)</td>
                            <td>Preclinical/IND-enabling</td>
                            <td>mRNA</td>
                            <td>LNP</td>
                            <td>Yes &mdash; autoimmune</td>
                        </tr>
                        <tr>
                            <td><strong>AstraZeneca (EsoBiotec)</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>Undisclosed</td>
                            <td>CD19 (likely)</td>
                            <td>Early clinical</td>
                            <td>Lentiviral</td>
                            <td>Lentiviral vector</td>
                            <td>Yes &mdash; autoimmune</td>
                        </tr>
                        <tr>
                            <td><strong>BMS (Orbital)</strong></td>
                            <td>Engineered RNA</td>
                            <td>Undisclosed</td>
                            <td>Multiple</td>
                            <td>Preclinical</td>
                            <td>Circular RNA</td>
                            <td>TBD</td>
                            <td>Yes + Oncology</td>
                        </tr>
                        <tr>
                            <td><strong>Gilead (Interius)</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>Undisclosed</td>
                            <td>Undisclosed</td>
                            <td>Preclinical</td>
                            <td>TBD</td>
                            <td>TBD</td>
                            <td>Likely autoimmune</td>
                        </tr>
                        <tr>
                            <td><strong>Umoja Biopharma</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>UB-VV111</td>
                            <td>CD19</td>
                            <td>Phase 1 (r/r NHL)</td>
                            <td>N/A</td>
                            <td>Lentiviral (VivoVec)</td>
                            <td>Oncology first, autoimmune planned</td>
                        </tr>
                        <tr>
                            <td><strong>Sana Biotechnology</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>Multiple</td>
                            <td>CD19</td>
                            <td>Preclinical</td>
                            <td>Fusogen-delivered</td>
                            <td>Engineered fusogens</td>
                            <td>Yes &mdash; autoimmune</td>
                        </tr>
                        <tr>
                            <td><strong>Kelonia Therapeutics</strong></td>
                            <td>In vivo CAR-T</td>
                            <td>Undisclosed</td>
                            <td>Multiple</td>
                            <td>Preclinical</td>
                            <td>N/A</td>
                            <td>Retroviral</td>
                            <td>Oncology + autoimmune</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Nearly every approach converges on CD19 as the initial target &mdash; the same antigen used in approved ex vivo CAR-T products. This de-risks the biology (CD19 depletion is well-characterized) and focuses competition on the delivery modality itself.</p>
        </div>

        <!-- Section 7: Approved Ex Vivo CAR-T Products -->
        <div class="section">
            <h2>7. Ex Vivo CAR-T &mdash; Approved Products and Commercial Reality</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Company</th>
                            <th>Target</th>
                            <th>Indication</th>
                            <th>Year Approved</th>
                            <th>List Price</th>
                            <th>2025 Revenue Est</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Kymriah</strong></td>
                            <td>Novartis</td>
                            <td>CD19</td>
                            <td>ALL, DLBCL</td>
                            <td>2017</td>
                            <td>$475K</td>
                            <td>~$500M (declining)</td>
                        </tr>
                        <tr>
                            <td><strong>Yescarta</strong></td>
                            <td>Gilead/Kite</td>
                            <td>CD19</td>
                            <td>LBCL, FL</td>
                            <td>2017</td>
                            <td>$373K</td>
                            <td>~$1.2B (declining)</td>
                        </tr>
                        <tr>
                            <td><strong>Tecartus</strong></td>
                            <td>Gilead/Kite</td>
                            <td>CD19</td>
                            <td>MCL, ALL</td>
                            <td>2020</td>
                            <td>$373K</td>
                            <td>~$200M (declining)</td>
                        </tr>
                        <tr>
                            <td><strong>Breyanzi</strong></td>
                            <td>BMS</td>
                            <td>CD19</td>
                            <td>LBCL</td>
                            <td>2021</td>
                            <td>$410K</td>
                            <td>~$600M</td>
                        </tr>
                        <tr>
                            <td><strong>Abecma</strong></td>
                            <td>BMS</td>
                            <td>BCMA</td>
                            <td>Multiple myeloma</td>
                            <td>2021</td>
                            <td>$419K</td>
                            <td>~$400M (losing to Carvykti)</td>
                        </tr>
                        <tr>
                            <td><strong>Carvykti</strong></td>
                            <td>J&amp;J/Legend</td>
                            <td>BCMA</td>
                            <td>Multiple myeloma</td>
                            <td>2022</td>
                            <td>$465K</td>
                            <td>~$1.5B (growing)</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="table-footnote">Total ex vivo CAR-T market ~$4&ndash;5B globally in 2025. Carvykti is the only product with strong growth trajectory. The others are flat or declining, constrained by manufacturing capacity, high cost, and competition from bispecific T-cell engagers.</p>
        </div>

        <!-- Section 8: The Debate -->
        <div class="section">
            <h2>8. The Debate: In Vivo CAR-T vs. T-Cell Engagers vs. Ex Vivo CAR-T</h2>

            <h3>Ex vivo CAR-T advocates say:</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                Proven deep and durable responses in cancer. Permanent genomic integration means true one-shot potential. Growing autoimmune data &mdash; Mackensen&rsquo;s lupus data showed drug-free remission, and Kyverna&rsquo;s KYV-101 is in clinical trials for myasthenia gravis. Manufacturing will improve over time with automation and allogeneic approaches.
            </p>

            <h3>T-cell engager advocates say:</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                Already commercial &mdash; Tecvayli, Elrexfio, and Columvi are approved bispecific T-cell engagers in hematologic malignancies. Off-the-shelf, no genetic modification, simpler manufacturing. Growing autoimmune pipeline (CD19&times;CD3 bispecifics). But: require continuous dosing, produce no T-cell memory, and CRS still occurs. Not true cell therapy &mdash; they redirect existing T-cells rather than reprogram them.
            </p>

            <h3>In vivo CAR-T advocates say:</h3>
            <p style="font-size: 0.9rem; line-height: 1.7; color: #374151; margin-bottom: 16px;">
                Combines the best of both &mdash; the genetic programming of CAR-T with the off-the-shelf convenience of engagers. No leukapheresis, no lymphodepletion, outpatient administration, potentially redosable. But: <strong>completely unproven in humans</strong> for RNA-based approaches. No Phase 1 data yet. The LNP delivery challenge &mdash; getting RNA into T-cells rather than liver &mdash; is unsolved at scale.
            </p>

            <div class="bio-box">
                <h3>The Honest Answer</h3>
                <p>One size does not fit all. Different indications may require different modalities. Deep B-cell depletion for severe lupus may need permanent ex vivo CAR-T. Mild-to-moderate autoimmune disease may be better served by transient in vivo approaches. Cancer may continue to favor ex vivo for its proven durability. <strong>The companies that match the right modality to the right indication will win.</strong></p>
            </div>
        </div>

        <!-- Section 9: Bull/Bear -->
        <div class="section">
            <h2>9. Bull/Bear Case for In Vivo CAR-T</h2>
            <div class="thesis-grid">
                <div class="bull-box">
                    <h3>Bull Case</h3>
                    <ul class="thesis-list">
                        <li>$7B+ in Big Pharma M&amp;A validates the thesis &mdash; five acquirers in 12 months</li>
                        <li>Autoimmune market is 10&ndash;100x larger than hematologic oncology (lupus, RA, MS = millions of patients)</li>
                        <li>Off-the-shelf + outpatient + redosable = commercially scalable modality</li>
                        <li>Circular RNA provides longer expression than mRNA, potentially solving the durability gap</li>
                        <li>First-mover advantage: Lilly/Orna&rsquo;s ORN-252 could be first-in-class in vivo CAR-T in humans</li>
                    </ul>
                </div>
                <div class="bear-box">
                    <h3>Bear Case</h3>
                    <ul class="thesis-list">
                        <li>Zero human clinical data for RNA-based in vivo CAR-T &mdash; entirely preclinical</li>
                        <li>LNP delivery to T-cells (not liver) is an unsolved problem at scale</li>
                        <li>Transient expression means repeated dosing &mdash; cost advantage over ex vivo unclear</li>
                        <li>T-cell engagers (bispecifics) may be &ldquo;good enough&rdquo; and are years ahead clinically</li>
                        <li>Insertional mutagenesis risk for lentiviral approaches (same concern as ex vivo)</li>
                        <li>Regulatory path unclear &mdash; FDA has no precedent for in vivo genetic modification for autoimmune disease</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Section 10: Catalysts (shared system) -->
        {catalyst_html}

        <!-- Section 11: Sources -->
        <div class="section">
            <h2>Key Sources</h2>
            <ol class="source-list">
                <li>Mackensen A et al. &ldquo;Anti-CD19 CAR T cells for refractory systemic lupus erythematosus.&rdquo; <em>NEJM</em> 2022; 387:2055-2064. <a href="https://pubmed.ncbi.nlm.nih.gov/36507686/" target="_blank">PubMed</a></li>
                <li>Eli Lilly press release. &ldquo;Lilly to Acquire Orna Therapeutics.&rdquo; Feb 9, 2026.</li>
                <li>AbbVie press release. &ldquo;AbbVie to Acquire Capstan Therapeutics.&rdquo; Jun 2025.</li>
                <li>BMS press release. &ldquo;BMS to Acquire Orbital Therapeutics.&rdquo; Oct 2025.</li>
                <li>Gilead Sciences. Q3 2025 Earnings Report &mdash; Yescarta and Tecartus sales decline.</li>
                <li>FDA Safety Communication. &ldquo;Risk of T-cell Malignancy Following BCMA- and CD19-Directed Autologous CAR T-cell Therapies.&rdquo; Nov 2023.</li>
                <li>MedCity News. &ldquo;Eli Lilly Expands Its In Vivo Ambitions with Orna Therapeutics Acquisition.&rdquo; Feb 2026.</li>
                <li>STAT News. &ldquo;Eli Lilly to buy Orna Therapeutics in $2.4B deal.&rdquo; Feb 2026.</li>
            </ol>
        </div>

        <a href="/targets" class="back-link">&larr; Back to Target Landscapes</a>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
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

    company_detail_styles = """
        .company-header { background: linear-gradient(135deg, var(--navy), #2d4a6f); color: white; padding: 48px 32px; margin: -32px -32px 32px; }
        .company-header h1 { font-size: 2rem; margin-bottom: 8px; }
        .company-header .ticker { background: var(--accent); padding: 8px 16px; border-radius: 8px; font-weight: 700; display: inline-block; margin-bottom: 16px; }
        .company-header p { opacity: 0.9; max-width: 600px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 24px 0; }
        .stat-box { background: rgba(255,255,255,0.15); padding: 20px; border-radius: 12px; text-align: center; }
        .stat-box .value { font-size: 2rem; font-weight: 700; }
        .stat-box .label { font-size: 0.85rem; opacity: 0.8; }
        .detail-section { background: var(--surface); border-radius: 16px; padding: 24px; margin-bottom: 24px; border: 1px solid var(--border); }
        .detail-section h2 { color: var(--navy); margin-bottom: 16px; }
    """
    company_detail_title = f'{company["ticker"]} - {company["name"]} | Satya Bio Analysis'
    return f'''{_render_head(company_detail_title, company_detail_styles)}
    {_render_nav()}
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
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''


# Note: Legacy generate_arwr_thesis function removed - ARWR now uses standard clinical asset rendering via /api/clinical/companies/ARWR/html


def generate_terms_page():
    legal_styles = """
        .legal-content { max-width: 700px; margin: 0 auto; }
        .legal-content h1 { font-size: 2rem; margin-bottom: 8px; color: var(--navy); }
        .legal-content .effective { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 32px; }
        .legal-content h2 { font-size: 1.1rem; font-weight: 600; color: var(--navy); margin: 28px 0 10px; }
        .legal-content p { font-size: 0.95rem; line-height: 1.75; color: var(--text-secondary); margin-bottom: 14px; }
        .legal-content ul { margin: 0 0 14px 20px; color: var(--text-secondary); font-size: 0.95rem; line-height: 1.75; }
    """
    return f'''{_render_head("Terms of Service | Satya Bio", legal_styles)}
    {_render_nav()}
    <main class="main">
        <div class="legal-content">
            <h1>Terms of Service</h1>
            <p class="effective">Effective February 2026</p>

            <h2>1. What This Service Is</h2>
            <p>Satya Bio ("we", "us") provides a biotech intelligence platform that aggregates and presents publicly available information about biotechnology companies, clinical trials, and competitive landscapes. All data is sourced from public filings, corporate presentations, and published clinical data.</p>

            <h2>2. Not Investment Advice</h2>
            <p>Nothing on this site constitutes investment advice, a recommendation, or a solicitation to buy or sell any security. We are not a registered investment adviser, broker-dealer, or financial planner. You should consult a qualified financial professional before making investment decisions.</p>

            <h2>3. Data Accuracy</h2>
            <p>We make reasonable efforts to ensure our data is accurate and up to date, but we do not guarantee completeness or accuracy. Biotech data changes rapidly — clinical results are updated, regulatory statuses shift, and company strategies evolve. Always verify critical data points against primary sources (SEC filings, ClinicalTrials.gov, company IR pages).</p>

            <h2>4. Your Use of the Service</h2>
            <p>You may use Satya Bio for your own research and analysis. You agree not to:</p>
            <ul>
                <li>Scrape or bulk-download data for redistribution</li>
                <li>Misrepresent Satya Bio content as your own original research</li>
                <li>Use automated tools to overwhelm our servers</li>
            </ul>

            <h2>5. Intellectual Property</h2>
            <p>The presentation, analysis, and original commentary on this site are our work. The underlying clinical data, company filings, and public information belong to their respective owners. Our value-add is in aggregation, analysis, and presentation.</p>

            <h2>6. Limitation of Liability</h2>
            <p>Satya Bio is provided "as is." We are not liable for any losses arising from your use of or reliance on information presented here. This includes but is not limited to investment losses, trading decisions, or actions taken based on our data.</p>

            <h2>7. Changes</h2>
            <p>We may update these terms as the service evolves. Continued use after changes constitutes acceptance.</p>

            <h2>8. Contact</h2>
            <p>Questions about these terms? Email <a href="mailto:contact@satyabio.com" style="color: var(--accent);">contact@satyabio.com</a>.</p>
        </div>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''


def generate_privacy_page():
    legal_styles = """
        .legal-content { max-width: 700px; margin: 0 auto; }
        .legal-content h1 { font-size: 2rem; margin-bottom: 8px; color: var(--navy); }
        .legal-content .effective { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 32px; }
        .legal-content h2 { font-size: 1.1rem; font-weight: 600; color: var(--navy); margin: 28px 0 10px; }
        .legal-content p { font-size: 0.95rem; line-height: 1.75; color: var(--text-secondary); margin-bottom: 14px; }
        .legal-content ul { margin: 0 0 14px 20px; color: var(--text-secondary); font-size: 0.95rem; line-height: 1.75; }
    """
    return f'''{_render_head("Privacy Policy | Satya Bio", legal_styles)}
    {_render_nav()}
    <main class="main">
        <div class="legal-content">
            <h1>Privacy Policy</h1>
            <p class="effective">Effective February 2026</p>

            <h2>1. What We Collect</h2>
            <p>We keep data collection minimal:</p>
            <ul>
                <li><strong>Email address</strong> — if you subscribe for access or request coverage</li>
                <li><strong>Basic analytics</strong> — page views, referral source, and general usage patterns (no tracking pixels, no fingerprinting)</li>
                <li><strong>Server logs</strong> — IP address, browser type, and request timestamps, retained for security purposes</li>
            </ul>

            <h2>2. What We Don't Collect</h2>
            <p>We do not collect personal financial information, trading data, portfolio holdings, or any information about your investment activities. We do not use third-party advertising trackers.</p>

            <h2>3. How We Use Your Data</h2>
            <ul>
                <li>To provide and improve the service</li>
                <li>To send updates you've opted into (coverage alerts, new features)</li>
                <li>To respond to your inquiries</li>
            </ul>

            <h2>4. Data Sharing</h2>
            <p>We do not sell your personal information. We may share data only when required by law or to protect our rights.</p>

            <h2>5. Cookies</h2>
            <p>We use minimal, functional cookies to keep the site working (e.g., session management). No third-party tracking cookies.</p>

            <h2>6. Data Retention</h2>
            <p>We retain your email for as long as you maintain a subscription. Server logs are retained for 90 days. You can request deletion of your data at any time.</p>

            <h2>7. Your Rights</h2>
            <p>You can request access to, correction of, or deletion of your personal data by emailing us. We will respond within 30 days.</p>

            <h2>8. Contact</h2>
            <p>Privacy questions? Email <a href="mailto:contact@satyabio.com" style="color: var(--accent);">contact@satyabio.com</a>.</p>
        </div>
    </main>
    <footer class="footer">
        <p>&copy; 2026 Satya Bio. Biotech intelligence for the buy side.</p>
        <p style="margin-top: 8px; font-size: 0.75rem;"><a href="/terms" style="color: rgba(255,255,255,0.5); text-decoration: none;">Terms</a> &middot; <a href="/privacy" style="color: rgba(255,255,255,0.5); text-decoration: none;">Privacy</a></p>
    </footer>
</body>
</html>'''
