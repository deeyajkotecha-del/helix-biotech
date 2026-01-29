/**
 * Asset Research Engine
 *
 * Intelligent multi-source research for therapeutic target assets.
 * Combines clinical trials, publications, and curated databases
 * to produce comprehensive competitive intelligence.
 */

import { Trial } from '../types/schema';
import {
  KnownAsset,
  getTargetDatabase,
  findKnownAsset,
  isExcludedDrug,
  isTargetRelatedIntervention,
  getKnownAssetsForTarget,
} from '../data/known-assets';
import { searchTrialsByCondition, searchTrialsByIntervention } from './trials';
import { searchPublications } from './publications';

// ============================================
// Types
// ============================================

export interface ResearchedAsset {
  // Identity
  drugName: string;
  codeName?: string;
  genericName?: string;
  aliases: string[];

  // Classification
  target: string;
  modality: string;
  payload?: string;

  // Ownership
  owner: string;
  ownerType: 'Big Pharma' | 'Biotech' | 'Chinese Biotech' | 'Academic' | 'Other';
  partner?: string;

  // Development
  phase: string;
  status: 'Active' | 'Completed' | 'Terminated' | 'On Hold' | 'Unknown';
  leadIndication: string;
  otherIndications: string[];

  // Evidence
  trialCount: number;
  trialIds: string[];
  publicationCount: number;

  // Deal info
  dealTerms?: string;
  dealDate?: string;

  // Analysis
  notes?: string;
  differentiator?: string;
  dataSource: 'Known Database' | 'Clinical Trials' | 'Publications' | 'Multiple';
  confidence: 'High' | 'Medium' | 'Low';
  lastUpdated: string;
}

export interface AssetResearchReport {
  target: string;
  generatedAt: string;

  // Assets
  assets: ResearchedAsset[];

  // Summary stats
  summary: {
    totalAssets: number;
    byModality: Record<string, number>;
    byPhase: Record<string, number>;
    byOwnerType: Record<string, number>;
    byGeography: Record<string, number>;
  };

  // Data quality
  knownAssetsFound: number;
  newAssetsDiscovered: number;
  excludedDrugs: number;
}

// ============================================
// Main Research Function
// ============================================

/**
 * Research all assets for a therapeutic target
 */
export async function researchTargetAssets(target: string): Promise<AssetResearchReport> {
  console.log(`[AssetResearch] Starting research for target: ${target}`);
  const startTime = Date.now();

  // Step 1: Get known assets from curated database
  const knownAssets = getKnownAssetsForTarget(target);
  console.log(`[AssetResearch] Found ${knownAssets.length} known assets in database`);

  // Step 2: Search clinical trials
  const trials = await fetchAllTrialsForTarget(target);
  console.log(`[AssetResearch] Found ${trials.length} clinical trials`);

  // Step 3: Extract and filter interventions
  const extractedAssets = extractAssetsFromTrials(trials, target);
  console.log(`[AssetResearch] Extracted ${extractedAssets.length} unique interventions`);

  // Step 4: Merge known assets with extracted assets
  const mergedAssets = mergeAssets(knownAssets, extractedAssets, target);
  console.log(`[AssetResearch] Merged to ${mergedAssets.length} final assets`);

  // Step 5: Calculate summary statistics
  const summary = calculateSummary(mergedAssets);

  const report: AssetResearchReport = {
    target,
    generatedAt: new Date().toISOString(),
    assets: mergedAssets,
    summary,
    knownAssetsFound: knownAssets.length,
    newAssetsDiscovered: mergedAssets.length - knownAssets.length,
    excludedDrugs: extractedAssets.filter(a => a.excluded).length,
  };

  console.log(`[AssetResearch] Completed in ${Date.now() - startTime}ms`);
  return report;
}

// ============================================
// Data Collection
// ============================================

/**
 * Fetch trials from multiple search strategies
 */
async function fetchAllTrialsForTarget(target: string): Promise<Trial[]> {
  const db = getTargetDatabase(target);
  const searchTerms = db
    ? [db.target, ...db.aliases]
    : [target];

  const allTrials: Trial[] = [];
  const seen = new Set<string>();

  for (const term of searchTerms) {
    try {
      // Search by condition
      const conditionTrials = await searchTrialsByCondition(term, { maxResults: 100 });
      for (const t of conditionTrials) {
        if (!seen.has(t.nctId)) {
          seen.add(t.nctId);
          allTrials.push(t);
        }
      }

      // Search by intervention
      const interventionTrials = await searchTrialsByIntervention(term, { maxResults: 100 });
      for (const t of interventionTrials) {
        if (!seen.has(t.nctId)) {
          seen.add(t.nctId);
          allTrials.push(t);
        }
      }
    } catch (error) {
      console.error(`[AssetResearch] Error searching for ${term}: ${error}`);
    }
  }

  return allTrials;
}

// ============================================
// Asset Extraction
// ============================================

interface ExtractedIntervention {
  name: string;
  normalizedName: string;
  type: string;
  description?: string;
  sponsor: string;
  sponsorType: string;
  phase: string;
  status: string;
  conditions: string[];
  trialId: string;
  trialStartDate?: string;
  isTargetRelated: boolean;
  knownAsset: KnownAsset | null;
  excluded: boolean;
  excludeReason?: string;
}

/**
 * Extract and classify interventions from trials
 */
function extractAssetsFromTrials(
  trials: Trial[],
  target: string
): ExtractedIntervention[] {
  const interventionMap = new Map<string, ExtractedIntervention>();

  for (const trial of trials) {
    for (const intervention of trial.interventions || []) {
      if (!intervention.name) continue;

      const name = intervention.name;
      const normalizedName = normalizeDrugName(name);

      // Check if excluded
      let excluded = false;
      let excludeReason: string | undefined;

      if (isExcludedDrug(name, target)) {
        excluded = true;
        excludeReason = 'Generic/supportive care drug';
      }

      // Check if target-related (strict check)
      const isRelated = isTargetRelatedIntervention(
        name,
        intervention.description,
        target
      );

      // Try to find known asset
      const knownAsset = findKnownAsset(name, target);

      // STRICT FILTERING: Only include if we're confident this drug targets our target
      // Priority 1: Known asset from curated database (HIGH confidence)
      // Priority 2: Drug name/description explicitly mentions target (MEDIUM confidence)
      // EXCLUDE: Everything else - better to miss than to include false positives
      if (!knownAsset && !isRelated && !isLikelyTargetDrug(name, target)) {
        continue;
      }

      const key = knownAsset?.primaryName.toLowerCase() || normalizedName;

      if (!interventionMap.has(key)) {
        interventionMap.set(key, {
          name: knownAsset?.primaryName || name,
          normalizedName,
          type: intervention.type,
          description: intervention.description,
          sponsor: trial.leadSponsor?.name || 'Unknown',
          sponsorType: trial.leadSponsor?.type || 'Other',
          phase: trial.phase,
          status: normalizeStatus(trial.status),
          conditions: trial.conditions || [],
          trialId: trial.nctId,
          trialStartDate: trial.startDate,
          isTargetRelated: isRelated,
          knownAsset,
          excluded,
          excludeReason,
        });
      } else {
        // Update existing entry with more info
        const existing = interventionMap.get(key)!;
        // Keep the most advanced phase
        existing.phase = getMostAdvancedPhase([existing.phase, trial.phase]);
        // Add conditions
        for (const cond of trial.conditions || []) {
          if (!existing.conditions.includes(cond)) {
            existing.conditions.push(cond);
          }
        }
      }
    }
  }

  return Array.from(interventionMap.values());
}

/**
 * Check if drug name looks like a target-specific drug
 *
 * STRICT MODE: Only return true if we have HIGH confidence this drug targets
 * the specific target. False positives destroy credibility.
 */
function isLikelyTargetDrug(name: string, target: string): boolean {
  const lower = name.toLowerCase();
  const targetLower = target.toLowerCase().replace(/[-\s]/g, '');

  // STRICT: Must contain target name in the drug name itself
  // This is the only reliable way to link a drug to a target
  if (lower.replace(/[-\s]/g, '').includes(targetLower)) return true;

  // Check for explicit "anti-TARGET" patterns
  if (lower.includes(`anti-${targetLower}`) || lower.includes(`anti ${targetLower}`)) return true;

  // REMOVED: Generic modality patterns (ADC, CAR-T, bispecific)
  // These patterns are too loose - an ADC could target ANY target
  // Just because a drug is an ADC doesn't mean it targets our specific target

  // REMOVED: Company code patterns (e.g., DS-7300)
  // A company code tells us nothing about the target
  // DS-7300 could target B7-H3 or HER2 or anything else

  // DEFAULT: When in doubt, exclude
  // It's better to miss a real asset than to include a false one
  return false;
}

// ============================================
// Asset Merging
// ============================================

/**
 * Merge known assets with extracted assets
 */
function mergeAssets(
  knownAssets: KnownAsset[],
  extracted: ExtractedIntervention[],
  target: string
): ResearchedAsset[] {
  const results: ResearchedAsset[] = [];
  const addedNames = new Set<string>();

  // First add all known assets, enriched with trial data
  for (const known of knownAssets) {
    const matchingExtracted = extracted.filter(e =>
      e.knownAsset?.primaryName === known.primaryName ||
      e.normalizedName === normalizeDrugName(known.primaryName)
    );

    const trialIds = matchingExtracted.map(e => e.trialId);
    const conditions = new Set<string>();
    for (const e of matchingExtracted) {
      e.conditions.forEach(c => conditions.add(c));
    }

    results.push({
      drugName: known.primaryName,
      codeName: known.codeNames?.[0],
      genericName: known.genericName,
      aliases: known.aliases,
      target: known.target,
      modality: known.modality,
      payload: known.payload,
      owner: known.owner,
      ownerType: known.ownerType,
      partner: known.partner,
      phase: known.phase,
      status: known.status === 'Active' ? 'Active' : known.status === 'Discontinued' ? 'Terminated' : 'Unknown',
      leadIndication: known.leadIndication,
      otherIndications: known.otherIndications || [],
      trialCount: trialIds.length,
      trialIds,
      publicationCount: 0,
      dealTerms: known.deal?.headline,
      dealDate: known.deal?.date,
      notes: known.notes,
      differentiator: known.differentiator,
      dataSource: trialIds.length > 0 ? 'Multiple' : 'Known Database',
      confidence: 'High',
      lastUpdated: new Date().toISOString(),
    });

    addedNames.add(known.primaryName.toLowerCase());
    addedNames.add(normalizeDrugName(known.primaryName));
    for (const codeName of known.codeNames || []) {
      addedNames.add(codeName.toLowerCase());
      addedNames.add(normalizeDrugName(codeName));
    }
    if (known.genericName) {
      addedNames.add(known.genericName.toLowerCase());
      addedNames.add(normalizeDrugName(known.genericName));
    }
    // Add all aliases
    for (const alias of known.aliases) {
      addedNames.add(alias.toLowerCase());
      addedNames.add(normalizeDrugName(alias));
    }
  }

  // Then add extracted assets not in known database
  for (const item of extracted) {
    if (item.excluded) continue;
    if (addedNames.has(item.normalizedName)) continue;
    if (addedNames.has(item.name.toLowerCase())) continue;
    if (item.knownAsset) continue; // Already added via known assets

    // Classify modality from intervention
    const modality = classifyModality(item.name, item.type, item.description);

    // Assign confidence based on how well we can verify target relationship
    // HIGH: In curated database (already handled above)
    // MEDIUM: Drug name or description explicitly mentions target
    // LOW: Only indirect evidence - EXCLUDE from default reports
    const confidence = item.isTargetRelated ? 'Medium' : 'Low';

    // SKIP LOW confidence assets - they're likely false positives
    // False positives destroy credibility more than missing assets
    if (confidence === 'Low') {
      continue;
    }

    results.push({
      drugName: item.name,
      aliases: [],
      target,
      modality,
      owner: item.sponsor,
      ownerType: classifyOwnerType(item.sponsor),
      phase: item.phase,
      status: item.status as ResearchedAsset['status'],
      leadIndication: item.conditions[0] || 'Solid tumors',
      otherIndications: item.conditions.slice(1),
      trialCount: 1, // TODO: Aggregate across trials
      trialIds: [item.trialId],
      publicationCount: 0,
      dataSource: 'Clinical Trials',
      confidence,
      lastUpdated: new Date().toISOString(),
    });

    addedNames.add(item.normalizedName);
  }

  // Sort by phase (most advanced first), then by trial count
  return results.sort((a, b) => {
    const phaseOrder = ['Approved', 'Filed', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Preclinical'];
    const aPhaseIndex = phaseOrder.indexOf(a.phase);
    const bPhaseIndex = phaseOrder.indexOf(b.phase);
    if (aPhaseIndex !== bPhaseIndex) {
      return (aPhaseIndex === -1 ? 999 : aPhaseIndex) - (bPhaseIndex === -1 ? 999 : bPhaseIndex);
    }
    return b.trialCount - a.trialCount;
  });
}

// ============================================
// Classification Functions
// ============================================

/**
 * Classify modality from drug name and intervention type
 */
function classifyModality(
  name: string,
  type: string,
  description?: string
): string {
  const text = `${name} ${description || ''}`.toLowerCase();

  if (text.includes('adc') || text.includes('antibody-drug conjugate') ||
      text.includes('deruxtecan') || text.includes('vedotin') ||
      text.includes('duocarmazine') || text.includes('mafodotin') ||
      text.includes('govitecan') || text.includes('emtansine')) {
    return 'ADC';
  }

  if (text.includes('car-t') || text.includes('cart') || text.includes('car t') ||
      text.includes('chimeric antigen receptor')) {
    return 'CAR-T';
  }

  if (text.includes('bispecific') || text.includes('bite') || text.includes('dart')) {
    return 'Bispecific';
  }

  if (text.includes('radioimmuno') || text.includes('radiopharm') ||
      text.includes('lutetium') || text.includes('iodine-131') || text.includes('actinium')) {
    return 'Radioconjugate';
  }

  if (type === 'Biological' || text.includes('antibody') || text.includes('mab')) {
    return 'mAb';
  }

  if (type === 'Drug' || text.includes('inhibitor')) {
    return 'Small Molecule';
  }

  return 'Other';
}

/**
 * Classify owner type from sponsor name
 */
function classifyOwnerType(sponsor: string): ResearchedAsset['ownerType'] {
  const lower = sponsor.toLowerCase();

  // Big Pharma
  const bigPharma = [
    'merck', 'pfizer', 'novartis', 'roche', 'johnson', 'abbvie', 'bms',
    'bristol-myers', 'astrazeneca', 'sanofi', 'gsk', 'glaxo', 'lilly',
    'amgen', 'gilead', 'takeda', 'daiichi', 'boehringer'
  ];
  if (bigPharma.some(p => lower.includes(p))) return 'Big Pharma';

  // Chinese Biotech
  const chineseBiotech = [
    'hansoh', 'hengrui', 'beigene', 'innovent', 'junshi', 'zai lab',
    'simcere', 'kelun', 'luye', 'alphamab', 'chia tai', 'shanghai',
    'beijing', 'china', 'chinese', 'sichuan', 'jiangsu', 'nanjing',
    'fudan', 'peking', 'tsinghua'
  ];
  if (chineseBiotech.some(p => lower.includes(p))) return 'Chinese Biotech';

  // Academic
  const academic = [
    'university', 'college', 'institute', 'hospital', 'medical center',
    'cancer center', 'memorial sloan', 'md anderson', 'dana-farber',
    'mayo clinic', 'cleveland clinic', 'nih', 'national cancer'
  ];
  if (academic.some(p => lower.includes(p))) return 'Academic';

  // Default to Biotech
  return 'Biotech';
}

// ============================================
// Summary Statistics
// ============================================

function calculateSummary(assets: ResearchedAsset[]) {
  const byModality: Record<string, number> = {};
  const byPhase: Record<string, number> = {};
  const byOwnerType: Record<string, number> = {};
  const byGeography: Record<string, number> = {};

  for (const asset of assets) {
    byModality[asset.modality] = (byModality[asset.modality] || 0) + 1;
    byPhase[asset.phase] = (byPhase[asset.phase] || 0) + 1;
    byOwnerType[asset.ownerType] = (byOwnerType[asset.ownerType] || 0) + 1;

    // Geography
    let geo = 'Other';
    if (asset.ownerType === 'Chinese Biotech') geo = 'China';
    else if (['Big Pharma', 'Biotech'].includes(asset.ownerType)) geo = 'US/EU';
    else if (asset.ownerType === 'Academic') geo = 'Academic';
    byGeography[geo] = (byGeography[geo] || 0) + 1;
  }

  return {
    totalAssets: assets.length,
    byModality,
    byPhase,
    byOwnerType,
    byGeography,
  };
}

// ============================================
// Utility Functions
// ============================================

function normalizeDrugName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\([^)]*\)/g, '') // Remove parenthetical content like (I-DXd)
    .replace(/[-\s]+/g, '')
    .replace(/\d+\s*(mg|mcg|ml|iu)/gi, '')
    .trim();
}

function normalizeStatus(status: string): string {
  if (['Recruiting', 'Active, not recruiting', 'Enrolling by invitation', 'Not yet recruiting'].includes(status)) {
    return 'Active';
  }
  if (status === 'Completed') return 'Completed';
  if (['Terminated', 'Withdrawn'].includes(status)) return 'Terminated';
  if (status === 'Suspended') return 'On Hold';
  return 'Unknown';
}

function getMostAdvancedPhase(phases: string[]): string {
  const phaseOrder = ['Approved', 'Filed', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Early Phase 1', 'Preclinical', 'Not Applicable'];

  for (const phase of phaseOrder) {
    for (const p of phases) {
      if (p.toLowerCase().includes(phase.toLowerCase().replace(' ', ''))) return phase;
      if (p === phase) return phase;
    }
  }

  return phases[0] || 'Unknown';
}

// ============================================
// Export for HTML formatting
// ============================================

export function formatAssetForDisplay(asset: ResearchedAsset): {
  drugName: string;
  modality: string;
  target: string;
  payload: string;
  owner: string;
  partner: string;
  phase: string;
  status: string;
  leadIndication: string;
  dealTerms: string;
  notes: string;
  confidence: string;
  trialCount: number;
} {
  return {
    drugName: `${asset.drugName}${asset.codeName ? ` (${asset.codeName})` : ''}`,
    modality: asset.modality,
    target: asset.target,
    payload: asset.payload || '-',
    owner: asset.owner,
    partner: asset.partner || '-',
    phase: asset.phase,
    status: asset.status,
    leadIndication: asset.leadIndication,
    dealTerms: asset.dealTerms || '-',
    notes: asset.notes || asset.differentiator || '-',
    confidence: asset.confidence,
    trialCount: asset.trialCount,
  };
}
