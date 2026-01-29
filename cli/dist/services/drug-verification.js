"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.KNOWN_FALSE_POSITIVES = void 0;
exports.verifyDrugTarget = verifyDrugTarget;
exports.verifyDrugsBatch = verifyDrugsBatch;
exports.filterVerifiedDrugs = filterVerifiedDrugs;
exports.isKnownFalsePositive = isKnownFalsePositive;
const known_assets_1 = require("../data/known-assets");
const target_aliases_1 = require("../data/target-aliases");
// ============================================
// Main Verification Functions
// ============================================
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
function verifyDrugTarget(drugName, expectedTarget, context) {
    const targetInfo = (0, target_aliases_1.getTargetInfo)(expectedTarget);
    // Layer 1: Check curated database
    const curatedResult = checkCuratedDatabase(drugName, expectedTarget);
    if (curatedResult.verified) {
        return curatedResult;
    }
    // Layer 2: Check exclusion lists
    const exclusionResult = checkExclusionLists(drugName, expectedTarget);
    if (exclusionResult.verified === false && exclusionResult.confidence === 'HIGH') {
        return exclusionResult;
    }
    // Layer 3: Check name for target keywords
    const nameResult = checkNameForTarget(drugName, expectedTarget, targetInfo);
    if (nameResult.verified) {
        return nameResult;
    }
    // Layer 4: Check description for target keywords
    if (context?.interventionDescription) {
        const descResult = checkDescriptionForTarget(drugName, context.interventionDescription, expectedTarget, targetInfo);
        if (descResult.verified) {
            return descResult;
        }
    }
    // Layer 5: Cross-reference with trial conditions
    if (context?.trialConditions) {
        const conditionResult = checkTrialConditions(drugName, context.trialConditions, expectedTarget, targetInfo);
        if (conditionResult.confidence !== 'UNVERIFIED') {
            return conditionResult;
        }
    }
    // Cannot verify - return unverified
    return {
        drugName,
        expectedTarget,
        actualTarget: null,
        verified: false,
        confidence: 'UNVERIFIED',
        verificationSources: [],
        reason: `Cannot verify ${drugName} targets ${expectedTarget}. No matching evidence found.`,
    };
}
// ============================================
// Verification Layers
// ============================================
/**
 * Layer 1: Check curated database
 */
function checkCuratedDatabase(drugName, expectedTarget) {
    const knownAsset = (0, known_assets_1.findKnownAsset)(drugName, expectedTarget);
    if (knownAsset) {
        return {
            drugName: knownAsset.primaryName,
            expectedTarget,
            actualTarget: knownAsset.target,
            verified: true,
            confidence: 'HIGH',
            verificationSources: ['curated_database'],
            reason: `Found in curated ${expectedTarget} asset database`,
            drugInfo: {
                phase: knownAsset.phase,
                owner: knownAsset.owner,
                modality: knownAsset.modality,
                indications: [knownAsset.leadIndication, ...(knownAsset.otherIndications || [])],
                dealInfo: knownAsset.deal?.headline,
            },
        };
    }
    return {
        drugName,
        expectedTarget,
        actualTarget: null,
        verified: false,
        confidence: 'UNVERIFIED',
        verificationSources: [],
        reason: 'Not found in curated database',
    };
}
/**
 * Layer 2: Check exclusion lists
 */
function checkExclusionLists(drugName, expectedTarget) {
    // Check common non-target drugs (chemo, steroids, etc.)
    if ((0, target_aliases_1.isCommonNonTargetDrug)(drugName)) {
        return {
            drugName,
            expectedTarget,
            actualTarget: 'NOT_TARGET_SPECIFIC',
            verified: false,
            confidence: 'HIGH',
            verificationSources: ['exclusion_list'],
            reason: `${drugName} is a common non-target-specific drug (chemo, steroid, or supportive care)`,
        };
    }
    // Check target-specific exclusions
    if ((0, known_assets_1.isExcludedDrug)(drugName, expectedTarget)) {
        return {
            drugName,
            expectedTarget,
            actualTarget: 'EXCLUDED',
            verified: false,
            confidence: 'HIGH',
            verificationSources: ['target_exclusion_list'],
            reason: `${drugName} is in the ${expectedTarget} exclusion list (known to target different protein)`,
        };
    }
    return {
        drugName,
        expectedTarget,
        actualTarget: null,
        verified: false,
        confidence: 'UNVERIFIED',
        verificationSources: [],
        reason: 'Not in exclusion lists',
    };
}
/**
 * Layer 3: Check drug name for target keywords
 */
function checkNameForTarget(drugName, expectedTarget, targetInfo) {
    const nameLower = drugName.toLowerCase().replace(/[-\s]/g, '');
    const targetLower = expectedTarget.toLowerCase().replace(/[-\s]/g, '');
    // Direct target name match
    if (nameLower.includes(targetLower)) {
        return {
            drugName,
            expectedTarget,
            actualTarget: expectedTarget,
            verified: true,
            confidence: 'MEDIUM',
            verificationSources: ['name_match'],
            reason: `Drug name contains "${expectedTarget}"`,
        };
    }
    // Check target aliases
    if (targetInfo) {
        for (const alias of targetInfo.aliases) {
            const aliasLower = alias.toLowerCase().replace(/[-\s]/g, '');
            if (nameLower.includes(aliasLower)) {
                return {
                    drugName,
                    expectedTarget,
                    actualTarget: expectedTarget,
                    verified: true,
                    confidence: 'MEDIUM',
                    verificationSources: ['name_match', 'alias_match'],
                    reason: `Drug name contains target alias "${alias}"`,
                };
            }
        }
        // Check mechanism keywords
        for (const mechanism of targetInfo.commonMechanisms) {
            const mechLower = mechanism.toLowerCase().replace(/[-\s]/g, '');
            if (nameLower.includes(mechLower)) {
                return {
                    drugName,
                    expectedTarget,
                    actualTarget: expectedTarget,
                    verified: true,
                    confidence: 'MEDIUM',
                    verificationSources: ['name_match', 'mechanism_match'],
                    reason: `Drug name contains mechanism keyword "${mechanism}"`,
                };
            }
        }
    }
    return {
        drugName,
        expectedTarget,
        actualTarget: null,
        verified: false,
        confidence: 'UNVERIFIED',
        verificationSources: [],
        reason: 'Drug name does not contain target keywords',
    };
}
/**
 * Layer 4: Check description for target keywords
 */
function checkDescriptionForTarget(drugName, description, expectedTarget, targetInfo) {
    const descLower = description.toLowerCase();
    const targetLower = expectedTarget.toLowerCase();
    // Check for target mention in description
    if (descLower.includes(targetLower)) {
        return {
            drugName,
            expectedTarget,
            actualTarget: expectedTarget,
            verified: true,
            confidence: 'LOW',
            verificationSources: ['description_match'],
            reason: `Description mentions "${expectedTarget}"`,
        };
    }
    // Check aliases in description
    if (targetInfo) {
        for (const alias of targetInfo.aliases) {
            if (descLower.includes(alias.toLowerCase())) {
                return {
                    drugName,
                    expectedTarget,
                    actualTarget: expectedTarget,
                    verified: true,
                    confidence: 'LOW',
                    verificationSources: ['description_match', 'alias_match'],
                    reason: `Description mentions target alias "${alias}"`,
                };
            }
        }
        // Check mechanisms in description
        for (const mechanism of targetInfo.commonMechanisms) {
            if (descLower.includes(mechanism.toLowerCase())) {
                return {
                    drugName,
                    expectedTarget,
                    actualTarget: expectedTarget,
                    verified: true,
                    confidence: 'LOW',
                    verificationSources: ['description_match', 'mechanism_match'],
                    reason: `Description contains mechanism "${mechanism}"`,
                };
            }
        }
    }
    return {
        drugName,
        expectedTarget,
        actualTarget: null,
        verified: false,
        confidence: 'UNVERIFIED',
        verificationSources: [],
        reason: 'Description does not mention target',
    };
}
/**
 * Layer 5: Cross-reference with trial conditions
 */
function checkTrialConditions(drugName, conditions, expectedTarget, targetInfo) {
    // This is a weak signal - just because a drug is in a trial
    // for a condition doesn't mean it targets our target
    // Use only as supporting evidence, not primary verification
    return {
        drugName,
        expectedTarget,
        actualTarget: null,
        verified: false,
        confidence: 'UNVERIFIED',
        verificationSources: [],
        reason: 'Trial conditions alone cannot verify target',
    };
}
// ============================================
// Batch Verification
// ============================================
/**
 * Verify multiple drugs in batch
 */
function verifyDrugsBatch(drugs, expectedTarget) {
    const results = new Map();
    for (const drug of drugs) {
        const result = verifyDrugTarget(drug.name, expectedTarget, drug.context);
        results.set(drug.name, result);
    }
    return results;
}
/**
 * Filter to only verified drugs
 */
function filterVerifiedDrugs(drugs, expectedTarget, minConfidence = 'LOW') {
    const confidenceOrder = ['LOW', 'MEDIUM', 'HIGH'];
    const minIdx = confidenceOrder.indexOf(minConfidence);
    return drugs.filter(drug => {
        const result = verifyDrugTarget(drug, expectedTarget);
        if (!result.verified)
            return false;
        const resultIdx = confidenceOrder.indexOf(result.confidence);
        return resultIdx >= minIdx;
    });
}
// ============================================
// Known False Positive Database
// ============================================
/**
 * Database of known false positives - drugs that are frequently
 * incorrectly associated with targets they don't actually target.
 */
exports.KNOWN_FALSE_POSITIVES = {
    'TL1A': [
        'NM26', // Actually targets IL-31
        'OSE-703', // Actually targets CD127
        'CNTE-0532', // Cannot verify
    ],
    'B7-H3': [
    // Add any B7-H3 false positives here
    ],
};
/**
 * Check if a drug is a known false positive for a target
 */
function isKnownFalsePositive(drugName, target) {
    const falsePositives = exports.KNOWN_FALSE_POSITIVES[target.toUpperCase()] || [];
    const normalizedDrug = drugName.toLowerCase().replace(/[-\s]/g, '');
    return falsePositives.some(fp => fp.toLowerCase().replace(/[-\s]/g, '') === normalizedDrug);
}
//# sourceMappingURL=drug-verification.js.map