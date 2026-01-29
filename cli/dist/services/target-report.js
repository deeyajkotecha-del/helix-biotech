"use strict";
/**
 * Target Report Service
 *
 * Generates comprehensive intelligence reports for therapeutic targets,
 * compiling data from trials, publications, and the intelligent asset research engine.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateTargetReport = generateTargetReport;
exports.getTrialAnalytics = getTrialAnalytics;
exports.getPublicationAnalytics = getPublicationAnalytics;
const trials_1 = require("./trials");
const publications_1 = require("./publications");
const asset_research_1 = require("./asset-research");
// ============================================
// Main Report Generation
// ============================================
/**
 * Generate comprehensive target report
 * Uses the intelligent asset research engine for high-quality asset data
 */
async function generateTargetReport(target) {
    console.log(`[Report] Generating report for target: ${target}`);
    const startTime = Date.now();
    // Step 1: Run intelligent asset research (includes trial fetching)
    const assetReport = await (0, asset_research_1.researchTargetAssets)(target);
    console.log(`[Report] Asset research complete: ${assetReport.assets.length} assets`);
    // Step 2: Also fetch all trials for the trials table
    const trials = await fetchTrialsForTarget(target);
    // Step 3: Fetch publications (real PubMed data)
    const publications = await fetchPublicationsForTarget(target);
    // Step 4: Extract KOLs from real publication authors
    const kols = (0, publications_1.extractTopAuthors)(publications, 20);
    console.log(`[Report] Identified ${kols.length} top authors from publications`);
    // Calculate summary statistics
    const activeTrials = trials.filter(t => ['Recruiting', 'Active, not recruiting', 'Enrolling by invitation'].includes(t.status)).length;
    const report = {
        target,
        generatedAt: new Date().toISOString(),
        summary: {
            totalTrials: trials.length,
            activeTrials,
            totalPublications: publications.length,
            totalDeals: 0, // Deals from asset report
            totalKOLs: kols.length,
        },
        trials,
        publications,
        deals: [], // TODO: Extract deals from asset research
        kols,
        assets: assetReport.assets,
        assetStats: assetReport.summary,
        assetReport,
    };
    console.log(`[Report] Generated report in ${Date.now() - startTime}ms`);
    console.log(`[Report] Summary: ${trials.length} trials, ${publications.length} pubs, ${assetReport.assets.length} assets`);
    return report;
}
// ============================================
// Data Fetching Functions
// ============================================
/**
 * Fetch trials related to a target
 */
async function fetchTrialsForTarget(target) {
    try {
        // Search by condition first
        const conditionTrials = await (0, trials_1.searchTrialsByCondition)(target, {
            maxResults: 200,
        });
        // Also search by intervention for drug/molecule targets
        const interventionTrials = await (0, trials_1.searchTrialsByIntervention)(target, {
            maxResults: 100,
        });
        // Deduplicate by NCT ID
        const seen = new Set();
        const allTrials = [];
        for (const trial of [...conditionTrials, ...interventionTrials]) {
            if (!seen.has(trial.nctId)) {
                seen.add(trial.nctId);
                allTrials.push(trial);
            }
        }
        return allTrials;
    }
    catch (error) {
        console.error(`[Report] Error fetching trials: ${error}`);
        return [];
    }
}
/**
 * Fetch publications for target from PubMed
 */
async function fetchPublicationsForTarget(target) {
    try {
        const publications = await (0, publications_1.searchPublications)(target, {
            maxResults: 50,
        });
        return publications;
    }
    catch (error) {
        console.error(`[Report] Error fetching publications: ${error}`);
        return [];
    }
}
// ============================================
// Report Analysis Functions
// ============================================
/**
 * Get trial analytics for a report
 */
function getTrialAnalytics(trials) {
    return {
        phaseBreakdown: (0, trials_1.getPhaseBreakdown)(trials),
        statusBreakdown: (0, trials_1.getStatusBreakdown)(trials),
        topSponsors: (0, trials_1.getTopSponsors)(trials, 10),
        byYear: getTrialsByYear(trials),
    };
}
function getTrialsByYear(trials) {
    const byYear = {};
    for (const trial of trials) {
        if (trial.startDate) {
            const year = trial.startDate.substring(0, 4);
            byYear[year] = (byYear[year] || 0) + 1;
        }
    }
    return byYear;
}
/**
 * Get publication analytics
 */
function getPublicationAnalytics(publications) {
    const byYear = {};
    const byJournal = {};
    for (const pub of publications) {
        if (pub.publicationDate) {
            const year = pub.publicationDate.substring(0, 4);
            byYear[year] = (byYear[year] || 0) + 1;
        }
        const journalName = typeof pub.journal === 'string' ? pub.journal : pub.journal?.name;
        if (journalName) {
            byJournal[journalName] = (byJournal[journalName] || 0) + 1;
        }
    }
    return { byYear, byJournal };
}
//# sourceMappingURL=target-report.js.map