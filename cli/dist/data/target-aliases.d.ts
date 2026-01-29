/**
 * Target Aliases Database
 *
 * Comprehensive mapping of therapeutic targets to their aliases,
 * gene symbols, and common mechanism descriptions.
 *
 * Used for accurate asset verification - prevents false positives
 * by ensuring discovered drugs actually target the query target.
 */
export interface TargetInfo {
    officialName: string;
    aliases: string[];
    geneSymbol: string;
    uniprotId?: string;
    commonMechanisms: string[];
    relatedTargets?: string[];
}
export declare const TARGET_ALIASES: Record<string, TargetInfo>;
/**
 * Drugs that commonly appear in clinical trials but are NOT
 * target-specific therapeutics. These should be EXCLUDED from
 * asset discovery unless they explicitly match the target.
 */
export declare const COMMON_NON_TARGET_DRUGS: string[];
/**
 * Get target info by name (case-insensitive, handles aliases)
 */
export declare function getTargetInfo(target: string): TargetInfo | null;
/**
 * Get all name variants for a target (for matching)
 */
export declare function getTargetVariants(target: string): string[];
/**
 * Check if a drug name is in the common exclusion list
 */
export declare function isCommonNonTargetDrug(drugName: string): boolean;
/**
 * Infer target info for unknown targets
 */
export declare function inferTargetInfo(target: string): TargetInfo;
//# sourceMappingURL=target-aliases.d.ts.map