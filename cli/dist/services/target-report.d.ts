/**
 * Target Report Service - Investment Ready
 *
 * Generates comprehensive intelligence reports for therapeutic targets,
 * compiling data from trials, publications, and curated asset database.
 */
import { ReportData } from './export';
import { Trial, Publication } from '../types/schema';
import { KnownAsset, InvestmentMetrics } from '../data/known-assets';
export interface ExtendedReportData extends ReportData {
    curatedAssets: KnownAsset[];
    investmentMetrics: InvestmentMetrics;
    assets?: any[];
    assetStats?: any;
    assetReport?: any;
}
/**
 * Generate comprehensive investment-ready target report
 */
export declare function generateTargetReport(target: string): Promise<ExtendedReportData>;
/**
 * Get trial analytics for a report
 */
export declare function getTrialAnalytics(trials: Trial[]): {
    phaseBreakdown: Record<import("../types/schema").TrialPhase, number>;
    statusBreakdown: Record<import("../types/schema").TrialStatus, number>;
    topSponsors: {
        sponsor: string;
        count: number;
        type: string;
    }[];
    byYear: Record<string, number>;
};
/**
 * Get publication analytics
 */
export declare function getPublicationAnalytics(publications: Publication[]): {
    byYear: Record<string, number>;
    byJournal: Record<string, number>;
};
//# sourceMappingURL=target-report.d.ts.map