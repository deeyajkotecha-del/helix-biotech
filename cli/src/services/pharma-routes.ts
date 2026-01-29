/**
 * Pharma Intelligence Routes
 *
 * Express Router providing pharma profile endpoints,
 * pipeline views, catalyst tracking, BD fit analysis,
 * and JPM presentation URLs.
 */

import { Router, Request, Response } from 'express';
import { PHARMA_COMPANIES, getAllTickers, getVerifiedCompanies, getJPM2026Urls } from './pharma-registry';
import {
  getPharmaProfile,
  getAllPharmaSummary,
  comparePipelines,
  analyzeBDFit,
  getUpcomingCatalysts,
} from './pharma-data';

export const pharmaRouter = Router();

// ============================================
// GET /api/pharma — List all companies
// ============================================
pharmaRouter.get('/api/pharma', (_req: Request, res: Response) => {
  const companies = getAllPharmaSummary();
  res.json({
    count: companies.length,
    companies,
    verifiedCompanies: getVerifiedCompanies().map((c) => c.ticker),
  });
});

// ============================================
// GET /api/pharma/catalysts — All upcoming catalysts
// ============================================
pharmaRouter.get('/api/pharma/catalysts', (_req: Request, res: Response) => {
  const catalysts = getUpcomingCatalysts();
  res.json({
    count: catalysts.length,
    catalysts,
  });
});

// ============================================
// GET /api/pharma/jpm2026 — JPM presentation URLs
// ============================================
pharmaRouter.get('/api/pharma/jpm2026', (_req: Request, res: Response) => {
  const urls = getJPM2026Urls();
  res.json({
    conference: 'JPM Healthcare Conference 2026',
    companies: urls,
  });
});

// ============================================
// GET /api/pharma/compare?a=MRK&b=PFE — Compare pipelines
// ============================================
pharmaRouter.get('/api/pharma/compare', (req: Request, res: Response) => {
  const tickerA = (req.query.a as string || '').toUpperCase();
  const tickerB = (req.query.b as string || '').toUpperCase();

  if (!tickerA || !tickerB) {
    res.status(400).json({ error: 'Provide ?a=TICKER&b=TICKER' });
    return;
  }

  const result = comparePipelines(tickerA, tickerB);
  if (!result) {
    res.status(404).json({ error: `One or both tickers not found: ${tickerA}, ${tickerB}` });
    return;
  }

  res.json(result);
});

// ============================================
// GET /api/pharma/bd-fit?target=MRK&area=oncology&modality=ADC
// ============================================
pharmaRouter.get('/api/pharma/bd-fit', (req: Request, res: Response) => {
  const target = (req.query.target as string || '').toUpperCase();
  const area = req.query.area as string || '';
  const modality = req.query.modality as string || '';

  if (!target || !area) {
    res.status(400).json({ error: 'Provide ?target=TICKER&area=therapeutic_area&modality=modality_type' });
    return;
  }

  const result = analyzeBDFit(target, area, modality);
  if (!result) {
    res.status(404).json({ error: `Company not found: ${target}` });
    return;
  }

  res.json(result);
});

// ============================================
// GET /api/pharma/:ticker — Full JSON profile
// ============================================
pharmaRouter.get('/api/pharma/:ticker', (req: Request, res: Response) => {
  const ticker = (req.params.ticker as string).toUpperCase();
  const profile = getPharmaProfile(ticker);

  if (!profile) {
    res.status(404).json({ error: `Company not found: ${ticker}. Available: ${getAllTickers().join(', ')}` });
    return;
  }

  res.json(profile);
});

// ============================================
// GET /api/pharma/:ticker/pipeline — Pipeline only
// ============================================
pharmaRouter.get('/api/pharma/:ticker/pipeline', (req: Request, res: Response) => {
  const ticker = (req.params.ticker as string).toUpperCase();
  const profile = getPharmaProfile(ticker);

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
pharmaRouter.get('/api/pharma/:ticker/catalysts', (req: Request, res: Response) => {
  const ticker = (req.params.ticker as string).toUpperCase();
  const profile = getPharmaProfile(ticker);

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
pharmaRouter.get('/api/pharma/:ticker/strategy', (req: Request, res: Response) => {
  const ticker = (req.params.ticker as string).toUpperCase();
  const profile = getPharmaProfile(ticker);

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
pharmaRouter.get('/api/pharma/:ticker/deals', (req: Request, res: Response) => {
  const ticker = (req.params.ticker as string).toUpperCase();
  const profile = getPharmaProfile(ticker);

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
pharmaRouter.get('/api/pharma/:ticker/html', (req: Request, res: Response) => {
  const ticker = (req.params.ticker as string).toUpperCase();
  const profile = getPharmaProfile(ticker);

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

function generateProfileHtml(profile: ReturnType<typeof getPharmaProfile>): string {
  if (!profile) return '<h1>Not Found</h1>';

  const { company, pipeline, catalysts, recentDeals, strategy, revenueOpportunities, pipelineStats, keyFinancials } = profile;

  const pipelineRows = pipeline
    .map(
      (a) => `
    <tr>
      <td><strong>${a.drugName}</strong>${a.genericName ? `<br><small>${a.genericName}</small>` : ''}</td>
      <td>${a.phase >= 4 ? 'Approved' : `Phase ${a.phase}`}</td>
      <td>${a.indication}</td>
      <td>${a.mechanism}</td>
      <td>${a.modality}</td>
      <td>${a.peakRevenuePotential || '-'}</td>
      <td>${a.expectedReadout || a.expectedApproval || '-'}</td>
      <td>${a.partner || '-'}</td>
    </tr>`
    )
    .join('');

  const catalystRows = catalysts
    .map(
      (c) => `
    <tr>
      <td>${c.date}</td>
      <td><span class="badge badge-${c.significance}">${c.significance}</span></td>
      <td>${c.drugName}</td>
      <td>${c.indication}</td>
      <td>${c.description}</td>
    </tr>`
    )
    .join('');

  const dealRows = recentDeals
    .map(
      (d) => `
    <tr>
      <td>${d.date}</td>
      <td>${d.type}</td>
      <td>${d.targetCompany || '-'}</td>
      <td>${d.asset || '-'}</td>
      <td>${d.rationale || '-'}</td>
    </tr>`
    )
    .join('');

  const revenueRows = revenueOpportunities
    .map(
      (r) => `
    <tr>
      <td>${r.therapeuticArea}</td>
      <td>${r.targetYear}</td>
      <td>${r.revenueEstimate}</td>
      <td>${r.keyAssets.join(', ')}</td>
    </tr>`
    )
    .join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${company.name} (${company.ticker}) - Pharma Intelligence</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    :root {
      --background: #FAF9F7;
      --surface: #FFFFFF;
      --surface-hover: #F5F4F2;
      --border: #E5E4E2;
      --text-primary: #1A1915;
      --text-secondary: #706F6C;
      --text-muted: #9B9A97;
      --accent: #D97756;
      --accent-hover: #C4684A;
      --success: #5B8C6F;
      --warning: #D4A84B;
      --error: #C75D5D;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--background); color: var(--text-primary); padding: 20px; line-height: 1.6; }
    .container { max-width: 1200px; margin: 0 auto; }
    h1 { color: var(--text-primary); margin-bottom: 8px; font-weight: 700; }
    h2 { color: var(--text-primary); margin: 30px 0 15px; border-bottom: 1px solid var(--border); padding-bottom: 8px; font-weight: 600; }
    h3 { color: var(--text-secondary); margin: 20px 0 10px; font-weight: 600; }
    .subtitle { color: var(--text-secondary); margin-bottom: 20px; }
    .meta { display: flex; gap: 20px; margin-bottom: 25px; flex-wrap: wrap; }
    .meta-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 15px 20px; flex: 1; min-width: 200px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .meta-card .label { color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .meta-card .value { color: var(--text-primary); font-size: 1.3rem; font-weight: 700; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0 25px; background: var(--surface); border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    th { background: var(--surface-hover); color: var(--text-secondary); padding: 12px 14px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 0.9rem; color: var(--text-primary); }
    tr:hover { background: var(--surface-hover); }
    tr:last-child td { border-bottom: none; }
    .badge { padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .badge-high { background: #FEE2E2; color: var(--error); }
    .badge-medium { background: #FEF3C7; color: #B45309; }
    .badge-low { background: #DBEAFE; color: #1D4ED8; }
    .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .tag { display: inline-block; background: var(--surface-hover); color: var(--text-secondary); padding: 4px 12px; border-radius: 8px; margin: 3px; font-size: 0.85rem; border: 1px solid var(--border); }
    .quote { border-left: 3px solid var(--accent); padding: 10px 15px; margin: 10px 0; background: var(--surface); border-radius: 0 8px 8px 0; }
    .quote .speaker { color: var(--accent); font-weight: 600; margin-top: 5px; }
    a { color: var(--accent); text-decoration: none; font-weight: 500; }
    a:hover { color: var(--accent-hover); text-decoration: underline; }
    .back { margin-bottom: 20px; }
    .verified { color: var(--success); font-weight: 600; }
    .unverified { color: var(--text-muted); }
    .nav { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
    .nav a { background: var(--surface); border: 1px solid var(--border); padding: 8px 16px; border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary); font-weight: 500; }
    .nav a:hover { background: var(--surface-hover); text-decoration: none; color: var(--text-primary); }
    ul { margin-left: 20px; color: var(--text-secondary); }
    li { margin: 8px 0; }
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
      Source: ${strategy.source || 'Pharma Intelligence Module'} | Satya Bio
    </p>
  </div>
</body>
</html>`;
}
