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

// ============================================
// Types
// ============================================

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
  confidence: number; // 0-1 confidence score
}

export interface KaplanMeierData {
  arms: {
    name: string;
    survivalProbabilities: { time: number; probability: number }[];
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
    pr: number;  // Partial response threshold (typically -30%)
    pd: number;  // Progressive disease threshold (typically +20%)
  };
}

// ============================================
// Main Functions
// ============================================

/**
 * Analyze an image and extract chart data
 * TODO: Integrate with Claude Vision API
 * TODO: Add support for multiple image formats
 */
export async function analyzeChartImage(
  imageUrl: string | Buffer,
  context?: {
    paperTitle?: string;
    expectedChartType?: string;
    drug?: string;
  }
): Promise<ExtractedChartData> {
  // TODO: Send image to Claude Vision
  // TODO: Parse structured response
  // TODO: Validate extracted data
  throw new Error('Not implemented');
}

/**
 * Extract Kaplan-Meier data from image
 */
export async function extractKaplanMeierData(
  imageUrl: string | Buffer
): Promise<KaplanMeierData> {
  // TODO: Use vision model with specific KM prompt
  // TODO: Extract survival curves
  // TODO: Extract statistics from legend/table
  throw new Error('Not implemented');
}

/**
 * Extract forest plot data from image
 */
export async function extractForestPlotData(
  imageUrl: string | Buffer
): Promise<ForestPlotData> {
  // TODO: Identify individual studies
  // TODO: Extract effect sizes and CIs
  // TODO: Extract overall effect
  throw new Error('Not implemented');
}

/**
 * Extract waterfall plot data from image
 */
export async function extractWaterfallPlotData(
  imageUrl: string | Buffer
): Promise<WaterfallPlotData> {
  // TODO: Extract bar heights
  // TODO: Identify response categories
  throw new Error('Not implemented');
}

/**
 * Extract bar chart data from image
 */
export async function extractBarChartData(
  imageUrl: string | Buffer
): Promise<{
  categories: string[];
  series: { name: string; values: number[]; errorBars?: number[] }[];
  pValues?: Record<string, string>;
}> {
  // TODO: Implement
  throw new Error('Not implemented');
}

// ============================================
// Image Processing
// ============================================

/**
 * Preprocess image for better analysis
 */
export async function preprocessImage(imageBuffer: Buffer): Promise<Buffer> {
  // TODO: Enhance contrast
  // TODO: Remove watermarks if possible
  // TODO: Crop to chart area
  throw new Error('Not implemented');
}

/**
 * Detect chart type from image
 */
export async function detectChartType(
  imageUrl: string | Buffer
): Promise<{
  type: ExtractedChartData['chartType'];
  confidence: number;
}> {
  // TODO: Use vision model to classify
  throw new Error('Not implemented');
}

/**
 * Extract text/labels from chart image
 */
export async function extractChartLabels(
  imageUrl: string | Buffer
): Promise<{
  title?: string;
  xAxisLabel?: string;
  yAxisLabel?: string;
  legendLabels?: string[];
  annotations?: string[];
}> {
  // TODO: OCR-like extraction via vision model
  throw new Error('Not implemented');
}

// ============================================
// Prompts for Vision Model
// ============================================

/**
 * Generate prompt for Kaplan-Meier extraction
 */
export function getKaplanMeierPrompt(): string {
  return `Analyze this Kaplan-Meier survival curve and extract the following data:

1. For each arm/group (treatment vs control):
   - Name of the group
   - Survival probabilities at each time point visible
   - Median survival time if shown
   - Number at risk at each time point (if shown in table below)

2. Statistical information:
   - Hazard ratio (HR) if shown
   - 95% confidence interval for HR
   - P-value
   - Log-rank test result if shown

3. General information:
   - Endpoint being measured (e.g., "Overall Survival", "Progression-Free Survival")
   - Maximum follow-up time shown on x-axis

Return the data as structured JSON.`;
}

/**
 * Generate prompt for forest plot extraction
 */
export function getForestPlotPrompt(): string {
  return `Analyze this forest plot and extract the following data:

1. For each study/subgroup shown:
   - Study name or subgroup label
   - Effect size (point estimate)
   - Lower bound of confidence interval
   - Upper bound of confidence interval
   - Weight (if shown)
   - P-value (if shown)

2. Overall/summary effect:
   - Combined effect size
   - 95% CI bounds
   - P-value

3. Heterogeneity statistics:
   - I-squared value
   - P-value for heterogeneity test

4. Effect measure being used (OR, RR, HR, Mean Difference, etc.)

Return the data as structured JSON.`;
}

/**
 * Generate prompt for waterfall plot extraction
 */
export function getWaterfallPlotPrompt(): string {
  return `Analyze this waterfall plot and extract the following data:

1. For each patient bar:
   - Percent change from baseline (height of bar)
   - Response category if color-coded (CR, PR, SD, PD)
   - Any biomarker status indicated

2. Response thresholds:
   - Line indicating PR threshold (typically -30%)
   - Line indicating PD threshold (typically +20%)

3. Endpoint being measured (e.g., "Best % Change in Tumor Size")

Return the data as structured JSON with an array of patient data.`;
}

// ============================================
// Data Validation
// ============================================

/**
 * Validate extracted Kaplan-Meier data
 */
export function validateKaplanMeierData(data: KaplanMeierData): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check arms exist
  if (!data.arms || data.arms.length === 0) {
    errors.push('No survival arms found');
  }

  for (const arm of data.arms) {
    // Survival probabilities should be decreasing
    const probs = arm.survivalProbabilities;
    for (let i = 1; i < probs.length; i++) {
      if (probs[i].probability > probs[i - 1].probability) {
        errors.push(`Survival probability increased at time ${probs[i].time} for ${arm.name}`);
      }
    }

    // Probabilities should be 0-1
    for (const p of probs) {
      if (p.probability < 0 || p.probability > 1) {
        errors.push(`Invalid probability ${p.probability} for ${arm.name}`);
      }
    }

    // HR should be positive
    if (arm.hazardRatio && arm.hazardRatio <= 0) {
      errors.push(`Invalid hazard ratio ${arm.hazardRatio}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validate extracted forest plot data
 */
export function validateForestPlotData(data: ForestPlotData): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check studies exist
  if (!data.studies || data.studies.length === 0) {
    errors.push('No studies found');
  }

  for (const study of data.studies) {
    // CI lower should be less than upper
    if (study.ciLower > study.ciUpper) {
      errors.push(`CI bounds inverted for ${study.name}`);
    }

    // Effect size should be within CI
    if (study.effectSize < study.ciLower || study.effectSize > study.ciUpper) {
      errors.push(`Effect size outside CI for ${study.name}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

// ============================================
// Utility Functions
// ============================================

/**
 * Convert image URL to base64
 */
export async function imageUrlToBase64(url: string): Promise<string> {
  // TODO: Fetch image and convert
  throw new Error('Not implemented');
}

/**
 * Estimate confidence based on data completeness
 */
export function estimateConfidence(data: ExtractedChartData): number {
  let score = 0;

  if (data.chartType !== 'unknown') score += 0.2;
  if (data.title) score += 0.1;
  if (data.xAxis?.label) score += 0.1;
  if (data.yAxis?.label) score += 0.1;
  if (data.series.length > 0) score += 0.3;
  if (data.series.some(s => s.values.length > 3)) score += 0.2;

  return Math.min(score, 1);
}
