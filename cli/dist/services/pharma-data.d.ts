/**
 * Pharma Data Service
 *
 * Proof-of-concept data for Merck (MRK) based on JPM 2026 presentation.
 * Provides pharma profile lookups, pipeline comparisons, BD fit analysis,
 * and catalyst tracking.
 */
import { PharmaProfile, Catalyst, PipelineStats } from '../types/pharma';
/**
 * Get full pharma profile for a given ticker.
 * Currently only Merck (MRK) has proof-of-concept data.
 */
export declare function getPharmaProfile(ticker: string): PharmaProfile | null;
/**
 * Get summary list of all registered pharma companies
 */
export declare function getAllPharmaSummary(): {
    ticker: string;
    name: string;
    verified: boolean;
    hasData: boolean;
    pipelineCount: number;
}[];
/**
 * Compare pipeline stats between two companies
 */
export declare function comparePipelines(tickerA: string, tickerB: string): {
    companyA: {
        ticker: string;
        name: string;
        stats: PipelineStats;
    };
    companyB: {
        ticker: string;
        name: string;
        stats: PipelineStats;
    };
    overlappingAreas: string[];
} | null;
/**
 * Analyze BD fit: which of a target company's whitespace areas
 * match an asset's therapeutic area?
 */
export declare function analyzeBDFit(targetTicker: string, assetTherapeuticArea: string, assetModality: string): {
    targetCompany: string;
    fitScore: 'high' | 'medium' | 'low' | 'unknown';
    rationale: string[];
} | null;
/**
 * Get upcoming catalysts across all companies (or for a specific ticker)
 */
export declare function getUpcomingCatalysts(ticker?: string): Catalyst[];
//# sourceMappingURL=pharma-data.d.ts.map