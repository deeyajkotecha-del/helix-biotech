/**
 * PDF Downloader Service
 *
 * Downloads PDF documents from IR sites with caching
 * to avoid re-downloading on subsequent runs.
 */
import { IRDocument } from './ir-scraper';
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
declare function getCompanyDir(ticker: string): string;
declare function getPresentationsDir(ticker: string): string;
declare function getExtractedDir(ticker: string): string;
declare function ensureDir(dirPath: string): void;
/**
 * Download a single PDF document
 */
export declare function downloadDocument(ticker: string, doc: IRDocument, options?: {
    force?: boolean;
}): Promise<DownloadResult>;
/**
 * Download all PDF documents for a company
 */
export declare function downloadAllDocuments(ticker: string, documents: IRDocument[], options?: {
    force?: boolean;
    concurrency?: number;
    priorityTypes?: string[];
    maxDocuments?: number;
}): Promise<BatchDownloadResult>;
/**
 * Get list of downloaded documents for a company
 */
export declare function getDownloadedDocuments(ticker: string): string[];
/**
 * Get the file path for a document
 */
export declare function getDocumentPath(ticker: string, documentId: string): string | null;
/**
 * Delete all downloaded documents for a company
 */
export declare function clearDownloads(ticker: string): void;
export { getCompanyDir, getPresentationsDir, getExtractedDir, ensureDir };
//# sourceMappingURL=pdf-downloader.d.ts.map