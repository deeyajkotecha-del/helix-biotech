"use strict";
/**
 * PDF Downloader Service
 *
 * Downloads PDF documents from IR sites with caching
 * to avoid re-downloading on subsequent runs.
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
exports.downloadDocument = downloadDocument;
exports.downloadAllDocuments = downloadAllDocuments;
exports.getDownloadedDocuments = getDownloadedDocuments;
exports.getDocumentPath = getDocumentPath;
exports.clearDownloads = clearDownloads;
exports.getCompanyDir = getCompanyDir;
exports.getPresentationsDir = getPresentationsDir;
exports.getExtractedDir = getExtractedDir;
exports.ensureDir = ensureDir;
const axios_1 = __importDefault(require("axios"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
// ============================================
// Configuration
// ============================================
const DATA_DIR = path.join(process.cwd(), 'data', 'companies');
function getCompanyDir(ticker) {
    return path.join(DATA_DIR, ticker.toLowerCase());
}
function getPresentationsDir(ticker) {
    return path.join(getCompanyDir(ticker), 'presentations');
}
function getExtractedDir(ticker) {
    return path.join(getCompanyDir(ticker), 'extracted');
}
// ============================================
// Helper Functions
// ============================================
function ensureDir(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
    }
}
function sanitizeFilename(name) {
    return name
        .replace(/[<>:"/\\|?*]/g, '-')
        .replace(/\s+/g, '_')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
        .slice(0, 100);
}
function getFilePath(ticker, doc) {
    const dir = getPresentationsDir(ticker);
    const filename = `${sanitizeFilename(doc.id)}.pdf`;
    return path.join(dir, filename);
}
// ============================================
// Download Functions
// ============================================
/**
 * Download a single PDF document
 */
async function downloadDocument(ticker, doc, options = {}) {
    const filePath = getFilePath(ticker, doc);
    const dir = path.dirname(filePath);
    ensureDir(dir);
    // Check if already downloaded
    if (!options.force && fs.existsSync(filePath)) {
        const stats = fs.statSync(filePath);
        console.log(`[PDF Downloader] Cached: ${doc.title} (${Math.round(stats.size / 1024)} KB)`);
        return {
            documentId: doc.id,
            success: true,
            filePath,
            fileSize: stats.size,
            cached: true,
        };
    }
    try {
        console.log(`[PDF Downloader] Downloading: ${doc.title}`);
        const response = await axios_1.default.get(doc.url, {
            responseType: 'arraybuffer',
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; SatyaBio/1.0; +https://satyabio.com)',
                'Accept': 'application/pdf,*/*',
            },
            timeout: 120000, // 2 minute timeout for large files
            maxRedirects: 5,
        });
        // Verify it's a PDF
        const contentType = response.headers['content-type'] || '';
        if (!contentType.includes('pdf') && !contentType.includes('octet-stream')) {
            console.warn(`[PDF Downloader] Warning: Unexpected content type for ${doc.title}: ${contentType}`);
        }
        // Write to file
        fs.writeFileSync(filePath, response.data);
        const stats = fs.statSync(filePath);
        console.log(`[PDF Downloader] Downloaded: ${doc.title} (${Math.round(stats.size / 1024)} KB)`);
        return {
            documentId: doc.id,
            success: true,
            filePath,
            fileSize: stats.size,
            cached: false,
        };
    }
    catch (error) {
        console.error(`[PDF Downloader] Failed: ${doc.title} - ${error.message}`);
        return {
            documentId: doc.id,
            success: false,
            cached: false,
            error: error.message,
        };
    }
}
/**
 * Download all PDF documents for a company
 */
async function downloadAllDocuments(ticker, documents, options = {}) {
    const { force = false, concurrency = 3, priorityTypes = ['presentation', 'poster'], maxDocuments = 50, } = options;
    console.log(`[PDF Downloader] Starting batch download for ${ticker}: ${documents.length} documents`);
    // Filter to PDFs only and prioritize
    let pdfDocs = documents.filter(d => d.url.includes('/static-files/') ||
        d.url.endsWith('.pdf'));
    // Sort by priority
    pdfDocs.sort((a, b) => {
        const aPriority = priorityTypes.includes(a.type) ? 0 : 1;
        const bPriority = priorityTypes.includes(b.type) ? 0 : 1;
        if (aPriority !== bPriority)
            return aPriority - bPriority;
        return b.dateObj.getTime() - a.dateObj.getTime();
    });
    // Limit number of documents
    pdfDocs = pdfDocs.slice(0, maxDocuments);
    const results = [];
    let downloaded = 0;
    let cached = 0;
    let failed = 0;
    // Download in batches
    for (let i = 0; i < pdfDocs.length; i += concurrency) {
        const batch = pdfDocs.slice(i, i + concurrency);
        const batchResults = await Promise.all(batch.map(doc => downloadDocument(ticker, doc, { force })));
        for (const result of batchResults) {
            results.push(result);
            if (result.success) {
                if (result.cached)
                    cached++;
                else
                    downloaded++;
            }
            else {
                failed++;
            }
        }
        // Rate limiting between batches
        if (i + concurrency < pdfDocs.length) {
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    console.log(`[PDF Downloader] Batch complete: ${downloaded} downloaded, ${cached} cached, ${failed} failed`);
    return {
        ticker: ticker.toUpperCase(),
        totalDocuments: pdfDocs.length,
        downloaded,
        cached,
        failed,
        results,
        downloadedAt: new Date().toISOString(),
    };
}
/**
 * Get list of downloaded documents for a company
 */
function getDownloadedDocuments(ticker) {
    const dir = getPresentationsDir(ticker);
    if (!fs.existsSync(dir))
        return [];
    return fs.readdirSync(dir)
        .filter(f => f.endsWith('.pdf'))
        .map(f => path.join(dir, f));
}
/**
 * Get the file path for a document
 */
function getDocumentPath(ticker, documentId) {
    const dir = getPresentationsDir(ticker);
    const filePath = path.join(dir, `${sanitizeFilename(documentId)}.pdf`);
    return fs.existsSync(filePath) ? filePath : null;
}
/**
 * Delete all downloaded documents for a company
 */
function clearDownloads(ticker) {
    const dir = getCompanyDir(ticker);
    if (fs.existsSync(dir)) {
        fs.rmSync(dir, { recursive: true, force: true });
        console.log(`[PDF Downloader] Cleared all data for ${ticker}`);
    }
}
//# sourceMappingURL=pdf-downloader.js.map