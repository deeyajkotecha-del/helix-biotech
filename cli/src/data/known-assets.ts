/**
 * Known Assets Database - Investment Ready
 *
 * Curated database of known drug assets for key targets.
 * Contains complete deal terms, regulatory designations, and clinical data.
 */

// ============================================
// Types
// ============================================

export interface RegulatoryDesignations {
  btd: boolean;      // Breakthrough Therapy Designation
  odd: boolean;      // Orphan Drug Designation
  fastTrack: boolean;
  prime: boolean;    // EU PRIME
  rmat?: boolean;    // Regenerative Medicine Advanced Therapy
}

export interface DealTerms {
  headline: string;           // e.g., "$22B collaboration with Merck"
  upfront?: string;           // e.g., "$4B + $1.5B equity"
  milestones?: string;        // e.g., "Up to $16.5B"
  totalValue?: string;        // e.g., "$22B"
  date?: string;              // e.g., "2023-10"
  partner?: string;           // Deal partner
  territory?: string;         // e.g., "Global ex-China"
  notes?: string;
}

export interface KnownAsset {
  // Names and identifiers
  primaryName: string;        // Full INN name: "Ifinatamab deruxtecan"
  codeNames: string[];        // Code names: ["DS-7300", "I-DXd", "DS-7300a"]
  genericName?: string;       // Generic/INN: "ifinatamab deruxtecan"
  aliases: string[];          // All searchable names

  // Classification
  target: string;             // "B7-H3" or "B7-H3 x CD3"
  modality: 'ADC' | 'mAb' | 'Bispecific' | 'CAR-T' | 'Radioconjugate' | 'Small Molecule' | 'BiTE' | 'TCE' | 'Vaccine' | 'Other';
  modalityDetail?: string;    // "Topoisomerase I inhibitor (DXd payload)"
  payload?: string;           // For ADCs: "DXd", "MMAE", "Duocarmazine"

  // Ownership
  owner: string;
  ownerType: 'Big Pharma' | 'Biotech' | 'Chinese Biotech' | 'Academic' | 'Other';
  partner?: string;

  // Development status
  phase: 'Preclinical' | 'Phase 1' | 'Phase 1/2' | 'Phase 2' | 'Phase 2/3' | 'Phase 3' | 'Filed' | 'Approved';
  status: 'Active' | 'Discontinued' | 'On Hold';
  leadIndication: string;
  otherIndications?: string[];

  // Regulatory designations
  regulatory: RegulatoryDesignations;

  // Deal information
  deal?: DealTerms;

  // Clinical data
  trialIds: string[];         // Linked NCT IDs
  keyData?: string;           // "52% ORR in SCLC (ASCO 2024)"

  // Notes
  notes?: string;
  differentiator?: string;
}

export interface TargetAssetDatabase {
  target: string;
  aliases: string[];
  description: string;
  assets: KnownAsset[];
  excludedDrugs: string[];
  excludedSponsors: string[];
}

// ============================================
// B7-H3 / CD276 Asset Database - COMPLETE
// ============================================

export const B7H3_DATABASE: TargetAssetDatabase = {
  target: 'B7-H3',
  aliases: ['B7H3', 'CD276', 'B7-H3/CD276', '4Ig-B7-H3'],
  description: 'Immune checkpoint protein overexpressed in solid tumors. Limited expression on normal tissues makes it attractive ADC target.',

  assets: [
    // ========== ADCs ==========
    {
      primaryName: 'Ifinatamab deruxtecan',
      codeNames: ['DS-7300', 'I-DXd', 'DS-7300a'],
      genericName: 'ifinatamab deruxtecan',
      aliases: ['DS-7300', 'DS-7300a', 'I-DXd', 'DS7300', 'ifinatamab'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'Topoisomerase I inhibitor (DXd/deruxtecan payload)',
      payload: 'DXd (deruxtecan)',
      owner: 'Daiichi Sankyo',
      ownerType: 'Big Pharma',
      partner: 'Merck',
      phase: 'Phase 3',
      status: 'Active',
      leadIndication: 'ES-SCLC (Extensive-Stage Small Cell Lung Cancer)',
      otherIndications: ['NSCLC', 'Solid tumors', 'Breast cancer', 'Prostate cancer'],
      regulatory: { btd: true, odd: true, fastTrack: true, prime: false },
      deal: {
        headline: '$22B collaboration with Merck',
        upfront: '$4B + $1.5B equity investment',
        milestones: 'Up to $16.5B',
        totalValue: '$22B',
        date: '2023-10',
        partner: 'Merck',
        territory: 'Global (co-develop/co-commercialize)',
        notes: 'Includes I-DXd + 2 other Daiichi ADCs. Largest ADC deal ever.',
      },
      trialIds: ['NCT05280470', 'NCT04145622', 'NCT05104866', 'NCT06362252'],
      keyData: '52% ORR in ES-SCLC; 26% ORR in heavily pretreated solid tumors (ASCO 2024)',
      notes: 'Lead B7-H3 ADC globally. DXd payload proven with Enhertu. Pivotal Phase 3 TROPION-Lung08 ongoing.',
      differentiator: 'Best-in-class DXd payload; deep Merck partnership; most advanced',
    },
    {
      primaryName: 'Risvutatug rezetecan',
      codeNames: ['HS-20093', 'GSK4428859'],
      genericName: 'risvutatug rezetecan',
      aliases: ['HS-20093', 'HS20093', 'GSK4428859', 'GSK\'227'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'Topoisomerase I inhibitor payload',
      payload: 'Topoisomerase I inhibitor',
      owner: 'Hansoh Pharma',
      ownerType: 'Chinese Biotech',
      partner: 'GSK',
      phase: 'Phase 3',
      status: 'Active',
      leadIndication: 'ES-SCLC',
      otherIndications: ['NSCLC', 'Solid tumors'],
      regulatory: { btd: false, odd: false, fastTrack: true, prime: false },
      deal: {
        headline: '$1.7B deal with GSK',
        upfront: '$85M',
        milestones: 'Up to $1.525B',
        totalValue: '$1.7B',
        date: '2024-01',
        partner: 'GSK',
        territory: 'Ex-China rights',
      },
      trialIds: ['NCT06052423', 'NCT05276609'],
      keyData: '75% ORR in ES-SCLC 2L+ (WCLC 2023); durable responses',
      notes: 'Chinese-origin ADC with strong efficacy data. Phase 3 initiated.',
      differentiator: 'Strong China data; GSK global development; competitive with I-DXd',
    },
    {
      primaryName: 'YL201',
      codeNames: ['YL201'],
      aliases: ['YL-201'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'Topoisomerase I inhibitor (proprietary payload)',
      payload: 'Topo I inhibitor',
      owner: 'MediLink Therapeutics',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'ES-SCLC',
      otherIndications: ['Solid tumors'],
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: ['NCT05857684'],
      keyData: '61% ORR in ES-SCLC; 80.6% DCR (ASCO 2024)',
      notes: 'Competitive China ADC with strong Phase 1/2 data. Seeking global partner.',
      differentiator: 'Differentiated payload; strong efficacy',
    },
    {
      primaryName: 'DB-1311',
      codeNames: ['DB-1311', 'BNT324'],
      aliases: ['BNT324', 'DB1311'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'Topoisomerase I inhibitor payload',
      payload: 'Topo I inhibitor',
      owner: 'DualityBio',
      ownerType: 'Chinese Biotech',
      partner: 'BioNTech',
      phase: 'Phase 1/2',
      status: 'Active',
      leadIndication: 'Solid tumors',
      otherIndications: ['SCLC', 'NSCLC'],
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      deal: {
        headline: '$1.67B deal with BioNTech',
        upfront: '$170M',
        milestones: 'Up to $1.5B',
        totalValue: '$1.67B',
        date: '2024-03',
        partner: 'BioNTech',
        territory: 'Global ex-Greater China',
      },
      trialIds: ['NCT05914116'],
      keyData: 'Early clinical; BioNTech validation',
      notes: 'BioNTech acquired global rights. Part of broader ADC collaboration.',
      differentiator: 'BioNTech partnership; mRNA combo potential',
    },
    {
      primaryName: 'MHB088C',
      codeNames: ['MHB088C'],
      aliases: ['MHB-088C'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'ADC with undisclosed payload',
      owner: 'Minghui Pharmaceuticals',
      ownerType: 'Chinese Biotech',
      partner: 'Qilu Pharmaceutical',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      deal: {
        headline: '1.345B RMB deal with Qilu',
        upfront: '45M RMB',
        milestones: '1.3B RMB',
        totalValue: '1.345B RMB (~$185M)',
        date: '2024-04',
        partner: 'Qilu Pharmaceutical',
        territory: 'Greater China',
      },
      trialIds: ['NCT05865470'],
      notes: 'China-focused ADC program.',
      differentiator: 'China market focus',
    },
    {
      primaryName: 'Vobramitamab duocarmazine',
      codeNames: ['MGC018'],
      genericName: 'vobramitamab duocarmazine',
      aliases: ['MGC018', 'MGC-018', 'vobramitamab'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'Duocarmazine DNA alkylating payload',
      payload: 'Duocarmazine',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'mCRPC (Metastatic Castration-Resistant Prostate Cancer)',
      otherIndications: ['Solid tumors', 'NSCLC', 'Triple-negative breast cancer'],
      regulatory: { btd: false, odd: false, fastTrack: true, prime: false },
      trialIds: ['NCT03729596', 'NCT04086368'],
      keyData: '40% PSA50 response rate in mCRPC; differentiated prostate focus',
      notes: 'Only B7-H3 ADC with duocarmazine payload. Prostate cancer focus differentiates.',
      differentiator: 'Unique payload; prostate cancer focus; less competitive landscape',
    },
    {
      primaryName: 'BA3011',
      codeNames: ['BA3011', 'CAB-B7-H3-ADC'],
      aliases: ['CAB-B7-H3-ADC'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'Conditionally Active Biologic (CAB) with MMAE payload',
      payload: 'MMAE',
      owner: 'BioAtla',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'Solid tumors',
      otherIndications: ['Sarcoma', 'NSCLC'],
      regulatory: { btd: false, odd: true, fastTrack: false, prime: false },
      trialIds: ['NCT03872947'],
      keyData: 'CAB technology enables tumor-selective activation',
      notes: 'Conditionally active - only activates in tumor microenvironment.',
      differentiator: 'CAB technology for improved therapeutic window',
    },
    {
      primaryName: 'JS203',
      codeNames: ['JS203'],
      aliases: ['JS-203'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'ADC with proprietary payload',
      owner: 'Junshi Biosciences',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: ['NCT05252390'],
      notes: 'Early-stage China ADC program.',
      differentiator: 'Junshi platform',
    },
    {
      primaryName: 'SHR-3680',
      codeNames: ['SHR-3680'],
      aliases: ['SHR3680'],
      target: 'B7-H3',
      modality: 'ADC',
      owner: 'Hengrui Medicine',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: [],
      notes: 'Hengrui B7-H3 ADC program.',
      differentiator: 'Hengrui capabilities',
    },

    // ========== Monoclonal Antibodies ==========
    {
      primaryName: 'Enoblituzumab',
      codeNames: ['MGA271'],
      genericName: 'enoblituzumab',
      aliases: ['MGA271', 'MGA-271'],
      target: 'B7-H3',
      modality: 'mAb',
      modalityDetail: 'Fc-enhanced humanized IgG1 monoclonal antibody',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'HNSCC (Head and Neck Squamous Cell Carcinoma)',
      otherIndications: ['Prostate cancer', 'Pediatric solid tumors', 'Melanoma'],
      regulatory: { btd: false, odd: true, fastTrack: false, prime: false },
      trialIds: ['NCT02475213', 'NCT02923180'],
      keyData: 'Fc-enhanced for ADCC; combination with retifanlimab (PD-1)',
      notes: 'Being studied in combination with PD-1 inhibitor retifanlimab.',
      differentiator: 'Fc-enhanced ADCC; IO combination approach',
    },
    {
      primaryName: 'TQB2103',
      codeNames: ['TQB2103'],
      aliases: ['TQB-2103'],
      target: 'B7-H3',
      modality: 'mAb',
      owner: 'Chia Tai Tianqing',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: [],
      notes: 'Chinese B7-H3 antibody program.',
      differentiator: 'China market',
    },

    // ========== Bispecifics ==========
    {
      primaryName: 'MGD024',
      codeNames: ['MGD024'],
      aliases: ['MGD-024'],
      target: 'B7-H3 x CD3',
      modality: 'Bispecific',
      modalityDetail: 'DART (Dual-Affinity Re-Targeting) B7-H3 x CD3 bispecific',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      otherIndications: ['Pediatric solid tumors'],
      regulatory: { btd: false, odd: true, fastTrack: false, prime: false },
      trialIds: ['NCT05440500'],
      notes: 'Next-generation DART bispecific. Successor to MGD009.',
      differentiator: 'DART platform; T-cell engagement',
    },
    {
      primaryName: 'Orlotamab',
      codeNames: ['MGD009'],
      genericName: 'orlotamab',
      aliases: ['MGD009', 'MGD-009'],
      target: 'B7-H3 x CD3',
      modality: 'Bispecific',
      modalityDetail: 'DART B7-H3 x CD3 bispecific (first-gen)',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 1',
      status: 'On Hold',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: ['NCT02628535'],
      notes: 'Development paused. MGD024 is successor.',
      differentiator: 'First-gen DART; development paused',
    },
    {
      primaryName: 'PT217',
      codeNames: ['PT217'],
      aliases: [],
      target: 'B7-H3 x 4-1BB',
      modality: 'Bispecific',
      modalityDetail: 'B7-H3 x 4-1BB bispecific antibody',
      owner: 'Phanes Therapeutics',
      ownerType: 'Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: [],
      notes: 'Novel 4-1BB costimulation approach.',
      differentiator: '4-1BB costimulation',
    },

    // ========== Radioconjugates ==========
    {
      primaryName: 'Omburtamab',
      codeNames: ['8H9', 'Burtomab'],
      genericName: 'omburtamab',
      aliases: ['131I-omburtamab', 'I-131 omburtamab', '8H9', 'Burtomab'],
      target: 'B7-H3',
      modality: 'Radioconjugate',
      modalityDetail: 'Iodine-131 labeled monoclonal antibody (radioimmunotherapy)',
      payload: 'Iodine-131',
      owner: 'Y-mAbs Therapeutics',
      ownerType: 'Biotech',
      phase: 'Filed',
      status: 'Active',
      leadIndication: 'CNS/leptomeningeal metastases from neuroblastoma',
      otherIndications: ['Medulloblastoma', 'DIPG (Diffuse Intrinsic Pontine Glioma)', 'Brain metastases'],
      regulatory: { btd: true, odd: true, fastTrack: false, prime: true, rmat: true },
      trialIds: ['NCT03275402', 'NCT01502917', 'NCT05064306'],
      keyData: 'BLA filed Oct 2022; PDUFA extended; Phase 3 for DIPG',
      notes: 'First-in-class radioimmunotherapy for CNS tumors. BLA under review.',
      differentiator: 'Only radioconjugate; CNS penetration; pediatric focus',
    },

    // ========== CAR-T ==========
    {
      primaryName: '4SCAR-276',
      codeNames: ['4SCAR-276'],
      aliases: ['B7-H3 CAR-T Stanford'],
      target: 'B7-H3',
      modality: 'CAR-T',
      modalityDetail: '4th generation CAR-T targeting B7-H3',
      owner: 'Stanford University',
      ownerType: 'Academic',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Pediatric solid tumors',
      otherIndications: ['Neuroblastoma', 'Osteosarcoma'],
      regulatory: { btd: false, odd: true, fastTrack: false, prime: false },
      trialIds: ['NCT04483778'],
      notes: 'Academic CAR-T program with encouraging early signals.',
      differentiator: 'Academic; pediatric focus; 4th gen CAR',
    },
    {
      primaryName: 'SCRI-CARB7H3',
      codeNames: ['SCRI-CARB7H3'],
      aliases: ['Seattle B7-H3 CAR-T', 'B7-H3 CAR-T Seattle'],
      target: 'B7-H3',
      modality: 'CAR-T',
      modalityDetail: 'CAR-T for CNS tumors with intrathecal delivery',
      owner: "Seattle Children's Research Institute",
      ownerType: 'Academic',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Medulloblastoma',
      otherIndications: ['DIPG', 'CNS tumors', 'Ependymoma'],
      regulatory: { btd: false, odd: true, fastTrack: false, prime: false },
      trialIds: ['NCT04185038', 'NCT04897321'],
      keyData: 'Intrathecal delivery for CNS penetration',
      notes: 'Pioneering intrathecal CAR-T delivery for brain tumors.',
      differentiator: 'CNS administration; pediatric CNS tumors',
    },
    {
      primaryName: 'TAA06',
      codeNames: ['TAA06'],
      aliases: [],
      target: 'B7-H3',
      modality: 'CAR-T',
      modalityDetail: 'Autologous B7-H3 CAR-T',
      owner: 'PersonGen BioTherapeutics',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      otherIndications: ['Lung cancer', 'Ovarian cancer'],
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: ['NCT04432649'],
      notes: 'Chinese CAR-T program advancing in solid tumors.',
      differentiator: 'China CAR-T leader',
    },
    {
      primaryName: 'LM-302',
      codeNames: ['LM-302'],
      aliases: ['LM302'],
      target: 'B7-H3',
      modality: 'CAR-T',
      modalityDetail: 'Autologous B7-H3 CAR-T',
      owner: 'Legend Biotech',
      ownerType: 'Chinese Biotech',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: [],
      notes: 'Legend Biotech B7-H3 CAR-T (same company as Carvykti).',
      differentiator: 'Legend platform expertise (Carvykti approved)',
    },
    {
      primaryName: 'B7-H3 CAR-T (NCI)',
      codeNames: ['NCI-B7H3-CAR'],
      aliases: [],
      target: 'B7-H3',
      modality: 'CAR-T',
      modalityDetail: 'NCI-developed B7-H3 CAR-T',
      owner: 'National Cancer Institute',
      ownerType: 'Academic',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Pediatric solid tumors',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: ['NCT04897321'],
      notes: 'NCI-sponsored pediatric program.',
      differentiator: 'NCI expertise; pediatric focus',
    },
    {
      primaryName: 'C7R-GD2/B7-H3 CAR-T',
      codeNames: ['C7R-GD2-B7H3'],
      aliases: ['Dual CAR-T GD2/B7-H3'],
      target: 'B7-H3 + GD2',
      modality: 'CAR-T',
      modalityDetail: 'Dual-targeting CAR-T (GD2 + B7-H3) with C7R cytokine support',
      owner: 'Baylor College of Medicine',
      ownerType: 'Academic',
      phase: 'Phase 1',
      status: 'Active',
      leadIndication: 'Neuroblastoma',
      otherIndications: ['Pediatric solid tumors'],
      regulatory: { btd: false, odd: true, fastTrack: false, prime: false },
      trialIds: ['NCT04897321'],
      notes: 'Dual targeting to prevent antigen escape.',
      differentiator: 'Dual targeting; cytokine armored',
    },

    // ========== Combinations ==========
    {
      primaryName: 'DS-7300 + Pembrolizumab',
      codeNames: ['I-DXd + Keytruda'],
      aliases: ['DS-7300 + pembro', 'I-DXd + pembrolizumab'],
      target: 'B7-H3',
      modality: 'ADC',
      modalityDetail: 'B7-H3 ADC + PD-1 combination',
      owner: 'Daiichi Sankyo',
      ownerType: 'Big Pharma',
      partner: 'Merck',
      phase: 'Phase 3',
      status: 'Active',
      leadIndication: 'NSCLC',
      otherIndications: ['ES-SCLC'],
      regulatory: { btd: false, odd: false, fastTrack: true, prime: false },
      trialIds: ['NCT05280470'],
      keyData: 'Pivotal combination study in lung cancer',
      notes: 'Key combination strategy under Merck partnership.',
      differentiator: 'IO combination; Merck partnership',
    },
    {
      primaryName: 'Enoblituzumab + Retifanlimab',
      codeNames: ['MGA271 + INCMGA00012'],
      aliases: ['enoblituzumab combo', 'MGA271 combo'],
      target: 'B7-H3',
      modality: 'mAb',
      modalityDetail: 'B7-H3 mAb + PD-1 combination',
      owner: 'MacroGenics',
      ownerType: 'Biotech',
      phase: 'Phase 2',
      status: 'Active',
      leadIndication: 'HNSCC',
      regulatory: { btd: false, odd: false, fastTrack: false, prime: false },
      trialIds: ['NCT02475213'],
      notes: 'B7-H3 mAb combined with PD-1 inhibitor.',
      differentiator: 'IO combination approach',
    },
  ],

  excludedDrugs: [
    // Generic chemotherapy
    'cyclophosphamide', 'fludarabine', 'bendamustine', 'temozolomide',
    'cisplatin', 'carboplatin', 'oxaliplatin', 'etoposide', 'irinotecan',
    'docetaxel', 'paclitaxel', 'gemcitabine', 'pemetrexed', 'vinblastine',
    'doxorubicin', 'epirubicin', 'methotrexate', 'cytarabine', 'azacitidine',
    'capecitabine', 'vinorelbine', 'topotecan', 'vincristine',

    // Standard checkpoint inhibitors
    'pembrolizumab', 'nivolumab', 'atezolizumab', 'durvalumab', 'avelumab',
    'ipilimumab', 'tremelimumab', 'cemiplimab', 'dostarlimab', 'retifanlimab',

    // Supportive care
    'dexamethasone', 'prednisone', 'methylprednisolone', 'hydrocortisone',
    'ondansetron', 'granisetron', 'palonosetron', 'aprepitant',
    'filgrastim', 'pegfilgrastim', 'epoetin', 'darbepoetin',

    // Other common trial drugs
    'placebo', 'standard of care', 'best supportive care',
    'leucovorin', 'mesna', 'zoledronic acid',
  ],

  excludedSponsors: [],
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
// Investment Metrics Calculation
// ============================================

export interface InvestmentMetrics {
  totalDisclosedDealValue: number;      // in billions
  totalUpfront: number;                 // in millions
  largestDeal: { name: string; value: string };
  assetsWithBTD: number;
  assetsWithODD: number;
  assetsWithPRIME: number;
  assetsWithFastTrack: number;
  phaseDistribution: Record<string, number>;
  modalityBreakdown: Record<string, { count: number; dealValue: number }>;
  ownershipBreakdown: Record<string, number>;
  totalAssets: number;
  curatedAssets: number;
}

/**
 * Calculate investment metrics for a set of assets
 */
export function calculateInvestmentMetrics(assets: KnownAsset[]): InvestmentMetrics {
  let totalDealValue = 0;
  let totalUpfront = 0;
  let largestDeal = { name: '', value: '', numericValue: 0 };

  const phaseDistribution: Record<string, number> = {};
  const modalityBreakdown: Record<string, { count: number; dealValue: number }> = {};
  const ownershipBreakdown: Record<string, number> = {};

  let btdCount = 0, oddCount = 0, primeCount = 0, fastTrackCount = 0;

  for (const asset of assets) {
    // Count regulatory designations
    if (asset.regulatory.btd) btdCount++;
    if (asset.regulatory.odd) oddCount++;
    if (asset.regulatory.prime) primeCount++;
    if (asset.regulatory.fastTrack) fastTrackCount++;

    // Phase distribution
    phaseDistribution[asset.phase] = (phaseDistribution[asset.phase] || 0) + 1;

    // Ownership
    ownershipBreakdown[asset.ownerType] = (ownershipBreakdown[asset.ownerType] || 0) + 1;

    // Modality
    if (!modalityBreakdown[asset.modality]) {
      modalityBreakdown[asset.modality] = { count: 0, dealValue: 0 };
    }
    modalityBreakdown[asset.modality].count++;

    // Deal value parsing
    if (asset.deal?.totalValue) {
      const dealNum = parseDealValue(asset.deal.totalValue);
      if (dealNum > 0) {
        totalDealValue += dealNum;
        modalityBreakdown[asset.modality].dealValue += dealNum;

        if (dealNum > largestDeal.numericValue) {
          largestDeal = {
            name: asset.primaryName,
            value: asset.deal.totalValue,
            numericValue: dealNum
          };
        }
      }
    }

    if (asset.deal?.upfront) {
      const upfrontNum = parseDealValue(asset.deal.upfront);
      if (upfrontNum > 0) {
        totalUpfront += upfrontNum;
      }
    }
  }

  return {
    totalDisclosedDealValue: totalDealValue / 1000, // Convert to billions
    totalUpfront: totalUpfront,
    largestDeal: { name: largestDeal.name, value: largestDeal.value },
    assetsWithBTD: btdCount,
    assetsWithODD: oddCount,
    assetsWithPRIME: primeCount,
    assetsWithFastTrack: fastTrackCount,
    phaseDistribution,
    modalityBreakdown,
    ownershipBreakdown,
    totalAssets: assets.length,
    curatedAssets: assets.length,
  };
}

/**
 * Parse deal value string to numeric (in millions)
 */
function parseDealValue(value: string): number {
  if (!value) return 0;

  const cleanValue = value.toLowerCase().replace(/[,$]/g, '');

  // Handle "XXB" or "XX billion"
  const billionMatch = cleanValue.match(/([\d.]+)\s*b/);
  if (billionMatch) {
    return parseFloat(billionMatch[1]) * 1000;
  }

  // Handle "XXM" or "XX million"
  const millionMatch = cleanValue.match(/([\d.]+)\s*m/);
  if (millionMatch) {
    return parseFloat(millionMatch[1]);
  }

  // Handle RMB values
  const rmbMatch = cleanValue.match(/([\d.]+)\s*rmb/);
  if (rmbMatch) {
    return parseFloat(rmbMatch[1]) * 0.14; // Rough RMB to USD conversion
  }

  return 0;
}

// ============================================
// Lookup Functions
// ============================================

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

export function findKnownAsset(name: string, target?: string): KnownAsset | null {
  const normalizedName = name.toLowerCase().replace(/[-\s]/g, '');

  const databases = target
    ? [getTargetDatabase(target)].filter(Boolean) as TargetAssetDatabase[]
    : Object.values(TARGET_DATABASES);

  for (const db of databases) {
    for (const asset of db.assets) {
      if (asset.primaryName.toLowerCase().replace(/[-\s]/g, '') === normalizedName) return asset;
      if (asset.genericName?.toLowerCase().replace(/[-\s]/g, '') === normalizedName) return asset;
      if (asset.codeNames.some(c => c.toLowerCase().replace(/[-\s]/g, '') === normalizedName)) return asset;
      if (asset.aliases.some(a => a.toLowerCase().replace(/[-\s]/g, '') === normalizedName)) return asset;
    }
  }

  return null;
}

export function isExcludedDrug(name: string, target?: string): boolean {
  const normalizedName = name.toLowerCase().trim();
  const db = target ? getTargetDatabase(target) : null;
  const excludedDrugs = db?.excludedDrugs || B7H3_DATABASE.excludedDrugs;

  return excludedDrugs.some(excluded =>
    normalizedName.includes(excluded.toLowerCase()) ||
    excluded.toLowerCase().includes(normalizedName)
  );
}

export function getKnownAssetsForTarget(target: string): KnownAsset[] {
  const db = getTargetDatabase(target);
  return db?.assets || [];
}

export function isTargetRelatedIntervention(
  interventionName: string,
  interventionDescription: string | undefined,
  target: string
): boolean {
  const db = getTargetDatabase(target);
  if (!db) return false;

  const searchText = `${interventionName} ${interventionDescription || ''}`.toLowerCase();
  const targetAliases = [db.target.toLowerCase(), ...db.aliases.map(a => a.toLowerCase())];

  for (const alias of targetAliases) {
    if (searchText.includes(alias.replace(/-/g, ''))) return true;
    if (searchText.includes(alias)) return true;
  }

  const knownAsset = findKnownAsset(interventionName, target);
  if (knownAsset) return true;

  return false;
}
