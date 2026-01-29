/**
 * Pharma Data Service
 *
 * Proof-of-concept data for Merck (MRK) based on JPM 2026 presentation.
 * Provides pharma profile lookups, pipeline comparisons, BD fit analysis,
 * and catalyst tracking.
 */

import {
  PharmaProfile,
  PipelineAsset,
  Catalyst,
  RevenueOpportunity,
  Deal,
  StrategicPriorities,
  PipelineStats,
} from '../types/pharma';
import { PHARMA_COMPANIES } from './pharma-registry';

// ============================================
// Merck JPM 2026 Pipeline Data - 10 Priority Assets
// ============================================

const MERCK_PIPELINE: PipelineAsset[] = [
  {
    drugName: 'sacituzumab tirumotecan (sac-TMT)',
    genericName: 'MK-2870',
    mechanism: 'Trop2-directed ADC',
    modality: 'Antibody-drug conjugate',
    phase: 3,
    indication: 'Breast cancer, NSCLC',
    therapeuticArea: 'Oncology',
    partner: 'Kelun-Biotech',
    expectedReadout: '2026 H2',
    isPriority: true,
    peakRevenuePotential: '>$5B',
    notes: 'Next-gen Trop2 ADC with differentiated payload; potential best-in-class',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'ifinatamab deruxtecan (I-DXd)',
    genericName: 'MK-7036',
    mechanism: 'B7-H3-directed ADC',
    modality: 'Antibody-drug conjugate',
    phase: 3,
    indication: 'Small cell lung cancer (SCLC)',
    therapeuticArea: 'Oncology',
    partner: 'Daiichi Sankyo',
    expectedReadout: '2026',
    isPriority: true,
    peakRevenuePotential: '>$3B',
    notes: 'Part of $22B Daiichi Sankyo collaboration; first-in-class B7-H3 ADC',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'enlicitide',
    genericName: 'MK-6024',
    mechanism: 'Oral GLP-1 receptor agonist',
    modality: 'Small molecule',
    phase: 2,
    indication: 'Obesity, Type 2 diabetes',
    therapeuticArea: 'Cardiovascular/Metabolic',
    expectedReadout: '2026 H2',
    isPriority: true,
    peakRevenuePotential: '>$10B',
    notes: 'Oral small molecule GLP-1; potential game-changer if efficacy matches injectables',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'tulisokibart',
    genericName: 'MK-7240',
    mechanism: 'TL1A antibody',
    modality: 'Monoclonal antibody',
    phase: 3,
    indication: 'Ulcerative colitis, Crohn\'s disease',
    therapeuticArea: 'Immunology',
    expectedReadout: '2026 H2',
    isPriority: true,
    peakRevenuePotential: '>$4B',
    notes: 'Novel target in IBD; potential first-in-class TL1A inhibitor',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'WINREVAIR',
    genericName: 'sotatercept',
    mechanism: 'Activin signaling inhibitor',
    modality: 'Fusion protein',
    phase: 4,
    indication: 'Pulmonary arterial hypertension (PAH)',
    therapeuticArea: 'Cardiovascular',
    expectedApproval: 'Filed',
    isPriority: true,
    peakRevenuePotential: '>$3B',
    notes: 'Approved March 2024; best-in-class PAH therapy; rapid uptake; label expansion ongoing',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'MK-5684',
    genericName: 'opevesostat',
    mechanism: 'CYP11A1 inhibitor',
    modality: 'Small molecule',
    phase: 3,
    indication: 'Metastatic castration-resistant prostate cancer (mCRPC)',
    therapeuticArea: 'Oncology',
    expectedReadout: '2026 H2',
    isPriority: true,
    peakRevenuePotential: '>$2B',
    notes: 'Novel androgen synthesis inhibitor; differentiated from current standards',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'patritumab deruxtecan (HER3-DXd)',
    genericName: 'MK-7684',
    mechanism: 'HER3-directed ADC',
    modality: 'Antibody-drug conjugate',
    phase: 3,
    indication: 'NSCLC, breast cancer',
    therapeuticArea: 'Oncology',
    partner: 'Daiichi Sankyo',
    expectedReadout: '2026',
    isPriority: true,
    peakRevenuePotential: '>$3B',
    notes: 'Part of $22B Daiichi Sankyo collaboration; EGFR-mutant NSCLC focus',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'MK-8189',
    mechanism: 'PDE10A inhibitor',
    modality: 'Small molecule',
    phase: 2,
    indication: 'Schizophrenia',
    therapeuticArea: 'Neuroscience',
    expectedReadout: '2026 Q2',
    isPriority: true,
    peakRevenuePotential: '>$2B',
    notes: 'Differentiated mechanism; adjunctive therapy for treatment-resistant patients',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'clesrovimab',
    genericName: 'MK-1654',
    mechanism: 'RSV F-protein inhibitor',
    modality: 'Monoclonal antibody',
    phase: 3,
    indication: 'RSV prevention in infants',
    therapeuticArea: 'Infectious Disease',
    expectedApproval: 'Filed',
    isPriority: true,
    peakRevenuePotential: '>$2B',
    notes: 'Extended half-life; single dose for full RSV season; differentiated from Beyfortus',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
  {
    drugName: 'V116',
    mechanism: 'Pneumococcal conjugate vaccine (21-valent)',
    modality: 'Vaccine',
    phase: 3,
    indication: 'Pneumococcal disease in adults',
    therapeuticArea: 'Infectious Disease',
    expectedApproval: 'Filed',
    isPriority: true,
    peakRevenuePotential: '>$2B',
    notes: 'Adult-specific PCV; PNEU-AGE Phase 3 positive; differentiated serotype coverage',
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
  },
];

// ============================================
// Merck Catalysts
// ============================================

const MERCK_CATALYSTS: Catalyst[] = [
  {
    date: '2026-Q1',
    dateType: 'quarter',
    eventType: 'filing',
    drugName: 'clesrovimab',
    indication: 'RSV prevention in infants',
    description: 'FDA filing decision expected; BLA under priority review',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026-Q1',
    dateType: 'quarter',
    eventType: 'approval',
    drugName: 'V116',
    indication: 'Pneumococcal disease (adults)',
    description: 'FDA approval decision for adult pneumococcal vaccine',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026-Q2',
    dateType: 'quarter',
    eventType: 'phase2_readout',
    drugName: 'MK-8189',
    indication: 'Schizophrenia',
    description: 'Phase 2b readout for PDE10A inhibitor in schizophrenia',
    significance: 'medium',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026-H2',
    dateType: 'half',
    eventType: 'phase3_readout',
    drugName: 'sac-TMT',
    indication: 'Triple-negative breast cancer',
    description: 'Phase 3 OptiTROP-Breast01 readout in TNBC',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026-H2',
    dateType: 'half',
    eventType: 'phase3_readout',
    drugName: 'tulisokibart',
    indication: 'Ulcerative colitis',
    description: 'Phase 3 AMBITION UC readout',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026-H2',
    dateType: 'half',
    eventType: 'phase2_readout',
    drugName: 'enlicitide',
    indication: 'Obesity',
    description: 'Phase 2 dose-ranging study readout for oral GLP-1',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026-H2',
    dateType: 'half',
    eventType: 'phase3_readout',
    drugName: 'MK-5684',
    indication: 'Prostate cancer',
    description: 'Phase 3 readout in mCRPC',
    significance: 'medium',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026',
    dateType: 'year',
    eventType: 'phase3_readout',
    drugName: 'I-DXd',
    indication: 'Small cell lung cancer',
    description: 'Phase 3 IDeate-Lung01 readout in extensive-stage SCLC',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2026',
    dateType: 'year',
    eventType: 'phase3_readout',
    drugName: 'HER3-DXd',
    indication: 'EGFR-mutant NSCLC',
    description: 'Phase 3 HERTHENA-Lung02 readout',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2027',
    dateType: 'year',
    eventType: 'phase3_readout',
    drugName: 'tulisokibart',
    indication: "Crohn's disease",
    description: "Phase 3 AMBITION CD readout",
    significance: 'high',
    source: 'Merck JPM 2026',
  },
  {
    date: '2028',
    dateType: 'year',
    eventType: 'approval',
    drugName: 'KEYTRUDA SC',
    indication: 'Multiple solid tumors',
    description: 'Subcutaneous KEYTRUDA approval expected; LOE extension strategy',
    significance: 'high',
    source: 'Merck JPM 2026',
  },
];

// ============================================
// Merck Deals
// ============================================

const MERCK_DEALS: Deal[] = [
  {
    date: '2023-10',
    type: 'Collaboration ($22B)',
    targetCompany: 'Daiichi Sankyo',
    asset: 'Three ADC candidates (patritumab deruxtecan, ifinatamab deruxtecan, raludotatug deruxtecan)',
    therapeuticArea: 'Oncology',
    rationale: 'Next-generation ADC platform to diversify beyond KEYTRUDA IO franchise',
    source: 'Merck JPM 2026',
  },
  {
    date: '2024-01',
    type: 'Acquisition ($680M)',
    targetCompany: 'Harpoon Therapeutics',
    asset: 'T-cell engager platform',
    therapeuticArea: 'Oncology',
    rationale: 'Expand into T-cell engager modality for hematologic malignancies',
    source: 'Merck JPM 2026',
  },
  {
    date: '2024-02',
    type: 'License ($5.5B)',
    targetCompany: 'Kelun-Biotech',
    asset: 'sacituzumab tirumotecan (sac-TMT) and other ADCs',
    therapeuticArea: 'Oncology',
    rationale: 'Trop2 ADC with differentiated payload; best-in-class potential',
    source: 'Merck JPM 2026',
  },
  {
    date: '2024-09',
    type: 'Collaboration ($2B)',
    targetCompany: 'LaNova Medicines',
    asset: 'ADC candidates (HER2, Trop2)',
    therapeuticArea: 'Oncology',
    rationale: 'Expand ADC portfolio; China-origin assets with global rights',
    source: 'Merck JPM 2026',
  },
  {
    date: '2025-05',
    type: 'License ($1.3B)',
    targetCompany: 'Curon Biopharmaceutical',
    asset: 'CN201 (bispecific antibody)',
    therapeuticArea: 'Oncology',
    rationale: 'PD-1 x VEGF bispecific to complement KEYTRUDA franchise',
    source: 'Merck JPM 2026',
  },
];

// ============================================
// Merck Strategic Priorities
// ============================================

const MERCK_STRATEGY: StrategicPriorities = {
  priorities: [
    'Navigate KEYTRUDA LOE (2028) with pipeline diversification',
    'Build next-generation oncology franchise (ADCs, bispecifics, IO combos)',
    'Grow cardiovascular portfolio (WINREVAIR, oral GLP-1)',
    'Expand immunology franchise with TL1A platform',
    'Strengthen infectious disease and vaccine portfolio',
    'Maintain $10B+ annual BD investment pace',
  ],
  therapeuticFocus: [
    'Oncology (60%+ of pipeline)',
    'Cardiovascular/Metabolic',
    'Immunology',
    'Infectious Disease & Vaccines',
    'Neuroscience (selective)',
  ],
  modalityInvestments: [
    'Antibody-drug conjugates (ADCs)',
    'Bispecific antibodies',
    'Immuno-oncology combinations',
    'Oral biologics (GLP-1, PCSK9)',
    'mRNA (next-gen vaccines)',
  ],
  whitespaceAreas: [
    'Ophthalmology',
    'CNS beyond schizophrenia',
    'Dermatology',
    'Rare diseases with high unmet need',
  ],
  bdAppetite: {
    highInterest: [
      'Antibody-drug conjugates (ADCs)',
      'Ophthalmology assets',
      'Novel IO mechanisms (LAG-3, TIGIT, etc.)',
      'Cardiovascular with large patient populations',
    ],
    moderateInterest: [
      'Neuroscience (differentiated mechanisms)',
      'Vaccines and infectious disease',
      'Rare diseases with clear path to approval',
    ],
    lowInterest: [
      'Cell therapy / CAR-T (manufacturing complexity)',
      'Obesity (large acquisitions - prefer internal development)',
      'Biosimilars',
      'Gene therapy (delivery challenges)',
    ],
  },
  keyQuotes: [
    {
      quote: 'We are building a pipeline that can more than offset the KEYTRUDA LOE and deliver sustained growth through the end of the decade.',
      speaker: 'Robert Davis, CEO',
      context: 'JPM 2026 Healthcare Conference',
    },
    {
      quote: 'Our ADC strategy is differentiated - we are not building one ADC, we are building a platform with multiple payloads and targets.',
      speaker: 'Dean Li, President of Merck Research Labs',
      context: 'JPM 2026 R&D Overview',
    },
    {
      quote: 'Tulisokibart represents our entry into immunology with a first-in-class mechanism that could transform treatment of IBD.',
      speaker: 'Dean Li, President of Merck Research Labs',
      context: 'JPM 2026 Pipeline Update',
    },
  ],
  source: 'Merck JPM 2026 Presentation',
  extractedAt: '2026-01-13',
};

// ============================================
// Merck Revenue Opportunities
// ============================================

const MERCK_REVENUE_OPPS: RevenueOpportunity[] = [
  {
    therapeuticArea: 'Oncology',
    targetYear: '2030',
    revenueEstimate: '>$25B',
    riskAdjusted: false,
    keyAssets: ['sac-TMT', 'I-DXd', 'HER3-DXd', 'MK-5684', 'KEYTRUDA combos'],
    source: 'Merck JPM 2026',
  },
  {
    therapeuticArea: 'Cardiovascular/Metabolic',
    targetYear: '2030',
    revenueEstimate: '~$20B',
    riskAdjusted: false,
    keyAssets: ['WINREVAIR', 'enlicitide', 'MK-0616 (oral PCSK9)'],
    source: 'Merck JPM 2026',
  },
  {
    therapeuticArea: 'Infectious Disease',
    targetYear: '2030',
    revenueEstimate: '~$15B',
    riskAdjusted: false,
    keyAssets: ['V116', 'clesrovimab', 'GARDASIL', 'VAXNEUVANCE'],
    source: 'Merck JPM 2026',
  },
  {
    therapeuticArea: 'Immunology',
    targetYear: '2030',
    revenueEstimate: '>$5B',
    riskAdjusted: false,
    keyAssets: ['tulisokibart'],
    source: 'Merck JPM 2026',
  },
  {
    therapeuticArea: 'Total Company',
    targetYear: '2030',
    revenueEstimate: '>$65B',
    riskAdjusted: false,
    keyAssets: ['Diversified portfolio across oncology, CV, ID, immunology'],
    source: 'Merck JPM 2026',
  },
];

// ============================================
// Merck Key Financials
// ============================================

const MERCK_FINANCIALS = {
  rdSpend: '$30.5B (2024)',
  bdInvestmentSince2021: '$50B+',
  phase3StudiesOngoing: 25,
  expectedLaunches: '10+ new products by 2030',
};

// ============================================
// Service Functions
// ============================================

function computePipelineStats(pipeline: PipelineAsset[]): PipelineStats {
  const byPhase: Record<string, number> = {};
  const byTherapeuticArea: Record<string, number> = {};
  const byModality: Record<string, number> = {};

  for (const asset of pipeline) {
    const phaseLabel = asset.phase >= 4 ? 'Approved/Phase 4' : `Phase ${asset.phase}`;
    byPhase[phaseLabel] = (byPhase[phaseLabel] || 0) + 1;
    byTherapeuticArea[asset.therapeuticArea] = (byTherapeuticArea[asset.therapeuticArea] || 0) + 1;
    byModality[asset.modality] = (byModality[asset.modality] || 0) + 1;
  }

  return {
    totalAssets: pipeline.length,
    byPhase,
    byTherapeuticArea,
    byModality,
  };
}

/**
 * Get full pharma profile for a given ticker.
 * Currently only Merck (MRK) has proof-of-concept data.
 */
export function getPharmaProfile(ticker: string): PharmaProfile | null {
  const key = ticker.toUpperCase();
  const company = PHARMA_COMPANIES[key];
  if (!company) return null;

  if (key === 'MRK') {
    return {
      company,
      lastUpdated: '2026-01-13',
      keyFinancials: MERCK_FINANCIALS,
      pipeline: MERCK_PIPELINE,
      pipelineStats: computePipelineStats(MERCK_PIPELINE),
      revenueOpportunities: MERCK_REVENUE_OPPS,
      catalysts: MERCK_CATALYSTS,
      recentDeals: MERCK_DEALS,
      strategy: MERCK_STRATEGY,
    };
  }

  // Stub for non-Merck companies
  return {
    company,
    lastUpdated: 'N/A',
    pipeline: [],
    pipelineStats: { totalAssets: 0, byPhase: {}, byTherapeuticArea: {}, byModality: {} },
    revenueOpportunities: [],
    catalysts: [],
    recentDeals: [],
    strategy: {
      priorities: [],
      therapeuticFocus: [],
      modalityInvestments: [],
      whitespaceAreas: [],
      bdAppetite: { highInterest: [], moderateInterest: [], lowInterest: [] },
      keyQuotes: [],
      source: 'Not yet available',
      extractedAt: 'N/A',
    },
  };
}

/**
 * Get summary list of all registered pharma companies
 */
export function getAllPharmaSummary(): {
  ticker: string;
  name: string;
  cik: string;
  verified: boolean;
  hasData: boolean;
  pipelineCount: number;
}[] {
  return Object.values(PHARMA_COMPANIES).map((c) => {
    const profile = getPharmaProfile(c.ticker);
    return {
      ticker: c.ticker,
      name: c.name,
      cik: c.cik,
      verified: c.verified,
      hasData: (profile?.pipeline.length ?? 0) > 0,
      pipelineCount: profile?.pipeline.length ?? 0,
    };
  });
}

/**
 * Compare pipeline stats between two companies
 */
export function comparePipelines(
  tickerA: string,
  tickerB: string
): {
  companyA: { ticker: string; name: string; stats: PipelineStats };
  companyB: { ticker: string; name: string; stats: PipelineStats };
  overlappingAreas: string[];
} | null {
  const profileA = getPharmaProfile(tickerA);
  const profileB = getPharmaProfile(tickerB);
  if (!profileA || !profileB) return null;

  const areasA = new Set(Object.keys(profileA.pipelineStats.byTherapeuticArea));
  const areasB = new Set(Object.keys(profileB.pipelineStats.byTherapeuticArea));
  const overlappingAreas = [...areasA].filter((a) => areasB.has(a));

  return {
    companyA: {
      ticker: profileA.company.ticker,
      name: profileA.company.name,
      stats: profileA.pipelineStats,
    },
    companyB: {
      ticker: profileB.company.ticker,
      name: profileB.company.name,
      stats: profileB.pipelineStats,
    },
    overlappingAreas,
  };
}

/**
 * Analyze BD fit: which of a target company's whitespace areas
 * match an asset's therapeutic area?
 */
export function analyzeBDFit(
  targetTicker: string,
  assetTherapeuticArea: string,
  assetModality: string
): {
  targetCompany: string;
  fitScore: 'high' | 'medium' | 'low' | 'unknown';
  rationale: string[];
} | null {
  const profile = getPharmaProfile(targetTicker);
  if (!profile) return null;

  const rationale: string[] = [];
  let score = 0;

  const strategy = profile.strategy;

  // Check if area is in therapeutic focus
  if (strategy.therapeuticFocus.some((f) => f.toLowerCase().includes(assetTherapeuticArea.toLowerCase()))) {
    score += 3;
    rationale.push(`${assetTherapeuticArea} is a core therapeutic focus area`);
  }

  // Check whitespace
  if (strategy.whitespaceAreas.some((w) => w.toLowerCase().includes(assetTherapeuticArea.toLowerCase()))) {
    score += 2;
    rationale.push(`${assetTherapeuticArea} is an identified whitespace area`);
  }

  // Check modality fit
  if (strategy.modalityInvestments.some((m) => m.toLowerCase().includes(assetModality.toLowerCase()))) {
    score += 2;
    rationale.push(`${assetModality} aligns with modality investment priorities`);
  }

  // Check BD appetite
  if (strategy.bdAppetite.highInterest.some((h) => h.toLowerCase().includes(assetTherapeuticArea.toLowerCase()) || h.toLowerCase().includes(assetModality.toLowerCase()))) {
    score += 3;
    rationale.push(`High BD interest in ${assetModality || assetTherapeuticArea}`);
  } else if (strategy.bdAppetite.moderateInterest.some((m) => m.toLowerCase().includes(assetTherapeuticArea.toLowerCase()) || m.toLowerCase().includes(assetModality.toLowerCase()))) {
    score += 1;
    rationale.push(`Moderate BD interest in ${assetTherapeuticArea}`);
  } else if (strategy.bdAppetite.lowInterest.some((l) => l.toLowerCase().includes(assetTherapeuticArea.toLowerCase()) || l.toLowerCase().includes(assetModality.toLowerCase()))) {
    score -= 1;
    rationale.push(`Low BD interest in ${assetModality || assetTherapeuticArea}`);
  }

  if (rationale.length === 0) {
    rationale.push('Insufficient strategy data to assess fit');
  }

  let fitScore: 'high' | 'medium' | 'low' | 'unknown';
  if (score >= 5) fitScore = 'high';
  else if (score >= 2) fitScore = 'medium';
  else if (rationale.length > 0 && score >= 0) fitScore = 'low';
  else fitScore = 'unknown';

  return {
    targetCompany: profile.company.name,
    fitScore,
    rationale,
  };
}

/**
 * Get upcoming catalysts across all companies (or for a specific ticker)
 */
export function getUpcomingCatalysts(ticker?: string): Catalyst[] {
  if (ticker) {
    const profile = getPharmaProfile(ticker);
    return profile?.catalysts ?? [];
  }

  // Aggregate from all companies
  const all: Catalyst[] = [];
  for (const key of Object.keys(PHARMA_COMPANIES)) {
    const profile = getPharmaProfile(key);
    if (profile) {
      all.push(...profile.catalysts);
    }
  }
  return all;
}
