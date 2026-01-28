/**
 * FDA Service
 *
 * Fetches and processes FDA documents including:
 * - Drug approvals (Drugs@FDA)
 * - Advisory committee meetings
 * - Complete Response Letters
 * - Label updates
 */
export interface FDAApproval {
    applicationNumber: string;
    applicationType: 'NDA' | 'BLA' | 'ANDA';
    brandName: string;
    genericName: string;
    activeIngredient: string;
    sponsorName: string;
    approvalDate: string;
    marketingStatus: 'Prescription' | 'OTC' | 'Discontinued';
    indications: string[];
    dosageForms: string[];
    routes: string[];
    reviewPriority: 'Standard' | 'Priority' | 'Breakthrough' | 'Fast Track' | 'Accelerated';
    therapeuticEquivalence?: string;
}
export interface AdvisoryCommitteeMeeting {
    date: string;
    committee: string;
    drug: string;
    sponsor: string;
    indication: string;
    outcome?: 'Positive' | 'Negative' | 'Split' | 'Pending';
    voteFor?: number;
    voteAgainst?: number;
    voteAbstain?: number;
    briefingDocUrl?: string;
    minutesUrl?: string;
}
export interface PDUFADate {
    drug: string;
    sponsor: string;
    indication: string;
    targetDate: string;
    applicationNumber?: string;
    applicationType: 'NDA' | 'BLA' | 'sNDA' | 'sBLA';
    status: 'Pending' | 'Approved' | 'CRL' | 'Withdrawn';
}
export interface CompleteResponseLetter {
    drug: string;
    sponsor: string;
    indication: string;
    crlDate: string;
    reasons?: string[];
    resubmissionDate?: string;
    outcome?: 'Approved' | 'Pending' | 'Withdrawn';
}
/**
 * Get FDA approval details for a drug
 * TODO: Implement Drugs@FDA scraping or API
 */
export declare function getFDAApproval(drugName: string): Promise<FDAApproval | null>;
/**
 * Get recent FDA approvals
 */
export declare function getRecentApprovals(options?: {
    daysBack?: number;
    therapeuticArea?: string;
    applicationType?: 'NDA' | 'BLA';
}): Promise<FDAApproval[]>;
/**
 * Search FDA approvals by indication
 */
export declare function searchApprovalsByIndication(indication: string): Promise<FDAApproval[]>;
/**
 * Get upcoming PDUFA dates
 */
export declare function getUpcomingPDUFADates(monthsAhead?: number): Promise<PDUFADate[]>;
/**
 * Get advisory committee calendar
 */
export declare function getAdvisoryCommitteeMeetings(options?: {
    monthsAhead?: number;
    committee?: string;
}): Promise<AdvisoryCommitteeMeeting[]>;
/**
 * Get historical advisory committee outcomes
 */
export declare function getAdCommOutcome(drug: string, sponsor?: string): Promise<AdvisoryCommitteeMeeting | null>;
/**
 * Get Complete Response Letters for a drug/company
 */
export declare function getCRLs(options?: {
    drug?: string;
    sponsor?: string;
    daysBack?: number;
}): Promise<CompleteResponseLetter[]>;
/**
 * Get current drug label
 */
export declare function getDrugLabel(drugName: string): Promise<{
    brandName: string;
    genericName: string;
    indications: string;
    dosageAndAdministration: string;
    warnings: string;
    adverseReactions: string;
    clinicalStudies: string;
    labelDate: string;
    labelUrl: string;
} | null>;
/**
 * Get label history (updates over time)
 */
export declare function getLabelHistory(drugName: string): Promise<{
    date: string;
    changeType: 'Initial' | 'Safety Update' | 'Indication Expansion' | 'Dosing Change';
    summary: string;
}[]>;
/**
 * Extract indications from label text
 */
export declare function extractIndicationsFromLabel(labelText: string): string[];
/**
 * Search FDA OpenFDA API
 */
export declare function searchOpenFDA(query: string, options?: {
    count?: string;
    limit?: number;
}): Promise<any>;
/**
 * Analyze AdComm voting patterns
 */
export declare function analyzeAdCommVotes(meetings: AdvisoryCommitteeMeeting[]): {
    totalMeetings: number;
    positiveRate: number;
    byCommittee: Record<string, {
        positive: number;
        negative: number;
    }>;
};
/**
 * Calculate PDUFA date success rate
 */
export declare function analyzePDUFAOutcomes(dates: PDUFADate[]): {
    total: number;
    approved: number;
    crl: number;
    withdrawn: number;
    approvalRate: number;
};
/**
 * Assess regulatory risk based on historical data
 */
export declare function assessRegulatoryRisk(drug: string, indication: string, hasAdComm: boolean, adCommOutcome?: 'Positive' | 'Negative' | 'Split'): 'Low' | 'Medium' | 'High';
/**
 * Get upcoming FDA events for a drug
 */
export declare function getUpcomingFDAEvents(drugName: string): Promise<{
    type: 'PDUFA' | 'AdComm' | 'Label Update' | 'Other';
    date: string;
    description: string;
}[]>;
/**
 * Build FDA timeline for a drug
 */
export declare function buildFDATimeline(drugName: string): Promise<{
    date: string;
    event: string;
    description: string;
}[]>;
//# sourceMappingURL=fda.d.ts.map