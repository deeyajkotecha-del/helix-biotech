/**
 * Target Modalities Database
 *
 * Defines which therapeutic modalities are relevant for each target type.
 * Used to guide comprehensive asset discovery searches.
 */

// ============================================
// Types
// ============================================

export interface TargetModalities {
  officialName: string;
  targetType: 'protein' | 'checkpoint' | 'oncogene' | 'miRNA' | 'receptor' | 'enzyme' | 'other';
  relevantModalities: string[];
  searchTerms: string[];          // Additional search terms for this target
  companyKeywords: string[];      // Companies known to work on this target
  indicationKeywords: string[];   // Common indications
  excludeModalities?: string[];   // Modalities that don't make sense for this target
}

// ============================================
// Target Modalities Database
// ============================================

export const TARGET_MODALITIES: Record<string, TargetModalities> = {
  // ========== Inflammatory/Autoimmune Targets ==========
  'TL1A': {
    officialName: 'TL1A',
    targetType: 'protein',
    relevantModalities: ['mAb', 'bispecific'],
    searchTerms: [
      'TL1A antibody',
      'TL1A inhibitor',
      'anti-TL1A',
      'TNFSF15 antibody',
      'TL1A IBD',
      'TL1A Crohn',
      'TL1A ulcerative colitis',
    ],
    companyKeywords: [
      'Merck', 'Prometheus', 'Roche', 'Roivant', 'Telavant',
      'Sanofi', 'Teva', 'Pfizer', 'AbbVie', 'AnaptysBio', 'GSK',
    ],
    indicationKeywords: ['IBD', 'Crohn', 'ulcerative colitis', 'inflammatory bowel'],
    excludeModalities: ['ADC', 'CAR-T', 'radioconjugate'],  // Not used for autoimmune
  },

  'IL-23': {
    officialName: 'IL-23',
    targetType: 'protein',
    relevantModalities: ['mAb', 'bispecific'],
    searchTerms: [
      'IL-23 antibody',
      'IL-23p19 antibody',
      'anti-IL-23',
      'IL-23 inhibitor',
    ],
    companyKeywords: [
      'AbbVie', 'Johnson & Johnson', 'Janssen', 'Lilly', 'Sun Pharma',
      'Bristol-Myers Squibb', 'UCB',
    ],
    indicationKeywords: ['psoriasis', 'psoriatic arthritis', 'IBD', 'Crohn'],
    excludeModalities: ['ADC', 'CAR-T'],
  },

  // ========== Oncology - Solid Tumor Targets ==========
  'B7-H3': {
    officialName: 'B7-H3',
    targetType: 'checkpoint',
    relevantModalities: ['ADC', 'CAR-T', 'bispecific', 'mAb', 'radioconjugate'],
    searchTerms: [
      'B7-H3 ADC',
      'B7-H3 antibody drug conjugate',
      'B7-H3 CAR-T',
      'CD276 antibody',
      'B7-H3 bispecific',
      'anti-B7-H3',
      'B7-H3 solid tumor',
      'B7-H3 SCLC',
      'B7-H3 pediatric',
    ],
    companyKeywords: [
      'Daiichi Sankyo', 'Merck', 'MacroGenics', 'Y-mAbs', 'GSK', 'Hansoh',
      'BioNTech', 'DualityBio', 'MediLink', 'Legend Biotech', 'BioAtla',
    ],
    indicationKeywords: [
      'SCLC', 'small cell lung', 'NSCLC', 'solid tumor', 'prostate',
      'neuroblastoma', 'pediatric', 'brain tumor', 'DIPG',
    ],
  },

  'Claudin 18.2': {
    officialName: 'Claudin 18.2',
    targetType: 'protein',
    relevantModalities: ['mAb', 'ADC', 'CAR-T', 'bispecific'],
    searchTerms: [
      'Claudin 18.2 antibody',
      'CLDN18.2 ADC',
      'Claudin 18.2 CAR-T',
      'zolbetuximab',
      'anti-Claudin 18.2',
    ],
    companyKeywords: [
      'Astellas', 'Innovent', 'BioNTech', 'I-Mab', 'Kelun',
      'Sotio', 'Arcus', 'CASI',
    ],
    indicationKeywords: ['gastric', 'stomach cancer', 'GEJ', 'pancreatic'],
  },

  'TROP2': {
    officialName: 'TROP2',
    targetType: 'protein',
    relevantModalities: ['ADC', 'bispecific'],
    searchTerms: [
      'TROP2 ADC',
      'TROP2 antibody drug conjugate',
      'sacituzumab govitecan',
      'datopotamab deruxtecan',
      'anti-TROP2',
    ],
    companyKeywords: [
      'Gilead', 'Daiichi Sankyo', 'AstraZeneca', 'Kelun', 'Merck KGaA',
    ],
    indicationKeywords: ['breast cancer', 'TNBC', 'NSCLC', 'urothelial'],
  },

  'HER2': {
    officialName: 'HER2',
    targetType: 'receptor',
    relevantModalities: ['mAb', 'ADC', 'bispecific', 'small molecule'],
    searchTerms: [
      'HER2 antibody',
      'HER2 ADC',
      'trastuzumab',
      'pertuzumab',
      'T-DXd',
      'anti-HER2',
      'HER2 bispecific',
    ],
    companyKeywords: [
      'Roche', 'Genentech', 'Daiichi Sankyo', 'AstraZeneca', 'Seagen',
      'Pfizer', 'Zymeworks',
    ],
    indicationKeywords: ['breast cancer', 'gastric', 'HER2+', 'HER2 low'],
  },

  // ========== Oncology - Mutation Targets ==========
  'KRAS': {
    officialName: 'KRAS',
    targetType: 'oncogene',
    relevantModalities: ['small molecule', 'degrader', 'bispecific'],
    searchTerms: [
      'KRAS inhibitor',
      'KRAS G12C inhibitor',
      'KRAS G12D inhibitor',
      'sotorasib',
      'adagrasib',
      'pan-KRAS',
      'KRAS degrader',
    ],
    companyKeywords: [
      'Amgen', 'Mirati', 'Revolution Medicines', 'Eli Lilly', 'Roche',
      'Bristol-Myers Squibb', 'Boehringer Ingelheim',
    ],
    indicationKeywords: ['NSCLC', 'pancreatic', 'colorectal', 'KRAS mutant'],
    excludeModalities: ['mAb', 'CAR-T'],  // Intracellular target
  },

  'EGFR': {
    officialName: 'EGFR',
    targetType: 'receptor',
    relevantModalities: ['small molecule', 'mAb', 'ADC', 'bispecific'],
    searchTerms: [
      'EGFR inhibitor',
      'EGFR TKI',
      'EGFR antibody',
      'osimertinib',
      'EGFR exon 20',
      'anti-EGFR',
    ],
    companyKeywords: [
      'AstraZeneca', 'Roche', 'Amgen', 'Takeda', 'Janssen', 'Jazz',
    ],
    indicationKeywords: ['NSCLC', 'colorectal', 'head and neck', 'EGFR mutant'],
  },

  // ========== Hematology Targets ==========
  'BCMA': {
    officialName: 'BCMA',
    targetType: 'protein',
    relevantModalities: ['CAR-T', 'bispecific', 'ADC'],
    searchTerms: [
      'BCMA CAR-T',
      'BCMA bispecific',
      'BCMA ADC',
      'anti-BCMA',
      'carvykti',
      'abecma',
      'teclistamab',
    ],
    companyKeywords: [
      'Janssen', 'Legend Biotech', 'Bristol-Myers Squibb', 'Celgene',
      'Pfizer', 'Regeneron', 'GSK',
    ],
    indicationKeywords: ['multiple myeloma', 'myeloma', 'RRMM'],
  },

  'CD19': {
    officialName: 'CD19',
    targetType: 'protein',
    relevantModalities: ['CAR-T', 'bispecific', 'ADC'],
    searchTerms: [
      'CD19 CAR-T',
      'CD19 bispecific',
      'anti-CD19',
      'tisagenlecleucel',
      'axicabtagene',
      'blinatumomab',
    ],
    companyKeywords: [
      'Novartis', 'Kite', 'Gilead', 'Amgen', 'Autolus', 'Caribou',
    ],
    indicationKeywords: ['ALL', 'DLBCL', 'lymphoma', 'leukemia', 'B-cell'],
  },

  // ========== RNA/Gene Targets ==========
  'miR-124': {
    officialName: 'miR-124',
    targetType: 'miRNA',
    relevantModalities: ['mimic', 'small molecule activator', 'nanoparticle', 'exosome', 'gene therapy'],
    searchTerms: [
      'miR-124 mimic',
      'miR-124 therapy',
      'miR-124 nanoparticle',
      'microRNA-124',
      'miR-124 delivery',
      'miR-124 cancer',
      'miR-124 neurodegeneration',
    ],
    companyKeywords: [
      // miRNA space is mostly academic/early stage
      'Regulus', 'miRagen', 'Alnylam', 'Arrowhead',
    ],
    indicationKeywords: [
      'glioblastoma', 'brain cancer', 'neurodegeneration', 'Parkinson',
      'hepatocellular carcinoma',
    ],
    excludeModalities: ['mAb', 'ADC', 'CAR-T'],  // RNA target
  },

  // ========== Checkpoint Inhibitors ==========
  'PD-1': {
    officialName: 'PD-1',
    targetType: 'checkpoint',
    relevantModalities: ['mAb', 'bispecific'],
    searchTerms: [
      'PD-1 antibody',
      'anti-PD-1',
      'PD-1 inhibitor',
      'pembrolizumab',
      'nivolumab',
    ],
    companyKeywords: [
      'Merck', 'Bristol-Myers Squibb', 'Roche', 'AstraZeneca', 'Regeneron',
    ],
    indicationKeywords: ['melanoma', 'NSCLC', 'solid tumor', 'IO'],
  },

  'PD-L1': {
    officialName: 'PD-L1',
    targetType: 'checkpoint',
    relevantModalities: ['mAb', 'bispecific', 'ADC'],
    searchTerms: [
      'PD-L1 antibody',
      'anti-PD-L1',
      'atezolizumab',
      'durvalumab',
      'avelumab',
    ],
    companyKeywords: [
      'Roche', 'AstraZeneca', 'Merck KGaA', 'Pfizer',
    ],
    indicationKeywords: ['NSCLC', 'bladder', 'TNBC', 'solid tumor'],
  },

  'CTLA-4': {
    officialName: 'CTLA-4',
    targetType: 'checkpoint',
    relevantModalities: ['mAb', 'bispecific'],
    searchTerms: [
      'CTLA-4 antibody',
      'anti-CTLA-4',
      'ipilimumab',
      'tremelimumab',
    ],
    companyKeywords: [
      'Bristol-Myers Squibb', 'AstraZeneca', 'Agenus',
    ],
    indicationKeywords: ['melanoma', 'RCC', 'NSCLC'],
  },
};

// ============================================
// Default Modalities
// ============================================

export const DEFAULT_MODALITIES: TargetModalities = {
  officialName: 'Unknown',
  targetType: 'other',
  relevantModalities: ['mAb', 'small molecule', 'ADC', 'bispecific', 'CAR-T'],
  searchTerms: [],
  companyKeywords: [],
  indicationKeywords: [],
};

// ============================================
// Lookup Functions
// ============================================

/**
 * Get modality info for a target
 */
export function getTargetModalities(target: string): TargetModalities {
  const normalized = target.toUpperCase().replace(/[-\s]/g, '');

  for (const [key, info] of Object.entries(TARGET_MODALITIES)) {
    const keyNormalized = key.toUpperCase().replace(/[-\s]/g, '');
    if (keyNormalized === normalized || info.officialName.toUpperCase().replace(/[-\s]/g, '') === normalized) {
      return info;
    }
  }

  // Return default for unknown targets
  return {
    ...DEFAULT_MODALITIES,
    officialName: target,
    searchTerms: [
      `${target} antibody`,
      `${target} inhibitor`,
      `anti-${target}`,
      `${target} drug`,
    ],
  };
}

/**
 * Check if a target has curated modality data
 */
export function hasCuratedModalities(target: string): boolean {
  const normalized = target.toUpperCase().replace(/[-\s]/g, '');
  return Object.keys(TARGET_MODALITIES).some(
    key => key.toUpperCase().replace(/[-\s]/g, '') === normalized
  );
}

/**
 * Get all search terms for comprehensive target research
 */
export function getComprehensiveSearchTerms(target: string): string[] {
  const info = getTargetModalities(target);
  const terms: string[] = [];

  // Basic target searches
  terms.push(`${target} clinical trials drugs companies 2024 2025`);
  terms.push(`${target} pipeline development`);
  terms.push(`anti-${target} therapy`);

  // Add curated search terms
  terms.push(...info.searchTerms);

  // Modality-specific searches
  for (const modality of info.relevantModalities) {
    terms.push(`${target} ${modality} clinical development`);
  }

  // Geographic searches
  terms.push(`Chinese biotech ${target} drug`);
  terms.push(`European ${target} development`);
  terms.push(`Japan ${target} pharmaceutical`);

  // Company searches
  for (const company of info.companyKeywords.slice(0, 5)) {
    terms.push(`${company} ${target}`);
  }

  // Deal searches
  terms.push(`${target} licensing deal acquisition 2023 2024`);
  terms.push(`${target} partnership collaboration`);

  return [...new Set(terms)];  // Dedupe
}
