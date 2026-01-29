"use strict";
/**
 * Serve Command
 *
 * Start an HTTP server for browser-based access to the analysis API.
 *
 * Examples:
 *   helix serve                 # Start on default port 3001
 *   helix serve --port 8080     # Start on custom port
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerServeCommand = registerServeCommand;
const chalk_1 = __importDefault(require("chalk"));
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const sec_edgar_1 = require("../services/sec-edgar");
const companies_1 = require("../services/companies");
const llm_1 = require("../services/llm");
const config_1 = require("../config");
const landscape_1 = require("../services/landscape");
const trials_1 = require("../services/trials");
const molecules_1 = require("../services/molecules");
const trial_results_1 = require("../services/trial-results");
const patents_1 = require("../services/patents");
const pharma_routes_1 = require("../services/pharma-routes");
const target_report_1 = require("../services/target-report");
const export_1 = require("../services/export");
// Cache directory for analysis results
const CACHE_DIR = path.resolve(__dirname, '..', '..', 'cache');
// Rate limiting: track timestamps of Claude API calls
const apiCallTimestamps = [];
const RATE_LIMIT_MAX_CALLS = 10;
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour
function registerServeCommand(program) {
    program
        .command('serve')
        .description('Start HTTP server for browser-based API access')
        .option('-p, --port <port>', 'Port to listen on', '3001')
        .action(async (options) => {
        // Use PORT env var (for Railway/Docker) or command line option
        const port = parseInt(process.env.PORT || options.port, 10);
        startServer(port);
    });
}
function startServer(port) {
    const app = (0, express_1.default)();
    // Log configuration at startup
    const config = (0, config_1.getConfig)();
    console.log('');
    console.log(chalk_1.default.yellow('Configuration:'));
    console.log(chalk_1.default.gray(`  LLM_PROVIDER: ${config.llmProvider}`));
    console.log(chalk_1.default.gray(`  CLAUDE_MODEL: ${config.claudeModel}`));
    console.log(chalk_1.default.gray(`  ANTHROPIC_API_KEY: ${config.claudeApiKey ? '***' + config.claudeApiKey.slice(-4) : 'NOT SET'}`));
    // Enable CORS for browser access
    app.use((0, cors_1.default)());
    app.use(express_1.default.json());
    // Ensure cache directory exists
    if (!fs.existsSync(CACHE_DIR)) {
        fs.mkdirSync(CACHE_DIR, { recursive: true });
        console.log(chalk_1.default.gray(`  Created cache directory: ${CACHE_DIR}`));
    }
    // Mount pharma intelligence routes
    app.use(pharma_routes_1.pharmaRouter);
    // Homepage - Helix Research Portal
    app.get('/', (_req, res) => {
        res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Helix Research Portal</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
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
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--background); color: var(--text-primary); min-height: 100vh; line-height: 1.6; }
    .hero { background: var(--surface); padding: 80px 20px; text-align: center; border-bottom: 1px solid var(--border); }
    .hero h1 { font-size: 2.5rem; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; letter-spacing: -0.02em; }
    .hero p { color: var(--text-secondary); font-size: 1.1rem; margin-bottom: 35px; }
    .search-box { max-width: 600px; margin: 0 auto; display: flex; gap: 12px; }
    .search-box input { flex: 1; padding: 14px 18px; font-size: 1rem; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); color: var(--text-primary); outline: none; transition: all 0.2s; }
    .search-box input::placeholder { color: var(--text-muted); }
    .search-box input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(217, 119, 86, 0.1); }
    .search-box button { padding: 14px 28px; font-size: 1rem; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; transition: all 0.2s; }
    .search-box button:hover { background: var(--accent-hover); }
    .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
    .quick-links { display: flex; gap: 12px; justify-content: center; margin-top: 30px; flex-wrap: wrap; }
    .quick-links a { padding: 10px 18px; background: var(--background); color: var(--text-secondary); text-decoration: none; border-radius: 20px; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; border: 1px solid var(--border); }
    .quick-links a:hover { background: var(--surface-hover); color: var(--text-primary); border-color: var(--accent); }
    .section-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 24px; margin-top: 40px; }
    .section-card { background: var(--surface); border-radius: 12px; padding: 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    .section-card h2 { color: var(--text-primary); font-size: 1.2rem; font-weight: 600; margin-bottom: 18px; display: flex; align-items: center; gap: 10px; }
    .endpoint { background: var(--background); padding: 14px 16px; margin: 12px 0; border-radius: 8px; border-left: 3px solid var(--accent); }
    .endpoint a { color: var(--accent); text-decoration: none; font-weight: 500; }
    .endpoint a:hover { text-decoration: underline; color: var(--accent-hover); }
    .endpoint p { color: var(--text-secondary); font-size: 0.85rem; margin-top: 6px; }
    .method { color: var(--success); font-weight: 600; font-size: 0.75rem; margin-right: 8px; }
    .pharma-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 10px; margin-top: 16px; }
    .pharma-link { background: var(--background); padding: 10px 12px; border-radius: 6px; text-align: center; color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; border: 1px solid var(--border); }
    .pharma-link:hover { background: var(--accent); color: white; border-color: var(--accent); }
    .footer { text-align: center; color: var(--text-muted); padding: 40px 20px; border-top: 1px solid var(--border); margin-top: 50px; font-size: 0.9rem; }
    .footer a { color: var(--accent); text-decoration: none; }
    .footer a:hover { text-decoration: underline; }
    .featured { background: linear-gradient(135deg, var(--accent) 0%, #B85A3D 100%); border: none; box-shadow: 0 4px 12px rgba(217, 119, 86, 0.25); }
    .featured h2 { color: white; }
    .featured .endpoint { background: rgba(255,255,255,0.15); border-left-color: rgba(255,255,255,0.5); }
    .featured .endpoint a { color: white; }
    .featured .endpoint p { color: rgba(255,255,255,0.8); }
    .featured .method { color: rgba(255,255,255,0.9); }
  </style>
</head>
<body>
  <div class="hero">
    <h1>Helix Research Portal</h1>
    <p>Biotech competitive intelligence powered by real-time data</p>

    <form class="search-box" onsubmit="event.preventDefault(); const q = document.getElementById('target-search').value; if(q) window.location.href = '/api/report/target/' + encodeURIComponent(q) + '/html';">
      <input type="text" id="target-search" placeholder="Enter target, indication, or drug name (e.g., B7-H3, NSCLC, pembrolizumab)">
      <button type="submit">Generate Report</button>
    </form>

    <div class="quick-links">
      <a href="/api/report/target/B7-H3/html">B7-H3 ADCs</a>
      <a href="/api/report/target/TL1A/html">TL1A Inhibitors</a>
      <a href="/api/report/target/GLP-1/html">GLP-1 Agonists</a>
      <a href="/api/landscape/ulcerative%20colitis/molecules/html">UC Landscape</a>
      <a href="/api/pharma/MRK/html">Merck Profile</a>
    </div>
  </div>

  <div class="container">
    <div class="section-grid">
      <div class="section-card featured">
        <h2>Target Intelligence Reports</h2>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/report/target/B7-H3/html">/api/report/target/:target/html</a>
          <p>Comprehensive report: trials, publications, deals, KOLs</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/report/target/B7-H3/excel">/api/report/target/:target/excel</a>
          <p>Download multi-tab Excel workbook</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/report/target/B7-H3">/api/report/target/:target</a>
          <p>JSON API for programmatic access</p>
        </div>
      </div>

      <div class="section-card">
        <h2>Pharma Intelligence</h2>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/pharma/MRK/html">/api/pharma/:ticker/html</a>
          <p>Pipeline, catalysts, deals, BD strategy</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/pharma/bd-fit?target=MRK&area=ophthalmology&modality=ADC">/api/pharma/bd-fit</a>
          <p>Analyze BD fit for assets</p>
        </div>
        <div class="pharma-grid">
          <a href="/api/pharma/MRK/html" class="pharma-link">MRK</a>
          <a href="/api/pharma/PFE/html" class="pharma-link">PFE</a>
          <a href="/api/pharma/LLY/html" class="pharma-link">LLY</a>
          <a href="/api/pharma/ABBV/html" class="pharma-link">ABBV</a>
          <a href="/api/pharma/BMY/html" class="pharma-link">BMY</a>
          <a href="/api/pharma/AZN/html" class="pharma-link">AZN</a>
          <a href="/api/pharma/JNJ/html" class="pharma-link">JNJ</a>
          <a href="/api/pharma/NVS/html" class="pharma-link">NVS</a>
          <a href="/api/pharma/AMGN/html" class="pharma-link">AMGN</a>
          <a href="/api/pharma/GILD/html" class="pharma-link">GILD</a>
        </div>
      </div>

      <div class="section-card">
        <h2>Therapeutic Landscapes</h2>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/landscape/ulcerative%20colitis/full">/api/landscape/:condition/full</a>
          <p>Complete landscape analysis</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/landscape/ulcerative%20colitis/molecules/html">/api/landscape/:condition/molecules/html</a>
          <p>All drugs in development</p>
        </div>
      </div>

      <div class="section-card">
        <h2>Clinical Trial Analysis</h2>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/trial/NCT02819635/results/html">/api/trial/:nctId/results/html</a>
          <p>Deep efficacy &amp; safety data</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/compare-trials/html?ncts=NCT02819635,NCT03518086">/api/compare-trials/html</a>
          <p>Head-to-head trial comparison</p>
        </div>
      </div>

      <div class="section-card">
        <h2>Patent &amp; Exclusivity</h2>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/patents/rinvoq/html">/api/patents/:drugName/html</a>
          <p>Patent protection timeline</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/patents/condition/ulcerative%20colitis/html">/api/patents/condition/:condition/html</a>
          <p>LOE timeline by therapeutic area</p>
        </div>
      </div>

      <div class="section-card">
        <h2>Company Analysis</h2>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/report/MRNA">/api/report/:ticker</a>
          <p>SEC filing analysis (10-K)</p>
        </div>
        <div class="endpoint">
          <span class="method">GET</span> <a href="/api/dashboard">/api/dashboard</a>
          <p>Analyzed companies dashboard</p>
        </div>
      </div>
    </div>

    <footer class="footer">
      <p>Helix Intelligence Platform</p>
      <p style="margin-top: 8px;">Data: <a href="https://clinicaltrials.gov">ClinicalTrials.gov</a> | <a href="https://pubmed.ncbi.nlm.nih.gov">PubMed</a> | <a href="https://www.fda.gov">FDA</a> | <a href="https://www.sec.gov/edgar">SEC EDGAR</a></p>
    </footer>
  </div>
</body>
</html>`);
    });
    // Health check endpoint
    app.get('/api/health', (_req, res) => {
        const rateLimit = getRateLimitStatus();
        res.json({
            status: 'ok',
            timestamp: new Date().toISOString(),
            rateLimit: {
                remaining: rateLimit.remaining,
                limit: RATE_LIMIT_MAX_CALLS,
                resetInMinutes: rateLimit.resetInMinutes
            }
        });
    });
    // Get all XBI companies
    app.get('/api/companies', async (_req, res) => {
        try {
            const companies = await (0, companies_1.getAllCompanies)();
            res.json({
                count: companies.length,
                companies: companies.map(c => ({
                    ticker: c.ticker,
                    name: c.name,
                    marketCap: c.weight ? `$${(c.weight * 100).toFixed(1)}B` : null,
                    sector: c.sector,
                    stage: c.stage
                }))
            });
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Batch analyze multiple tickers
    app.post('/api/analyze/batch', async (req, res) => {
        try {
            const { tickers } = req.body;
            if (!tickers || !Array.isArray(tickers)) {
                res.status(400).json({ error: 'Request body must include "tickers" array' });
                return;
            }
            const results = [];
            for (let i = 0; i < tickers.length; i++) {
                const ticker = tickers[i].toUpperCase();
                try {
                    // Check cache first
                    const cached = getCachedAnalysis(ticker);
                    if (cached) {
                        results.push({ ticker, status: 'cached', cached: true });
                        continue;
                    }
                    // Check rate limit before calling Claude
                    if (isRateLimitExceeded()) {
                        // Try to get expired cache as fallback
                        const expiredCache = getCachedAnalysisIgnoreExpiry(ticker);
                        if (expiredCache) {
                            console.log(chalk_1.default.yellow(`  [Batch] Rate limit reached, using expired cache for ${ticker}`));
                            results.push({ ticker, status: 'rate-limited-cached', cached: true });
                        }
                        else {
                            const { resetInMinutes } = getRateLimitStatus();
                            console.log(chalk_1.default.red(`  [Batch] Rate limit reached for ${ticker}, no cache available`));
                            results.push({ ticker, status: `rate-limited (reset in ${resetInMinutes}m)` });
                        }
                        continue;
                    }
                    // Rate limit: wait 10 seconds between API calls (except first)
                    if (i > 0) {
                        console.log(chalk_1.default.gray(`  [Batch] Waiting 10s before analyzing ${ticker}...`));
                        await sleep(10000);
                    }
                    console.log(chalk_1.default.cyan(`  [Batch] Analyzing ${ticker} (${i + 1}/${tickers.length})...`));
                    // Get filing
                    const filings = await (0, sec_edgar_1.getFilings)(ticker, 5);
                    const filing = filings.find(f => f.form === '10-K' || f.form === '10-K/A');
                    if (!filing) {
                        results.push({ ticker, status: 'no-10k-filing' });
                        continue;
                    }
                    // Analyze
                    const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing);
                    const llm = (0, llm_1.getLLMProvider)();
                    let analysis = await llm.analyze(content, ticker);
                    recordApiCall(); // Record the API call for rate limiting
                    analysis = postProcessAnalysis(analysis, filing);
                    // Save to cache
                    saveCachedAnalysis(ticker, filing.filingDate, analysis);
                    results.push({ ticker, status: 'analyzed', cached: false });
                }
                catch (err) {
                    results.push({ ticker, status: `error: ${err instanceof Error ? err.message : 'unknown'}` });
                }
            }
            res.json({
                completed: results.length,
                results
            });
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Dashboard - HTML view of all analyzed companies
    app.get('/api/dashboard', async (_req, res) => {
        try {
            // Get all cached analyses
            const cachedAnalyses = getAllCachedAnalyses();
            // Get company info for each
            const dashboardData = await Promise.all(cachedAnalyses.map(async (cached) => {
                const company = await (0, companies_1.getCompanyByTicker)(cached.ticker);
                const mostAdvancedPhase = getMostAdvancedPhase(cached.analysis.pipeline);
                const keyCatalyst = getKeyCatalyst(cached.analysis.pipeline);
                return {
                    ticker: cached.ticker,
                    name: company?.name || cached.ticker,
                    filingDate: cached.filingDate,
                    marketCap: cached.analysis.company.marketCap,
                    phase: mostAdvancedPhase,
                    runway: cached.analysis.financials.runwayMonths,
                    cash: cached.analysis.financials.cash,
                    catalyst: keyCatalyst,
                    pipelineCount: cached.analysis.pipeline.length
                };
            }));
            // Sort by phase (most advanced first)
            dashboardData.sort((a, b) => getPhaseRank(b.phase) - getPhaseRank(a.phase));
            const html = generateDashboardHtml(dashboardData);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // List filings for a ticker
    app.get('/api/filings/:ticker', async (req, res) => {
        try {
            const ticker = req.params.ticker.toUpperCase();
            const company = await (0, companies_1.getCompanyByTicker)(ticker);
            const filings = await (0, sec_edgar_1.getFilings)(ticker, 10);
            res.json({
                ticker,
                company: company?.name || ticker,
                filings: filings.map(f => ({
                    form: f.form,
                    filingDate: f.filingDate,
                    reportDate: f.reportDate,
                    url: f.fileUrl
                }))
            });
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Analyze a ticker
    app.get('/api/analyze/:ticker', async (req, res) => {
        try {
            const ticker = req.params.ticker.toUpperCase();
            const useMock = req.query.mock === 'true';
            const form = req.query.form?.toUpperCase() || '10-K';
            // Get company info
            const company = await (0, companies_1.getCompanyByTicker)(ticker);
            // Fetch filings
            const filings = await (0, sec_edgar_1.getFilings)(ticker, 10);
            if (filings.length === 0) {
                res.status(404).json({ error: `No filings found for ${ticker}` });
                return;
            }
            // Find requested filing type
            const filing = filings.find(f => f.form === form || f.form === `${form}/A`);
            if (!filing) {
                res.status(404).json({
                    error: `No ${form} filing found for ${ticker}`,
                    availableFilings: filings.slice(0, 5).map(f => ({ form: f.form, date: f.filingDate }))
                });
                return;
            }
            let analysis;
            let fromCache = false;
            if (useMock) {
                // Return mock data
                analysis = getMockAnalysis(ticker);
            }
            else {
                // Check cache first
                const cached = getCachedAnalysis(ticker);
                if (cached) {
                    console.log(chalk_1.default.green(`  [Cache] Using cached analysis for ${ticker}`));
                    analysis = cached.analysis;
                    fromCache = true;
                }
                else {
                    // Check rate limit before calling Claude
                    if (isRateLimitExceeded()) {
                        // Try to get expired cache as fallback
                        const expiredCache = getCachedAnalysisIgnoreExpiry(ticker);
                        if (expiredCache) {
                            console.log(chalk_1.default.yellow(`  [Rate Limit] Using expired cache for ${ticker}`));
                            analysis = expiredCache.analysis;
                            fromCache = true;
                        }
                        else {
                            const { resetInMinutes } = getRateLimitStatus();
                            res.status(429).json({
                                error: 'Rate limit reached, try again later',
                                resetInMinutes
                            });
                            return;
                        }
                    }
                    else {
                        // Fetch filing content and analyze
                        console.log(chalk_1.default.yellow(`  [API] Running Claude analysis for ${ticker}...`));
                        const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing);
                        const llm = (0, llm_1.getLLMProvider)();
                        analysis = await llm.analyze(content, ticker);
                        recordApiCall(); // Record the API call for rate limiting
                        // Post-process to fix common LLM issues
                        analysis = postProcessAnalysis(analysis, filing);
                        // Save to cache
                        saveCachedAnalysis(ticker, filing.filingDate, analysis);
                    }
                }
            }
            // Remove rawResponse to reduce response size
            const { rawResponse, ...cleanAnalysis } = analysis;
            res.json({
                ticker,
                company: company?.name || ticker,
                filing: {
                    form: filing.form,
                    filingDate: filing.filingDate,
                    reportDate: filing.reportDate,
                    url: filing.fileUrl
                },
                analysis: cleanAnalysis,
                provider: useMock ? 'mock' : (0, config_1.getConfig)().llmProvider,
                cached: fromCache,
                mock: useMock
            });
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // HTML Report endpoint
    app.get('/api/report/:ticker', async (req, res) => {
        try {
            const ticker = req.params.ticker.toUpperCase();
            const useMock = req.query.mock === 'true';
            // Get company info
            const company = await (0, companies_1.getCompanyByTicker)(ticker);
            // Check cache first for instant loading
            const cached = getCachedAnalysis(ticker);
            if (cached && !useMock) {
                console.log(chalk_1.default.green(`  [Cache] Using cached analysis for ${ticker}`));
                const html = generateHtmlReport(ticker, company?.name || ticker, { form: '10-K', filingDate: cached.filingDate, reportDate: cached.filingDate, fileUrl: '' }, cached.analysis);
                res.setHeader('Content-Type', 'text/html');
                res.send(html);
                return;
            }
            // Fetch filings
            const filings = await (0, sec_edgar_1.getFilings)(ticker, 10);
            if (filings.length === 0) {
                res.status(404).send(`<h1>No filings found for ${ticker}</h1>`);
                return;
            }
            const filing = filings.find(f => f.form === '10-K' || f.form === '10-K/A') || filings[0];
            let analysis;
            if (useMock) {
                analysis = getMockAnalysis(ticker);
            }
            else {
                // Check rate limit before calling Claude
                if (isRateLimitExceeded()) {
                    // Try to get expired cache as fallback
                    const expiredCache = getCachedAnalysisIgnoreExpiry(ticker);
                    if (expiredCache) {
                        console.log(chalk_1.default.yellow(`  [Rate Limit] Using expired cache for ${ticker}`));
                        analysis = expiredCache.analysis;
                    }
                    else {
                        const { resetInMinutes } = getRateLimitStatus();
                        res.status(429).send(`<h1>Rate limit reached</h1><p>Try again in ${resetInMinutes} minutes.</p>`);
                        return;
                    }
                }
                else {
                    console.log(chalk_1.default.yellow(`  [API] Running Claude analysis for ${ticker}...`));
                    const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing);
                    const llm = (0, llm_1.getLLMProvider)();
                    analysis = await llm.analyze(content, ticker);
                    recordApiCall(); // Record the API call for rate limiting
                    analysis = postProcessAnalysis(analysis, filing);
                    // Save to cache for next time
                    saveCachedAnalysis(ticker, filing.filingDate, analysis);
                }
            }
            const html = generateHtmlReport(ticker, company?.name || ticker, filing, analysis);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // Search companies
    app.get('/api/search', async (req, res) => {
        try {
            const query = req.query.q;
            if (!query) {
                res.status(400).json({ error: 'Missing query parameter: q' });
                return;
            }
            const results = await (0, companies_1.searchCompanies)(query);
            res.json({ query, results });
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Therapeutic Landscape Dashboard
    app.get('/api/landscape/:condition/full', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            console.log(chalk_1.default.cyan(`  [Landscape] Building dashboard for "${condition}"...`));
            const data = await (0, landscape_1.getLandscapeData)(condition);
            const html = generateLandscapeHtml(data);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // Landscape CSV Export
    app.get('/api/landscape/:condition/csv', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            const data = await (0, landscape_1.getLandscapeData)(condition);
            const csv = (0, landscape_1.generateLandscapeCSV)(data);
            res.setHeader('Content-Type', 'text/csv');
            res.setHeader('Content-Disposition', `attachment; filename="landscape-${condition.replace(/\s+/g, '-')}.csv"`);
            res.send(csv);
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Landscape JSON API
    app.get('/api/landscape/:condition/json', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            const data = await (0, landscape_1.getLandscapeData)(condition);
            res.json(data);
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Molecules Landscape API
    app.get('/api/landscape/:condition/molecules', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            const maxTrials = parseInt(req.query.maxTrials) || 500;
            console.log(chalk_1.default.cyan(`  [Molecules] Fetching molecules for "${condition}"...`));
            // Fetch trials from ClinicalTrials.gov
            const trials = await (0, trials_1.searchTrialsByCondition)(condition, { maxResults: maxTrials });
            console.log(chalk_1.default.gray(`  [Molecules] Found ${trials.length} trials, extracting molecules...`));
            // Extract molecules from trials
            const molecules = (0, molecules_1.extractMoleculesFromTrials)(trials);
            console.log(chalk_1.default.green(`  [Molecules] Extracted ${molecules.length} unique molecules`));
            // Sort by highest phase (descending) then by trial count (descending)
            molecules.sort((a, b) => {
                const phaseDiff = getMoleculePhaseRank(b.highestPhase) - getMoleculePhaseRank(a.highestPhase);
                if (phaseDiff !== 0)
                    return phaseDiff;
                return b.trialCount - a.trialCount;
            });
            // Format response
            const response = {
                condition,
                totalTrials: trials.length,
                totalMolecules: molecules.length,
                fetchedAt: new Date().toISOString(),
                molecules: molecules.map(mol => ({
                    name: mol.name,
                    aliases: mol.aliases.slice(0, 3), // Limit aliases for readability
                    mechanism: mol.mechanism,
                    target: mol.target,
                    type: mol.type,
                    sponsor: mol.sponsors[0] || 'Unknown',
                    allSponsors: mol.sponsors,
                    highestPhase: mol.highestPhase,
                    trialCount: mol.trialCount,
                    activeTrialCount: mol.activeTrialCount,
                    leadTrialNctId: mol.leadTrialId,
                    conditions: mol.conditions.slice(0, 5), // Limit conditions
                }))
            };
            res.json(response);
        }
        catch (error) {
            console.error(chalk_1.default.red(`  [Molecules] Error: ${error instanceof Error ? error.message : 'Unknown'}`));
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Molecules HTML View
    app.get('/api/landscape/:condition/molecules/html', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            const maxTrials = parseInt(req.query.maxTrials) || 500;
            console.log(chalk_1.default.cyan(`  [Molecules] Building HTML view for "${condition}"...`));
            // Fetch trials from ClinicalTrials.gov
            const trials = await (0, trials_1.searchTrialsByCondition)(condition, { maxResults: maxTrials });
            // Extract molecules from trials
            const molecules = (0, molecules_1.extractMoleculesFromTrials)(trials);
            // Sort by highest phase then trial count
            molecules.sort((a, b) => {
                const phaseDiff = getMoleculePhaseRank(b.highestPhase) - getMoleculePhaseRank(a.highestPhase);
                if (phaseDiff !== 0)
                    return phaseDiff;
                return b.trialCount - a.trialCount;
            });
            const html = generateMoleculesHtml(condition, trials.length, molecules);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // ============================================
    // Trial Results Endpoints
    // ============================================
    // Trial Results JSON API
    app.get('/api/trial/:nctId/results', async (req, res) => {
        try {
            const nctId = req.params.nctId.toUpperCase();
            if (!nctId.startsWith('NCT')) {
                res.status(400).json({ error: 'Invalid NCT ID format. Expected format: NCT########' });
                return;
            }
            console.log(chalk_1.default.cyan(`  [Trial] Fetching results for ${nctId}...`));
            const data = await (0, trial_results_1.getFullTrialData)(nctId);
            if (!data) {
                res.status(404).json({ error: `Trial ${nctId} not found or has no data` });
                return;
            }
            if (!data.hasResults) {
                res.status(200).json({
                    ...data,
                    message: 'Trial found but no results have been posted yet',
                });
                return;
            }
            res.json(data);
        }
        catch (error) {
            console.error(chalk_1.default.red(`  [Trial] Error: ${error instanceof Error ? error.message : 'Unknown'}`));
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Trial Results HTML View
    app.get('/api/trial/:nctId/results/html', async (req, res) => {
        try {
            const nctId = req.params.nctId.toUpperCase();
            if (!nctId.startsWith('NCT')) {
                res.status(400).send('<h1>Error</h1><p>Invalid NCT ID format. Expected: NCT########</p>');
                return;
            }
            console.log(chalk_1.default.cyan(`  [Trial] Building HTML report for ${nctId}...`));
            const data = await (0, trial_results_1.getFullTrialData)(nctId);
            if (!data) {
                res.status(404).send(`<h1>Not Found</h1><p>Trial ${nctId} not found</p>`);
                return;
            }
            const html = generateTrialResultsHtml(data);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // Trial Comparison Endpoint
    app.get('/api/compare-trials', async (req, res) => {
        try {
            const nctsParam = req.query.ncts;
            if (!nctsParam) {
                res.status(400).json({
                    error: 'Missing required parameter: ncts',
                    example: '/api/compare-trials?ncts=NCT02819635,NCT03518086'
                });
                return;
            }
            const nctIds = nctsParam.split(',').map(id => id.trim().toUpperCase());
            if (nctIds.length < 2) {
                res.status(400).json({ error: 'At least 2 NCT IDs required for comparison' });
                return;
            }
            if (nctIds.length > 5) {
                res.status(400).json({ error: 'Maximum 5 trials can be compared at once' });
                return;
            }
            console.log(chalk_1.default.cyan(`  [Compare] Comparing ${nctIds.length} trials: ${nctIds.join(', ')}...`));
            const comparison = await (0, trial_results_1.compareTrials)(nctIds);
            if (comparison.trials.length === 0) {
                res.status(404).json({ error: 'No trial data found for the provided NCT IDs' });
                return;
            }
            res.json(comparison);
        }
        catch (error) {
            console.error(chalk_1.default.red(`  [Compare] Error: ${error instanceof Error ? error.message : 'Unknown'}`));
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Trial Comparison HTML View
    app.get('/api/compare-trials/html', async (req, res) => {
        try {
            const nctsParam = req.query.ncts;
            if (!nctsParam) {
                res.status(400).send('<h1>Error</h1><p>Missing required parameter: ncts</p><p>Example: /api/compare-trials/html?ncts=NCT02819635,NCT03518086</p>');
                return;
            }
            const nctIds = nctsParam.split(',').map(id => id.trim().toUpperCase());
            if (nctIds.length < 2 || nctIds.length > 5) {
                res.status(400).send('<h1>Error</h1><p>Provide 2-5 NCT IDs for comparison</p>');
                return;
            }
            console.log(chalk_1.default.cyan(`  [Compare] Building comparison HTML for ${nctIds.join(', ')}...`));
            const comparison = await (0, trial_results_1.compareTrials)(nctIds);
            if (comparison.trials.length === 0) {
                res.status(404).send('<h1>Not Found</h1><p>No trial data found</p>');
                return;
            }
            const html = generateTrialComparisonHtml(comparison);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // ============================================
    // Patent/Exclusivity Endpoints
    // NOTE: Condition routes MUST come before :drugName routes
    // to avoid Express matching "condition" as a drug name
    // ============================================
    // Patents by Condition JSON
    app.get('/api/patents/condition/:condition', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            console.log(chalk_1.default.cyan(`  [Patents] Finding patents for "${condition}" drugs...`));
            const profiles = await (0, patents_1.getPatentsByCondition)(condition);
            res.json({
                condition,
                drugCount: profiles.length,
                profiles,
                fetchedAt: new Date().toISOString(),
            });
        }
        catch (error) {
            res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
        }
    });
    // Patents by Condition HTML (Timeline)
    app.get('/api/patents/condition/:condition/html', async (req, res) => {
        try {
            const condition = decodeURIComponent(req.params.condition);
            console.log(chalk_1.default.cyan(`  [Patents] Building patent timeline for "${condition}"...`));
            const profiles = await (0, patents_1.getPatentsByCondition)(condition);
            const html = generatePatentTimelineHtml(condition, profiles);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // Patent Profile JSON (must be after /condition/ routes)
    app.get('/api/patents/:drugName', async (req, res) => {
        try {
            const drugName = decodeURIComponent(req.params.drugName);
            console.log(chalk_1.default.cyan(`  [Patents] Looking up "${drugName}"...`));
            const profile = await (0, patents_1.getDrugPatentProfile)(drugName);
            if (!profile) {
                res.status(404).json({ error: `No FDA approval found for "${drugName}"` });
                return;
            }
            res.json(profile);
        }
        catch (error) {
            res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
        }
    });
    // Patent Profile HTML (must be after /condition/ routes)
    app.get('/api/patents/:drugName/html', async (req, res) => {
        try {
            const drugName = decodeURIComponent(req.params.drugName);
            console.log(chalk_1.default.cyan(`  [Patents] Building HTML for "${drugName}"...`));
            const profile = await (0, patents_1.getDrugPatentProfile)(drugName);
            if (!profile) {
                res.status(404).send(`<h1>Not Found</h1><p>No FDA approval found for "${drugName}"</p>`);
                return;
            }
            const html = generatePatentProfileHtml(profile);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // ============================================
    // Target Report Routes
    // ============================================
    // Target Report - JSON
    app.get('/api/report/target/:target', async (req, res) => {
        try {
            const target = decodeURIComponent(req.params.target);
            console.log(chalk_1.default.cyan(`  [Report] Generating JSON report for "${target}"...`));
            const report = await (0, target_report_1.generateTargetReport)(target);
            res.json(report);
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Target Report - Excel Download
    app.get('/api/report/target/:target/excel', async (req, res) => {
        try {
            const target = decodeURIComponent(req.params.target);
            console.log(chalk_1.default.cyan(`  [Report] Generating Excel for "${target}"...`));
            const report = await (0, target_report_1.generateTargetReport)(target);
            const buffer = await (0, export_1.generateExcel)(report);
            const filename = `${target.replace(/[^a-zA-Z0-9]/g, '_')}_Report.xlsx`;
            res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
            res.send(buffer);
        }
        catch (error) {
            res.status(500).json({
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    });
    // Target Report - HTML
    app.get('/api/report/target/:target/html', async (req, res) => {
        try {
            const target = decodeURIComponent(req.params.target);
            console.log(chalk_1.default.cyan(`  [Report] Generating HTML report for "${target}"...`));
            const report = await (0, target_report_1.generateTargetReport)(target);
            const trialAnalytics = (0, target_report_1.getTrialAnalytics)(report.trials);
            const html = generateTargetReportHtml(report, trialAnalytics);
            res.setHeader('Content-Type', 'text/html');
            res.send(html);
        }
        catch (error) {
            res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
        }
    });
    // Start server
    app.listen(port, () => {
        console.log('');
        console.log(chalk_1.default.green.bold('Server running!'));
        console.log('');
        console.log(chalk_1.default.white('API Endpoints:'));
        console.log(chalk_1.default.gray(`  GET  /api/health`));
        console.log(chalk_1.default.gray(`  GET  /api/companies`));
        console.log(chalk_1.default.gray(`  GET  /api/filings/:ticker`));
        console.log(chalk_1.default.gray(`  GET  /api/analyze/:ticker`));
        console.log(chalk_1.default.gray(`  POST /api/analyze/batch`));
        console.log('');
        console.log(chalk_1.default.cyan('HTML Views:'));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/dashboard`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/report/MRNA`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/landscape/ulcerative%20colitis/full`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/landscape/ulcerative%20colitis/molecules/html`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/trial/NCT02819635/results/html`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/compare-trials/html?ncts=NCT02819635,NCT03518086`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/patents/rinvoq/html`));
        console.log(chalk_1.default.cyan(`  GET  http://localhost:${port}/api/patents/condition/ulcerative%20colitis/html`));
        console.log('');
        console.log(chalk_1.default.gray('API Endpoints (JSON):'));
        console.log(chalk_1.default.gray(`  GET  /api/landscape/:condition/molecules`));
        console.log(chalk_1.default.gray(`  GET  /api/trial/:nctId/results`));
        console.log(chalk_1.default.gray(`  GET  /api/compare-trials?ncts=NCT1,NCT2`));
        console.log(chalk_1.default.gray(`  GET  /api/patents/:drugName`));
        console.log(chalk_1.default.gray(`  GET  /api/patents/condition/:condition`));
        console.log('');
        console.log(chalk_1.default.magenta('Pharma Intelligence:'));
        console.log(chalk_1.default.magenta(`  GET  http://localhost:${port}/api/pharma`));
        console.log(chalk_1.default.magenta(`  GET  http://localhost:${port}/api/pharma/MRK/html`));
        console.log(chalk_1.default.magenta(`  GET  http://localhost:${port}/api/pharma/MRK`));
        console.log(chalk_1.default.magenta(`  GET  http://localhost:${port}/api/pharma/catalysts`));
        console.log(chalk_1.default.magenta(`  GET  http://localhost:${port}/api/pharma/compare?a=MRK&b=PFE`));
        console.log(chalk_1.default.magenta(`  GET  http://localhost:${port}/api/pharma/bd-fit?target=MRK&area=oncology&modality=ADC`));
        console.log('');
        console.log(chalk_1.default.gray(`Cache: ${CACHE_DIR}`));
        console.log('');
        console.log(chalk_1.default.yellow('Press Ctrl+C to stop'));
    });
}
// ============================================
// Post-processing (duplicated from analyze.ts for server use)
// ============================================
function postProcessAnalysis(analysis, filing) {
    const cleaned = JSON.parse(JSON.stringify(analysis));
    cleaned.pipeline = deduplicatePipeline(cleaned.pipeline);
    cleaned.financials = validateFinancials(cleaned.financials, filing);
    return cleaned;
}
function deduplicatePipeline(pipeline) {
    const drugMap = new Map();
    for (const item of pipeline) {
        const drugKey = item.drug.toLowerCase().trim();
        const existing = drugMap.get(drugKey);
        if (!existing) {
            drugMap.set(drugKey, item);
        }
        else {
            const existingScore = scoreEntry(existing);
            const newScore = scoreEntry(item);
            if (newScore > existingScore ||
                (newScore === existingScore && getPhaseRank(item.phase) > getPhaseRank(existing.phase))) {
                drugMap.set(drugKey, item);
            }
        }
    }
    return Array.from(drugMap.values());
}
function scoreEntry(item) {
    let score = 0;
    if (item.drug)
        score += 1;
    if (item.phase)
        score += 1;
    if (item.indication)
        score += 1;
    if (item.status)
        score += 2;
    if (item.catalyst)
        score += 2;
    return score;
}
function getPhaseRank(phase) {
    const p = phase.toLowerCase();
    if (p.includes('approved') || p.includes('marketed'))
        return 100;
    if (p.includes('bla') || p.includes('nda'))
        return 90;
    if (p.includes('3'))
        return 70;
    if (p.includes('2/3'))
        return 60;
    if (p.includes('2'))
        return 50;
    if (p.includes('1/2'))
        return 40;
    if (p.includes('1'))
        return 30;
    if (p.includes('preclinical') || p.includes('pre-clinical'))
        return 10;
    return 0;
}
function validateFinancials(financials, filing) {
    const validated = { ...financials };
    const warnings = [];
    const filingYear = new Date(filing.filingDate).getFullYear();
    if (validated.cashDate) {
        const yearMatch = validated.cashDate.match(/20\d{2}/);
        if (yearMatch) {
            const cashYear = parseInt(yearMatch[0]);
            if (filingYear - cashYear > 1) {
                warnings.push(`Cash date (${cashYear}) may be outdated for ${filingYear} filing`);
            }
        }
    }
    if (validated.runwayMonths !== null) {
        if (validated.runwayMonths > 120) {
            warnings.push('Runway >10 years seems unrealistic');
        }
        else if (validated.runwayMonths < 0) {
            warnings.push('Negative runway detected');
            validated.runwayMonths = null;
        }
    }
    if (warnings.length > 0) {
        validated.dataWarning = warnings.join('; ');
    }
    return validated;
}
// ============================================
// Mock data
// ============================================
function getMockAnalysis(ticker) {
    return {
        company: {
            name: `${ticker} Inc.`,
            ticker: ticker,
            marketCap: '$18.5B',
            employees: 5200
        },
        analystSummary: `${ticker} is a clinical-stage biotechnology company focused on developing novel mRNA therapeutics for infectious diseases and oncology. The company has a diversified pipeline with lead assets in Phase 3 trials. Strong cash position provides runway through 2026, though burn rate has increased due to expanded clinical programs. Key catalyst: Phase 3 data readout expected Q2 2025.`,
        financials: {
            cash: '$4.2B',
            cashDate: 'Dec 31, 2024',
            quarterlyBurnRate: '$380M',
            runwayMonths: 28,
            revenue: '$1.8B',
            revenueSource: 'Product sales (COVID-19 vaccine)'
        },
        pipeline: [
            { drug: 'mRNA-1283', indication: 'COVID-19 (next-gen)', phase: 'Phase 3', status: 'Enrollment complete', catalyst: 'Data Q2 2025' },
            { drug: 'mRNA-1345', indication: 'RSV Vaccine', phase: 'Approved', status: 'FDA approved May 2024', catalyst: 'EU approval pending' },
            { drug: 'mRNA-4157', indication: 'Melanoma (adjuvant)', phase: 'Phase 3', status: 'Partnered with Merck', catalyst: 'Pivotal data H2 2025' },
            { drug: 'mRNA-1893', indication: 'Zika Vaccine', phase: 'Phase 2', status: 'Dose optimization', catalyst: 'Phase 3 initiation 2025' },
            { drug: 'mRNA-3927', indication: 'Propionic Acidemia', phase: 'Phase 1/2', status: 'Rare disease orphan drug', catalyst: 'Interim data Q3 2025' }
        ],
        fdaInteractions: [
            'Breakthrough Therapy designation granted for mRNA-4157 in melanoma',
            'Fast Track designation for mRNA-3927 in propionic acidemia',
            'Pre-BLA meeting completed for next-gen COVID vaccine'
        ],
        partnerships: [
            { partner: 'Merck', type: 'Development', value: 'Up to $950M + royalties', details: 'Collaboration on personalized cancer vaccines using mRNA-4157' },
            { partner: 'Vertex', type: 'Research', value: '$75M upfront', details: 'Cystic fibrosis mRNA therapeutics development' },
            { partner: 'BARDA', type: 'Government', value: '$1.3B contract', details: 'Pandemic preparedness and vaccine stockpile' }
        ],
        risks: [
            'Revenue concentration: 85% from COVID-19 vaccine which faces declining demand',
            'Competition: Multiple mRNA competitors advancing similar programs',
            'Manufacturing capacity constraints may delay commercial scale-up',
            'Patent litigation ongoing with CureVac and Arbutus',
            'Regulatory uncertainty around annual vaccine reformulation requirements'
        ],
        recentEvents: [
            'Q4 2024 revenue beat estimates by 12%, driven by updated COVID booster',
            'Announced $3B share repurchase program in January 2025',
            'Expanded manufacturing facility in Melbourne, Australia',
            'Phase 2 flu/COVID combo vaccine showed positive immunogenicity data',
            'CEO highlighted plans for 10+ Phase 3 programs by 2026'
        ]
    };
}
function generateHtmlReport(ticker, companyName, filing, analysis) {
    const timestamp = new Date().toISOString();
    const filingYear = filing.reportDate ? new Date(filing.reportDate).getFullYear() : '';
    // Get runway indicator
    const runway = analysis.financials.runwayMonths;
    let runwayIndicator = '';
    let runwayClass = '';
    if (runway !== null) {
        if (runway >= 24) {
            runwayIndicator = '🟢';
            runwayClass = 'runway-good';
        }
        else if (runway >= 12) {
            runwayIndicator = '🟡';
            runwayClass = 'runway-moderate';
        }
        else {
            runwayIndicator = '🔴';
            runwayClass = 'runway-low';
        }
    }
    // Sort pipeline by phase
    const sortedPipeline = [...analysis.pipeline].sort((a, b) => {
        return getPhaseRank(b.phase) - getPhaseRank(a.phase);
    });
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${ticker} Analysis | Helix Intelligence</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-300: #d1d5db;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .container {
      max-width: 1100px;
      margin: 0 auto;
      padding: 2rem;
    }

    /* Header */
    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
      border-radius: 12px;
      margin-bottom: 2rem;
    }

    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .company-name {
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 0.25rem;
    }

    .ticker-badge {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      font-size: 1.25rem;
      font-weight: 600;
      margin-left: 1rem;
    }

    .filing-info {
      font-size: 0.95rem;
      opacity: 0.9;
      margin-top: 0.5rem;
    }

    .sec-link {
      color: white;
      text-decoration: underline;
      opacity: 0.9;
    }

    .sec-link:hover {
      opacity: 1;
    }

    .helix-logo {
      font-size: 1.5rem;
      font-weight: 700;
      opacity: 0.9;
    }

    /* Executive Summary */
    .summary-box {
      background: white;
      border: 1px solid var(--gray-200);
      border-left: 4px solid var(--primary);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }

    .summary-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--primary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;
    }

    .summary-text {
      font-size: 1.1rem;
      color: var(--gray-700);
      line-height: 1.7;
    }

    .key-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--gray-200);
    }

    .stat-item {
      text-align: center;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--gray-900);
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--gray-500);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Cards */
    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .card-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card-icon {
      font-size: 1.25rem;
    }

    /* Pipeline Table */
    .pipeline-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }

    .pipeline-table th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      border-bottom: 2px solid var(--gray-200);
      font-weight: 600;
      color: var(--gray-700);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .pipeline-table td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    .pipeline-table tr:hover {
      background: var(--gray-50);
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-preclinical { background: var(--gray-100); color: var(--gray-500); }

    .drug-name {
      font-weight: 600;
      color: var(--gray-900);
    }

    .catalyst-tag {
      display: inline-block;
      background: #fef3c7;
      color: #92400e;
      padding: 0.125rem 0.375rem;
      border-radius: 4px;
      font-size: 0.75rem;
      margin-top: 0.25rem;
    }

    /* Financials */
    .financials-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
    }

    .financial-item {
      padding: 1rem;
      background: var(--gray-50);
      border-radius: 8px;
    }

    .financial-label {
      font-size: 0.75rem;
      color: var(--gray-500);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.25rem;
    }

    .financial-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--gray-900);
    }

    .financial-detail {
      font-size: 0.875rem;
      color: var(--gray-500);
      margin-top: 0.25rem;
    }

    .runway-good .financial-value { color: var(--success); }
    .runway-moderate .financial-value { color: var(--warning); }
    .runway-low .financial-value { color: var(--danger); }

    /* FDA & Partnerships */
    .fda-list, .risk-list {
      list-style: none;
    }

    .fda-list li, .risk-list li {
      padding: 0.75rem 0;
      border-bottom: 1px solid var(--gray-100);
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
    }

    .fda-list li:last-child, .risk-list li:last-child {
      border-bottom: none;
    }

    .fda-icon {
      color: var(--primary);
      font-size: 1.25rem;
    }

    .risk-icon {
      color: var(--warning);
    }

    .partnership-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }

    .partnership-card {
      background: var(--gray-50);
      border-radius: 8px;
      padding: 1rem;
    }

    .partner-name {
      font-weight: 600;
      color: var(--gray-900);
      font-size: 1.1rem;
    }

    .partner-type {
      display: inline-block;
      background: var(--gray-200);
      color: var(--gray-700);
      padding: 0.125rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      margin-left: 0.5rem;
    }

    .partner-value {
      color: var(--success);
      font-weight: 600;
      font-size: 1.1rem;
      margin: 0.5rem 0;
    }

    .partner-details {
      font-size: 0.875rem;
      color: var(--gray-500);
    }

    /* Events */
    .events-list {
      list-style: none;
    }

    .events-list li {
      padding: 0.5rem 0;
      padding-left: 1.5rem;
      position: relative;
      border-left: 2px solid var(--gray-200);
      margin-left: 0.5rem;
    }

    .events-list li::before {
      content: '';
      position: absolute;
      left: -5px;
      top: 0.75rem;
      width: 8px;
      height: 8px;
      background: var(--secondary);
      border-radius: 50%;
    }

    /* Collapsible */
    .collapsible-header {
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .collapsible-header::after {
      content: '▼';
      font-size: 0.75rem;
      transition: transform 0.2s;
    }

    .collapsible.collapsed .collapsible-header::after {
      transform: rotate(-90deg);
    }

    .collapsible.collapsed .collapsible-content {
      display: none;
    }

    /* Footer */
    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    .footer-brand {
      font-weight: 600;
      color: var(--primary);
    }

    .disclaimer {
      margin-top: 1rem;
      font-size: 0.75rem;
      color: var(--gray-400);
    }

    /* Responsive */
    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }

      .company-name {
        font-size: 1.75rem;
      }

      .ticker-badge {
        display: block;
        margin-left: 0;
        margin-top: 0.5rem;
      }

      .header-top {
        flex-direction: column;
      }

      .pipeline-table {
        font-size: 0.8rem;
      }

      .pipeline-table th:nth-child(4),
      .pipeline-table td:nth-child(4) {
        display: none;
      }
    }

    /* Print */
    @media print {
      body {
        background: white;
      }

      .container {
        max-width: none;
        padding: 0;
      }

      .header {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }

      .collapsible.collapsed .collapsible-content {
        display: block;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="header-top">
        <div>
          <h1 class="company-name">
            ${escapeHtml(companyName)}
            <span class="ticker-badge">${ticker}</span>
          </h1>
          <div class="filing-info">
            ${filing.form} | Filed ${formatDate(filing.filingDate)} | FY ${filingYear}
            <br>
            <a href="${filing.fileUrl}" target="_blank" class="sec-link">View SEC Filing →</a>
          </div>
        </div>
        <div class="helix-logo">⬡ Helix</div>
      </div>
    </header>

    <!-- Executive Summary -->
    <div class="summary-box">
      <div class="summary-title">Executive Summary</div>
      <p class="summary-text">${escapeHtml(analysis.analystSummary)}</p>

      <div class="key-stats">
        <div class="stat-item">
          <div class="stat-value">${analysis.company.marketCap || '—'}</div>
          <div class="stat-label">Market Cap</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${analysis.financials.revenue || '—'}</div>
          <div class="stat-label">Revenue</div>
        </div>
        <div class="stat-item ${runwayClass}">
          <div class="stat-value">${runwayIndicator} ${runway ? runway + ' mo' : '—'}</div>
          <div class="stat-label">Cash Runway</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${analysis.pipeline.length}</div>
          <div class="stat-label">Pipeline Assets</div>
        </div>
      </div>
    </div>

    <!-- Two Column Layout -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;">
      <div>
        <!-- Pipeline Table -->
        <div class="card">
          <h2 class="card-title"><span class="card-icon">🧬</span> Pipeline</h2>
          <table class="pipeline-table">
            <thead>
              <tr>
                <th>Drug</th>
                <th>Phase</th>
                <th>Indication</th>
                <th>Status</th>
                <th>Catalyst</th>
              </tr>
            </thead>
            <tbody>
              ${sortedPipeline.map(drug => `
                <tr>
                  <td class="drug-name">${escapeHtml(drug.drug)}</td>
                  <td><span class="phase-badge ${getPhaseClass(drug.phase)}">${escapeHtml(drug.phase)}</span></td>
                  <td>${escapeHtml(drug.indication)}</td>
                  <td>${drug.status ? escapeHtml(drug.status) : '—'}</td>
                  <td>${drug.catalyst ? `<span class="catalyst-tag">📅 ${escapeHtml(drug.catalyst)}</span>` : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <!-- Partnerships -->
        ${analysis.partnerships.length > 0 ? `
        <div class="card">
          <h2 class="card-title"><span class="card-icon">🤝</span> Partnerships</h2>
          <div class="partnership-cards">
            ${analysis.partnerships.map(p => `
              <div class="partnership-card">
                <div>
                  <span class="partner-name">${escapeHtml(p.partner)}</span>
                  <span class="partner-type">${escapeHtml(p.type)}</span>
                </div>
                ${p.value ? `<div class="partner-value">${escapeHtml(p.value)}</div>` : ''}
                <div class="partner-details">${escapeHtml(p.details)}</div>
              </div>
            `).join('')}
          </div>
        </div>
        ` : ''}

        <!-- Recent Events -->
        ${analysis.recentEvents.length > 0 ? `
        <div class="card">
          <h2 class="card-title"><span class="card-icon">📰</span> Recent Events</h2>
          <ul class="events-list">
            ${analysis.recentEvents.map(event => `
              <li>${escapeHtml(event)}</li>
            `).join('')}
          </ul>
        </div>
        ` : ''}
      </div>

      <div>
        <!-- Financials -->
        <div class="card">
          <h2 class="card-title"><span class="card-icon">💰</span> Financials</h2>
          <div class="financials-grid" style="grid-template-columns: 1fr;">
            <div class="financial-item ${runwayClass}">
              <div class="financial-label">Cash Position</div>
              <div class="financial-value">${analysis.financials.cash || '—'}</div>
              ${analysis.financials.cashDate ? `<div class="financial-detail">as of ${escapeHtml(analysis.financials.cashDate)}</div>` : ''}
            </div>

            <div class="financial-item ${runwayClass}">
              <div class="financial-label">Cash Runway</div>
              <div class="financial-value">${runwayIndicator} ${runway ? runway + ' months' : '—'}</div>
            </div>

            ${analysis.financials.quarterlyBurnRate ? `
            <div class="financial-item">
              <div class="financial-label">Quarterly Burn</div>
              <div class="financial-value">${escapeHtml(analysis.financials.quarterlyBurnRate)}</div>
            </div>
            ` : ''}

            ${analysis.financials.revenue ? `
            <div class="financial-item">
              <div class="financial-label">Revenue</div>
              <div class="financial-value">${escapeHtml(analysis.financials.revenue)}</div>
              ${analysis.financials.revenueSource ? `<div class="financial-detail">${escapeHtml(analysis.financials.revenueSource)}</div>` : ''}
            </div>
            ` : ''}
          </div>
        </div>

        <!-- FDA Interactions -->
        ${analysis.fdaInteractions.length > 0 ? `
        <div class="card">
          <h2 class="card-title"><span class="card-icon">🏛️</span> FDA Interactions</h2>
          <ul class="fda-list">
            ${analysis.fdaInteractions.map(item => `
              <li>
                <span class="fda-icon">✓</span>
                <span>${escapeHtml(item)}</span>
              </li>
            `).join('')}
          </ul>
        </div>
        ` : ''}

        <!-- Risks -->
        ${analysis.risks.length > 0 ? `
        <div class="card collapsible">
          <h2 class="card-title collapsible-header">
            <span><span class="card-icon">⚠️</span> Key Risks</span>
          </h2>
          <div class="collapsible-content">
            <ul class="risk-list">
              ${analysis.risks.map(risk => `
                <li>
                  <span class="risk-icon">⚠</span>
                  <span>${escapeHtml(risk)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        </div>
        ` : ''}
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-brand">⬡ Powered by Helix Intelligence</div>
      <div>Generated ${new Date().toLocaleString()}</div>
      <div class="disclaimer">
        Data extracted from SEC filings using AI. Verify all information before making investment decisions.
        This is not financial advice.
      </div>
    </footer>
  </div>

  <script>
    // Toggle collapsible sections
    document.querySelectorAll('.collapsible-header').forEach(header => {
      header.addEventListener('click', () => {
        header.closest('.collapsible').classList.toggle('collapsed');
      });
    });
  </script>
</body>
</html>`;
}
function escapeHtml(text) {
    if (!text)
        return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
function formatDate(dateStr) {
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    catch {
        return dateStr;
    }
}
function getPhaseClass(phase) {
    const p = phase.toLowerCase();
    if (p.includes('approved') || p.includes('marketed'))
        return 'phase-approved';
    if (p.includes('3') || p.includes('nda') || p.includes('bla'))
        return 'phase-3';
    if (p.includes('2'))
        return 'phase-2';
    if (p.includes('1'))
        return 'phase-1';
    return 'phase-preclinical';
}
// ============================================
// Cache Functions
// ============================================
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
function getCacheFilePath(ticker) {
    return path.join(CACHE_DIR, `${ticker.toUpperCase()}.json`);
}
// Cache validity period: 7 days
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
// ============================================
// Rate Limiting Functions
// ============================================
function isRateLimitExceeded() {
    const now = Date.now();
    // Remove timestamps older than the rate limit window
    while (apiCallTimestamps.length > 0 && apiCallTimestamps[0] < now - RATE_LIMIT_WINDOW_MS) {
        apiCallTimestamps.shift();
    }
    return apiCallTimestamps.length >= RATE_LIMIT_MAX_CALLS;
}
function recordApiCall() {
    apiCallTimestamps.push(Date.now());
}
function getRateLimitStatus() {
    const now = Date.now();
    // Clean up old timestamps
    while (apiCallTimestamps.length > 0 && apiCallTimestamps[0] < now - RATE_LIMIT_WINDOW_MS) {
        apiCallTimestamps.shift();
    }
    const remaining = Math.max(0, RATE_LIMIT_MAX_CALLS - apiCallTimestamps.length);
    const oldestCall = apiCallTimestamps[0];
    const resetInMinutes = oldestCall
        ? Math.ceil((oldestCall + RATE_LIMIT_WINDOW_MS - now) / (60 * 1000))
        : 0;
    return { remaining, resetInMinutes };
}
// Get cached analysis ignoring expiry (for rate limit scenarios)
function getCachedAnalysisIgnoreExpiry(ticker) {
    const filePath = getCacheFilePath(ticker);
    if (!fs.existsSync(filePath))
        return null;
    try {
        const data = fs.readFileSync(filePath, 'utf-8');
        return JSON.parse(data);
    }
    catch {
        return null;
    }
}
function getCachedAnalysis(ticker) {
    const filePath = getCacheFilePath(ticker);
    if (!fs.existsSync(filePath))
        return null;
    try {
        const data = fs.readFileSync(filePath, 'utf-8');
        const cached = JSON.parse(data);
        // Check if cache is still valid (less than 7 days old)
        if (cached.analyzedAt) {
            const cacheAge = Date.now() - new Date(cached.analyzedAt).getTime();
            if (cacheAge > CACHE_MAX_AGE_MS) {
                console.log(chalk_1.default.yellow(`  [Cache] ${ticker} cache expired (${Math.floor(cacheAge / (24 * 60 * 60 * 1000))} days old)`));
                return null;
            }
        }
        return cached;
    }
    catch {
        return null;
    }
}
function saveCachedAnalysis(ticker, filingDate, analysis) {
    const filePath = getCacheFilePath(ticker);
    const cached = {
        ticker: ticker.toUpperCase(),
        filingDate,
        analyzedAt: new Date().toISOString(),
        analysis
    };
    fs.writeFileSync(filePath, JSON.stringify(cached, null, 2));
}
function getAllCachedAnalyses() {
    if (!fs.existsSync(CACHE_DIR))
        return [];
    const files = fs.readdirSync(CACHE_DIR).filter(f => f.endsWith('.json'));
    const analyses = [];
    for (const file of files) {
        try {
            const data = fs.readFileSync(path.join(CACHE_DIR, file), 'utf-8');
            analyses.push(JSON.parse(data));
        }
        catch {
            // Skip invalid files
        }
    }
    return analyses;
}
function getMostAdvancedPhase(pipeline) {
    if (pipeline.length === 0)
        return 'N/A';
    let maxRank = 0;
    let maxPhase = 'Preclinical';
    for (const item of pipeline) {
        const rank = getPhaseRank(item.phase);
        if (rank > maxRank) {
            maxRank = rank;
            maxPhase = item.phase;
        }
    }
    return maxPhase;
}
function getKeyCatalyst(pipeline) {
    // Find the first catalyst from the most advanced drugs
    const sorted = [...pipeline].sort((a, b) => getPhaseRank(b.phase) - getPhaseRank(a.phase));
    for (const item of sorted) {
        if (item.catalyst)
            return item.catalyst;
    }
    return null;
}
function generateDashboardHtml(data) {
    const timestamp = new Date().toLocaleString();
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Helix Dashboard | Biotech Portfolio Analysis</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.5;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 1.5rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 700;
    }

    .header-stats {
      display: flex;
      gap: 2rem;
    }

    .header-stat {
      text-align: center;
    }

    .header-stat-value {
      font-size: 1.5rem;
      font-weight: 700;
    }

    .header-stat-label {
      font-size: 0.75rem;
      opacity: 0.8;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .controls {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }

    .search-box {
      flex: 1;
      min-width: 200px;
      padding: 0.75rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 1rem;
    }

    .filter-btn {
      padding: 0.75rem 1rem;
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.875rem;
    }

    .filter-btn:hover {
      background: var(--gray-50);
    }

    .filter-btn.active {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }

    .table-container {
      background: white;
      border-radius: 12px;
      border: 1px solid var(--gray-200);
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th {
      text-align: left;
      padding: 1rem;
      background: var(--gray-50);
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--gray-500);
      border-bottom: 1px solid var(--gray-200);
      cursor: pointer;
      user-select: none;
    }

    th:hover {
      background: var(--gray-100);
    }

    th .sort-arrow {
      margin-left: 0.5rem;
      opacity: 0.5;
    }

    td {
      padding: 1rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: middle;
    }

    tr:hover {
      background: var(--gray-50);
    }

    tr.clickable {
      cursor: pointer;
    }

    .ticker-cell {
      font-weight: 700;
      color: var(--primary);
    }

    .company-name {
      color: var(--gray-700);
      font-size: 0.875rem;
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }

    .runway-good { color: var(--success); font-weight: 600; }
    .runway-moderate { color: var(--warning); font-weight: 600; }
    .runway-low { color: var(--danger); font-weight: 600; }

    .catalyst-tag {
      background: #fef3c7;
      color: #92400e;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
    }

    .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: var(--gray-500);
    }

    .empty-state h2 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
      color: var(--gray-700);
    }

    .batch-btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
    }

    .batch-btn:hover {
      background: var(--primary-dark);
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .header { flex-direction: column; gap: 1rem; }
      .header-stats { justify-content: center; }
      th, td { padding: 0.75rem 0.5rem; font-size: 0.8rem; }
      .controls { flex-direction: column; }
    }
  </style>
</head>
<body>
  <header class="header">
    <h1>⬡ Helix Dashboard</h1>
    <div class="header-stats">
      <div class="header-stat">
        <div class="header-stat-value">${data.length}</div>
        <div class="header-stat-label">Companies Analyzed</div>
      </div>
      <div class="header-stat">
        <div class="header-stat-value">${data.filter(d => d.phase.toLowerCase().includes('approved')).length}</div>
        <div class="header-stat-label">With Approved Drugs</div>
      </div>
      <div class="header-stat">
        <div class="header-stat-value">${data.filter(d => d.phase.toLowerCase().includes('3')).length}</div>
        <div class="header-stat-label">Phase 3</div>
      </div>
    </div>
  </header>

  <div class="container">
    ${data.length === 0 ? `
      <div class="empty-state">
        <h2>No analyses yet</h2>
        <p>Run a batch analysis to populate the dashboard</p>
        <br>
        <code>POST /api/analyze/batch</code> with <code>{"tickers": ["MRNA", "REGN", "VRTX"]}</code>
      </div>
    ` : `
      <div class="controls">
        <input type="text" class="search-box" placeholder="Search by ticker or company..." id="searchInput">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="approved">Approved</button>
        <button class="filter-btn" data-filter="phase-3">Phase 3</button>
        <button class="filter-btn" data-filter="phase-2">Phase 2</button>
        <button class="filter-btn" data-filter="low-runway">Low Runway (&lt;12mo)</button>
      </div>

      <div class="table-container">
        <table id="dashboardTable">
          <thead>
            <tr>
              <th data-sort="ticker">Ticker <span class="sort-arrow">↕</span></th>
              <th data-sort="name">Company <span class="sort-arrow">↕</span></th>
              <th data-sort="phase">Phase <span class="sort-arrow">↕</span></th>
              <th data-sort="runway">Runway <span class="sort-arrow">↕</span></th>
              <th data-sort="cash">Cash <span class="sort-arrow">↕</span></th>
              <th>Key Catalyst</th>
              <th>Pipeline</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(row => {
        const runwayClass = row.runway === null ? '' :
            row.runway >= 24 ? 'runway-good' :
                row.runway >= 12 ? 'runway-moderate' : 'runway-low';
        const runwayIcon = row.runway === null ? '' :
            row.runway >= 24 ? '🟢' :
                row.runway >= 12 ? '🟡' : '🔴';
        return `
                <tr class="clickable" onclick="window.location='/api/report/${row.ticker}'" data-phase="${row.phase.toLowerCase()}" data-runway="${row.runway || 0}">
                  <td class="ticker-cell">${row.ticker}</td>
                  <td>
                    <div>${escapeHtml(row.name)}</div>
                    ${row.marketCap ? `<div class="company-name">${row.marketCap}</div>` : ''}
                  </td>
                  <td><span class="phase-badge ${getPhaseClass(row.phase)}">${escapeHtml(row.phase)}</span></td>
                  <td class="${runwayClass}">${runwayIcon} ${row.runway ? row.runway + ' mo' : '—'}</td>
                  <td>${row.cash || '—'}</td>
                  <td>${row.catalyst ? `<span class="catalyst-tag">📅 ${escapeHtml(row.catalyst)}</span>` : '—'}</td>
                  <td>${row.pipelineCount} assets</td>
                </tr>
              `;
    }).join('')}
          </tbody>
        </table>
      </div>
    `}

    <footer class="footer">
      <div>⬡ Powered by Helix Intelligence</div>
      <div>Last updated: ${timestamp}</div>
    </footer>
  </div>

  <script>
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        document.querySelectorAll('#dashboardTable tbody tr').forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      });
    }

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        const filter = this.dataset.filter;
        document.querySelectorAll('#dashboardTable tbody tr').forEach(row => {
          const phase = row.dataset.phase || '';
          const runway = parseInt(row.dataset.runway) || 0;

          let show = true;
          if (filter === 'approved') show = phase.includes('approved');
          else if (filter === 'phase-3') show = phase.includes('3');
          else if (filter === 'phase-2') show = phase.includes('2');
          else if (filter === 'low-runway') show = runway > 0 && runway < 12;

          row.style.display = show ? '' : 'none';
        });
      });
    });

    // Sort functionality
    document.querySelectorAll('th[data-sort]').forEach(th => {
      th.addEventListener('click', function() {
        const table = document.getElementById('dashboardTable');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const col = this.dataset.sort;
        const colIndex = Array.from(this.parentNode.children).indexOf(this);

        const direction = this.classList.contains('sort-asc') ? -1 : 1;
        this.parentNode.querySelectorAll('th').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
        this.classList.add(direction === 1 ? 'sort-asc' : 'sort-desc');

        rows.sort((a, b) => {
          let aVal = a.children[colIndex].textContent.trim();
          let bVal = b.children[colIndex].textContent.trim();

          // Handle numeric columns
          if (col === 'runway') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
            return (aVal - bVal) * direction;
          }

          return aVal.localeCompare(bVal) * direction;
        });

        rows.forEach(row => tbody.appendChild(row));
      });
    });
  </script>
</body>
</html>`;
}
// ============================================
// Landscape Dashboard HTML Generator
// ============================================
function generateLandscapeHtml(data) {
    const timestamp = new Date(data.fetchedAt).toLocaleString();
    // Prepare chart data
    const phaseLabels = Object.keys(data.clinicalTrials.phaseBreakdown);
    const phaseValues = Object.values(data.clinicalTrials.phaseBreakdown);
    const sponsorLabels = data.clinicalTrials.topSponsors.map(s => s.name.substring(0, 30));
    const sponsorValues = data.clinicalTrials.topSponsors.map(s => s.count);
    const yearLabels = data.research.byYear.map(y => y.year.toString());
    const yearValues = data.research.byYear.map(y => y.count);
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(data.condition)} Landscape | Helix Intelligence</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-300: #d1d5db;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header-content {
      max-width: 1400px;
      margin: 0 auto;
    }

    .header h1 {
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .header-subtitle {
      opacity: 0.9;
      font-size: 1rem;
    }

    .summary-stats {
      display: flex;
      gap: 2rem;
      margin-top: 1.5rem;
      flex-wrap: wrap;
    }

    .stat-box {
      background: rgba(255,255,255,0.15);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      text-align: center;
      min-width: 140px;
    }

    .stat-value {
      font-size: 2rem;
      font-weight: 700;
    }

    .stat-label {
      font-size: 0.75rem;
      opacity: 0.9;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .section {
      margin-bottom: 2rem;
    }

    .section-title {
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1rem;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 1.5rem;
    }

    .chart-container {
      position: relative;
      height: 300px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--gray-200);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    tr:hover {
      background: var(--gray-50);
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-4 { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-na { background: var(--gray-100); color: var(--gray-500); }

    .status-recruiting { color: var(--success); font-weight: 500; }
    .status-completed { color: var(--gray-500); }
    .status-active { color: var(--secondary); font-weight: 500; }
    .status-terminated { color: var(--danger); }

    .deal-type {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      background: var(--gray-100);
      color: var(--gray-700);
    }

    .deal-value {
      color: var(--success);
      font-weight: 600;
    }

    .link {
      color: var(--primary);
      text-decoration: none;
    }

    .link:hover {
      text-decoration: underline;
    }

    .kol-rank {
      color: var(--primary);
      font-weight: 700;
    }

    .export-btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
    }

    .export-btn:hover {
      background: var(--primary-dark);
    }

    .search-box {
      width: 100%;
      max-width: 400px;
      padding: 0.75rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    .no-data {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
    }

    @media (max-width: 768px) {
      .grid-2 { grid-template-columns: 1fr; }
      .summary-stats { flex-direction: column; gap: 1rem; }
      .stat-box { min-width: auto; }
      .header h1 { font-size: 1.75rem; }
      th, td { padding: 0.5rem; font-size: 0.75rem; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <h1>⬡ ${escapeHtml(data.condition)}</h1>
      <div class="header-subtitle">Therapeutic Landscape Analysis | Updated ${timestamp}</div>

      <div class="summary-stats">
        <div class="stat-box">
          <div class="stat-value">${data.summary.totalTrials}</div>
          <div class="stat-label">Clinical Trials</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.uniqueMolecules || 0}</div>
          <div class="stat-label">Molecules</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.activeCompanies}</div>
          <div class="stat-label">Active Companies</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.recentDeals}</div>
          <div class="stat-label">Recent Deals</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.totalPublications.toLocaleString()}</div>
          <div class="stat-label">Publications</div>
        </div>
      </div>
    </div>
  </header>

  <div class="container">
    <!-- Section 1: Clinical Landscape -->
    <section class="section">
      <h2 class="section-title">🧬 Clinical Landscape</h2>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">Phase Distribution</div>
          <div class="chart-container">
            <canvas id="phaseChart"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Top 10 Sponsors</div>
          <div class="chart-container">
            <canvas id="sponsorChart"></canvas>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Clinical Trials (${data.clinicalTrials.trials.length})</div>
        <input type="text" class="search-box" placeholder="Search trials..." id="trialSearch">
        <div style="max-height: 500px; overflow-y: auto;">
          <table id="trialsTable">
            <thead>
              <tr>
                <th>NCT ID</th>
                <th>Title</th>
                <th>Phase</th>
                <th>Status</th>
                <th>Sponsor</th>
                <th>Enrollment</th>
              </tr>
            </thead>
            <tbody>
              ${data.clinicalTrials.trials.length === 0 ? `
                <tr><td colspan="6" class="no-data">No trials found</td></tr>
              ` : data.clinicalTrials.trials.map(trial => `
                <tr>
                  <td><a href="https://clinicaltrials.gov/study/${trial.nctId}" target="_blank" class="link">${trial.nctId}</a></td>
                  <td>${escapeHtml(trial.title.substring(0, 100))}${trial.title.length > 100 ? '...' : ''}</td>
                  <td><span class="phase-badge ${getTrialPhaseClass(trial.phase)}">${escapeHtml(trial.phase)}</span></td>
                  <td class="${getTrialStatusClass(trial.status)}">${escapeHtml(trial.status)}</td>
                  <td>${escapeHtml(trial.sponsor.substring(0, 40))}${trial.sponsor.length > 40 ? '...' : ''}</td>
                  <td>${trial.enrollment ? trial.enrollment.toLocaleString() : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Section 2: Molecule Landscape -->
    <section class="section">
      <h2 class="section-title">💊 Molecule Landscape</h2>

      <div class="card">
        <div class="card-title">Drugs & Molecules in Development (${data.molecules?.length || 0})</div>
        ${!data.molecules || data.molecules.length === 0 ? `
          <div class="no-data">No molecules extracted from trials</div>
        ` : `
          <input type="text" class="search-box" placeholder="Search molecules..." id="moleculeSearch">
          <div style="max-height: 400px; overflow-y: auto;">
            <table id="moleculesTable">
              <thead>
                <tr>
                  <th>Molecule</th>
                  <th>Mechanism</th>
                  <th>Sponsor</th>
                  <th>Highest Phase</th>
                  <th>Trials</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${data.molecules.map(mol => `
                  <tr>
                    <td><strong>${escapeHtml(mol.name)}</strong></td>
                    <td>${mol.mechanism ? `<span class="deal-type">${escapeHtml(mol.mechanism)}</span>` : '—'}</td>
                    <td>${escapeHtml(mol.sponsor.substring(0, 35))}${mol.sponsor.length > 35 ? '...' : ''}</td>
                    <td><span class="phase-badge ${getTrialPhaseClass(mol.highestPhase)}">${escapeHtml(mol.highestPhase)}</span></td>
                    <td>${mol.trialCount}</td>
                    <td class="${getTrialStatusClass(mol.status)}">${escapeHtml(mol.status)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    </section>

    <!-- Section 3: Deal Tracker -->
    <section class="section">
      <h2 class="section-title">💰 Deal Tracker</h2>

      <div class="card">
        <div class="card-title">Recent Deals & News (${data.dealsNews.length})</div>
        ${data.dealsNews.length === 0 ? `
          <div class="no-data">No deals or news found matching "${escapeHtml(data.condition)}"</div>
        ` : `
          <div style="max-height: 400px; overflow-y: auto;">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Title</th>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                ${data.dealsNews.map(deal => {
        const date = new Date(deal.pubDate);
        const dateStr = isNaN(date.getTime()) ? '—' : date.toLocaleDateString();
        return `
                    <tr>
                      <td>${dateStr}</td>
                      <td><a href="${escapeHtml(deal.link)}" target="_blank" class="link">${escapeHtml(deal.title.substring(0, 80))}${deal.title.length > 80 ? '...' : ''}</a></td>
                      <td>${escapeHtml(deal.source)}</td>
                      <td>${deal.dealType ? `<span class="deal-type">${escapeHtml(deal.dealType)}</span>` : '—'}</td>
                      <td class="deal-value">${deal.dealValue || '—'}</td>
                    </tr>
                  `;
    }).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    </section>

    <!-- Section 4: Research Intelligence -->
    <section class="section">
      <h2 class="section-title">📚 Research Intelligence</h2>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">Publications by Year</div>
          <div class="chart-container">
            <canvas id="pubChart"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Top Key Opinion Leaders (Active Researchers)</div>
          ${data.research.topKOLs.length === 0 ? `
            <div class="no-data">No KOL data available</div>
          ` : `
            <div style="max-height: 350px; overflow-y: auto;">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Author</th>
                    <th>Institution</th>
                    <th>Pubs</th>
                    <th>Contact</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.research.topKOLs.map((kol, i) => `
                    <tr>
                      <td class="kol-rank">${i + 1}</td>
                      <td><strong>${escapeHtml(kol.name)}</strong></td>
                      <td>${kol.institution ? escapeHtml(kol.institution.substring(0, 30)) + (kol.institution.length > 30 ? '...' : '') : '—'}</td>
                      <td>${kol.publicationCount}</td>
                      <td>${kol.email ? `<a href="mailto:${escapeHtml(kol.email)}" class="link">${escapeHtml(kol.email.substring(0, 25))}${kol.email.length > 25 ? '...' : ''}</a>` : '—'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>
    </section>

    <!-- Section 5: Export -->
    <section class="section">
      <h2 class="section-title">📥 Export Data</h2>
      <div class="card">
        <p style="margin-bottom: 1rem; color: var(--gray-500);">Download the complete landscape data including all trials, deals, and KOL information.</p>
        <a href="/api/landscape/${encodeURIComponent(data.condition)}/csv" class="export-btn">Download CSV</a>
        <a href="/api/landscape/${encodeURIComponent(data.condition)}/json" class="export-btn" style="margin-left: 1rem; background: var(--gray-700);">Download JSON</a>
      </div>
    </section>

    <footer class="footer">
      <div>⬡ Powered by Helix Intelligence</div>
      <div>Data sources: ClinicalTrials.gov, PubMed, Fierce Biotech, Fierce Pharma, PR Newswire, Endpoints News, BioPharma Dive</div>
      <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--gray-400);">
        This is aggregated public data. Verify all information before making decisions.
      </div>
    </footer>
  </div>

  <script>
    // Phase Distribution Pie Chart
    new Chart(document.getElementById('phaseChart'), {
      type: 'doughnut',
      data: {
        labels: ${JSON.stringify(phaseLabels)},
        datasets: [{
          data: ${JSON.stringify(phaseValues)},
          backgroundColor: [
            '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#6b7280', '#06b6d4'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });

    // Top Sponsors Bar Chart
    new Chart(document.getElementById('sponsorChart'), {
      type: 'bar',
      data: {
        labels: ${JSON.stringify(sponsorLabels)},
        datasets: [{
          label: 'Trials',
          data: ${JSON.stringify(sponsorValues)},
          backgroundColor: '#6366f1'
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true }
        }
      }
    });

    // Publications by Year Line Chart
    new Chart(document.getElementById('pubChart'), {
      type: 'line',
      data: {
        labels: ${JSON.stringify(yearLabels)},
        datasets: [{
          label: 'Publications',
          data: ${JSON.stringify(yearValues)},
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true }
        }
      }
    });

    // Trial search functionality
    document.getElementById('trialSearch')?.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      document.querySelectorAll('#trialsTable tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });

    // Molecule search functionality
    document.getElementById('moleculeSearch')?.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      document.querySelectorAll('#moleculesTable tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  </script>
</body>
</html>`;
}
function getTrialPhaseClass(phase) {
    const p = phase.toLowerCase();
    if (p.includes('4'))
        return 'phase-4';
    if (p.includes('3'))
        return 'phase-3';
    if (p.includes('2'))
        return 'phase-2';
    if (p.includes('1'))
        return 'phase-1';
    return 'phase-na';
}
function getTrialStatusClass(status) {
    const s = status.toLowerCase();
    if (s.includes('recruiting'))
        return 'status-recruiting';
    if (s.includes('completed'))
        return 'status-completed';
    if (s.includes('active'))
        return 'status-active';
    if (s.includes('terminated') || s.includes('withdrawn'))
        return 'status-terminated';
    return '';
}
// ============================================
// Molecules Endpoint Helpers
// ============================================
function getMoleculePhaseRank(phase) {
    const p = phase.toLowerCase();
    if (p.includes('approved') || p.includes('marketed'))
        return 100;
    if (p.includes('4'))
        return 90;
    if (p.includes('3'))
        return 70;
    if (p.includes('2/3'))
        return 60;
    if (p.includes('2'))
        return 50;
    if (p.includes('1/2'))
        return 40;
    if (p.includes('1'))
        return 30;
    if (p.includes('early'))
        return 20;
    if (p.includes('preclinical') || p.includes('pre-clinical'))
        return 10;
    return 0;
}
function generateMoleculesHtml(condition, trialCount, molecules) {
    const timestamp = new Date().toLocaleString();
    // Count by phase
    const phaseBreakdown = {};
    for (const mol of molecules) {
        const phase = mol.highestPhase || 'Unknown';
        phaseBreakdown[phase] = (phaseBreakdown[phase] || 0) + 1;
    }
    // Count by mechanism
    const mechanismBreakdown = {};
    for (const mol of molecules) {
        const mech = mol.mechanism || 'Unknown';
        mechanismBreakdown[mech] = (mechanismBreakdown[mech] || 0) + 1;
    }
    const topMechanisms = Object.entries(mechanismBreakdown)
        .filter(([key]) => key !== 'Unknown')
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(condition)} Molecules | Helix Intelligence</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header-content {
      max-width: 1400px;
      margin: 0 auto;
    }

    .header h1 {
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .header-subtitle {
      opacity: 0.9;
      font-size: 1rem;
    }

    .summary-stats {
      display: flex;
      gap: 2rem;
      margin-top: 1.5rem;
      flex-wrap: wrap;
    }

    .stat-box {
      background: rgba(255,255,255,0.15);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      text-align: center;
      min-width: 120px;
    }

    .stat-value {
      font-size: 1.75rem;
      font-weight: 700;
    }

    .stat-label {
      font-size: 0.75rem;
      opacity: 0.9;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .card-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    .search-box {
      width: 100%;
      max-width: 400px;
      padding: 0.75rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 2px solid var(--gray-200);
      position: sticky;
      top: 0;
      cursor: pointer;
    }

    th:hover {
      background: var(--gray-100);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: middle;
    }

    tr:hover {
      background: var(--gray-50);
    }

    .molecule-name {
      font-weight: 600;
      color: var(--gray-900);
    }

    .molecule-aliases {
      font-size: 0.75rem;
      color: var(--gray-500);
      margin-top: 0.25rem;
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-4, .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-na { background: var(--gray-100); color: var(--gray-500); }

    .mechanism-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 500;
      background: #ede9fe;
      color: #5b21b6;
    }

    .type-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 500;
      background: #e0f2fe;
      color: #0369a1;
    }

    .link {
      color: var(--primary);
      text-decoration: none;
    }

    .link:hover {
      text-decoration: underline;
    }

    .trial-count {
      font-weight: 600;
      color: var(--gray-700);
    }

    .sponsor-name {
      color: var(--gray-600);
      font-size: 0.8rem;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .mechanism-list {
      list-style: none;
    }

    .mechanism-list li {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0;
      border-bottom: 1px solid var(--gray-100);
    }

    .mechanism-list li:last-child {
      border-bottom: none;
    }

    .mechanism-count {
      font-weight: 600;
      color: var(--primary);
    }

    .export-btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
      font-size: 0.875rem;
    }

    .export-btn:hover {
      background: var(--primary-dark);
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .summary-stats { flex-direction: column; gap: 1rem; }
      th, td { padding: 0.5rem; font-size: 0.75rem; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <h1>💊 ${escapeHtml(condition)} - Molecule Landscape</h1>
      <div class="header-subtitle">Drug candidates in clinical development | ${timestamp}</div>

      <div class="summary-stats">
        <div class="stat-box">
          <div class="stat-value">${molecules.length}</div>
          <div class="stat-label">Molecules</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${trialCount}</div>
          <div class="stat-label">Trials Analyzed</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${molecules.filter(m => m.highestPhase.includes('3')).length}</div>
          <div class="stat-label">Phase 3</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${molecules.filter(m => m.highestPhase.includes('2')).length}</div>
          <div class="stat-label">Phase 2</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${new Set(molecules.flatMap(m => m.sponsors)).size}</div>
          <div class="stat-label">Sponsors</div>
        </div>
      </div>
    </div>
  </header>

  <div class="container">
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Phase Distribution</div>
        <ul class="mechanism-list">
          ${Object.entries(phaseBreakdown)
        .sort((a, b) => getMoleculePhaseRank(b[0]) - getMoleculePhaseRank(a[0]))
        .map(([phase, count]) => `
              <li>
                <span><span class="phase-badge ${getTrialPhaseClass(phase)}">${escapeHtml(phase)}</span></span>
                <span class="mechanism-count">${count}</span>
              </li>
            `).join('')}
        </ul>
      </div>

      <div class="card">
        <div class="card-title">Top Mechanisms of Action</div>
        <ul class="mechanism-list">
          ${topMechanisms.map(([mech, count]) => `
            <li>
              <span class="mechanism-badge">${escapeHtml(mech)}</span>
              <span class="mechanism-count">${count}</span>
            </li>
          `).join('') || '<li>No mechanism data available</li>'}
        </ul>
      </div>
    </div>

    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem;">
        <div class="card-title" style="margin-bottom: 0;">Molecules in Development (${molecules.length})</div>
        <a href="/api/landscape/${encodeURIComponent(condition)}/molecules" class="export-btn">Download JSON</a>
      </div>
      <input type="text" class="search-box" placeholder="Search molecules, mechanisms, sponsors..." id="moleculeSearch">
      <div style="max-height: 600px; overflow-y: auto;">
        <table id="moleculesTable">
          <thead>
            <tr>
              <th>Molecule</th>
              <th>Type</th>
              <th>Mechanism</th>
              <th>Target</th>
              <th>Sponsor</th>
              <th>Phase</th>
              <th>Trials</th>
              <th>Lead Trial</th>
            </tr>
          </thead>
          <tbody>
            ${molecules.length === 0 ? `
              <tr><td colspan="8" style="text-align: center; color: var(--gray-500); padding: 2rem;">No molecules found</td></tr>
            ` : molecules.map(mol => `
              <tr>
                <td>
                  <div class="molecule-name">${escapeHtml(mol.name)}</div>
                  ${mol.aliases.length > 0 ? `<div class="molecule-aliases">${mol.aliases.slice(0, 2).map(a => escapeHtml(a)).join(', ')}${mol.aliases.length > 2 ? '...' : ''}</div>` : ''}
                </td>
                <td>${mol.type ? `<span class="type-badge">${escapeHtml(mol.type)}</span>` : '—'}</td>
                <td>${mol.mechanism ? `<span class="mechanism-badge">${escapeHtml(mol.mechanism)}</span>` : '—'}</td>
                <td>${mol.target ? escapeHtml(mol.target) : '—'}</td>
                <td><span class="sponsor-name">${escapeHtml((mol.sponsors[0] || 'Unknown').substring(0, 35))}${(mol.sponsors[0] || '').length > 35 ? '...' : ''}</span></td>
                <td><span class="phase-badge ${getTrialPhaseClass(mol.highestPhase)}">${escapeHtml(mol.highestPhase)}</span></td>
                <td class="trial-count">${mol.trialCount}</td>
                <td>${mol.leadTrialId ? `<a href="https://clinicaltrials.gov/study/${mol.leadTrialId}" target="_blank" class="link">${mol.leadTrialId}</a>` : '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <footer class="footer">
      <div>⬡ Powered by Helix Intelligence</div>
      <div>Data source: ClinicalTrials.gov</div>
    </footer>
  </div>

  <script>
    // Search functionality
    document.getElementById('moleculeSearch')?.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      document.querySelectorAll('#moleculesTable tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  </script>
</body>
</html>`;
}
// ============================================
// Trial Results HTML Generator
// ============================================
function generateTrialResultsHtml(data) {
    const timestamp = new Date().toLocaleString();
    // Build arms table data
    const armsHtml = data.arms.map(arm => `
    <tr>
      <td><strong>${escapeHtml(arm.title)}</strong></td>
      <td>${arm.type || '—'}</td>
      <td>${arm.intervention ? escapeHtml(arm.intervention) : '—'}</td>
      <td class="text-center">${arm.n !== undefined ? arm.n.toLocaleString() : '—'}</td>
    </tr>
  `).join('');
    // Build primary outcomes table
    const primaryOutcomesHtml = data.primaryOutcomes.length > 0
        ? data.primaryOutcomes.map(outcome => generateOutcomeSection(outcome, 'primary')).join('')
        : '<p class="no-data">No primary outcome results posted</p>';
    // Build secondary outcomes table
    const secondaryOutcomesHtml = data.secondaryOutcomes.length > 0
        ? data.secondaryOutcomes.map(outcome => generateOutcomeSection(outcome, 'secondary')).join('')
        : '<p class="no-data">No secondary outcome results posted</p>';
    // Build safety tables
    const safetyHtml = data.safety ? generateSafetySection(data.safety) : '<p class="no-data">No adverse events data posted</p>';
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(data.nctId)} Results | Helix Intelligence</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header-content {
      max-width: 1200px;
      margin: 0 auto;
    }

    .nct-badge {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      line-height: 1.3;
    }

    .header-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 1.5rem;
      margin-top: 1rem;
      font-size: 0.9rem;
      opacity: 0.9;
    }

    .header-meta-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .status-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .status-completed { background: #dcfce7; color: #166534; }
    .status-recruiting { background: #dbeafe; color: #1e40af; }
    .status-terminated { background: #fee2e2; color: #991b1b; }
    .status-other { background: var(--gray-200); color: var(--gray-700); }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
    }

    .section {
      margin-bottom: 2rem;
    }

    .section-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1rem;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 2px solid var(--gray-200);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    tr:hover {
      background: var(--gray-50);
    }

    .text-center {
      text-align: center;
    }

    .text-right {
      text-align: right;
    }

    .outcome-header {
      background: var(--gray-50);
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    }

    .outcome-title {
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 0.5rem;
    }

    .outcome-meta {
      font-size: 0.875rem;
      color: var(--gray-500);
    }

    .outcome-description {
      font-size: 0.875rem;
      color: var(--gray-600);
      margin-top: 0.5rem;
    }

    .result-value {
      font-weight: 600;
      color: var(--gray-900);
    }

    .result-ci {
      font-size: 0.8rem;
      color: var(--gray-500);
    }

    .p-value {
      font-weight: 600;
    }

    .p-significant {
      color: var(--success);
    }

    .p-not-significant {
      color: var(--gray-500);
    }

    .analysis-box {
      background: #f0fdf4;
      border: 1px solid #86efac;
      border-radius: 8px;
      padding: 1rem;
      margin-top: 1rem;
    }

    .analysis-box.not-significant {
      background: var(--gray-50);
      border-color: var(--gray-200);
    }

    .analysis-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--gray-500);
      text-transform: uppercase;
      margin-bottom: 0.5rem;
    }

    .analysis-value {
      font-size: 1.25rem;
      font-weight: 700;
    }

    .ae-rate {
      font-weight: 600;
    }

    .ae-rate-high {
      color: var(--danger);
    }

    .ae-rate-medium {
      color: var(--warning);
    }

    .ae-rate-low {
      color: var(--gray-700);
    }

    .search-box {
      width: 100%;
      max-width: 300px;
      padding: 0.5rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 6px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    .link {
      color: var(--primary);
      text-decoration: none;
    }

    .link:hover {
      text-decoration: underline;
    }

    .no-data {
      color: var(--gray-500);
      font-style: italic;
      padding: 1rem;
      text-align: center;
    }

    .no-results-banner {
      background: #fef3c7;
      border: 1px solid #f59e0b;
      border-radius: 8px;
      padding: 1rem;
      text-align: center;
      color: #92400e;
      margin-bottom: 2rem;
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .header h1 { font-size: 1.25rem; }
      .header-meta { flex-direction: column; gap: 0.5rem; }
      th, td { padding: 0.5rem; font-size: 0.8rem; }
    }

    @media print {
      .header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .search-box { display: none; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <div class="nct-badge">
        <a href="https://clinicaltrials.gov/study/${data.nctId}" target="_blank" style="color: white; text-decoration: none;">
          ${data.nctId} ↗
        </a>
      </div>
      <h1>${escapeHtml(data.title)}</h1>
      <div class="header-meta">
        <div class="header-meta-item">
          <span class="status-badge ${getStatusBadgeClass(data.status)}">${escapeHtml(data.status)}</span>
        </div>
        <div class="header-meta-item">
          <strong>Phase:</strong> ${escapeHtml(data.phase)}
        </div>
        <div class="header-meta-item">
          <strong>Sponsor:</strong> ${escapeHtml(data.sponsor)}
        </div>
        <div class="header-meta-item">
          <strong>Enrollment:</strong> ${data.enrollment.toLocaleString()}
        </div>
        ${data.completionDate ? `<div class="header-meta-item"><strong>Completed:</strong> ${data.completionDate}</div>` : ''}
      </div>
    </div>
  </header>

  <div class="container">
    ${!data.hasResults ? `
      <div class="no-results-banner">
        <strong>No Results Posted Yet</strong><br>
        This trial has not posted results to ClinicalTrials.gov.
        ${data.status === 'COMPLETED' ? 'Results may be posted within 12 months of completion.' : ''}
      </div>
    ` : ''}

    <!-- Study Arms -->
    <section class="section">
      <h2 class="section-title">📊 Study Population & Arms</h2>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Arm</th>
              <th>Type</th>
              <th>Intervention</th>
              <th class="text-center">N</th>
            </tr>
          </thead>
          <tbody>
            ${armsHtml || '<tr><td colspan="4" class="no-data">No arm information available</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

    ${data.hasResults ? `
    <!-- Primary Outcomes -->
    <section class="section">
      <h2 class="section-title">🎯 Primary Outcomes</h2>
      ${primaryOutcomesHtml}
    </section>

    <!-- Secondary Outcomes -->
    <section class="section">
      <h2 class="section-title">📈 Secondary Outcomes</h2>
      ${secondaryOutcomesHtml}
    </section>

    <!-- Safety -->
    <section class="section">
      <h2 class="section-title">⚠️ Adverse Events</h2>
      ${safetyHtml}
    </section>
    ` : ''}

    <footer class="footer">
      <div>⬡ Powered by Helix Intelligence</div>
      <div>Data source: <a href="https://clinicaltrials.gov/study/${data.nctId}" class="link">ClinicalTrials.gov</a></div>
      <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--gray-400);">
        Fetched ${timestamp}. Verify all data before making clinical or investment decisions.
      </div>
    </footer>
  </div>

  <script>
    // Search functionality for AE tables
    document.querySelectorAll('.ae-search').forEach(input => {
      input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        const tableId = this.dataset.table;
        document.querySelectorAll('#' + tableId + ' tbody tr').forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      });
    });
  </script>
</body>
</html>`;
}
function generateOutcomeSection(outcome, type) {
    const resultsRows = outcome.results.map(r => `
    <tr>
      <td>${escapeHtml(r.armTitle)}</td>
      <td class="result-value">${escapeHtml(r.value)}${outcome.units ? ' ' + escapeHtml(outcome.units) : ''}</td>
      <td class="result-ci">${r.ci ? `[${r.ci.lower}, ${r.ci.upper}]` : r.spread ? `(${r.spread})` : '—'}</td>
      <td class="text-center">${r.n !== undefined ? r.n.toLocaleString() : '—'}</td>
    </tr>
  `).join('');
    const analysisHtml = outcome.analysis ? `
    <div class="analysis-box ${outcome.analysis.pValueSignificant ? '' : 'not-significant'}">
      <div class="analysis-label">Statistical Analysis</div>
      <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
        ${outcome.analysis.pValue ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">P-value</div>
            <div class="p-value ${outcome.analysis.pValueSignificant ? 'p-significant' : 'p-not-significant'}">
              ${escapeHtml(outcome.analysis.pValue)}
              ${outcome.analysis.pValueSignificant ? ' ✓' : ''}
            </div>
          </div>
        ` : ''}
        ${outcome.analysis.estimateValue ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">${outcome.analysis.estimateType || 'Estimate'}</div>
            <div style="font-weight: 600;">${escapeHtml(outcome.analysis.estimateValue)}</div>
          </div>
        ` : ''}
        ${outcome.analysis.ci ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">${outcome.analysis.ci.pct}% CI</div>
            <div>[${outcome.analysis.ci.lower}, ${outcome.analysis.ci.upper}]</div>
          </div>
        ` : ''}
        ${outcome.analysis.method ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">Method</div>
            <div style="font-size: 0.875rem;">${escapeHtml(outcome.analysis.method)}</div>
          </div>
        ` : ''}
      </div>
    </div>
  ` : '';
    return `
    <div class="card">
      <div class="outcome-header">
        <div class="outcome-title">${escapeHtml(outcome.title)}</div>
        <div class="outcome-meta">
          ${outcome.timeFrame ? `<strong>Time Frame:</strong> ${escapeHtml(outcome.timeFrame)}` : ''}
          ${outcome.paramType ? ` | <strong>Measure:</strong> ${escapeHtml(outcome.paramType)}` : ''}
        </div>
        ${outcome.description ? `<div class="outcome-description">${escapeHtml(outcome.description)}</div>` : ''}
      </div>

      ${outcome.results.length > 0 ? `
        <table>
          <thead>
            <tr>
              <th>Arm</th>
              <th>Value</th>
              <th>CI/Spread</th>
              <th class="text-center">N</th>
            </tr>
          </thead>
          <tbody>
            ${resultsRows}
          </tbody>
        </table>
        ${analysisHtml}
      ` : '<p class="no-data">No measurements posted</p>'}
    </div>
  `;
}
function generateSafetySection(safety) {
    // Summary cards
    const summaryHtml = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
      ${safety.arms.map(arm => `
        <div class="card" style="margin-bottom: 0;">
          <div style="font-weight: 600; margin-bottom: 0.5rem;">${escapeHtml(arm.title)}</div>
          <div style="font-size: 0.875rem; color: var(--gray-600);">
            <div>Serious AEs: <strong>${arm.seriousNumAffected}</strong>/${arm.seriousNumAtRisk} (${arm.seriousNumAtRisk > 0 ? ((arm.seriousNumAffected / arm.seriousNumAtRisk) * 100).toFixed(1) : 0}%)</div>
            <div>Other AEs: <strong>${arm.otherNumAffected}</strong>/${arm.otherNumAtRisk} (${arm.otherNumAtRisk > 0 ? ((arm.otherNumAffected / arm.otherNumAtRisk) * 100).toFixed(1) : 0}%)</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
    // Serious events table
    const seriousEventsHtml = safety.seriousEvents.length > 0 ? `
    <div class="card">
      <div class="card-title">Serious Adverse Events (${safety.seriousEvents.length})</div>
      <input type="text" class="search-box ae-search" data-table="sae-table" placeholder="Search serious events...">
      <div style="max-height: 400px; overflow-y: auto;">
        <table id="sae-table">
          <thead>
            <tr>
              <th>Event Term</th>
              <th>Organ System</th>
              ${safety.arms.map(arm => `<th class="text-center">${escapeHtml(arm.title.substring(0, 20))}</th>`).join('')}
              <th class="text-center">Overall</th>
            </tr>
          </thead>
          <tbody>
            ${safety.seriousEvents.slice(0, 50).map(event => `
              <tr>
                <td><strong>${escapeHtml(event.term)}</strong></td>
                <td style="font-size: 0.8rem; color: var(--gray-500);">${event.organSystem ? escapeHtml(event.organSystem) : '—'}</td>
                ${event.byArm.map(a => `
                  <td class="text-center">
                    <span class="ae-rate ${getRateClass(a.rate)}">${a.rate.toFixed(1)}%</span>
                    <div style="font-size: 0.7rem; color: var(--gray-400);">${a.numAffected}/${a.numAtRisk}</div>
                  </td>
                `).join('')}
                <td class="text-center">
                  <span class="ae-rate ${getRateClass(event.overallRate)}">${event.overallRate.toFixed(1)}%</span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  ` : '<div class="card"><p class="no-data">No serious adverse events reported</p></div>';
    // Other events table (top 30)
    const otherEventsHtml = safety.otherEvents.length > 0 ? `
    <div class="card">
      <div class="card-title">Other Adverse Events (showing top 30 of ${safety.otherEvents.length})</div>
      <input type="text" class="search-box ae-search" data-table="oae-table" placeholder="Search other events...">
      <div style="max-height: 400px; overflow-y: auto;">
        <table id="oae-table">
          <thead>
            <tr>
              <th>Event Term</th>
              <th>Organ System</th>
              ${safety.arms.map(arm => `<th class="text-center">${escapeHtml(arm.title.substring(0, 20))}</th>`).join('')}
              <th class="text-center">Overall</th>
            </tr>
          </thead>
          <tbody>
            ${safety.otherEvents.slice(0, 30).map(event => `
              <tr>
                <td><strong>${escapeHtml(event.term)}</strong></td>
                <td style="font-size: 0.8rem; color: var(--gray-500);">${event.organSystem ? escapeHtml(event.organSystem) : '—'}</td>
                ${event.byArm.map(a => `
                  <td class="text-center">
                    <span class="ae-rate ${getRateClass(a.rate)}">${a.rate.toFixed(1)}%</span>
                    <div style="font-size: 0.7rem; color: var(--gray-400);">${a.numAffected}/${a.numAtRisk}</div>
                  </td>
                `).join('')}
                <td class="text-center">
                  <span class="ae-rate ${getRateClass(event.overallRate)}">${event.overallRate.toFixed(1)}%</span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  ` : '<div class="card"><p class="no-data">No other adverse events reported</p></div>';
    return `
    ${safety.timeFrame ? `<p style="margin-bottom: 1rem; color: var(--gray-600);"><strong>Time Frame:</strong> ${escapeHtml(safety.timeFrame)}</p>` : ''}
    ${summaryHtml}
    ${seriousEventsHtml}
    ${otherEventsHtml}
  `;
}
function getStatusBadgeClass(status) {
    const s = status.toLowerCase();
    if (s.includes('completed'))
        return 'status-completed';
    if (s.includes('recruiting'))
        return 'status-recruiting';
    if (s.includes('terminated') || s.includes('withdrawn'))
        return 'status-terminated';
    return 'status-other';
}
function getRateClass(rate) {
    if (rate >= 10)
        return 'ae-rate-high';
    if (rate >= 5)
        return 'ae-rate-medium';
    return 'ae-rate-low';
}
// ============================================
// Trial Comparison HTML Generator
// ============================================
function generateTrialComparisonHtml(comparison) {
    const { trials } = comparison;
    const timestamp = new Date().toLocaleString();
    // Build comparison tables
    const populationHtml = `
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          ${trials.map(t => `<th class="text-center">${t.nctId}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Title</strong></td>
          ${trials.map(t => `<td style="font-size: 0.8rem;">${escapeHtml(t.title.substring(0, 60))}...</td>`).join('')}
        </tr>
        <tr>
          <td><strong>Phase</strong></td>
          ${trials.map(t => `<td class="text-center"><span class="phase-badge ${getTrialPhaseClass(t.phase)}">${escapeHtml(t.phase)}</span></td>`).join('')}
        </tr>
        <tr>
          <td><strong>Status</strong></td>
          ${trials.map(t => `<td class="text-center"><span class="status-badge ${getStatusBadgeClass(t.status)}">${escapeHtml(t.status)}</span></td>`).join('')}
        </tr>
        <tr>
          <td><strong>Sponsor</strong></td>
          ${trials.map(t => `<td style="font-size: 0.85rem;">${escapeHtml(t.sponsor)}</td>`).join('')}
        </tr>
        <tr>
          <td><strong>Enrollment</strong></td>
          ${trials.map(t => `<td class="text-center">${t.enrollment.toLocaleString()}</td>`).join('')}
        </tr>
        <tr>
          <td><strong>Arms</strong></td>
          ${trials.map(t => `<td style="font-size: 0.8rem;">${t.arms.map(a => `${escapeHtml(a.title)} (N=${a.n || '?'})`).join('<br>')}</td>`).join('')}
        </tr>
      </tbody>
    </table>
  `;
    const endpointsHtml = comparison.comparison.primaryEndpoints.length > 0 ? `
    <table>
      <thead>
        <tr>
          <th>Primary Endpoint</th>
          ${trials.map(t => `<th class="text-center">${t.nctId}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${comparison.comparison.primaryEndpoints.map(ep => `
          <tr>
            <td><strong>${escapeHtml(ep.endpoint.substring(0, 50))}${ep.endpoint.length > 50 ? '...' : ''}</strong></td>
            ${trials.map(t => {
        const result = ep.byTrial.find(r => r.nctId === t.nctId);
        if (!result)
            return '<td class="text-center" style="color: var(--gray-400);">N/A</td>';
        return `
                <td class="text-center">
                  <div class="result-value">${escapeHtml(result.value)}</div>
                  ${result.pValue ? `<div class="p-value ${result.significant ? 'p-significant' : 'p-not-significant'}">${escapeHtml(result.pValue)}</div>` : ''}
                </td>
              `;
    }).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  ` : '<p class="no-data">No primary endpoint data available for comparison</p>';
    const safetyHtml = comparison.comparison.safetyHighlights.length > 0 ? `
    <table>
      <thead>
        <tr>
          <th>Adverse Event</th>
          ${trials.map(t => `<th class="text-center">${t.nctId}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${comparison.comparison.safetyHighlights.map(event => `
          <tr>
            <td><strong>${escapeHtml(event.event)}</strong></td>
            ${trials.map(t => {
        const result = event.byTrial.find(r => r.nctId === t.nctId);
        if (!result)
            return '<td class="text-center" style="color: var(--gray-400);">—</td>';
        return `<td class="text-center"><span class="ae-rate ${getRateClass(result.rate)}">${result.rate.toFixed(1)}%</span></td>`;
    }).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  ` : '<p class="no-data">No common adverse events to compare</p>';
    const differencesHtml = comparison.comparison.endpointDifferences.length > 0 ? `
    <div class="card" style="background: #fef3c7; border-color: #f59e0b;">
      <div class="card-title" style="color: #92400e;">⚠️ Endpoint Differences</div>
      <ul style="margin-left: 1.5rem; color: #92400e;">
        ${comparison.comparison.endpointDifferences.map(d => `<li>${escapeHtml(d)}</li>`).join('')}
      </ul>
    </div>
  ` : '';
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trial Comparison | Helix Intelligence</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-400: #9ca3af;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 600;
      max-width: 1200px;
      margin: 0 auto;
    }

    .header-subtitle {
      max-width: 1200px;
      margin: 0.5rem auto 0;
      opacity: 0.9;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
    }

    .section {
      margin-bottom: 2rem;
    }

    .section-title {
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1rem;
      overflow-x: auto;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      border-bottom: 2px solid var(--gray-200);
      white-space: nowrap;
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    tr:hover { background: var(--gray-50); }

    .text-center { text-align: center; }

    .phase-badge, .status-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-4, .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-na { background: var(--gray-100); color: var(--gray-500); }

    .status-completed { background: #dcfce7; color: #166534; }
    .status-recruiting { background: #dbeafe; color: #1e40af; }
    .status-terminated { background: #fee2e2; color: #991b1b; }
    .status-other { background: var(--gray-200); color: var(--gray-700); }

    .result-value { font-weight: 600; }

    .p-value { font-size: 0.8rem; margin-top: 0.25rem; }
    .p-significant { color: var(--success); }
    .p-not-significant { color: var(--gray-500); }

    .ae-rate { font-weight: 600; }
    .ae-rate-high { color: var(--danger); }
    .ae-rate-medium { color: var(--warning); }
    .ae-rate-low { color: var(--gray-700); }

    .no-data { color: var(--gray-500); font-style: italic; padding: 1rem; text-align: center; }

    .link { color: var(--primary); text-decoration: none; }
    .link:hover { text-decoration: underline; }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }
  </style>
</head>
<body>
  <header class="header">
    <h1>📊 Trial Comparison</h1>
    <div class="header-subtitle">
      Comparing ${trials.length} trials: ${trials.map(t => `<a href="/api/trial/${t.nctId}/results/html" style="color: white;">${t.nctId}</a>`).join(', ')}
    </div>
  </header>

  <div class="container">
    ${differencesHtml}

    <section class="section">
      <h2 class="section-title">📋 Study Overview</h2>
      <div class="card">
        ${populationHtml}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">🎯 Primary Efficacy Endpoints</h2>
      <div class="card">
        ${endpointsHtml}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">⚠️ Safety Comparison (Common AEs)</h2>
      <div class="card">
        ${safetyHtml}
      </div>
    </section>

    <footer class="footer">
      <div>⬡ Powered by Helix Intelligence</div>
      <div>Data source: ClinicalTrials.gov | ${timestamp}</div>
    </footer>
  </div>
</body>
</html>`;
}
// ============================================
// Patent Profile HTML
// ============================================
function generatePatentProfileHtml(profile) {
    const timestamp = new Date().toLocaleString();
    // LOE status badge
    const daysUntil = profile.daysUntilLOE;
    let loeStatus = '';
    let loeClass = '';
    if (daysUntil === null) {
        loeStatus = 'Unknown';
        loeClass = 'badge-gray';
    }
    else if (daysUntil <= 0) {
        loeStatus = 'Expired';
        loeClass = 'badge-red';
    }
    else if (daysUntil <= 365) {
        loeStatus = `${Math.round(daysUntil / 30)} months`;
        loeClass = 'badge-red';
    }
    else if (daysUntil <= 365 * 3) {
        loeStatus = `${(daysUntil / 365).toFixed(1)} years`;
        loeClass = 'badge-orange';
    }
    else {
        loeStatus = `${(daysUntil / 365).toFixed(1)} years`;
        loeClass = 'badge-green';
    }
    // Patent table rows
    const patentRows = profile.patents.map(p => {
        const typeFlags = [];
        if (p.drugSubstance)
            typeFlags.push('Substance');
        if (p.drugProduct)
            typeFlags.push('Product');
        if (p.patentUseCode)
            typeFlags.push(`Use: ${p.patentUseCode}`);
        return `<tr>
      <td><a href="https://patents.google.com/patent/US${p.patentNumber}" target="_blank">${p.patentNumber}</a></td>
      <td>${typeFlags.join(', ') || '—'}</td>
      <td>${p.expiryDate || '—'}</td>
      <td>${p.expiryDateParsed || '—'}</td>
      <td>${p.delistFlag ? 'Yes' : 'No'}</td>
    </tr>`;
    }).join('\n');
    // Exclusivity table rows
    const exclRows = profile.exclusivities.map(e => `<tr>
    <td><strong>${e.exclusivityCode}</strong></td>
    <td>${e.exclusivityType}</td>
    <td>${e.exclusivityDate}</td>
    <td>${e.exclusivityDateParsed || '—'}</td>
  </tr>`).join('\n');
    // Patent expiry timeline visualization
    const today = new Date();
    const timelineStart = today.getFullYear();
    const timelineEnd = timelineStart + 15;
    const timelineYears = [];
    for (let y = timelineStart; y <= timelineEnd; y++)
        timelineYears.push(y);
    // Group patents by expiry year
    const patentsByYear = new Map();
    for (const p of profile.patents) {
        if (p.expiryDateParsed) {
            const year = new Date(p.expiryDateParsed).getFullYear();
            if (!patentsByYear.has(year))
                patentsByYear.set(year, []);
            patentsByYear.get(year).push(p);
        }
    }
    const timelineBars = timelineYears.map(year => {
        const patents = patentsByYear.get(year) || [];
        const count = patents.length;
        const height = count > 0 ? Math.max(20, Math.min(count * 15, 150)) : 0;
        const isPast = year < today.getFullYear();
        const isLOEYear = profile.effectiveLOE && new Date(profile.effectiveLOE).getFullYear() === year;
        const barClass = isLOEYear ? 'timeline-bar-loe' : isPast ? 'timeline-bar-past' : count > 0 ? 'timeline-bar-active' : '';
        return `<div class="timeline-col">
      <div class="timeline-bar ${barClass}" style="height: ${height}px" title="${count} patents expire in ${year}">
        ${count > 0 ? `<span class="timeline-count">${count}</span>` : ''}
      </div>
      <div class="timeline-label${isLOEYear ? ' timeline-loe-label' : ''}">${year}</div>
    </div>`;
    }).join('\n');
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Patent Profile: ${profile.brandName} - Helix Intelligence</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a1a; color: #e0e0e0; line-height: 1.6; }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #1a1a3e, #2d1b4e); border-radius: 12px; padding: 30px; margin-bottom: 20px; }
    .header h1 { font-size: 2em; color: #fff; margin-bottom: 5px; }
    .header .subtitle { color: #aaa; font-size: 1.1em; }
    .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
    .meta-card { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; }
    .meta-label { color: #888; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; }
    .meta-value { font-size: 1.3em; font-weight: 600; color: #fff; margin-top: 4px; }
    .section { margin-bottom: 25px; }
    .section-title { font-size: 1.3em; color: #fff; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #333; }
    .card { background: #12122a; border-radius: 10px; padding: 20px; border: 1px solid #222; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }
    .badge-green { background: rgba(0,200,100,0.15); color: #00c864; }
    .badge-orange { background: rgba(255,165,0,0.15); color: #ffa500; }
    .badge-red { background: rgba(255,60,60,0.15); color: #ff3c3c; }
    .badge-gray { background: rgba(150,150,150,0.15); color: #999; }
    .badge-blue { background: rgba(100,149,237,0.15); color: #6495ed; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 10px 12px; background: rgba(255,255,255,0.05); color: #aaa; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }
    td { padding: 10px 12px; border-top: 1px solid #1a1a35; }
    td a { color: #6495ed; text-decoration: none; }
    td a:hover { text-decoration: underline; }
    tr:hover td { background: rgba(255,255,255,0.03); }
    .loe-banner { background: linear-gradient(135deg, #1a2a1a, #1a3a1a); border: 1px solid #2a4a2a; border-radius: 10px; padding: 25px; text-align: center; margin-bottom: 25px; }
    .loe-date { font-size: 2em; font-weight: 700; color: #fff; }
    .loe-detail { color: #aaa; margin-top: 5px; }
    .timeline { display: flex; align-items: flex-end; gap: 4px; height: 180px; padding: 10px 0; }
    .timeline-col { display: flex; flex-direction: column; align-items: center; flex: 1; }
    .timeline-bar { width: 100%; max-width: 50px; border-radius: 4px 4px 0 0; display: flex; align-items: flex-end; justify-content: center; transition: all 0.3s; }
    .timeline-bar-active { background: linear-gradient(to top, #4a6cf7, #6a8cff); }
    .timeline-bar-past { background: #333; }
    .timeline-bar-loe { background: linear-gradient(to top, #ff3c3c, #ff6b6b); }
    .timeline-count { color: #fff; font-size: 0.8em; font-weight: 600; padding: 4px; }
    .timeline-label { font-size: 0.75em; color: #888; margin-top: 5px; writing-mode: vertical-rl; text-orientation: mixed; }
    .timeline-loe-label { color: #ff3c3c; font-weight: 700; }
    .footer { text-align: center; color: #555; font-size: 0.85em; margin-top: 30px; padding: 15px; border-top: 1px solid #222; }
    .empty-msg { color: #666; font-style: italic; padding: 20px; text-align: center; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${profile.brandName}</h1>
      <div class="subtitle">${profile.drugName} | ${profile.sponsor} | ${profile.approval.applicationNumber}</div>
      <div class="meta-grid">
        <div class="meta-card">
          <div class="meta-label">Application Type</div>
          <div class="meta-value">
            <span class="badge ${profile.approval.isBiologic ? 'badge-blue' : 'badge-green'}">${profile.approval.applicationType}</span>
          </div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Approval Date</div>
          <div class="meta-value">${profile.approval.approvalDate || 'Unknown'}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Unique Patents</div>
          <div class="meta-value">${profile.uniquePatentNumbers.length}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Exclusivities</div>
          <div class="meta-value">${profile.exclusivities.length}</div>
        </div>
      </div>
    </div>

    <div class="loe-banner">
      <div style="color: #888; font-size: 0.9em; text-transform: uppercase; letter-spacing: 2px;">Effective Loss of Exclusivity</div>
      <div class="loe-date">${profile.effectiveLOE || 'Unknown'}</div>
      <div class="loe-detail">
        <span class="badge ${loeClass}">${loeStatus} remaining</span>
        ${profile.biologicExclusivityExpiry ? `<span style="color:#888; margin-left:10px;">BPCIA 12-year: ${profile.biologicExclusivityExpiry}</span>` : ''}
      </div>
      <div class="loe-detail" style="margin-top:8px;">
        ${profile.latestPatentExpiry ? `Latest Patent: ${profile.latestPatentExpiry}` : ''}
        ${profile.latestPatentExpiry && profile.latestExclusivityExpiry ? ' | ' : ''}
        ${profile.latestExclusivityExpiry ? `Latest Exclusivity: ${profile.latestExclusivityExpiry}` : ''}
      </div>
    </div>

    <section class="section">
      <h2 class="section-title">Patent Expiry Timeline</h2>
      <div class="card">
        ${profile.patents.length > 0 ? `<div class="timeline">${timelineBars}</div>
        <div style="text-align:center; margin-top:10px; font-size:0.85em; color:#888;">
          <span style="display:inline-block; width:12px; height:12px; background:#4a6cf7; border-radius:2px; margin-right:4px;"></span> Active patents
          <span style="display:inline-block; width:12px; height:12px; background:#ff3c3c; border-radius:2px; margin-left:15px; margin-right:4px;"></span> LOE year
          <span style="display:inline-block; width:12px; height:12px; background:#333; border-radius:2px; margin-left:15px; margin-right:4px;"></span> Past
        </div>` : '<div class="empty-msg">No Orange Book patent data (biologic products use BPCIA exclusivity)</div>'}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Orange Book Patents (${profile.patents.length})</h2>
      <div class="card">
        ${profile.patents.length > 0 ? `<table>
          <thead><tr><th>Patent #</th><th>Type</th><th>Expiry</th><th>ISO Date</th><th>Delisted</th></tr></thead>
          <tbody>${patentRows}</tbody>
        </table>` : '<div class="empty-msg">No patents listed in Orange Book</div>'}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Exclusivities (${profile.exclusivities.length})</h2>
      <div class="card">
        ${profile.exclusivities.length > 0 ? `<table>
          <thead><tr><th>Code</th><th>Type</th><th>Expiry</th><th>ISO Date</th></tr></thead>
          <tbody>${exclRows}</tbody>
        </table>` : `<div class="empty-msg">No exclusivities listed${profile.approval.isBiologic ? ' (biologic &mdash; 12-year BPCIA exclusivity applies)' : ''}</div>`}
      </div>
    </section>

    <footer class="footer">
      <div>Helix Intelligence | Patent & Exclusivity Tracker</div>
      <div>Data: FDA Orange Book + OpenFDA | ${timestamp}</div>
    </footer>
  </div>
</body>
</html>`;
}
// ============================================
// Patent Timeline HTML (by Condition)
// ============================================
function generatePatentTimelineHtml(condition, profiles) {
    const timestamp = new Date().toLocaleString();
    const condTitle = condition.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    // Build timeline data: group by year
    const today = new Date();
    const currentYear = today.getFullYear();
    const timelineStart = currentYear;
    const timelineEnd = currentYear + 15;
    // Create LOE timeline rows
    const drugRows = profiles.map(profile => {
        const loeYear = profile.effectiveLOE ? new Date(profile.effectiveLOE).getFullYear() : null;
        const daysUntil = profile.daysUntilLOE;
        let urgency = '';
        if (daysUntil === null)
            urgency = 'unknown';
        else if (daysUntil <= 0)
            urgency = 'expired';
        else if (daysUntil <= 365 * 2)
            urgency = 'imminent';
        else if (daysUntil <= 365 * 5)
            urgency = 'approaching';
        else
            urgency = 'protected';
        // Timeline bar
        const barCells = [];
        for (let y = timelineStart; y <= timelineEnd; y++) {
            const isLOE = loeYear === y;
            const isProtected = loeYear !== null && y < loeYear;
            const isExpired = loeYear !== null && y > loeYear;
            let cellClass = 'tl-empty';
            if (isLOE)
                cellClass = 'tl-loe';
            else if (isProtected)
                cellClass = 'tl-protected';
            else if (isExpired)
                cellClass = 'tl-expired';
            barCells.push(`<td class="tl-cell ${cellClass}" title="${profile.brandName}: ${isLOE ? 'LOE' : isProtected ? 'Protected' : isExpired ? 'Exposed' : 'Unknown'} in ${y}"></td>`);
        }
        return `<tr>
      <td class="drug-name">
        <a href="/api/patents/${encodeURIComponent(profile.brandName.toLowerCase())}/html">${profile.brandName}</a>
        <div class="drug-sub">${profile.drugName} | ${profile.sponsor}</div>
      </td>
      <td><span class="badge badge-${profile.approval.applicationType === 'BLA' ? 'blue' : 'green'}">${profile.approval.applicationType}</span></td>
      <td>${profile.uniquePatentNumbers.length}</td>
      <td class="loe-cell loe-${urgency}">${profile.effectiveLOE || '—'}</td>
      ${barCells.join('\n')}
    </tr>`;
    }).join('\n');
    // Year headers
    const yearHeaders = [];
    for (let y = timelineStart; y <= timelineEnd; y++) {
        yearHeaders.push(`<th class="tl-header">${y.toString().slice(2)}</th>`);
    }
    // Summary stats
    const loeThisYear = profiles.filter(p => p.effectiveLOE && new Date(p.effectiveLOE).getFullYear() === currentYear).length;
    const loeNext3Years = profiles.filter(p => {
        if (!p.effectiveLOE)
            return false;
        const y = new Date(p.effectiveLOE).getFullYear();
        return y >= currentYear && y <= currentYear + 3;
    }).length;
    const biologics = profiles.filter(p => p.approval.isBiologic).length;
    const totalPatents = profiles.reduce((sum, p) => sum + p.uniquePatentNumbers.length, 0);
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Patent Timeline: ${condTitle} - Helix Intelligence</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a1a; color: #e0e0e0; line-height: 1.6; }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #1a1a3e, #2d1b4e); border-radius: 12px; padding: 30px; margin-bottom: 20px; }
    .header h1 { font-size: 2em; color: #fff; }
    .header .subtitle { color: #aaa; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-top: 20px; }
    .stat-card { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; text-align: center; }
    .stat-num { font-size: 2em; font-weight: 700; color: #fff; }
    .stat-label { color: #888; font-size: 0.85em; }
    .section { margin-bottom: 25px; }
    .section-title { font-size: 1.3em; color: #fff; margin-bottom: 15px; }
    .card { background: #12122a; border-radius: 10px; padding: 20px; border: 1px solid #222; overflow-x: auto; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.8em; font-weight: 600; }
    .badge-green { background: rgba(0,200,100,0.15); color: #00c864; }
    .badge-blue { background: rgba(100,149,237,0.15); color: #6495ed; }
    table { width: 100%; border-collapse: collapse; white-space: nowrap; }
    th { text-align: left; padding: 8px 10px; background: rgba(255,255,255,0.05); color: #aaa; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; position: sticky; top: 0; }
    td { padding: 8px 10px; border-top: 1px solid #1a1a35; font-size: 0.9em; }
    .drug-name a { color: #6495ed; text-decoration: none; font-weight: 600; }
    .drug-name a:hover { text-decoration: underline; }
    .drug-sub { color: #666; font-size: 0.8em; }
    .loe-cell { font-weight: 600; }
    .loe-expired { color: #ff3c3c; }
    .loe-imminent { color: #ff8c00; }
    .loe-approaching { color: #ffd700; }
    .loe-protected { color: #00c864; }
    .loe-unknown { color: #666; }
    .tl-cell { width: 30px; min-width: 30px; height: 20px; border: 1px solid #1a1a35; }
    .tl-protected { background: rgba(0,200,100,0.25); }
    .tl-loe { background: #ff3c3c; }
    .tl-expired { background: rgba(255,60,60,0.1); }
    .tl-empty { background: transparent; }
    .tl-header { text-align: center; font-size: 0.75em; width: 30px; min-width: 30px; }
    .footer { text-align: center; color: #555; font-size: 0.85em; margin-top: 30px; padding: 15px; border-top: 1px solid #222; }
    .legend { display: flex; gap: 20px; margin-top: 15px; font-size: 0.85em; color: #888; }
    .legend-item { display: flex; align-items: center; gap: 5px; }
    .legend-color { width: 16px; height: 12px; border-radius: 2px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Patent & Exclusivity Timeline</h1>
      <div class="subtitle">${condTitle} — ${profiles.length} drugs analyzed</div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">${profiles.length}</div>
          <div class="stat-label">Drugs Tracked</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${totalPatents}</div>
          <div class="stat-label">Total Patents</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${biologics}</div>
          <div class="stat-label">Biologics (BLA)</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: ${loeThisYear > 0 ? '#ff3c3c' : '#00c864'}">${loeThisYear}</div>
          <div class="stat-label">LOE This Year</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: ${loeNext3Years > 0 ? '#ffa500' : '#00c864'}">${loeNext3Years}</div>
          <div class="stat-label">LOE Next 3 Years</div>
        </div>
      </div>
    </div>

    <section class="section">
      <h2 class="section-title">LOE Timeline</h2>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Drug</th>
              <th>Type</th>
              <th>Patents</th>
              <th>Eff. LOE</th>
              ${yearHeaders.join('\n')}
            </tr>
          </thead>
          <tbody>
            ${drugRows}
          </tbody>
        </table>
        <div class="legend">
          <div class="legend-item"><div class="legend-color" style="background: rgba(0,200,100,0.25);"></div> Protected</div>
          <div class="legend-item"><div class="legend-color" style="background: #ff3c3c;"></div> LOE Year</div>
          <div class="legend-item"><div class="legend-color" style="background: rgba(255,60,60,0.1);"></div> Exposed</div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div>Helix Intelligence | Patent & Exclusivity Tracker</div>
      <div>Data: FDA Orange Book + OpenFDA + BPCIA | ${timestamp}</div>
    </footer>
  </div>
</body>
</html>`;
}
// ============================================
// Target Report HTML Generator
// ============================================
function generateTargetReportHtml(report, trialAnalytics) {
    const timestamp = new Date().toLocaleString();
    const { target, summary, trials, publications, deals, kols, curatedAssets, investmentMetrics } = report;
    const assetCount = curatedAssets?.length || 0;
    // Trial rows
    const trialRows = trials.slice(0, 50).map((t) => `
    <tr>
      <td><a href="https://clinicaltrials.gov/study/${t.nctId}" target="_blank">${t.nctId}</a></td>
      <td class="title-cell">${t.briefTitle}</td>
      <td><span class="phase-badge phase-${(t.phase || '').toLowerCase().replace(/[^a-z0-9]/g, '')}">${t.phase}</span></td>
      <td><span class="status-badge status-${(t.status || '').toLowerCase().replace(/[^a-z]/g, '-')}">${t.status}</span></td>
      <td>${t.leadSponsor?.name || '-'}</td>
      <td>${t.enrollment?.count || '-'}</td>
      <td>${t.startDate || '-'}</td>
    </tr>
  `).join('');
    // Asset rows (curated investment-quality data)
    const assetRows = (curatedAssets || []).map((a) => {
        const ownerTypeClass = (a.ownerType || '').toLowerCase().replace(/\s+/g, '-');
        const regBadges = [];
        if (a.regulatory?.btd)
            regBadges.push('<span class="reg-badge reg-btd">BTD</span>');
        if (a.regulatory?.odd)
            regBadges.push('<span class="reg-badge reg-odd">ODD</span>');
        if (a.regulatory?.prime)
            regBadges.push('<span class="reg-badge reg-prime">PRIME</span>');
        if (a.regulatory?.fastTrack)
            regBadges.push('<span class="reg-badge reg-ft">FT</span>');
        const linkedTrials = (a.trialIds || []).slice(0, 3).map((nct) => `<a href="https://clinicaltrials.gov/study/${nct}" target="_blank" class="trial-link">${nct}</a>`).join(' ');
        return `
    <tr class="curated-asset">
      <td>
        <strong>${a.primaryName}</strong>
        ${a.codeNames?.length ? `<br><span class="code-name">${a.codeNames.join(', ')}</span>` : ''}
        ${regBadges.length ? `<br>${regBadges.join(' ')}` : ''}
      </td>
      <td>
        <span class="modality-badge modality-${(a.modality || '').toLowerCase().replace(/[^a-z]/g, '')}">${a.modality}</span>
        ${a.modalityDetail ? `<br><span class="payload">${a.modalityDetail}</span>` : (a.payload ? `<br><span class="payload">${a.payload}</span>` : '')}
      </td>
      <td>
        <span class="owner-type owner-${ownerTypeClass}">${a.owner || '-'}</span>
        ${a.partner ? `<br><span class="partner">+ ${a.partner}</span>` : ''}
      </td>
      <td><span class="phase-badge phase-${(a.phase || '').toLowerCase().replace(/[^a-z0-9]/g, '')}">${a.phase}</span></td>
      <td><span class="status-badge status-${(a.status || '').toLowerCase()}">${a.status}</span></td>
      <td class="indication-cell">${a.leadIndication || '-'}</td>
      <td class="deal-cell">${a.deal?.headline || '-'}${a.deal?.upfront ? `<br><span class="deal-upfront">Upfront: ${a.deal.upfront}</span>` : ''}</td>
      <td class="notes-cell">
        ${a.keyData ? `<span class="key-data">${a.keyData}</span><br>` : ''}
        ${linkedTrials ? `<span class="linked-trials">${linkedTrials}</span>` : ''}
      </td>
    </tr>`;
    }).join('');
    // Publication rows
    const pubRows = publications.slice(0, 20).map((p) => `
    <tr>
      <td>${p.pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${p.pmid}" target="_blank">${p.pmid}</a>` : '-'}</td>
      <td class="title-cell">${p.title}</td>
      <td>${(p.authors || []).slice(0, 3).map((a) => `${a.lastName}`).join(', ')}${p.authors?.length > 3 ? ' et al.' : ''}</td>
      <td>${p.journal || '-'}</td>
      <td>${p.publicationDate?.split('-')[0] || '-'}</td>
    </tr>
  `).join('');
    // Deal rows
    const dealRows = deals.map((d) => `
    <tr>
      <td>${d.date || d.announcedDate || '-'}</td>
      <td><span class="deal-badge">${d.dealType || d.type || '-'}</span></td>
      <td>${(d.parties || []).join(' + ')}</td>
      <td>${d.assetName || d.asset?.name || '-'}</td>
      <td>${d.terms?.totalValue ? `$${d.terms.totalValue}M` : d.terms?.upfrontPayment ? `$${d.terms.upfrontPayment}M upfront` : '-'}</td>
    </tr>
  `).join('');
    // Author rows (derived from publications, no fake h-index)
    const authorRows = kols.map((k) => `
    <tr>
      <td><strong>${k.name || `${k.lastName || ''} ${k.foreName || ''}`.trim()}</strong></td>
      <td>${k.institution || '-'}</td>
      <td>${k.publicationCount || 0}</td>
      <td>${k.firstAuthorCount || 0}</td>
      <td>${k.lastAuthorCount || 0}</td>
      <td>${k.isActive ? '<span class="active-badge">Active</span>' : '<span class="inactive-badge">Inactive</span>'}</td>
    </tr>
  `).join('');
    // Phase breakdown
    const phaseLabels = Object.keys(trialAnalytics.phaseBreakdown);
    const phaseCounts = Object.values(trialAnalytics.phaseBreakdown);
    const maxPhaseCount = Math.max(...phaseCounts, 1);
    const phaseChart = phaseLabels.map((label, i) => {
        const pct = (phaseCounts[i] / maxPhaseCount) * 100;
        return `<div class="bar-row"><span class="bar-label">${label}</span><div class="bar-container"><div class="bar" style="width: ${pct}%"></div><span class="bar-value">${phaseCounts[i]}</span></div></div>`;
    }).join('');
    // Top sponsors
    const sponsorRows = (trialAnalytics.topSponsors || []).slice(0, 10).map((s) => `
    <tr>
      <td>${s.sponsor}</td>
      <td>${s.count}</td>
      <td><span class="type-badge ${s.type?.toLowerCase()}">${s.type}</span></td>
    </tr>
  `).join('');
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${target} - Helix Intelligence Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
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
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--background); color: var(--text-primary); line-height: 1.6; }
    .container { max-width: 1400px; margin: 0 auto; padding: 24px; }
    .header { background: var(--surface); padding: 32px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    h1 { color: var(--text-primary); font-size: 2rem; font-weight: 600; margin-bottom: 8px; }
    .subtitle { color: var(--text-secondary); margin-bottom: 24px; }
    .nav { display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }
    .nav a { background: var(--background); color: var(--text-secondary); padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 0.9rem; font-weight: 500; border: 1px solid var(--border); transition: all 0.2s; }
    .nav a:hover { background: var(--surface-hover); color: var(--text-primary); }
    .nav a.download { background: var(--accent); color: white; border-color: var(--accent); }
    .nav a.download:hover { background: var(--accent-hover); }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-top: 24px; }
    .stat-card { background: var(--background); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border); }
    .stat-num { font-size: 1.8rem; font-weight: 600; color: var(--accent); }
    .stat-label { font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; }
    .section { margin-bottom: 32px; }
    .section-title { color: var(--text-primary); font-size: 1.2rem; font-weight: 600; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
    .card { background: var(--surface); border-radius: 10px; padding: 20px; overflow-x: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { background: var(--background); color: var(--text-secondary); padding: 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; position: sticky; top: 0; border-bottom: 1px solid var(--border); }
    td { padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
    tr:nth-child(even) { background: var(--background); }
    tr:hover { background: var(--surface-hover); }
    .title-cell { max-width: 400px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; color: var(--accent-hover); }
    .phase-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; background: var(--background); border: 1px solid var(--border); }
    .phase-badge.phase-phase3, .phase-badge.phase-filed { background: #E8F5E9; color: #2E7D32; border-color: #C8E6C9; }
    .phase-badge.phase-phase2 { background: #FFF8E1; color: #F57F17; border-color: #FFECB3; }
    .phase-badge.phase-phase1 { background: #E3F2FD; color: #1565C0; border-color: #BBDEFB; }
    .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
    .status-badge.status-recruiting, .status-badge.status-active { background: #E8F5E9; color: #2E7D32; }
    .status-badge.status-completed { background: var(--background); color: var(--text-secondary); }
    .active-badge { background: #E8F5E9; color: #2E7D32; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; }
    .inactive-badge { background: var(--background); color: var(--text-muted); padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; }
    .type-badge { padding: 3px 8px; border-radius: 4px; font-size: 0.7rem; text-transform: uppercase; font-weight: 500; }
    .type-badge.industry { background: #F3E5F5; color: #7B1FA2; }
    .type-badge.academic { background: #E0F7FA; color: #00838F; }
    .modality-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
    .modality-badge.modality-adc { background: #FFEBEE; color: #C62828; }
    .modality-badge.modality-mab { background: #E3F2FD; color: #1565C0; }
    .modality-badge.modality-cart { background: #FCE4EC; color: #AD1457; }
    .modality-badge.modality-bispecific { background: #FFF3E0; color: #E65100; }
    .modality-badge.modality-radioconjugate { background: #FFFDE7; color: #F57F17; }
    .payload { font-size: 0.75rem; color: var(--text-secondary); }
    .code-name { font-size: 0.8rem; color: var(--accent); }
    .owner-type { font-weight: 500; }
    .owner-big-pharma { color: #AD1457; }
    .owner-biotech { color: #1565C0; }
    .owner-chinese-biotech { color: #E65100; }
    .owner-academic { color: #2E7D32; }
    .partner { font-size: 0.8rem; color: var(--text-secondary); }
    .indication-cell { max-width: 200px; font-size: 0.85rem; }
    .deal-cell { max-width: 220px; font-size: 0.85rem; color: var(--success); font-weight: 500; }
    .notes-cell { max-width: 300px; font-size: 0.85rem; color: var(--text-secondary); }
    tr.curated-asset { background: var(--surface); }
    tr.curated-asset:hover { background: var(--surface-hover); }
    .reg-badge { padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; margin-right: 4px; }
    .reg-btd { background: #E8F5E9; color: #2E7D32; }
    .reg-odd { background: #F3E5F5; color: #7B1FA2; }
    .reg-prime { background: #E0F7FA; color: #00838F; }
    .reg-ft { background: #FFF3E0; color: #E65100; }
    .key-data { color: var(--success); font-weight: 500; }
    .deal-upfront { font-size: 0.75rem; color: var(--text-secondary); }
    .linked-trials { font-size: 0.75rem; }
    .trial-link { color: var(--accent); margin-right: 6px; }
    .investment-dashboard { background: var(--surface); padding: 28px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    .investment-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 20px; }
    .investment-metric { text-align: center; padding: 20px; background: var(--background); border-radius: 10px; }
    .investment-metric .big-value { font-size: 2rem; font-weight: 600; color: var(--success); }
    .investment-metric .metric-label { font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; }
    .deal-highlight { background: #FFF8E1; border-left: 3px solid var(--warning); padding: 14px 18px; margin: 16px 0 0 0; border-radius: 0 8px 8px 0; }
    .deal-highlight strong { color: var(--text-primary); }
    .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }
    .summary-card { background: var(--background); padding: 18px; border-radius: 8px; border: 1px solid var(--border); }
    .summary-card h4 { color: var(--text-secondary); font-size: 0.8rem; font-weight: 600; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
    .summary-item { display: flex; justify-content: space-between; padding: 5px 0; font-size: 0.9rem; }
    .summary-item .label { color: var(--text-secondary); }
    .summary-item .value { color: var(--text-primary); font-weight: 600; }
    .analytics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 28px; }
    .bar-row { display: flex; align-items: center; margin-bottom: 10px; }
    .bar-label { width: 100px; font-size: 0.85rem; color: var(--text-secondary); }
    .bar-container { flex: 1; display: flex; align-items: center; gap: 10px; }
    .bar { height: 24px; background: linear-gradient(90deg, var(--accent), #E89B7D); border-radius: 4px; min-width: 4px; }
    .bar-value { font-size: 0.85rem; color: var(--text-primary); font-weight: 500; min-width: 30px; }
    .footer { text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 24px; margin-top: 32px; border-top: 1px solid var(--border); }
    .back-link { margin-bottom: 20px; }
    .back-link a { color: var(--accent); font-weight: 500; }
  </style>
</head>
<body>
  <div class="container">
    <div class="back-link"><a href="/">&larr; Back to Home</a></div>

    <div class="header">
      <h1>${target}</h1>
      <p class="subtitle">Helix Intelligence Report | Generated ${timestamp}</p>

      <div class="nav">
        <a href="#assets">Assets (${assetCount})</a>
        <a href="#trials">Trials (${summary.totalTrials})</a>
        <a href="#publications">Publications (${summary.totalPublications})</a>
        <a href="#authors">Authors (${summary.totalKOLs})</a>
        <a href="/api/report/target/${encodeURIComponent(target)}/excel" class="download">Download Excel</a>
        <a href="/api/report/target/${encodeURIComponent(target)}">JSON API</a>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">${assetCount}</div>
          <div class="stat-label">Curated Assets</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--success);">$${investmentMetrics?.totalDisclosedDealValue?.toFixed(1) || '0'}B</div>
          <div class="stat-label">Deal Value</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${summary.totalTrials}</div>
          <div class="stat-label">Clinical Trials</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: var(--success);">${summary.activeTrials}</div>
          <div class="stat-label">Active Trials</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${summary.totalPublications}</div>
          <div class="stat-label">Publications</div>
        </div>
      </div>
    </div>

    ${investmentMetrics ? `
    <div class="investment-dashboard">
      <h2 style="color:var(--text-primary);margin-bottom:20px;font-weight:600;">Investment Metrics</h2>
      <div class="investment-grid">
        <div class="investment-metric">
          <div class="big-value">$${investmentMetrics.totalDisclosedDealValue?.toFixed(1) || '0'}B</div>
          <div class="metric-label">Total Deal Value</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">$${investmentMetrics.totalUpfront?.toFixed(0) || '0'}M</div>
          <div class="metric-label">Total Upfront</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${investmentMetrics.assetsWithBTD || 0}</div>
          <div class="metric-label">BTD Designations</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${investmentMetrics.assetsWithODD || 0}</div>
          <div class="metric-label">Orphan Drug</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${investmentMetrics.assetsWithFastTrack || 0}</div>
          <div class="metric-label">Fast Track</div>
        </div>
      </div>
      ${investmentMetrics.largestDeal?.name ? `
      <div class="deal-highlight">
        <strong>Largest Deal:</strong> ${investmentMetrics.largestDeal.name} - ${investmentMetrics.largestDeal.value}
      </div>
      ` : ''}
    </div>
    ` : ''}

    <div class="analytics-grid">
      <section class="section">
        <h2 class="section-title">Trials by Phase</h2>
        <div class="card">
          ${phaseChart || '<p style="color:#94a3b8;">No trial phase data available</p>'}
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">Top Sponsors</h2>
        <div class="card">
          <table>
            <thead><tr><th>Sponsor</th><th>Trials</th><th>Type</th></tr></thead>
            <tbody>${sponsorRows || '<tr><td colspan="3" style="color:#94a3b8;">No sponsor data</td></tr>'}</tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="section" id="assets">
      <h2 class="section-title">Competitive Landscape: ${target} Assets (${assetCount})</h2>
      <p style="color:#94a3b8;margin-bottom:15px;font-size:0.9rem;">
        Investment-quality curated database with deal terms, regulatory designations, and clinical data
      </p>

      ${investmentMetrics ? `
      <div class="summary-cards">
        <div class="summary-card">
          <h4>By Modality</h4>
          ${Object.entries(investmentMetrics.modalityBreakdown || {}).map(([k, v]) => `<div class="summary-item"><span class="label">${k}</span><span class="value">${v.count}${v.dealValue > 0 ? ` <span style="color:#4ade80;font-size:0.75rem;">($${(v.dealValue / 1000).toFixed(1)}B)</span>` : ''}</span></div>`).join('')}
        </div>
        <div class="summary-card">
          <h4>By Phase</h4>
          ${Object.entries(investmentMetrics.phaseDistribution || {}).sort((a, b) => {
        const order = ['Approved', 'Filed', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Preclinical'];
        return order.indexOf(a[0]) - order.indexOf(b[0]);
    }).map(([k, v]) => `<div class="summary-item"><span class="label">${k}</span><span class="value">${v}</span></div>`).join('')}
        </div>
        <div class="summary-card">
          <h4>By Owner Type</h4>
          ${Object.entries(investmentMetrics.ownershipBreakdown || {}).map(([k, v]) => `<div class="summary-item"><span class="label">${k}</span><span class="value">${v}</span></div>`).join('')}
        </div>
        <div class="summary-card">
          <h4>Regulatory</h4>
          <div class="summary-item"><span class="label">BTD</span><span class="value">${investmentMetrics.assetsWithBTD || 0}</span></div>
          <div class="summary-item"><span class="label">ODD</span><span class="value">${investmentMetrics.assetsWithODD || 0}</span></div>
          <div class="summary-item"><span class="label">PRIME</span><span class="value">${investmentMetrics.assetsWithPRIME || 0}</span></div>
          <div class="summary-item"><span class="label">Fast Track</span><span class="value">${investmentMetrics.assetsWithFastTrack || 0}</span></div>
        </div>
      </div>
      ` : ''}

      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Drug Name / Regulatory</th>
              <th>Modality / Tech</th>
              <th>Owner / Partner</th>
              <th>Phase</th>
              <th>Status</th>
              <th>Lead Indication</th>
              <th>Deal Info</th>
              <th>Key Data / Trials</th>
            </tr>
          </thead>
          <tbody>
            ${assetRows || '<tr><td colspan="8" style="color:#94a3b8;">No assets found</td></tr>'}
          </tbody>
        </table>
        <p style="margin-top:15px;font-size:0.8rem;color:#64748b;">
          <span class="reg-badge reg-btd">BTD</span> Breakthrough Therapy |
          <span class="reg-badge reg-odd">ODD</span> Orphan Drug |
          <span class="reg-badge reg-prime">PRIME</span> EU Priority |
          <span class="reg-badge reg-ft">FT</span> Fast Track
        </p>
      </div>
    </section>

    <section class="section" id="trials">
      <h2 class="section-title">Clinical Trials (${trials.length})</h2>
      <div class="card">
        <table>
          <thead>
            <tr><th>NCT ID</th><th>Title</th><th>Phase</th><th>Status</th><th>Sponsor</th><th>Enrollment</th><th>Start</th></tr>
          </thead>
          <tbody>
            ${trialRows || '<tr><td colspan="7" style="color:#94a3b8;">No trials found</td></tr>'}
          </tbody>
        </table>
        ${trials.length > 50 ? `<p style="margin-top:15px;color:#94a3b8;">Showing 50 of ${trials.length} trials. Download Excel for complete data.</p>` : ''}
      </div>
    </section>

    <section class="section" id="publications">
      <h2 class="section-title">Publications (${publications.length})</h2>
      <div class="card">
        <table>
          <thead>
            <tr><th>PMID</th><th>Title</th><th>Authors</th><th>Journal</th><th>Year</th></tr>
          </thead>
          <tbody>
            ${pubRows || '<tr><td colspan="5" style="color:#94a3b8;">No publications found</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section" id="authors">
      <h2 class="section-title">Top Authors (${kols.length})</h2>
      <p style="color:#94a3b8;margin-bottom:15px;font-size:0.9rem;">Authors ranked by publication count from PubMed search results</p>
      <div class="card">
        <table>
          <thead>
            <tr><th>Name</th><th>Institution</th><th>Publications</th><th>First Author</th><th>Last Author</th><th>Status</th></tr>
          </thead>
          <tbody>
            ${authorRows || '<tr><td colspan="6" style="color:#94a3b8;">No authors found in publications</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      <div>Helix Intelligence Platform</div>
      <div>Data: ClinicalTrials.gov, PubMed, SEC EDGAR, FDA Orange Book</div>
    </footer>
  </div>
</body>
</html>`;
}
//# sourceMappingURL=serve.js.map