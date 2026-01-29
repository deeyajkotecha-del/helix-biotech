/**
 * Drug Verification Service
 *
 * Verifies that a drug candidate actually targets the expected target.
 * Uses multiple sources to confirm target specificity.
 *
 * Prevents false positives like:
 * - pembrolizumab listed as "TL1A asset" (actually PD-1)
 * - NM26 listed as "TL1A asset" (actually IL-31)
 */
export interface DrugVerificationResult {
    drugName: string;
    expectedTarget: string;
    actualTarget: string | null;
    verified: boolean;
    confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNVERIFIED';
    verificationSources: string[];
    reason: string;
    drugInfo?: {
        phase: string;
        owner: string;
        modality: string;
        indications: string[];
        dealInfo?: string;
    };
}
export interface VerificationContext {
    interventionName: string;
    interventionDescription?: string;
    trialTitle?: string;
    trialConditions?: string[];
    sponsor?: string;
}
/**
 * Verify a drug targets the expected target.
 *
 * Verification layers:
 * 1. Check curated database (highest confidence)
 * 2. Check exclusion lists (common drugs, known false positives)
 * 3. Check name for target keywords
 * 4. Check description/mechanism for target keywords
 * 5. Cross-reference with trial conditions
 */
export declare function verifyDrugTarget(drugName: string, expectedTarget: string, context?: VerificationContext): DrugVerificationResult;
/**
 * Verify multiple drugs in batch
 */
export declare function verifyDrugsBatch(drugs: Array<{
    name: string;
    context?: VerificationContext;
}>, expectedTarget: string): Map<string, DrugVerificationResult>;
/**
 * Filter to only verified drugs
 */
export declare function filterVerifiedDrugs(drugs: string[], expectedTarget: string, minConfidence?: 'HIGH' | 'MEDIUM' | 'LOW'): string[];
/**
 * Database of known false positives - drugs that are frequently
 * incorrectly associated with targets they don't actually target.
 */
export declare const KNOWN_FALSE_POSITIVES: Record<string, string[]>;
/**
 * Check if a drug is a known false positive for a target
 */
export declare function isKnownFalsePositive(drugName: string, target: string): boolean;
//# sourceMappingURL=drug-verification.d.ts.map