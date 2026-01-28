"use strict";
/**
 * Patents Service
 *
 * Fetches patent data from USPTO, Orange Book, and EPO.
 * Tracks patent expiry dates and exclusivity periods.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.searchPatentsByDrug = searchPatentsByDrug;
exports.getPatentByNumber = getPatentByNumber;
exports.getPatentsByCompany = getPatentsByCompany;
exports.getOrangeBookListings = getOrangeBookListings;
exports.getExpiringPatents = getExpiringPatents;
exports.calculateEffectiveExpiry = calculateEffectiveExpiry;
exports.inferPatentType = inferPatentType;
exports.assessPatentStrength = assessPatentStrength;
exports.getGenericEntryWindow = getGenericEntryWindow;
exports.buildPatentLandscape = buildPatentLandscape;
exports.identifyPatentCliffs = identifyPatentCliffs;
exports.parseOrangeBookEntry = parseOrangeBookEntry;
exports.normalizePatentNumber = normalizePatentNumber;
// API endpoints
const USPTO_API = 'https://developer.uspto.gov/ibd-api/v1';
const ORANGE_BOOK_URL = 'https://www.accessdata.fda.gov/scripts/cder/ob/default.cfm';
const EPO_OPS_API = 'https://ops.epo.org/3.2/rest-services';
// ============================================
// Main Functions
// ============================================
/**
 * Search patents by drug name
 * TODO: Implement USPTO API integration
 * TODO: Add EPO integration for international patents
 */
async function searchPatentsByDrug(drugName) {
    // TODO: Search USPTO
    // TODO: Search Orange Book
    // TODO: Search EPO for international
    throw new Error('Not implemented');
}
/**
 * Get patent by number
 */
async function getPatentByNumber(patentNumber) {
    // TODO: Fetch from USPTO
    throw new Error('Not implemented');
}
/**
 * Get all patents for a company
 */
async function getPatentsByCompany(companyName) {
    // TODO: Search by assignee
    throw new Error('Not implemented');
}
/**
 * Get Orange Book listings for a drug
 */
async function getOrangeBookListings(drugName) {
    // TODO: Query FDA Orange Book
    // TODO: Parse listings
    throw new Error('Not implemented');
}
/**
 * Check for upcoming patent expirations
 */
async function getExpiringPatents(withinMonths, options) {
    // TODO: Implement
    throw new Error('Not implemented');
}
// ============================================
// Patent Analysis
// ============================================
/**
 * Calculate effective patent expiry (including extensions)
 */
function calculateEffectiveExpiry(patent) {
    if (!patent.originalExpiryDate)
        return patent.expiryDate || null;
    let expiryDate = new Date(patent.originalExpiryDate);
    // Add extensions
    for (const ext of patent.extensions || []) {
        expiryDate.setDate(expiryDate.getDate() + ext.days);
    }
    return expiryDate.toISOString().split('T')[0];
}
/**
 * Determine patent type from claims/title
 */
function inferPatentType(title, claims) {
    const text = (title + ' ' + (claims?.join(' ') || '')).toLowerCase();
    if (text.includes('composition') || text.includes('compound') || text.includes('formula')) {
        return 'Composition of Matter';
    }
    if (text.includes('method of treatment') || text.includes('method for treating') || text.includes('use of')) {
        return 'Method of Use';
    }
    if (text.includes('formulation') || text.includes('dosage form') || text.includes('sustained release')) {
        return 'Formulation';
    }
    if (text.includes('process') || text.includes('synthesis') || text.includes('manufacture')) {
        return 'Process';
    }
    if (text.includes('combination') || text.includes('co-administration')) {
        return 'Combination';
    }
    return 'Composition of Matter'; // Default
}
/**
 * Assess patent strength (simplified heuristic)
 */
function assessPatentStrength(patent) {
    // Composition of matter patents are generally stronger
    if (patent.patentType === 'Composition of Matter') {
        if (!patent.challenges || patent.challenges.length === 0) {
            return 'Strong';
        }
        return 'Moderate';
    }
    // Method of use and formulation patents are weaker
    if (patent.patentType === 'Method of Use' || patent.patentType === 'Formulation') {
        return 'Moderate';
    }
    // Patents with successful challenges are weak
    if (patent.challenges?.some(c => c.outcome?.toLowerCase().includes('invalidated'))) {
        return 'Weak';
    }
    return 'Moderate';
}
/**
 * Check for generic entry window
 */
function getGenericEntryWindow(patent) {
    const effectiveExpiry = calculateEffectiveExpiry(patent);
    if (!effectiveExpiry) {
        return { earliestEntry: null, daysUntilEntry: null, hasExclusivity: false };
    }
    const expiryDate = new Date(effectiveExpiry);
    const today = new Date();
    const daysUntil = Math.ceil((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    // Check for pediatric exclusivity (adds 6 months)
    const hasPediatric = patent.extensions?.some(e => e.type === 'PED');
    return {
        earliestEntry: effectiveExpiry,
        daysUntilEntry: daysUntil,
        hasExclusivity: hasPediatric || false
    };
}
// ============================================
// Patent Landscape
// ============================================
/**
 * Build patent landscape for a drug
 */
async function buildPatentLandscape(drugName) {
    // TODO: Implement
    throw new Error('Not implemented');
}
/**
 * Identify patent cliffs
 */
async function identifyPatentCliffs(year) {
    // TODO: Find patents expiring in given year
    // TODO: Match with revenue data
    throw new Error('Not implemented');
}
// ============================================
// USPTO API Functions
// ============================================
/**
 * Search USPTO patent database
 */
async function searchUSPTO(query, maxResults = 100) {
    // TODO: Implement USPTO API call
    // TODO: Handle pagination
    throw new Error('Not implemented');
}
/**
 * Get patent full text from USPTO
 */
async function getPatentFullText(patentNumber) {
    // TODO: Implement
    throw new Error('Not implemented');
}
// ============================================
// Orange Book Functions
// ============================================
/**
 * Parse Orange Book data
 */
function parseOrangeBookEntry(entry) {
    // TODO: Implement parsing
    throw new Error('Not implemented');
}
/**
 * Download Orange Book data file
 */
async function downloadOrangeBookData() {
    // TODO: Download from FDA
    // TODO: Parse CSV/text file
    throw new Error('Not implemented');
}
// ============================================
// Utility
// ============================================
/**
 * Normalize patent number format
 */
function normalizePatentNumber(number) {
    // Remove spaces, commas
    let normalized = number.replace(/[\s,]/g, '');
    // Ensure country prefix
    if (/^\d/.test(normalized)) {
        normalized = 'US' + normalized;
    }
    return normalized.toUpperCase();
}
//# sourceMappingURL=patents.js.map