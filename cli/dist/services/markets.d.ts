/**
 * Markets Service
 *
 * Extracts market size and growth data from SEC filings,
 * analyst reports, and other sources.
 */
import { Market, Region } from '../types/schema';
/**
 * Get market data for an indication
 * TODO: Implement SEC filing extraction
 * TODO: Add analyst report parsing
 */
export declare function getMarketData(indication: string, region?: Region, year?: number): Promise<Market | null>;
/**
 * Get market projections for an indication
 */
export declare function getMarketProjections(indication: string, startYear: number, endYear: number): Promise<{
    year: number;
    sizeBillion: number;
    source: string;
}[]>;
/**
 * Get market leaders for an indication
 */
export declare function getMarketLeaders(indication: string): Promise<{
    company: string;
    drug: string;
    marketSharePct: number;
    revenueBillion: number;
}[]>;
/**
 * Search SEC filings for market size mentions
 */
export declare function searchFilingsForMarketData(indication: string, options?: {
    formTypes?: string[];
    daysBack?: number;
}): Promise<{
    ticker: string;
    filingDate: string;
    marketSize: number;
    year: number;
    context: string;
}[]>;
/**
 * Extract market size from filing text
 */
export declare function extractMarketSize(text: string): {
    value: number;
    unit: 'billion' | 'million';
    year?: number;
    region?: string;
}[];
/**
 * Extract growth rate from filing text
 */
export declare function extractGrowthRate(text: string): number | null;
/**
 * Extract patient population from text
 */
export declare function extractPatientPopulation(text: string): number | null;
/**
 * Compare market sizes across indications
 */
export declare function compareMarkets(indications: string[]): Promise<{
    indication: string;
    sizeBillion: number;
    growthRate: number;
}[]>;
/**
 * Get largest markets in a therapeutic area
 */
export declare function getLargestMarkets(therapeuticArea: string, limit?: number): Promise<Market[]>;
/**
 * Get fastest growing markets
 */
export declare function getFastestGrowingMarkets(minSizeBillion?: number, limit?: number): Promise<Market[]>;
/**
 * Extract drug revenue from SEC filings
 */
export declare function extractDrugRevenue(ticker: string, drugName: string): Promise<{
    year: number;
    quarter?: number;
    revenueMillion: number;
    growth?: number;
}[]>;
/**
 * Build revenue timeline for a drug
 */
export declare function buildRevenueTimeline(drugName: string): Promise<{
    year: number;
    globalRevenue: number;
    byRegion: Record<Region, number>;
}[]>;
/**
 * Estimate market size using prevalence model
 */
export declare function estimateMarketFromPrevalence(prevalence: number, // Number of patients
treatmentRate: number, // % who receive treatment
annualCostPerPatient: number): number;
/**
 * Project market growth
 */
export declare function projectMarketGrowth(currentSize: number, cagr: number, years: number): {
    year: number;
    size: number;
}[];
/**
 * Normalize indication name for matching
 */
export declare function normalizeIndicationName(indication: string): string;
/**
 * Match indication variations
 */
export declare function matchIndication(query: string, target: string): boolean;
//# sourceMappingURL=markets.d.ts.map