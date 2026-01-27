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
// Cache directory for analysis results
const CACHE_DIR = path.resolve(__dirname, '..', '..', 'cache');
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
    // Health check endpoint
    app.get('/api/health', (_req, res) => {
        res.json({ status: 'ok', timestamp: new Date().toISOString() });
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
                    // Fetch filing content and analyze
                    console.log(chalk_1.default.yellow(`  [API] Running Claude analysis for ${ticker}...`));
                    const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing);
                    const llm = (0, llm_1.getLLMProvider)();
                    analysis = await llm.analyze(content, ticker);
                    // Post-process to fix common LLM issues
                    analysis = postProcessAnalysis(analysis, filing);
                    // Save to cache
                    saveCachedAnalysis(ticker, filing.filingDate, analysis);
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
                console.log(chalk_1.default.yellow(`  [API] Running Claude analysis for ${ticker}...`));
                const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing);
                const llm = (0, llm_1.getLLMProvider)();
                analysis = await llm.analyze(content, ticker);
                analysis = postProcessAnalysis(analysis, filing);
                // Save to cache for next time
                saveCachedAnalysis(ticker, filing.filingDate, analysis);
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
function getCachedAnalysis(ticker) {
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
//# sourceMappingURL=serve.js.map