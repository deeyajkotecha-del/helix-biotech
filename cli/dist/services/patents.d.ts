/**
 * Patents & Exclusivity Service
 *
 * Provides patent and exclusivity data for FDA-approved drugs using:
 * - FDA Orange Book ZIP download (patents + exclusivities for NDA drugs)
 * - OpenFDA drugsfda API (drug approval lookup)
 * - BPCIA 12-year exclusivity calculation for biologics (BLA)
 */
import { DrugApproval, OrangeBookPatent, OrangeBookExclusivity, DrugPatentProfile } from '../types/schema';
/**
 * Search OpenFDA drugsfda endpoint for a drug by name.
 * Returns approval information including application number.
 */
export declare function searchDrugApprovals(drugName: string): Promise<DrugApproval[]>;
/**
 * Get Orange Book patents for a given application number.
 */
export declare function getPatentsForApplication(applicationNumber: string): Promise<OrangeBookPatent[]>;
/**
 * Get Orange Book exclusivities for a given application number.
 */
export declare function getExclusivitiesForApplication(applicationNumber: string): Promise<OrangeBookExclusivity[]>;
/**
 * Calculate the effective Loss of Exclusivity (LOE) date.
 * This is the latest of:
 * - Latest patent expiry
 * - Latest exclusivity expiry
 * - 12-year BPCIA exclusivity for biologics
 */
export declare function calculateEffectiveLOE(patents: OrangeBookPatent[], exclusivities: OrangeBookExclusivity[], approval?: DrugApproval): {
    effectiveLOE: string | null;
    latestPatentExpiry: string | null;
    latestExclusivityExpiry: string | null;
    biologicExclusivityExpiry: string | null;
    daysUntilLOE: number | null;
};
/**
 * Get complete patent/exclusivity profile for a drug.
 * This is the main function called by the API endpoint.
 */
export declare function getDrugPatentProfile(drugName: string): Promise<DrugPatentProfile | null>;
/**
 * Get patent profiles for all drugs used in trials for a condition.
 * Cross-references landscape molecules with patent data.
 */
export declare function getPatentsByCondition(condition: string): Promise<DrugPatentProfile[]>;
//# sourceMappingURL=patents.d.ts.map