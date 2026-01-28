"use strict";
/**
 * Key Opinion Leaders (KOL) Service
 *
 * Identifies and tracks key opinion leaders from publication data.
 * Normalizes author names and aggregates publication metrics.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildKOLsFromPublications = buildKOLsFromPublications;
exports.getTopKOLsForCondition = getTopKOLsForCondition;
exports.getKOLByName = getKOLByName;
exports.getKOLsByInstitution = getKOLsByInstitution;
exports.getKOLsForDrug = getKOLsForDrug;
exports.normalizeAuthorName = normalizeAuthorName;
exports.generateKOLId = generateKOLId;
exports.namesSimilar = namesSimilar;
exports.calculateHIndex = calculateHIndex;
exports.isActiveKOL = isActiveKOL;
exports.calculateKOLScore = calculateKOLScore;
exports.detectIndustryAffiliations = detectIndustryAffiliations;
exports.extractTherapeuticAreas = extractTherapeuticAreas;
// ============================================
// Main Functions
// ============================================
/**
 * Build KOL database from publications
 * TODO: Implement name normalization
 * TODO: Handle institution changes over time
 * TODO: Calculate h-index
 */
async function buildKOLsFromPublications(publications) {
    // TODO: Extract all authors
    // TODO: Normalize names
    // TODO: Aggregate by normalized name
    // TODO: Calculate metrics
    throw new Error('Not implemented');
}
/**
 * Get top KOLs for a condition
 */
async function getTopKOLsForCondition(condition, options) {
    // TODO: Search publications
    // TODO: Build KOL list
    // TODO: Sort by publication count
    throw new Error('Not implemented');
}
/**
 * Get KOL profile by name
 */
async function getKOLByName(name) {
    // TODO: Search by normalized name
    // TODO: Search name variations
    throw new Error('Not implemented');
}
/**
 * Get KOLs at an institution
 */
async function getKOLsByInstitution(institution) {
    // TODO: Implement
    throw new Error('Not implemented');
}
/**
 * Get KOLs for a specific drug/molecule
 */
async function getKOLsForDrug(drugName) {
    // TODO: Search publications mentioning drug
    // TODO: Extract authors
    throw new Error('Not implemented');
}
// ============================================
// Name Normalization
// ============================================
/**
 * Normalize author name to standard format
 * Returns: "LastName FirstName MiddleInitial"
 */
function normalizeAuthorName(author) {
    let lastName;
    let foreName;
    if (typeof author === 'string') {
        // Parse string format: "John A Smith" or "Smith, John A"
        if (author.includes(',')) {
            const parts = author.split(',').map(p => p.trim());
            lastName = parts[0];
            foreName = parts[1] || '';
        }
        else {
            const parts = author.split(' ');
            lastName = parts[parts.length - 1];
            foreName = parts.slice(0, -1).join(' ');
        }
    }
    else {
        lastName = author.lastName;
        foreName = author.foreName || author.initials || '';
    }
    // Normalize: LastName FirstName
    return `${capitalizeFirst(lastName)} ${capitalizeFirst(foreName)}`.trim();
}
/**
 * Generate canonical name ID (for deduplication)
 */
function generateKOLId(name) {
    return normalizeAuthorName(name)
        .toLowerCase()
        .replace(/[^a-z]+/g, '-')
        .replace(/^-|-$/g, '');
}
/**
 * Check if two names likely refer to same person
 */
function namesSimilar(name1, name2) {
    const n1 = normalizeAuthorName(name1).toLowerCase();
    const n2 = normalizeAuthorName(name2).toLowerCase();
    // Exact match
    if (n1 === n2)
        return true;
    // Extract parts
    const parts1 = n1.split(' ');
    const parts2 = n2.split(' ');
    // Same last name required
    if (parts1[0] !== parts2[0])
        return false;
    // Check first name / initials
    if (parts1.length > 1 && parts2.length > 1) {
        const first1 = parts1[1];
        const first2 = parts2[1];
        // One is initial of the other
        if (first1[0] === first2[0]) {
            if (first1.length === 1 || first2.length === 1)
                return true;
            // Both full names - should match
            return first1 === first2;
        }
    }
    return false;
}
// ============================================
// Metrics Calculation
// ============================================
/**
 * Calculate h-index from citation data
 */
function calculateHIndex(citationCounts) {
    // Sort in descending order
    const sorted = [...citationCounts].sort((a, b) => b - a);
    let h = 0;
    for (let i = 0; i < sorted.length; i++) {
        if (sorted[i] >= i + 1) {
            h = i + 1;
        }
        else {
            break;
        }
    }
    return h;
}
/**
 * Determine if KOL is currently active
 */
function isActiveKOL(kol, yearsThreshold = 3) {
    if (!kol.lastPublicationDate)
        return false;
    const lastPub = new Date(kol.lastPublicationDate);
    const cutoff = new Date();
    cutoff.setFullYear(cutoff.getFullYear() - yearsThreshold);
    return lastPub >= cutoff;
}
/**
 * Calculate KOL score (composite ranking metric)
 */
function calculateKOLScore(kol) {
    // Weighted scoring:
    // - Publication count (recent weighted 2x)
    // - H-index
    // - Active status
    // - Trial involvement
    let score = 0;
    // Publication metrics
    score += kol.publicationCount * 1;
    score += kol.recentPublicationCount * 2;
    // H-index
    if (kol.hIndex) {
        score += kol.hIndex * 3;
    }
    // Active bonus
    if (kol.isActive) {
        score += 20;
    }
    // Trial involvement bonus
    if (kol.trialInvolvement && kol.trialInvolvement.length > 0) {
        score += kol.trialInvolvement.length * 10;
    }
    return score;
}
// ============================================
// Industry Connection Detection
// ============================================
/**
 * Detect potential industry affiliations from publications
 */
function detectIndustryAffiliations(publications) {
    const companies = new Set();
    // Known pharma company patterns
    const pharmaPatterns = [
        /\b(pfizer|novartis|roche|merck|abbvie|bms|bristol.?myers|johnson|sanofi|gsk|glaxo|lilly|amgen|gilead|regeneron|biogen|vertex|moderna)\b/gi
    ];
    for (const pub of publications) {
        for (const author of pub.authors) {
            if (author.affiliation) {
                for (const pattern of pharmaPatterns) {
                    const matches = author.affiliation.match(pattern);
                    if (matches) {
                        matches.forEach(m => companies.add(m.toLowerCase()));
                    }
                }
            }
        }
    }
    return Array.from(companies);
}
// ============================================
// Topic Analysis
// ============================================
/**
 * Extract therapeutic areas from publication MeSH terms
 */
function extractTherapeuticAreas(publications) {
    const areaCounts = {};
    // Major therapeutic area MeSH categories
    const therapeuticAreas = {
        'Oncology': ['neoplasms', 'cancer', 'tumor', 'carcinoma', 'lymphoma', 'leukemia'],
        'Immunology': ['autoimmune', 'inflammation', 'immune', 'immunotherapy'],
        'Cardiology': ['cardiovascular', 'heart', 'cardiac', 'hypertension'],
        'Neurology': ['nervous system', 'brain', 'neurological', 'alzheimer', 'parkinson'],
        'Gastroenterology': ['gastrointestinal', 'digestive', 'liver', 'hepatic', 'colitis', 'crohn'],
        'Respiratory': ['respiratory', 'lung', 'pulmonary', 'asthma', 'copd'],
        'Infectious Disease': ['infection', 'bacterial', 'viral', 'fungal', 'hiv', 'hepatitis'],
        'Rare Disease': ['rare disease', 'orphan'],
    };
    for (const pub of publications) {
        const meshTerms = (pub.meshTerms || []).map(t => t.toLowerCase());
        const keywords = (pub.keywords || []).map(k => k.toLowerCase());
        const allTerms = [...meshTerms, ...keywords, pub.title.toLowerCase()];
        for (const [area, patterns] of Object.entries(therapeuticAreas)) {
            if (patterns.some(p => allTerms.some(t => t.includes(p)))) {
                areaCounts[area] = (areaCounts[area] || 0) + 1;
            }
        }
    }
    return Object.entries(areaCounts)
        .map(([area, count]) => ({ area, count }))
        .sort((a, b) => b.count - a.count);
}
// ============================================
// Utility
// ============================================
function capitalizeFirst(str) {
    if (!str)
        return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}
//# sourceMappingURL=kols.js.map