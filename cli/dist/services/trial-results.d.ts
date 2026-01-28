/**
 * Trial Results Service
 *
 * Extracts and processes clinical trial results from ClinicalTrials.gov.
 * Parses efficacy endpoints, statistical analyses, and safety data.
 */
import { TrialResults, SafetyData } from '../types/schema';
export interface FullTrialData {
    nctId: string;
    title: string;
    officialTitle?: string;
    phase: string;
    status: string;
    sponsor: string;
    sponsorClass?: string;
    collaborators?: string[];
    startDate?: string;
    completionDate?: string;
    enrollment: number;
    enrollmentType?: string;
    arms: {
        id: string;
        title: string;
        description?: string;
        type?: string;
        intervention?: string;
        n?: number;
    }[];
    studyType?: string;
    allocation?: string;
    interventionModel?: string;
    primaryPurpose?: string;
    masking?: string;
    hasResults: boolean;
    resultsFirstPosted?: string;
    primaryOutcomes: FormattedOutcome[];
    secondaryOutcomes: FormattedOutcome[];
    safety?: FormattedSafety;
    fetchedAt: string;
}
export interface FormattedOutcome {
    title: string;
    description?: string;
    timeFrame?: string;
    type: string;
    units?: string;
    paramType?: string;
    results: {
        armId: string;
        armTitle: string;
        value: string;
        spread?: string;
        ci?: {
            lower: string;
            upper: string;
        };
        n?: number;
    }[];
    analysis?: {
        method?: string;
        pValue?: string;
        pValueSignificant?: boolean;
        estimateType?: string;
        estimateValue?: string;
        ci?: {
            lower: string;
            upper: string;
            pct: number;
        };
        description?: string;
    };
}
export interface FormattedSafety {
    timeFrame?: string;
    description?: string;
    arms: {
        id: string;
        title: string;
        seriousNumAffected: number;
        seriousNumAtRisk: number;
        otherNumAffected: number;
        otherNumAtRisk: number;
    }[];
    seriousEvents: FormattedAE[];
    otherEvents: FormattedAE[];
}
export interface FormattedAE {
    term: string;
    organSystem?: string;
    sourceVocabulary?: string;
    byArm: {
        armId: string;
        armTitle: string;
        numAffected: number;
        numAtRisk: number;
        rate: number;
        numEvents?: number;
    }[];
    totalAffected: number;
    totalAtRisk: number;
    overallRate: number;
}
/**
 * Get comprehensive trial data with results
 * This is the main function for the /api/trial/:nctId/results endpoint
 */
export declare function getFullTrialData(nctId: string): Promise<FullTrialData | null>;
/**
 * Get full results for a trial (original function, kept for compatibility)
 */
export declare function getTrialResults(nctId: string): Promise<TrialResults | null>;
/**
 * Get safety data for a trial
 */
export declare function getSafetyData(nctId: string): Promise<SafetyData | null>;
/**
 * Get results for multiple trials (batch)
 */
export declare function getBatchTrialResults(nctIds: string[]): Promise<Map<string, TrialResults>>;
/**
 * Extract primary endpoint results summary
 */
export declare function extractPrimaryEndpointSummary(results: TrialResults): {
    endpoint: string;
    arms: {
        name: string;
        value: string;
        n: number;
    }[];
    pValue?: string;
    significant?: boolean;
}[];
/**
 * Compare efficacy across arms for a specific endpoint
 */
export declare function compareArmEfficacy(results: TrialResults, endpointTitle: string): {
    arms: {
        id: string;
        title: string;
        value: number;
        ci?: [number, number];
    }[];
    comparison?: {
        difference: number;
        pValue: string;
        significant: boolean;
    };
} | null;
/**
 * Extract all p-values from a trial's results
 */
export declare function extractPValues(results: TrialResults): {
    endpoint: string;
    comparison: string;
    pValue: string;
    significant: boolean;
}[];
/**
 * Get safety summary from adverse events
 */
export declare function getSafetySummary(safety: SafetyData): {
    totalSeriousEvents: number;
    totalOtherEvents: number;
    topSeriousEvents: {
        term: string;
        rate: number;
    }[];
    topOtherEvents: {
        term: string;
        rate: number;
    }[];
};
/**
 * Determine if p-value is statistically significant
 */
export declare function isSignificant(pValue: string, threshold?: number): boolean;
/**
 * Parse confidence interval string
 */
export declare function parseCI(ciString: string): [number, number] | null;
/**
 * Normalize endpoint name for matching
 */
export declare function normalizeEndpointName(name: string): string;
/**
 * Compare multiple trials side by side
 */
export declare function compareTrials(nctIds: string[]): Promise<{
    trials: FullTrialData[];
    comparison: {
        populations: {
            nctId: string;
            enrollment: number;
            arms: string[];
        }[];
        primaryEndpoints: {
            endpoint: string;
            byTrial: {
                nctId: string;
                value: string;
                pValue?: string;
                significant?: boolean;
            }[];
        }[];
        safetyHighlights: {
            event: string;
            byTrial: {
                nctId: string;
                rate: number;
            }[];
        }[];
        endpointDifferences: string[];
    };
}>;
//# sourceMappingURL=trial-results.d.ts.map