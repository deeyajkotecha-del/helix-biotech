"use strict";
/**
 * SEC EDGAR Service
 *
 * Fetches company filings from the SEC's free EDGAR API.
 *
 * How SEC EDGAR works:
 * 1. Every company has a CIK (Central Index Key) - like an ID number
 * 2. We use the ticker to look up the CIK from SEC's mapping
 * 3. Then we fetch filings using: https://data.sec.gov/submissions/CIK{cik}.json
 *
 * Important: SEC requires a User-Agent header with your email (it's free, just for abuse prevention)
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
exports.getCIKFromTicker = getCIKFromTicker;
exports.getCompanySubmissions = getCompanySubmissions;
exports.getFilings = getFilings;
exports.getFilingContent = getFilingContent;
exports.extractTextFromHtml = extractTextFromHtml;
exports.getFilingForAnalysis = getFilingForAnalysis;
const axios_1 = __importDefault(require("axios"));
const cheerio = __importStar(require("cheerio"));
const config_1 = require("../config");
// SEC API base URLs
// - data.sec.gov is for JSON API endpoints (submissions, company_tickers)
// - www.sec.gov is for actual filing documents (Archives)
const SEC_API_URL = 'https://data.sec.gov';
const SEC_ARCHIVES_URL = 'https://www.sec.gov';
// Request timeouts
const METADATA_TIMEOUT = 15000; // 15 seconds for metadata requests
const FILING_TIMEOUT = 30000; // 30 seconds for filing downloads
// Size limits
const MAX_FILING_SIZE = 500000; // 500KB max download
const MAX_OUTPUT_CHARS = 50000; // 50K chars max output (faster LLM response)
// Cache for ticker -> CIK mappings (to avoid repeated lookups)
const cikCache = new Map();
/**
 * Get SEC API headers with required User-Agent
 * SEC requires format: "User-Agent: CompanyName contact@email.com"
 */
function getSecHeaders() {
    const config = (0, config_1.getConfig)();
    return {
        'User-Agent': config.secUserAgent,
        'Accept': 'application/json',
    };
}
/**
 * Format error messages for user display
 */
function formatError(error, context, timeoutMs) {
    if (axios_1.default.isAxiosError(error)) {
        const axiosError = error;
        if (axiosError.code === 'ECONNABORTED' || axiosError.code === 'ETIMEDOUT') {
            const timeout = timeoutMs ? timeoutMs / 1000 : 30;
            return new Error(`${context}: Request timed out after ${timeout}s. SEC servers may be slow - try again.`);
        }
        if (axiosError.response) {
            const status = axiosError.response.status;
            if (status === 403) {
                return new Error(`${context}: SEC blocked request (403). Check User-Agent format.`);
            }
            if (status === 404) {
                return new Error(`${context}: Not found (404).`);
            }
            if (status >= 500) {
                return new Error(`${context}: SEC server error (${status}). Try again later.`);
            }
            return new Error(`${context}: HTTP ${status}`);
        }
        if (axiosError.code === 'ENOTFOUND') {
            return new Error(`${context}: Network error. Check your internet connection.`);
        }
        return new Error(`${context}: ${axiosError.message}`);
    }
    return new Error(`${context}: ${error instanceof Error ? error.message : 'Unknown error'}`);
}
/**
 * Sleep function to respect SEC rate limits (10 requests/second max)
 */
async function rateLimitDelay() {
    await new Promise(resolve => setTimeout(resolve, 100)); // 100ms between requests
}
/**
 * Look up a company's CIK number from their ticker symbol
 *
 * The SEC provides a JSON file mapping all tickers to CIKs:
 * https://www.sec.gov/files/company_tickers.json
 */
async function getCIKFromTicker(ticker) {
    const tickerUpper = ticker.toUpperCase();
    // Check cache first
    if (cikCache.has(tickerUpper)) {
        return cikCache.get(tickerUpper);
    }
    try {
        await rateLimitDelay();
        // Fetch the SEC's ticker -> CIK mapping
        const response = await axios_1.default.get('https://www.sec.gov/files/company_tickers.json', {
            headers: getSecHeaders(),
            timeout: METADATA_TIMEOUT,
        });
        // Find our ticker in the response
        // The response is an object with numeric keys, each containing { cik_str, ticker, title }
        for (const key of Object.keys(response.data)) {
            const company = response.data[key];
            if (company.ticker.toUpperCase() === tickerUpper) {
                // CIK needs to be padded to 10 digits with leading zeros
                const cik = company.cik_str.toString().padStart(10, '0');
                cikCache.set(tickerUpper, cik);
                return cik;
            }
        }
        return null;
    }
    catch (error) {
        throw formatError(error, `Failed to look up CIK for ${ticker}`);
    }
}
/**
 * Fetch all filings for a company from SEC EDGAR
 * Uses the fast JSON metadata endpoint: https://data.sec.gov/submissions/CIK{cik}.json
 * Returns the raw submission data from SEC
 */
async function getCompanySubmissions(cik) {
    await rateLimitDelay();
    const url = `${SEC_API_URL}/submissions/CIK${cik}.json`;
    try {
        const response = await axios_1.default.get(url, {
            headers: getSecHeaders(),
            timeout: METADATA_TIMEOUT,
        });
        return response.data;
    }
    catch (error) {
        throw formatError(error, `Failed to fetch filings for CIK ${cik}`, METADATA_TIMEOUT);
    }
}
/**
 * Get 10-K and 10-Q filings for a company by ticker
 *
 * 10-K = Annual report (comprehensive, includes audited financials)
 * 10-Q = Quarterly report (3 per year, unaudited)
 */
async function getFilings(ticker, limit = 5) {
    // Step 1: Get the CIK for this ticker
    const cik = await getCIKFromTicker(ticker);
    if (!cik) {
        throw new Error(`Could not find CIK for ticker: ${ticker}`);
    }
    // Step 2: Fetch the company's submission history
    const submissions = await getCompanySubmissions(cik);
    // Step 3: Extract 10-K and 10-Q filings from the recent filings array
    const filings = [];
    const recent = submissions.filings.recent;
    for (let i = 0; i < recent.accessionNumber.length && filings.length < limit; i++) {
        const form = recent.form[i];
        // Only include 10-K (annual) and 10-Q (quarterly) filings
        if (form === '10-K' || form === '10-Q' || form === '10-K/A' || form === '10-Q/A') {
            const accessionNumber = recent.accessionNumber[i];
            // Accession number format: 0001234567-23-000001, need to remove dashes for URL
            const accessionNoFormatted = accessionNumber.replace(/-/g, '');
            filings.push({
                accessionNumber,
                filingDate: recent.filingDate[i],
                reportDate: recent.reportDate[i],
                form,
                primaryDocument: recent.primaryDocument[i],
                // Build the full URL to the filing document (uses www.sec.gov for archives)
                fileUrl: `${SEC_ARCHIVES_URL}/Archives/edgar/data/${cik.replace(/^0+/, '')}/${accessionNoFormatted}/${recent.primaryDocument[i]}`
            });
        }
    }
    return filings;
}
/**
 * Fetch the actual content of a filing document
 * Returns the HTML content of the filing (limited to 500KB)
 *
 * Note: SEC filings can be 1-10MB. We download with a size limit
 * and truncate to avoid hanging on large files.
 */
async function getFilingContent(filing) {
    await rateLimitDelay();
    console.log('Downloading filing (max 500KB)...');
    try {
        // Use stream to stop downloading after reaching our limit
        const response = await axios_1.default.get(filing.fileUrl, {
            headers: getSecHeaders(),
            responseType: 'stream',
            timeout: FILING_TIMEOUT,
        });
        const stream = response.data;
        // Collect data up to our limit
        return new Promise((resolve, reject) => {
            let data = '';
            let done = false;
            stream.on('data', (chunk) => {
                if (done)
                    return;
                data += chunk.toString('utf-8');
                if (data.length >= MAX_FILING_SIZE) {
                    done = true;
                    // Cast to any to access destroy() which exists on Node streams
                    stream.destroy();
                    console.log(`Downloaded ${(MAX_FILING_SIZE / 1024).toFixed(0)}KB (truncated)`);
                    resolve(data.substring(0, MAX_FILING_SIZE));
                }
            });
            stream.on('end', () => {
                if (!done) {
                    console.log(`Downloaded ${(data.length / 1024).toFixed(0)}KB`);
                    resolve(data);
                }
            });
            stream.on('error', (err) => {
                if (!done) {
                    reject(err);
                }
            });
        });
    }
    catch (error) {
        throw formatError(error, `Failed to download filing ${filing.form}`, FILING_TIMEOUT);
    }
}
/**
 * Extract plain text from HTML filing content using cheerio
 *
 * SEC filings contain lots of XBRL tags (<ix:*, <xbrli:*>) that we need to
 * handle specially - we want their inner text but not the tags themselves.
 */
function extractTextFromHtml(html) {
    console.log('Parsing HTML...');
    // Load HTML with cheerio
    const $ = cheerio.load(html);
    // Remove elements we don't want at all (including their content)
    $('script, style, head, header, footer, nav, noscript').remove();
    // Remove XBRL metadata sections (ix:header contains context definitions)
    // These appear at the top of inline XBRL filings and aren't readable content
    $('ix\\:header, [style*="display:none"], [style*="display: none"]').remove();
    // Remove hidden div elements (often used for XBRL context data)
    $('div[style*="display:none"], div[style*="display: none"]').remove();
    // For XBRL tags, we want to keep the inner text but remove the tag structure
    // These are inline tags like <ix:nonFraction>, <ix:nonNumeric>, etc.
    // We don't remove them - cheerio's text() will extract their inner content
    // Get just the body text (or full document if no body)
    const body = $('body');
    let text = body.length ? body.text() : $('html').text();
    // Remove XBRL-style prefixed identifiers that leaked through (e.g., "iso4217:USD", "xbrli:shares")
    text = text.replace(/\b[a-z0-9]+:[A-Za-z][A-Za-z0-9]*\b/g, '');
    // Remove long numeric sequences that are XBRL context IDs (e.g., "0001682852")
    text = text.replace(/\b\d{10,}\b/g, '');
    // Collapse multiple whitespace/newlines into single spaces
    text = text.replace(/\s+/g, ' ');
    // Trim
    text = text.trim();
    console.log(`Extracted ${text.length.toLocaleString()} characters of text`);
    return text;
}
/**
 * Get filing content ready for AI analysis
 * Fetches the filing and extracts clean text
 */
async function getFilingForAnalysis(filing, maxLength = MAX_OUTPUT_CHARS) {
    const htmlContent = await getFilingContent(filing);
    let text = extractTextFromHtml(htmlContent);
    // Truncate if too long (LLMs have token limits)
    if (text.length > maxLength) {
        text = text.substring(0, maxLength) + '\n\n[Content truncated for analysis...]';
    }
    return text;
}
//# sourceMappingURL=sec-edgar.js.map