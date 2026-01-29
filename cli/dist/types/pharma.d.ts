/**
 * Pharma Intelligence Types
 */
export interface PharmaCompany {
    ticker: string;
    name: string;
    cik: string;
    irPageUrl: string;
    cdnBase?: string;
    urlPatterns?: {
        jpm?: string;
        quarterly?: string;
        annual?: string;
    };
    verified: boolean;
}
export interface PipelineAsset {
    drugName: string;
    genericName?: string;
    mechanism: string;
    modality: string;
    phase: number;
    indication: string;
    therapeuticArea: string;
    partner?: string;
    expectedReadout?: string;
    expectedApproval?: string;
    isPriority: boolean;
    peakRevenuePotential?: string;
    notes?: string;
    source: string;
    extractedAt: string;
}
export interface Catalyst {
    date: string;
    dateType: 'exact' | 'quarter' | 'half' | 'year';
    eventType: 'phase3_readout' | 'phase2_readout' | 'approval' | 'filing' | 'advisory_committee' | 'conference';
    drugName: string;
    indication: string;
    description: string;
    significance: 'high' | 'medium' | 'low';
    source: string;
}
export interface RevenueOpportunity {
    therapeuticArea: string;
    targetYear: string;
    revenueEstimate: string;
    riskAdjusted: boolean;
    keyAssets: string[];
    source: string;
}
export interface Deal {
    date: string;
    type: string;
    targetCompany?: string;
    asset?: string;
    therapeuticArea: string;
    rationale?: string;
    source: string;
}
export interface StrategicPriorities {
    priorities: string[];
    therapeuticFocus: string[];
    modalityInvestments: string[];
    whitespaceAreas: string[];
    bdAppetite: {
        highInterest: string[];
        moderateInterest: string[];
        lowInterest: string[];
    };
    keyQuotes: {
        quote: string;
        speaker: string;
        context: string;
    }[];
    source: string;
    extractedAt: string;
}
export interface PipelineStats {
    totalAssets: number;
    byPhase: Record<string, number>;
    byTherapeuticArea: Record<string, number>;
    byModality: Record<string, number>;
}
export interface PharmaProfile {
    company: PharmaCompany;
    lastUpdated: string;
    keyFinancials?: {
        rdSpend?: string;
        bdInvestmentSince2021?: string;
        phase3StudiesOngoing?: number;
        expectedLaunches?: string;
    };
    pipeline: PipelineAsset[];
    pipelineStats: PipelineStats;
    revenueOpportunities: RevenueOpportunity[];
    catalysts: Catalyst[];
    recentDeals: Deal[];
    strategy: StrategicPriorities;
}
//# sourceMappingURL=pharma.d.ts.map