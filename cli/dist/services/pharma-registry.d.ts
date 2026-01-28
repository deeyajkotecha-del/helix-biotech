/**
 * Pharma Company Registry
 *
 * Registry of major pharma companies with IR page URLs,
 * presentation URL patterns, and verification status.
 */
import { PharmaCompany } from '../types/pharma';
export declare const PHARMA_COMPANIES: Record<string, PharmaCompany>;
/**
 * Get all registered ticker symbols
 */
export declare function getAllTickers(): string[];
/**
 * Get only companies with verified IR URL patterns
 */
export declare function getVerifiedCompanies(): PharmaCompany[];
/**
 * Build a presentation URL from a company's URL pattern
 */
export declare function buildPresentationUrl(ticker: string, type: 'jpm' | 'quarterly' | 'annual', params: {
    year: number;
    quarter?: number;
}): string | null;
/**
 * Get JPM presentation URLs for a given year across all verified companies
 */
export declare function getJPM2026Urls(): {
    ticker: string;
    name: string;
    url: string | null;
}[];
//# sourceMappingURL=pharma-registry.d.ts.map