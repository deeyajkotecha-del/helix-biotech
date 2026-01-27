/**
 * Companies Service
 *
 * Talks to your backend API to get XBI company data.
 * This service handles searching for companies and fetching their details.
 */
import { Company } from '../types';
/**
 * Search for companies by name or ticker
 * Uses fuzzy matching on the backend
 */
export declare function searchCompanies(query: string): Promise<Company[]>;
/**
 * Get a specific company by ticker
 */
export declare function getCompanyByTicker(ticker: string): Promise<Company | null>;
/**
 * Get all XBI companies
 */
export declare function getAllCompanies(): Promise<Company[]>;
//# sourceMappingURL=companies.d.ts.map