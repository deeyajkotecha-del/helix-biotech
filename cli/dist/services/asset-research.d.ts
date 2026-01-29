/**
 * Asset Research Engine - Multi-Layer Verification
 *
 * Discovers and verifies therapeutic assets for any target.
 * Uses strict multi-layer filtering to prevent false positives.
 *
 * PRINCIPLE: Accuracy over completeness.
 * Better to miss a real asset than to include a false one.
 */
import { TargetInfo } from '../data/target-aliases';
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'EXCLUDE';
export interface VerifiedAsset {
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
    confidence: ConfidenceLevel;
    verificationMethod: 'curated_database' | 'name_match' | 'mechanism_match' | 'trial_association';
    verificationDetails?: string;
    notes?: string;
    differentiator?: string;
    lastUpdated: string;
}
export interface AssetDiscoveryResult {
    target: string;
    targetInfo: TargetInfo;
    generatedAt: string;
    verified: VerifiedAsset[];
    probable: VerifiedAsset[];
    unverified: VerifiedAsset[];
    summary: {
        totalVerified: number;
        totalProbable: number;
        totalUnverified: number;
        totalExcluded: number;
        byModality: Record<string, number>;
        byPhase: Record<string, number>;
    };
}
/**
 * Discover and verify assets for a therapeutic target.
 * Uses multi-layer filtering to ensure accuracy.
 */
export declare function discoverAssets(target: string): Promise<AssetDiscoveryResult>;
export interface ResearchedAsset extends VerifiedAsset {
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
 * Legacy function for backwards compatibility
 */
export declare function researchTargetAssets(target: string): Promise<AssetResearchReport>;
/**
 * Format asset for display (legacy)
 */
export declare function formatAssetForDisplay(asset: VerifiedAsset): {
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