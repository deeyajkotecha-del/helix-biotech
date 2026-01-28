"use strict";
/**
 * Pharma Intelligence Routes
 *
 * Express Router providing pharma profile endpoints,
 * pipeline views, catalyst tracking, BD fit analysis,
 * and JPM presentation URLs.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.pharmaRouter = void 0;
const express_1 = require("express");
const pharma_registry_1 = require("./pharma-registry");
const pharma_data_1 = require("./pharma-data");
exports.pharmaRouter = (0, express_1.Router)();
// ============================================
// GET /api/pharma — List all companies
// ============================================
exports.pharmaRouter.get('/api/pharma', (_req, res) => {
    const companies = (0, pharma_data_1.getAllPharmaSummary)();
    res.json({
        count: companies.length,
        companies,
        verifiedCompanies: (0, pharma_registry_1.getVerifiedCompanies)().map((c) => c.ticker),
    });
});
// ============================================
// GET /api/pharma/catalysts — All upcoming catalysts
// ============================================
exports.pharmaRouter.get('/api/pharma/catalysts', (_req, res) => {
    const catalysts = (0, pharma_data_1.getUpcomingCatalysts)();
    res.json({
        count: catalysts.length,
        catalysts,
    });
});
// ============================================
// GET /api/pharma/jpm2026 — JPM presentation URLs
// ============================================
exports.pharmaRouter.get('/api/pharma/jpm2026', (_req, res) => {
    const urls = (0, pharma_registry_1.getJPM2026Urls)();
    res.json({
        conference: 'JPM Healthcare Conference 2026',
        companies: urls,
    });
});
// ============================================
// GET /api/pharma/compare?a=MRK&b=PFE — Compare pipelines
// ============================================
exports.pharmaRouter.get('/api/pharma/compare', (req, res) => {
    const tickerA = (req.query.a || '').toUpperCase();
    const tickerB = (req.query.b || '').toUpperCase();
    if (!tickerA || !tickerB) {
        res.status(400).json({ error: 'Provide ?a=TICKER&b=TICKER' });
        return;
    }
    const result = (0, pharma_data_1.comparePipelines)(tickerA, tickerB);
    if (!result) {
        res.status(404).json({ error: `One or both tickers not found: ${tickerA}, ${tickerB}` });
        return;
    }
    res.json(result);
});
// ============================================
// GET /api/pharma/bd-fit?target=MRK&area=oncology&modality=ADC
// ============================================
exports.pharmaRouter.get('/api/pharma/bd-fit', (req, res) => {
    const target = (req.query.target || '').toUpperCase();
    const area = req.query.area || '';
    const modality = req.query.modality || '';
    if (!target || !area) {
        res.status(400).json({ error: 'Provide ?target=TICKER&area=therapeutic_area&modality=modality_type' });
        return;
    }
    const result = (0, pharma_data_1.analyzeBDFit)(target, area, modality);
    if (!result) {
        res.status(404).json({ error: `Company not found: ${target}` });
        return;
    }
    res.json(result);
});
// ============================================
// GET /api/pharma/:ticker — Full JSON profile
// ============================================
exports.pharmaRouter.get('/api/pharma/:ticker', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const profile = (0, pharma_data_1.getPharmaProfile)(ticker);
    if (!profile) {
        res.status(404).json({ error: `Company not found: ${ticker}. Available: ${(0, pharma_registry_1.getAllTickers)().join(', ')}` });
        return;
    }
    res.json(profile);
});
// ============================================
// GET /api/pharma/:ticker/pipeline — Pipeline only
// ============================================
exports.pharmaRouter.get('/api/pharma/:ticker/pipeline', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const profile = (0, pharma_data_1.getPharmaProfile)(ticker);
    if (!profile) {
        res.status(404).json({ error: `Company not found: ${ticker}` });
        return;
    }
    res.json({
        company: profile.company.name,
        ticker: profile.company.ticker,
        stats: profile.pipelineStats,
        assets: profile.pipeline,
    });
});
// ============================================
// GET /api/pharma/:ticker/catalysts — Catalysts only
// ============================================
exports.pharmaRouter.get('/api/pharma/:ticker/catalysts', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const profile = (0, pharma_data_1.getPharmaProfile)(ticker);
    if (!profile) {
        res.status(404).json({ error: `Company not found: ${ticker}` });
        return;
    }
    res.json({
        company: profile.company.name,
        count: profile.catalysts.length,
        catalysts: profile.catalysts,
    });
});
// ============================================
// GET /api/pharma/:ticker/strategy — Strategy & BD
// ============================================
exports.pharmaRouter.get('/api/pharma/:ticker/strategy', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const profile = (0, pharma_data_1.getPharmaProfile)(ticker);
    if (!profile) {
        res.status(404).json({ error: `Company not found: ${ticker}` });
        return;
    }
    res.json({
        company: profile.company.name,
        strategy: profile.strategy,
        revenueOpportunities: profile.revenueOpportunities,
    });
});
// ============================================
// GET /api/pharma/:ticker/deals — Recent deals
// ============================================
exports.pharmaRouter.get('/api/pharma/:ticker/deals', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const profile = (0, pharma_data_1.getPharmaProfile)(ticker);
    if (!profile) {
        res.status(404).json({ error: `Company not found: ${ticker}` });
        return;
    }
    res.json({
        company: profile.company.name,
        count: profile.recentDeals.length,
        deals: profile.recentDeals,
    });
});
// ============================================
// GET /api/pharma/:ticker/html — Full HTML view
// ============================================
exports.pharmaRouter.get('/api/pharma/:ticker/html', (req, res) => {
    const ticker = req.params.ticker.toUpperCase();
    const profile = (0, pharma_data_1.getPharmaProfile)(ticker);
    if (!profile) {
        res.status(404).send(`<h1>Not Found</h1><p>Company not found: ${ticker}</p>`);
        return;
    }
    const html = generateProfileHtml(profile);
    res.setHeader('Content-Type', 'text/html');
    res.send(html);
});
// ============================================
// HTML Generator
// ============================================
function generateProfileHtml(profile) {
    if (!profile)
        return '<h1>Not Found</h1>';
    const { company, pipeline, catalysts, recentDeals, strategy, revenueOpportunities, pipelineStats, keyFinancials } = profile;
    const pipelineRows = pipeline
        .map((a) => `
    <tr>
      <td><strong>${a.drugName}</strong>${a.genericName ? `<br><small>${a.genericName}</small>` : ''}</td>
      <td>${a.phase >= 4 ? 'Approved' : `Phase ${a.phase}`}</td>
      <td>${a.indication}</td>
      <td>${a.mechanism}</td>
      <td>${a.modality}</td>
      <td>${a.peakRevenuePotential || '-'}</td>
      <td>${a.expectedReadout || a.expectedApproval || '-'}</td>
      <td>${a.partner || '-'}</td>
    </tr>`)
        .join('');
    const catalystRows = catalysts
        .map((c) => `
    <tr>
      <td>${c.date}</td>
      <td><span class="badge badge-${c.significance}">${c.significance}</span></td>
      <td>${c.drugName}</td>
      <td>${c.indication}</td>
      <td>${c.description}</td>
    </tr>`)
        .join('');
    const dealRows = recentDeals
        .map((d) => `
    <tr>
      <td>${d.date}</td>
      <td>${d.type}</td>
      <td>${d.targetCompany || '-'}</td>
      <td>${d.asset || '-'}</td>
      <td>${d.rationale || '-'}</td>
    </tr>`)
        .join('');
    const revenueRows = revenueOpportunities
        .map((r) => `
    <tr>
      <td>${r.therapeuticArea}</td>
      <td>${r.targetYear}</td>
      <td>${r.revenueEstimate}</td>
      <td>${r.keyAssets.join(', ')}</td>
    </tr>`)
        .join('');
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${company.name} (${company.ticker}) - Pharma Intelligence</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { color: #818cf8; margin-bottom: 8px; }
    h2 { color: #a5b4fc; margin: 30px 0 15px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
    h3 { color: #93c5fd; margin: 20px 0 10px; }
    .subtitle { color: #94a3b8; margin-bottom: 20px; }
    .meta { display: flex; gap: 20px; margin-bottom: 25px; flex-wrap: wrap; }
    .meta-card { background: #1e293b; border-radius: 8px; padding: 15px 20px; flex: 1; min-width: 200px; }
    .meta-card .label { color: #94a3b8; font-size: 0.85rem; }
    .meta-card .value { color: #f1f5f9; font-size: 1.3rem; font-weight: bold; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0 25px; }
    th { background: #1e293b; color: #a5b4fc; padding: 10px 12px; text-align: left; font-size: 0.85rem; text-transform: uppercase; }
    td { padding: 10px 12px; border-bottom: 1px solid #1e293b; font-size: 0.9rem; }
    tr:hover { background: #1e293b44; }
    .badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase; }
    .badge-high { background: #991b1b; color: #fca5a5; }
    .badge-medium { background: #92400e; color: #fcd34d; }
    .badge-low { background: #1e3a5f; color: #93c5fd; }
    .section { background: #1e293b; border-radius: 10px; padding: 20px; margin: 15px 0; }
    .tag { display: inline-block; background: #334155; color: #cbd5e1; padding: 4px 10px; border-radius: 6px; margin: 3px; font-size: 0.85rem; }
    .quote { border-left: 3px solid #818cf8; padding: 10px 15px; margin: 10px 0; background: #1e293b; border-radius: 0 8px 8px 0; }
    .quote .speaker { color: #818cf8; font-weight: bold; margin-top: 5px; }
    a { color: #60a5fa; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .back { margin-bottom: 20px; }
    .verified { color: #4ade80; }
    .unverified { color: #94a3b8; }
    .nav { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
    .nav a { background: #334155; padding: 6px 14px; border-radius: 6px; font-size: 0.85rem; }
    .nav a:hover { background: #475569; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <div class="back"><a href="/api/pharma">&larr; All Companies</a></div>

    <h1>${company.name} (${company.ticker})</h1>
    <p class="subtitle">
      <span class="${company.verified ? 'verified' : 'unverified'}">${company.verified ? 'Verified' : 'Unverified'}</span>
      &middot; Last updated: ${profile.lastUpdated}
      &middot; <a href="${company.irPageUrl}" target="_blank">IR Page</a>
    </p>

    <div class="nav">
      <a href="#pipeline">Pipeline</a>
      <a href="#catalysts">Catalysts</a>
      <a href="#deals">Deals</a>
      <a href="#strategy">Strategy</a>
      <a href="#revenue">Revenue</a>
      <a href="/api/pharma/${company.ticker}">JSON</a>
      <a href="/api/pharma/${company.ticker}/pipeline">Pipeline JSON</a>
      <a href="/api/pharma/${company.ticker}/catalysts">Catalysts JSON</a>
    </div>

    ${keyFinancials ? `
    <div class="meta">
      <div class="meta-card">
        <div class="label">R&D Spend</div>
        <div class="value">${keyFinancials.rdSpend || '-'}</div>
      </div>
      <div class="meta-card">
        <div class="label">BD Investment (since 2021)</div>
        <div class="value">${keyFinancials.bdInvestmentSince2021 || '-'}</div>
      </div>
      <div class="meta-card">
        <div class="label">Phase 3 Studies</div>
        <div class="value">${keyFinancials.phase3StudiesOngoing ?? '-'}</div>
      </div>
      <div class="meta-card">
        <div class="label">Expected Launches</div>
        <div class="value">${keyFinancials.expectedLaunches || '-'}</div>
      </div>
    </div>` : ''}

    <div class="meta">
      <div class="meta-card">
        <div class="label">Total Pipeline Assets</div>
        <div class="value">${pipelineStats.totalAssets}</div>
      </div>
      <div class="meta-card">
        <div class="label">Therapeutic Areas</div>
        <div class="value">${Object.keys(pipelineStats.byTherapeuticArea).length}</div>
      </div>
      <div class="meta-card">
        <div class="label">Upcoming Catalysts</div>
        <div class="value">${catalysts.length}</div>
      </div>
      <div class="meta-card">
        <div class="label">Recent Deals</div>
        <div class="value">${recentDeals.length}</div>
      </div>
    </div>

    <h2 id="pipeline">Pipeline (${pipeline.length} assets)</h2>
    <table>
      <thead>
        <tr><th>Drug</th><th>Phase</th><th>Indication</th><th>Mechanism</th><th>Modality</th><th>Peak Revenue</th><th>Readout</th><th>Partner</th></tr>
      </thead>
      <tbody>${pipelineRows}</tbody>
    </table>

    <h3>Pipeline by Phase</h3>
    <div>${Object.entries(pipelineStats.byPhase).map(([k, v]) => `<span class="tag">${k}: ${v}</span>`).join('')}</div>

    <h3>Pipeline by Therapeutic Area</h3>
    <div>${Object.entries(pipelineStats.byTherapeuticArea).map(([k, v]) => `<span class="tag">${k}: ${v}</span>`).join('')}</div>

    <h2 id="catalysts">Upcoming Catalysts (${catalysts.length})</h2>
    <table>
      <thead>
        <tr><th>Date</th><th>Significance</th><th>Drug</th><th>Indication</th><th>Event</th></tr>
      </thead>
      <tbody>${catalystRows}</tbody>
    </table>

    <h2 id="deals">Recent Deals (${recentDeals.length})</h2>
    <table>
      <thead>
        <tr><th>Date</th><th>Type</th><th>Target</th><th>Asset</th><th>Rationale</th></tr>
      </thead>
      <tbody>${dealRows}</tbody>
    </table>

    <h2 id="strategy">Strategic Priorities</h2>
    <div class="section">
      <h3>Key Priorities</h3>
      <ul>${strategy.priorities.map((p) => `<li>${p}</li>`).join('')}</ul>

      <h3>Therapeutic Focus</h3>
      <div>${strategy.therapeuticFocus.map((t) => `<span class="tag">${t}</span>`).join('')}</div>

      <h3>Modality Investments</h3>
      <div>${strategy.modalityInvestments.map((m) => `<span class="tag">${m}</span>`).join('')}</div>

      <h3>Whitespace / Opportunity Areas</h3>
      <div>${strategy.whitespaceAreas.map((w) => `<span class="tag">${w}</span>`).join('')}</div>

      <h3>BD Appetite</h3>
      <p><strong>High Interest:</strong></p>
      <ul>${strategy.bdAppetite.highInterest.map((h) => `<li>${h}</li>`).join('')}</ul>
      <p><strong>Moderate Interest:</strong></p>
      <ul>${strategy.bdAppetite.moderateInterest.map((m) => `<li>${m}</li>`).join('')}</ul>
      <p><strong>Low Interest:</strong></p>
      <ul>${strategy.bdAppetite.lowInterest.map((l) => `<li>${l}</li>`).join('')}</ul>
    </div>

    ${strategy.keyQuotes.length > 0 ? `
    <h3>Key Quotes</h3>
    ${strategy.keyQuotes.map((q) => `
      <div class="quote">
        <p>"${q.quote}"</p>
        <p class="speaker">&mdash; ${q.speaker}, ${q.context}</p>
      </div>
    `).join('')}` : ''}

    <h2 id="revenue">Revenue Opportunities</h2>
    <table>
      <thead>
        <tr><th>Therapeutic Area</th><th>Target Year</th><th>Estimate</th><th>Key Assets</th></tr>
      </thead>
      <tbody>${revenueRows}</tbody>
    </table>

    <p style="margin-top: 40px; color: #64748b; font-size: 0.85rem;">
      Source: ${strategy.source || 'Pharma Intelligence Module'} | Helix Intelligence Platform
    </p>
  </div>
</body>
</html>`;
}
//# sourceMappingURL=pharma-routes.js.map