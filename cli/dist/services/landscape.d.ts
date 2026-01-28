/**
 * Therapeutic Landscape Service
 *
 * Fetches and combines data from multiple sources:
 * - ClinicalTrials.gov (clinical trials with pagination)
 * - RSS feeds (deals & news) with broader matching
 * - PubMed (research publications with proper year counts and KOL filtering)
 */
export interface ClinicalTrial {
    nctId: string;
    title: string;
    status: string;
    phase: string;
    sponsor: string;
    startDate: string | null;
    completionDate: string | null;
    enrollment: number | null;
    locations: string[];
    interventions: string[];
    primaryEndpoint: string | null;
    resultsAvailable: boolean;
}
export interface Molecule {
    name: string;
    mechanism: string | null;
    sponsor: string;
    highestPhase: string;
    trialCount: number;
    trialIds: string[];
    status: string;
}
export interface DealNews {
    title: string;
    link: string;
    pubDate: string;
    source: string;
    companies: string[];
    dealType: string | null;
    dealValue: string | null;
}
export interface Publication {
    pmid: string;
    title: string;
    authors: string[];
    journal: string;
    pubDate: string;
    year: number;
}
export interface KOL {
    name: string;
    institution: string | null;
    email: string | null;
    publicationCount: number;
    recentPublications: number;
    hIndex: number | null;
}
export interface LandscapeData {
    condition: string;
    fetchedAt: string;
    summary: {
        totalTrials: number;
        activeCompanies: number;
        recentDeals: number;
        totalPublications: number;
        uniqueMolecules: number;
    };
    clinicalTrials: {
        trials: ClinicalTrial[];
        phaseBreakdown: Record<string, number>;
        topSponsors: {
            name: string;
            count: number;
        }[];
        statusBreakdown: Record<string, number>;
    };
    molecules: Molecule[];
    dealsNews: DealNews[];
    research: {
        totalCount: number;
        byYear: {
            year: number;
            count: number;
        }[];
        topKOLs: KOL[];
    };
}
export declare function getLandscapeData(condition: string): Promise<LandscapeData>;
export declare function generateLandscapeCSV(data: LandscapeData): string;
//# sourceMappingURL=landscape.d.ts.map