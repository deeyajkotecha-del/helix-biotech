/**
 * Assets Service
 *
 * Extracts and deduplicates drug/asset information from clinical trial data.
 * Identifies company sponsors, modalities, and development phases.
 */
import { Trial } from '../types/schema';
export interface Asset {
    name: string;
    genericName?: string;
    company: string;
    companyType: 'Industry' | 'Academic' | 'Government' | 'Other';
    modality: string;
    phase: string;
    indications: string[];
    trialCount: number;
    trialIds: string[];
    status: 'Active' | 'Completed' | 'Terminated' | 'Mixed';
    partners: string[];
    firstTrialDate?: string;
    latestTrialDate?: string;
}
/**
 * Extract assets from clinical trials
 */
export declare function extractAssetsFromTrials(trials: Trial[]): Asset[];
/**
 * Filter assets by modality
 */
export declare function filterAssetsByModality(assets: Asset[], modality: string): Asset[];
/**
 * Filter assets by company type
 */
export declare function filterAssetsByCompanyType(assets: Asset[], type: Asset['companyType']): Asset[];
/**
 * Get asset summary statistics
 */
export declare function getAssetStats(assets: Asset[]): {
    totalAssets: number;
    byModality: Record<string, number>;
    byPhase: Record<string, number>;
    byCompanyType: Record<string, number>;
    topCompanies: {
        company: string;
        assetCount: number;
    }[];
};
//# sourceMappingURL=assets.d.ts.map