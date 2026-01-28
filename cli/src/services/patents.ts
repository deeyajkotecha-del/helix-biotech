/**
 * Patents & Exclusivity Service
 *
 * Provides patent and exclusivity data for FDA-approved drugs using:
 * - FDA Orange Book ZIP download (patents + exclusivities for NDA drugs)
 * - OpenFDA drugsfda API (drug approval lookup)
 * - BPCIA 12-year exclusivity calculation for biologics (BLA)
 */

import * as fs from 'fs';
import * as path from 'path';
import axios from 'axios';
import AdmZip from 'adm-zip';
import {
  DrugApproval,
  OrangeBookPatent,
  OrangeBookExclusivity,
  DrugPatentProfile,
} from '../types/schema';
import { searchTrialsByCondition } from './trials';
import { extractMoleculesFromTrials } from './molecules';

// ============================================
// Constants
// ============================================

const ORANGE_BOOK_ZIP_URL = 'https://www.fda.gov/media/76860/download';
const OPENFDA_DRUGSFDA_URL = 'https://api.fda.gov/drug/drugsfda.json';
const CACHE_DIR = path.resolve(__dirname, '..', '..', 'cache', 'patents');

// Exclusivity code descriptions
const EXCLUSIVITY_CODES: Record<string, string> = {
  'NCE': 'New Chemical Entity (5 years)',
  'NP': 'New Product (3 years)',
  'NPP': 'New Patient Population (3 years)',
  'NDA_AUTH': 'NDA-Authorized Generic',
  'ODE': 'Orphan Drug Exclusivity (7 years)',
  'PED': 'Pediatric Exclusivity (6 months)',
  'RTO': 'Right of Reference',
};

// In-memory cache for Orange Book data
let cachedProducts: OrangeBookProduct[] | null = null;
let cachedPatents: OrangeBookPatentRow[] | null = null;
let cachedExclusivities: OrangeBookExclusivityRow[] | null = null;
let cacheLoadedAt: number = 0;
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

// Rate limiting for OpenFDA
let lastOpenFDACall = 0;
const OPENFDA_DELAY_MS = 300;

// ============================================
// Internal Orange Book row types
// ============================================

interface OrangeBookProduct {
  ingredient: string;
  dfRoute: string;
  tradeName: string;
  applicant: string;
  strength: string;
  applType: string;
  applNo: string;
  productNo: string;
  teCode: string;
  approvalDate: string;
  rld: string;
  rs: string;
  type: string;
  applicantFullName: string;
}

interface OrangeBookPatentRow {
  applType: string;
  applNo: string;
  productNo: string;
  patentNo: string;
  patentExpireDateText: string;
  drugSubstanceFlag: string;
  drugProductFlag: string;
  patentUseCode: string;
  delistFlag: string;
  submissionDate: string;
}

interface OrangeBookExclusivityRow {
  applType: string;
  applNo: string;
  productNo: string;
  exclusivityCode: string;
  exclusivityDate: string;
}

// ============================================
// Orange Book Data Loading
// ============================================

/**
 * Download and parse the FDA Orange Book ZIP file.
 * Caches to disk and memory for 24 hours.
 */
async function loadOrangeBookData(): Promise<void> {
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

  let patentText: string;
  let exclusivityText: string;
  let productsText: string;

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
  } else {
    console.log('  [Patents] Downloading Orange Book ZIP from FDA...');
    const response = await axios.get(ORANGE_BOOK_ZIP_URL, {
      responseType: 'arraybuffer',
      timeout: 30000,
    });

    const zip = new AdmZip(Buffer.from(response.data));
    const entries = zip.getEntries();

    patentText = '';
    exclusivityText = '';
    productsText = '';

    for (const entry of entries) {
      const name = entry.entryName.toLowerCase();
      const content = entry.getData().toString('utf-8');
      if (name.includes('patent')) patentText = content;
      else if (name.includes('exclusivity')) exclusivityText = content;
      else if (name.includes('products')) productsText = content;
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
  cachedProducts = parseTildeDelimited<OrangeBookProduct>(productsText, [
    'ingredient', 'dfRoute', 'tradeName', 'applicant', 'strength',
    'applType', 'applNo', 'productNo', 'teCode', 'approvalDate',
    'rld', 'rs', 'type', 'applicantFullName',
  ]);

  cachedPatents = parseTildeDelimited<OrangeBookPatentRow>(patentText, [
    'applType', 'applNo', 'productNo', 'patentNo', 'patentExpireDateText',
    'drugSubstanceFlag', 'drugProductFlag', 'patentUseCode', 'delistFlag', 'submissionDate',
  ]);

  cachedExclusivities = parseTildeDelimited<OrangeBookExclusivityRow>(exclusivityText, [
    'applType', 'applNo', 'productNo', 'exclusivityCode', 'exclusivityDate',
  ]);

  cacheLoadedAt = Date.now();
  console.log(`  [Patents] Loaded: ${cachedProducts.length} products, ${cachedPatents.length} patent rows, ${cachedExclusivities.length} exclusivity rows`);
}

/**
 * Parse a tilde-delimited text file into objects
 */
function parseTildeDelimited<T>(text: string, fields: string[]): T[] {
  const lines = text.split('\n').filter(line => line.trim().length > 0);
  // Skip header row
  const dataLines = lines.slice(1);
  return dataLines.map(line => {
    const parts = line.split('~');
    const obj: Record<string, string> = {};
    for (let i = 0; i < fields.length; i++) {
      obj[fields[i]] = (parts[i] || '').trim();
    }
    return obj as unknown as T;
  });
}

/**
 * Parse an Orange Book date string like "Oct 17, 2036" to ISO date "2036-10-17"
 */
function parseOBDate(dateStr: string): string | null {
  if (!dateStr || dateStr.trim() === '') return null;
  const d = new Date(dateStr.trim());
  if (isNaN(d.getTime())) return null;
  return d.toISOString().split('T')[0];
}

// ============================================
// OpenFDA Drug Lookup
// ============================================

/**
 * Search OpenFDA drugsfda endpoint for a drug by name.
 * Returns approval information including application number.
 */
export async function searchDrugApprovals(drugName: string): Promise<DrugApproval[]> {
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

  const allResults: DrugApproval[] = [];

  for (const search of searches) {
    try {
      const url = `${OPENFDA_DRUGSFDA_URL}?search=${encodeURIComponent(search)}&limit=5`;
      const response = await axios.get(url, { timeout: 15000 });

      if (response.data?.results) {
        for (const result of response.data.results) {
          const applNo = result.application_number || '';
          const isBiologic = applNo.startsWith('BLA');
          const applType = isBiologic ? 'BLA' : applNo.startsWith('ANDA') ? 'ANDA' : 'NDA';

          // Extract original approval date from submissions
          // Prefer ORIG submission (original application), fall back to earliest AP
          let approvalDate: string | undefined;
          if (result.submissions?.length > 0) {
            // First try to find the ORIG (original) submission
            const origSubmission = result.submissions.find(
              (s: any) => s.submission_type === 'ORIG'
            );
            if (origSubmission?.submission_status_date) {
              const dateStr = origSubmission.submission_status_date;
              approvalDate = `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
            } else {
              // Fall back to the earliest approved submission
              const approvedSubs = result.submissions
                .filter((s: any) => s.submission_status === 'AP' && s.submission_status_date)
                .sort((a: any, b: any) => (a.submission_status_date || '').localeCompare(b.submission_status_date || ''));
              if (approvedSubs.length > 0) {
                const dateStr = approvedSubs[0].submission_status_date;
                approvalDate = `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
              }
            }
          }

          const products = result.products || [];
          const activeIngredients: { name: string; strength?: string }[] = [];
          const productNumbers: string[] = [];
          let brandName = '';
          let genericName = '';
          let dosageForm = '';
          let route = '';

          for (const prod of products) {
            if (prod.brand_name && !brandName) brandName = prod.brand_name;
            if (prod.dosage_form && !dosageForm) dosageForm = prod.dosage_form;
            if (prod.route && !route) route = prod.route;
            if (prod.product_number) productNumbers.push(prod.product_number);
            if (prod.active_ingredients) {
              for (const ai of prod.active_ingredients) {
                genericName = ai.name || genericName;
                const existing = activeIngredients.find(
                  (x: { name: string }) => x.name === ai.name
                );
                if (!existing) {
                  activeIngredients.push({ name: ai.name, strength: ai.strength });
                }
              }
            }
          }

          // Avoid duplicates
          if (allResults.some((a: DrugApproval) => a.applicationNumber === applNo)) continue;

          allResults.push({
            applicationNumber: applNo,
            applicationType: applType as 'NDA' | 'BLA' | 'ANDA',
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
    } catch (err: any) {
      if (err.response?.status === 404) continue;
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
export async function getPatentsForApplication(applicationNumber: string): Promise<OrangeBookPatent[]> {
  await loadOrangeBookData();

  // Extract numeric part: "NDA211675" -> "211675"
  const applNo = applicationNumber.replace(/^(NDA|BLA|ANDA)/i, '').trim();

  const matches = cachedPatents!.filter(p => p.applNo === applNo);

  // Deduplicate by patent number (keep unique patents)
  const seen = new Map<string, OrangeBookPatent>();
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
    if (!a.expiryDateParsed) return 1;
    if (!b.expiryDateParsed) return -1;
    return b.expiryDateParsed.localeCompare(a.expiryDateParsed);
  });

  return patents;
}

/**
 * Get Orange Book exclusivities for a given application number.
 */
export async function getExclusivitiesForApplication(applicationNumber: string): Promise<OrangeBookExclusivity[]> {
  await loadOrangeBookData();

  const applNo = applicationNumber.replace(/^(NDA|BLA|ANDA)/i, '').trim();
  const matches = cachedExclusivities!.filter(e => e.applNo === applNo);

  return matches.map(row => {
    const code = row.exclusivityCode;
    // Determine exclusivity type from code
    let exclusivityType = '';
    if (code.startsWith('NCE')) exclusivityType = 'New Chemical Entity (5 years)';
    else if (code.startsWith('NP') && !code.startsWith('NPP')) exclusivityType = 'New Product (3 years)';
    else if (code.startsWith('NPP')) exclusivityType = 'New Patient Population (3 years)';
    else if (code.startsWith('ODE')) exclusivityType = 'Orphan Drug Exclusivity (7 years)';
    else if (code.startsWith('PED')) exclusivityType = 'Pediatric Exclusivity (6 months added)';
    else if (code.startsWith('I-')) exclusivityType = `New Indication Exclusivity (3 years)`;
    else if (code.startsWith('D-')) exclusivityType = `New Dosage Form Exclusivity`;
    else if (code.startsWith('RTO')) exclusivityType = 'Right of Reference';
    else exclusivityType = EXCLUSIVITY_CODES[code] || code;

    return {
      exclusivityCode: code,
      exclusivityDate: row.exclusivityDate,
      exclusivityDateParsed: parseOBDate(row.exclusivityDate) || '',
      exclusivityType,
      applicationNumber,
      productNumber: row.productNo,
    };
  }).sort((a, b) => {
    if (!a.exclusivityDateParsed) return 1;
    if (!b.exclusivityDateParsed) return -1;
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
export function calculateEffectiveLOE(
  patents: OrangeBookPatent[],
  exclusivities: OrangeBookExclusivity[],
  approval?: DrugApproval,
): {
  effectiveLOE: string | null;
  latestPatentExpiry: string | null;
  latestExclusivityExpiry: string | null;
  biologicExclusivityExpiry: string | null;
  daysUntilLOE: number | null;
} {
  // Latest patent expiry
  let latestPatent: string | null = null;
  for (const p of patents) {
    if (p.expiryDateParsed && (!latestPatent || p.expiryDateParsed > latestPatent)) {
      latestPatent = p.expiryDateParsed;
    }
  }

  // Latest exclusivity expiry
  let latestExcl: string | null = null;
  for (const e of exclusivities) {
    if (e.exclusivityDateParsed && (!latestExcl || e.exclusivityDateParsed > latestExcl)) {
      latestExcl = e.exclusivityDateParsed;
    }
  }

  // Biologic exclusivity (12 years from approval under BPCIA)
  let biologicExpiry: string | null = null;
  if (approval?.isBiologic && approval.approvalDate) {
    const approvalDate = new Date(approval.approvalDate);
    approvalDate.setFullYear(approvalDate.getFullYear() + 12);
    biologicExpiry = approvalDate.toISOString().split('T')[0];
  }

  // Effective LOE = latest of all protections
  const candidates = [latestPatent, latestExcl, biologicExpiry].filter(Boolean) as string[];
  const effectiveLOE = candidates.length > 0
    ? candidates.reduce((a, b) => a > b ? a : b)
    : null;

  // Days until LOE
  let daysUntilLOE: number | null = null;
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
export async function getDrugPatentProfile(drugName: string): Promise<DrugPatentProfile | null> {
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
  let patents: OrangeBookPatent[] = [];
  let exclusivities: OrangeBookExclusivity[] = [];

  if (approval.applicationType === 'NDA') {
    patents = await getPatentsForApplication(approval.applicationNumber);
    exclusivities = await getExclusivitiesForApplication(approval.applicationNumber);
    console.log(`  [Patents] Orange Book: ${patents.length} unique patents, ${exclusivities.length} exclusivities`);
  } else if (approval.applicationType === 'BLA') {
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
 * Uses ClinicalTrials.gov molecules pipeline to find drugs, then looks up patents.
 */
export async function getPatentsByCondition(condition: string): Promise<DrugPatentProfile[]> {
  console.log(`  [Patents] Finding patents for drugs in "${condition}"...`);

  // Step 1: Find molecules via ClinicalTrials.gov (same pipeline as /api/landscape/:condition/molecules)
  console.log(`  [Patents] Fetching trials from ClinicalTrials.gov...`);
  const trials = await searchTrialsByCondition(condition, { maxResults: 200 });
  console.log(`  [Patents] Found ${trials.length} trials, extracting molecules...`);

  const molecules = extractMoleculesFromTrials(trials);
  console.log(`  [Patents] Extracted ${molecules.length} total molecules`);

  // Step 2: Filter to late-stage molecules (Phase 3+) that are likely FDA-approved
  const PHASE_RANK: Record<string, number> = {
    'Phase 4': 5, 'Phase 3': 4, 'Phase 2/3': 3, 'Phase 2': 2,
    'Phase 1/2': 1, 'Phase 1': 0, 'Preclinical': -1, 'Not Applicable': -2,
  };
  const lateStage = molecules
    .filter(m => (PHASE_RANK[m.highestPhase] ?? -1) >= 3) // Phase 2/3 and above
    .sort((a, b) => (PHASE_RANK[b.highestPhase] ?? 0) - (PHASE_RANK[a.highestPhase] ?? 0) || b.trialCount - a.trialCount);

  // Take top 15 molecules
  const candidates = lateStage.slice(0, 15);
  console.log(`  [Patents] ${lateStage.length} late-stage molecules, profiling top ${candidates.length}...`);

  // Step 3: Look up patents for each molecule
  const profiles: DrugPatentProfile[] = [];
  for (const mol of candidates) {
    // Try the molecule name, then aliases
    const namesToTry = [mol.name, ...mol.aliases.slice(0, 2)];
    let found = false;

    for (const name of namesToTry) {
      if (found) break;
      try {
        const profile = await getDrugPatentProfile(name);
        if (profile) {
          profiles.push(profile);
          found = true;
          console.log(`  [Patents]   + ${profile.brandName} (${profile.approval.applicationType}) — LOE: ${profile.effectiveLOE || 'unknown'}`);
        }
      } catch (err: any) {
        // Try next alias
      }
      await new Promise(r => setTimeout(r, 400));
    }

    if (!found) {
      console.log(`  [Patents]   - ${mol.name}: not found in FDA`);
    }
  }

  // Deduplicate by application number
  const seen = new Set<string>();
  const deduped = profiles.filter(p => {
    if (seen.has(p.approval.applicationNumber)) return false;
    seen.add(p.approval.applicationNumber);
    return true;
  });

  // Sort by LOE date
  deduped.sort((a, b) => {
    if (!a.effectiveLOE) return 1;
    if (!b.effectiveLOE) return -1;
    return a.effectiveLOE.localeCompare(b.effectiveLOE);
  });

  console.log(`  [Patents] Complete: ${deduped.length} drug profiles with patent data`);
  return deduped;
}
