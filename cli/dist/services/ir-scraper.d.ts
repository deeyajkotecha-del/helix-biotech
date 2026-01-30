/**
 * IR Scraper Service
 *
 * Scrapes investor relations pages to discover presentations,
 * SEC filings, and other investor documents.
 */
export interface IRDocument {
    id: string;
    title: string;
    url: string;
    date: string;
    dateObj: Date;
    type: 'presentation' | 'poster' | 'sec-filing' | 'webcast' | 'other';
    event?: string;
    fileSize?: string;
    fileSizeBytes?: number;
    category?: string;
    downloaded?: boolean;
    extractedText?: boolean;
}
export interface IRScraperResult {
    ticker: string;
    companyName: string;
    irBaseUrl: string;
    documents: IRDocument[];
    scrapedAt: string;
    totalDocuments: number;
    documentsByYear: Record<string, number>;
}
/**
 * Scrape all IR documents for a company
 */
export declare function scrapeIRDocuments(ticker: string): Promise<IRScraperResult>;
/**
 * Get list of supported tickers
 */
export declare function getSupportedTickers(): string[];
/**
 * Check if a ticker is supported
 */
export declare function isTickerSupported(ticker: string): boolean;
//# sourceMappingURL=ir-scraper.d.ts.map