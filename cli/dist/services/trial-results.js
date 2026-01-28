"use strict";
/**
 * Trial Results Service
 *
 * Extracts and processes clinical trial results from ClinicalTrials.gov.
 * Parses efficacy endpoints, statistical analyses, and safety data.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getFullTrialData = getFullTrialData;
exports.getTrialResults = getTrialResults;
exports.getSafetyData = getSafetyData;
exports.getBatchTrialResults = getBatchTrialResults;
exports.extractPrimaryEndpointSummary = extractPrimaryEndpointSummary;
exports.compareArmEfficacy = compareArmEfficacy;
exports.extractPValues = extractPValues;
exports.getSafetySummary = getSafetySummary;
exports.isSignificant = isSignificant;
exports.parseCI = parseCI;
exports.normalizeEndpointName = normalizeEndpointName;
exports.compareTrials = compareTrials;
const CLINICALTRIALS_API = 'https://clinicaltrials.gov/api/v2/studies';
const REQUEST_DELAY_MS = 500;
// ============================================
// Main Functions
// ============================================
/**
 * Get comprehensive trial data with results
 * This is the main function for the /api/trial/:nctId/results endpoint
 */
async function getFullTrialData(nctId) {
    console.log(`[Results] Fetching full data for ${nctId}...`);
    try {
        // Request all relevant fields
        const url = `${CLINICALTRIALS_API}/${nctId}?format=json`;
        const response = await fetch(url, {
            headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
        });
        if (!response.ok) {
            console.log(`[Results] API returned ${response.status} for ${nctId}`);
            return null;
        }
        const data = await response.json();
        // Extract protocol section
        const protocol = data.protocolSection || {};
        const identification = protocol.identificationModule || {};
        const status = protocol.statusModule || {};
        const sponsor = protocol.sponsorCollaboratorsModule || {};
        const design = protocol.designModule || {};
        const arms = protocol.armsInterventionsModule || {};
        // Extract results section
        const resultsSection = data.resultsSection || {};
        const hasResults = data.hasResults === true;
        // Build trial info
        const trialData = {
            nctId: identification.nctId || nctId,
            title: identification.briefTitle || '',
            officialTitle: identification.officialTitle,
            phase: normalizePhaseFromApi(design.phases?.[0] || 'N/A'),
            status: status.overallStatus || 'Unknown',
            sponsor: sponsor.leadSponsor?.name || 'Unknown',
            sponsorClass: sponsor.leadSponsor?.class,
            collaborators: sponsor.collaborators?.map((c) => c.name),
            startDate: status.startDateStruct?.date,
            completionDate: status.completionDateStruct?.date,
            enrollment: parseInt(design.enrollmentInfo?.count || '0', 10),
            enrollmentType: design.enrollmentInfo?.type,
            arms: parseArmsFromProtocol(arms.armGroups || [], arms.interventions || []),
            studyType: design.studyType,
            allocation: design.designInfo?.allocation,
            interventionModel: design.designInfo?.interventionModel,
            primaryPurpose: design.designInfo?.primaryPurpose,
            masking: design.designInfo?.maskingInfo?.masking,
            hasResults,
            resultsFirstPosted: status.resultsFirstPostDateStruct?.date,
            primaryOutcomes: [],
            secondaryOutcomes: [],
            fetchedAt: new Date().toISOString(),
        };
        // Parse results if available
        if (hasResults) {
            const participantFlow = resultsSection.participantFlowModule;
            const outcomes = resultsSection.outcomeMeasuresModule;
            const aeModule = resultsSection.adverseEventsModule;
            // Get arm counts from participant flow
            const armCounts = getArmCountsFromFlow(participantFlow);
            // Update arm N values
            for (const arm of trialData.arms) {
                arm.n = armCounts[arm.id] || undefined;
            }
            // Parse outcomes
            const outcomeGroups = outcomes?.outcomeMeasures?.[0]?.groups ||
                participantFlow?.groups || [];
            const primaryRaw = outcomes?.outcomeMeasures?.filter((o) => o.type === 'PRIMARY') || [];
            const secondaryRaw = outcomes?.outcomeMeasures?.filter((o) => o.type === 'SECONDARY') || [];
            trialData.primaryOutcomes = formatOutcomesForDisplay(primaryRaw, outcomeGroups);
            trialData.secondaryOutcomes = formatOutcomesForDisplay(secondaryRaw, outcomeGroups);
            // Parse safety
            if (aeModule) {
                trialData.safety = formatSafetyForDisplay(aeModule);
            }
        }
        return trialData;
    }
    catch (error) {
        console.log(`[Results] Error fetching data for ${nctId}: ${error}`);
        return null;
    }
}
/**
 * Get full results for a trial (original function, kept for compatibility)
 */
async function getTrialResults(nctId) {
    console.log(`[Results] Fetching results for ${nctId}...`);
    try {
        const url = `${CLINICALTRIALS_API}/${nctId}?format=json`;
        const response = await fetch(url, {
            headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
        });
        if (!response.ok) {
            console.log(`[Results] API returned ${response.status} for ${nctId}`);
            return null;
        }
        const data = await response.json();
        if (!data.hasResults) {
            console.log(`[Results] No results available for ${nctId}`);
            return null;
        }
        const resultsSection = data.resultsSection;
        if (!resultsSection) {
            return null;
        }
        return parseResultsSection(nctId, resultsSection);
    }
    catch (error) {
        console.log(`[Results] Error fetching results for ${nctId}: ${error}`);
        return null;
    }
}
/**
 * Get safety data for a trial
 */
async function getSafetyData(nctId) {
    console.log(`[Results] Fetching safety data for ${nctId}...`);
    try {
        const url = `${CLINICALTRIALS_API}/${nctId}?format=json`;
        const response = await fetch(url, {
            headers: { 'User-Agent': 'Helix/1.0 (biotech-intelligence-platform)' }
        });
        if (!response.ok)
            return null;
        const data = await response.json();
        if (!data.hasResults)
            return null;
        const resultsSection = data.resultsSection;
        const aeModule = resultsSection?.adverseEventsModule;
        if (!aeModule)
            return null;
        return parseAdverseEventsModule(nctId, aeModule);
    }
    catch (error) {
        console.log(`[Results] Error fetching safety data for ${nctId}: ${error}`);
        return null;
    }
}
/**
 * Get results for multiple trials (batch)
 */
async function getBatchTrialResults(nctIds) {
    const results = new Map();
    for (const nctId of nctIds) {
        const result = await getTrialResults(nctId);
        if (result) {
            results.set(nctId, result);
        }
        await sleep(REQUEST_DELAY_MS);
    }
    console.log(`[Results] Fetched results for ${results.size}/${nctIds.length} trials`);
    return results;
}
// ============================================
// Parsing Functions
// ============================================
/**
 * Parse results section from API response
 */
function parseResultsSection(nctId, resultsSection) {
    const participantFlow = resultsSection.participantFlowModule;
    const baseline = resultsSection.baselineCharacteristicsModule;
    const outcomes = resultsSection.outcomeMeasuresModule;
    const moreInfo = resultsSection.moreInfoModule;
    // Parse groups (arms)
    const groups = parseParticipantGroups(participantFlow?.groups || baseline?.groups || outcomes?.outcomeMeasures?.[0]?.groups || []);
    // Parse primary outcomes
    const primaryOutcomes = parseOutcomes(outcomes?.outcomeMeasures?.filter((o) => o.type === 'PRIMARY') || [], groups);
    // Parse secondary outcomes
    const secondaryOutcomes = parseOutcomes(outcomes?.outcomeMeasures?.filter((o) => o.type === 'SECONDARY') || [], groups);
    return {
        nctId,
        participantFlow: participantFlow ? {
            recruitmentDetails: participantFlow.recruitmentDetails,
            preAssignmentDetails: participantFlow.preAssignmentDetails,
            groups,
            periods: parseFlowPeriods(participantFlow.periods || []),
        } : undefined,
        baselineCharacteristics: baseline ? {
            groups,
            measures: parseBaselineMeasures(baseline.measures || []),
        } : undefined,
        primaryOutcomes,
        secondaryOutcomes,
        pointOfContactOrg: moreInfo?.pointOfContact?.organization,
        limitations: moreInfo?.limitations,
        fetchedAt: new Date().toISOString(),
    };
}
/**
 * Parse participant groups
 */
function parseParticipantGroups(groups) {
    return groups.map((g) => ({
        id: g.id || '',
        title: g.title || '',
        description: g.description,
    }));
}
/**
 * Parse flow periods (enrollment flow)
 */
function parseFlowPeriods(periods) {
    return periods.map((p) => ({
        title: p.title || '',
        milestones: (p.milestones || []).map((m) => ({
            type: m.type,
            counts: (m.achievements || []).map((a) => ({
                groupId: a.groupId,
                count: parseInt(a.numSubjects || '0', 10),
            })),
        })),
    }));
}
/**
 * Parse baseline measures
 */
function parseBaselineMeasures(measures) {
    return measures.map((m) => ({
        title: m.title || '',
        description: m.description,
        units: m.unitOfMeasure,
        param: normalizeParam(m.paramType),
        dispersion: normalizeDispersion(m.dispersionType),
        classes: (m.classes || [{ categories: m.categories || [] }]).map((c) => ({
            title: c.title,
            categories: (c.categories || []).map((cat) => ({
                title: cat.title,
                measurements: (cat.measurements || []).map((meas) => ({
                    groupId: meas.groupId,
                    value: meas.value,
                    spread: meas.spread,
                    lowerLimit: meas.lowerLimit,
                    upperLimit: meas.upperLimit,
                })),
            })),
        })),
    }));
}
/**
 * Parse outcome measures
 */
function parseOutcomes(outcomes, groups) {
    return outcomes.map((o) => ({
        title: o.title || '',
        description: o.description,
        timeFrame: o.timeFrame,
        type: o.type,
        populationDescription: o.populationDescription,
        reportingStatus: o.reportingStatus === 'POSTED' ? 'Posted' : 'Not Posted',
        groups,
        measures: parseOutcomeMeasures(o.classes || [{ categories: [{ measurements: o.denoms || [] }] }], o),
        analyses: parseOutcomeAnalyses(o.analyses || []),
    }));
}
/**
 * Parse outcome measure details
 */
function parseOutcomeMeasures(classes, outcome) {
    // Handle the nested structure
    const measures = [];
    const baseMeasure = {
        title: outcome.title || '',
        description: outcome.description,
        units: outcome.unitOfMeasure,
        param: normalizeParam(outcome.paramType),
        dispersion: normalizeDispersion(outcome.dispersionType),
        classes: classes.map((c) => ({
            title: c.title,
            categories: (c.categories || []).map((cat) => ({
                title: cat.title,
                measurements: (cat.measurements || []).map((m) => ({
                    groupId: m.groupId,
                    value: m.value,
                    spread: m.spread,
                    lowerLimit: m.lowerLimit,
                    upperLimit: m.upperLimit,
                    comment: m.comment,
                })),
            })),
        })),
    };
    measures.push(baseMeasure);
    return measures;
}
/**
 * Parse statistical analyses
 */
function parseOutcomeAnalyses(analyses) {
    return analyses.map((a) => ({
        groupIds: a.groupIds || [],
        groupDescription: a.groupDescription,
        nonInferiorityType: a.nonInferiorityType,
        pValue: a.pValue,
        pValueComment: a.pValueComment,
        statisticalMethod: a.statisticalMethod,
        statisticalComment: a.statisticalComment,
        paramType: a.paramType,
        paramValue: a.paramValue,
        ciPctValue: a.ciPctValue,
        ciNumSides: a.ciNumSides,
        ciLowerLimit: a.ciLowerLimit,
        ciUpperLimit: a.ciUpperLimit,
        estimateComment: a.estimateComment,
    }));
}
/**
 * Parse adverse events module
 */
function parseAdverseEventsModule(nctId, aeModule) {
    const eventGroups = aeModule.eventGroups || [];
    const seriousEvents = aeModule.seriousEvents || [];
    const otherEvents = aeModule.otherEvents || [];
    // Parse groups
    const groups = eventGroups.map((g) => ({
        id: g.id || '',
        title: g.title || '',
        description: g.description,
    }));
    return {
        nctId,
        timeFrame: aeModule.timeFrame || '',
        description: aeModule.description,
        groups,
        seriousEvents: parseAdverseEvents(seriousEvents, eventGroups),
        otherEvents: parseAdverseEvents(otherEvents, eventGroups),
        totals: eventGroups.map((g) => ({
            groupId: g.id,
            seriousNumAffected: parseInt(g.seriousNumAffected || '0', 10),
            seriousNumAtRisk: parseInt(g.seriousNumAtRisk || '0', 10),
            otherNumAffected: parseInt(g.otherNumAffected || '0', 10),
            otherNumAtRisk: parseInt(g.otherNumAtRisk || '0', 10),
        })),
        fetchedAt: new Date().toISOString(),
    };
}
/**
 * Parse adverse event list
 */
function parseAdverseEvents(events, groups) {
    return events.map((e) => ({
        term: e.term || '',
        organSystem: e.organSystem,
        sourceVocabulary: e.sourceVocabulary,
        assessmentType: e.assessmentType,
        stats: (e.stats || []).map((s) => ({
            groupId: s.groupId,
            numEvents: s.numEvents ? parseInt(s.numEvents, 10) : undefined,
            numAffected: parseInt(s.numAffected || '0', 10),
            numAtRisk: parseInt(s.numAtRisk || '0', 10),
        })),
    }));
}
// ============================================
// Analysis Functions
// ============================================
/**
 * Extract primary endpoint results summary
 */
function extractPrimaryEndpointSummary(results) {
    const summaries = [];
    for (const outcome of results.primaryOutcomes) {
        const arms = [];
        for (const measure of outcome.measures) {
            for (const cls of measure.classes) {
                for (const cat of cls.categories) {
                    for (const m of cat.measurements) {
                        const group = outcome.groups.find(g => g.id === m.groupId);
                        arms.push({
                            name: group?.title || m.groupId,
                            value: formatMeasurement(m, measure),
                            n: 0, // Would need to get from participant flow
                        });
                    }
                }
            }
        }
        // Get p-value from analyses
        const analysis = outcome.analyses?.[0];
        const pValue = analysis?.pValue;
        const significant = pValue ? isSignificant(pValue) : undefined;
        summaries.push({
            endpoint: outcome.title,
            arms,
            pValue,
            significant,
        });
    }
    return summaries;
}
/**
 * Compare efficacy across arms for a specific endpoint
 */
function compareArmEfficacy(results, endpointTitle) {
    // Find the outcome matching the title
    const outcome = [...results.primaryOutcomes, ...(results.secondaryOutcomes || [])]
        .find(o => normalizeEndpointName(o.title).includes(normalizeEndpointName(endpointTitle)));
    if (!outcome)
        return null;
    const arms = [];
    for (const measure of outcome.measures) {
        for (const cls of measure.classes) {
            for (const cat of cls.categories) {
                for (const m of cat.measurements) {
                    const group = outcome.groups.find(g => g.id === m.groupId);
                    const value = parseFloat(m.value || '0');
                    const ci = m.lowerLimit && m.upperLimit
                        ? [parseFloat(m.lowerLimit), parseFloat(m.upperLimit)]
                        : undefined;
                    arms.push({
                        id: m.groupId,
                        title: group?.title || m.groupId,
                        value,
                        ci,
                    });
                }
            }
        }
    }
    // Get comparison from first analysis
    const analysis = outcome.analyses?.[0];
    let comparison;
    if (analysis && arms.length >= 2) {
        comparison = {
            difference: arms[0].value - arms[1].value,
            pValue: analysis.pValue || '',
            significant: isSignificant(analysis.pValue || ''),
        };
    }
    return { arms, comparison };
}
/**
 * Extract all p-values from a trial's results
 */
function extractPValues(results) {
    const pValues = [];
    const allOutcomes = [...results.primaryOutcomes, ...(results.secondaryOutcomes || [])];
    for (const outcome of allOutcomes) {
        for (const analysis of outcome.analyses || []) {
            if (analysis.pValue) {
                pValues.push({
                    endpoint: outcome.title,
                    comparison: analysis.groupDescription || analysis.groupIds.join(' vs '),
                    pValue: analysis.pValue,
                    significant: isSignificant(analysis.pValue),
                });
            }
        }
    }
    return pValues;
}
/**
 * Get safety summary from adverse events
 */
function getSafetySummary(safety) {
    // Calculate totals
    let totalSerious = 0;
    let totalOther = 0;
    for (const total of safety.totals || []) {
        totalSerious += total.seriousNumAffected;
        totalOther += total.otherNumAffected;
    }
    // Get top events by rate
    const seriousRates = safety.seriousEvents.map(e => {
        const totalAffected = e.stats.reduce((sum, s) => sum + s.numAffected, 0);
        const totalAtRisk = e.stats.reduce((sum, s) => sum + s.numAtRisk, 0);
        return {
            term: e.term,
            rate: totalAtRisk > 0 ? totalAffected / totalAtRisk : 0,
        };
    }).sort((a, b) => b.rate - a.rate);
    const otherRates = safety.otherEvents.map(e => {
        const totalAffected = e.stats.reduce((sum, s) => sum + s.numAffected, 0);
        const totalAtRisk = e.stats.reduce((sum, s) => sum + s.numAtRisk, 0);
        return {
            term: e.term,
            rate: totalAtRisk > 0 ? totalAffected / totalAtRisk : 0,
        };
    }).sort((a, b) => b.rate - a.rate);
    return {
        totalSeriousEvents: totalSerious,
        totalOtherEvents: totalOther,
        topSeriousEvents: seriousRates.slice(0, 10),
        topOtherEvents: otherRates.slice(0, 10),
    };
}
// ============================================
// Utility Functions
// ============================================
function normalizeParam(param) {
    if (!param)
        return 'Number';
    const p = param.toLowerCase();
    if (p.includes('count'))
        return 'Count';
    if (p.includes('mean') && p.includes('least'))
        return 'Least Squares Mean';
    if (p.includes('geometric'))
        return 'Geometric Mean';
    if (p.includes('mean'))
        return 'Mean';
    if (p.includes('median'))
        return 'Median';
    if (p.includes('log'))
        return 'Log Mean';
    return 'Number';
}
function normalizeDispersion(dispersion) {
    if (!dispersion)
        return undefined;
    const d = dispersion.toLowerCase();
    if (d.includes('standard deviation') || d === 'sd')
        return 'Standard Deviation';
    if (d.includes('standard error') || d === 'se')
        return 'Standard Error';
    if (d.includes('confidence') || d.includes('ci'))
        return '95% Confidence Interval';
    if (d.includes('inter-quartile') || d.includes('iqr'))
        return 'Inter-Quartile Range';
    if (d.includes('range'))
        return 'Full Range';
    return undefined;
}
function formatMeasurement(m, measure) {
    let result = m.value || '';
    if (m.spread) {
        const dispType = measure.dispersion || 'SD';
        result += ` (${dispType}: ${m.spread})`;
    }
    if (m.lowerLimit && m.upperLimit) {
        result += ` [${m.lowerLimit}, ${m.upperLimit}]`;
    }
    return result;
}
/**
 * Determine if p-value is statistically significant
 */
function isSignificant(pValue, threshold = 0.05) {
    const cleaned = pValue.toLowerCase().replace('p', '').replace('=', '').trim();
    if (cleaned === 'ns' || cleaned.includes('not significant'))
        return false;
    if (cleaned.startsWith('<')) {
        const num = parseFloat(cleaned.substring(1));
        return !isNaN(num) && num <= threshold;
    }
    const num = parseFloat(cleaned);
    return !isNaN(num) && num <= threshold;
}
/**
 * Parse confidence interval string
 */
function parseCI(ciString) {
    const match = ciString.match(/[\(\[]?\s*([\d.-]+)\s*[,\-to]+\s*([\d.-]+)\s*[\)\]]?/i);
    if (!match)
        return null;
    return [parseFloat(match[1]), parseFloat(match[2])];
}
/**
 * Normalize endpoint name for matching
 */
function normalizeEndpointName(name) {
    return name
        .toLowerCase()
        .replace(/[^\w\s]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
// ============================================
// Formatting Functions for Full Trial Data
// ============================================
/**
 * Parse arms from protocol section
 */
function parseArmsFromProtocol(armGroups, interventions) {
    return armGroups.map((arm, index) => {
        // Find matching intervention
        const intervention = interventions.find((i) => i.armGroupLabels?.includes(arm.label));
        return {
            id: `A${index + 1}`,
            title: arm.label || `Arm ${index + 1}`,
            description: arm.description,
            type: arm.type,
            intervention: intervention?.name || arm.interventionNames?.[0],
        };
    });
}
/**
 * Get arm participant counts from participant flow
 */
function getArmCountsFromFlow(participantFlow) {
    const counts = {};
    if (!participantFlow?.periods)
        return counts;
    // Look for "Started" milestone in first period
    const firstPeriod = participantFlow.periods[0];
    if (!firstPeriod?.milestones)
        return counts;
    const startedMilestone = firstPeriod.milestones.find((m) => m.type === 'STARTED');
    if (startedMilestone?.achievements) {
        for (const achievement of startedMilestone.achievements) {
            counts[achievement.groupId] = parseInt(achievement.numSubjects || '0', 10);
        }
    }
    return counts;
}
/**
 * Format outcomes for display
 */
function formatOutcomesForDisplay(outcomes, groups) {
    const formatted = [];
    for (const outcome of outcomes) {
        const formattedOutcome = {
            title: outcome.title || '',
            description: outcome.description,
            timeFrame: outcome.timeFrame,
            type: outcome.type || 'PRIMARY',
            units: outcome.unitOfMeasure,
            paramType: outcome.paramType,
            results: [],
        };
        // Get group info
        const outcomeGroups = outcome.groups || groups;
        const groupMap = new Map(outcomeGroups.map((g) => [g.id, g.title]));
        // Parse measurements from classes/categories structure
        const classes = outcome.classes || [];
        for (const cls of classes) {
            const categories = cls.categories || [];
            for (const cat of categories) {
                const measurements = cat.measurements || [];
                for (const m of measurements) {
                    formattedOutcome.results.push({
                        armId: m.groupId,
                        armTitle: groupMap.get(m.groupId) || m.groupId,
                        value: m.value || '',
                        spread: m.spread,
                        ci: m.lowerLimit && m.upperLimit
                            ? { lower: m.lowerLimit, upper: m.upperLimit }
                            : undefined,
                    });
                }
            }
        }
        // Parse analysis if available
        if (outcome.analyses?.length > 0) {
            const analysis = outcome.analyses[0];
            formattedOutcome.analysis = {
                method: analysis.statisticalMethod,
                pValue: analysis.pValue,
                pValueSignificant: analysis.pValue ? isSignificant(analysis.pValue) : undefined,
                estimateType: analysis.paramType,
                estimateValue: analysis.paramValue,
                ci: analysis.ciLowerLimit && analysis.ciUpperLimit
                    ? {
                        lower: analysis.ciLowerLimit,
                        upper: analysis.ciUpperLimit,
                        pct: parseInt(analysis.ciPctValue || '95', 10),
                    }
                    : undefined,
                description: analysis.groupDescription,
            };
        }
        formatted.push(formattedOutcome);
    }
    return formatted;
}
/**
 * Format safety data for display
 */
function formatSafetyForDisplay(aeModule) {
    const eventGroups = aeModule.eventGroups || [];
    const seriousEvents = aeModule.seriousEvents || [];
    const otherEvents = aeModule.otherEvents || [];
    // Build arm info
    const arms = eventGroups.map((g) => ({
        id: g.id || '',
        title: g.title || '',
        seriousNumAffected: parseInt(g.seriousNumAffected || '0', 10),
        seriousNumAtRisk: parseInt(g.seriousNumAtRisk || '0', 10),
        otherNumAffected: parseInt(g.otherNumAffected || '0', 10),
        otherNumAtRisk: parseInt(g.otherNumAtRisk || '0', 10),
    }));
    const groupMap = new Map(eventGroups.map((g) => [g.id, g.title]));
    return {
        timeFrame: aeModule.timeFrame,
        description: aeModule.description,
        arms,
        seriousEvents: formatAEList(seriousEvents, groupMap),
        otherEvents: formatAEList(otherEvents, groupMap),
    };
}
/**
 * Format adverse event list
 */
function formatAEList(events, groupMap) {
    return events.map((e) => {
        const byArm = (e.stats || []).map((s) => {
            const numAffected = parseInt(s.numAffected || '0', 10);
            const numAtRisk = parseInt(s.numAtRisk || '0', 10);
            return {
                armId: s.groupId,
                armTitle: groupMap.get(s.groupId) || s.groupId,
                numAffected,
                numAtRisk,
                rate: numAtRisk > 0 ? (numAffected / numAtRisk) * 100 : 0,
                numEvents: s.numEvents ? parseInt(s.numEvents, 10) : undefined,
            };
        });
        const totalAffected = byArm.reduce((sum, a) => sum + a.numAffected, 0);
        const totalAtRisk = byArm.reduce((sum, a) => sum + a.numAtRisk, 0);
        return {
            term: e.term || '',
            organSystem: e.organSystem,
            sourceVocabulary: e.sourceVocabulary,
            byArm,
            totalAffected,
            totalAtRisk,
            overallRate: totalAtRisk > 0 ? (totalAffected / totalAtRisk) * 100 : 0,
        };
    }).sort((a, b) => b.overallRate - a.overallRate); // Sort by frequency
}
/**
 * Normalize phase from API format
 */
function normalizePhaseFromApi(phase) {
    if (!phase)
        return 'N/A';
    const p = phase.toUpperCase();
    if (p === 'NA')
        return 'N/A';
    if (p === 'EARLY_PHASE1')
        return 'Early Phase 1';
    if (p === 'PHASE1')
        return 'Phase 1';
    if (p === 'PHASE2')
        return 'Phase 2';
    if (p === 'PHASE3')
        return 'Phase 3';
    if (p === 'PHASE4')
        return 'Phase 4';
    return phase;
}
// ============================================
// Comparison Functions
// ============================================
/**
 * Compare multiple trials side by side
 */
async function compareTrials(nctIds) {
    // Fetch all trial data
    const trials = [];
    for (const nctId of nctIds) {
        const data = await getFullTrialData(nctId);
        if (data) {
            trials.push(data);
        }
        await sleep(REQUEST_DELAY_MS);
    }
    if (trials.length === 0) {
        return {
            trials: [],
            comparison: {
                populations: [],
                primaryEndpoints: [],
                safetyHighlights: [],
                endpointDifferences: [],
            },
        };
    }
    // Compare populations
    const populations = trials.map(t => ({
        nctId: t.nctId,
        enrollment: t.enrollment,
        arms: t.arms.map(a => `${a.title} (N=${a.n || '?'})`),
    }));
    // Collect all primary endpoints
    const endpointMap = new Map();
    for (const trial of trials) {
        for (const outcome of trial.primaryOutcomes) {
            const normalizedTitle = normalizeEndpointName(outcome.title);
            // Get the treatment arm result (first non-placebo arm)
            const treatmentResult = outcome.results.find(r => !r.armTitle.toLowerCase().includes('placebo') &&
                !r.armTitle.toLowerCase().includes('control'));
            if (!endpointMap.has(normalizedTitle)) {
                endpointMap.set(normalizedTitle, []);
            }
            endpointMap.get(normalizedTitle).push({
                nctId: trial.nctId,
                value: treatmentResult
                    ? `${treatmentResult.value}${outcome.units ? ' ' + outcome.units : ''}`
                    : 'N/A',
                pValue: outcome.analysis?.pValue,
                significant: outcome.analysis?.pValueSignificant,
            });
        }
    }
    const primaryEndpoints = Array.from(endpointMap.entries()).map(([endpoint, byTrial]) => ({
        endpoint,
        byTrial,
    }));
    // Compare safety - find common AEs
    const aeMap = new Map();
    for (const trial of trials) {
        if (!trial.safety)
            continue;
        // Combine serious and other events, take top 20
        const allEvents = [...trial.safety.seriousEvents, ...trial.safety.otherEvents]
            .sort((a, b) => b.overallRate - a.overallRate)
            .slice(0, 20);
        for (const event of allEvents) {
            const normalizedTerm = event.term.toLowerCase();
            if (!aeMap.has(normalizedTerm)) {
                aeMap.set(normalizedTerm, []);
            }
            aeMap.get(normalizedTerm).push({
                nctId: trial.nctId,
                rate: event.overallRate,
            });
        }
    }
    // Only include AEs that appear in multiple trials
    const safetyHighlights = Array.from(aeMap.entries())
        .filter(([_, byTrial]) => byTrial.length > 1)
        .map(([event, byTrial]) => ({ event, byTrial }))
        .sort((a, b) => {
        const avgA = a.byTrial.reduce((sum, t) => sum + t.rate, 0) / a.byTrial.length;
        const avgB = b.byTrial.reduce((sum, t) => sum + t.rate, 0) / b.byTrial.length;
        return avgB - avgA;
    })
        .slice(0, 15);
    // Note endpoint differences
    const endpointDifferences = [];
    for (const [endpoint, byTrial] of endpointMap.entries()) {
        if (byTrial.length !== trials.length) {
            const missingTrials = trials
                .filter(t => !byTrial.find(bt => bt.nctId === t.nctId))
                .map(t => t.nctId);
            endpointDifferences.push(`"${endpoint}" not measured in: ${missingTrials.join(', ')}`);
        }
    }
    return {
        trials,
        comparison: {
            populations,
            primaryEndpoints,
            safetyHighlights,
            endpointDifferences,
        },
    };
}
//# sourceMappingURL=trial-results.js.map