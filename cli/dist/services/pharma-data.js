"use strict";
/**
 * Pharma Data Service
 *
 * Proof-of-concept data for Merck (MRK) based on JPM 2026 presentation.
 * Provides pharma profile lookups, pipeline comparisons, BD fit analysis,
 * and catalyst tracking.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getPharmaProfile = getPharmaProfile;
exports.getAllPharmaSummary = getAllPharmaSummary;
exports.comparePipelines = comparePipelines;
exports.analyzeBDFit = analyzeBDFit;
exports.getUpcomingCatalysts = getUpcomingCatalysts;
const pharma_registry_1 = require("./pharma-registry");
// ============================================
// Merck JPM 2026 Pipeline Data
// ============================================
const MERCK_PIPELINE = [
    {
        drugName: 'KEYTRUDA',
        genericName: 'pembrolizumab',
        mechanism: 'PD-1 inhibitor',
        modality: 'Monoclonal antibody',
        phase: 4,
        indication: 'Multiple solid tumors (40+ approved indications)',
        therapeuticArea: 'Oncology',
        isPriority: true,
        peakRevenuePotential: '$25B+ (current franchise)',
        notes: 'LOE expected 2028; subcutaneous formulation in development to extend lifecycle',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'MK-1484',
        genericName: 'favezelimab',
        mechanism: 'LAG-3 inhibitor',
        modality: 'Monoclonal antibody',
        phase: 3,
        indication: 'Colorectal cancer (MSS-CRC)',
        therapeuticArea: 'Oncology',
        partner: undefined,
        expectedReadout: '2026 H2',
        isPriority: true,
        peakRevenuePotential: '$3-5B',
        notes: 'Key KEYTRUDA successor; combo with pembrolizumab',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'MK-7684A',
        genericName: 'vibostolimab + pembrolizumab',
        mechanism: 'TIGIT inhibitor + PD-1 inhibitor',
        modality: 'Fixed-dose combination',
        phase: 3,
        indication: 'NSCLC, melanoma',
        therapeuticArea: 'Oncology',
        expectedReadout: '2026 H1',
        isPriority: true,
        peakRevenuePotential: '$4-6B',
        notes: 'Multiple Phase 3 studies ongoing',
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
        isPriority: true,
        peakRevenuePotential: '$5-7B',
        notes: 'Approved March 2024; best-in-class PAH therapy; rapid uptake',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'MK-0616',
        mechanism: 'Oral PCSK9 inhibitor',
        modality: 'Small molecule (oral peptide)',
        phase: 3,
        indication: 'Hypercholesterolemia / ASCVD',
        therapeuticArea: 'Cardiovascular',
        expectedReadout: '2026 H2',
        isPriority: true,
        peakRevenuePotential: '$4-6B',
        notes: 'First oral PCSK9; could transform lipid management',
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
        isPriority: false,
        notes: 'Differentiated mechanism; adjunctive therapy',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'LAGEVRIO',
        genericName: 'molnupiravir',
        mechanism: 'RNA polymerase inhibitor (lethal mutagenesis)',
        modality: 'Small molecule (oral antiviral)',
        phase: 4,
        indication: 'COVID-19',
        therapeuticArea: 'Infectious Disease',
        isPriority: false,
        notes: 'Revenue declining; pandemic tailwind over',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'V116',
        mechanism: 'Pneumococcal conjugate vaccine (21-valent)',
        modality: 'Vaccine',
        phase: 3,
        indication: 'Pneumococcal disease in adults',
        therapeuticArea: 'Vaccines',
        expectedApproval: '2026',
        isPriority: true,
        peakRevenuePotential: '$2-4B',
        notes: 'Adult-specific PCV; PNEU-AGE Phase 3 positive',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'MK-1654',
        genericName: 'clesrovimab',
        mechanism: 'RSV F-protein inhibitor',
        modality: 'Monoclonal antibody',
        phase: 3,
        indication: 'RSV prevention in infants',
        therapeuticArea: 'Infectious Disease',
        expectedReadout: '2026 H1',
        isPriority: true,
        peakRevenuePotential: '$2-3B',
        notes: 'Extended half-life; single dose for full RSV season',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
    {
        drugName: 'Patritumab deruxtecan',
        mechanism: 'HER3-directed ADC',
        modality: 'Antibody-drug conjugate',
        phase: 3,
        indication: 'NSCLC (EGFR-mutant)',
        therapeuticArea: 'Oncology',
        partner: 'Daiichi Sankyo',
        expectedReadout: '2026',
        isPriority: true,
        peakRevenuePotential: '$3-5B',
        notes: 'Part of $22B Daiichi Sankyo ADC collaboration',
        source: 'Merck JPM 2026 Presentation',
        extractedAt: '2026-01-13',
    },
];
// ============================================
// Merck Catalysts
// ============================================
const MERCK_CATALYSTS = [
    {
        date: '2026-H1',
        dateType: 'half',
        eventType: 'phase3_readout',
        drugName: 'MK-7684A (vibostolimab + pembro)',
        indication: 'NSCLC 1L',
        description: 'Phase 3 KeyVibe-003 readout in first-line NSCLC',
        significance: 'high',
        source: 'Merck JPM 2026',
    },
    {
        date: '2026-H1',
        dateType: 'half',
        eventType: 'phase3_readout',
        drugName: 'MK-1654 (clesrovimab)',
        indication: 'RSV prevention in infants',
        description: 'Phase 3 readout for extended half-life RSV mAb',
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
        drugName: 'MK-0616 (oral PCSK9)',
        indication: 'Hypercholesterolemia',
        description: 'Phase 3 cardiovascular outcomes data for oral PCSK9 inhibitor',
        significance: 'high',
        source: 'Merck JPM 2026',
    },
    {
        date: '2026-H2',
        dateType: 'half',
        eventType: 'phase3_readout',
        drugName: 'MK-1484 (favezelimab)',
        indication: 'MSS-CRC',
        description: 'Phase 3 readout in microsatellite-stable colorectal cancer',
        significance: 'high',
        source: 'Merck JPM 2026',
    },
    {
        date: '2026',
        dateType: 'year',
        eventType: 'approval',
        drugName: 'V116 (21-valent PCV)',
        indication: 'Pneumococcal disease (adults)',
        description: 'Expected FDA approval for adult-specific pneumococcal vaccine',
        significance: 'high',
        source: 'Merck JPM 2026',
    },
    {
        date: '2026',
        dateType: 'year',
        eventType: 'phase3_readout',
        drugName: 'Patritumab deruxtecan',
        indication: 'EGFR-mutant NSCLC',
        description: 'Phase 3 HERTHENA-Lung02 in EGFR-mutant NSCLC',
        significance: 'high',
        source: 'Merck JPM 2026',
    },
];
// ============================================
// Merck Deals
// ============================================
const MERCK_DEALS = [
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
const MERCK_STRATEGY = {
    priorities: [
        'Navigate KEYTRUDA LOE (2028) with pipeline diversification',
        'Build next-generation oncology franchise (ADCs, bispecifics, IO combos)',
        'Grow cardiovascular portfolio (WINREVAIR, oral PCSK9)',
        'Expand vaccine franchise (V116, RSV)',
        'Maintain $10B+ annual BD investment pace',
    ],
    therapeuticFocus: [
        'Oncology (60%+ of pipeline)',
        'Cardiovascular/Metabolic',
        'Vaccines & Infectious Disease',
        'Neuroscience (selective)',
    ],
    modalityInvestments: [
        'Antibody-drug conjugates (ADCs)',
        'Bispecific antibodies',
        'Immuno-oncology combinations',
        'Oral biologics',
        'mRNA (next-gen vaccines)',
    ],
    whitespaceAreas: [
        'Autoimmune/inflammation (no current franchise)',
        'CNS beyond schizophrenia',
        'Cell & gene therapy',
        'Obesity/metabolic',
        'Radiopharmaceuticals',
    ],
    bdAppetite: {
        highInterest: [
            'Late-stage oncology assets (especially ADCs, bispecifics)',
            'Cardiovascular/metabolic with large patient populations',
            'Differentiated vaccines',
            'IO-combinable agents',
        ],
        moderateInterest: [
            'Early-stage oncology platforms',
            'Autoimmune/inflammation assets',
            'Neuroscience (differentiated mechanisms)',
        ],
        lowInterest: [
            'Rare disease (small markets)',
            'Gene therapy (manufacturing complexity)',
            'Biosimilars',
        ],
    },
    keyQuotes: [
        {
            quote: 'We are building a pipeline that can more than offset the KEYTRUDA LOE and deliver sustained growth through the end of the decade.',
            speaker: 'Robert Davis, CEO',
            context: 'JPM 2026 Healthcare Conference',
        },
        {
            quote: 'Our $22 billion Daiichi Sankyo collaboration represents the largest biopharma deal of 2023 and gives us access to the most validated ADC platform in oncology.',
            speaker: 'Dean Li, President of Merck Research Labs',
            context: 'JPM 2026 R&D Overview',
        },
    ],
    source: 'Merck JPM 2026 Presentation',
    extractedAt: '2026-01-13',
};
// ============================================
// Merck Revenue Opportunities
// ============================================
const MERCK_REVENUE_OPPS = [
    {
        therapeuticArea: 'Oncology (IO combos & ADCs)',
        targetYear: '2030',
        revenueEstimate: '$20-25B',
        riskAdjusted: false,
        keyAssets: ['MK-7684A', 'Patritumab deruxtecan', 'MK-1484', 'KEYTRUDA subQ'],
        source: 'Merck JPM 2026',
    },
    {
        therapeuticArea: 'Cardiovascular',
        targetYear: '2030',
        revenueEstimate: '$10-12B',
        riskAdjusted: false,
        keyAssets: ['WINREVAIR', 'MK-0616'],
        source: 'Merck JPM 2026',
    },
    {
        therapeuticArea: 'Vaccines',
        targetYear: '2030',
        revenueEstimate: '$12-14B',
        riskAdjusted: false,
        keyAssets: ['GARDASIL', 'V116', 'MK-1654', 'VAXNEUVANCE'],
        source: 'Merck JPM 2026',
    },
    {
        therapeuticArea: 'Total Company',
        targetYear: '2030',
        revenueEstimate: '$55-65B',
        riskAdjusted: false,
        keyAssets: ['Diversified portfolio'],
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
function computePipelineStats(pipeline) {
    const byPhase = {};
    const byTherapeuticArea = {};
    const byModality = {};
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
function getPharmaProfile(ticker) {
    const key = ticker.toUpperCase();
    const company = pharma_registry_1.PHARMA_COMPANIES[key];
    if (!company)
        return null;
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
function getAllPharmaSummary() {
    return Object.values(pharma_registry_1.PHARMA_COMPANIES).map((c) => {
        const profile = getPharmaProfile(c.ticker);
        return {
            ticker: c.ticker,
            name: c.name,
            verified: c.verified,
            hasData: (profile?.pipeline.length ?? 0) > 0,
            pipelineCount: profile?.pipeline.length ?? 0,
        };
    });
}
/**
 * Compare pipeline stats between two companies
 */
function comparePipelines(tickerA, tickerB) {
    const profileA = getPharmaProfile(tickerA);
    const profileB = getPharmaProfile(tickerB);
    if (!profileA || !profileB)
        return null;
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
function analyzeBDFit(targetTicker, assetTherapeuticArea, assetModality) {
    const profile = getPharmaProfile(targetTicker);
    if (!profile)
        return null;
    const rationale = [];
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
    if (strategy.bdAppetite.highInterest.some((h) => h.toLowerCase().includes(assetTherapeuticArea.toLowerCase()))) {
        score += 3;
        rationale.push(`High BD interest in ${assetTherapeuticArea}`);
    }
    else if (strategy.bdAppetite.moderateInterest.some((m) => m.toLowerCase().includes(assetTherapeuticArea.toLowerCase()))) {
        score += 1;
        rationale.push(`Moderate BD interest in ${assetTherapeuticArea}`);
    }
    else if (strategy.bdAppetite.lowInterest.some((l) => l.toLowerCase().includes(assetTherapeuticArea.toLowerCase()))) {
        score -= 1;
        rationale.push(`Low BD interest in ${assetTherapeuticArea}`);
    }
    if (rationale.length === 0) {
        rationale.push('Insufficient strategy data to assess fit');
    }
    let fitScore;
    if (score >= 5)
        fitScore = 'high';
    else if (score >= 2)
        fitScore = 'medium';
    else if (rationale.length > 0 && score >= 0)
        fitScore = 'low';
    else
        fitScore = 'unknown';
    return {
        targetCompany: profile.company.name,
        fitScore,
        rationale,
    };
}
/**
 * Get upcoming catalysts across all companies (or for a specific ticker)
 */
function getUpcomingCatalysts(ticker) {
    if (ticker) {
        const profile = getPharmaProfile(ticker);
        return profile?.catalysts ?? [];
    }
    // Aggregate from all companies
    const all = [];
    for (const key of Object.keys(pharma_registry_1.PHARMA_COMPANIES)) {
        const profile = getPharmaProfile(key);
        if (profile) {
            all.push(...profile.catalysts);
        }
    }
    return all;
}
//# sourceMappingURL=pharma-data.js.map