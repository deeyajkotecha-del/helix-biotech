/**
 * Key Opinion Leaders (KOL) Service
 *
 * Identifies and tracks key opinion leaders from publication data.
 * Normalizes author names and aggregates publication metrics.
 */
import { KOL, Publication, Author } from '../types/schema';
/**
 * Build KOL database from publications
 * TODO: Implement name normalization
 * TODO: Handle institution changes over time
 * TODO: Calculate h-index
 */
export declare function buildKOLsFromPublications(publications: Publication[]): Promise<KOL[]>;
/**
 * Get top KOLs for a condition
 */
export declare function getTopKOLsForCondition(condition: string, options?: {
    limit?: number;
    minPublications?: number;
    yearsBack?: number;
}): Promise<KOL[]>;
/**
 * Get KOL profile by name
 */
export declare function getKOLByName(name: string): Promise<KOL | null>;
/**
 * Get KOLs at an institution
 */
export declare function getKOLsByInstitution(institution: string): Promise<KOL[]>;
/**
 * Get KOLs for a specific drug/molecule
 */
export declare function getKOLsForDrug(drugName: string): Promise<KOL[]>;
/**
 * Normalize author name to standard format
 * Returns: "LastName FirstName MiddleInitial"
 */
export declare function normalizeAuthorName(author: Author | string): string;
/**
 * Generate canonical name ID (for deduplication)
 */
export declare function generateKOLId(name: string): string;
/**
 * Check if two names likely refer to same person
 */
export declare function namesSimilar(name1: string, name2: string): boolean;
/**
 * Calculate h-index from citation data
 */
export declare function calculateHIndex(citationCounts: number[]): number;
/**
 * Determine if KOL is currently active
 */
export declare function isActiveKOL(kol: KOL, yearsThreshold?: number): boolean;
/**
 * Calculate KOL score (composite ranking metric)
 */
export declare function calculateKOLScore(kol: KOL): number;
/**
 * Detect potential industry affiliations from publications
 */
export declare function detectIndustryAffiliations(publications: Publication[]): string[];
/**
 * Extract therapeutic areas from publication MeSH terms
 */
export declare function extractTherapeuticAreas(publications: Publication[]): {
    area: string;
    count: number;
}[];
//# sourceMappingURL=kols.d.ts.map