/**
 * Known Assets Database - Investment Ready
 *
 * Curated database of known drug assets for key targets.
 * Contains complete deal terms, regulatory designations, and clinical data.
 */
export interface RegulatoryDesignations {
    btd: boolean;
    odd: boolean;
    fastTrack: boolean;
    prime: boolean;
    rmat?: boolean;
}
export interface DealTerms {
    upfront?: number;
    equity?: number;
    committed?: number;
    milestones?: number;
    totalPotential?: number;
    headline?: string;
    date?: string;
    partner?: string;
    territory?: string;
    notes?: string;
    source?: string;
    sourceDate?: string;
    hasBreakdown: boolean;
}
export interface KnownAsset {
    primaryName: string;
    codeNames: string[];
    genericName?: string;
    aliases: string[];
    target: string;
    modality: 'ADC' | 'mAb' | 'Bispecific' | 'CAR-T' | 'Radioconjugate' | 'Small Molecule' | 'BiTE' | 'TCE' | 'Vaccine' | 'Other';
    modalityDetail?: string;
    payload?: string;
    owner: string;
    ownerType: 'Big Pharma' | 'Biotech' | 'Chinese Biotech' | 'Academic' | 'Other';
    partner?: string;
    phase: 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2/3' | 'Phase 3' | 'Filed' | 'Approved';
    status: 'Active' | 'Discontinued' | 'On Hold';
    leadIndication: string;
    otherIndications?: string[];
    regulatory: RegulatoryDesignations;
    deal?: DealTerms;
    trialIds: string[];
    keyData?: string;
    notes?: string;
    differentiator?: string;
}
export interface TargetAssetDatabase {
    target: string;
    aliases: string[];
    description: string;
    assets: KnownAsset[];
    excludedDrugs: string[];
    excludedSponsors: string[];
}
export declare const B7H3_DATABASE: TargetAssetDatabase;
export declare const TARGET_DATABASES: Record<string, TargetAssetDatabase>;
export interface InvestmentMetrics {
    totalCommitted: number;
    totalPotential: number;
    totalUpfront: number;
    totalEquity: number;
    totalMilestones: number;
    largestDeal: {
        name: string;
        committed: number;
        potential: number;
        partner?: string;
    };
    assetsWithBTD: number;
    assetsWithODD: number;
    assetsWithPRIME: number;
    assetsWithFastTrack: number;
    phaseDistribution: Record<string, number>;
    modalityBreakdown: Record<string, {
        count: number;
        committed: number;
        potential: number;
    }>;
    ownershipBreakdown: Record<string, number>;
    totalAssets: number;
    curatedAssets: number;
    assetsWithDeals: number;
    assetsWithVerifiedDeals: number;
    phase3Assets: number;
    activeAssets: number;
}
/**
 * Calculate investment metrics for a set of assets
 * Uses committed (upfront + equity) as primary metric, not total potential
 */
export declare function calculateInvestmentMetrics(assets: KnownAsset[]): InvestmentMetrics;
export declare function getTargetDatabase(target: string): TargetAssetDatabase | null;
export declare function findKnownAsset(name: string, target?: string): KnownAsset | null;
export declare function isExcludedDrug(name: string, target?: string): boolean;
export declare function getKnownAssetsForTarget(target: string): KnownAsset[];
export declare function isTargetRelatedIntervention(interventionName: string, interventionDescription: string | undefined, target: string): boolean;
//# sourceMappingURL=known-assets.d.ts.map