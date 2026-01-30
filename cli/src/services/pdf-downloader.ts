/**
 * PDF Downloader Service
 *
 * Downloads PDF documents from IR sites with caching
 * to avoid re-downloading on subsequent runs.
 */

import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';
import { IRDocument } from './ir-scraper';

// ============================================
// Types
// ============================================

export interface DownloadResult {
  documentId: string;
  success: boolean;
  filePath?: string;
  fileSize?: number;
  cached: boolean;
  error?: string;
}

export interface BatchDownloadResult {
  ticker: string;
  totalDocuments: number;
  downloaded: number;
  cached: number;
  failed: number;
  results: DownloadResult[];
  downloadedAt: string;
}

// ============================================
// Configuration
// ============================================

const DATA_DIR = path.join(process.cwd(), 'data', 'companies');

function getCompanyDir(ticker: string): string {
  return path.join(DATA_DIR, ticker.toLowerCase());
}

function getPresentationsDir(ticker: string): string {
  return path.join(getCompanyDir(ticker), 'presentations');
}

function getExtractedDir(ticker: string): string {
  return path.join(getCompanyDir(ticker), 'extracted');
}

// ============================================
// Helper Functions
// ============================================

function ensureDir(dirPath: string): void {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function sanitizeFilename(name: string): string {
  return name
    .replace(/[<>:"/\\|?*]/g, '-')
    .replace(/\s+/g, '_')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 100);
}

function getFilePath(ticker: string, doc: IRDocument): string {
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
export async function downloadDocument(
  ticker: string,
  doc: IRDocument,
  options: { force?: boolean } = {}
): Promise<DownloadResult> {
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

    const response = await axios.get(doc.url, {
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
  } catch (error: any) {
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
export async function downloadAllDocuments(
  ticker: string,
  documents: IRDocument[],
  options: {
    force?: boolean;
    concurrency?: number;
    priorityTypes?: string[];
    maxDocuments?: number;
  } = {}
): Promise<BatchDownloadResult> {
  const {
    force = false,
    concurrency = 3,
    priorityTypes = ['presentation', 'poster'],
    maxDocuments = 50,
  } = options;

  console.log(`[PDF Downloader] Starting batch download for ${ticker}: ${documents.length} documents`);

  // Filter to PDFs only and prioritize
  let pdfDocs = documents.filter(d =>
    d.url.includes('/static-files/') ||
    d.url.endsWith('.pdf')
  );

  // Sort by priority
  pdfDocs.sort((a, b) => {
    const aPriority = priorityTypes.includes(a.type) ? 0 : 1;
    const bPriority = priorityTypes.includes(b.type) ? 0 : 1;
    if (aPriority !== bPriority) return aPriority - bPriority;
    return b.dateObj.getTime() - a.dateObj.getTime();
  });

  // Limit number of documents
  pdfDocs = pdfDocs.slice(0, maxDocuments);

  const results: DownloadResult[] = [];
  let downloaded = 0;
  let cached = 0;
  let failed = 0;

  // Download in batches
  for (let i = 0; i < pdfDocs.length; i += concurrency) {
    const batch = pdfDocs.slice(i, i + concurrency);
    const batchResults = await Promise.all(
      batch.map(doc => downloadDocument(ticker, doc, { force }))
    );

    for (const result of batchResults) {
      results.push(result);
      if (result.success) {
        if (result.cached) cached++;
        else downloaded++;
      } else {
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
export function getDownloadedDocuments(ticker: string): string[] {
  const dir = getPresentationsDir(ticker);
  if (!fs.existsSync(dir)) return [];

  return fs.readdirSync(dir)
    .filter(f => f.endsWith('.pdf'))
    .map(f => path.join(dir, f));
}

/**
 * Get the file path for a document
 */
export function getDocumentPath(ticker: string, documentId: string): string | null {
  const dir = getPresentationsDir(ticker);
  const filePath = path.join(dir, `${sanitizeFilename(documentId)}.pdf`);
  return fs.existsSync(filePath) ? filePath : null;
}

/**
 * Delete all downloaded documents for a company
 */
export function clearDownloads(ticker: string): void {
  const dir = getCompanyDir(ticker);
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(`[PDF Downloader] Cleared all data for ${ticker}`);
  }
}

// Export directory helpers
export { getCompanyDir, getPresentationsDir, getExtractedDir, ensureDir };
