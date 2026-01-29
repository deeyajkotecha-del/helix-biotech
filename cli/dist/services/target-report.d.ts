/**
 * Target Report Service - Investment Ready
 *
 * Generates comprehensive intelligence reports for therapeutic targets,
 * compiling data from trials, publications, and curated asset database.
 * For uncurated targets, uses AI-powered research with web search.
 */
import { ReportData } from './export';
import { Trial, Publication } from '../types/schema';
import { KnownAsset, InvestmentMetrics } from '../data/known-assets';
import { DiscoveredAsset } from './ai-research-agent';
export interface DataSourceInfo {
    type: 'curated' | 'ai-research' | 'hybrid';
    lastUpdated: string;
    cacheAge?: string;
    fromCache?: boolean;
    assetsDiscovered?: number;
    searchQueries?: string[];
    totalSourcesChecked?: number;
    error?: string;
}
export interface ExtendedReportData extends ReportData {
    curatedAssets: KnownAsset[];
    investmentMetrics: InvestmentMetrics;
    dataSource: DataSourceInfo;
    discoveredAssets?: DiscoveredAsset[];
    assets?: any[];
    assetStats?: any;
    assetReport?: any;
}
/**
 * Generate comprehensive investment-ready target report
 * Uses curated data when available, falls back to AI research for uncurated targets
 */
export declare function generateTargetReport(target: string, options?: {
    forceRefresh?: boolean;
}): Promise<ExtendedReportData>;
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