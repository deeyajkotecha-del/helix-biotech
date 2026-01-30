/**
 * Arrowhead Pharmaceuticals (ARWR) Company Profile
 *
 * Curated data from investor presentations and SEC filings.
 * Platform: TRiM (Targeted RNAi Molecule) technology
 */
export interface CompanyProfile {
    ticker: string;
    name: string;
    description: string;
    platform: string;
    therapeuticFocus: string[];
    headquarters: string;
    founded: number;
    employees?: number;
    website: string;
    irUrl: string;
}
export interface PipelineAsset {
    name: string;
    codeNames: string[];
    target: string;
    modality: string;
    phase: 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2b' | 'Phase 3' | 'Filed' | 'Approved';
    status: 'Active' | 'On Hold' | 'Discontinued';
    leadIndication: string;
    otherIndications?: string[];
    partner?: string;
    partnerTerritory?: string;
    trials?: string[];
    keyData?: string;
    nextCatalyst?: string;
    catalystDate?: string;
    regulatoryDesignations?: string[];
    notes?: string;
}
export interface ClinicalDataPoint {
    drug: string;
    trial: string;
    indication: string;
    phase: string;
    endpoint: string;
    result: string;
    comparator?: string;
    comparatorResult?: string;
    pValue?: string;
    nPatients?: number;
    duration?: string;
    source: string;
    sourceDate: string;
    conference?: string;
}
export interface UpcomingCatalyst {
    drug: string;
    event: string;
    expectedDate: string;
    type: 'data-readout' | 'regulatory' | 'conference' | 'commercial' | 'other';
    importance: 'high' | 'medium' | 'low';
    notes?: string;
}
export interface Presentation {
    id: string;
    title: string;
    date: string;
    event?: string;
    url: string;
    type: 'corporate' | 'clinical' | 'conference' | 'earnings' | 'poster';
    fileSize?: string;
    downloaded?: boolean;
    analyzed?: boolean;
}
export declare const ARWR_PROFILE: CompanyProfile;
export declare const ARWR_PIPELINE: PipelineAsset[];
export declare const ARWR_CLINICAL_DATA: ClinicalDataPoint[];
export declare const ARWR_CATALYSTS: UpcomingCatalyst[];
export declare const ARWR_PRESENTATIONS: Presentation[];
export declare function getARWRProfile(): {
    company: CompanyProfile;
    pipeline: PipelineAsset[];
    clinicalData: ClinicalDataPoint[];
    catalysts: UpcomingCatalyst[];
    presentations: Presentation[];
    stats: {
        totalPipelineAssets: number;
        phase3Programs: number;
        approvedProducts: number;
        partneredPrograms: number;
        upcomingCatalysts: number;
        totalPresentations: number;
    };
};
export declare function getARWRPipeline(): PipelineAsset[];
export declare function getARWRCatalysts(): UpcomingCatalyst[];
export declare function getARWRPresentations(): Presentation[];
//# sourceMappingURL=arwr.d.ts.map