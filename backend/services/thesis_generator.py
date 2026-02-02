"""
Investment Thesis Generator

Generates comprehensive investment thesis HTML pages from pipeline data.
Pulls data from verified sources (FDA, ClinicalTrials.gov, SEC).
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import html

DATA_DIR = Path(__file__).parent.parent / "data" / "pipeline_data"


class ThesisGenerator:
    """Generate investment thesis HTML from pipeline data."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load pipeline data for ticker."""
        file_path = DATA_DIR / f"{self.ticker.lower()}.json"
        if not file_path.exists():
            return {}
        with open(file_path, "r") as f:
            return json.load(f)

    def generate_html(self) -> str:
        """Generate complete investment thesis HTML."""
        if not self.data:
            return self._error_html(f"No data found for {self.ticker}")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.ticker} Investment Thesis | Helix</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._header_section()}
        {self._executive_summary()}
        {self._platform_section()}
        {self._pipeline_by_area()}
        {self._partnership_section()}
        {self._catalyst_calendar()}
        {self._valuation_section()}
        {self._risks_section()}
        {self._sources_section()}
    </div>
</body>
</html>"""

    def _get_css(self) -> str:
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc; color: #1e293b; line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }

        /* Header */
        .header { background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
            color: white; padding: 3rem; border-radius: 1rem; margin-bottom: 2rem; }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header .subtitle { opacity: 0.8; font-size: 1.1rem; }
        .header .meta { margin-top: 1rem; font-size: 0.9rem; opacity: 0.7; }

        /* Sections */
        .section { background: white; border-radius: 0.75rem; padding: 2rem;
            margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section-title { font-size: 1.5rem; font-weight: 700; color: #0f172a;
            border-bottom: 3px solid #0ea5e9; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }
        .section-divider { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em;
            color: #64748b; margin: 2rem 0 1rem; }

        /* Grid layouts */
        .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
        @media (max-width: 768px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }

        /* Cards */
        .card { background: #f8fafc; border-radius: 0.5rem; padding: 1.25rem;
            border: 1px solid #e2e8f0; }
        .card-title { font-weight: 600; color: #0f172a; margin-bottom: 0.5rem; }
        .card-value { font-size: 1.75rem; font-weight: 700; color: #0ea5e9; }
        .card-label { font-size: 0.85rem; color: #64748b; }

        /* Pipeline cards */
        .pipeline-card { border-left: 4px solid #0ea5e9; }
        .pipeline-card.approved { border-left-color: #22c55e; }
        .pipeline-card.phase3 { border-left-color: #f59e0b; }
        .pipeline-card.phase2 { border-left-color: #8b5cf6; }
        .pipeline-card.phase1 { border-left-color: #64748b; }

        /* Status badges */
        .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px;
            font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
        .badge-approved { background: #dcfce7; color: #166534; }
        .badge-phase3 { background: #fef3c7; color: #92400e; }
        .badge-phase2 { background: #ede9fe; color: #5b21b6; }
        .badge-phase1 { background: #f1f5f9; color: #475569; }
        .badge-recruiting { background: #dbeafe; color: #1e40af; }
        .badge-completed { background: #d1fae5; color: #065f46; }

        /* Tables */
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-weight: 600; color: #475569; font-size: 0.85rem;
            text-transform: uppercase; letter-spacing: 0.05em; }
        tr:hover { background: #f8fafc; }

        /* Bull/Bear boxes */
        .thesis-box { padding: 1.25rem; border-radius: 0.5rem; margin: 1rem 0; }
        .thesis-bull { background: #ecfdf5; border-left: 4px solid #22c55e; }
        .thesis-bear { background: #fef2f2; border-left: 4px solid #ef4444; }
        .thesis-key { background: #eff6ff; border-left: 4px solid #3b82f6; }
        .thesis-label { font-weight: 700; margin-bottom: 0.5rem; }
        .thesis-bull .thesis-label { color: #166534; }
        .thesis-bear .thesis-label { color: #991b1b; }
        .thesis-key .thesis-label { color: #1e40af; }

        /* Links */
        a { color: #0ea5e9; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .source-link { font-size: 0.75rem; color: #64748b; }

        /* Trial details */
        .trial-detail { display: flex; gap: 2rem; flex-wrap: wrap; }
        .trial-metric { text-align: center; padding: 1rem; background: #f8fafc; border-radius: 0.5rem; }
        .trial-metric-value { font-size: 1.5rem; font-weight: 700; color: #0ea5e9; }
        .trial-metric-label { font-size: 0.8rem; color: #64748b; }

        /* Catalyst timeline */
        .catalyst-item { display: flex; gap: 1rem; padding: 1rem 0; border-bottom: 1px solid #e2e8f0; }
        .catalyst-date { min-width: 100px; font-weight: 600; color: #0f172a; }
        .catalyst-event { flex: 1; }
        .catalyst-asset { font-size: 0.85rem; color: #64748b; }

        /* Verified badge */
        .verified { display: inline-flex; align-items: center; gap: 0.25rem;
            font-size: 0.75rem; color: #22c55e; }
        .verified::before { content: '✓'; }

        /* Print styles */
        @media print {
            .container { max-width: 100%; padding: 0; }
            .section { break-inside: avoid; box-shadow: none; border: 1px solid #e2e8f0; }
        }
        """

    def _header_section(self) -> str:
        name = html.escape(self.data.get("name", self.ticker))
        desc = html.escape(self.data.get("description", ""))
        lead_asset = html.escape(self.data.get("lead_asset", ""))
        lead_stage = html.escape(self.data.get("lead_asset_stage", ""))

        verification = self.data.get("_data_verification", {})
        last_verified = verification.get("last_verified", "")

        return f"""
        <div class="header">
            <h1>{self.ticker} Investment Thesis</h1>
            <div class="subtitle">{name}</div>
            <div class="meta">
                Lead Asset: {lead_asset} ({lead_stage}) |
                Last Verified: {last_verified[:10] if last_verified else 'N/A'}
            </div>
        </div>
        """

    def _executive_summary(self) -> str:
        name = html.escape(self.data.get("name", self.ticker))
        desc = html.escape(self.data.get("description", ""))

        # Count programs by stage
        programs = self.data.get("programs", [])
        approved = sum(1 for p in programs if "Approved" in p.get("stage", ""))
        phase3 = sum(1 for p in programs if "Phase 3" in p.get("stage", "") or "Phase 2/3" in p.get("stage", ""))
        phase2 = sum(1 for p in programs if "Phase 2" in p.get("stage", "") and "Phase 2/3" not in p.get("stage", ""))
        phase1 = sum(1 for p in programs if "Phase 1" in p.get("stage", ""))

        # Partnerships
        partnerships = self.data.get("partnerships", [])
        total_milestones = sum(p.get("financial_terms", {}).get("milestones_potential", 0) for p in partnerships)
        total_received = sum(p.get("financial_terms", {}).get("received_to_date", 0) for p in partnerships)

        # Key debates from first approved/lead program
        key_debates = []
        for p in programs:
            if p.get("satya_view"):
                sv = p["satya_view"]
                if sv.get("key_question"):
                    key_debates.append(html.escape(sv["key_question"]))
                break

        return f"""
        <div class="section">
            <h2 class="section-title">Executive Summary</h2>

            <p style="font-size: 1.1rem; margin-bottom: 1.5rem;">{desc}</p>

            <div class="grid-3" style="margin-bottom: 2rem;">
                <div class="card">
                    <div class="card-label">Approved Products</div>
                    <div class="card-value">{approved}</div>
                </div>
                <div class="card">
                    <div class="card-label">Phase 3 Programs</div>
                    <div class="card-value">{phase3}</div>
                </div>
                <div class="card">
                    <div class="card-label">Partnership Milestones</div>
                    <div class="card-value">${total_milestones/1e9:.1f}B</div>
                    <div class="card-label" style="margin-top: 0.25rem;">Received: ${total_received/1e6:.0f}M</div>
                </div>
            </div>

            <div class="section-divider">Pipeline Summary</div>
            <div class="grid-2">
                {self._program_summary_cards(programs[:4])}
            </div>

            {"<div class='section-divider'>Key Investment Debates</div><ul style='margin-left: 1.5rem;'>" + "".join(f"<li style='margin-bottom: 0.5rem;'>{d}</li>" for d in key_debates) + "</ul>" if key_debates else ""}
        </div>
        """

    def _program_summary_cards(self, programs: list) -> str:
        cards = []
        for p in programs:
            stage = p.get("stage", "")
            stage_class = "approved" if "Approved" in stage else "phase3" if "Phase 3" in stage else "phase2" if "Phase 2" in stage else "phase1"
            badge_class = "badge-approved" if "Approved" in stage else "badge-phase3" if "Phase 3" in stage else "badge-phase2" if "Phase 2" in stage else "badge-phase1"

            name = html.escape(p.get("name", ""))
            indication = html.escape(p.get("indication", "")[:50])
            partner = html.escape(p.get("partner") or "Wholly-owned")
            key_data = html.escape(p.get("key_data", ""))

            fda = p.get("fda_verification", {})
            verified = '<span class="verified">FDA Verified</span>' if fda.get("is_approved") else ""

            cards.append(f"""
            <div class="card pipeline-card {stage_class}">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div class="card-title">{name}</div>
                    <span class="badge {badge_class}">{stage.split('/')[0].strip()}</span>
                </div>
                <div style="color: #64748b; font-size: 0.9rem; margin: 0.5rem 0;">{indication}</div>
                <div style="font-weight: 600; color: #0ea5e9; margin: 0.5rem 0;">{key_data}</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #64748b;">
                    <span>Partner: {partner}</span>
                    {verified}
                </div>
            </div>
            """)
        return "".join(cards)

    def _platform_section(self) -> str:
        return f"""
        <div class="section">
            <h2 class="section-title">Platform Technology: TRiM</h2>

            <div class="grid-2">
                <div>
                    <h3 style="margin-bottom: 1rem;">Technology Overview</h3>
                    <p>Arrowhead's Targeted RNAi Molecule (TRiM) platform enables tissue-specific
                    delivery of siRNA therapeutics. The platform uses proprietary ligand-targeting
                    chemistry to direct RNAi payloads to specific cell types.</p>

                    <h4 style="margin: 1.5rem 0 0.75rem;">Tissue Targeting Capabilities</h4>
                    <ul style="margin-left: 1.5rem;">
                        <li><strong>Liver (GalNAc)</strong> - Most advanced, multiple programs</li>
                        <li><strong>Lung (inhaled)</strong> - ARO-RAGE, ARO-MUC5AC</li>
                        <li><strong>Muscle</strong> - ARO-DUX4 (FSHD), ARO-DM1</li>
                        <li><strong>CNS</strong> - ARO-MAPT (Alzheimer's), ARO-ATXN2</li>
                    </ul>
                </div>
                <div>
                    <h3 style="margin-bottom: 1rem;">Competitive Advantages</h3>
                    <table>
                        <tr><th>Feature</th><th>ARWR (TRiM)</th><th>ALNY (GalNAc)</th><th>IONS (ASO)</th></tr>
                        <tr><td>Dosing Frequency</td><td>Quarterly</td><td>Quarterly-Annual</td><td>Weekly-Monthly</td></tr>
                        <tr><td>Tissue Targets</td><td>Liver, Lung, Muscle, CNS</td><td>Primarily Liver</td><td>Broad</td></tr>
                        <tr><td>Approved Products</td><td>1 (REDEMPLO)</td><td>5</td><td>5</td></tr>
                        <tr><td>Partnership Model</td><td>Ph1 then partner</td><td>Retained rights</td><td>Mixed</td></tr>
                    </table>

                    <h4 style="margin: 1.5rem 0 0.75rem;">Platform Validation</h4>
                    <p>REDEMPLO (plozasiran) approval in Nov 2025 validated TRiM platform.
                    Multiple Phase 3 programs across therapeutic areas.</p>
                </div>
            </div>
        </div>
        """

    def _pipeline_by_area(self) -> str:
        programs = self.data.get("programs", [])
        sections = []

        for program in programs:
            sections.append(self._program_detail_section(program))

        return "".join(sections)

    def _program_detail_section(self, program: dict) -> str:
        name = html.escape(program.get("name", ""))
        target = html.escape(program.get("target", ""))
        indication = html.escape(program.get("indication", ""))
        stage = html.escape(program.get("stage", ""))
        mechanism = program.get("mechanism", {})

        # Clinical trials
        trials_html = self._trials_table(program.get("clinical_data", []))

        # Competitors
        competitors_html = self._competitors_table(program.get("competitors", []))

        # Satya view
        satya = program.get("satya_view", {})
        satya_html = ""
        if satya:
            bull = html.escape(satya.get("bull_thesis", ""))
            bear = html.escape(satya.get("bear_thesis", ""))
            key_q = html.escape(satya.get("key_question", ""))
            satya_html = f"""
            <div class="section-divider">Investment View</div>
            <div class="thesis-box thesis-bull">
                <div class="thesis-label">Bull Thesis</div>
                <p>{bull}</p>
            </div>
            <div class="thesis-box thesis-bear">
                <div class="thesis-label">Bear Thesis</div>
                <p>{bear}</p>
            </div>
            <div class="thesis-box thesis-key">
                <div class="thesis-label">Key Question</div>
                <p>{key_q}</p>
            </div>
            """

        # FDA verification
        fda = program.get("fda_verification", {})
        fda_html = ""
        if fda.get("is_approved"):
            fda_html = f"""
            <div class="card" style="background: #ecfdf5; border: 1px solid #22c55e; margin-top: 1rem;">
                <div class="verified" style="font-size: 1rem; color: #166534; margin-bottom: 0.5rem;">
                    FDA Approved
                </div>
                <div><strong>Brand:</strong> {html.escape(fda.get("brand_name", ""))}</div>
                <div><strong>Approval Date:</strong> {fda.get("approval_date", "")}</div>
                <div><strong>Indication:</strong> {html.escape(fda.get("indication_summary", "")[:200])}</div>
                <div class="source-link">Source: <a href="{fda.get('source_url', '#')}" target="_blank">OpenFDA</a></div>
            </div>
            """

        return f"""
        <div class="section">
            <h2 class="section-title">{name}</h2>

            <div class="grid-2" style="margin-bottom: 1.5rem;">
                <div>
                    <table>
                        <tr><td style="font-weight: 600; width: 120px;">Target</td><td>{target}</td></tr>
                        <tr><td style="font-weight: 600;">Stage</td><td>{stage}</td></tr>
                        <tr><td style="font-weight: 600;">Indication</td><td>{indication}</td></tr>
                        <tr><td style="font-weight: 600;">Modality</td><td>{html.escape(mechanism.get("modality", ""))}</td></tr>
                        <tr><td style="font-weight: 600;">Dosing</td><td>{html.escape(mechanism.get("dosing", ""))}</td></tr>
                    </table>
                </div>
                <div>
                    <h4 style="margin-bottom: 0.75rem;">Mechanism</h4>
                    <p style="font-size: 0.9rem; color: #475569;">{html.escape(mechanism.get("description", ""))}</p>
                </div>
            </div>

            {fda_html}

            <div class="section-divider">Clinical Development</div>
            {trials_html}

            <div class="section-divider">Competitive Landscape</div>
            {competitors_html}

            {satya_html}
        </div>
        """

    def _trials_table(self, trials: list) -> str:
        if not trials:
            return "<p>No clinical trials listed.</p>"

        rows = []
        for t in trials:
            nct = t.get("nct_id", "")
            name = html.escape(t.get("trial_name", ""))
            phase = html.escape(t.get("phase", ""))
            status = t.get("status", "")

            # Status badge
            status_class = "badge-completed" if status == "COMPLETED" else "badge-recruiting" if "RECRUIT" in status else "badge-phase2"
            status_display = status.replace("_", " ").title() if status else "Unknown"

            # Results
            results = t.get("results", {})
            primary = results.get("primary", {})
            result_text = html.escape(primary.get("result", "Pending"))

            source_url = t.get("source_url", f"https://clinicaltrials.gov/study/{nct}")

            rows.append(f"""
            <tr>
                <td><a href="{source_url}" target="_blank">{nct}</a></td>
                <td>{name}</td>
                <td>{phase}</td>
                <td><span class="badge {status_class}">{status_display}</span></td>
                <td style="font-weight: 600; color: #0ea5e9;">{result_text}</td>
            </tr>
            """)

        return f"""
        <table>
            <thead>
                <tr><th>NCT ID</th><th>Trial</th><th>Phase</th><th>Status</th><th>Result</th></tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """

    def _competitors_table(self, competitors: list) -> str:
        if not competitors:
            return "<p>No competitors listed.</p>"

        rows = []
        for c in competitors:
            rows.append(f"""
            <tr>
                <td><strong>{html.escape(c.get("drug_name", ""))}</strong></td>
                <td>{html.escape(c.get("company", ""))}</td>
                <td>{html.escape(c.get("mechanism", ""))}</td>
                <td>{html.escape(c.get("stage", ""))}</td>
                <td>{html.escape(c.get("efficacy", ""))}</td>
                <td style="font-size: 0.85rem;">{html.escape(c.get("differentiation", ""))}</td>
            </tr>
            """)

        return f"""
        <table>
            <thead>
                <tr><th>Drug</th><th>Company</th><th>Mechanism</th><th>Stage</th><th>Efficacy</th><th>Differentiation</th></tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """

    def _partnership_section(self) -> str:
        partnerships = self.data.get("partnerships", [])
        if not partnerships:
            return ""

        rows = []
        for p in partnerships:
            partner = html.escape(p.get("partner", ""))
            programs = ", ".join(p.get("programs", []))
            terms = p.get("financial_terms", {})
            upfront = terms.get("upfront", 0)
            milestones = terms.get("milestones_potential", 0)
            received = terms.get("received_to_date", 0)
            royalties = html.escape(str(terms.get("royalties", "")))

            rows.append(f"""
            <tr>
                <td><strong>{partner}</strong></td>
                <td>{programs}</td>
                <td>${upfront/1e6:.0f}M</td>
                <td>${milestones/1e6:.0f}M</td>
                <td>${received/1e6:.0f}M</td>
                <td>{royalties}</td>
            </tr>
            """)

        total_potential = sum(p.get("financial_terms", {}).get("milestones_potential", 0) for p in partnerships)
        total_received = sum(p.get("financial_terms", {}).get("received_to_date", 0) for p in partnerships)

        return f"""
        <div class="section">
            <h2 class="section-title">Partnership Analysis</h2>

            <div class="grid-3" style="margin-bottom: 1.5rem;">
                <div class="card">
                    <div class="card-label">Total Partnerships</div>
                    <div class="card-value">{len(partnerships)}</div>
                </div>
                <div class="card">
                    <div class="card-label">Total Milestone Potential</div>
                    <div class="card-value">${total_potential/1e9:.1f}B</div>
                </div>
                <div class="card">
                    <div class="card-label">Received to Date</div>
                    <div class="card-value">${total_received/1e6:.0f}M</div>
                </div>
            </div>

            <table>
                <thead>
                    <tr><th>Partner</th><th>Programs</th><th>Upfront</th><th>Milestones</th><th>Received</th><th>Royalties</th></tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    def _catalyst_calendar(self) -> str:
        catalysts = self.data.get("company_catalysts", [])

        # Also gather catalysts from programs
        for program in self.data.get("programs", []):
            for cat in program.get("catalysts", []):
                cat["_program"] = program.get("name", "")
                if cat not in catalysts:
                    catalysts.append(cat)

        if not catalysts:
            return ""

        # Sort by expected date, putting completed ones last
        def sort_key(c):
            if c.get("status") == "completed":
                return (1, c.get("actual_date", ""))
            return (0, c.get("expected_date", ""))

        catalysts.sort(key=sort_key)

        items = []
        for cat in catalysts[:12]:  # Limit to 12
            date = cat.get("actual_date") or cat.get("expected_date", "TBD")
            event = html.escape(cat.get("event", ""))
            program = html.escape(cat.get("_program", ""))
            status = cat.get("status", "")
            outcome = html.escape(cat.get("outcome", ""))

            status_badge = ""
            if status == "completed":
                status_badge = '<span class="badge badge-completed">Completed</span>'
            elif status == "upcoming":
                status_badge = '<span class="badge badge-recruiting">Upcoming</span>'

            items.append(f"""
            <div class="catalyst-item">
                <div class="catalyst-date">{date}</div>
                <div class="catalyst-event">
                    <div><strong>{event}</strong> {status_badge}</div>
                    {f'<div class="catalyst-asset">{program}</div>' if program else ""}
                    {f'<div style="color: #22c55e; font-size: 0.9rem;">{outcome}</div>' if outcome else ""}
                </div>
            </div>
            """)

        return f"""
        <div class="section">
            <h2 class="section-title">Catalyst Calendar</h2>
            {"".join(items)}
        </div>
        """

    def _valuation_section(self) -> str:
        return f"""
        <div class="section">
            <h2 class="section-title">Valuation Framework</h2>

            <div class="grid-2">
                <div>
                    <h3 style="margin-bottom: 1rem;">Comparable Companies</h3>
                    <table>
                        <tr><th>Company</th><th>Market Cap</th><th>Lead Asset Stage</th></tr>
                        <tr><td>Alnylam (ALNY)</td><td>~$28B</td><td>5 Approved</td></tr>
                        <tr><td>Ionis (IONS)</td><td>~$8B</td><td>5 Approved</td></tr>
                        <tr><td>Arrowhead (ARWR)</td><td>~$4B</td><td>1 Approved</td></tr>
                    </table>
                </div>
                <div>
                    <h3 style="margin-bottom: 1rem;">Key Considerations</h3>
                    <ul style="margin-left: 1.5rem;">
                        <li>Platform value: Multiple Phase 3 programs</li>
                        <li>Partnership milestones: $3B+ potential</li>
                        <li>First approved product validates platform</li>
                        <li>Obesity programs if successful could be transformative</li>
                    </ul>
                </div>
            </div>

            <div class="thesis-box thesis-key" style="margin-top: 1.5rem;">
                <div class="thesis-label">Valuation Note</div>
                <p>Current valuation reflects approved FCS product and Phase 3 pipeline.
                Upside scenarios depend on sHTG approval (10x larger market) and obesity
                program success (multi-hundred billion market if competitive with GLP-1s).</p>
            </div>
        </div>
        """

    def _risks_section(self) -> str:
        return f"""
        <div class="section">
            <h2 class="section-title">Key Risks</h2>

            <div class="grid-2">
                <div class="card" style="border-left: 4px solid #ef4444;">
                    <div class="card-title">Commercial Execution</div>
                    <p style="font-size: 0.9rem; color: #64748b;">First commercial product launch.
                    Amgen partnership helps but ARWR has limited commercial track record.</p>
                </div>
                <div class="card" style="border-left: 4px solid #ef4444;">
                    <div class="card-title">Competition</div>
                    <p style="font-size: 0.9rem; color: #64748b;">Ionis Tryngolza (olezarsen) already
                    approved for FCS. Racing for sHTG market. GLP-1s dominating obesity.</p>
                </div>
                <div class="card" style="border-left: 4px solid #f59e0b;">
                    <div class="card-title">Partnership Dependency</div>
                    <p style="font-size: 0.9rem; color: #64748b;">Amgen and Takeda control late-stage
                    development and commercialization for key assets.</p>
                </div>
                <div class="card" style="border-left: 4px solid #f59e0b;">
                    <div class="card-title">Pipeline Concentration</div>
                    <p style="font-size: 0.9rem; color: #64748b;">Significant value tied to plozasiran
                    success. sHTG outcome critical.</p>
                </div>
            </div>
        </div>
        """

    def _sources_section(self) -> str:
        verification = self.data.get("_data_verification", {})
        sources = verification.get("sources", {})
        nct_ids = verification.get("nct_ids_verified", [])

        source_items = []
        for source_type, url in sources.items():
            source_items.append(f"""
            <div style="margin-bottom: 0.5rem;">
                <strong>{source_type.replace("_", " ").title()}</strong>:
                <a href="{html.escape(url)}" target="_blank">{html.escape(url)}</a>
            </div>
            """)

        nct_links = ", ".join(
            f'<a href="https://clinicaltrials.gov/study/{nct}" target="_blank">{nct}</a>'
            for nct in nct_ids[:10]
        )

        return f"""
        <div class="section">
            <h2 class="section-title">Data Sources</h2>

            <p style="margin-bottom: 1rem;">All data verified from authoritative sources.
            Last verification: {verification.get("last_verified", "N/A")}</p>

            <div class="section-divider">API Sources</div>
            {"".join(source_items)}

            <div class="section-divider">Verified Clinical Trials</div>
            <p>{nct_links}{"..." if len(nct_ids) > 10 else ""}</p>

            <div class="section-divider">Additional Sources</div>
            <ul style="margin-left: 1.5rem; color: #64748b; font-size: 0.9rem;">
                <li><a href="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001580063" target="_blank">SEC EDGAR Filings</a></li>
                <li><a href="https://ir.arrowheadpharma.com/news-releases" target="_blank">Company IR Page</a></li>
                <li><a href="https://www.accessdata.fda.gov/scripts/cder/daf/" target="_blank">FDA Drugs@FDA</a></li>
            </ul>
        </div>
        """

    def _error_html(self, message: str) -> str:
        return f"""<!DOCTYPE html>
<html><head><title>Error</title></head>
<body style="font-family: sans-serif; padding: 2rem;">
<h1>Error</h1><p>{html.escape(message)}</p>
</body></html>"""


def generate_thesis(ticker: str) -> str:
    """Generate investment thesis HTML for a ticker."""
    generator = ThesisGenerator(ticker)
    return generator.generate_html()


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "ARWR"
    html_content = generate_thesis(ticker)
    output_path = Path(__file__).parent.parent / "data" / "thesis" / f"{ticker.lower()}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html_content)
    print(f"Generated: {output_path}")
