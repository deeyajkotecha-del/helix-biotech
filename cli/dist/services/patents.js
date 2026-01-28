"use strict";
/**
 * Patents & Exclusivity Service
 *
 * Provides patent and exclusivity data for FDA-approved drugs using:
 * - FDA Orange Book ZIP download (patents + exclusivities for NDA drugs)
 * - OpenFDA drugsfda API (drug approval lookup)
 * - BPCIA 12-year exclusivity calculation for biologics (BLA)
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.searchDrugApprovals = searchDrugApprovals;
exports.getPatentsForApplication = getPatentsForApplication;
exports.getExclusivitiesForApplication = getExclusivitiesForApplication;
exports.calculateEffectiveLOE = calculateEffectiveLOE;
exports.getDrugPatentProfile = getDrugPatentProfile;
exports.getPatentsByCondition = getPatentsByCondition;
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const axios_1 = __importDefault(require("axios"));
const adm_zip_1 = __importDefault(require("adm-zip"));
// ============================================
// Constants
// ============================================
const ORANGE_BOOK_ZIP_URL = 'https://www.fda.gov/media/76860/download';
const OPENFDA_DRUGSFDA_URL = 'https://api.fda.gov/drug/drugsfda.json';
const CACHE_DIR = path.resolve(__dirname, '..', '..', 'cache', 'patents');
// Exclusivity code descriptions
const EXCLUSIVITY_CODES = {
    'NCE': 'New Chemical Entity (5 years)',
    'NP': 'New Product (3 years)',
    'NPP': 'New Patient Population (3 years)',
    'NDA_AUTH': 'NDA-Authorized Generic',
    'ODE': 'Orphan Drug Exclusivity (7 years)',
    'PED': 'Pediatric Exclusivity (6 months)',
    'RTO': 'Right of Reference',
};
// In-memory cache for Orange Book data
let cachedProducts = null;
let cachedPatents = null;
let cachedExclusivities = null;
let cacheLoadedAt = 0;
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
// Rate limiting for OpenFDA
let lastOpenFDACall = 0;
const OPENFDA_DELAY_MS = 300;
// ============================================
// Orange Book Data Loading
// ============================================
/**
 * Download and parse the FDA Orange Book ZIP file.
 * Caches to disk and memory for 24 hours.
 */
async function loadOrangeBookData() {
    // Check memory cache
    if (cachedProducts && cachedPatents && cachedExclusivities) {
        if (Date.now() - cacheLoadedAt < CACHE_TTL_MS) {
            return;
        }
    }
    // Check disk cache
    const patentCacheFile = path.join(CACHE_DIR, 'patent.txt');
    const exclusivityCacheFile = path.join(CACHE_DIR, 'exclusivity.txt');
    const productsCacheFile = path.join(CACHE_DIR, 'products.txt');
    let patentText;
    let exclusivityText;
    let productsText;
    const cacheExists = fs.existsSync(patentCacheFile) &&
        fs.existsSync(exclusivityCacheFile) &&
        fs.existsSync(productsCacheFile);
    const cacheAge = cacheExists
        ? Date.now() - fs.statSync(patentCacheFile).mtimeMs
        : Infinity;
    if (cacheExists && cacheAge < CACHE_TTL_MS) {
        console.log('  [Patents] Loading Orange Book from disk cache...');
        patentText = fs.readFileSync(patentCacheFile, 'utf-8');
        exclusivityText = fs.readFileSync(exclusivityCacheFile, 'utf-8');
        productsText = fs.readFileSync(productsCacheFile, 'utf-8');
    }
    else {
        console.log('  [Patents] Downloading Orange Book ZIP from FDA...');
        const response = await axios_1.default.get(ORANGE_BOOK_ZIP_URL, {
            responseType: 'arraybuffer',
            timeout: 30000,
        });
        const zip = new adm_zip_1.default(Buffer.from(response.data));
        const entries = zip.getEntries();
        patentText = '';
        exclusivityText = '';
        productsText = '';
        for (const entry of entries) {
            const name = entry.entryName.toLowerCase();
            const content = entry.getData().toString('utf-8');
            if (name.includes('patent'))
                patentText = content;
            else if (name.includes('exclusivity'))
                exclusivityText = content;
            else if (name.includes('products'))
                productsText = content;
        }
        // Cache to disk
        if (!fs.existsSync(CACHE_DIR)) {
            fs.mkdirSync(CACHE_DIR, { recursive: true });
        }
        fs.writeFileSync(patentCacheFile, patentText);
        fs.writeFileSync(exclusivityCacheFile, exclusivityText);
        fs.writeFileSync(productsCacheFile, productsText);
        console.log('  [Patents] Orange Book cached to disk.');
    }
    // Parse tilde-delimited files
    cachedProducts = parseTildeDelimited(productsText, [
        'ingredient', 'dfRoute', 'tradeName', 'applicant', 'strength',
        'applType', 'applNo', 'productNo', 'teCode', 'approvalDate',
        'rld', 'rs', 'type', 'applicantFullName',
    ]);
    cachedPatents = parseTildeDelimited(patentText, [
        'applType', 'applNo', 'productNo', 'patentNo', 'patentExpireDateText',
        'drugSubstanceFlag', 'drugProductFlag', 'patentUseCode', 'delistFlag', 'submissionDate',
    ]);
    cachedExclusivities = parseTildeDelimited(exclusivityText, [
        'applType', 'applNo', 'productNo', 'exclusivityCode', 'exclusivityDate',
    ]);
    cacheLoadedAt = Date.now();
    console.log(`  [Patents] Loaded: ${cachedProducts.length} products, ${cachedPatents.length} patent rows, ${cachedExclusivities.length} exclusivity rows`);
}
/**
 * Parse a tilde-delimited text file into objects
 */
function parseTildeDelimited(text, fields) {
    const lines = text.split('\n').filter(line => line.trim().length > 0);
    // Skip header row
    const dataLines = lines.slice(1);
    return dataLines.map(line => {
        const parts = line.split('~');
        const obj = {};
        for (let i = 0; i < fields.length; i++) {
            obj[fields[i]] = (parts[i] || '').trim();
        }
        return obj;
    });
}
/**
 * Parse an Orange Book date string like "Oct 17, 2036" to ISO date "2036-10-17"
 */
function parseOBDate(dateStr) {
    if (!dateStr || dateStr.trim() === '')
        return null;
    const d = new Date(dateStr.trim());
    if (isNaN(d.getTime()))
        return null;
    return d.toISOString().split('T')[0];
}
// ============================================
// OpenFDA Drug Lookup
// ============================================
/**
 * Search OpenFDA drugsfda endpoint for a drug by name.
 * Returns approval information including application number.
 */
async function searchDrugApprovals(drugName) {
    // Rate limit
    const now = Date.now();
    const elapsed = now - lastOpenFDACall;
    if (elapsed < OPENFDA_DELAY_MS) {
        await new Promise(r => setTimeout(r, OPENFDA_DELAY_MS - elapsed));
    }
    lastOpenFDACall = Date.now();
    const nameNorm = drugName.trim().toLowerCase();
    // Try brand name first, then generic name
    const searches = [
        `openfda.brand_name:"${nameNorm}"`,
        `openfda.generic_name:"${nameNorm}"`,
    ];
    const allResults = [];
    for (const search of searches) {
        try {
            const url = `${OPENFDA_DRUGSFDA_URL}?search=${encodeURIComponent(search)}&limit=5`;
            const response = await axios_1.default.get(url, { timeout: 15000 });
            if (response.data?.results) {
                for (const result of response.data.results) {
                    const applNo = result.application_number || '';
                    const isBiologic = applNo.startsWith('BLA');
                    const applType = isBiologic ? 'BLA' : applNo.startsWith('ANDA') ? 'ANDA' : 'NDA';
                    // Extract original approval date from submissions
                    // Prefer ORIG submission (original application), fall back to earliest AP
                    let approvalDate;
                    if (result.submissions?.length > 0) {
                        // First try to find the ORIG (original) submission
                        const origSubmission = result.submissions.find((s) => s.submission_type === 'ORIG');
                        if (origSubmission?.submission_status_date) {
                            const dateStr = origSubmission.submission_status_date;
                            approvalDate = `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
                        }
                        else {
                            // Fall back to the earliest approved submission
                            const approvedSubs = result.submissions
                                .filter((s) => s.submission_status === 'AP' && s.submission_status_date)
                                .sort((a, b) => (a.submission_status_date || '').localeCompare(b.submission_status_date || ''));
                            if (approvedSubs.length > 0) {
                                const dateStr = approvedSubs[0].submission_status_date;
                                approvalDate = `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
                            }
                        }
                    }
                    const products = result.products || [];
                    const activeIngredients = [];
                    const productNumbers = [];
                    let brandName = '';
                    let genericName = '';
                    let dosageForm = '';
                    let route = '';
                    for (const prod of products) {
                        if (prod.brand_name && !brandName)
                            brandName = prod.brand_name;
                        if (prod.dosage_form && !dosageForm)
                            dosageForm = prod.dosage_form;
                        if (prod.route && !route)
                            route = prod.route;
                        if (prod.product_number)
                            productNumbers.push(prod.product_number);
                        if (prod.active_ingredients) {
                            for (const ai of prod.active_ingredients) {
                                genericName = ai.name || genericName;
                                const existing = activeIngredients.find((x) => x.name === ai.name);
                                if (!existing) {
                                    activeIngredients.push({ name: ai.name, strength: ai.strength });
                                }
                            }
                        }
                    }
                    // Avoid duplicates
                    if (allResults.some((a) => a.applicationNumber === applNo))
                        continue;
                    allResults.push({
                        applicationNumber: applNo,
                        applicationType: applType,
                        brandName: brandName || drugName,
                        genericName: genericName || '',
                        sponsorName: result.sponsor_name || '',
                        approvalDate,
                        activeIngredients,
                        dosageForm,
                        route,
                        productNumbers,
                        isBiologic,
                    });
                }
            }
        }
        catch (err) {
            if (err.response?.status === 404)
                continue;
            console.error(`  [Patents] OpenFDA search error for "${search}":`, err.message);
        }
    }
    return allResults;
}
// ============================================
// Patent & Exclusivity Retrieval
// ============================================
/**
 * Get Orange Book patents for a given application number.
 */
async function getPatentsForApplication(applicationNumber) {
    await loadOrangeBookData();
    // Extract numeric part: "NDA211675" -> "211675"
    const applNo = applicationNumber.replace(/^(NDA|BLA|ANDA)/i, '').trim();
    const matches = cachedPatents.filter(p => p.applNo === applNo);
    // Deduplicate by patent number (keep unique patents)
    const seen = new Map();
    for (const row of matches) {
        const key = row.patentNo;
        if (!seen.has(key)) {
            const expiryParsed = parseOBDate(row.patentExpireDateText);
            seen.set(key, {
                patentNumber: row.patentNo,
                expiryDate: row.patentExpireDateText,
                expiryDateParsed: expiryParsed || '',
                drugSubstance: row.drugSubstanceFlag === 'Y',
                drugProduct: row.drugProductFlag === 'Y',
                patentUseCode: row.patentUseCode || undefined,
                delistFlag: row.delistFlag === 'Y',
                submissionDate: row.submissionDate || undefined,
                applicationNumber,
                productNumber: row.productNo,
            });
        }
    }
    const patents = Array.from(seen.values());
    // Sort by expiry date descending
    patents.sort((a, b) => {
        if (!a.expiryDateParsed)
            return 1;
        if (!b.expiryDateParsed)
            return -1;
        return b.expiryDateParsed.localeCompare(a.expiryDateParsed);
    });
    return patents;
}
/**
 * Get Orange Book exclusivities for a given application number.
 */
async function getExclusivitiesForApplication(applicationNumber) {
    await loadOrangeBookData();
    const applNo = applicationNumber.replace(/^(NDA|BLA|ANDA)/i, '').trim();
    const matches = cachedExclusivities.filter(e => e.applNo === applNo);
    return matches.map(row => {
        const code = row.exclusivityCode;
        // Determine exclusivity type from code
        let exclusivityType = '';
        if (code.startsWith('NCE'))
            exclusivityType = 'New Chemical Entity (5 years)';
        else if (code.startsWith('NP') && !code.startsWith('NPP'))
            exclusivityType = 'New Product (3 years)';
        else if (code.startsWith('NPP'))
            exclusivityType = 'New Patient Population (3 years)';
        else if (code.startsWith('ODE'))
            exclusivityType = 'Orphan Drug Exclusivity (7 years)';
        else if (code.startsWith('PED'))
            exclusivityType = 'Pediatric Exclusivity (6 months added)';
        else if (code.startsWith('I-'))
            exclusivityType = `New Indication Exclusivity (3 years)`;
        else if (code.startsWith('D-'))
            exclusivityType = `New Dosage Form Exclusivity`;
        else if (code.startsWith('RTO'))
            exclusivityType = 'Right of Reference';
        else
            exclusivityType = EXCLUSIVITY_CODES[code] || code;
        return {
            exclusivityCode: code,
            exclusivityDate: row.exclusivityDate,
            exclusivityDateParsed: parseOBDate(row.exclusivityDate) || '',
            exclusivityType,
            applicationNumber,
            productNumber: row.productNo,
        };
    }).sort((a, b) => {
        if (!a.exclusivityDateParsed)
            return 1;
        if (!b.exclusivityDateParsed)
            return -1;
        return b.exclusivityDateParsed.localeCompare(a.exclusivityDateParsed);
    });
}
// ============================================
// LOE Calculation
// ============================================
/**
 * Calculate the effective Loss of Exclusivity (LOE) date.
 * This is the latest of:
 * - Latest patent expiry
 * - Latest exclusivity expiry
 * - 12-year BPCIA exclusivity for biologics
 */
function calculateEffectiveLOE(patents, exclusivities, approval) {
    // Latest patent expiry
    let latestPatent = null;
    for (const p of patents) {
        if (p.expiryDateParsed && (!latestPatent || p.expiryDateParsed > latestPatent)) {
            latestPatent = p.expiryDateParsed;
        }
    }
    // Latest exclusivity expiry
    let latestExcl = null;
    for (const e of exclusivities) {
        if (e.exclusivityDateParsed && (!latestExcl || e.exclusivityDateParsed > latestExcl)) {
            latestExcl = e.exclusivityDateParsed;
        }
    }
    // Biologic exclusivity (12 years from approval under BPCIA)
    let biologicExpiry = null;
    if (approval?.isBiologic && approval.approvalDate) {
        const approvalDate = new Date(approval.approvalDate);
        approvalDate.setFullYear(approvalDate.getFullYear() + 12);
        biologicExpiry = approvalDate.toISOString().split('T')[0];
    }
    // Effective LOE = latest of all protections
    const candidates = [latestPatent, latestExcl, biologicExpiry].filter(Boolean);
    const effectiveLOE = candidates.length > 0
        ? candidates.reduce((a, b) => a > b ? a : b)
        : null;
    // Days until LOE
    let daysUntilLOE = null;
    if (effectiveLOE) {
        const loeDate = new Date(effectiveLOE);
        const today = new Date();
        daysUntilLOE = Math.ceil((loeDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    }
    return {
        effectiveLOE,
        latestPatentExpiry: latestPatent,
        latestExclusivityExpiry: latestExcl,
        biologicExclusivityExpiry: biologicExpiry,
        daysUntilLOE,
    };
}
// ============================================
// Main Public API
// ============================================
/**
 * Get complete patent/exclusivity profile for a drug.
 * This is the main function called by the API endpoint.
 */
async function getDrugPatentProfile(drugName) {
    console.log(`  [Patents] Looking up "${drugName}"...`);
    // Step 1: Find approval info from OpenFDA
    const approvals = await searchDrugApprovals(drugName);
    if (approvals.length === 0) {
        console.log(`  [Patents] No FDA approvals found for "${drugName}"`);
        return null;
    }
    // Use the first (most relevant) approval
    const approval = approvals[0];
    console.log(`  [Patents] Found: ${approval.applicationNumber} (${approval.brandName}) - ${approval.sponsorName}`);
    // Step 2: Get Orange Book patents and exclusivities
    let patents = [];
    let exclusivities = [];
    if (approval.applicationType === 'NDA') {
        patents = await getPatentsForApplication(approval.applicationNumber);
        exclusivities = await getExclusivitiesForApplication(approval.applicationNumber);
        console.log(`  [Patents] Orange Book: ${patents.length} unique patents, ${exclusivities.length} exclusivities`);
    }
    else if (approval.applicationType === 'BLA') {
        console.log(`  [Patents] Biologic (BLA) — no Orange Book data; using BPCIA 12-year exclusivity`);
    }
    // Step 3: Calculate LOE
    const loe = calculateEffectiveLOE(patents, exclusivities, approval);
    // Extract unique patent numbers
    const uniquePatentNumbers = [...new Set(patents.map(p => p.patentNumber))];
    return {
        drugName: approval.genericName || drugName,
        brandName: approval.brandName,
        sponsor: approval.sponsorName,
        approval,
        patents,
        exclusivities,
        uniquePatentNumbers,
        earliestPatentExpiry: patents.length > 0
            ? patents.filter(p => p.expiryDateParsed).sort((a, b) => a.expiryDateParsed.localeCompare(b.expiryDateParsed))[0]?.expiryDateParsed || null
            : null,
        latestPatentExpiry: loe.latestPatentExpiry,
        latestExclusivityExpiry: loe.latestExclusivityExpiry,
        effectiveLOE: loe.effectiveLOE,
        biologicExclusivityExpiry: loe.biologicExclusivityExpiry,
        daysUntilLOE: loe.daysUntilLOE,
        fetchedAt: new Date().toISOString(),
    };
}
/**
 * Get patent profiles for all drugs used in trials for a condition.
 * Cross-references landscape molecules with patent data.
 */
async function getPatentsByCondition(condition) {
    console.log(`  [Patents] Finding patents for drugs in "${condition}"...`);
    // Load Orange Book product data to find drugs by ingredient
    await loadOrangeBookData();
    // Search OpenFDA for drugs approved for this condition
    const condNorm = condition.trim().toLowerCase();
    // Strategy: search OpenFDA for drugs matching the condition
    let drugNames = [];
    try {
        // Rate limit
        const now = Date.now();
        const elapsed = now - lastOpenFDACall;
        if (elapsed < OPENFDA_DELAY_MS) {
            await new Promise(r => setTimeout(r, OPENFDA_DELAY_MS - elapsed));
        }
        lastOpenFDACall = Date.now();
        const url = `${OPENFDA_DRUGSFDA_URL}?search=openfda.pharm_class_epc:"${encodeURIComponent(condNorm)}"&limit=100`;
        const response = await axios_1.default.get(url, { timeout: 15000 });
        if (response.data?.results) {
            for (const result of response.data.results) {
                for (const prod of (result.products || [])) {
                    if (prod.brand_name) {
                        const name = prod.brand_name.toLowerCase();
                        if (!drugNames.includes(name))
                            drugNames.push(name);
                    }
                }
            }
        }
    }
    catch (err) {
        // If pharmacologic class search fails, try indication search via Orange Book
        console.log(`  [Patents] Pharmacologic class search failed, trying product name search...`);
    }
    // Also search Orange Book products by ingredient/trade name matching condition keywords
    if (drugNames.length === 0) {
        // Fall back to finding well-known drugs in the Orange Book
        const condKeywords = condNorm.split(/\s+/);
        const obProducts = cachedProducts.filter(p => {
            const text = `${p.ingredient} ${p.tradeName}`.toLowerCase();
            return condKeywords.some(kw => text.includes(kw));
        });
        for (const prod of obProducts) {
            const name = prod.tradeName.toLowerCase();
            if (!drugNames.includes(name))
                drugNames.push(name);
        }
    }
    // Limit to top 20 drugs
    drugNames = drugNames.slice(0, 20);
    console.log(`  [Patents] Found ${drugNames.length} drugs to profile`);
    // Get patent profiles for each drug
    const profiles = [];
    for (const name of drugNames) {
        try {
            const profile = await getDrugPatentProfile(name);
            if (profile) {
                profiles.push(profile);
            }
        }
        catch (err) {
            console.error(`  [Patents] Error profiling "${name}":`, err.message);
        }
        // Rate limit between calls
        await new Promise(r => setTimeout(r, 400));
    }
    // Sort by LOE date
    profiles.sort((a, b) => {
        if (!a.effectiveLOE)
            return 1;
        if (!b.effectiveLOE)
            return -1;
        return a.effectiveLOE.localeCompare(b.effectiveLOE);
    });
    return profiles;
}
//# sourceMappingURL=patents.js.map