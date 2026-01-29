/**
 * Target Report Service - Investment Ready
 *
 * Generates comprehensive intelligence reports for therapeutic targets,
 * compiling data from trials, publications, and curated asset database.
 * For uncurated targets, uses AI-powered research with web search.
 */

import { ReportData } from './export';
import {
  searchTrialsByCondition,
  searchTrialsByIntervention,
  getPhaseBreakdown,
  getTopSponsors,
  getStatusBreakdown,
} from './trials';
import { searchPublications, extractTopAuthors } from './publications';
import { Trial, Publication } from '../types/schema';
import {
  KnownAsset,
  InvestmentMetrics,
  getKnownAssetsForTarget,
  calculateInvestmentMetrics,
} from '../data/known-assets';
import { getCachedOrResearch } from './research-cache';
import { convertToKnownAssets, DiscoveredAsset } from './ai-research-agent';

// Data source information for transparency
export interface DataSourceInfo {
  type: 'curated' | 'ai-research' | 'hybrid';
  lastUpdated: string;
  cacheAge?: string;
  fromCache?: boolean;
  assetsDiscovered?: number;
  searchQueries?: string[];
  totalSourcesChecked?: number;
}

// Extended ReportData for investment-ready reports
export interface ExtendedReportData extends ReportData {
  curatedAssets: KnownAsset[];
  investmentMetrics: InvestmentMetrics;
  // Data source tracking
  dataSource: DataSourceInfo;
  // AI-discovered assets (if any)
  discoveredAssets?: DiscoveredAsset[];
  // Legacy fields for backwards compatibility
  assets?: any[];
  assetStats?: any;
  assetReport?: any;
}

// ============================================
// Main Report Generation
// ============================================

/**
 * Generate comprehensive investment-ready target report
 * Uses curated data when available, falls back to AI research for uncurated targets
 */
export async function generateTargetReport(
  target: string,
  options: { forceRefresh?: boolean } = {}
): Promise<ExtendedReportData> {
  console.log(`[Report] Generating investment-ready report for target: ${target}`);
  const startTime = Date.now();

  // Step 1: Get curated assets from database (investment-quality data)
  let curatedAssets = getKnownAssetsForTarget(target);
  console.log(`[Report] Found ${curatedAssets.length} curated assets`);

  // Step 2: If no curated data, use AI research agent
  let dataSource: DataSourceInfo;
  let discoveredAssets: DiscoveredAsset[] | undefined;

  if (curatedAssets.length === 0) {
    console.log(`[Report] No curated data for ${target}, using AI research agent...`);

    try {
      const researchResult = await getCachedOrResearch(target, {
        forceRefresh: options.forceRefresh,
      });

      discoveredAssets = researchResult.assets;
      curatedAssets = convertToKnownAssets(researchResult.assets);

      console.log(`[Report] AI research found ${researchResult.assets.length} assets`);

      dataSource = {
        type: 'ai-research',
        lastUpdated: researchResult.researchedAt,
        fromCache: researchResult.fromCache,
        cacheAge: researchResult.cacheAge,
        assetsDiscovered: researchResult.assets.length,
        searchQueries: researchResult.searchQueries,
        totalSourcesChecked: researchResult.totalSourcesChecked,
      };
    } catch (error) {
      console.error(`[Report] AI research failed: ${error}`);
      // Continue with empty assets - trials and publications may still be valuable
      dataSource = {
        type: 'ai-research',
        lastUpdated: new Date().toISOString(),
        assetsDiscovered: 0,
      };
    }
  } else {
    dataSource = {
      type: 'curated',
      lastUpdated: '2026-01-29', // Update this with actual curation date
    };
  }

  // Step 3: Calculate investment metrics
  const investmentMetrics = calculateInvestmentMetrics(curatedAssets);
  if (investmentMetrics.totalCommitted > 0) {
    console.log(`[Report] Committed: $${(investmentMetrics.totalCommitted / 1000).toFixed(1)}B, Potential: $${(investmentMetrics.totalPotential / 1000).toFixed(1)}B across ${investmentMetrics.assetsWithDeals} deals`);
  }

  // Step 4: Fetch all trials for the trials table
  const trials = await fetchTrialsForTarget(target);

  // Step 5: Fetch publications (real PubMed data)
  const publications = await fetchPublicationsForTarget(target);

  // Step 6: Extract KOLs from real publication authors
  const kols = extractTopAuthors(publications, 20);
  console.log(`[Report] Identified ${kols.length} top authors from publications`);

  // Calculate summary statistics
  const activeTrials = trials.filter(t =>
    ['Recruiting', 'Active, not recruiting', 'Enrolling by invitation'].includes(t.status)
  ).length;

  const report: ExtendedReportData = {
    target,
    generatedAt: new Date().toISOString(),
    summary: {
      totalTrials: trials.length,
      activeTrials,
      totalPublications: publications.length,
      totalDeals: curatedAssets.filter(a => a.deal).length,
      totalKOLs: kols.length,
    },
    trials,
    publications,
    deals: curatedAssets.filter(a => a.deal).map(a => ({
      asset: a.primaryName,
      headline: a.deal?.headline,
      upfront: a.deal?.upfront || 0,
      equity: a.deal?.equity || 0,
      committed: a.deal?.committed || 0,
      milestones: a.deal?.milestones || 0,
      totalPotential: a.deal?.totalPotential || 0,
      date: a.deal?.date,
      partner: a.deal?.partner,
      hasBreakdown: a.deal?.hasBreakdown || false,
    })),
    kols,
    curatedAssets,
    investmentMetrics,
    dataSource,
    discoveredAssets,
  };

  console.log(`[Report] Generated report in ${Date.now() - startTime}ms`);
  console.log(`[Report] Summary: ${curatedAssets.length} assets (${dataSource.type}), ${trials.length} trials, ${publications.length} pubs`);

  return report;
}

// ============================================
// Data Fetching Functions
// ============================================

/**
 * Fetch trials related to a target
 */
async function fetchTrialsForTarget(target: string): Promise<Trial[]> {
  try {
    // Search by condition first
    const conditionTrials = await searchTrialsByCondition(target, {
      maxResults: 200,
    });

    // Also search by intervention for drug/molecule targets
    const interventionTrials = await searchTrialsByIntervention(target, {
      maxResults: 100,
    });

    // Deduplicate by NCT ID
    const seen = new Set<string>();
    const allTrials: Trial[] = [];

    for (const trial of [...conditionTrials, ...interventionTrials]) {
      if (!seen.has(trial.nctId)) {
        seen.add(trial.nctId);
        allTrials.push(trial);
      }
    }

    return allTrials;
  } catch (error) {
    console.error(`[Report] Error fetching trials: ${error}`);
    return [];
  }
}

/**
 * Fetch publications for target from PubMed
 */
async function fetchPublicationsForTarget(target: string): Promise<Publication[]> {
  try {
    const publications = await searchPublications(target, {
      maxResults: 50,
    });
    return publications;
  } catch (error) {
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
export function getTrialAnalytics(trials: Trial[]) {
  return {
    phaseBreakdown: getPhaseBreakdown(trials),
    statusBreakdown: getStatusBreakdown(trials),
    topSponsors: getTopSponsors(trials, 10),
    byYear: getTrialsByYear(trials),
  };
}

function getTrialsByYear(trials: Trial[]): Record<string, number> {
  const byYear: Record<string, number> = {};
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
export function getPublicationAnalytics(publications: Publication[]) {
  const byYear: Record<string, number> = {};
  const byJournal: Record<string, number> = {};

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
