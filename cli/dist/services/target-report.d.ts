/**
 * Target Report Service
 *
 * Generates comprehensive intelligence reports for therapeutic targets,
 * compiling data from trials, publications, and the intelligent asset research engine.
 */
import { ReportData } from './export';
import { AssetResearchReport, ResearchedAsset } from './asset-research';
import { Trial, Publication } from '../types/schema';
export interface ExtendedReportData extends ReportData {
    assets: ResearchedAsset[];
    assetStats: AssetResearchReport['summary'];
    assetReport: AssetResearchReport;
}
/**
 * Generate comprehensive target report
 * Uses the intelligent asset research engine for high-quality asset data
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