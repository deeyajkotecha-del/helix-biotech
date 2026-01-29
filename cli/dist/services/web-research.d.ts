/**
 * Comprehensive Web Research Engine
 *
 * Multi-source research methodology for therapeutic target discovery.
 * Replicates Claude Co-work's comprehensive research approach.
 *
 * NOTE: Live web search is not yet implemented. Currently, this module
 * provides the framework and falls back to curated database + trials.
 */
import { VerifiedAsset } from './asset-research';
export interface WebSearchResult {
    title: string;
    snippet: string;
    url: string;
    source: string;
}
export interface DrugCandidate {
    name: string;
    source: 'web_search' | 'clinical_trials' | 'curated' | 'company_pipeline';
    context: string;
    confidence: number;
}
export interface VerifiedDrugInfo {
    name: string;
    confirmedTarget: string;
    matchesExpected: boolean;
    sources: string[];
    phase: string;
    owner: string;
    modality: string;
    indications: string[];
    dealInfo?: string;
}
export interface ComprehensiveResearchResult {
    target: string;
    methodology: string;
    searchesPerformed: string[];
    curatedAssets: VerifiedAsset[];
    discoveredAssets: VerifiedAsset[];
    unverifiedCandidates: DrugCandidate[];
    summary: {
        totalVerified: number;
        totalUnverified: number;
        coverageLevel: 'comprehensive' | 'limited' | 'minimal';
        dataQualityNote: string;
    };
    generatedAt: string;
}
/**
 * Comprehensive target research using multi-source methodology.
 *
 * Current implementation:
 * 1. Uses curated database (known-assets.ts) for verified data
 * 2. Uses clinical trials discovery for additional candidates
 * 3. Logs what web searches WOULD be performed
 *
 * Future implementation will add live web search.
 */
export declare function comprehensiveTargetResearch(target: string): Promise<ComprehensiveResearchResult>;
/**
 * Extract potential drug names from search result text.
 * Uses patterns common in drug naming.
 */
export declare function extractDrugNames(text: string): string[];
/**
 * Get a user-facing message about data coverage for a target
 */
export declare function getResearchStatusMessage(target: string): {
    hasComprehensiveData: boolean;
    message: string;
    callToAction?: string;
};
//# sourceMappingURL=web-research.d.ts.map