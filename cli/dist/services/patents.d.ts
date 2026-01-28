/**
 * Patents Service
 *
 * Fetches patent data from USPTO, Orange Book, and EPO.
 * Tracks patent expiry dates and exclusivity periods.
 */
import { Patent, PatentType } from '../types/schema';
/**
 * Search patents by drug name
 * TODO: Implement USPTO API integration
 * TODO: Add EPO integration for international patents
 */
export declare function searchPatentsByDrug(drugName: string): Promise<Patent[]>;
/**
 * Get patent by number
 */
export declare function getPatentByNumber(patentNumber: string): Promise<Patent | null>;
/**
 * Get all patents for a company
 */
export declare function getPatentsByCompany(companyName: string): Promise<Patent[]>;
/**
 * Get Orange Book listings for a drug
 */
export declare function getOrangeBookListings(drugName: string): Promise<Patent[]>;
/**
 * Check for upcoming patent expirations
 */
export declare function getExpiringPatents(withinMonths: number, options?: {
    drugNames?: string[];
    companies?: string[];
}): Promise<Patent[]>;
/**
 * Calculate effective patent expiry (including extensions)
 */
export declare function calculateEffectiveExpiry(patent: Patent): string | null;
/**
 * Determine patent type from claims/title
 */
export declare function inferPatentType(title: string, claims?: string[]): PatentType;
/**
 * Assess patent strength (simplified heuristic)
 */
export declare function assessPatentStrength(patent: Patent): 'Strong' | 'Moderate' | 'Weak';
/**
 * Check for generic entry window
 */
export declare function getGenericEntryWindow(patent: Patent): {
    earliestEntry: string | null;
    daysUntilEntry: number | null;
    hasExclusivity: boolean;
};
/**
 * Build patent landscape for a drug
 */
export declare function buildPatentLandscape(drugName: string): Promise<{
    corePatents: Patent[];
    methodPatents: Patent[];
    formulationPatents: Patent[];
    earliestExpiry: string | null;
    latestExpiry: string | null;
    activeLitigation: {
        patent: Patent;
        challenger: string;
        status: string;
    }[];
}>;
/**
 * Identify patent cliffs
 */
export declare function identifyPatentCliffs(year: number): Promise<{
    drug: string;
    company: string;
    expiryDate: string;
    estimatedRevenueAtRisk: number;
}[]>;
/**
 * Parse Orange Book data
 */
export declare function parseOrangeBookEntry(entry: any): Patent;
/**
 * Normalize patent number format
 */
export declare function normalizePatentNumber(number: string): string;
//# sourceMappingURL=patents.d.ts.map