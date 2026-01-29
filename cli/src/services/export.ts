/**
 * Export Service - Investment Ready
 *
 * Generates Excel exports with comprehensive asset data,
 * investment metrics, and regulatory information.
 */

import * as XLSX from 'xlsx';
import { KnownAsset, InvestmentMetrics, calculateInvestmentMetrics } from '../data/known-assets';

// ============================================
// Types
// ============================================

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

// ============================================
// Excel Generation - Investment Ready
// ============================================

/**
 * Generate investment-ready Excel workbook
 */
export function generateExcel(reportData: ReportData): Buffer {
  const workbook = XLSX.utils.book_new();

  // Calculate investment metrics from curated assets
  const curatedAssets = reportData.curatedAssets || [];
  const metrics = curatedAssets.length > 0
    ? calculateInvestmentMetrics(curatedAssets)
    : reportData.investmentMetrics;

  // 1. Investment Summary Sheet (FIRST)
  if (metrics) {
    const investmentSummary = generateInvestmentSummaryData(reportData.target, metrics, curatedAssets);
    const summarySheet = XLSX.utils.aoa_to_sheet(investmentSummary);
    summarySheet['!cols'] = [{ wch: 35 }, { wch: 25 }, { wch: 20 }, { wch: 20 }];
    XLSX.utils.book_append_sheet(workbook, summarySheet, 'Investment Summary');
  }

  // 2. Comprehensive Assets Sheet
  if (curatedAssets.length > 0) {
    const assetsData = generateComprehensiveAssetsData(curatedAssets);
    const assetsSheet = XLSX.utils.json_to_sheet(assetsData);
    assetsSheet['!cols'] = [
      { wch: 30 },  // Drug Name
      { wch: 25 },  // Code Names
      { wch: 12 },  // Target
      { wch: 12 },  // Modality
      { wch: 35 },  // Payload/Tech
      { wch: 25 },  // Owner
      { wch: 20 },  // Partner
      { wch: 15 },  // Owner Type
      { wch: 12 },  // Phase
      { wch: 10 },  // Status
      { wch: 35 },  // Lead Indication
      { wch: 40 },  // Other Indications
      { wch: 5 },   // BTD
      { wch: 5 },   // ODD
      { wch: 6 },   // PRIME
      { wch: 10 },  // Fast Track
      { wch: 35 },  // Deal Headline
      { wch: 25 },  // Deal Upfront
      { wch: 25 },  // Deal Milestones
      { wch: 12 },  // Deal Date
      { wch: 40 },  // Trial IDs
      { wch: 10 },  // Trial Count
      { wch: 50 },  // Key Data
      { wch: 60 },  // Notes
    ];
    XLSX.utils.book_append_sheet(workbook, assetsSheet, 'Assets');
  }

  // 3. Trials Sheet (linked to assets)
  if (reportData.trials.length > 0) {
    const trialsForExport = reportData.trials.map(t => {
      // Find linked asset
      const linkedAsset = curatedAssets.find(a =>
        a.trialIds.includes(t.nctId)
      );

      return {
        'NCT ID': t.nctId,
        'Linked Asset': linkedAsset?.primaryName || '',
        'Title': t.briefTitle,
        'Phase': t.phase,
        'Status': t.status,
        'Sponsor': t.leadSponsor?.name || '',
        'Sponsor Type': t.leadSponsor?.type || '',
        'Conditions': (t.conditions || []).join('; '),
        'Interventions': (t.interventions || []).map((i: any) => i.name).join('; '),
        'Enrollment': t.enrollment?.count || '',
        'Start Date': t.startDate || '',
        'Completion Date': t.completionDate || '',
        'Countries': (t.countries || []).join('; '),
        'Has Results': t.resultsAvailable ? 'Yes' : 'No',
      };
    });
    const trialsSheet = XLSX.utils.json_to_sheet(trialsForExport);
    trialsSheet['!cols'] = [
      { wch: 15 }, { wch: 25 }, { wch: 60 }, { wch: 12 }, { wch: 20 },
      { wch: 30 }, { wch: 12 }, { wch: 40 }, { wch: 40 },
      { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 20 }, { wch: 10 }
    ];
    XLSX.utils.book_append_sheet(workbook, trialsSheet, 'Trials');
  }

  // 4. Publications sheet
  if (reportData.publications.length > 0) {
    const pubsForExport = reportData.publications.map(p => ({
      'PMID': p.pmid || '',
      'Title': p.title,
      'Authors': (p.authors || []).map((a: any) => `${a.lastName} ${a.foreName || ''}`).join('; '),
      'Journal': typeof p.journal === 'object' ? p.journal?.name : p.journal || '',
      'Year': p.publicationDate?.split('-')[0] || '',
      'Type': p.publicationType || '',
      'Abstract': (p.abstract || '').substring(0, 500) + (p.abstract?.length > 500 ? '...' : ''),
    }));
    const pubsSheet = XLSX.utils.json_to_sheet(pubsForExport);
    pubsSheet['!cols'] = [
      { wch: 12 }, { wch: 80 }, { wch: 50 }, { wch: 30 },
      { wch: 6 }, { wch: 15 }, { wch: 100 }
    ];
    XLSX.utils.book_append_sheet(workbook, pubsSheet, 'Publications');
  }

  // 5. Authors/KOLs sheet
  if (reportData.kols.length > 0) {
    const kolsForExport = reportData.kols.map(k => ({
      'Name': k.name || `${k.lastName || ''} ${k.foreName || ''}`.trim(),
      'Institution': k.primaryInstitution || k.institution || '',
      'Publications': k.publicationCount || 0,
      'First Author': k.firstAuthorCount || 0,
      'Last Author': k.lastAuthorCount || 0,
    }));
    const kolsSheet = XLSX.utils.json_to_sheet(kolsForExport);
    kolsSheet['!cols'] = [
      { wch: 30 }, { wch: 50 }, { wch: 12 }, { wch: 12 }, { wch: 12 }
    ];
    XLSX.utils.book_append_sheet(workbook, kolsSheet, 'Authors');
  }

  // Write to buffer
  const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
  return buffer;
}

/**
 * Generate Investment Summary data for Excel
 */
function generateInvestmentSummaryData(
  target: string,
  metrics: InvestmentMetrics,
  assets: KnownAsset[]
): any[][] {
  const data: any[][] = [];

  // Header
  data.push([`${target} Investment Intelligence Report`]);
  data.push([`Generated: ${new Date().toISOString()}`]);
  data.push(['']);

  // Deal Metrics Section
  data.push(['=== DEAL METRICS ===']);
  data.push(['Total Disclosed Deal Value:', `$${metrics.totalDisclosedDealValue.toFixed(1)}B`]);
  data.push(['Total Upfront Payments:', `$${metrics.totalUpfront.toFixed(0)}M`]);
  data.push(['Largest Deal:', `${metrics.largestDeal.name} - ${metrics.largestDeal.value}`]);
  data.push(['']);

  // List all deals
  data.push(['Recent Deals:']);
  for (const asset of assets.filter(a => a.deal)) {
    data.push([
      `  ${asset.primaryName}`,
      asset.deal?.headline || '',
      asset.deal?.date || ''
    ]);
  }
  data.push(['']);

  // Regulatory Section
  data.push(['=== REGULATORY DESIGNATIONS ===']);
  data.push(['Assets with BTD:', metrics.assetsWithBTD]);
  data.push(['Assets with ODD:', metrics.assetsWithODD]);
  data.push(['Assets with PRIME:', metrics.assetsWithPRIME]);
  data.push(['Assets with Fast Track:', metrics.assetsWithFastTrack]);
  data.push(['']);

  // Phase Distribution
  data.push(['=== PHASE DISTRIBUTION ===']);
  const phaseOrder = ['Filed', 'Approved', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Preclinical'];
  for (const phase of phaseOrder) {
    if (metrics.phaseDistribution[phase]) {
      data.push([phase + ':', metrics.phaseDistribution[phase]]);
    }
  }
  data.push(['']);

  // Modality Breakdown
  data.push(['=== MODALITY BREAKDOWN ===']);
  data.push(['Modality', 'Count', 'Deal Value']);
  for (const [modality, info] of Object.entries(metrics.modalityBreakdown)) {
    data.push([
      modality,
      info.count,
      info.dealValue > 0 ? `$${(info.dealValue / 1000).toFixed(1)}B` : '-'
    ]);
  }
  data.push(['']);

  // Ownership Breakdown
  data.push(['=== OWNERSHIP BREAKDOWN ===']);
  for (const [ownerType, count] of Object.entries(metrics.ownershipBreakdown)) {
    data.push([ownerType + ':', count]);
  }
  data.push(['']);

  // Summary
  data.push(['=== SUMMARY ===']);
  data.push(['Total Curated Assets:', metrics.curatedAssets]);
  data.push(['Assets with Deals:', assets.filter(a => a.deal).length]);
  data.push(['Assets with Key Data:', assets.filter(a => a.keyData).length]);

  return data;
}

/**
 * Generate comprehensive assets data for Excel
 */
function generateComprehensiveAssetsData(assets: KnownAsset[]): any[] {
  return assets.map(a => ({
    'Drug Name': a.primaryName,
    'Code Names': a.codeNames.join(', '),
    'Target': a.target,
    'Modality': a.modality,
    'Payload/Tech': a.modalityDetail || a.payload || '',
    'Owner': a.owner,
    'Partner': a.partner || '',
    'Owner Type': a.ownerType,
    'Phase': a.phase,
    'Status': a.status,
    'Lead Indication': a.leadIndication,
    'Other Indications': (a.otherIndications || []).join('; '),
    'BTD': a.regulatory.btd ? 'Y' : '',
    'ODD': a.regulatory.odd ? 'Y' : '',
    'PRIME': a.regulatory.prime ? 'Y' : '',
    'Fast Track': a.regulatory.fastTrack ? 'Y' : '',
    'Deal Headline': a.deal?.headline || '',
    'Deal Upfront': a.deal?.upfront || '',
    'Deal Milestones': a.deal?.milestones || '',
    'Deal Date': a.deal?.date || '',
    'Trial IDs': a.trialIds.join(', '),
    'Trial Count': a.trialIds.length,
    'Key Data': a.keyData || '',
    'Notes': a.notes || '',
  }));
}

// ============================================
// CSV Generation
// ============================================

export function generateCSV(data: any[], filename?: string): string {
  if (data.length === 0) return '';

  const headers = Object.keys(data[0]);
  const rows: string[] = [];
  rows.push(headers.map(h => escapeCSV(h)).join(','));

  for (const item of data) {
    const values = headers.map(h => {
      const val = item[h];
      if (val === null || val === undefined) return '';
      if (Array.isArray(val)) return escapeCSV(val.join('; '));
      if (typeof val === 'object') return escapeCSV(JSON.stringify(val));
      return escapeCSV(String(val));
    });
    rows.push(values.join(','));
  }

  return rows.join('\n');
}

export function generateMultiCSV(reportData: ReportData): Record<string, string> {
  const csvFiles: Record<string, string> = {};

  if (reportData.trials.length > 0) {
    csvFiles['trials.csv'] = generateCSV(reportData.trials.map(t => ({
      nctId: t.nctId,
      title: t.briefTitle,
      phase: t.phase,
      status: t.status,
      sponsor: t.leadSponsor?.name,
      conditions: (t.conditions || []).join('; '),
      startDate: t.startDate,
    })));
  }

  if (reportData.publications.length > 0) {
    csvFiles['publications.csv'] = generateCSV(reportData.publications.map(p => ({
      pmid: p.pmid,
      title: p.title,
      journal: p.journal,
      year: p.publicationDate?.split('-')[0],
    })));
  }

  return csvFiles;
}

// ============================================
// Utility Functions
// ============================================

function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function getContentType(format: 'xlsx' | 'csv'): string {
  return format === 'xlsx'
    ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    : 'text/csv';
}

export function getFileExtension(format: 'xlsx' | 'csv'): string {
  return format;
}
