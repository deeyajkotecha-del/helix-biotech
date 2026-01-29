/**
 * Asset Research Engine - Multi-Layer Verification
 *
 * Discovers and verifies therapeutic assets for any target.
 * Uses strict multi-layer filtering to prevent false positives.
 *
 * PRINCIPLE: Accuracy over completeness.
 * Better to miss a real asset than to include a false one.
 */

import { Trial } from '../types/schema';
import {
  KnownAsset,
  getTargetDatabase,
  findKnownAsset,
  getKnownAssetsForTarget,
} from '../data/known-assets';
import {
  TargetInfo,
  getTargetInfo,
  getTargetVariants,
  isCommonNonTargetDrug,
  inferTargetInfo,
} from '../data/target-aliases';
import { searchTrialsByCondition, searchTrialsByIntervention } from './trials';

// ============================================
// Types
// ============================================

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'EXCLUDE';

export interface VerifiedAsset {
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

  // Verification
  confidence: ConfidenceLevel;
  verificationMethod: 'curated_database' | 'name_match' | 'mechanism_match' | 'trial_association';
  verificationDetails?: string;

  // Analysis
  notes?: string;
  differentiator?: string;
  lastUpdated: string;
}

export interface AssetDiscoveryResult {
  target: string;
  targetInfo: TargetInfo;
  generatedAt: string;

  // Categorized assets
  verified: VerifiedAsset[];      // HIGH confidence - show by default
  probable: VerifiedAsset[];      // MEDIUM confidence - show with caution
  unverified: VerifiedAsset[];    // LOW confidence - hide by default

  // Summary
  summary: {
    totalVerified: number;
    totalProbable: number;
    totalUnverified: number;
    totalExcluded: number;
    byModality: Record<string, number>;
    byPhase: Record<string, number>;
  };
}

// ============================================
// Main Discovery Function
// ============================================

/**
 * Discover and verify assets for a therapeutic target.
 * Uses multi-layer filtering to ensure accuracy.
 */
export async function discoverAssets(target: string): Promise<AssetDiscoveryResult> {
  console.log(`[AssetDiscovery] Starting multi-layer verification for: ${target}`);
  const startTime = Date.now();

  // Get target info (aliases, mechanisms)
  const targetInfo = getTargetInfo(target) || inferTargetInfo(target);
  console.log(`[AssetDiscovery] Target variants: ${targetInfo.aliases.join(', ')}`);

  // LAYER 1: Curated Database (Highest Trust)
  const curatedAssets = getCuratedAssetsWithHighConfidence(target);
  console.log(`[AssetDiscovery] Layer 1 - Curated: ${curatedAssets.length} assets`);

  // Fetch trials for discovery
  const trials = await fetchTrialsForTarget(target, targetInfo);
  console.log(`[AssetDiscovery] Found ${trials.length} trials to analyze`);

  // LAYERS 2-5: Multi-layer verification of discovered assets
  const { discovered, excluded } = extractAndVerifyInterventions(trials, target, targetInfo);
  console.log(`[AssetDiscovery] Layers 2-5 - Discovered: ${discovered.length}, Excluded: ${excluded}`);

  // Merge curated + discovered, deduplicate
  const allAssets = mergeAndDeduplicate(curatedAssets, discovered);

  // Categorize by confidence
  const verified = allAssets.filter(a => a.confidence === 'HIGH');
  const probable = allAssets.filter(a => a.confidence === 'MEDIUM');
  const unverified = allAssets.filter(a => a.confidence === 'LOW');

  // Calculate summary
  const summary = calculateSummary(allAssets, excluded);

  console.log(`[AssetDiscovery] Complete in ${Date.now() - startTime}ms`);
  console.log(`[AssetDiscovery] Results: ${verified.length} verified, ${probable.length} probable, ${unverified.length} unverified`);

  return {
    target,
    targetInfo,
    generatedAt: new Date().toISOString(),
    verified,
    probable,
    unverified,
    summary,
  };
}

// ============================================
// LAYER 1: Curated Database
// ============================================

/**
 * Get curated assets from known-assets.ts with HIGH confidence
 */
function getCuratedAssetsWithHighConfidence(target: string): VerifiedAsset[] {
  const knownAssets = getKnownAssetsForTarget(target);

  return knownAssets.map(asset => ({
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
    status: asset.status === 'Active' ? 'Active' : asset.status === 'Discontinued' ? 'Terminated' : 'Unknown',
    leadIndication: asset.leadIndication,
    otherIndications: asset.otherIndications || [],
    trialCount: asset.trialIds?.length || 0,
    trialIds: asset.trialIds || [],
    publicationCount: 0,
    dealTerms: asset.deal?.headline,
    dealDate: asset.deal?.date,
    confidence: 'HIGH' as ConfidenceLevel,
    verificationMethod: 'curated_database' as const,
    verificationDetails: 'Pre-verified in curated database with sources',
    notes: asset.notes,
    differentiator: asset.differentiator,
    lastUpdated: new Date().toISOString(),
  }));
}

// ============================================
// Trial Fetching
// ============================================

async function fetchTrialsForTarget(target: string, targetInfo: TargetInfo): Promise<Trial[]> {
  const allTrials: Trial[] = [];
  const seen = new Set<string>();

  // Search by all target variants
  const searchTerms = [...new Set([target, ...targetInfo.aliases])];

  for (const term of searchTerms.slice(0, 3)) {  // Limit to avoid too many API calls
    try {
      const conditionTrials = await searchTrialsByCondition(term, { maxResults: 100 });
      for (const t of conditionTrials) {
        if (!seen.has(t.nctId)) {
          seen.add(t.nctId);
          allTrials.push(t);
        }
      }

      const interventionTrials = await searchTrialsByIntervention(term, { maxResults: 50 });
      for (const t of interventionTrials) {
        if (!seen.has(t.nctId)) {
          seen.add(t.nctId);
          allTrials.push(t);
        }
      }
    } catch (error) {
      console.error(`[AssetDiscovery] Error searching for ${term}: ${error}`);
    }
  }

  return allTrials;
}

// ============================================
// LAYERS 2-5: Multi-Layer Verification
// ============================================

interface ExtractionResult {
  discovered: VerifiedAsset[];
  excluded: number;
}

function extractAndVerifyInterventions(
  trials: Trial[],
  target: string,
  targetInfo: TargetInfo
): ExtractionResult {
  const assetMap = new Map<string, VerifiedAsset>();
  let excludedCount = 0;

  for (const trial of trials) {
    for (const intervention of trial.interventions || []) {
      if (!intervention.name) continue;

      const name = intervention.name;
      const description = intervention.description || '';
      const normalizedName = normalizeDrugName(name);

      // Skip if already in curated database (will be added separately)
      const knownAsset = findKnownAsset(name, target);
      if (knownAsset) continue;

      // Apply multi-layer verification
      const verification = verifyIntervention(name, description, target, targetInfo);

      if (verification.confidence === 'EXCLUDE') {
        excludedCount++;
        continue;
      }

      // Use normalized name as key for deduplication
      const key = normalizedName;

      if (!assetMap.has(key)) {
        const modality = classifyModality(name, intervention.type, description);

        assetMap.set(key, {
          drugName: name,
          aliases: [],
          target,
          modality,
          owner: trial.leadSponsor?.name || 'Unknown',
          ownerType: classifyOwnerType(trial.leadSponsor?.name || ''),
          phase: trial.phase || 'Unknown',
          status: normalizeStatus(trial.status),
          leadIndication: trial.conditions?.[0] || 'Unknown',
          otherIndications: trial.conditions?.slice(1) || [],
          trialCount: 1,
          trialIds: [trial.nctId],
          publicationCount: 0,
          confidence: verification.confidence,
          verificationMethod: verification.method,
          verificationDetails: verification.details,
          lastUpdated: new Date().toISOString(),
        });
      } else {
        // Update existing - aggregate trial info
        const existing = assetMap.get(key)!;
        existing.trialCount++;
        if (!existing.trialIds.includes(trial.nctId)) {
          existing.trialIds.push(trial.nctId);
        }
        // Upgrade confidence if better verification found
        if (confidenceRank(verification.confidence) > confidenceRank(existing.confidence)) {
          existing.confidence = verification.confidence;
          existing.verificationMethod = verification.method;
          existing.verificationDetails = verification.details;
        }
        // Keep most advanced phase
        existing.phase = getMostAdvancedPhase([existing.phase, trial.phase || 'Unknown']);
      }
    }
  }

  return {
    discovered: Array.from(assetMap.values()),
    excluded: excludedCount,
  };
}

/**
 * Multi-layer verification of an intervention
 */
interface VerificationResult {
  confidence: ConfidenceLevel;
  method: 'name_match' | 'mechanism_match' | 'trial_association';
  details: string;
}

function verifyIntervention(
  name: string,
  description: string,
  target: string,
  targetInfo: TargetInfo
): VerificationResult {
  // LAYER 4: Check exclusion list first
  if (isCommonNonTargetDrug(name)) {
    // Only exclude if name doesn't explicitly match target
    if (!interventionNameMatchesTarget(name, targetInfo)) {
      return {
        confidence: 'EXCLUDE',
        method: 'trial_association',
        details: `Common non-target drug: ${name}`,
      };
    }
  }

  // LAYER 2: Name-based filtering (strongest signal)
  const nameMatches = interventionNameMatchesTarget(name, targetInfo);

  // LAYER 3: Mechanism verification
  const mechanismMatches = mechanismContainsTarget(description, targetInfo);

  // LAYER 5: Confidence scoring
  if (nameMatches && mechanismMatches) {
    return {
      confidence: 'HIGH',
      method: 'name_match',
      details: `Drug name AND mechanism mention ${target}`,
    };
  }

  if (nameMatches) {
    return {
      confidence: 'MEDIUM',
      method: 'name_match',
      details: `Drug name contains ${target} variant`,
    };
  }

  if (mechanismMatches) {
    return {
      confidence: 'LOW',
      method: 'mechanism_match',
      details: `Mechanism mentions ${target} but name does not`,
    };
  }

  // No verification possible - exclude
  return {
    confidence: 'EXCLUDE',
    method: 'trial_association',
    details: `No evidence drug targets ${target}`,
  };
}

/**
 * LAYER 2: Check if intervention name contains target
 */
function interventionNameMatchesTarget(name: string, targetInfo: TargetInfo): boolean {
  const nameLower = name.toLowerCase().replace(/[-\s]/g, '');

  // Check all aliases
  for (const alias of targetInfo.aliases) {
    const aliasLower = alias.toLowerCase().replace(/[-\s]/g, '');
    if (nameLower.includes(aliasLower)) {
      return true;
    }
  }

  // Check common mechanisms (e.g., "anti-TL1A")
  for (const mechanism of targetInfo.commonMechanisms) {
    const mechLower = mechanism.toLowerCase().replace(/[-\s]/g, '');
    if (nameLower.includes(mechLower)) {
      return true;
    }
  }

  return false;
}

/**
 * LAYER 3: Check if mechanism/description mentions target
 */
function mechanismContainsTarget(description: string, targetInfo: TargetInfo): boolean {
  if (!description) return false;

  const descLower = description.toLowerCase();

  // Check aliases
  for (const alias of targetInfo.aliases) {
    if (descLower.includes(alias.toLowerCase())) {
      return true;
    }
  }

  // Check mechanisms
  for (const mechanism of targetInfo.commonMechanisms) {
    if (descLower.includes(mechanism.toLowerCase())) {
      return true;
    }
  }

  // Check gene symbol
  if (targetInfo.geneSymbol && descLower.includes(targetInfo.geneSymbol.toLowerCase())) {
    return true;
  }

  return false;
}

// ============================================
// Merging & Deduplication
// ============================================

function mergeAndDeduplicate(
  curated: VerifiedAsset[],
  discovered: VerifiedAsset[]
): VerifiedAsset[] {
  const result: VerifiedAsset[] = [...curated];
  const addedNames = new Set<string>();

  // Track curated names
  for (const asset of curated) {
    addedNames.add(normalizeDrugName(asset.drugName));
    if (asset.codeName) addedNames.add(normalizeDrugName(asset.codeName));
    if (asset.genericName) addedNames.add(normalizeDrugName(asset.genericName));
    for (const alias of asset.aliases) {
      addedNames.add(normalizeDrugName(alias));
    }
  }

  // Add discovered that aren't duplicates
  for (const asset of discovered) {
    const normalized = normalizeDrugName(asset.drugName);
    if (!addedNames.has(normalized)) {
      result.push(asset);
      addedNames.add(normalized);
    }
  }

  // Sort by phase (most advanced first), then by confidence
  return result.sort((a, b) => {
    // First by confidence
    const confDiff = confidenceRank(b.confidence) - confidenceRank(a.confidence);
    if (confDiff !== 0) return confDiff;

    // Then by phase
    const phaseOrder = ['Approved', 'Filed', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Preclinical'];
    const aIdx = phaseOrder.indexOf(a.phase);
    const bIdx = phaseOrder.indexOf(b.phase);
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
  });
}

// ============================================
// Classification Helpers
// ============================================

function classifyModality(name: string, type: string, description?: string): string {
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

function classifyOwnerType(sponsor: string): VerifiedAsset['ownerType'] {
  const lower = sponsor.toLowerCase();

  const bigPharma = [
    'merck', 'pfizer', 'novartis', 'roche', 'johnson', 'abbvie', 'bms',
    'bristol-myers', 'astrazeneca', 'sanofi', 'gsk', 'glaxo', 'lilly',
    'amgen', 'gilead', 'takeda', 'daiichi', 'boehringer', 'teva'
  ];
  if (bigPharma.some(p => lower.includes(p))) return 'Big Pharma';

  const chineseBiotech = [
    'hansoh', 'hengrui', 'beigene', 'innovent', 'junshi', 'zai lab',
    'simcere', 'kelun', 'luye', 'alphamab', 'chia tai', 'shanghai',
    'beijing', 'china', 'chinese', 'sichuan', 'jiangsu'
  ];
  if (chineseBiotech.some(p => lower.includes(p))) return 'Chinese Biotech';

  const academic = [
    'university', 'college', 'institute', 'hospital', 'medical center',
    'cancer center', 'memorial sloan', 'md anderson', 'dana-farber',
    'mayo clinic', 'nih', 'national cancer'
  ];
  if (academic.some(p => lower.includes(p))) return 'Academic';

  return 'Biotech';
}

// ============================================
// Utility Functions
// ============================================

function normalizeDrugName(name: string): string {
  return name
    .toLowerCase()
    .replace(/\([^)]*\)/g, '')  // Remove parenthetical content
    .replace(/[-\s]+/g, '')
    .replace(/\d+\s*(mg|mcg|ml|iu)/gi, '')
    .trim();
}

function normalizeStatus(status: string): VerifiedAsset['status'] {
  if (['Recruiting', 'Active, not recruiting', 'Enrolling by invitation', 'Not yet recruiting'].includes(status)) {
    return 'Active';
  }
  if (status === 'Completed') return 'Completed';
  if (['Terminated', 'Withdrawn'].includes(status)) return 'Terminated';
  if (status === 'Suspended') return 'On Hold';
  return 'Unknown';
}

function getMostAdvancedPhase(phases: string[]): string {
  const phaseOrder = ['Approved', 'Filed', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Early Phase 1', 'Preclinical'];

  for (const phase of phaseOrder) {
    for (const p of phases) {
      if (p && p.toLowerCase().replace(/\s/g, '').includes(phase.toLowerCase().replace(/\s/g, ''))) {
        return phase;
      }
    }
  }

  return phases.find(p => p && p !== 'Unknown') || 'Unknown';
}

function confidenceRank(confidence: ConfidenceLevel): number {
  switch (confidence) {
    case 'HIGH': return 3;
    case 'MEDIUM': return 2;
    case 'LOW': return 1;
    case 'EXCLUDE': return 0;
  }
}

// ============================================
// Summary Statistics
// ============================================

function calculateSummary(
  assets: VerifiedAsset[],
  excludedCount: number
) {
  const byModality: Record<string, number> = {};
  const byPhase: Record<string, number> = {};

  for (const asset of assets) {
    byModality[asset.modality] = (byModality[asset.modality] || 0) + 1;
    byPhase[asset.phase] = (byPhase[asset.phase] || 0) + 1;
  }

  return {
    totalVerified: assets.filter(a => a.confidence === 'HIGH').length,
    totalProbable: assets.filter(a => a.confidence === 'MEDIUM').length,
    totalUnverified: assets.filter(a => a.confidence === 'LOW').length,
    totalExcluded: excludedCount,
    byModality,
    byPhase,
  };
}

// ============================================
// Legacy Export (backwards compatibility)
// ============================================

export interface ResearchedAsset extends VerifiedAsset {}

export interface AssetResearchReport {
  target: string;
  generatedAt: string;
  assets: ResearchedAsset[];
  summary: {
    totalAssets: number;
    byModality: Record<string, number>;
    byPhase: Record<string, number>;
    byOwnerType: Record<string, number>;
    byGeography: Record<string, number>;
  };
  knownAssetsFound: number;
  newAssetsDiscovered: number;
  excludedDrugs: number;
}

/**
 * Legacy function for backwards compatibility
 */
export async function researchTargetAssets(target: string): Promise<AssetResearchReport> {
  const result = await discoverAssets(target);

  // Combine verified + probable for legacy format
  const allAssets = [...result.verified, ...result.probable];

  const byOwnerType: Record<string, number> = {};
  const byGeography: Record<string, number> = {};

  for (const asset of allAssets) {
    byOwnerType[asset.ownerType] = (byOwnerType[asset.ownerType] || 0) + 1;

    let geo = 'Other';
    if (asset.ownerType === 'Chinese Biotech') geo = 'China';
    else if (['Big Pharma', 'Biotech'].includes(asset.ownerType)) geo = 'US/EU';
    else if (asset.ownerType === 'Academic') geo = 'Academic';
    byGeography[geo] = (byGeography[geo] || 0) + 1;
  }

  return {
    target,
    generatedAt: result.generatedAt,
    assets: allAssets,
    summary: {
      totalAssets: allAssets.length,
      byModality: result.summary.byModality,
      byPhase: result.summary.byPhase,
      byOwnerType,
      byGeography,
    },
    knownAssetsFound: result.verified.filter(a => a.verificationMethod === 'curated_database').length,
    newAssetsDiscovered: result.verified.filter(a => a.verificationMethod !== 'curated_database').length + result.probable.length,
    excludedDrugs: result.summary.totalExcluded,
  };
}

/**
 * Format asset for display (legacy)
 */
export function formatAssetForDisplay(asset: VerifiedAsset): {
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
