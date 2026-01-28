/**
 * Deals Service
 *
 * Fetches and tracks biopharma deals from RSS feeds,
 * SEC filings, and news sources.
 */
import { Deal, DealType } from '../types/schema';
/**
 * Fetch recent deals from all sources
 * TODO: Implement comprehensive deal extraction
 * TODO: Add SEC 8-K parsing for material agreements
 */
export declare function fetchRecentDeals(options?: {
    daysBack?: number;
    dealTypes?: DealType[];
    companies?: string[];
    conditions?: string[];
}): Promise<Deal[]>;
/**
 * Search deals by company
 */
export declare function searchDealsByCompany(companyName: string): Promise<Deal[]>;
/**
 * Search deals by drug/asset
 */
export declare function searchDealsByAsset(assetName: string): Promise<Deal[]>;
/**
 * Get deals for a therapeutic area
 */
export declare function getDealsByTherapeuticArea(therapeuticArea: string, options?: {
    daysBack?: number;
    dealTypes?: DealType[];
}): Promise<Deal[]>;
/**
 * Get M&A activity summary
 */
export declare function getMAActivity(year: number): Promise<{
    totalDeals: number;
    totalValue: number;
    topDeals: Deal[];
    byMonth: {
        month: string;
        count: number;
        value: number;
    }[];
}>;
/**
 * Fetch and parse RSS feed
 */
export declare function fetchRSSFeed(url: string, source: string): Promise<{
    title: string;
    link: string;
    pubDate: string;
    description: string;
}[]>;
/**
 * Parse RSS XML to extract items
 */
export declare function parseRSSXml(xml: string): {
    title: string;
    link: string;
    pubDate: string;
    description: string;
}[];
/**
 * Extract deal information from news text
 */
export declare function extractDealInfo(title: string, description: string): Partial<Deal>;
/**
 * Detect deal type from text
 */
export declare function extractDealType(text: string): DealType | null;
/**
 * Extract monetary values from text
 */
export declare function extractUpfrontPayment(text: string): number | undefined;
export declare function extractMilestones(text: string): number | undefined;
export declare function extractTotalValue(text: string): number | undefined;
export declare function extractRoyalties(text: string): string | undefined;
/**
 * Extract company names from text
 */
export declare function extractCompanyNames(text: string): string[];
/**
 * Extract asset/drug information
 */
export declare function extractAssetInfo(text: string): Deal['asset'] | undefined;
/**
 * Search SEC 8-K filings for material agreements
 * TODO: Implement SEC EDGAR integration
 */
export declare function searchSECMaterialAgreements(companyName: string, options?: {
    daysBack?: number;
}): Promise<Deal[]>;
//# sourceMappingURL=deals.d.ts.map