/**
 * AI Research Agent
 *
 * Uses Claude API with web search to automatically discover and verify
 * drug assets for any therapeutic target. Provides the same research
 * capability as Claude Co-work but automated.
 */
import { KnownAsset } from '../data/known-assets';
export interface DiscoveredAsset {
    name: string;
    codeNames: string[];
    genericName?: string;
    target: string;
    modality: string;
    mechanism?: string;
    owner: string;
    ownerType?: string;
    partner?: string;
    phase: string;
    status: string;
    leadIndication: string;
    otherIndications?: string[];
    keyData?: string;
    trialIds?: string[];
    deal?: {
        partner?: string;
        value?: string;
        upfront?: number;
        milestones?: number;
        date?: string;
    };
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    sources: string[];
    verificationNotes?: string;
}
export interface ResearchResult {
    target: string;
    assets: DiscoveredAsset[];
    researchedAt: string;
    searchQueries: string[];
    totalSourcesChecked: number;
    dataSource: 'ai-research';
}
/**
 * Research a therapeutic target using Claude with web search
 */
export declare function researchTarget(target: string): Promise<ResearchResult>;
/**
 * Convert discovered assets to KnownAsset format for report compatibility
 */
export declare function convertToKnownAssets(discovered: DiscoveredAsset[]): KnownAsset[];
//# sourceMappingURL=ai-research-agent.d.ts.map