"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.analyzeChartImage = analyzeChartImage;
exports.extractKaplanMeierData = extractKaplanMeierData;
exports.extractForestPlotData = extractForestPlotData;
exports.extractWaterfallPlotData = extractWaterfallPlotData;
exports.extractBarChartData = extractBarChartData;
exports.preprocessImage = preprocessImage;
exports.detectChartType = detectChartType;
exports.extractChartLabels = extractChartLabels;
exports.getKaplanMeierPrompt = getKaplanMeierPrompt;
exports.getForestPlotPrompt = getForestPlotPrompt;
exports.getWaterfallPlotPrompt = getWaterfallPlotPrompt;
exports.validateKaplanMeierData = validateKaplanMeierData;
exports.validateForestPlotData = validateForestPlotData;
exports.imageUrlToBase64 = imageUrlToBase64;
exports.estimateConfidence = estimateConfidence;
// ============================================
// Main Functions
// ============================================
/**
 * Analyze an image and extract chart data
 * TODO: Integrate with Claude Vision API
 * TODO: Add support for multiple image formats
 */
async function analyzeChartImage(imageUrl, context) {
    // TODO: Send image to Claude Vision
    // TODO: Parse structured response
    // TODO: Validate extracted data
    throw new Error('Not implemented');
}
/**
 * Extract Kaplan-Meier data from image
 */
async function extractKaplanMeierData(imageUrl) {
    // TODO: Use vision model with specific KM prompt
    // TODO: Extract survival curves
    // TODO: Extract statistics from legend/table
    throw new Error('Not implemented');
}
/**
 * Extract forest plot data from image
 */
async function extractForestPlotData(imageUrl) {
    // TODO: Identify individual studies
    // TODO: Extract effect sizes and CIs
    // TODO: Extract overall effect
    throw new Error('Not implemented');
}
/**
 * Extract waterfall plot data from image
 */
async function extractWaterfallPlotData(imageUrl) {
    // TODO: Extract bar heights
    // TODO: Identify response categories
    throw new Error('Not implemented');
}
/**
 * Extract bar chart data from image
 */
async function extractBarChartData(imageUrl) {
    // TODO: Implement
    throw new Error('Not implemented');
}
// ============================================
// Image Processing
// ============================================
/**
 * Preprocess image for better analysis
 */
async function preprocessImage(imageBuffer) {
    // TODO: Enhance contrast
    // TODO: Remove watermarks if possible
    // TODO: Crop to chart area
    throw new Error('Not implemented');
}
/**
 * Detect chart type from image
 */
async function detectChartType(imageUrl) {
    // TODO: Use vision model to classify
    throw new Error('Not implemented');
}
/**
 * Extract text/labels from chart image
 */
async function extractChartLabels(imageUrl) {
    // TODO: OCR-like extraction via vision model
    throw new Error('Not implemented');
}
// ============================================
// Prompts for Vision Model
// ============================================
/**
 * Generate prompt for Kaplan-Meier extraction
 */
function getKaplanMeierPrompt() {
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
function getForestPlotPrompt() {
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
function getWaterfallPlotPrompt() {
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
function validateKaplanMeierData(data) {
    const errors = [];
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
function validateForestPlotData(data) {
    const errors = [];
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
async function imageUrlToBase64(url) {
    // TODO: Fetch image and convert
    throw new Error('Not implemented');
}
/**
 * Estimate confidence based on data completeness
 */
function estimateConfidence(data) {
    let score = 0;
    if (data.chartType !== 'unknown')
        score += 0.2;
    if (data.title)
        score += 0.1;
    if (data.xAxis?.label)
        score += 0.1;
    if (data.yAxis?.label)
        score += 0.1;
    if (data.series.length > 0)
        score += 0.3;
    if (data.series.some(s => s.values.length > 3))
        score += 0.2;
    return Math.min(score, 1);
}
//# sourceMappingURL=graphs.js.map