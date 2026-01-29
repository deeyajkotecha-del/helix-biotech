/**
 * Publications Service
 *
 * Fetches and processes publications from PubMed E-utilities API.
 * Handles article metadata, author extraction, and search.
 */
import { Publication, Author } from '../types/schema';
/**
 * Search publications by query using PubMed E-utilities
 */
export declare function searchPublications(query: string, options?: {
    maxResults?: number;
    fromDate?: string;
    toDate?: string;
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
 * Parse PubMed XML response into Publication objects
 */
export declare function parsePubmedXml(xml: string): Publication[];
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
 * Categorize publication by type
 */
export declare function categorizePublication(pubTypes: string[]): 'Clinical Trial' | 'Review' | 'Meta-Analysis' | 'Case Report' | 'Other';
/**
 * Check if publication is high-impact (by journal)
 */
export declare function isHighImpactJournal(journalName: string): boolean;
/**
 * Extract top authors from publications
 */
export declare function extractTopAuthors(publications: Publication[], limit?: number): {
    name: string;
    lastName: string;
    foreName: string;
    institution: string | null;
    publicationCount: number;
    firstAuthorCount: number;
    lastAuthorCount: number;
    recentPublications: number;
    isActive: boolean;
}[];
//# sourceMappingURL=publications.d.ts.map