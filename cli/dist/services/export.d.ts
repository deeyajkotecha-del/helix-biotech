/**
 * Export Service
 *
 * Generates Excel and CSV exports for Helix reports.
 * Supports multi-tab workbooks and single-file CSV exports.
 */
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
}
/**
 * Generate multi-tab Excel workbook from report data
 */
export declare function generateExcel(reportData: ReportData): Buffer;
/**
 * Generate CSV from array of objects
 */
export declare function generateCSV(data: any[], filename?: string): string;
/**
 * Generate multiple CSVs as a zip (for multi-section reports)
 */
export declare function generateMultiCSV(reportData: ReportData): Record<string, string>;
/**
 * Get content type for export format
 */
export declare function getContentType(format: 'xlsx' | 'csv'): string;
/**
 * Get file extension for export format
 */
export declare function getFileExtension(format: 'xlsx' | 'csv'): string;
//# sourceMappingURL=export.d.ts.map