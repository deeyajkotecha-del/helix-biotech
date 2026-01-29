"use strict";
/**
 * Comprehensive Web Research Engine
 *
 * Multi-source research methodology for therapeutic target discovery.
 * Replicates Claude Co-work's comprehensive research approach.
 *
 * NOTE: Live web search is not yet implemented. Currently, this module
 * provides the framework and falls back to curated database + trials.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.comprehensiveTargetResearch = comprehensiveTargetResearch;
exports.extractDrugNames = extractDrugNames;
exports.getResearchStatusMessage = getResearchStatusMessage;
const target_modalities_1 = require("../data/target-modalities");
const target_aliases_1 = require("../data/target-aliases");
const known_assets_1 = require("../data/known-assets");
const asset_research_1 = require("./asset-research");
// ============================================
// Research Phases
// ============================================
/**
 * PHASE 1: Broad Discovery Searches
 * Finds initial list of drug candidates
 */
async function phase1BroadDiscovery(target) {
    const searchTerms = [
        `${target} clinical trials drugs companies 2024 2025`,
        `${target} inhibitor antibody pipeline`,
        `anti-${target} therapy development`,
    ];
    // TODO: Implement actual web search
    // For now, return empty - will rely on curated data
    console.log(`[WebResearch] Phase 1: Would search: ${searchTerms.join(' | ')}`);
    return searchTerms;
}
/**
 * PHASE 2: Modality-Specific Searches
 * Based on target type (protein vs RNA vs oncogene)
 */
async function phase2ModalitySearches(target) {
    const modalities = (0, target_modalities_1.getTargetModalities)(target);
    const searchTerms = modalities.relevantModalities.map(mod => `${target} ${mod} clinical development`);
    console.log(`[WebResearch] Phase 2: Modality searches for ${modalities.relevantModalities.join(', ')}`);
    return searchTerms;
}
/**
 * PHASE 3: Geographic Searches
 * Chinese, European, Japanese biotechs
 */
async function phase3GeographicSearches(target) {
    const searchTerms = [
        `Chinese biotech ${target} drug`,
        `European ${target} development`,
        `Japan ${target} pharmaceutical`,
        `Korea ${target} biotech`,
    ];
    console.log(`[WebResearch] Phase 3: Geographic searches`);
    return searchTerms;
}
/**
 * PHASE 4: Academic/Research Searches
 */
async function phase4AcademicSearches(target) {
    const searchTerms = [
        `${target} university research preclinical`,
        `${target} academic medical center trial`,
        `${target} NIH NCI research`,
    ];
    console.log(`[WebResearch] Phase 4: Academic searches`);
    return searchTerms;
}
/**
 * PHASE 5: Deal/Partnership Searches
 */
async function phase5DealSearches(target) {
    const searchTerms = [
        `${target} licensing deal acquisition 2023 2024`,
        `${target} partnership collaboration pharma`,
        `${target} biotech M&A`,
    ];
    console.log(`[WebResearch] Phase 5: Deal searches`);
    return searchTerms;
}
/**
 * PHASE 6: Company Pipeline Searches
 */
async function phase6CompanySearches(target) {
    const modalities = (0, target_modalities_1.getTargetModalities)(target);
    const searchTerms = modalities.companyKeywords.slice(0, 8).map(company => `${company} ${target} pipeline`);
    console.log(`[WebResearch] Phase 6: Company searches for ${modalities.companyKeywords.slice(0, 5).join(', ')}`);
    return searchTerms;
}
// ============================================
// Drug Verification
// ============================================
/**
 * Verify a drug candidate actually targets the expected target
 */
async function verifyDrug(drugName, expectedTarget) {
    // Check if in curated database first
    const knownAsset = (0, known_assets_1.findKnownAsset)(drugName, expectedTarget);
    if (knownAsset) {
        return {
            name: knownAsset.primaryName,
            confirmedTarget: knownAsset.target,
            matchesExpected: true,
            sources: ['curated_database'],
            phase: knownAsset.phase,
            owner: knownAsset.owner,
            modality: knownAsset.modality,
            indications: [knownAsset.leadIndication, ...(knownAsset.otherIndications || [])],
            dealInfo: knownAsset.deal?.headline,
        };
    }
    // Check if it's a common non-target drug
    if ((0, target_aliases_1.isCommonNonTargetDrug)(drugName)) {
        console.log(`[WebResearch] Excluding common drug: ${drugName}`);
        return null;
    }
    // TODO: Implement web verification
    // For now, return null - unverified
    console.log(`[WebResearch] Cannot verify: ${drugName} (web search not implemented)`);
    return null;
}
// ============================================
// Main Research Function
// ============================================
/**
 * Comprehensive target research using multi-source methodology.
 *
 * Current implementation:
 * 1. Uses curated database (known-assets.ts) for verified data
 * 2. Uses clinical trials discovery for additional candidates
 * 3. Logs what web searches WOULD be performed
 *
 * Future implementation will add live web search.
 */
async function comprehensiveTargetResearch(target) {
    console.log(`\n[WebResearch] ========================================`);
    console.log(`[WebResearch] Comprehensive research for: ${target}`);
    console.log(`[WebResearch] ========================================\n`);
    const startTime = Date.now();
    const allSearchTerms = [];
    // Check if we have curated data for this target
    const hasCurated = (0, target_modalities_1.hasCuratedModalities)(target);
    const curatedAssets = (0, known_assets_1.getKnownAssetsForTarget)(target);
    if (curatedAssets.length > 0) {
        console.log(`[WebResearch] Found ${curatedAssets.length} curated assets - HIGH confidence data`);
    }
    else {
        console.log(`[WebResearch] No curated data for ${target} - will use trial discovery`);
    }
    // Collect all search terms (for logging/future implementation)
    allSearchTerms.push(...await phase1BroadDiscovery(target));
    allSearchTerms.push(...await phase2ModalitySearches(target));
    allSearchTerms.push(...await phase3GeographicSearches(target));
    allSearchTerms.push(...await phase4AcademicSearches(target));
    allSearchTerms.push(...await phase5DealSearches(target));
    allSearchTerms.push(...await phase6CompanySearches(target));
    console.log(`[WebResearch] Would perform ${allSearchTerms.length} web searches`);
    // Run trial-based discovery (current implementation)
    const trialDiscovery = await (0, asset_research_1.discoverAssets)(target);
    // Convert curated assets to VerifiedAsset format
    const curatedVerified = curatedAssets.map(asset => ({
        drugName: asset.primaryName,
        codeName: asset.codeNames?.[0],
        genericName: asset.genericName,
        aliases: asset.aliases,
        target: asset.target,
        modality: asset.modality,
        payload: asset.payload,
        owner: asset.owner,
        ownerType: asset.ownerType,
        partner: asset.partner,
        phase: asset.phase,
        status: asset.status === 'Active' ? 'Active' : 'Unknown',
        leadIndication: asset.leadIndication,
        otherIndications: asset.otherIndications || [],
        trialCount: asset.trialIds?.length || 0,
        trialIds: asset.trialIds || [],
        publicationCount: 0,
        dealTerms: asset.deal?.headline,
        dealDate: asset.deal?.date,
        confidence: 'HIGH',
        verificationMethod: 'curated_database',
        verificationDetails: 'Pre-verified in curated database',
        notes: asset.notes,
        differentiator: asset.differentiator,
        lastUpdated: new Date().toISOString(),
    }));
    // Determine coverage level
    let coverageLevel;
    let dataQualityNote;
    if (curatedAssets.length >= 5) {
        coverageLevel = 'comprehensive';
        dataQualityNote = `Comprehensive curated data with ${curatedAssets.length} verified assets.`;
    }
    else if (curatedAssets.length > 0 || trialDiscovery.verified.length > 0) {
        coverageLevel = 'limited';
        dataQualityNote = `Limited data available. ${curatedAssets.length} curated + ${trialDiscovery.verified.length} discovered.`;
    }
    else {
        coverageLevel = 'minimal';
        dataQualityNote = `Minimal data available for ${target}. Contact us to request comprehensive research.`;
    }
    const result = {
        target,
        methodology: 'Multi-layer verification with curated database priority',
        searchesPerformed: allSearchTerms,
        curatedAssets: curatedVerified,
        discoveredAssets: trialDiscovery.verified.filter(a => a.verificationMethod !== 'curated_database'),
        unverifiedCandidates: trialDiscovery.unverified.map(a => ({
            name: a.drugName,
            source: 'clinical_trials',
            context: `Found in trial ${a.trialIds[0]}`,
            confidence: 0.3,
        })),
        summary: {
            totalVerified: curatedVerified.length + trialDiscovery.verified.length,
            totalUnverified: trialDiscovery.unverified.length,
            coverageLevel,
            dataQualityNote,
        },
        generatedAt: new Date().toISOString(),
    };
    console.log(`\n[WebResearch] Research complete in ${Date.now() - startTime}ms`);
    console.log(`[WebResearch] Coverage: ${coverageLevel}`);
    console.log(`[WebResearch] Verified: ${result.summary.totalVerified}, Unverified: ${result.summary.totalUnverified}`);
    return result;
}
// ============================================
// Helper: Extract Drug Names from Text
// ============================================
/**
 * Extract potential drug names from search result text.
 * Uses patterns common in drug naming.
 */
function extractDrugNames(text) {
    const candidates = [];
    // Pattern 1: Company codes (e.g., DS-7300, MK-7240, PRA023)
    const codePattern = /\b([A-Z]{2,4}[-]?\d{3,5}[A-Za-z]?)\b/g;
    let match;
    while ((match = codePattern.exec(text)) !== null) {
        candidates.push(match[1]);
    }
    // Pattern 2: -mab suffix (antibodies)
    const mabPattern = /\b(\w+mab)\b/gi;
    while ((match = mabPattern.exec(text)) !== null) {
        candidates.push(match[1]);
    }
    // Pattern 3: -nib suffix (kinase inhibitors)
    const nibPattern = /\b(\w+nib)\b/gi;
    while ((match = nibPattern.exec(text)) !== null) {
        candidates.push(match[1]);
    }
    // Pattern 4: -cel suffix (cell therapies)
    const celPattern = /\b(\w+cel)\b/gi;
    while ((match = celPattern.exec(text)) !== null) {
        candidates.push(match[1]);
    }
    // Dedupe and return
    return [...new Set(candidates)];
}
// ============================================
// Export: Get Research Status Message
// ============================================
/**
 * Get a user-facing message about data coverage for a target
 */
function getResearchStatusMessage(target) {
    const curatedAssets = (0, known_assets_1.getKnownAssetsForTarget)(target);
    if (curatedAssets.length >= 5) {
        return {
            hasComprehensiveData: true,
            message: `Comprehensive data: ${curatedAssets.length} verified ${target} assets with deal terms and clinical data.`,
        };
    }
    if (curatedAssets.length > 0) {
        return {
            hasComprehensiveData: false,
            message: `Limited data: ${curatedAssets.length} verified ${target} assets. Additional unverified candidates from clinical trials.`,
            callToAction: 'Request comprehensive research for complete competitive intelligence.',
        };
    }
    return {
        hasComprehensiveData: false,
        message: `Minimal data available for ${target}. Showing trial-discovered candidates only.`,
        callToAction: 'Request Research: Get comprehensive analysis with verified assets, deal terms, and investment insights.',
    };
}
//# sourceMappingURL=web-research.js.map