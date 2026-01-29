/**
 * Assets Service
 *
 * Extracts and deduplicates drug/asset information from clinical trial data.
 * Identifies company sponsors, modalities, and development phases.
 */

import { Trial } from '../types/schema';

// ============================================
// Types
// ============================================

export interface Asset {
  name: string;
  genericName?: string;
  company: string;
  companyType: 'Industry' | 'Academic' | 'Government' | 'Other';
  modality: string;
  phase: string;
  indications: string[];
  trialCount: number;
  trialIds: string[];
  status: 'Active' | 'Completed' | 'Terminated' | 'Mixed';
  partners: string[];
  firstTrialDate?: string;
  latestTrialDate?: string;
}

// ============================================
// Main Functions
// ============================================

/**
 * Extract assets from clinical trials
 */
export function extractAssetsFromTrials(trials: Trial[]): Asset[] {
  const assetMap = new Map<string, {
    name: string;
    genericName?: string;
    companies: Map<string, { type: string; count: number }>;
    modalities: Map<string, number>;
    phases: Set<string>;
    indications: Set<string>;
    trialIds: string[];
    statuses: Map<string, number>;
    collaborators: Set<string>;
    dates: string[];
  }>();

  for (const trial of trials) {
    for (const intervention of trial.interventions || []) {
      if (!intervention.name) continue;

      // Skip generic/control interventions
      if (isControlIntervention(intervention.name)) continue;

      const assetName = normalizeAssetName(intervention.name);
      const genericName = extractGenericName(intervention);

      if (!assetMap.has(assetName)) {
        assetMap.set(assetName, {
          name: assetName,
          genericName,
          companies: new Map(),
          modalities: new Map(),
          phases: new Set(),
          indications: new Set(),
          trialIds: [],
          statuses: new Map(),
          collaborators: new Set(),
          dates: [],
        });
      }

      const entry = assetMap.get(assetName)!;

      // Track company
      const sponsor = trial.leadSponsor;
      if (sponsor?.name) {
        const companyKey = normalizeCompanyName(sponsor.name);
        if (!entry.companies.has(companyKey)) {
          entry.companies.set(companyKey, { type: sponsor.type || 'Other', count: 0 });
        }
        entry.companies.get(companyKey)!.count++;
      }

      // Track modality
      const modality = classifyModality(intervention);
      entry.modalities.set(modality, (entry.modalities.get(modality) || 0) + 1);

      // Track phase
      if (trial.phase) {
        entry.phases.add(normalizePhase(trial.phase));
      }

      // Track indications
      for (const condition of trial.conditions || []) {
        entry.indications.add(condition);
      }

      // Track trial
      if (trial.nctId && !entry.trialIds.includes(trial.nctId)) {
        entry.trialIds.push(trial.nctId);
      }

      // Track status
      if (trial.status) {
        entry.statuses.set(trial.status, (entry.statuses.get(trial.status) || 0) + 1);
      }

      // Track collaborators
      for (const collab of trial.collaborators || []) {
        if (collab !== sponsor?.name) {
          entry.collaborators.add(collab);
        }
      }

      // Track dates
      if (trial.startDate) {
        entry.dates.push(trial.startDate);
      }

      // Update generic name if found
      if (genericName && !entry.genericName) {
        entry.genericName = genericName;
      }
    }
  }

  // Convert to Asset array
  const assets: Asset[] = [];

  for (const entry of assetMap.values()) {
    // Get primary company (most trials)
    let primaryCompany = 'Unknown';
    let primaryCompanyType: Asset['companyType'] = 'Other';
    let maxTrials = 0;

    for (const [company, data] of entry.companies) {
      if (data.count > maxTrials) {
        maxTrials = data.count;
        primaryCompany = company;
        primaryCompanyType = data.type as Asset['companyType'];
      }
    }

    // Get primary modality
    let primaryModality = 'Other';
    let maxModalityCount = 0;
    for (const [modality, count] of entry.modalities) {
      if (count > maxModalityCount) {
        maxModalityCount = count;
        primaryModality = modality;
      }
    }

    // Get most advanced phase
    const mostAdvancedPhase = getMostAdvancedPhase(Array.from(entry.phases));

    // Determine overall status
    const status = determineOverallStatus(entry.statuses);

    // Get partners (excluding primary company)
    const partners = Array.from(entry.collaborators)
      .filter(c => normalizeCompanyName(c) !== primaryCompany)
      .slice(0, 5);

    // Sort dates
    const sortedDates = entry.dates.sort();

    assets.push({
      name: entry.name,
      genericName: entry.genericName,
      company: primaryCompany,
      companyType: primaryCompanyType,
      modality: primaryModality,
      phase: mostAdvancedPhase,
      indications: Array.from(entry.indications).slice(0, 10),
      trialCount: entry.trialIds.length,
      trialIds: entry.trialIds,
      status,
      partners,
      firstTrialDate: sortedDates[0],
      latestTrialDate: sortedDates[sortedDates.length - 1],
    });
  }

  // Sort by trial count descending
  return assets.sort((a, b) => b.trialCount - a.trialCount);
}

/**
 * Filter assets by modality
 */
export function filterAssetsByModality(assets: Asset[], modality: string): Asset[] {
  return assets.filter(a => a.modality.toLowerCase() === modality.toLowerCase());
}

/**
 * Filter assets by company type
 */
export function filterAssetsByCompanyType(assets: Asset[], type: Asset['companyType']): Asset[] {
  return assets.filter(a => a.companyType === type);
}

/**
 * Get asset summary statistics
 */
export function getAssetStats(assets: Asset[]): {
  totalAssets: number;
  byModality: Record<string, number>;
  byPhase: Record<string, number>;
  byCompanyType: Record<string, number>;
  topCompanies: { company: string; assetCount: number }[];
} {
  const byModality: Record<string, number> = {};
  const byPhase: Record<string, number> = {};
  const byCompanyType: Record<string, number> = {};
  const companyAssets: Record<string, number> = {};

  for (const asset of assets) {
    byModality[asset.modality] = (byModality[asset.modality] || 0) + 1;
    byPhase[asset.phase] = (byPhase[asset.phase] || 0) + 1;
    byCompanyType[asset.companyType] = (byCompanyType[asset.companyType] || 0) + 1;
    companyAssets[asset.company] = (companyAssets[asset.company] || 0) + 1;
  }

  const topCompanies = Object.entries(companyAssets)
    .map(([company, assetCount]) => ({ company, assetCount }))
    .sort((a, b) => b.assetCount - a.assetCount)
    .slice(0, 10);

  return {
    totalAssets: assets.length,
    byModality,
    byPhase,
    byCompanyType,
    topCompanies,
  };
}

// ============================================
// Helper Functions
// ============================================

/**
 * Check if intervention is a control/standard treatment
 */
function isControlIntervention(name: string): boolean {
  const controlPatterns = [
    /^placebo$/i,
    /^standard\s+(of\s+)?care$/i,
    /^soc$/i,
    /^best\s+supportive\s+care$/i,
    /^bsc$/i,
    /^observation$/i,
    /^no\s+intervention$/i,
    /^active\s+comparator$/i,
    /^control$/i,
    /^saline$/i,
    /^vehicle$/i,
    /^sham$/i,
  ];

  return controlPatterns.some(p => p.test(name.trim()));
}

/**
 * Normalize asset name for deduplication
 */
function normalizeAssetName(name: string): string {
  // Remove dosage info
  let normalized = name.replace(/\d+\s*(mg|mcg|g|ml|iu|units?)\b/gi, '').trim();

  // Remove route of administration
  normalized = normalized.replace(/\b(oral|iv|sc|im|topical|intradermal|intrathecal|subcutaneous|intravenous|intramuscular)\b/gi, '').trim();

  // Remove common suffixes/prefixes
  normalized = normalized.replace(/\s*(injection|solution|tablet|capsule|infusion|formulation|combination)\s*/gi, ' ').trim();

  // Normalize whitespace
  normalized = normalized.replace(/\s+/g, ' ').trim();

  // Title case
  normalized = normalized.split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');

  return normalized;
}

/**
 * Extract generic/code name from intervention
 */
function extractGenericName(intervention: { name: string; otherNames?: string[]; description?: string }): string | undefined {
  // Check other names for code names (e.g., MK-1234)
  const codePattern = /^[A-Z]{2,4}[-\s]?\d{3,6}[A-Z]?$/;

  if (intervention.otherNames) {
    for (const name of intervention.otherNames) {
      if (codePattern.test(name.trim())) {
        return name.trim();
      }
    }
  }

  // Check if main name is a code name
  if (codePattern.test(intervention.name.trim())) {
    return intervention.name.trim();
  }

  return undefined;
}

/**
 * Normalize company name for matching
 */
function normalizeCompanyName(name: string): string {
  return name
    .replace(/\b(Inc\.?|Corp\.?|Ltd\.?|LLC|PLC|SA|AG|GmbH|Co\.?|Company|Pharmaceuticals?|Biopharmaceuticals?|Biotech|Therapeutics?|Sciences?|Oncology|Medicines?)\b/gi, '')
    .replace(/[,.]$/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Classify modality from intervention
 */
function classifyModality(intervention: { type: string; name: string; description?: string }): string {
  const name = intervention.name.toLowerCase();
  const desc = (intervention.description || '').toLowerCase();
  const type = intervention.type.toLowerCase();

  // ADC
  if (name.includes('adc') || name.includes('deruxtecan') || name.includes('vedotin') ||
      name.includes('emtansine') || name.includes('mafodotin') || name.includes('govitecan') ||
      desc.includes('antibody-drug conjugate') || desc.includes('antibody drug conjugate')) {
    return 'ADC';
  }

  // CAR-T
  if (name.includes('car-t') || name.includes('cart') || name.includes('car t') ||
      desc.includes('chimeric antigen receptor') || desc.includes('car-t')) {
    return 'CAR-T';
  }

  // Bispecific
  if (name.includes('bispecific') || desc.includes('bispecific') ||
      name.includes('-amg') || name.includes('bsab')) {
    return 'Bispecific';
  }

  // mRNA
  if (name.includes('mrna') || desc.includes('mrna') || desc.includes('messenger rna')) {
    return 'mRNA';
  }

  // Monoclonal antibody
  if (type === 'biological' || name.endsWith('mab') || name.endsWith('umab') ||
      name.endsWith('zumab') || name.endsWith('ximab') || name.endsWith('tumab') ||
      desc.includes('monoclonal antibody') || desc.includes('mab')) {
    return 'Monoclonal Antibody';
  }

  // Small molecule
  if (type === 'drug' || name.endsWith('ib') || name.endsWith('nib') ||
      name.endsWith('lib') || name.endsWith('tinib')) {
    return 'Small Molecule';
  }

  // Vaccine
  if (name.includes('vaccine') || desc.includes('vaccine') || desc.includes('immunization')) {
    return 'Vaccine';
  }

  // Gene therapy
  if (desc.includes('gene therapy') || desc.includes('aav') || desc.includes('viral vector')) {
    return 'Gene Therapy';
  }

  // Cell therapy (non-CAR-T)
  if (desc.includes('cell therapy') || desc.includes('stem cell')) {
    return 'Cell Therapy';
  }

  // Default based on intervention type
  if (type === 'biological') return 'Biologic';
  if (type === 'drug') return 'Small Molecule';

  return 'Other';
}

/**
 * Normalize phase string
 */
function normalizePhase(phase: string): string {
  const p = phase.toLowerCase();
  if (p.includes('4')) return 'Phase 4';
  if (p.includes('3')) return 'Phase 3';
  if (p.includes('2') && p.includes('3')) return 'Phase 2/3';
  if (p.includes('2')) return 'Phase 2';
  if (p.includes('1') && p.includes('2')) return 'Phase 1/2';
  if (p.includes('1')) return 'Phase 1';
  if (p.includes('early')) return 'Early Phase 1';
  return phase;
}

/**
 * Get most advanced phase from a list
 */
function getMostAdvancedPhase(phases: string[]): string {
  const phaseOrder = ['Phase 4', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Early Phase 1'];

  for (const phase of phaseOrder) {
    if (phases.includes(phase)) return phase;
  }

  return phases[0] || 'Unknown';
}

/**
 * Determine overall status from status counts
 */
function determineOverallStatus(statuses: Map<string, number>): Asset['status'] {
  const activeStatuses = ['Recruiting', 'Active, not recruiting', 'Enrolling by invitation', 'Not yet recruiting'];
  const completedStatuses = ['Completed'];
  const terminatedStatuses = ['Terminated', 'Withdrawn', 'Suspended'];

  let hasActive = false;
  let hasCompleted = false;
  let hasTerminated = false;

  for (const [status] of statuses) {
    if (activeStatuses.includes(status)) hasActive = true;
    if (completedStatuses.includes(status)) hasCompleted = true;
    if (terminatedStatuses.includes(status)) hasTerminated = true;
  }

  if (hasActive) return 'Active';
  if (hasCompleted && !hasTerminated) return 'Completed';
  if (hasTerminated && !hasCompleted) return 'Terminated';
  if (hasCompleted && hasTerminated) return 'Mixed';

  return 'Mixed';
}
