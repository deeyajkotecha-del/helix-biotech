/**
 * Export Service - Professional Quality Excel
 *
 * Generates investment-grade Excel exports with:
 * - Auto-filters and freeze panes
 * - Conditional formatting by modality
 * - Styled headers and summary dashboards
 */

import ExcelJS from 'exceljs';
import { KnownAsset, InvestmentMetrics, calculateInvestmentMetrics } from '../data/known-assets';
import { getTargetAnalysis, EfficacyDataPoint, DifferentiatorMatrix, TargetAnalysis } from '../data/target-analysis';

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
// Color Schemes
// ============================================

const COLORS = {
  headerBg: '1E3A5F',       // Dark blue
  headerText: 'FFFFFF',      // White
  dealHighlight: '4ADE80',   // Green for deal values

  // Modality colors (light backgrounds)
  ADC: 'E3F2FD',            // Light blue
  'CAR-T': 'E8F5E9',        // Light green
  Bispecific: 'F3E5F5',     // Light purple
  mAb: 'FFF3E0',            // Light orange
  Radioconjugate: 'FFFDE7', // Light yellow
  Other: 'F5F5F5',          // Light gray

  // Phase colors
  'Phase 3': 'C8E6C9',      // Green
  'Filed': 'A5D6A7',        // Darker green
  'Approved': '81C784',     // Even darker green
  'Phase 2': 'FFF9C4',      // Yellow
  'Phase 1': 'E1F5FE',      // Light blue

  // Owner type colors
  'Big Pharma': 'FCE4EC',   // Light pink
  'Biotech': 'E3F2FD',      // Light blue
  'Chinese Biotech': 'FFF8E1', // Light amber
  'Academic': 'E8F5E9',     // Light green
};

function getModalityColor(modality: string): string {
  return COLORS[modality as keyof typeof COLORS] || COLORS.Other;
}

// ============================================
// Excel Generation - Professional Quality
// ============================================

/**
 * Generate professional Excel workbook
 */
export async function generateExcel(reportData: ReportData): Promise<Buffer> {
  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'Satya Bio';
  workbook.created = new Date();

  const curatedAssets = reportData.curatedAssets || [];
  const metrics = curatedAssets.length > 0
    ? calculateInvestmentMetrics(curatedAssets)
    : reportData.investmentMetrics;

  // Get target analysis for investment-grade content
  const targetAnalysis = getTargetAnalysis(reportData.target);

  // 1. Investment Summary Sheet
  if (metrics) {
    createSummarySheet(workbook, reportData.target, metrics, curatedAssets);
  }

  // 2. Investment Thesis Sheet (NEW)
  if (targetAnalysis) {
    createInvestmentThesisSheet(workbook, targetAnalysis);
  }

  // 3. Efficacy Comparison Sheet (NEW)
  if (targetAnalysis && targetAnalysis.efficacyComparison.length > 0) {
    createEfficacyComparisonSheet(workbook, targetAnalysis);
  }

  // 4. Competitive Differentiation Sheet (NEW)
  if (targetAnalysis && targetAnalysis.differentiators.length > 0) {
    createDifferentiatorSheet(workbook, targetAnalysis);
  }

  // 5. Assets Sheet
  if (curatedAssets.length > 0) {
    createAssetsSheet(workbook, curatedAssets);
  }

  // 6. Deal Landscape Sheet (NEW)
  if (curatedAssets.length > 0) {
    createDealLandscapeSheet(workbook, curatedAssets, reportData.target);
  }

  // 7. Trials Sheet
  if (reportData.trials.length > 0) {
    createTrialsSheet(workbook, reportData.trials, curatedAssets);
  }

  // 8. Publications Sheet
  if (reportData.publications.length > 0) {
    createPublicationsSheet(workbook, reportData.publications);
  }

  // 9. Authors Sheet
  if (reportData.kols.length > 0) {
    createAuthorsSheet(workbook, reportData.kols);
  }

  // Write to buffer
  const buffer = await workbook.xlsx.writeBuffer();
  return Buffer.from(buffer);
}

// ============================================
// Summary Dashboard Sheet
// ============================================

function createSummarySheet(
  workbook: ExcelJS.Workbook,
  target: string,
  metrics: InvestmentMetrics,
  assets: KnownAsset[]
): void {
  const sheet = workbook.addWorksheet('Investment Summary', {
    properties: { tabColor: { argb: '4F46E5' } }
  });

  // Title
  sheet.mergeCells('A1:D1');
  const titleCell = sheet.getCell('A1');
  titleCell.value = `${target} Investment Intelligence Report`;
  titleCell.font = { bold: true, size: 18, color: { argb: '1E3A5F' } };
  titleCell.alignment = { horizontal: 'center' };

  sheet.mergeCells('A2:D2');
  sheet.getCell('A2').value = `Generated: ${new Date().toISOString()}`;
  sheet.getCell('A2').font = { italic: true, color: { argb: '6B7280' } };

  let row = 4;

  // DEAL METRICS SECTION
  addSectionHeader(sheet, row, 'DEAL METRICS');
  row += 2;

  addMetricRow(sheet, row++, 'Total Committed (upfront + equity)', `$${(metrics.totalCommitted / 1000).toFixed(2)}B`, '166534');
  addMetricRow(sheet, row++, 'Total Potential (with milestones)', `$${(metrics.totalPotential / 1000).toFixed(2)}B`, '4ADE80');
  addMetricRow(sheet, row++, 'Total Upfront', `$${metrics.totalUpfront.toFixed(0)}M`, '60A5FA');
  addMetricRow(sheet, row++, 'Total Equity Investments', `$${metrics.totalEquity.toFixed(0)}M`, '818CF8');
  addMetricRow(sheet, row++, 'Total Milestones (contingent)', `$${metrics.totalMilestones.toFixed(0)}M`, 'F472B6');
  addMetricRow(sheet, row++, 'Largest Deal', `${metrics.largestDeal.name} - $${(metrics.largestDeal.committed / 1000).toFixed(1)}B committed`, 'DC2626');
  addMetricRow(sheet, row++, 'Assets with Deals', `${metrics.assetsWithDeals} (${metrics.assetsWithVerifiedDeals} verified)`);

  row += 2;

  // Recent Deals List
  addSectionHeader(sheet, row, 'DEALS BREAKDOWN');
  row += 2;

  // Headers
  sheet.getCell(`A${row}`).value = 'Drug';
  sheet.getCell(`B${row}`).value = 'Partner';
  sheet.getCell(`C${row}`).value = 'Upfront ($M)';
  sheet.getCell(`D${row}`).value = 'Equity ($M)';
  sheet.getCell(`E${row}`).value = 'Committed ($M)';
  sheet.getCell(`F${row}`).value = 'Milestones ($M)';
  sheet.getCell(`G${row}`).value = 'Total ($M)';
  sheet.getCell(`H${row}`).value = 'Date';
  const dealHeaderRow = sheet.getRow(row);
  dealHeaderRow.font = { bold: true };
  dealHeaderRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'E5E7EB' }
  };
  row++;

  const dealAssets = assets.filter(a => a.deal);
  for (const asset of dealAssets) {
    const upfront = asset.deal?.upfront || 0;
    const equity = asset.deal?.equity || 0;
    const milestones = asset.deal?.milestones || 0;
    const committed = upfront + equity;
    const total = committed + milestones;

    sheet.getCell(`A${row}`).value = asset.primaryName;
    sheet.getCell(`B${row}`).value = asset.deal?.partner || '';
    sheet.getCell(`C${row}`).value = upfront || '';
    sheet.getCell(`D${row}`).value = equity || '';
    sheet.getCell(`E${row}`).value = committed || '';
    sheet.getCell(`F${row}`).value = milestones || '';
    sheet.getCell(`G${row}`).value = total || '';
    sheet.getCell(`H${row}`).value = asset.deal?.date || '';

    // Highlight committed column
    if (committed > 0) {
      sheet.getCell(`E${row}`).font = { bold: true, color: { argb: '166534' } };
    }

    // Highlight deal rows
    const dealRow = sheet.getRow(row);
    dealRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'F0FDF4' }  // Light green
    };
    row++;
  }

  row += 2;

  // REGULATORY SECTION
  addSectionHeader(sheet, row, 'REGULATORY DESIGNATIONS');
  row += 2;

  addMetricRow(sheet, row++, 'Breakthrough Therapy (BTD)', `${metrics.assetsWithBTD}`, '166534');
  addMetricRow(sheet, row++, 'Orphan Drug (ODD)', `${metrics.assetsWithODD}`, '7C3AED');
  addMetricRow(sheet, row++, 'EU PRIME', `${metrics.assetsWithPRIME}`, '0891B2');
  addMetricRow(sheet, row++, 'Fast Track', `${metrics.assetsWithFastTrack}`, 'EA580C');

  row += 2;

  // PHASE DISTRIBUTION
  addSectionHeader(sheet, row, 'PHASE DISTRIBUTION');
  row += 2;

  const phaseOrder = ['Filed', 'Approved', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Preclinical'];
  for (const phase of phaseOrder) {
    if (metrics.phaseDistribution[phase]) {
      sheet.getCell(`A${row}`).value = phase;
      sheet.getCell(`B${row}`).value = metrics.phaseDistribution[phase];

      const phaseRow = sheet.getRow(row);
      const phaseColor = COLORS[phase as keyof typeof COLORS] || 'F5F5F5';
      phaseRow.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: phaseColor }
      };
      row++;
    }
  }

  row += 2;

  // MODALITY BREAKDOWN
  addSectionHeader(sheet, row, 'MODALITY BREAKDOWN');
  row += 2;

  sheet.getCell(`A${row}`).value = 'Modality';
  sheet.getCell(`B${row}`).value = 'Count';
  sheet.getCell(`C${row}`).value = 'Committed ($B)';
  sheet.getCell(`D${row}`).value = 'Potential ($B)';
  const modalityHeaderRow = sheet.getRow(row);
  modalityHeaderRow.font = { bold: true };
  row++;

  for (const [modality, info] of Object.entries(metrics.modalityBreakdown)) {
    sheet.getCell(`A${row}`).value = modality;
    sheet.getCell(`B${row}`).value = info.count;
    sheet.getCell(`C${row}`).value = info.committed > 0 ? `$${(info.committed / 1000).toFixed(2)}B` : '-';
    sheet.getCell(`D${row}`).value = info.potential > 0 ? `$${(info.potential / 1000).toFixed(2)}B` : '-';

    const modalityRow = sheet.getRow(row);
    modalityRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: getModalityColor(modality) }
    };
    row++;
  }

  row += 2;

  // OWNERSHIP BREAKDOWN
  addSectionHeader(sheet, row, 'OWNERSHIP BREAKDOWN');
  row += 2;

  for (const [ownerType, count] of Object.entries(metrics.ownershipBreakdown)) {
    sheet.getCell(`A${row}`).value = ownerType;
    sheet.getCell(`B${row}`).value = count;

    const ownerColor = COLORS[ownerType as keyof typeof COLORS] || 'F5F5F5';
    const ownerRow = sheet.getRow(row);
    ownerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: ownerColor }
    };
    row++;
  }

  // Column widths
  sheet.getColumn('A').width = 35;
  sheet.getColumn('B').width = 25;
  sheet.getColumn('C').width = 20;
  sheet.getColumn('D').width = 15;
}

function addSectionHeader(sheet: ExcelJS.Worksheet, row: number, title: string): void {
  sheet.mergeCells(`A${row}:D${row}`);
  const cell = sheet.getCell(`A${row}`);
  cell.value = title;
  cell.font = { bold: true, size: 12, color: { argb: 'FFFFFF' } };
  cell.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: '1E3A5F' }
  };
  cell.alignment = { horizontal: 'left' };
}

function addMetricRow(sheet: ExcelJS.Worksheet, row: number, label: string, value: string, valueColor?: string): void {
  sheet.getCell(`A${row}`).value = label;
  sheet.getCell(`A${row}`).font = { bold: true };

  const valueCell = sheet.getCell(`B${row}`);
  valueCell.value = value;
  if (valueColor) {
    valueCell.font = { bold: true, color: { argb: valueColor } };
  }
}

// ============================================
// Assets Sheet
// ============================================

function createAssetsSheet(workbook: ExcelJS.Workbook, assets: KnownAsset[]): void {
  const sheet = workbook.addWorksheet('Assets', {
    properties: { tabColor: { argb: 'DC2626' } },
    views: [{ state: 'frozen', ySplit: 1 }]  // Freeze header row
  });

  // Define columns - with accurate deal metrics
  sheet.columns = [
    { header: 'Drug Name', key: 'drugName', width: 30 },
    { header: 'Code Names', key: 'codeNames', width: 22 },
    { header: 'Target', key: 'target', width: 12 },
    { header: 'Modality', key: 'modality', width: 14 },
    { header: 'Payload/Tech', key: 'tech', width: 35 },
    { header: 'Owner', key: 'owner', width: 25 },
    { header: 'Partner', key: 'partner', width: 18 },
    { header: 'Owner Type', key: 'ownerType', width: 15 },
    { header: 'Phase', key: 'phase', width: 12 },
    { header: 'Status', key: 'status', width: 10 },
    { header: 'Lead Indication', key: 'indication', width: 35 },
    { header: 'Other Indications', key: 'otherIndications', width: 40 },
    { header: 'BTD', key: 'btd', width: 5 },
    { header: 'ODD', key: 'odd', width: 5 },
    { header: 'PRIME', key: 'prime', width: 6 },
    { header: 'Fast Track', key: 'fastTrack', width: 10 },
    { header: 'Deal Partner', key: 'dealPartner', width: 18 },
    { header: 'Upfront ($M)', key: 'dealUpfront', width: 14 },
    { header: 'Equity ($M)', key: 'dealEquity', width: 13 },
    { header: 'Committed ($M)', key: 'dealCommitted', width: 15 },
    { header: 'Milestones ($M)', key: 'dealMilestones', width: 15 },
    { header: 'Total Potential ($M)', key: 'dealTotal', width: 18 },
    { header: 'Deal Date', key: 'dealDate', width: 12 },
    { header: 'Verified', key: 'dealVerified', width: 8 },
    { header: 'Trial IDs', key: 'trialIds', width: 40 },
    { header: 'Trial Count', key: 'trialCount', width: 10 },
    { header: 'Key Data', key: 'keyData', width: 50 },
    { header: 'Notes', key: 'notes', width: 60 },
  ];

  // Style header row
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };
  headerRow.alignment = { horizontal: 'center', vertical: 'middle' };
  headerRow.height = 25;

  // Add data rows with conditional formatting
  assets.forEach((asset, index) => {
    // Calculate committed value
    const upfront = asset.deal?.upfront || 0;
    const equity = asset.deal?.equity || 0;
    const milestones = asset.deal?.milestones || 0;
    const committed = upfront + equity;
    const totalPotential = committed + milestones;

    const row = sheet.addRow({
      drugName: asset.primaryName,
      codeNames: asset.codeNames.join(', '),
      target: asset.target,
      modality: asset.modality,
      tech: asset.modalityDetail || asset.payload || '',
      owner: asset.owner,
      partner: asset.partner || '',
      ownerType: asset.ownerType,
      phase: asset.phase,
      status: asset.status,
      indication: asset.leadIndication,
      otherIndications: (asset.otherIndications || []).join('; '),
      btd: asset.regulatory.btd ? 'Y' : '',
      odd: asset.regulatory.odd ? 'Y' : '',
      prime: asset.regulatory.prime ? 'Y' : '',
      fastTrack: asset.regulatory.fastTrack ? 'Y' : '',
      dealPartner: asset.deal?.partner || '',
      dealUpfront: upfront || '',
      dealEquity: equity || '',
      dealCommitted: committed || '',
      dealMilestones: milestones || '',
      dealTotal: totalPotential || '',
      dealDate: asset.deal?.date || '',
      dealVerified: asset.deal?.hasBreakdown ? 'Y' : '',
      trialIds: asset.trialIds.join(', '),
      trialCount: asset.trialIds.length,
      keyData: asset.keyData || '',
      notes: asset.notes || '',
    });

    // Color row by modality
    const bgColor = getModalityColor(asset.modality);
    row.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: bgColor }
    };

    // Highlight committed column in green if there's a deal
    if (committed > 0) {
      row.getCell('dealCommitted').font = { bold: true, color: { argb: '166534' } };
    }

    // Bold regulatory designations
    if (asset.regulatory.btd) {
      row.getCell('btd').font = { bold: true, color: { argb: '166534' } };
    }
    if (asset.regulatory.odd) {
      row.getCell('odd').font = { bold: true, color: { argb: '7C3AED' } };
    }

    // Add borders
    row.eachCell({ includeEmpty: true }, (cell) => {
      cell.border = {
        top: { style: 'thin', color: { argb: 'E5E7EB' } },
        bottom: { style: 'thin', color: { argb: 'E5E7EB' } },
      };
    });
  });

  // Add auto-filter
  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 28 }
  };
}

// ============================================
// Trials Sheet
// ============================================

function createTrialsSheet(
  workbook: ExcelJS.Workbook,
  trials: any[],
  assets: KnownAsset[]
): void {
  const sheet = workbook.addWorksheet('Trials', {
    properties: { tabColor: { argb: '2563EB' } },
    views: [{ state: 'frozen', ySplit: 1 }]
  });

  sheet.columns = [
    { header: 'NCT ID', key: 'nctId', width: 15 },
    { header: 'Linked Asset', key: 'linkedAsset', width: 25 },
    { header: 'Title', key: 'title', width: 60 },
    { header: 'Phase', key: 'phase', width: 12 },
    { header: 'Status', key: 'status', width: 20 },
    { header: 'Sponsor', key: 'sponsor', width: 30 },
    { header: 'Sponsor Type', key: 'sponsorType', width: 12 },
    { header: 'Conditions', key: 'conditions', width: 40 },
    { header: 'Interventions', key: 'interventions', width: 40 },
    { header: 'Enrollment', key: 'enrollment', width: 10 },
    { header: 'Start Date', key: 'startDate', width: 12 },
    { header: 'Completion', key: 'completion', width: 12 },
    { header: 'Countries', key: 'countries', width: 20 },
  ];

  // Style header
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };
  headerRow.height = 25;

  // Add data
  trials.forEach(trial => {
    const linkedAsset = assets.find(a => a.trialIds.includes(trial.nctId));

    const row = sheet.addRow({
      nctId: trial.nctId,
      linkedAsset: linkedAsset?.primaryName || '',
      title: trial.briefTitle,
      phase: trial.phase,
      status: trial.status,
      sponsor: trial.leadSponsor?.name || '',
      sponsorType: trial.leadSponsor?.type || '',
      conditions: (trial.conditions || []).join('; '),
      interventions: (trial.interventions || []).map((i: any) => i.name).join('; '),
      enrollment: trial.enrollment?.count || '',
      startDate: trial.startDate || '',
      completion: trial.completionDate || '',
      countries: (trial.countries || []).join('; '),
    });

    // Highlight linked trials
    if (linkedAsset) {
      row.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'F0FDF4' }
      };
      row.getCell('linkedAsset').font = { bold: true, color: { argb: '166534' } };
    }

    // Color by status
    if (trial.status === 'Recruiting') {
      row.getCell('status').font = { color: { argb: '166534' } };
    } else if (trial.status === 'Completed') {
      row.getCell('status').font = { color: { argb: '6B7280' } };
    }
  });

  // Auto-filter
  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 13 }
  };
}

// ============================================
// Publications Sheet
// ============================================

function createPublicationsSheet(workbook: ExcelJS.Workbook, publications: any[]): void {
  const sheet = workbook.addWorksheet('Publications', {
    properties: { tabColor: { argb: '059669' } },
    views: [{ state: 'frozen', ySplit: 1 }]
  });

  sheet.columns = [
    { header: 'PMID', key: 'pmid', width: 12 },
    { header: 'Title', key: 'title', width: 80 },
    { header: 'Authors', key: 'authors', width: 50 },
    { header: 'Journal', key: 'journal', width: 30 },
    { header: 'Year', key: 'year', width: 8 },
    { header: 'Type', key: 'type', width: 15 },
  ];

  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };

  publications.forEach(pub => {
    sheet.addRow({
      pmid: pub.pmid || '',
      title: pub.title,
      authors: (pub.authors || []).map((a: any) => `${a.lastName} ${a.foreName || ''}`).join('; '),
      journal: typeof pub.journal === 'object' ? pub.journal?.name : pub.journal || '',
      year: pub.publicationDate?.split('-')[0] || '',
      type: pub.publicationType || '',
    });
  });

  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 6 }
  };
}

// ============================================
// Authors Sheet
// ============================================

function createAuthorsSheet(workbook: ExcelJS.Workbook, kols: any[]): void {
  const sheet = workbook.addWorksheet('Authors', {
    properties: { tabColor: { argb: '7C3AED' } },
    views: [{ state: 'frozen', ySplit: 1 }]
  });

  sheet.columns = [
    { header: 'Name', key: 'name', width: 30 },
    { header: 'Institution', key: 'institution', width: 50 },
    { header: 'Publications', key: 'pubs', width: 12 },
    { header: 'First Author', key: 'first', width: 12 },
    { header: 'Last Author', key: 'last', width: 12 },
  ];

  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };

  kols.forEach(kol => {
    sheet.addRow({
      name: kol.name || `${kol.lastName || ''} ${kol.foreName || ''}`.trim(),
      institution: kol.primaryInstitution || kol.institution || '',
      pubs: kol.publicationCount || 0,
      first: kol.firstAuthorCount || 0,
      last: kol.lastAuthorCount || 0,
    });
  });

  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 5 }
  };
}

// ============================================
// Investment Thesis Sheet (NEW)
// ============================================

function createInvestmentThesisSheet(workbook: ExcelJS.Workbook, analysis: TargetAnalysis): void {
  const sheet = workbook.addWorksheet('Investment Thesis', {
    properties: { tabColor: { argb: 'EAB308' } }
  });

  // Title
  sheet.mergeCells('A1:E1');
  const titleCell = sheet.getCell('A1');
  titleCell.value = `${analysis.target} Investment Thesis`;
  titleCell.font = { bold: true, size: 18, color: { argb: '1E3A5F' } };
  titleCell.alignment = { horizontal: 'center' };

  let row = 3;

  // Headline
  addSectionHeader(sheet, row, 'HEADLINE');
  row += 2;
  sheet.mergeCells(`A${row}:E${row}`);
  sheet.getCell(`A${row}`).value = analysis.investmentThesis.headline;
  sheet.getCell(`A${row}`).font = { bold: true, size: 14, color: { argb: '166534' } };
  sheet.getRow(row).height = 30;
  row += 2;

  // Key Points
  addSectionHeader(sheet, row, 'KEY INVESTMENT POINTS');
  row += 2;
  for (const point of analysis.investmentThesis.keyPoints) {
    sheet.getCell(`A${row}`).value = `• ${point}`;
    sheet.getRow(row).height = 22;
    row++;
  }
  row += 1;

  // Mechanism
  addSectionHeader(sheet, row, 'MECHANISM');
  row += 2;
  sheet.getCell(`A${row}`).value = 'Biology:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.mergeCells(`B${row}:E${row}`);
  sheet.getCell(`B${row}`).value = analysis.mechanism.biology;
  row++;
  sheet.getCell(`A${row}`).value = 'Rationale:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.mergeCells(`B${row}:E${row}`);
  sheet.getCell(`B${row}`).value = analysis.mechanism.rationale;
  row++;
  sheet.getCell(`A${row}`).value = 'Unique Value:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.mergeCells(`B${row}:E${row}`);
  sheet.getCell(`B${row}`).value = analysis.mechanism.uniqueValue;
  sheet.getCell(`B${row}`).font = { color: { argb: '166534' } };
  row += 2;

  // Market Opportunity
  addSectionHeader(sheet, row, 'MARKET OPPORTUNITY');
  row += 2;
  sheet.getCell(`A${row}`).value = 'Total Market:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.getCell(`B${row}`).value = analysis.marketOpportunity.totalMarket;
  row++;
  sheet.getCell(`A${row}`).value = 'Target Share:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.getCell(`B${row}`).value = analysis.marketOpportunity.targetShare;
  sheet.getCell(`B${row}`).font = { bold: true, color: { argb: '166534' } };
  row++;
  sheet.getCell(`A${row}`).value = 'Patient Population:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.getCell(`B${row}`).value = analysis.marketOpportunity.patientPopulation;
  row++;
  sheet.getCell(`A${row}`).value = 'Unmet Need:';
  sheet.getCell(`A${row}`).font = { bold: true };
  sheet.mergeCells(`B${row}:E${row}`);
  sheet.getCell(`B${row}`).value = analysis.marketOpportunity.unmetNeed;
  row += 2;

  // Key Risks
  addSectionHeader(sheet, row, 'KEY RISKS');
  row += 2;
  sheet.getCell(`A${row}`).value = 'Risk';
  sheet.getCell(`B${row}`).value = 'Severity';
  sheet.getCell(`C${row}`).value = 'Mitigation';
  const riskHeaderRow = sheet.getRow(row);
  riskHeaderRow.font = { bold: true };
  riskHeaderRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'E5E7EB' }
  };
  row++;

  for (const risk of analysis.keyRisks) {
    sheet.getCell(`A${row}`).value = risk.risk;
    sheet.getCell(`B${row}`).value = risk.severity;
    sheet.getCell(`C${row}`).value = risk.mitigation || '';

    // Color severity
    const severityCell = sheet.getCell(`B${row}`);
    if (risk.severity === 'High') {
      severityCell.font = { bold: true, color: { argb: 'DC2626' } };
    } else if (risk.severity === 'Medium') {
      severityCell.font = { color: { argb: 'EA580C' } };
    } else {
      severityCell.font = { color: { argb: '166534' } };
    }
    row++;
  }
  row += 1;

  // Catalysts
  addSectionHeader(sheet, row, 'CATALYSTS TO WATCH');
  row += 2;
  sheet.getCell(`A${row}`).value = 'Event';
  sheet.getCell(`B${row}`).value = 'Drug';
  sheet.getCell(`C${row}`).value = 'Timing';
  sheet.getCell(`D${row}`).value = 'Significance';
  const catHeaderRow = sheet.getRow(row);
  catHeaderRow.font = { bold: true };
  catHeaderRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: 'E5E7EB' }
  };
  row++;

  for (const catalyst of analysis.catalystsToWatch) {
    sheet.getCell(`A${row}`).value = catalyst.event;
    sheet.getCell(`B${row}`).value = catalyst.drug;
    sheet.getCell(`C${row}`).value = catalyst.timing;
    sheet.getCell(`D${row}`).value = catalyst.significance;

    // Highlight high significance
    if (catalyst.significance === 'High') {
      const sigCell = sheet.getCell(`D${row}`);
      sigCell.font = { bold: true, color: { argb: '166534' } };
      sheet.getRow(row).fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'F0FDF4' }
      };
    }
    row++;
  }

  // Column widths
  sheet.getColumn('A').width = 45;
  sheet.getColumn('B').width = 30;
  sheet.getColumn('C').width = 40;
  sheet.getColumn('D').width = 15;
  sheet.getColumn('E').width = 20;
}

// ============================================
// Efficacy Comparison Sheet (NEW)
// ============================================

function createEfficacyComparisonSheet(workbook: ExcelJS.Workbook, analysis: TargetAnalysis): void {
  const sheet = workbook.addWorksheet('Efficacy Comparison', {
    properties: { tabColor: { argb: '22C55E' } },
    views: [{ state: 'frozen', ySplit: 1 }]
  });

  sheet.columns = [
    { header: 'Drug', key: 'drug', width: 30 },
    { header: 'Trial', key: 'trial', width: 20 },
    { header: 'Phase', key: 'phase', width: 12 },
    { header: 'Dose', key: 'dose', width: 22 },
    { header: 'Indication', key: 'indication', width: 20 },
    { header: 'Endpoint', key: 'endpoint', width: 22 },
    { header: 'Result (%)', key: 'result', width: 12 },
    { header: 'Placebo (%)', key: 'placebo', width: 12 },
    { header: 'Δ vs Placebo', key: 'delta', width: 14 },
    { header: 'Timepoint', key: 'timepoint', width: 12 },
    { header: 'Population', key: 'population', width: 25 },
    { header: 'Source', key: 'source', width: 15 },
    { header: 'Notes', key: 'notes', width: 40 },
  ];

  // Style header
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };
  headerRow.height = 25;

  // Add data - sort by placebo-adjusted descending
  const sortedData = [...analysis.efficacyComparison].sort((a, b) => b.placeboAdjusted - a.placeboAdjusted);

  sortedData.forEach((data, index) => {
    const row = sheet.addRow({
      drug: data.drug,
      trial: data.trial,
      phase: data.phase,
      dose: data.dose,
      indication: data.indication,
      endpoint: data.endpoint,
      result: data.result,
      placebo: data.placebo,
      delta: data.placeboAdjusted,
      timepoint: data.timepoint || '',
      population: data.population || '',
      source: data.source,
      notes: data.notes || '',
    });

    // Highlight best result (first row after sorting)
    if (index === 0) {
      row.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'DCFCE7' }  // Light green
      };
      row.getCell('delta').font = { bold: true, color: { argb: '166534' } };
    }

    // Bold the delta column
    row.getCell('delta').font = { bold: true };

    // Color delta by value
    if (data.placeboAdjusted >= 25) {
      row.getCell('delta').font = { bold: true, color: { argb: '166534' } };
    } else if (data.placeboAdjusted >= 20) {
      row.getCell('delta').font = { bold: true, color: { argb: '16A34A' } };
    }

    // Add note about biomarker selection
    if (data.population) {
      row.getCell('population').font = { italic: true, color: { argb: '7C3AED' } };
    }
  });

  // Auto-filter
  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 13 }
  };
}

// ============================================
// Competitive Differentiation Sheet (NEW)
// ============================================

function createDifferentiatorSheet(workbook: ExcelJS.Workbook, analysis: TargetAnalysis): void {
  const sheet = workbook.addWorksheet('Differentiation', {
    properties: { tabColor: { argb: 'A855F7' } },
    views: [{ state: 'frozen', ySplit: 1 }]
  });

  sheet.columns = [
    { header: 'Drug', key: 'drug', width: 30 },
    { header: 'Strategy', key: 'strategy', width: 25 },
    { header: 'Dosing', key: 'dosing', width: 22 },
    { header: 'Biomarker', key: 'biomarker', width: 18 },
    { header: 'Half-Life', key: 'halfLife', width: 12 },
    { header: 'Beyond Indication', key: 'beyond', width: 30 },
    { header: 'Mechanism', key: 'mechanism', width: 25 },
    { header: 'Administration', key: 'admin', width: 15 },
  ];

  // Style header
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };
  headerRow.height = 25;

  // Add data
  analysis.differentiators.forEach((diff, index) => {
    const row = sheet.addRow({
      drug: diff.drug,
      strategy: diff.strategy,
      dosing: diff.dosing,
      biomarker: diff.biomarker,
      halfLife: diff.halfLife,
      beyond: diff.beyondIndication,
      mechanism: diff.mechanism || '',
      admin: diff.administration || '',
    });

    // Alternate row colors
    if (index % 2 === 0) {
      row.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'F3E8FF' }  // Light purple
      };
    }

    // Highlight biomarker if present
    if (diff.biomarker && diff.biomarker !== 'No' && diff.biomarker !== 'TBD') {
      row.getCell('biomarker').font = { bold: true, color: { argb: '7C3AED' } };
    }
  });

  // Auto-filter
  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 8 }
  };
}

// ============================================
// Deal Landscape Sheet (NEW)
// ============================================

function createDealLandscapeSheet(workbook: ExcelJS.Workbook, assets: KnownAsset[], target: string): void {
  const sheet = workbook.addWorksheet('Deal Landscape', {
    properties: { tabColor: { argb: 'F59E0B' } },
    views: [{ state: 'frozen', ySplit: 1 }]
  });

  // Filter to only assets with deals
  const dealAssets = assets.filter(a => a.deal);

  sheet.columns = [
    { header: 'Drug', key: 'drug', width: 30 },
    { header: 'Partner', key: 'partner', width: 25 },
    { header: 'Deal Type', key: 'dealType', width: 20 },
    { header: 'Upfront ($M)', key: 'upfront', width: 14 },
    { header: 'Equity ($M)', key: 'equity', width: 14 },
    { header: 'Committed ($M)', key: 'committed', width: 16 },
    { header: 'Milestones ($M)', key: 'milestones', width: 16 },
    { header: 'Total Potential ($M)', key: 'total', width: 18 },
    { header: 'Date', key: 'date', width: 12 },
    { header: 'Territory', key: 'territory', width: 25 },
    { header: 'Verified', key: 'verified', width: 10 },
    { header: 'Notes', key: 'notes', width: 50 },
    { header: 'Source', key: 'source', width: 40 },
  ];

  // Style header
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true, color: { argb: 'FFFFFF' } };
  headerRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.headerBg }
  };
  headerRow.height = 25;

  // Sort by committed value descending
  const sortedAssets = [...dealAssets].sort((a, b) => {
    const aCommitted = (a.deal?.upfront || 0) + (a.deal?.equity || 0);
    const bCommitted = (b.deal?.upfront || 0) + (b.deal?.equity || 0);
    return bCommitted - aCommitted;
  });

  // Calculate totals
  let totalUpfront = 0;
  let totalEquity = 0;
  let totalMilestones = 0;

  sortedAssets.forEach((asset, index) => {
    const upfront = asset.deal?.upfront || 0;
    const equity = asset.deal?.equity || 0;
    const milestones = asset.deal?.milestones || 0;
    const committed = upfront + equity;
    const total = committed + milestones;

    totalUpfront += upfront;
    totalEquity += equity;
    totalMilestones += milestones;

    // Determine deal type
    let dealType = 'Partnership';
    if (asset.deal?.headline?.toLowerCase().includes('acquisition')) {
      dealType = 'Acquisition';
    } else if (asset.deal?.headline?.toLowerCase().includes('collaboration')) {
      dealType = 'Collaboration';
    } else if (asset.deal?.headline?.toLowerCase().includes('licens')) {
      dealType = 'License';
    }

    const row = sheet.addRow({
      drug: asset.primaryName,
      partner: asset.deal?.partner || '',
      dealType,
      upfront: upfront || '',
      equity: equity || '',
      committed: committed || '',
      milestones: milestones || '',
      total: total || '',
      date: asset.deal?.date || '',
      territory: asset.deal?.territory || '',
      verified: asset.deal?.hasBreakdown ? 'Yes' : 'No',
      notes: asset.deal?.notes || '',
      source: asset.deal?.source || '',
    });

    // Highlight largest deal
    if (index === 0) {
      row.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FEF3C7' }  // Light amber
      };
    }

    // Bold committed column
    if (committed > 0) {
      row.getCell('committed').font = { bold: true, color: { argb: '166534' } };
    }

    // Color by deal type
    if (dealType === 'Acquisition') {
      row.getCell('dealType').font = { bold: true, color: { argb: 'DC2626' } };
    }
  });

  // Add totals row
  const totalCommitted = totalUpfront + totalEquity;
  const totalPotential = totalCommitted + totalMilestones;

  const totalsRow = sheet.addRow({
    drug: 'TOTAL',
    partner: '',
    dealType: '',
    upfront: totalUpfront,
    equity: totalEquity,
    committed: totalCommitted,
    milestones: totalMilestones,
    total: totalPotential,
    date: '',
    territory: '',
    verified: '',
    notes: '',
    source: '',
  });

  totalsRow.font = { bold: true };
  totalsRow.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: '1E3A5F' }
  };
  totalsRow.getCell('drug').font = { bold: true, color: { argb: 'FFFFFF' } };
  totalsRow.getCell('committed').font = { bold: true, color: { argb: '4ADE80' } };
  totalsRow.getCell('total').font = { bold: true, color: { argb: 'FFFFFF' } };

  // Auto-filter (exclude totals row)
  sheet.autoFilter = {
    from: { row: 1, column: 1 },
    to: { row: 1, column: 13 }
  };
}

// ============================================
// CSV Generation (kept for backwards compat)
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
