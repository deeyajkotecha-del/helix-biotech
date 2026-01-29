/**
 * Export Service
 *
 * Generates Excel and CSV exports for Helix reports.
 * Supports multi-tab workbooks and single-file CSV exports.
 */

import * as XLSX from 'xlsx';

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
}

// ============================================
// Excel Generation
// ============================================

/**
 * Generate multi-tab Excel workbook from report data
 */
export function generateExcel(reportData: ReportData): Buffer {
  const workbook = XLSX.utils.book_new();

  // Summary sheet
  const summaryData = [
    ['Helix Intelligence Report'],
    ['Target:', reportData.target],
    ['Generated:', reportData.generatedAt],
    [''],
    ['Summary Statistics'],
    ['Total Trials:', reportData.summary.totalTrials],
    ['Active Trials:', reportData.summary.activeTrials],
    ['Publications:', reportData.summary.totalPublications],
    ['Deals:', reportData.summary.totalDeals],
    ['KOLs Identified:', reportData.summary.totalKOLs],
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  summarySheet['!cols'] = [{ wch: 20 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');

  // Trials sheet
  if (reportData.trials.length > 0) {
    const trialsForExport = reportData.trials.map(t => ({
      'NCT ID': t.nctId,
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
    }));
    const trialsSheet = XLSX.utils.json_to_sheet(trialsForExport);
    trialsSheet['!cols'] = [
      { wch: 15 }, { wch: 60 }, { wch: 12 }, { wch: 20 },
      { wch: 30 }, { wch: 12 }, { wch: 40 }, { wch: 40 },
      { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 20 }, { wch: 10 }
    ];
    XLSX.utils.book_append_sheet(workbook, trialsSheet, 'Trials');
  }

  // Publications sheet
  if (reportData.publications.length > 0) {
    const pubsForExport = reportData.publications.map(p => ({
      'PMID': p.pmid || '',
      'Title': p.title,
      'Authors': (p.authors || []).map((a: any) => `${a.lastName} ${a.foreName || ''}`).join('; '),
      'Journal': p.journal || '',
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

  // Deals sheet
  if (reportData.deals.length > 0) {
    const dealsForExport = reportData.deals.map(d => ({
      'Date': d.date || d.announcedDate || '',
      'Type': d.dealType || d.type || '',
      'Parties': (d.parties || []).join(', '),
      'Asset': d.asset?.name || d.assetName || '',
      'Therapeutic Area': d.therapeuticArea || '',
      'Upfront ($M)': d.terms?.upfrontPayment || '',
      'Total Value ($M)': d.terms?.totalValue || '',
      'Source': d.source || '',
    }));
    const dealsSheet = XLSX.utils.json_to_sheet(dealsForExport);
    dealsSheet['!cols'] = [
      { wch: 12 }, { wch: 15 }, { wch: 40 }, { wch: 30 },
      { wch: 20 }, { wch: 12 }, { wch: 15 }, { wch: 20 }
    ];
    XLSX.utils.book_append_sheet(workbook, dealsSheet, 'Deals');
  }

  // Authors/KOLs sheet (derived from publications)
  if (reportData.kols.length > 0) {
    const kolsForExport = reportData.kols.map(k => ({
      'Name': k.name || `${k.lastName || ''} ${k.foreName || ''}`.trim(),
      'Institution': k.primaryInstitution || k.institution || '',
      'Publications': k.publicationCount || 0,
      'First Author': k.firstAuthorCount || 0,
      'Last Author': k.lastAuthorCount || 0,
      'Recent Pubs': k.recentPublications || k.recentPublicationCount || 0,
      'Active': k.isActive ? 'Yes' : 'No',
    }));
    const kolsSheet = XLSX.utils.json_to_sheet(kolsForExport);
    kolsSheet['!cols'] = [
      { wch: 30 }, { wch: 50 }, { wch: 12 }, { wch: 12 },
      { wch: 12 }, { wch: 12 }, { wch: 8 }
    ];
    XLSX.utils.book_append_sheet(workbook, kolsSheet, 'Authors');
  }

  // Assets sheet
  if (reportData.assets && reportData.assets.length > 0) {
    const assetsForExport = reportData.assets.map(a => ({
      'Asset Name': a.name || '',
      'Code Name': a.genericName || '',
      'Company': a.company || '',
      'Modality': a.modality || '',
      'Phase': a.phase || '',
      'Status': a.status || '',
      'Trial Count': a.trialCount || 0,
      'Indications': (a.indications || []).slice(0, 5).join('; '),
      'Partners': (a.partners || []).join('; '),
      'First Trial': a.firstTrialDate || '',
      'Latest Trial': a.latestTrialDate || '',
    }));
    const assetsSheet = XLSX.utils.json_to_sheet(assetsForExport);
    assetsSheet['!cols'] = [
      { wch: 35 }, { wch: 15 }, { wch: 30 }, { wch: 20 },
      { wch: 12 }, { wch: 10 }, { wch: 10 }, { wch: 50 },
      { wch: 30 }, { wch: 12 }, { wch: 12 }
    ];
    XLSX.utils.book_append_sheet(workbook, assetsSheet, 'Assets');
  }

  // Pipeline sheet (if available)
  if (reportData.pipeline && reportData.pipeline.length > 0) {
    const pipelineForExport = reportData.pipeline.map(p => ({
      'Drug Name': p.drugName || p.name || '',
      'Generic Name': p.genericName || '',
      'Phase': typeof p.phase === 'number' ? `Phase ${p.phase}` : p.phase,
      'Indication': p.indication || '',
      'Mechanism': p.mechanism || '',
      'Modality': p.modality || '',
      'Sponsor': p.sponsor || p.partner || '',
      'Expected Readout': p.expectedReadout || p.expectedApproval || '',
      'Peak Revenue': p.peakRevenuePotential || '',
    }));
    const pipelineSheet = XLSX.utils.json_to_sheet(pipelineForExport);
    pipelineSheet['!cols'] = [
      { wch: 30 }, { wch: 20 }, { wch: 10 }, { wch: 40 },
      { wch: 30 }, { wch: 20 }, { wch: 25 }, { wch: 15 }, { wch: 12 }
    ];
    XLSX.utils.book_append_sheet(workbook, pipelineSheet, 'Pipeline');
  }

  // Write to buffer
  const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
  return buffer;
}

// ============================================
// CSV Generation
// ============================================

/**
 * Generate CSV from array of objects
 */
export function generateCSV(data: any[], filename?: string): string {
  if (data.length === 0) return '';

  // Get headers from first object
  const headers = Object.keys(data[0]);

  // Build CSV rows
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

/**
 * Generate multiple CSVs as a zip (for multi-section reports)
 */
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

  if (reportData.deals.length > 0) {
    csvFiles['deals.csv'] = generateCSV(reportData.deals.map(d => ({
      date: d.date || d.announcedDate,
      type: d.dealType || d.type,
      parties: (d.parties || []).join(', '),
      value: d.terms?.totalValue,
    })));
  }

  if (reportData.kols.length > 0) {
    csvFiles['kols.csv'] = generateCSV(reportData.kols.map(k => ({
      name: k.name || `${k.lastName} ${k.foreName}`,
      institution: k.primaryInstitution || k.institution,
      publications: k.publicationCount,
    })));
  }

  return csvFiles;
}

// ============================================
// Utility Functions
// ============================================

/**
 * Escape CSV field value
 */
function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Get content type for export format
 */
export function getContentType(format: 'xlsx' | 'csv'): string {
  return format === 'xlsx'
    ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    : 'text/csv';
}

/**
 * Get file extension for export format
 */
export function getFileExtension(format: 'xlsx' | 'csv'): string {
  return format;
}
