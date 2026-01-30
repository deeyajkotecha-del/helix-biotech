/**
 * Arrowhead Pharmaceuticals (ARWR) Company Profile
 *
 * Curated data from investor presentations and SEC filings.
 * Platform: TRiM (Targeted RNAi Molecule) technology
 */

// ============================================
// Types
// ============================================

export interface CompanyProfile {
  ticker: string;
  name: string;
  description: string;
  platform: string;
  therapeuticFocus: string[];
  headquarters: string;
  founded: number;
  employees?: number;
  website: string;
  irUrl: string;
}

export interface PipelineAsset {
  name: string;
  codeNames: string[];
  target: string;
  modality: string;
  phase: 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2b' | 'Phase 3' | 'Filed' | 'Approved';
  status: 'Active' | 'On Hold' | 'Discontinued';
  leadIndication: string;
  otherIndications?: string[];
  partner?: string;
  partnerTerritory?: string;
  trials?: string[];
  keyData?: string;
  nextCatalyst?: string;
  catalystDate?: string;
  regulatoryDesignations?: string[];
  notes?: string;
}

export interface ClinicalDataPoint {
  drug: string;
  trial: string;
  indication: string;
  phase: string;
  endpoint: string;
  result: string;
  comparator?: string;
  comparatorResult?: string;
  pValue?: string;
  nPatients?: number;
  duration?: string;
  source: string;
  sourceDate: string;
  conference?: string;
}

export interface UpcomingCatalyst {
  drug: string;
  event: string;
  expectedDate: string;
  type: 'data-readout' | 'regulatory' | 'conference' | 'commercial' | 'other';
  importance: 'high' | 'medium' | 'low';
  notes?: string;
}

export interface Presentation {
  id: string;
  title: string;
  date: string;
  event?: string;
  url: string;
  type: 'corporate' | 'clinical' | 'conference' | 'earnings' | 'poster';
  fileSize?: string;
  downloaded?: boolean;
  analyzed?: boolean;
}

// ============================================
// ARWR Company Profile
// ============================================

export const ARWR_PROFILE: CompanyProfile = {
  ticker: 'ARWR',
  name: 'Arrowhead Pharmaceuticals',
  description: 'Arrowhead develops medicines that treat intractable diseases by silencing the genes that cause them using RNA interference (RNAi). The company\'s proprietary TRiM platform enables targeted delivery of RNAi therapeutics to multiple tissue types.',
  platform: 'TRiM (Targeted RNAi Molecule)',
  therapeuticFocus: [
    'Cardiometabolic',
    'Pulmonary',
    'Hepatic',
    'Neurology (CNS)',
    'Oncology',
  ],
  headquarters: 'Pasadena, California',
  founded: 1989,
  website: 'https://arrowheadpharma.com',
  irUrl: 'https://ir.arrowheadpharma.com',
};

// ============================================
// Pipeline Assets
// ============================================

export const ARWR_PIPELINE: PipelineAsset[] = [
  // ========== APPROVED ==========
  {
    name: 'Plozasiran (REDEMPLO)',
    codeNames: ['ARO-APOC3', 'REDEMPLO'],
    target: 'APOC3',
    modality: 'siRNA',
    phase: 'Approved',
    status: 'Active',
    leadIndication: 'Familial Chylomicronemia Syndrome (FCS)',
    otherIndications: ['Severe Hypertriglyceridemia (sHTG)'],
    partner: 'Amgen',
    partnerTerritory: 'Global',
    keyData: 'PALISADE: 80% TG reduction maintained at 1 year',
    nextCatalyst: 'sHTG approval decision',
    catalystDate: 'H2 2025',
    regulatoryDesignations: ['Breakthrough Therapy', 'Orphan Drug', 'Priority Review'],
    notes: 'First approved Arrowhead drug. FDA approved Dec 2024 for FCS. NMPA (China) and Health Canada approved Jan 2026.',
  },

  // ========== PHASE 3 ==========
  {
    name: 'ARO-APOC3',
    codeNames: ['ARO-APOC3', 'Plozasiran'],
    target: 'APOC3',
    modality: 'siRNA',
    phase: 'Phase 3',
    status: 'Active',
    leadIndication: 'Severe Hypertriglyceridemia (sHTG)',
    trials: ['SHASTA-3', 'SHASTA-4'],
    partner: 'Amgen',
    keyData: 'SHASTA-2: 77% TG reduction (vs placebo)',
    nextCatalyst: 'SHASTA-3/4 Phase 3 data',
    catalystDate: 'H1 2025',
    notes: 'Separate program from approved FCS indication',
  },
  {
    name: 'Zodasiran',
    codeNames: ['ARO-ANG3', 'Zodasiran'],
    target: 'ANGPTL3',
    modality: 'siRNA',
    phase: 'Phase 3',
    status: 'Active',
    leadIndication: 'Mixed Hyperlipidemia',
    otherIndications: ['Homozygous Familial Hypercholesterolemia (HoFH)'],
    trials: ['ARCHES-2'],
    partner: 'Amgen',
    partnerTerritory: 'Global',
    keyData: 'ARCHES-2: 60% LDL reduction, 73% TG reduction',
    nextCatalyst: 'ARCHES-2 pivotal data',
    catalystDate: 'H2 2025',
    regulatoryDesignations: ['Breakthrough Therapy (HoFH)'],
    notes: 'Complementary to statins; potential first-in-class ANGPTL3 siRNA',
  },

  // ========== PHASE 2 ==========
  {
    name: 'ARO-HSD',
    codeNames: ['ARO-HSD'],
    target: 'HSD17B13',
    modality: 'siRNA',
    phase: 'Phase 2',
    status: 'Active',
    leadIndication: 'MASH (Metabolic dysfunction-associated steatohepatitis)',
    partner: 'Takeda',
    partnerTerritory: 'Global',
    keyData: 'Phase 1: Well-tolerated, dose-dependent knockdown',
    nextCatalyst: 'Phase 2 interim data',
    catalystDate: '2025',
    notes: 'Genetic target validated by human genetics; Takeda partnership',
  },
  {
    name: 'ARO-MMP7',
    codeNames: ['ARO-MMP7'],
    target: 'MMP7',
    modality: 'siRNA',
    phase: 'Phase 2',
    status: 'Active',
    leadIndication: 'Idiopathic Pulmonary Fibrosis (IPF)',
    keyData: 'Phase 1: MMP7 knockdown achieved; safety profile acceptable',
    nextCatalyst: 'Phase 2 data',
    catalystDate: '2025',
    notes: 'First pulmonary-targeted siRNA for fibrosis',
  },
  {
    name: 'ARO-DUX4',
    codeNames: ['ARO-DUX4'],
    target: 'DUX4',
    modality: 'siRNA',
    phase: 'Phase 2',
    status: 'Active',
    leadIndication: 'Facioscapulohumeral Muscular Dystrophy (FSHD)',
    partner: 'Sarepta',
    partnerTerritory: 'Ex-US',
    keyData: 'Phase 1: DUX4 silencing demonstrated in muscle',
    nextCatalyst: 'Phase 2 efficacy data',
    catalystDate: '2025',
    regulatoryDesignations: ['Orphan Drug', 'Fast Track'],
    notes: 'Muscle-targeted delivery; Sarepta partnership for commercialization',
  },
  {
    name: 'ARO-C3',
    codeNames: ['ARO-C3'],
    target: 'Complement C3',
    modality: 'siRNA',
    phase: 'Phase 2',
    status: 'Active',
    leadIndication: 'IgA Nephropathy',
    otherIndications: ['Geographic Atrophy', 'Paroxysmal Nocturnal Hemoglobinuria'],
    keyData: 'Phase 1: Robust C3 reduction',
    nextCatalyst: 'Phase 2 data',
    catalystDate: '2025',
    notes: 'Complement system inhibition; multiple indications',
  },

  // ========== PHASE 1/2 ==========
  {
    name: 'ARO-INHBE',
    codeNames: ['ARO-INHBE'],
    target: 'Inhibin beta E (INHBE)',
    modality: 'siRNA',
    phase: 'Phase 1/2',
    status: 'Active',
    leadIndication: 'Obesity',
    keyData: 'Jan 2026: Weight loss demonstrated in diabetic obese patients; improved body composition',
    nextCatalyst: 'Additional cohort data',
    catalystDate: 'H1 2026',
    notes: 'Novel obesity target from human genetics; fat cell apoptosis mechanism',
  },
  {
    name: 'ARO-ALK7',
    codeNames: ['ARO-ALK7'],
    target: 'ALK7 (ACVR1C)',
    modality: 'siRNA',
    phase: 'Phase 1/2',
    status: 'Active',
    leadIndication: 'Obesity',
    keyData: 'Jan 2026: Weight loss in obese diabetic patients; muscle-sparing effect',
    nextCatalyst: 'Additional cohort data',
    catalystDate: 'H1 2026',
    notes: 'Muscle-sparing weight loss; complementary to GLP-1s',
  },
  {
    name: 'ARO-MAPT',
    codeNames: ['ARO-MAPT'],
    target: 'MAPT (Tau)',
    modality: 'siRNA',
    phase: 'Phase 1/2',
    status: 'Active',
    leadIndication: 'Alzheimer\'s Disease',
    otherIndications: ['Frontotemporal Dementia', 'Progressive Supranuclear Palsy'],
    keyData: 'CNS-targeted delivery using TRiM platform',
    nextCatalyst: 'Phase 1 safety/PK data',
    catalystDate: '2026',
    notes: 'First CNS-targeted siRNA from Arrowhead; initiated Dec 2025',
  },
  {
    name: 'ARO-DIMER-PA',
    codeNames: ['ARO-DIMER-PA'],
    target: 'PCSK9 + ANGPTL3',
    modality: 'Dual siRNA',
    phase: 'Phase 1/2',
    status: 'Active',
    leadIndication: 'Mixed Hyperlipidemia',
    keyData: 'First dual-functional RNAi therapeutic',
    nextCatalyst: 'Phase 1 data',
    catalystDate: '2026',
    notes: 'Initiated Jan 2026; single injection targeting two genes',
  },

  // ========== PHASE 1 ==========
  {
    name: 'ARO-RAGE',
    codeNames: ['ARO-RAGE'],
    target: 'RAGE',
    modality: 'siRNA',
    phase: 'Phase 1',
    status: 'Active',
    leadIndication: 'Diabetic Kidney Disease',
    keyData: 'Novel target for diabetic complications',
    notes: 'Kidney-targeted delivery',
  },
  {
    name: 'ARO-COV2',
    codeNames: ['ARO-COV2'],
    target: 'SARS-CoV-2',
    modality: 'siRNA',
    phase: 'Phase 1',
    status: 'Active',
    leadIndication: 'COVID-19',
    notes: 'Inhaled siRNA; pancoronavirus approach',
  },

  // ========== PARTNERED PROGRAMS ==========
  {
    name: 'Fazirsiran',
    codeNames: ['ARO-AAT', 'Fazirsiran', 'TAK-999'],
    target: 'AAT (Alpha-1 Antitrypsin)',
    modality: 'siRNA',
    phase: 'Phase 3',
    status: 'Active',
    leadIndication: 'Alpha-1 Antitrypsin Deficiency Liver Disease (AATD-LD)',
    trials: ['SEQUOIA'],
    partner: 'Takeda',
    partnerTerritory: 'Global',
    keyData: 'SEQUOIA Ph2: Sustained Z-AAT reduction; fibrosis improvement',
    nextCatalyst: 'Phase 3 data',
    catalystDate: '2025',
    regulatoryDesignations: ['Breakthrough Therapy', 'Orphan Drug'],
    notes: 'Takeda-partnered; potential first disease-modifying therapy for AATD-LD',
  },
  {
    name: 'JNJ-3989',
    codeNames: ['ARO-HBV', 'JNJ-3989'],
    target: 'HBV (Hepatitis B Virus)',
    modality: 'siRNA',
    phase: 'Phase 2',
    status: 'Active',
    leadIndication: 'Chronic Hepatitis B',
    partner: 'Johnson & Johnson',
    partnerTerritory: 'Global',
    keyData: 'Functional cure potential; HBsAg reduction',
    nextCatalyst: 'Phase 2b combination data',
    catalystDate: '2025',
    notes: 'J&J-partnered; combination with capsid inhibitor',
  },
];

// ============================================
// Clinical Data Repository
// ============================================

export const ARWR_CLINICAL_DATA: ClinicalDataPoint[] = [
  // PALISADE (Plozasiran/FCS)
  {
    drug: 'Plozasiran',
    trial: 'PALISADE',
    indication: 'FCS',
    phase: 'Phase 3',
    endpoint: 'TG reduction at Week 10',
    result: '-80%',
    comparator: 'Placebo',
    comparatorResult: '-11%',
    pValue: '<0.0001',
    nPatients: 75,
    source: 'ESC 2025',
    sourceDate: '2025-08-29',
    conference: 'ESC 2025',
  },
  {
    drug: 'Plozasiran',
    trial: 'PALISADE OLE',
    indication: 'FCS',
    phase: 'Phase 3 OLE',
    endpoint: 'TG reduction at 1 year',
    result: '-77%',
    nPatients: 70,
    duration: '1 year',
    source: 'ESC 2025',
    sourceDate: '2025-08-29',
    conference: 'ESC 2025',
  },
  // ARCHES-2 (Zodasiran)
  {
    drug: 'Zodasiran',
    trial: 'ARCHES-2',
    indication: 'Mixed Hyperlipidemia',
    phase: 'Phase 2b',
    endpoint: 'LDL-C reduction',
    result: '-60%',
    comparator: 'Placebo',
    comparatorResult: '+2%',
    pValue: '<0.0001',
    source: 'ESC 2025',
    sourceDate: '2025-08-31',
    conference: 'ESC 2025',
  },
  {
    drug: 'Zodasiran',
    trial: 'ARCHES-2',
    indication: 'Mixed Hyperlipidemia',
    phase: 'Phase 2b',
    endpoint: 'TG reduction',
    result: '-73%',
    comparator: 'Placebo',
    comparatorResult: '+5%',
    pValue: '<0.0001',
    source: 'ESC 2025',
    sourceDate: '2025-08-31',
    conference: 'ESC 2025',
  },
  // Obesity programs (Jan 2026 data)
  {
    drug: 'ARO-INHBE',
    trial: 'Phase 1/2',
    indication: 'Obesity (T2D)',
    phase: 'Phase 1/2',
    endpoint: 'Weight loss (interim)',
    result: 'Significant weight loss',
    source: 'Obesity KOL Webinar',
    sourceDate: '2026-01-06',
    conference: 'Arrowhead KOL Webinar',
  },
  {
    drug: 'ARO-ALK7',
    trial: 'Phase 1/2',
    indication: 'Obesity (T2D)',
    phase: 'Phase 1/2',
    endpoint: 'Weight loss + body composition',
    result: 'Weight loss with improved body composition',
    source: 'Obesity KOL Webinar',
    sourceDate: '2026-01-06',
    conference: 'Arrowhead KOL Webinar',
  },
];

// ============================================
// Upcoming Catalysts
// ============================================

export const ARWR_CATALYSTS: UpcomingCatalyst[] = [
  {
    drug: 'Plozasiran',
    event: 'sHTG Phase 3 (SHASTA-3/4) topline data',
    expectedDate: 'H1 2025',
    type: 'data-readout',
    importance: 'high',
    notes: 'If positive, could expand market significantly beyond FCS',
  },
  {
    drug: 'Zodasiran',
    event: 'ARCHES-2 pivotal data / Phase 3 initiation',
    expectedDate: 'H2 2025',
    type: 'data-readout',
    importance: 'high',
    notes: 'Amgen-partnered; key cardiovascular program',
  },
  {
    drug: 'Fazirsiran',
    event: 'SEQUOIA Phase 3 data',
    expectedDate: '2025',
    type: 'data-readout',
    importance: 'high',
    notes: 'Takeda-partnered; first therapy for AATD liver disease',
  },
  {
    drug: 'ARO-INHBE',
    event: 'Additional obesity cohort data',
    expectedDate: 'H1 2026',
    type: 'data-readout',
    importance: 'medium',
    notes: 'Novel obesity mechanism; potential GLP-1 complement',
  },
  {
    drug: 'ARO-ALK7',
    event: 'Additional obesity cohort data',
    expectedDate: 'H1 2026',
    type: 'data-readout',
    importance: 'medium',
    notes: 'Muscle-sparing weight loss; differentiated profile',
  },
  {
    drug: 'ARO-MAPT',
    event: 'Phase 1 CNS data',
    expectedDate: '2026',
    type: 'data-readout',
    importance: 'medium',
    notes: 'First proof-of-concept for CNS TRiM delivery',
  },
  {
    drug: 'Q1 FY2026',
    event: 'Earnings call',
    expectedDate: 'Feb 5, 2026',
    type: 'other',
    importance: 'low',
    notes: 'Financial results and pipeline updates',
  },
];

// ============================================
// Presentations Archive
// ============================================

export const ARWR_PRESENTATIONS: Presentation[] = [
  {
    id: '8933943d-370c-4187-a752-4f73cc77c863',
    title: 'ARO-INHBE and ARO-ALK7 Interim Clinical Data',
    date: '2026-01-06',
    event: 'Obesity KOL Webinar',
    url: 'https://ir.arrowheadpharma.com/static-files/8933943d-370c-4187-a752-4f73cc77c863',
    type: 'clinical',
    fileSize: '20.1 MB',
  },
  {
    id: '61bc8b9b-ccf4-45d7-85ad-0d11825bdbc2',
    title: 'TRiM Platform for CNS Delivery',
    date: '2025-12-10',
    url: 'https://ir.arrowheadpharma.com/static-files/61bc8b9b-ccf4-45d7-85ad-0d11825bdbc2',
    type: 'corporate',
    fileSize: '2.6 MB',
  },
  {
    id: '30b2fbe8-e8b9-4e03-ac03-bd276293430c',
    title: 'Corporate Presentation - December 2025',
    date: '2025-12-08',
    url: 'https://ir.arrowheadpharma.com/static-files/30b2fbe8-e8b9-4e03-ac03-bd276293430c',
    type: 'corporate',
    fileSize: '2.8 MB',
  },
  {
    id: '16629e9f-4cbf-4c34-a39d-f64a88f4a6d5',
    title: 'RNA Leaders USA Congress 2025',
    date: '2025-09-09',
    event: 'RNA Leaders USA Congress',
    url: 'https://ir.arrowheadpharma.com/static-files/16629e9f-4cbf-4c34-a39d-f64a88f4a6d5',
    type: 'conference',
    fileSize: '2 MB',
  },
  {
    id: 'd9630706-0c91-4c68-8332-2e767d022399',
    title: 'ESC 2025 ARCHES-2 Data',
    date: '2025-08-31',
    event: 'ESC 2025',
    url: 'https://ir.arrowheadpharma.com/static-files/d9630706-0c91-4c68-8332-2e767d022399',
    type: 'clinical',
    fileSize: '461.8 KB',
  },
  {
    id: '85178334-9cf1-4b2d-902a-0b766eb133e0',
    title: 'ESC 2025 PALISADE Data',
    date: '2025-08-29',
    event: 'ESC 2025',
    url: 'https://ir.arrowheadpharma.com/static-files/85178334-9cf1-4b2d-902a-0b766eb133e0',
    type: 'clinical',
    fileSize: '723.5 KB',
  },
  {
    id: '25007351-232f-400a-bc0e-0fd4e2906fe8',
    title: 'Corporate Presentation - April 2025',
    date: '2025-04-15',
    url: 'https://ir.arrowheadpharma.com/static-files/25007351-232f-400a-bc0e-0fd4e2906fe8',
    type: 'corporate',
    fileSize: '2.5 MB',
  },
  {
    id: '2741b4fb-3be5-4fbf-be9e-90ce909cd5a9',
    title: 'Complement UK Poster',
    date: '2023-04-03',
    event: 'Complement UK Conference',
    url: 'https://ir.arrowheadpharma.com/static-files/2741b4fb-3be5-4fbf-be9e-90ce909cd5a9',
    type: 'poster',
    fileSize: '1.5 MB',
  },
  {
    id: '6ccca181-6f73-4a58-9a3d-80ba8f61fb1e',
    title: 'ARO-C3 Complement UK Conference',
    date: '2023-04-03',
    event: 'Complement UK Conference',
    url: 'https://ir.arrowheadpharma.com/static-files/6ccca181-6f73-4a58-9a3d-80ba8f61fb1e',
    type: 'conference',
    fileSize: '800.5 KB',
  },
  {
    id: 'ffc86cc4-7005-4f02-a538-ebcf0ed7de0a',
    title: 'Fazirsiran Phase 2 SEQUOIA Study',
    date: '2023-01-09',
    event: 'J.P. Morgan Healthcare Conference',
    url: 'https://ir.arrowheadpharma.com/static-files/ffc86cc4-7005-4f02-a538-ebcf0ed7de0a',
    type: 'clinical',
    fileSize: '1.9 MB',
  },
  {
    id: '740b5038-8ca2-49c9-89af-4dfdf852690a',
    title: 'ERS International Congress 2022',
    date: '2022-09-11',
    event: 'ERS Congress 2022',
    url: 'https://ir.arrowheadpharma.com/static-files/740b5038-8ca2-49c9-89af-4dfdf852690a',
    type: 'conference',
    fileSize: '2.5 MB',
  },
  {
    id: '9de6c80f-459a-419a-87a0-f82125d0196b',
    title: 'EASL 2018 ARO-HBV Talk',
    date: '2018-04-12',
    event: 'EASL 2018',
    url: 'https://ir.arrowheadpharma.com/static-files/9de6c80f-459a-419a-87a0-f82125d0196b',
    type: 'conference',
    fileSize: '1 MB',
  },
];

// ============================================
// Export Helper Functions
// ============================================

export function getARWRProfile() {
  return {
    company: ARWR_PROFILE,
    pipeline: ARWR_PIPELINE,
    clinicalData: ARWR_CLINICAL_DATA,
    catalysts: ARWR_CATALYSTS,
    presentations: ARWR_PRESENTATIONS,
    stats: {
      totalPipelineAssets: ARWR_PIPELINE.length,
      phase3Programs: ARWR_PIPELINE.filter(a => a.phase === 'Phase 3').length,
      approvedProducts: ARWR_PIPELINE.filter(a => a.phase === 'Approved').length,
      partneredPrograms: ARWR_PIPELINE.filter(a => a.partner).length,
      upcomingCatalysts: ARWR_CATALYSTS.filter(c => c.importance === 'high').length,
      totalPresentations: ARWR_PRESENTATIONS.length,
    },
  };
}

export function getARWRPipeline() {
  return ARWR_PIPELINE;
}

export function getARWRCatalysts() {
  return ARWR_CATALYSTS;
}

export function getARWRPresentations() {
  return ARWR_PRESENTATIONS;
}
