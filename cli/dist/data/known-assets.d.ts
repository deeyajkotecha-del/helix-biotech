/**
 * Known Assets Database
 *
 * Curated database of known drug assets for key targets.
 * Used to normalize messy clinical trial data and enrich with deal information.
 */
export interface KnownAsset {
    primaryName: string;
    codeName?: string;
    genericName?: string;
    aliases: string[];
    target: string;
    modality: 'ADC' | 'mAb' | 'Bispecific' | 'CAR-T' | 'Radioconjugate' | 'Small Molecule' | 'BiTE' | 'TCE' | 'Vaccine' | 'Other';
    payload?: string;
    owner: string;
    ownerType: 'Big Pharma' | 'Biotech' | 'Chinese Biotech' | 'Academic' | 'Other';
    partner?: string;
    phase: 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2/3' | 'Phase 3' | 'Filed' | 'Approved';
    status: 'Active' | 'Discontinued' | 'On Hold';
    leadIndication: string;
    otherIndications?: string[];
    dealTerms?: string;
    dealDate?: string;
    notes?: string;
    differentiator?: string;
    trialIds?: string[];
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
/**
 * Get asset database for a target
 */
export declare function getTargetDatabase(target: string): TargetAssetDatabase | null;
/**
 * Find known asset by name
 */
export declare function findKnownAsset(name: string, target?: string): KnownAsset | null;
/**
 * Check if a drug name should be excluded
 */
export declare function isExcludedDrug(name: string, target?: string): boolean;
/**
 * Get all known assets for a target
 */
export declare function getKnownAssetsForTarget(target: string): KnownAsset[];
/**
 * Check if intervention name relates to target
 */
export declare function isTargetRelatedIntervention(interventionName: string, interventionDescription: string | undefined, target: string): boolean;
//# sourceMappingURL=known-assets.d.ts.map