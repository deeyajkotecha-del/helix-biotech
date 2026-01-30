"use strict";
/**
 * IR Scraper Service
 *
 * Scrapes investor relations pages to discover presentations,
 * SEC filings, and other investor documents.
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
exports.scrapeIRDocuments = scrapeIRDocuments;
exports.getSupportedTickers = getSupportedTickers;
exports.isTickerSupported = isTickerSupported;
const axios_1 = __importDefault(require("axios"));
const cheerio = __importStar(require("cheerio"));
const IR_CONFIGS = {
    ARWR: {
        baseUrl: 'https://ir.arrowheadpharma.com',
        eventsPath: '/events-and-presentations',
        downloadLibraryPath: '/download-library',
        secFilingsPath: '/financials-filings',
        newsPath: 'https://arrowheadpharma.com/newsroom/',
    },
    // Add more companies as needed
};
// ============================================
// Helper Functions
// ============================================
function parseFileSize(sizeStr) {
    if (!sizeStr)
        return 0;
    const match = sizeStr.match(/([\d.]+)\s*(KB|MB|GB)/i);
    if (!match)
        return 0;
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase();
    switch (unit) {
        case 'KB': return value * 1024;
        case 'MB': return value * 1024 * 1024;
        case 'GB': return value * 1024 * 1024 * 1024;
        default: return 0;
    }
}
function parseDate(dateStr) {
    // Handle various date formats
    const cleaned = dateStr.trim().replace(/,/g, '');
    const date = new Date(cleaned);
    if (!isNaN(date.getTime()))
        return date;
    // Try parsing formats like "Apr 15, 2025"
    const months = {
        jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
        jul: 6, aug: 7, sep: 8, sept: 8, oct: 9, nov: 10, dec: 11
    };
    const match = cleaned.match(/(\w+)\s+(\d+)\s+(\d{4})/i);
    if (match) {
        const month = months[match[1].toLowerCase().slice(0, 3)];
        if (month !== undefined) {
            return new Date(parseInt(match[3]), month, parseInt(match[2]));
        }
    }
    return new Date();
}
function inferDocumentType(title, url) {
    const titleLower = title.toLowerCase();
    const urlLower = url.toLowerCase();
    if (titleLower.includes('poster') || urlLower.includes('poster'))
        return 'poster';
    if (titleLower.includes('webcast') || urlLower.includes('webcast'))
        return 'webcast';
    if (titleLower.includes('10-k') || titleLower.includes('10-q') || titleLower.includes('8-k'))
        return 'sec-filing';
    if (titleLower.includes('presentation') || titleLower.includes('corporate') ||
        titleLower.includes('conference') || titleLower.includes('congress') ||
        titleLower.includes('study') || titleLower.includes('data'))
        return 'presentation';
    return 'other';
}
function generateDocumentId(url, title) {
    // Extract UUID from static-files URL or generate from title
    const uuidMatch = url.match(/static-files\/([a-f0-9-]+)/i);
    if (uuidMatch)
        return uuidMatch[1];
    // Generate from title
    return title.toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .slice(0, 50);
}
// ============================================
// Scraping Functions
// ============================================
/**
 * Scrape the download library page for documents
 */
async function scrapeDownloadLibrary(config) {
    const documents = [];
    if (!config.downloadLibraryPath)
        return documents;
    let page = 1;
    let hasMore = true;
    while (hasMore && page <= 10) { // Max 10 pages
        try {
            const url = `${config.baseUrl}${config.downloadLibraryPath}${page > 1 ? `?page=${page}` : ''}`;
            console.log(`[IR Scraper] Fetching download library page ${page}: ${url}`);
            const response = await axios_1.default.get(url, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (compatible; SatyaBio/1.0; +https://satyabio.com)',
                },
                timeout: 30000,
            });
            const $ = cheerio.load(response.data);
            let foundDocs = 0;
            // Look for download links
            $('a[href*="/static-files/"]').each((_, el) => {
                const href = $(el).attr('href') || '';
                const fullUrl = href.startsWith('http') ? href : `${config.baseUrl}${href}`;
                // Get the text content and surrounding context
                let title = $(el).text().trim();
                // Look for title in parent elements
                if (!title || title.length < 3) {
                    title = $(el).closest('tr, .download-item, .document-item, li')
                        .find('td:first, .title, .name, h3, h4')
                        .first()
                        .text()
                        .trim();
                }
                // Look for date
                let dateStr = '';
                const row = $(el).closest('tr, .download-item, .document-item, li');
                row.find('td, .date, time').each((_, dateEl) => {
                    const text = $(dateEl).text().trim();
                    if (/\d{4}/.test(text) && text.length < 30) {
                        dateStr = text;
                        return false;
                    }
                });
                // Look for file size
                let fileSize = '';
                row.find('td, .size, .file-size').each((_, sizeEl) => {
                    const text = $(sizeEl).text().trim();
                    if (/\d+\s*(KB|MB|GB)/i.test(text)) {
                        fileSize = text;
                        return false;
                    }
                });
                if (title && fullUrl.includes('/static-files/')) {
                    foundDocs++;
                    documents.push({
                        id: generateDocumentId(fullUrl, title),
                        title,
                        url: fullUrl,
                        date: dateStr || 'Unknown',
                        dateObj: parseDate(dateStr),
                        type: inferDocumentType(title, fullUrl),
                        fileSize,
                        fileSizeBytes: parseFileSize(fileSize),
                        category: 'download-library',
                    });
                }
            });
            console.log(`[IR Scraper] Found ${foundDocs} documents on page ${page}`);
            // Check for next page
            hasMore = foundDocs > 0 && $('a[href*="page="]').length > 0;
            page++;
            // Rate limiting
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        catch (error) {
            console.error(`[IR Scraper] Error scraping page ${page}:`, error.message);
            hasMore = false;
        }
    }
    return documents;
}
/**
 * Scrape the events and presentations page
 */
async function scrapeEventsPage(config) {
    const documents = [];
    try {
        const url = `${config.baseUrl}${config.eventsPath}`;
        console.log(`[IR Scraper] Fetching events page: ${url}`);
        const response = await axios_1.default.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; SatyaBio/1.0; +https://satyabio.com)',
            },
            timeout: 30000,
        });
        const $ = cheerio.load(response.data);
        // Look for PDF links
        $('a[href*=".pdf"], a[href*="/static-files/"]').each((_, el) => {
            const href = $(el).attr('href') || '';
            const fullUrl = href.startsWith('http') ? href : `${config.baseUrl}${href}`;
            let title = $(el).text().trim();
            if (!title || title.length < 3) {
                title = $(el).attr('title') || $(el).attr('aria-label') || 'Untitled';
            }
            // Get date from parent
            let dateStr = '';
            const parent = $(el).closest('.event-item, .presentation-item, tr, li, article');
            parent.find('.date, time, .event-date').each((_, dateEl) => {
                const text = $(dateEl).text().trim();
                if (/\d{4}/.test(text)) {
                    dateStr = text;
                    return false;
                }
            });
            // Get event name
            let event = '';
            parent.find('.event-name, .event-title, h3, h4').each((_, eventEl) => {
                const text = $(eventEl).text().trim();
                if (text && text !== title) {
                    event = text;
                    return false;
                }
            });
            if (fullUrl && !documents.some(d => d.url === fullUrl)) {
                documents.push({
                    id: generateDocumentId(fullUrl, title),
                    title,
                    url: fullUrl,
                    date: dateStr || 'Unknown',
                    dateObj: parseDate(dateStr),
                    type: inferDocumentType(title, fullUrl),
                    event,
                    category: 'events',
                });
            }
        });
        console.log(`[IR Scraper] Found ${documents.length} documents on events page`);
    }
    catch (error) {
        console.error('[IR Scraper] Error scraping events page:', error.message);
    }
    return documents;
}
// ============================================
// Main Scraper Function
// ============================================
/**
 * Scrape all IR documents for a company
 */
async function scrapeIRDocuments(ticker) {
    const config = IR_CONFIGS[ticker.toUpperCase()];
    if (!config) {
        throw new Error(`No IR configuration found for ticker: ${ticker}`);
    }
    console.log(`[IR Scraper] Starting scrape for ${ticker}...`);
    // Scrape all sources
    const [downloadDocs, eventDocs] = await Promise.all([
        scrapeDownloadLibrary(config),
        scrapeEventsPage(config),
    ]);
    // Merge and dedupe
    const allDocs = [...downloadDocs, ...eventDocs];
    const uniqueDocs = new Map();
    for (const doc of allDocs) {
        const existing = uniqueDocs.get(doc.id);
        if (!existing || doc.fileSize) {
            uniqueDocs.set(doc.id, doc);
        }
    }
    const documents = Array.from(uniqueDocs.values())
        .sort((a, b) => b.dateObj.getTime() - a.dateObj.getTime());
    // Calculate stats
    const documentsByYear = {};
    for (const doc of documents) {
        const year = doc.dateObj.getFullYear().toString();
        documentsByYear[year] = (documentsByYear[year] || 0) + 1;
    }
    console.log(`[IR Scraper] Completed scrape for ${ticker}: ${documents.length} unique documents`);
    return {
        ticker: ticker.toUpperCase(),
        companyName: getCompanyName(ticker),
        irBaseUrl: config.baseUrl,
        documents,
        scrapedAt: new Date().toISOString(),
        totalDocuments: documents.length,
        documentsByYear,
    };
}
/**
 * Get company name from ticker
 */
function getCompanyName(ticker) {
    const names = {
        ARWR: 'Arrowhead Pharmaceuticals',
    };
    return names[ticker.toUpperCase()] || ticker;
}
/**
 * Get list of supported tickers
 */
function getSupportedTickers() {
    return Object.keys(IR_CONFIGS);
}
/**
 * Check if a ticker is supported
 */
function isTickerSupported(ticker) {
    return ticker.toUpperCase() in IR_CONFIGS;
}
//# sourceMappingURL=ir-scraper.js.map