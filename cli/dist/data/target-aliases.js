"use strict";
/**
 * Target Aliases Database
 *
 * Comprehensive mapping of therapeutic targets to their aliases,
 * gene symbols, and common mechanism descriptions.
 *
 * Used for accurate asset verification - prevents false positives
 * by ensuring discovered drugs actually target the query target.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.COMMON_NON_TARGET_DRUGS = exports.TARGET_ALIASES = void 0;
exports.getTargetInfo = getTargetInfo;
exports.getTargetVariants = getTargetVariants;
exports.isCommonNonTargetDrug = isCommonNonTargetDrug;
exports.inferTargetInfo = inferTargetInfo;
// ============================================
// Target Database
// ============================================
exports.TARGET_ALIASES = {
    // ========== TL1A / TNFSF15 ==========
    'TL1A': {
        officialName: 'TL1A',
        aliases: ['TL1A', 'TL-1A', 'TNFSF15', 'VEGI', 'TNF-like ligand 1A'],
        geneSymbol: 'TNFSF15',
        uniprotId: 'O95150',
        commonMechanisms: [
            'anti-TL1A',
            'TL1A inhibitor',
            'TL1A antagonist',
            'TL1A antibody',
            'TL1A blocker',
            'TNFSF15 inhibitor',
            'TNFSF15 antibody',
        ],
        relatedTargets: ['IL-23', 'TNF'], // For bispecifics
    },
    // ========== B7-H3 / CD276 ==========
    'B7-H3': {
        officialName: 'B7-H3',
        aliases: ['B7-H3', 'B7H3', 'CD276', '4Ig-B7-H3'],
        geneSymbol: 'CD276',
        uniprotId: 'Q5ZPR3',
        commonMechanisms: [
            'anti-B7-H3',
            'B7-H3 ADC',
            'B7-H3 antibody',
            'B7-H3 CAR-T',
            'B7-H3 bispecific',
            'CD276 antibody',
            'CD276 ADC',
        ],
        relatedTargets: ['CD3', '4-1BB', 'GD2'], // For bispecifics
    },
    // ========== KRAS ==========
    'KRAS': {
        officialName: 'KRAS',
        aliases: ['KRAS', 'K-RAS', 'KRAS G12C', 'KRAS G12D', 'KRAS G12V', 'KRAS G12R'],
        geneSymbol: 'KRAS',
        uniprotId: 'P01116',
        commonMechanisms: [
            'KRAS inhibitor',
            'KRAS G12C inhibitor',
            'KRAS G12D inhibitor',
            'KRAS degrader',
            'KRAS blocker',
            'pan-KRAS',
        ],
    },
    // ========== HER2 / ERBB2 ==========
    'HER2': {
        officialName: 'HER2',
        aliases: ['HER2', 'HER-2', 'ERBB2', 'ErbB2', 'neu'],
        geneSymbol: 'ERBB2',
        uniprotId: 'P04626',
        commonMechanisms: [
            'anti-HER2',
            'HER2 ADC',
            'HER2 antibody',
            'HER2 bispecific',
            'trastuzumab',
            'pertuzumab',
        ],
    },
    // ========== PD-1 / PDCD1 ==========
    'PD-1': {
        officialName: 'PD-1',
        aliases: ['PD-1', 'PD1', 'PDCD1', 'CD279'],
        geneSymbol: 'PDCD1',
        uniprotId: 'Q15116',
        commonMechanisms: [
            'anti-PD-1',
            'PD-1 inhibitor',
            'PD-1 antibody',
            'PD-1 blocker',
        ],
    },
    // ========== PD-L1 / CD274 ==========
    'PD-L1': {
        officialName: 'PD-L1',
        aliases: ['PD-L1', 'PDL1', 'CD274', 'B7-H1'],
        geneSymbol: 'CD274',
        uniprotId: 'Q9NZQ7',
        commonMechanisms: [
            'anti-PD-L1',
            'PD-L1 inhibitor',
            'PD-L1 antibody',
        ],
    },
    // ========== TROP2 / TACSTD2 ==========
    'TROP2': {
        officialName: 'TROP2',
        aliases: ['TROP2', 'TROP-2', 'TACSTD2', 'EGP-1'],
        geneSymbol: 'TACSTD2',
        uniprotId: 'P09758',
        commonMechanisms: [
            'anti-TROP2',
            'TROP2 ADC',
            'TROP2 antibody',
            'sacituzumab',
            'datopotamab',
        ],
    },
    // ========== Claudin 18.2 ==========
    'CLDN18.2': {
        officialName: 'Claudin 18.2',
        aliases: ['CLDN18.2', 'Claudin 18.2', 'CLDN18', 'Claudin-18.2', 'Claudin18.2'],
        geneSymbol: 'CLDN18',
        uniprotId: 'P56856',
        commonMechanisms: [
            'anti-Claudin 18.2',
            'CLDN18.2 antibody',
            'Claudin 18.2 ADC',
            'CLDN18.2 CAR-T',
            'zolbetuximab',
        ],
    },
    // ========== EGFR ==========
    'EGFR': {
        officialName: 'EGFR',
        aliases: ['EGFR', 'ErbB1', 'HER1', 'EGFR exon 20'],
        geneSymbol: 'EGFR',
        uniprotId: 'P00533',
        commonMechanisms: [
            'anti-EGFR',
            'EGFR inhibitor',
            'EGFR TKI',
            'EGFR antibody',
            'EGFR ADC',
        ],
    },
    // ========== BCMA / TNFRSF17 ==========
    'BCMA': {
        officialName: 'BCMA',
        aliases: ['BCMA', 'TNFRSF17', 'CD269'],
        geneSymbol: 'TNFRSF17',
        uniprotId: 'Q02223',
        commonMechanisms: [
            'anti-BCMA',
            'BCMA CAR-T',
            'BCMA bispecific',
            'BCMA ADC',
            'BCMA antibody',
        ],
    },
    // ========== CD19 ==========
    'CD19': {
        officialName: 'CD19',
        aliases: ['CD19', 'B4'],
        geneSymbol: 'CD19',
        uniprotId: 'P15391',
        commonMechanisms: [
            'anti-CD19',
            'CD19 CAR-T',
            'CD19 bispecific',
            'CD19 antibody',
        ],
    },
    // ========== IL-23 ==========
    'IL-23': {
        officialName: 'IL-23',
        aliases: ['IL-23', 'IL23', 'interleukin-23', 'IL-23p19'],
        geneSymbol: 'IL23A',
        uniprotId: 'Q9NPF7',
        commonMechanisms: [
            'anti-IL-23',
            'IL-23 inhibitor',
            'IL-23 antibody',
            'IL-23p19 antibody',
        ],
    },
    // ========== IL-17 ==========
    'IL-17': {
        officialName: 'IL-17',
        aliases: ['IL-17', 'IL17', 'IL-17A', 'interleukin-17'],
        geneSymbol: 'IL17A',
        uniprotId: 'Q16552',
        commonMechanisms: [
            'anti-IL-17',
            'IL-17 inhibitor',
            'IL-17 antibody',
        ],
    },
    // ========== GLP-1 ==========
    'GLP-1': {
        officialName: 'GLP-1',
        aliases: [
            'GLP-1', 'GLP1', 'GLP-1R', 'GLP1R',
            'glucagon-like peptide-1', 'glucagon-like peptide 1',
            'incretin', 'GLP-1 receptor', 'GLP-1 agonist',
        ],
        geneSymbol: 'GLP1R',
        uniprotId: 'P43220',
        commonMechanisms: [
            'GLP-1 agonist',
            'GLP-1 receptor agonist',
            'GLP-1R agonist',
            'GLP-1 analog',
            'incretin mimetic',
            'dual GLP-1/GIP',
            'triple agonist',
            'GLP-1/GIP/glucagon',
        ],
        relatedTargets: ['GIP', 'GCGR', 'Amylin'],
    },
};
// ============================================
// Common Non-Target Drugs (Exclusion List)
// ============================================
/**
 * Drugs that commonly appear in clinical trials but are NOT
 * target-specific therapeutics. These should be EXCLUDED from
 * asset discovery unless they explicitly match the target.
 */
exports.COMMON_NON_TARGET_DRUGS = [
    // Chemotherapy
    'cyclophosphamide', 'fludarabine', 'bendamustine', 'temozolomide',
    'cisplatin', 'carboplatin', 'oxaliplatin', 'etoposide', 'irinotecan',
    'docetaxel', 'paclitaxel', 'nab-paclitaxel', 'gemcitabine', 'pemetrexed',
    'vinblastine', 'vincristine', 'vinorelbine', 'topotecan',
    'doxorubicin', 'epirubicin', 'methotrexate', 'cytarabine', 'azacitidine',
    'capecitabine', 'fluorouracil', '5-fu', 'leucovorin', 'ifosfamide',
    // Checkpoint inhibitors (exclude unless searching for PD-1/PD-L1/CTLA-4)
    'pembrolizumab', 'keytruda', 'nivolumab', 'opdivo',
    'atezolizumab', 'tecentriq', 'durvalumab', 'imfinzi',
    'avelumab', 'bavencio', 'cemiplimab', 'libtayo',
    'ipilimumab', 'yervoy', 'tremelimumab',
    'dostarlimab', 'jemperli', 'retifanlimab',
    // Steroids
    'prednisone', 'prednisolone', 'dexamethasone', 'methylprednisolone',
    'hydrocortisone', 'budesonide', 'cortisone',
    // Supportive care / anti-emetics
    'ondansetron', 'granisetron', 'palonosetron', 'aprepitant',
    'fosaprepitant', 'dronabinol', 'nabilone',
    // Growth factors
    'filgrastim', 'pegfilgrastim', 'neulasta', 'epoetin', 'darbepoetin',
    // Bisphosphonates
    'zoledronic acid', 'zometa', 'pamidronate', 'denosumab',
    // Other common trial drugs
    'placebo', 'standard of care', 'best supportive care',
    'mesna', 'allopurinol', 'rasburicase',
    // Common IBD drugs (exclude for IBD target searches)
    'mesalamine', 'sulfasalazine', 'balsalazide', 'olsalazine',
    'azathioprine', 'mercaptopurine', '6-mp', '6-mercaptopurine',
    // Common biologics (target-specific, exclude unless searching for that target)
    'infliximab', 'remicade', 'adalimumab', 'humira',
    'certolizumab', 'cimzia', 'golimumab', 'simponi',
    'vedolizumab', 'entyvio', 'ustekinumab', 'stelara',
    'risankizumab', 'skyrizi', 'mirikizumab', 'omvoh',
    'guselkumab', 'tremfya', 'secukinumab', 'cosentyx',
    'ixekizumab', 'taltz', 'brodalumab', 'siliq',
    // JAK inhibitors
    'tofacitinib', 'xeljanz', 'upadacitinib', 'rinvoq',
    'filgotinib', 'jyseleca', 'baricitinib', 'olumiant',
    // S1P modulators
    'ozanimod', 'zeposia', 'etrasimod', 'velsipity',
];
// ============================================
// Lookup Functions
// ============================================
/**
 * Get target info by name (case-insensitive, handles aliases)
 */
function getTargetInfo(target) {
    const normalized = target.toUpperCase().replace(/[-\s]/g, '');
    // Direct lookup
    for (const [key, info] of Object.entries(exports.TARGET_ALIASES)) {
        if (key.toUpperCase().replace(/[-\s]/g, '') === normalized) {
            return info;
        }
        // Check aliases
        for (const alias of info.aliases) {
            if (alias.toUpperCase().replace(/[-\s]/g, '') === normalized) {
                return info;
            }
        }
    }
    return null;
}
/**
 * Get all name variants for a target (for matching)
 */
function getTargetVariants(target) {
    const info = getTargetInfo(target);
    if (info) {
        return [...info.aliases, ...info.commonMechanisms];
    }
    // Fallback: generate basic variants
    return [
        target,
        target.replace(/-/g, ''),
        target.replace(/-/g, ' '),
        `anti-${target}`,
        `${target} inhibitor`,
        `${target} antibody`,
    ];
}
/**
 * Check if a drug name is in the common exclusion list
 */
function isCommonNonTargetDrug(drugName) {
    const normalized = drugName.toLowerCase().trim();
    return exports.COMMON_NON_TARGET_DRUGS.some(drug => {
        const drugLower = drug.toLowerCase();
        return normalized === drugLower ||
            normalized.includes(drugLower) ||
            drugLower.includes(normalized);
    });
}
/**
 * Infer target info for unknown targets
 */
function inferTargetInfo(target) {
    return {
        officialName: target,
        aliases: [
            target,
            target.replace(/-/g, ''),
            target.replace(/-/g, ' '),
        ],
        geneSymbol: target.toUpperCase().replace(/[-\s]/g, ''),
        commonMechanisms: [
            `anti-${target}`,
            `${target} inhibitor`,
            `${target} antibody`,
            `${target} antagonist`,
        ],
    };
}
//# sourceMappingURL=target-aliases.js.map