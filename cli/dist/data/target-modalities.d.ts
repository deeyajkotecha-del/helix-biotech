/**
 * Target Modalities Database
 *
 * Defines which therapeutic modalities are relevant for each target type.
 * Used to guide comprehensive asset discovery searches.
 */
export interface TargetModalities {
    officialName: string;
    targetType: 'protein' | 'checkpoint' | 'oncogene' | 'miRNA' | 'receptor' | 'enzyme' | 'other';
    relevantModalities: string[];
    searchTerms: string[];
    companyKeywords: string[];
    indicationKeywords: string[];
    excludeModalities?: string[];
}
export declare const TARGET_MODALITIES: Record<string, TargetModalities>;
export declare const DEFAULT_MODALITIES: TargetModalities;
/**
 * Get modality info for a target
 */
export declare function getTargetModalities(target: string): TargetModalities;
/**
 * Check if a target has curated modality data
 */
export declare function hasCuratedModalities(target: string): boolean;
/**
 * Get all search terms for comprehensive target research
 */
export declare function getComprehensiveSearchTerms(target: string): string[];
//# sourceMappingURL=target-modalities.d.ts.map