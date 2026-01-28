"use strict";
/**
 * Markets Service
 *
 * Extracts market size and growth data from SEC filings,
 * analyst reports, and other sources.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getMarketData = getMarketData;
exports.getMarketProjections = getMarketProjections;
exports.getMarketLeaders = getMarketLeaders;
exports.searchFilingsForMarketData = searchFilingsForMarketData;
exports.extractMarketSize = extractMarketSize;
exports.extractGrowthRate = extractGrowthRate;
exports.extractPatientPopulation = extractPatientPopulation;
exports.compareMarkets = compareMarkets;
exports.getLargestMarkets = getLargestMarkets;
exports.getFastestGrowingMarkets = getFastestGrowingMarkets;
exports.extractDrugRevenue = extractDrugRevenue;
exports.buildRevenueTimeline = buildRevenueTimeline;
exports.estimateMarketFromPrevalence = estimateMarketFromPrevalence;
exports.projectMarketGrowth = projectMarketGrowth;
exports.normalizeIndicationName = normalizeIndicationName;
exports.matchIndication = matchIndication;
// ============================================
// Main Functions
// ============================================
/**
 * Get market data for an indication
 * TODO: Implement SEC filing extraction
 * TODO: Add analyst report parsing
 */
async function getMarketData(indication, region, year) {
    // TODO: Search cache first
    // TODO: Search SEC filings
    // TODO: Search analyst estimates
    throw new Error('Not implemented');
}
/**
 * Get market projections for an indication
 */
async function getMarketProjections(indication, startYear, endYear) {
    // TODO: Implement
    throw new Error('Not implemented');
}
/**
 * Get market leaders for an indication
 */
async function getMarketLeaders(indication) {
    // TODO: Extract from SEC filings
    // TODO: Calculate market share
    throw new Error('Not implemented');
}
/**
 * Search SEC filings for market size mentions
 */
async function searchFilingsForMarketData(indication, options) {
    // TODO: Search SEC EDGAR
    // TODO: Extract market size mentions
    throw new Error('Not implemented');
}
// ============================================
// SEC Filing Analysis
// ============================================
/**
 * Extract market size from filing text
 */
function extractMarketSize(text) {
    const results = [];
    // Pattern: "$X billion market" or "market of $X billion"
    const patterns = [
        /\$?([\d.]+)\s*(billion|million)\s+(?:market|opportunity|TAM)/gi,
        /(?:market|opportunity|TAM)\s+(?:of|worth|valued at)\s+\$?([\d.]+)\s*(billion|million)/gi,
        /(?:addressable market|total market)\s+(?:is|of|estimated at)\s+\$?([\d.]+)\s*(billion|million)/gi,
    ];
    for (const pattern of patterns) {
        let match;
        while ((match = pattern.exec(text)) !== null) {
            results.push({
                value: parseFloat(match[1]),
                unit: match[2].toLowerCase(),
            });
        }
    }
    return results;
}
/**
 * Extract growth rate from filing text
 */
function extractGrowthRate(text) {
    const patterns = [
        /(?:CAGR|growth rate|growing at)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%/gi,
        /(\d+(?:\.\d+)?)\s*%\s+(?:CAGR|growth|annual growth)/gi,
    ];
    for (const pattern of patterns) {
        const match = pattern.exec(text);
        if (match) {
            return parseFloat(match[1]);
        }
    }
    return null;
}
/**
 * Extract patient population from text
 */
function extractPatientPopulation(text) {
    const patterns = [
        /([\d.]+)\s*(million|thousand)\s+(?:patients|people|individuals)\s+(?:affected|diagnosed|living with)/gi,
        /(?:affects|affects approximately|prevalence of)\s+([\d.]+)\s*(million|thousand)/gi,
    ];
    for (const pattern of patterns) {
        const match = pattern.exec(text);
        if (match) {
            const value = parseFloat(match[1]);
            const multiplier = match[2].toLowerCase() === 'million' ? 1000000 : 1000;
            return value * multiplier;
        }
    }
    return null;
}
// ============================================
// Market Comparison
// ============================================
/**
 * Compare market sizes across indications
 */
async function compareMarkets(indications) {
    // TODO: Fetch data for each indication
    // TODO: Sort by size
    throw new Error('Not implemented');
}
/**
 * Get largest markets in a therapeutic area
 */
async function getLargestMarkets(therapeuticArea, limit) {
    // TODO: Implement
    throw new Error('Not implemented');
}
/**
 * Get fastest growing markets
 */
async function getFastestGrowingMarkets(minSizeBillion, limit) {
    // TODO: Implement
    throw new Error('Not implemented');
}
// ============================================
// Revenue Analysis
// ============================================
/**
 * Extract drug revenue from SEC filings
 */
async function extractDrugRevenue(ticker, drugName) {
    // TODO: Fetch 10-K/10-Q filings
    // TODO: Parse revenue tables
    throw new Error('Not implemented');
}
/**
 * Build revenue timeline for a drug
 */
async function buildRevenueTimeline(drugName) {
    // TODO: Aggregate from multiple company filings
    throw new Error('Not implemented');
}
// ============================================
// Market Sizing Models
// ============================================
/**
 * Estimate market size using prevalence model
 */
function estimateMarketFromPrevalence(prevalence, // Number of patients
treatmentRate, // % who receive treatment
annualCostPerPatient // Average annual cost
) {
    return (prevalence * treatmentRate * annualCostPerPatient) / 1e9; // Returns billions
}
/**
 * Project market growth
 */
function projectMarketGrowth(currentSize, cagr, years) {
    const projections = [];
    const currentYear = new Date().getFullYear();
    for (let i = 0; i <= years; i++) {
        projections.push({
            year: currentYear + i,
            size: currentSize * Math.pow(1 + cagr / 100, i)
        });
    }
    return projections;
}
// ============================================
// Utility
// ============================================
/**
 * Normalize indication name for matching
 */
function normalizeIndicationName(indication) {
    return indication
        .toLowerCase()
        .replace(/['']/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}
/**
 * Match indication variations
 */
function matchIndication(query, target) {
    const q = normalizeIndicationName(query);
    const t = normalizeIndicationName(target);
    // Exact match
    if (q === t)
        return true;
    // Partial match
    if (t.includes(q) || q.includes(t))
        return true;
    // Common abbreviations
    const abbreviations = {
        'ulcerative colitis': ['uc', 'ibd'],
        'crohns disease': ['crohn', 'cd', 'ibd'],
        'rheumatoid arthritis': ['ra'],
        'psoriatic arthritis': ['psa'],
        'multiple sclerosis': ['ms'],
        'non-small cell lung cancer': ['nsclc'],
        'small cell lung cancer': ['sclc'],
    };
    for (const [full, abbrevs] of Object.entries(abbreviations)) {
        if (q === full && abbrevs.includes(t))
            return true;
        if (t === full && abbrevs.includes(q))
            return true;
    }
    return false;
}
//# sourceMappingURL=markets.js.map