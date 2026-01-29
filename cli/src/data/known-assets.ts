/**
 * Known Assets Database
 *
 * Curated database of known drug assets for key targets.
 * Used to normalize messy clinical trial data and enrich with deal information.
 */

// ============================================
// Types
// ============================================

export interface KnownAsset {
  // Names and identifiers
  primaryName: string;
  codeName?: string;
  genericName?: string;
  aliases: string[];

  // Classification
  target: string;
  modality: 'ADC' | 'mAb' | 'Bispecific' | 'CAR-T' | 'Radioconjugate' | 'Small Molecule' | 'BiTE' | 'TCE' | 'Vaccine' | 'Other';
  payload?: string; // For ADCs: DXd, MMAE, duocarmazine, etc.

  // Ownership
  owner: string;
  ownerType: 'Big Pharma' | 'Biotech' | 'Chinese Biotech' | 'Academic' | 'Other';
  partner?: string;

  // Development status
  phase: 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2/3' | 'Phase 3' | 'Filed' | 'Approved';
  status: 'Active' | 'Discontinued' | 'On Hold';
  leadIndication: string;
  otherIndications?: string[];

  // Deal information
  dealTerms?: string;
  dealDate?: string;

  // Notes
  notes?: string;
  differentiator?: string;
  trialIds?: string[];
}

export interface TargetAssetDatabase {
  target: string;
  aliases: string[];
  description: string;
  assets: KnownAsset[];
  excludedDrugs: string[]; // Generic names to filter out
  excludedSponsors: string[]; // Sponsors that are NOT developing target-specific drugs
}

// ============================================
// B7-H3 / CD276 Asset Database
// ============================================

export const B7H3_DATABASE: TargetAssetDatabase = {
  target: 'B7-H3',
  aliases: ['B7H3', 'CD276', 'B7-H3/CD276', '4Ig-B7-H3'],
  description: 'Immune checkpoint protein overexpressed in solid tumors. Limited expression on normal tissues makes it attractive ADC target.',

  assets: [
    // ADCs
    {
      primaryName: 'Ifinatamab deruxtecan',
      codeName: 'DS-7300',
      genericName: 'ifinatamab deruxtecan',
      aliases: ['DS-7300', 'DS-7300a', 'I-DXd', 'DS7300'],
      target: 'B7-H3',
      modality: 'ADC',
      payload: 'DXd (deruxtecan)',
      owner: 'Daiichi Sankyo',
      ownerType: 'Big Pharma',
      partner: 'Merck',
      phase: 'Phase 3',
      status: 'Active',
      leadIndication: 'Small cell lung cancer (SCLC)',
      otherIndications: ['Solid tumors', 'NSCLC', 'Breast cancer'],
      dealTerms: '$22B collaboration with Merck (includes I-DXd + 2 other ADCs)',
      dealDate: '2023-10',
      notes: 'Lead B7-H3 ADC. Part of $22B Daiichi Sankyo/Merck mega-deal. DXd payload proven in Enhertu.',
      differentiator: 'Best-in-class DXd payload; deep Merck partnership',
    },
    {
      primaryName: 'HS-20093',
      codeName: 'HS-20093',
      aliases: ['HS20093', 'GSK4428859', 'GSK\'227', 'GSK-20093'],
      target: 'B7-H3',
      modality: 'ADC',
      payload: 'Topoisomerase I inhibitor',
      owner: 'Hansoh Pharma',
      ownerType: 'Chinese Biotech',
      partner: 'GSK',
      phase: 'Phase 3',
      status: 'Active',
      leadIndication: 'SCLC',
      otherIndications: ['Solid tumors', 'NSCLC'],
      dealTerms: '$85M upfront + $1.7B milestones to GSK for ex-China rights',
      dealDate: '2024-01',
      notes: 'Chinese-origin ADC with GSK partnership. Competing head-to-head with DS-7300.',
      differentiator: 'Strong China data; GSK global development',
    },
    {
      primaryName: 'Vobramitamab duocarmazine',
      codeName: 'MGC018',
      genericName: 'vobramitamab duocarmazine',
      aliases: ['MGC018', 'MGC-018', 'vobramitamab'],
      target: 'B7-H3',
      modality: 'ADC',
      payload: 'Duocarmazine',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'Prostate cancer (mCRPC)',
      otherIndications: ['Solid tumors', 'NSCLC'],
      notes: 'Duocarmazine payload differentiates from DXd-based ADCs. Focused on prostate cancer.',
      differentiator: 'Different payload; prostate cancer focus',
    },
    {
      primaryName: 'CAB-AXL-ADC',
      codeName: 'BA3011',
      aliases: ['BA3011', 'CAB-AXL-ADC'],
      target: 'B7-H3',
      modality: 'ADC',
      payload: 'MMAE',
      owner: 'BioAtla',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'Solid tumors',
      notes: 'Conditionally active biologic (CAB) technology. MMAE payload.',
      differentiator: 'CAB technology for tumor selectivity',
    },
    {
      primaryName: 'YL201',
      codeName: 'YL201',
      aliases: ['YL-201'],
      target: 'B7-H3',
      modality: 'ADC',
      payload: 'DXd',
      owner: 'Sichuan Kelun-Biotech',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1/2',
      status: 'Active',
      leadIndication: 'Solid tumors',
      notes: 'Kelun DXd-based ADC. Part of Merck collaboration.',
      differentiator: 'Merck collaboration potential',
    },

    // Monoclonal Antibodies
    {
      primaryName: 'Enoblituzumab',
      codeName: 'MGA271',
      genericName: 'enoblituzumab',
      aliases: ['MGA271', 'MGA-271'],
      target: 'B7-H3',
      modality: 'mAb',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'Head and neck cancer',
      otherIndications: ['Prostate cancer', 'Pediatric solid tumors'],
      notes: 'Fc-enhanced mAb. Being studied in combination with retifanlimab (PD-1).',
      differentiator: 'Fc-enhanced ADCC; combination potential',
    },
    {
      primaryName: 'Orlotamab',
      codeName: 'MGD009',
      genericName: 'orlotamab',
      aliases: ['MGD009', 'MGD-009'],
      target: 'B7-H3',
      modality: 'Bispecific',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 1',
      status: 'On Hold',
      leadIndication: 'Solid tumors',
      notes: 'B7-H3 x CD3 bispecific DART. Development paused.',
      differentiator: 'DART platform; T-cell engagement',
    },

    // Radioconjugates
    {
      primaryName: 'Omburtamab',
      codeName: '8H9',
      genericName: 'omburtamab',
      aliases: ['131I-omburtamab', 'I-131 omburtamab', '8H9', 'Burtomab'],
      target: 'B7-H3',
      modality: 'Radioconjugate',
      payload: 'Iodine-131',
      owner: 'Y-mAbs Therapeutics',
      ownerType: 'Biotech',
      phase: 'Filed',
      status: 'Active',
      leadIndication: 'CNS/leptomeningeal metastases from neuroblastoma',
      otherIndications: ['Medulloblastoma', 'Diffuse intrinsic pontine glioma (DIPG)'],
      notes: 'First-in-class radioimmunotherapy. BLA filed for neuroblastoma CNS metastases.',
      differentiator: 'Radioconjugate; CNS penetration; pediatric focus',
    },

    // CAR-T
    {
      primaryName: 'B7-H3 CAR-T (Stanford)',
      codeName: '4SCAR-276',
      aliases: ['4SCAR-276', 'B7-H3 CAR-T', 'B7H3 CART'],
      target: 'B7-H3',
      modality: 'CAR-T',
      owner: 'Stanford University',
      ownerType: 'Academic',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Pediatric solid tumors',
      notes: 'Academic CAR-T program. Also programs at Seattle Children\'s and other academic centers.',
      differentiator: 'Academic; pediatric focus',
    },
    {
      primaryName: 'B7-H3 CAR-T (Seattle)',
      codeName: 'SCRI-CARB7H3',
      aliases: ['SCRI-CARB7H3', 'Seattle B7-H3 CAR-T'],
      target: 'B7-H3',
      modality: 'CAR-T',
      owner: 'Seattle Children\'s Research Institute',
      ownerType: 'Academic',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Medulloblastoma and other CNS tumors',
      notes: 'Intrathecal/intratumoral administration for CNS penetration.',
      differentiator: 'CNS administration; pediatric focus',
    },
    {
      primaryName: 'LM-302',
      codeName: 'LM-302',
      aliases: ['LM302'],
      target: 'B7-H3',
      modality: 'CAR-T',
      owner: 'Legend Biotech',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      notes: 'Legend\'s B7-H3 CAR-T program.',
      differentiator: 'Legend platform expertise',
    },

    // Bispecifics
    {
      primaryName: 'Retifanlimab + Enoblituzumab',
      codeName: 'MGA271 combo',
      aliases: ['MGA271 + retifanlimab', 'enoblituzumab combo'],
      target: 'B7-H3',
      modality: 'mAb',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'Head and neck cancer',
      notes: 'Combination of B7-H3 mAb with PD-1 inhibitor.',
      differentiator: 'IO combination approach',
    },

    // Additional Chinese assets
    {
      primaryName: 'TQB2103',
      codeName: 'TQB2103',
      aliases: ['TQB-2103'],
      target: 'B7-H3',
      modality: 'mAb',
      owner: 'Chia Tai Tianqing',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      notes: 'Chinese B7-H3 antibody program.',
    },
    {
      primaryName: 'JS203',
      codeName: 'JS203',
      aliases: ['JS-203'],
      target: 'B7-H3',
      modality: 'ADC',
      owner: 'Junshi Biosciences',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      notes: 'Junshi B7-H3 ADC program.',
    },
  ],

  excludedDrugs: [
    // Generic chemotherapy
    'cyclophosphamide', 'fludarabine', 'bendamustine', 'temozolomide',
    'cisplatin', 'carboplatin', 'oxaliplatin', 'etoposide', 'irinotecan',
    'docetaxel', 'paclitaxel', 'gemcitabine', 'pemetrexed', 'vinblastine',
    'doxorubicin', 'epirubicin', 'methotrexate', 'cytarabine', 'azacitidine',

    // Standard checkpoint inhibitors (unless B7-H3 specific)
    'pembrolizumab', 'nivolumab', 'atezolizumab', 'durvalumab', 'avelumab',
    'ipilimumab', 'tremelimumab', 'cemiplimab',

    // Supportive care
    'dexamethasone', 'prednisone', 'methylprednisolone', 'hydrocortisone',
    'ondansetron', 'granisetron', 'palonosetron', 'aprepitant',
    'filgrastim', 'pegfilgrastim',

    // Other common trial drugs
    'placebo', 'standard of care', 'best supportive care',
  ],

  excludedSponsors: [
    // Generic sponsors that run multi-drug trials
  ],
};

// ============================================
// Target Database Registry
// ============================================

export const TARGET_DATABASES: Record<string, TargetAssetDatabase> = {
  'B7-H3': B7H3_DATABASE,
  'B7H3': B7H3_DATABASE,
  'CD276': B7H3_DATABASE,
};

// ============================================
// Lookup Functions
// ============================================

/**
 * Get asset database for a target
 */
export function getTargetDatabase(target: string): TargetAssetDatabase | null {
  const normalizedTarget = target.toUpperCase().replace(/[-\s]/g, '');

  for (const [key, db] of Object.entries(TARGET_DATABASES)) {
    if (key.toUpperCase().replace(/[-\s]/g, '') === normalizedTarget) {
      return db;
    }
    if (db.aliases.some(a => a.toUpperCase().replace(/[-\s]/g, '') === normalizedTarget)) {
      return db;
    }
  }

  return null;
}

/**
 * Find known asset by name
 */
export function findKnownAsset(
  name: string,
  target?: string
): KnownAsset | null {
  const normalizedName = name.toLowerCase().replace(/[-\s]/g, '');

  const databases = target
    ? [getTargetDatabase(target)].filter(Boolean) as TargetAssetDatabase[]
    : Object.values(TARGET_DATABASES);

  for (const db of databases) {
    for (const asset of db.assets) {
      // Check primary name
      if (asset.primaryName.toLowerCase().replace(/[-\s]/g, '') === normalizedName) {
        return asset;
      }
      // Check code name
      if (asset.codeName?.toLowerCase().replace(/[-\s]/g, '') === normalizedName) {
        return asset;
      }
      // Check generic name
      if (asset.genericName?.toLowerCase().replace(/[-\s]/g, '') === normalizedName) {
        return asset;
      }
      // Check aliases
      if (asset.aliases.some(a => a.toLowerCase().replace(/[-\s]/g, '') === normalizedName)) {
        return asset;
      }
    }
  }

  return null;
}

/**
 * Check if a drug name should be excluded
 */
export function isExcludedDrug(name: string, target?: string): boolean {
  const normalizedName = name.toLowerCase().trim();

  const db = target ? getTargetDatabase(target) : null;
  const excludedDrugs = db?.excludedDrugs || B7H3_DATABASE.excludedDrugs;

  return excludedDrugs.some(excluded =>
    normalizedName.includes(excluded.toLowerCase()) ||
    excluded.toLowerCase().includes(normalizedName)
  );
}

/**
 * Get all known assets for a target
 */
export function getKnownAssetsForTarget(target: string): KnownAsset[] {
  const db = getTargetDatabase(target);
  return db?.assets || [];
}

/**
 * Check if intervention name relates to target
 */
export function isTargetRelatedIntervention(
  interventionName: string,
  interventionDescription: string | undefined,
  target: string
): boolean {
  const db = getTargetDatabase(target);
  if (!db) return false;

  const searchText = `${interventionName} ${interventionDescription || ''}`.toLowerCase();

  // Check if intervention mentions target
  const targetAliases = [db.target.toLowerCase(), ...db.aliases.map(a => a.toLowerCase())];
  for (const alias of targetAliases) {
    if (searchText.includes(alias.replace(/-/g, ''))) return true;
    if (searchText.includes(alias)) return true;
  }

  // Check if intervention is a known asset
  const knownAsset = findKnownAsset(interventionName, target);
  if (knownAsset) return true;

  return false;
}
