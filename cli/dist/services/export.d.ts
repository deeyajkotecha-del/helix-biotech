/**
 * Export Service - Investment Ready
 *
 * Generates Excel exports with comprehensive asset data,
 * investment metrics, and regulatory information.
 */
import { KnownAsset, InvestmentMetrics } from '../data/known-assets';
export interface ReportData {
    target: string;
    generatedAt: string;
    summary: {
        totalTrials: number;
        activeTrials: number;
        totalPublications: number;
        totalDeals: number;
        totalKOLs: number;
    };
    trials: any[];
    publications: any[];
    deals: any[];
    kols: any[];
    pipeline?: any[];
    assets?: any[];
    assetStats?: any;
    curatedAssets?: KnownAsset[];
    investmentMetrics?: InvestmentMetrics;
}
/**
 * Generate investment-ready Excel workbook
 */
export declare function generateExcel(reportData: ReportData): Buffer;
export declare function generateCSV(data: any[], filename?: string): string;
export declare function generateMultiCSV(reportData: ReportData): Record<string, string>;
export declare function getContentType(format: 'xlsx' | 'csv'): string;
export declare function getFileExtension(format: 'xlsx' | 'csv'): string;
//# sourceMappingURL=export.d.ts.map