/**
 * Target-Level Investment Analysis
 *
 * Contains investment thesis, market opportunity, risks, and catalysts
 * for each therapeutic target. This data is used in Excel exports and HTML reports.
 */
export interface EfficacyDataPoint {
    drug: string;
    trial: string;
    nctId?: string;
    phase: string;
    dose: string;
    endpoint: string;
    result: number;
    placebo: number;
    placeboAdjusted: number;
    indication: string;
    population?: string;
    timepoint?: string;
    source: string;
    notes?: string;
}
export interface DifferentiatorMatrix {
    drug: string;
    strategy: string;
    dosing: string;
    biomarker: string;
    halfLife: string;
    beyondIndication: string;
    mechanism?: string;
    administration?: string;
}
export interface TargetAnalysis {
    target: string;
    aliases: string[];
    investmentThesis: {
        headline: string;
        keyPoints: string[];
        fullText: string;
    };
    mechanism: {
        biology: string;
        rationale: string;
        uniqueValue: string;
    };
    marketOpportunity: {
        totalMarket: string;
        targetShare: string;
        patientPopulation: string;
        unmetNeed: string;
    };
    keyRisks: Array<{
        risk: string;
        severity: 'High' | 'Medium' | 'Low';
        mitigation?: string;
    }>;
    catalystsToWatch: Array<{
        event: string;
        timing: string;
        drug: string;
        significance: 'High' | 'Medium' | 'Low';
    }>;
    efficacyComparison: EfficacyDataPoint[];
    differentiators: DifferentiatorMatrix[];
    lastUpdated: string;
    analyst?: string;
}
export declare const TL1A_ANALYSIS: TargetAnalysis;
export declare const B7H3_ANALYSIS: TargetAnalysis;
export declare const TARGET_ANALYSES: Record<string, TargetAnalysis>;
export declare function getTargetAnalysis(target: string): TargetAnalysis | null;
//# sourceMappingURL=target-analysis.d.ts.map