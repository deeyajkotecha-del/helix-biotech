/**
 * Graphs Service
 *
 * Analyzes images/graphs from publications and presentations
 * using AI vision models. Extracts data from:
 * - Kaplan-Meier survival curves
 * - Bar charts (efficacy results)
 * - Forest plots
 * - Waterfall plots
 */
export interface ExtractedChartData {
    chartType: 'kaplan-meier' | 'bar' | 'forest' | 'waterfall' | 'line' | 'scatter' | 'unknown';
    title?: string;
    xAxis?: {
        label: string;
        values: (string | number)[];
    };
    yAxis?: {
        label: string;
        min?: number;
        max?: number;
    };
    series: {
        name: string;
        values: number[];
        color?: string;
    }[];
    annotations?: string[];
    confidence: number;
}
export interface KaplanMeierData {
    arms: {
        name: string;
        survivalProbabilities: {
            time: number;
            probability: number;
        }[];
        medianSurvival?: number;
        hazardRatio?: number;
        ciLower?: number;
        ciUpper?: number;
        pValue?: string;
        numberOfEvents?: number;
        numberOfAtRisk?: number[];
    }[];
    endpoint: string;
    followUpMonths?: number;
}
export interface ForestPlotData {
    studies: {
        name: string;
        effectSize: number;
        ciLower: number;
        ciUpper: number;
        weight?: number;
        pValue?: string;
    }[];
    overallEffect?: {
        effectSize: number;
        ciLower: number;
        ciUpper: number;
        pValue?: string;
    };
    heterogeneity?: {
        iSquared?: number;
        pValue?: string;
    };
    effectMeasure: 'OR' | 'RR' | 'HR' | 'Mean Difference' | 'SMD';
}
export interface WaterfallPlotData {
    patients: {
        id?: string;
        percentChange: number;
        response?: 'CR' | 'PR' | 'SD' | 'PD';
        biomarker?: string;
    }[];
    endpoint: string;
    responseThresholds?: {
        pr: number;
        pd: number;
    };
}
/**
 * Analyze an image and extract chart data
 * TODO: Integrate with Claude Vision API
 * TODO: Add support for multiple image formats
 */
export declare function analyzeChartImage(imageUrl: string | Buffer, context?: {
    paperTitle?: string;
    expectedChartType?: string;
    drug?: string;
}): Promise<ExtractedChartData>;
/**
 * Extract Kaplan-Meier data from image
 */
export declare function extractKaplanMeierData(imageUrl: string | Buffer): Promise<KaplanMeierData>;
/**
 * Extract forest plot data from image
 */
export declare function extractForestPlotData(imageUrl: string | Buffer): Promise<ForestPlotData>;
/**
 * Extract waterfall plot data from image
 */
export declare function extractWaterfallPlotData(imageUrl: string | Buffer): Promise<WaterfallPlotData>;
/**
 * Extract bar chart data from image
 */
export declare function extractBarChartData(imageUrl: string | Buffer): Promise<{
    categories: string[];
    series: {
        name: string;
        values: number[];
        errorBars?: number[];
    }[];
    pValues?: Record<string, string>;
}>;
/**
 * Preprocess image for better analysis
 */
export declare function preprocessImage(imageBuffer: Buffer): Promise<Buffer>;
/**
 * Detect chart type from image
 */
export declare function detectChartType(imageUrl: string | Buffer): Promise<{
    type: ExtractedChartData['chartType'];
    confidence: number;
}>;
/**
 * Extract text/labels from chart image
 */
export declare function extractChartLabels(imageUrl: string | Buffer): Promise<{
    title?: string;
    xAxisLabel?: string;
    yAxisLabel?: string;
    legendLabels?: string[];
    annotations?: string[];
}>;
/**
 * Generate prompt for Kaplan-Meier extraction
 */
export declare function getKaplanMeierPrompt(): string;
/**
 * Generate prompt for forest plot extraction
 */
export declare function getForestPlotPrompt(): string;
/**
 * Generate prompt for waterfall plot extraction
 */
export declare function getWaterfallPlotPrompt(): string;
/**
 * Validate extracted Kaplan-Meier data
 */
export declare function validateKaplanMeierData(data: KaplanMeierData): {
    valid: boolean;
    errors: string[];
};
/**
 * Validate extracted forest plot data
 */
export declare function validateForestPlotData(data: ForestPlotData): {
    valid: boolean;
    errors: string[];
};
/**
 * Convert image URL to base64
 */
export declare function imageUrlToBase64(url: string): Promise<string>;
/**
 * Estimate confidence based on data completeness
 */
export declare function estimateConfidence(data: ExtractedChartData): number;
//# sourceMappingURL=graphs.d.ts.map