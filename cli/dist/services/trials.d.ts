/**
 * Clinical Trials Service
 *
 * Fetches and processes clinical trial data from ClinicalTrials.gov API v2.
 * Handles pagination, field mapping, and aggregation.
 */
import { Trial, TrialPhase, TrialStatus } from '../types/schema';
/**
 * Search trials by condition with full pagination
 */
export declare function searchTrialsByCondition(condition: string, options?: {
    maxResults?: number;
    phases?: TrialPhase[];
    statuses?: TrialStatus[];
    sponsorType?: 'Industry' | 'Academic' | 'Government';
    fromDate?: string;
    toDate?: string;
    includeResults?: boolean;
}): Promise<Trial[]>;
/**
 * Get a single trial by NCT ID
 */
export declare function getTrialByNctId(nctId: string): Promise<Trial | null>;
/**
 * Get multiple trials by NCT IDs (batch)
 */
export declare function getTrialsByNctIds(nctIds: string[]): Promise<Map<string, Trial>>;
/**
 * Search trials by intervention/drug name
 */
export declare function searchTrialsByIntervention(drugName: string, options?: {
    maxResults?: number;
    phases?: TrialPhase[];
}): Promise<Trial[]>;
/**
 * Search trials by sponsor
 */
export declare function searchTrialsBySponsor(sponsorName: string, options?: {
    maxResults?: number;
    includeCollaborators?: boolean;
}): Promise<Trial[]>;
/**
 * Get trials with results available
 */
export declare function getTrialsWithResults(condition: string, options?: {
    maxResults?: number;
    phases?: TrialPhase[];
}): Promise<Trial[]>;
/**
 * Get recently updated trials
 */
export declare function getRecentlyUpdatedTrials(daysBack: number, options?: {
    conditions?: string[];
    maxResults?: number;
}): Promise<Trial[]>;
/**
 * Get trial counts by phase for a condition
 */
export declare function getPhaseBreakdown(trials: Trial[]): Record<TrialPhase, number>;
/**
 * Get top sponsors for a set of trials
 */
export declare function getTopSponsors(trials: Trial[], limit?: number): {
    sponsor: string;
    count: number;
    type: string;
}[];
/**
 * Get status breakdown
 */
export declare function getStatusBreakdown(trials: Trial[]): Record<TrialStatus, number>;
/**
 * Get trial timeline (start dates by year)
 */
export declare function getTrialTimeline(trials: Trial[], groupBy?: 'month' | 'year'): {
    period: string;
    count: number;
}[];
/**
 * Get unique conditions across trials
 */
export declare function getUniqueConditions(trials: Trial[]): {
    condition: string;
    count: number;
}[];
/**
 * Get unique interventions across trials
 */
export declare function getUniqueInterventions(trials: Trial[]): {
    name: string;
    type: string;
    count: number;
}[];
/**
 * Parse ClinicalTrials.gov API response into Trial object
 */
declare function parseStudyToTrial(study: any): Trial;
/**
 * Normalize phase string to enum
 */
export declare function normalizePhase(phase: string): TrialPhase;
/**
 * Normalize status string to enum
 */
export declare function normalizeStatus(status: string): TrialStatus;
/**
 * Convert TrialPhase to API filter value
 */
declare function phaseToApiValue(phase: TrialPhase): string;
/**
 * Convert TrialStatus to API filter value
 */
declare function statusToApiValue(status: TrialStatus): string;
export { parseStudyToTrial, phaseToApiValue, statusToApiValue, };
//# sourceMappingURL=trials.d.ts.map