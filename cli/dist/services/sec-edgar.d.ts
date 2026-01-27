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
import { Filing, SECSubmission } from '../types';
/**
 * Look up a company's CIK number from their ticker symbol
 *
 * The SEC provides a JSON file mapping all tickers to CIKs:
 * https://www.sec.gov/files/company_tickers.json
 */
export declare function getCIKFromTicker(ticker: string): Promise<string | null>;
/**
 * Fetch all filings for a company from SEC EDGAR
 * Uses the fast JSON metadata endpoint: https://data.sec.gov/submissions/CIK{cik}.json
 * Returns the raw submission data from SEC
 */
export declare function getCompanySubmissions(cik: string): Promise<SECSubmission>;
/**
 * Get 10-K and 10-Q filings for a company by ticker
 *
 * 10-K = Annual report (comprehensive, includes audited financials)
 * 10-Q = Quarterly report (3 per year, unaudited)
 */
export declare function getFilings(ticker: string, limit?: number): Promise<Filing[]>;
/**
 * Fetch the actual content of a filing document
 * Returns the HTML content of the filing (limited to 500KB)
 *
 * Note: SEC filings can be 1-10MB. We download with a size limit
 * and truncate to avoid hanging on large files.
 */
export declare function getFilingContent(filing: Filing): Promise<string>;
/**
 * Extract plain text from HTML filing content using cheerio
 *
 * SEC filings contain lots of XBRL tags (<ix:*, <xbrli:*>) that we need to
 * handle specially - we want their inner text but not the tags themselves.
 */
export declare function extractTextFromHtml(html: string): string;
/**
 * Get filing content ready for AI analysis
 * Fetches the filing and extracts clean text
 */
export declare function getFilingForAnalysis(filing: Filing, maxLength?: number): Promise<string>;
//# sourceMappingURL=sec-edgar.d.ts.map