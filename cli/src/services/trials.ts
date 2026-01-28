/**
 * Clinical Trials Service
 *
 * Fetches and processes clinical trial data from ClinicalTrials.gov API v2.
 * Handles pagination, field mapping, and aggregation.
 */

import { Trial, TrialPhase, TrialStatus, Intervention, Outcome } from '../types/schema';

const CLINICALTRIALS_API = 'https://clinicaltrials.gov/api/v2/studies';
const DEFAULT_PAGE_SIZE = 100;
const MAX_PAGES = 20; // Up to 2000 trials
const REQUEST_DELAY_MS = 300; // Be nice to the API

// Fields to request from API
const STUDY_FIELDS = [
  'NCTId',
  'BriefTitle',
  'OfficialTitle',
  'Acronym',
  'OverallStatus',
  'Phase',
  'StudyType',
  'LeadSponsorName',
  'LeadSponsorClass',
  'CollaboratorName',
  'EnrollmentCount',
  'EnrollmentType',
  'StartDate',
  'StartDateType',
  'PrimaryCompletionDate',
  'PrimaryCompletionDateType',
  'CompletionDate',
  'CompletionDateType',
  'StudyFirstPostDate',
  'LastUpdatePostDate',
  'ResultsFirstPostDate',
  'Condition',
  'ConditionMeshTerm',
  'InterventionName',
  'InterventionType',
  'InterventionDescription',
  'InterventionOtherName',
  'PrimaryOutcomeMeasure',
  'PrimaryOutcomeDescription',
  'PrimaryOutcomeTimeFrame',
  'SecondaryOutcomeMeasure',
  'SecondaryOutcomeDescription',
  'SecondaryOutcomeTimeFrame',
  'DesignAllocation',
  'DesignInterventionModel',
  'DesignPrimaryPurpose',
  'DesignMasking',
  'LocationCountry',
  'LocationFacility',
  'LocationCity',
  'LocationState',
  'ReferencePMID',
].join(',');

// ============================================
// Main Functions
// ============================================

/**
 * Search trials by condition with full pagination
 */
export async function searchTrialsByCondition(
  condition: string,
  options?: {
    maxResults?: number;
    phases?: TrialPhase[];
    statuses?: TrialStatus[];
    sponsorType?: 'Industry' | 'Academic' | 'Government';
    fromDate?: string;
    toDate?: string;
    includeResults?: boolean;
  }
): Promise<Trial[]> {
  const maxResults = options?.maxResults || 1000;
  const maxPages = Math.ceil(maxResults / DEFAULT_PAGE_SIZE);

  console.log(`[Trials] Searching for "${condition}" (max ${maxResults} results)...`);

  const allTrials: Trial[] = [];
  let nextPageToken: string | null = null;
  let pageCount = 0;

  try {
    do {
      // Build query URL
      let url = `${CLINICALTRIALS_API}?query.cond=${encodeURIComponent(condition)}`;
      url += `&pageSize=${DEFAULT_PAGE_SIZE}`;
      url += `&fields=${STUDY_FIELDS}`;
      url += '&format=json';

      // Add filters
      if (options?.phases && options.phases.length > 0) {
        const phaseQuery = options.phases.map(p => phaseToApiValue(p)).join(',');
        url += `&filter.advanced=AREA[Phase](${phaseQuery})`;
      }

      if (options?.statuses && options.statuses.length > 0) {
        const statusQuery = options.statuses.map(s => statusToApiValue(s)).join(',');
        url += `&filter.overallStatus=${statusQuery}`;
      }

      if (nextPageToken) {
        url += `&pageToken=${nextPageToken}`;
      }

      const response = await fetch(url, {
        headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
      });

      if (!response.ok) {
        console.log(`[Trials] API returned ${response.status}`);
        break;
      }

      const data = await response.json() as {
        studies?: any[];
        nextPageToken?: string;
        totalCount?: number;
      };

      const studies = data.studies || [];
      pageCount++;

      console.log(`[Trials] Page ${pageCount}: ${studies.length} trials (total: ${allTrials.length + studies.length})`);

      // Parse studies into Trial objects
      for (const study of studies) {
        try {
          const trial = parseStudyToTrial(study);
          allTrials.push(trial);
        } catch (err) {
          console.log(`[Trials] Error parsing study: ${err}`);
        }
      }

      nextPageToken = data.nextPageToken || null;

      // Rate limiting
      if (nextPageToken && pageCount < maxPages) {
        await sleep(REQUEST_DELAY_MS);
      }

    } while (nextPageToken && pageCount < maxPages && allTrials.length < maxResults);

    console.log(`[Trials] Found ${allTrials.length} total trials for "${condition}"`);
    return allTrials;

  } catch (error) {
    console.log(`[Trials] Error searching trials: ${error}`);
    return allTrials;
  }
}

/**
 * Get a single trial by NCT ID
 */
export async function getTrialByNctId(nctId: string): Promise<Trial | null> {
  try {
    const url = `${CLINICALTRIALS_API}/${nctId}?fields=${STUDY_FIELDS}&format=json`;

    const response = await fetch(url, {
      headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
    });

    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    return parseStudyToTrial(data);

  } catch (error) {
    console.log(`[Trials] Error fetching ${nctId}: ${error}`);
    return null;
  }
}

/**
 * Get multiple trials by NCT IDs (batch)
 */
export async function getTrialsByNctIds(nctIds: string[]): Promise<Map<string, Trial>> {
  const results = new Map<string, Trial>();

  // Batch in groups of 20 to avoid URL length limits
  for (let i = 0; i < nctIds.length; i += 20) {
    const batch = nctIds.slice(i, i + 20);
    const query = batch.join(' OR ');

    try {
      const url = `${CLINICALTRIALS_API}?query.id=${encodeURIComponent(query)}&pageSize=100&fields=${STUDY_FIELDS}&format=json`;

      const response = await fetch(url, {
        headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
      });

      if (response.ok) {
        const data = await response.json() as { studies?: any[] };
        for (const study of data.studies || []) {
          const trial = parseStudyToTrial(study);
          results.set(trial.nctId, trial);
        }
      }

      await sleep(REQUEST_DELAY_MS);
    } catch (error) {
      console.log(`[Trials] Error fetching batch: ${error}`);
    }
  }

  return results;
}

/**
 * Search trials by intervention/drug name
 */
export async function searchTrialsByIntervention(
  drugName: string,
  options?: {
    maxResults?: number;
    phases?: TrialPhase[];
  }
): Promise<Trial[]> {
  const maxResults = options?.maxResults || 500;

  console.log(`[Trials] Searching for drug "${drugName}"...`);

  try {
    let url = `${CLINICALTRIALS_API}?query.intr=${encodeURIComponent(drugName)}`;
    url += `&pageSize=${Math.min(maxResults, DEFAULT_PAGE_SIZE)}`;
    url += `&fields=${STUDY_FIELDS}`;
    url += '&format=json';

    const allTrials: Trial[] = [];
    let nextPageToken: string | null = null;
    let pageCount = 0;
    const maxPages = Math.ceil(maxResults / DEFAULT_PAGE_SIZE);

    do {
      let fetchUrl = url;
      if (nextPageToken) {
        fetchUrl += `&pageToken=${nextPageToken}`;
      }

      const response = await fetch(fetchUrl, {
        headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
      });

      if (!response.ok) break;

      const data = await response.json() as { studies?: any[]; nextPageToken?: string };
      pageCount++;

      for (const study of data.studies || []) {
        allTrials.push(parseStudyToTrial(study));
      }

      nextPageToken = data.nextPageToken || null;

      if (nextPageToken && pageCount < maxPages) {
        await sleep(REQUEST_DELAY_MS);
      }
    } while (nextPageToken && pageCount < maxPages);

    return allTrials;

  } catch (error) {
    console.log(`[Trials] Error searching by intervention: ${error}`);
    return [];
  }
}

/**
 * Search trials by sponsor
 */
export async function searchTrialsBySponsor(
  sponsorName: string,
  options?: {
    maxResults?: number;
    includeCollaborators?: boolean;
  }
): Promise<Trial[]> {
  const query = options?.includeCollaborators
    ? `AREA[LeadSponsorName]${sponsorName} OR AREA[CollaboratorName]${sponsorName}`
    : `AREA[LeadSponsorName]${sponsorName}`;

  try {
    const url = `${CLINICALTRIALS_API}?query.spons=${encodeURIComponent(sponsorName)}&pageSize=${options?.maxResults || 100}&fields=${STUDY_FIELDS}&format=json`;

    const response = await fetch(url, {
      headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
    });

    if (!response.ok) return [];

    const data = await response.json() as { studies?: any[] };
    return (data.studies || []).map(parseStudyToTrial);

  } catch (error) {
    console.log(`[Trials] Error searching by sponsor: ${error}`);
    return [];
  }
}

/**
 * Get trials with results available
 */
export async function getTrialsWithResults(
  condition: string,
  options?: {
    maxResults?: number;
    phases?: TrialPhase[];
  }
): Promise<Trial[]> {
  console.log(`[Trials] Searching for trials with results for "${condition}"...`);

  try {
    // Use advanced filter to get only trials with results
    let url = `${CLINICALTRIALS_API}?query.cond=${encodeURIComponent(condition)}`;
    url += `&filter.advanced=AREA[ResultsFirstPostDate]RANGE[MIN,MAX]`; // Has results
    url += `&pageSize=${options?.maxResults || 100}`;
    url += `&fields=${STUDY_FIELDS}`;
    url += '&format=json';

    const response = await fetch(url, {
      headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
    });

    if (!response.ok) return [];

    const data = await response.json() as { studies?: any[] };
    const trials = (data.studies || []).map(parseStudyToTrial);

    console.log(`[Trials] Found ${trials.length} trials with results`);
    return trials;

  } catch (error) {
    console.log(`[Trials] Error fetching trials with results: ${error}`);
    return [];
  }
}

/**
 * Get recently updated trials
 */
export async function getRecentlyUpdatedTrials(
  daysBack: number,
  options?: {
    conditions?: string[];
    maxResults?: number;
  }
): Promise<Trial[]> {
  const fromDate = new Date();
  fromDate.setDate(fromDate.getDate() - daysBack);
  const fromDateStr = fromDate.toISOString().split('T')[0];

  try {
    let url = `${CLINICALTRIALS_API}?filter.advanced=AREA[LastUpdatePostDate]RANGE[${fromDateStr},MAX]`;

    if (options?.conditions && options.conditions.length > 0) {
      const condQuery = options.conditions.map(c => encodeURIComponent(c)).join(' OR ');
      url += `&query.cond=${condQuery}`;
    }

    url += `&pageSize=${options?.maxResults || 100}`;
    url += `&fields=${STUDY_FIELDS}`;
    url += '&format=json';
    url += '&sort=LastUpdatePostDate:desc';

    const response = await fetch(url, {
      headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
    });

    if (!response.ok) return [];

    const data = await response.json() as { studies?: any[] };
    return (data.studies || []).map(parseStudyToTrial);

  } catch (error) {
    console.log(`[Trials] Error fetching recent trials: ${error}`);
    return [];
  }
}

// ============================================
// Aggregation Functions
// ============================================

/**
 * Get trial counts by phase for a condition
 */
export function getPhaseBreakdown(trials: Trial[]): Record<TrialPhase, number> {
  const breakdown: Record<string, number> = {};

  for (const trial of trials) {
    const phase = trial.phase;
    breakdown[phase] = (breakdown[phase] || 0) + 1;
  }

  return breakdown as Record<TrialPhase, number>;
}

/**
 * Get top sponsors for a set of trials
 */
export function getTopSponsors(trials: Trial[], limit: number = 10): { sponsor: string; count: number; type: string }[] {
  const sponsorCounts: Record<string, { count: number; type: string }> = {};

  for (const trial of trials) {
    const sponsor = trial.leadSponsor.name;
    if (!sponsorCounts[sponsor]) {
      sponsorCounts[sponsor] = { count: 0, type: trial.leadSponsor.type };
    }
    sponsorCounts[sponsor].count++;
  }

  return Object.entries(sponsorCounts)
    .map(([sponsor, data]) => ({ sponsor, count: data.count, type: data.type }))
    .sort((a, b) => b.count - a.count)
    .slice(0, limit);
}

/**
 * Get status breakdown
 */
export function getStatusBreakdown(trials: Trial[]): Record<TrialStatus, number> {
  const breakdown: Record<string, number> = {};

  for (const trial of trials) {
    const status = trial.status;
    breakdown[status] = (breakdown[status] || 0) + 1;
  }

  return breakdown as Record<TrialStatus, number>;
}

/**
 * Get trial timeline (start dates by year)
 */
export function getTrialTimeline(
  trials: Trial[],
  groupBy: 'month' | 'year' = 'year'
): { period: string; count: number }[] {
  const counts: Record<string, number> = {};

  for (const trial of trials) {
    if (!trial.startDate) continue;

    const date = new Date(trial.startDate);
    const period = groupBy === 'year'
      ? date.getFullYear().toString()
      : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

    counts[period] = (counts[period] || 0) + 1;
  }

  return Object.entries(counts)
    .map(([period, count]) => ({ period, count }))
    .sort((a, b) => a.period.localeCompare(b.period));
}

/**
 * Get unique conditions across trials
 */
export function getUniqueConditions(trials: Trial[]): { condition: string; count: number }[] {
  const conditionCounts: Record<string, number> = {};

  for (const trial of trials) {
    for (const condition of trial.conditions) {
      conditionCounts[condition] = (conditionCounts[condition] || 0) + 1;
    }
  }

  return Object.entries(conditionCounts)
    .map(([condition, count]) => ({ condition, count }))
    .sort((a, b) => b.count - a.count);
}

/**
 * Get unique interventions across trials
 */
export function getUniqueInterventions(trials: Trial[]): { name: string; type: string; count: number }[] {
  const interventionCounts: Record<string, { type: string; count: number }> = {};

  for (const trial of trials) {
    for (const intervention of trial.interventions) {
      const key = intervention.name.toLowerCase();
      if (!interventionCounts[key]) {
        interventionCounts[key] = { type: intervention.type, count: 0 };
      }
      interventionCounts[key].count++;
    }
  }

  return Object.entries(interventionCounts)
    .map(([name, data]) => ({ name, type: data.type, count: data.count }))
    .sort((a, b) => b.count - a.count);
}

// ============================================
// Parsing Functions
// ============================================

/**
 * Parse ClinicalTrials.gov API response into Trial object
 */
function parseStudyToTrial(study: any): Trial {
  const protocol = study.protocolSection || {};
  const hasResults = study.hasResults || false;
  const resultsSection = study.resultsSection;

  // Identification
  const idModule = protocol.identificationModule || {};
  const nctId = idModule.nctId || '';
  const briefTitle = idModule.briefTitle || '';
  const officialTitle = idModule.officialTitle;
  const acronym = idModule.acronym;

  // Status
  const statusModule = protocol.statusModule || {};
  const overallStatus = statusModule.overallStatus || 'Unknown';
  const startDateStruct = statusModule.startDateStruct || {};
  const primaryCompletionDateStruct = statusModule.primaryCompletionDateStruct || {};
  const completionDateStruct = statusModule.completionDateStruct || {};
  const studyFirstPostDateStruct = statusModule.studyFirstPostDateStruct || {};
  const lastUpdatePostDateStruct = statusModule.lastUpdatePostDateStruct || {};
  const resultsFirstPostDateStruct = statusModule.resultsFirstPostDateStruct || {};

  // Design
  const designModule = protocol.designModule || {};
  const phases = designModule.phases || [];
  const studyType = designModule.studyType || 'Interventional';
  const designInfo = designModule.designInfo || {};

  // Sponsor
  const sponsorModule = protocol.sponsorCollaboratorsModule || {};
  const leadSponsor = sponsorModule.leadSponsor || {};
  const collaborators = sponsorModule.collaborators || [];

  // Enrollment
  const enrollmentInfo = designModule.enrollmentInfo || {};

  // Conditions
  const conditionsModule = protocol.conditionsModule || {};
  const conditions = conditionsModule.conditions || [];
  const meshTerms = conditionsModule.conditionMeshTerms || [];

  // Interventions
  const armsModule = protocol.armsInterventionsModule || {};
  const interventionsList = armsModule.interventions || [];

  // Outcomes
  const outcomesModule = protocol.outcomesModule || {};
  const primaryOutcomes = outcomesModule.primaryOutcomes || [];
  const secondaryOutcomes = outcomesModule.secondaryOutcomes || [];

  // Locations
  const contactsModule = protocol.contactsLocationsModule || {};
  const locationsList = contactsModule.locations || [];

  // References
  const referencesModule = protocol.referencesModule || {};
  const references = referencesModule.references || [];

  // Build Trial object
  const trial: Trial = {
    nctId,
    briefTitle,
    officialTitle,
    acronym,
    phase: normalizePhase(phases.join('/')),
    status: normalizeStatus(overallStatus),
    studyType: studyType as Trial['studyType'],
    leadSponsor: {
      name: leadSponsor.name || 'Unknown',
      type: normalizeSponsorType(leadSponsor.class),
    },
    collaborators: collaborators.map((c: any) => c.name).filter(Boolean),
    conditions,
    conditionMeshTerms: meshTerms.map((m: any) => m.term || m),
    interventions: interventionsList.map((i: any) => ({
      type: normalizeInterventionType(i.type),
      name: i.name || '',
      description: i.description,
      armGroupLabels: i.armGroupLabels,
      otherNames: i.otherNames,
    })),
    design: {
      allocation: designInfo.allocation as any,
      interventionModel: designInfo.interventionModel as any,
      primaryPurpose: designInfo.primaryPurpose as any,
      masking: designInfo.maskingInfo?.masking as any,
    },
    enrollment: enrollmentInfo.count ? {
      count: enrollmentInfo.count,
      type: enrollmentInfo.type as 'Actual' | 'Anticipated',
    } : undefined,
    startDate: startDateStruct.date || null,
    primaryCompletionDate: primaryCompletionDateStruct.date || null,
    completionDate: completionDateStruct.date || null,
    firstPostedDate: studyFirstPostDateStruct.date,
    lastUpdateDate: lastUpdatePostDateStruct.date,
    primaryOutcomes: primaryOutcomes.map((o: any) => ({
      measure: o.measure || '',
      description: o.description,
      timeFrame: o.timeFrame,
    })),
    secondaryOutcomes: secondaryOutcomes.map((o: any) => ({
      measure: o.measure || '',
      description: o.description,
      timeFrame: o.timeFrame,
    })),
    resultsAvailable: hasResults,
    resultsFirstPosted: resultsFirstPostDateStruct.date,
    locations: locationsList.slice(0, 10).map((loc: any) => ({
      facility: loc.facility,
      city: loc.city,
      state: loc.state,
      country: loc.country || 'Unknown',
      status: loc.status,
    })),
    countries: [...new Set(locationsList.map((loc: any) => loc.country).filter(Boolean))] as string[],
    publications: references
      .filter((r: any) => r.pmid)
      .map((r: any) => r.pmid),
    fetchedAt: new Date().toISOString(),
    source: 'ClinicalTrials.gov',
  };

  return trial;
}

// ============================================
// Helper Functions
// ============================================

/**
 * Normalize phase string to enum
 */
export function normalizePhase(phase: string): TrialPhase {
  if (!phase) return 'Not Applicable';

  const p = phase.toLowerCase();
  if (p.includes('4') || p.includes('phase4')) return 'Phase 4';
  if ((p.includes('2') && p.includes('3')) || p.includes('phase2/phase3')) return 'Phase 2/3';
  if (p.includes('3') || p.includes('phase3')) return 'Phase 3';
  if ((p.includes('1') && p.includes('2')) || p.includes('phase1/phase2')) return 'Phase 1/2';
  if (p.includes('2') || p.includes('phase2')) return 'Phase 2';
  if (p.includes('1') || p.includes('phase1') || p.includes('early')) return 'Phase 1';
  if (p.includes('preclinical') || p.includes('pre-clinical')) return 'Preclinical';
  if (p === 'n/a' || p === 'na' || p === 'not applicable') return 'Not Applicable';

  return 'Not Applicable';
}

/**
 * Normalize status string to enum
 */
export function normalizeStatus(status: string): TrialStatus {
  if (!status) return 'Unknown';

  const s = status.toLowerCase().replace(/_/g, ' ');
  if (s.includes('not yet') || s === 'not_yet_recruiting') return 'Not yet recruiting';
  if (s === 'recruiting' || s.includes('recruiting')) return 'Recruiting';
  if (s.includes('enrolling by invitation')) return 'Enrolling by invitation';
  if (s.includes('active') && s.includes('not recruiting')) return 'Active, not recruiting';
  if (s === 'completed') return 'Completed';
  if (s === 'suspended') return 'Suspended';
  if (s === 'terminated') return 'Terminated';
  if (s === 'withdrawn') return 'Withdrawn';

  return 'Unknown';
}

/**
 * Normalize sponsor type
 */
function normalizeSponsorType(sponsorClass: string): Trial['leadSponsor']['type'] {
  if (!sponsorClass) return 'Other';

  const s = sponsorClass.toLowerCase();
  if (s.includes('industry') || s === 'industry') return 'Industry';
  if (s.includes('nih') || s.includes('fed') || s.includes('gov')) return 'Government';
  if (s.includes('network') || s.includes('academic') || s.includes('other')) return 'Academic';

  return 'Other';
}

/**
 * Normalize intervention type
 */
function normalizeInterventionType(type: string): Intervention['type'] {
  if (!type) return 'Other';

  const t = type.toLowerCase();
  if (t === 'drug') return 'Drug';
  if (t === 'biological') return 'Biological';
  if (t === 'device') return 'Device';
  if (t === 'procedure') return 'Procedure';
  if (t === 'radiation') return 'Radiation';
  if (t === 'behavioral') return 'Behavioral';
  if (t === 'dietary supplement' || t === 'dietary') return 'Dietary';

  return 'Other';
}

/**
 * Convert TrialPhase to API filter value
 */
function phaseToApiValue(phase: TrialPhase): string {
  const mapping: Record<TrialPhase, string> = {
    'Preclinical': 'EARLY_PHASE1',
    'Phase 1': 'PHASE1',
    'Phase 1/2': 'PHASE1/PHASE2',
    'Phase 2': 'PHASE2',
    'Phase 2/3': 'PHASE2/PHASE3',
    'Phase 3': 'PHASE3',
    'Phase 4': 'PHASE4',
    'Not Applicable': 'NA',
  };
  return mapping[phase] || phase;
}

/**
 * Convert TrialStatus to API filter value
 */
function statusToApiValue(status: TrialStatus): string {
  const mapping: Record<TrialStatus, string> = {
    'Not yet recruiting': 'NOT_YET_RECRUITING',
    'Recruiting': 'RECRUITING',
    'Enrolling by invitation': 'ENROLLING_BY_INVITATION',
    'Active, not recruiting': 'ACTIVE_NOT_RECRUITING',
    'Completed': 'COMPLETED',
    'Suspended': 'SUSPENDED',
    'Terminated': 'TERMINATED',
    'Withdrawn': 'WITHDRAWN',
    'Unknown': 'UNKNOWN',
  };
  return mapping[status] || status;
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================
// Exports for external use
// ============================================

export {
  parseStudyToTrial,
  phaseToApiValue,
  statusToApiValue,
};
