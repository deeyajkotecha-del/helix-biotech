/**
 * Publications Service
 *
 * Fetches and processes publications from PubMed.
 * Handles article metadata, author extraction, and trial linkage.
 */
import { Publication, Author } from '../types/schema';
/**
 * Search publications by query
 * TODO: Implement full pagination
 * TODO: Add date filtering
 * TODO: Add publication type filtering
 */
export declare function searchPublications(query: string, options?: {
    maxResults?: number;
    fromDate?: string;
    toDate?: string;
    publicationTypes?: string[];
}): Promise<Publication[]>;
/**
 * Get publication by PMID
 */
export declare function getPublicationByPmid(pmid: string): Promise<Publication | null>;
/**
 * Get multiple publications by PMIDs
 */
export declare function getPublicationsByPmids(pmids: string[]): Promise<Map<string, Publication>>;
/**
 * Get publication count by year for a query
 */
export declare function getPublicationCountsByYear(query: string, years: number[]): Promise<{
    year: number;
    count: number;
}[]>;
/**
 * Get total publication count for a query
 */
export declare function getPublicationCount(query: string): Promise<number>;
/**
 * Extract authors from publication XML
 */
export declare function parseAuthors(authorListXml: string): Author[];
/**
 * Determine author position (first, last, middle)
 */
export declare function determineAuthorPosition(index: number, total: number): Author['authorPosition'];
/**
 * Extract institution from affiliation string
 */
export declare function extractInstitution(affiliation: string): string | null;
/**
 * Extract email from affiliation string
 */
export declare function extractEmail(text: string): string | null;
/**
 * Extract NCT IDs mentioned in publication text/abstract
 */
export declare function extractNctIds(text: string): string[];
/**
 * Find publications that mention a specific trial
 */
export declare function findPublicationsForTrial(nctId: string): Promise<Publication[]>;
/**
 * Find publications that mention a drug name
 */
export declare function findPublicationsForDrug(drugName: string): Promise<Publication[]>;
/**
 * Categorize publication by type
 */
export declare function categorizePublication(pubTypes: string[]): 'Clinical Trial' | 'Review' | 'Meta-Analysis' | 'Case Report' | 'Other';
/**
 * Check if publication is high-impact (by journal)
 */
export declare function isHighImpactJournal(journalName: string): boolean;
/**
 * Parse PubMed XML response
 */
export declare function parsePubmedXml(xml: string): Publication[];
//# sourceMappingURL=publications.d.ts.map