/**
 * Asset Research Engine
 *
 * Intelligent multi-source research for therapeutic target assets.
 * Combines clinical trials, publications, and curated databases
 * to produce comprehensive competitive intelligence.
 */
export interface ResearchedAsset {
    drugName: string;
    codeName?: string;
    genericName?: string;
    aliases: string[];
    target: string;
    modality: string;
    payload?: string;
    owner: string;
    ownerType: 'Big Pharma' | 'Biotech' | 'Chinese Biotech' | 'Academic' | 'Other';
    partner?: string;
    phase: string;
    status: 'Active' | 'Completed' | 'Terminated' | 'On Hold' | 'Unknown';
    leadIndication: string;
    otherIndications: string[];
    trialCount: number;
    trialIds: string[];
    publicationCount: number;
    dealTerms?: string;
    dealDate?: string;
    notes?: string;
    differentiator?: string;
    dataSource: 'Known Database' | 'Clinical Trials' | 'Publications' | 'Multiple';
    confidence: 'High' | 'Medium' | 'Low';
    lastUpdated: string;
}
export interface AssetResearchReport {
    target: string;
    generatedAt: string;
    assets: ResearchedAsset[];
    summary: {
        totalAssets: number;
        byModality: Record<string, number>;
        byPhase: Record<string, number>;
        byOwnerType: Record<string, number>;
        byGeography: Record<string, number>;
    };
    knownAssetsFound: number;
    newAssetsDiscovered: number;
    excludedDrugs: number;
}
/**
 * Research all assets for a therapeutic target
 */
export declare function researchTargetAssets(target: string): Promise<AssetResearchReport>;
export declare function formatAssetForDisplay(asset: ResearchedAsset): {
    drugName: string;
    modality: string;
    target: string;
    payload: string;
    owner: string;
    partner: string;
    phase: string;
    status: string;
    leadIndication: string;
    dealTerms: string;
    notes: string;
    confidence: string;
    trialCount: number;
};
//# sourceMappingURL=asset-research.d.ts.map