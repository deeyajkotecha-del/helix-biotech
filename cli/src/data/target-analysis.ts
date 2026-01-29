/**
 * Target-Level Investment Analysis
 *
 * Contains investment thesis, market opportunity, risks, and catalysts
 * for each therapeutic target. This data is used in Excel exports and HTML reports.
 */

// ============================================
// Types
// ============================================

export interface EfficacyDataPoint {
  drug: string;
  trial: string;
  nctId?: string;
  phase: string;
  dose: string;
  endpoint: string;
  result: number;           // e.g., 47.8 for 47.8%
  placebo: number;          // e.g., 20.4 for 20.4%
  placeboAdjusted: number;  // result - placebo
  indication: string;
  population?: string;      // e.g., "biomarker-positive"
  timepoint?: string;       // e.g., "Week 14"
  source: string;           // Publication or conference
  notes?: string;
}

export interface DifferentiatorMatrix {
  drug: string;
  strategy: string;         // e.g., "Precision medicine", "Best efficacy"
  dosing: string;           // e.g., "Q4W SC", "Q12W SC"
  biomarker: string;        // e.g., "Yes (TL1A-high)", "No"
  halfLife: string;         // e.g., "14 days", "21 days"
  beyondIndication: string; // e.g., "SSc-ILD, RA", "IBD only"
  mechanism?: string;       // e.g., "Full TL1A neutralization"
  administration?: string;  // e.g., "SC", "IV"
}

export interface TargetAnalysis {
  target: string;
  aliases: string[];

  // Investment Thesis
  investmentThesis: {
    headline: string;         // One-line summary
    keyPoints: string[];      // 3-5 bullet points
    fullText: string;         // Detailed paragraph
  };

  // Mechanism
  mechanism: {
    biology: string;          // How the target works
    rationale: string;        // Why blocking it helps
    uniqueValue: string;      // What makes this target special
  };

  // Market
  marketOpportunity: {
    totalMarket: string;      // e.g., "$25B IBD market"
    targetShare: string;      // e.g., "$8-10B peak potential"
    patientPopulation: string;
    unmetNeed: string;
  };

  // Risks
  keyRisks: Array<{
    risk: string;
    severity: 'High' | 'Medium' | 'Low';
    mitigation?: string;
  }>;

  // Catalysts
  catalystsToWatch: Array<{
    event: string;
    timing: string;
    drug: string;
    significance: 'High' | 'Medium' | 'Low';
  }>;

  // Efficacy Comparison
  efficacyComparison: EfficacyDataPoint[];

  // Competitive Differentiation
  differentiators: DifferentiatorMatrix[];

  // Metadata
  lastUpdated: string;
  analyst?: string;
}

// ============================================
// TL1A Target Analysis
// ============================================

export const TL1A_ANALYSIS: TargetAnalysis = {
  target: 'TL1A',
  aliases: ['TNFSF15', 'TL-1A', 'VEGI'],

  investmentThesis: {
    headline: 'TL1A is the hottest target in IBD with $22B+ in deal activity and dual inflammation/fibrosis mechanism',
    keyPoints: [
      'Genetic validation: TNFSF15 variants associated with IBD risk in GWAS studies',
      'Dual mechanism: Blocks both inflammation AND fibrosis progression',
      'Massive M&A: Merck ($10.8B for Prometheus), Roche ($7.25B for Telavant)',
      'Three Phase 3 assets racing: tulisokibart, duvakitug, afimkibart',
      'Best-in-class potential: Some programs showing 25-30% placebo-adjusted remission',
    ],
    fullText: `TL1A (TNF-like ligand 1A, encoded by TNFSF15) represents the most significant new target in IBD
since the advent of anti-TNF biologics. The target is genetically validated through GWAS studies showing
TNFSF15 variants are associated with Crohn's disease risk. Unlike existing therapies that only address
inflammation, TL1A inhibition blocks BOTH inflammatory cytokine production AND intestinal fibrosis -
addressing the key unmet need of stricturing/fistulizing disease.

The investment landscape is unprecedented: Merck acquired Prometheus for $10.8B (April 2023) solely for
tulisokibart, and Roche acquired Telavant for $7.25B (October 2023) for afimkibart. Combined with Sanofi's
TEV-48574 partnership and internal programs at Pfizer, AbbVie, and others, over $22B has been committed
to TL1A development.

Phase 2 data across multiple programs show 20-30% placebo-adjusted clinical remission rates, which would
be competitive with or superior to existing advanced therapies. The race to market is on, with Phase 3
readouts expected in 2025-2026.`,
  },

  mechanism: {
    biology: 'TL1A is a TNF superfamily cytokine that binds DR3 (death receptor 3), promoting Th1/Th17 differentiation, inflammatory cytokine production, and activation of fibroblasts leading to intestinal fibrosis.',
    rationale: 'Blocking TL1A interrupts both the inflammatory cascade (via reduced Th1/Th17 activity) and the fibrotic pathway (via reduced fibroblast activation), addressing the two key drivers of IBD progression.',
    uniqueValue: 'TL1A is the only validated target that addresses both inflammation AND fibrosis. Existing therapies (anti-TNF, anti-IL-23, JAKi) only target inflammation, leaving fibrosis/strictures unaddressed.',
  },

  marketOpportunity: {
    totalMarket: '$25B global IBD market (2024), growing to $35B by 2030',
    targetShare: '$8-12B peak revenue potential for best-in-class TL1A inhibitor',
    patientPopulation: '3.5M patients in US/EU with IBD; ~40% inadequate response to current therapies',
    unmetNeed: 'No approved therapy prevents or reverses intestinal fibrosis; 30-50% of Crohn\'s patients develop strictures requiring surgery',
  },

  keyRisks: [
    {
      risk: 'Crowded competitive landscape with 3+ Phase 3 assets',
      severity: 'High',
      mitigation: 'Differentiation through precision medicine (biomarker selection) or best-in-class efficacy',
    },
    {
      risk: 'Cross-trial comparison challenges make differentiation unclear',
      severity: 'Medium',
      mitigation: 'Phase 3 data will clarify; some head-to-head studies possible',
    },
    {
      risk: 'Safety signals in large trials could derail class',
      severity: 'Medium',
      mitigation: 'Phase 2 data shows clean safety profiles across programs',
    },
    {
      risk: 'Payer resistance if efficacy not clearly differentiated',
      severity: 'Medium',
      mitigation: 'Fibrosis benefit may provide unique value proposition',
    },
  ],

  catalystsToWatch: [
    {
      event: 'ARTEMIS-CD Phase 3 readout (Crohn\'s Disease)',
      timing: 'H2 2025',
      drug: 'Tulisokibart',
      significance: 'High',
    },
    {
      event: 'ARTEMIS-UC Phase 3 readout (Ulcerative Colitis)',
      timing: 'H1 2026',
      drug: 'Tulisokibart',
      significance: 'High',
    },
    {
      event: 'Phase 3 initiation in UC',
      timing: 'Q1 2025',
      drug: 'Duvakitug',
      significance: 'High',
    },
    {
      event: 'Phase 3 readout in UC',
      timing: '2026',
      drug: 'Afimkibart',
      significance: 'High',
    },
    {
      event: 'Phase 2 data in Crohn\'s Disease',
      timing: 'H2 2025',
      drug: 'Duvakitug',
      significance: 'Medium',
    },
  ],

  efficacyComparison: [
    {
      drug: 'Duvakitug (TEV-48574)',
      trial: 'RELIEVE UCCD',
      nctId: 'NCT05774587',
      phase: 'Phase 2',
      dose: '1000mg Q4W',
      endpoint: 'Clinical Remission',
      result: 47.8,
      placebo: 20.4,
      placeboAdjusted: 27.4,
      indication: 'Ulcerative Colitis',
      timepoint: 'Week 14',
      source: 'DDW 2024',
      notes: 'Highest placebo-adjusted remission rate reported',
    },
    {
      drug: 'Duvakitug (TEV-48574)',
      trial: 'RELIEVE UCCD',
      nctId: 'NCT05774587',
      phase: 'Phase 2',
      dose: '500mg Q4W',
      endpoint: 'Clinical Remission',
      result: 32.6,
      placebo: 20.4,
      placeboAdjusted: 12.2,
      indication: 'Ulcerative Colitis',
      timepoint: 'Week 14',
      source: 'DDW 2024',
    },
    {
      drug: 'Tulisokibart (PRA023)',
      trial: 'ARTEMIS-UC',
      nctId: 'NCT05499130',
      phase: 'Phase 2b',
      dose: '1000mg → 500mg Q4W',
      endpoint: 'Clinical Remission',
      result: 26,
      placebo: 1,
      placeboAdjusted: 25,
      indication: 'Ulcerative Colitis',
      population: 'TL1A-high biomarker positive',
      timepoint: 'Week 12',
      source: 'NEJM 2024',
      notes: 'Precision medicine approach; patients selected by TL1A biomarker',
    },
    {
      drug: 'Tulisokibart (PRA023)',
      trial: 'ARTEMIS-UC',
      nctId: 'NCT05499130',
      phase: 'Phase 2b',
      dose: '1000mg → 500mg Q4W',
      endpoint: 'Endoscopic Improvement',
      result: 49,
      placebo: 13,
      placeboAdjusted: 36,
      indication: 'Ulcerative Colitis',
      population: 'TL1A-high biomarker positive',
      timepoint: 'Week 12',
      source: 'NEJM 2024',
    },
    {
      drug: 'Afimkibart (RVT-3101)',
      trial: 'Phase 2',
      nctId: 'NCT05668039',
      phase: 'Phase 2',
      dose: '150mg Q4W',
      endpoint: 'Clinical Response',
      result: 70,
      placebo: 35,
      placeboAdjusted: 35,
      indication: 'Ulcerative Colitis',
      timepoint: 'Week 14',
      source: 'ACG 2023',
    },
    {
      drug: 'Afimkibart (RVT-3101)',
      trial: 'Phase 2',
      nctId: 'NCT05668039',
      phase: 'Phase 2',
      dose: '150mg Q4W',
      endpoint: 'Clinical Remission',
      result: 35,
      placebo: 12,
      placeboAdjusted: 23,
      indication: 'Ulcerative Colitis',
      timepoint: 'Week 14',
      source: 'ACG 2023',
    },
  ],

  differentiators: [
    {
      drug: 'Tulisokibart (PRA023)',
      strategy: 'Precision medicine',
      dosing: '1000mg → 500mg Q4W SC',
      biomarker: 'Yes (TL1A-high)',
      halfLife: '~14 days',
      beyondIndication: 'SSc-ILD, RA explored',
      mechanism: 'Full TL1A neutralization',
      administration: 'SC',
    },
    {
      drug: 'Duvakitug (TEV-48574)',
      strategy: 'Best-in-class efficacy',
      dosing: '500-1000mg Q4W SC',
      biomarker: 'No',
      halfLife: '~21 days',
      beyondIndication: 'IBD only',
      mechanism: 'Full TL1A neutralization',
      administration: 'SC',
    },
    {
      drug: 'Afimkibart (RVT-3101)',
      strategy: 'Multi-indication expansion',
      dosing: '150mg Q4W SC',
      biomarker: 'No',
      halfLife: '~14 days',
      beyondIndication: 'AD, MASH, Celiac potential',
      mechanism: 'Full TL1A neutralization',
      administration: 'SC',
    },
    {
      drug: 'SAR443765 (Bispecific)',
      strategy: 'Dual-target synergy',
      dosing: 'TBD',
      biomarker: 'No',
      halfLife: 'TBD',
      beyondIndication: 'IBD focus',
      mechanism: 'TL1A + IL-23 blockade',
      administration: 'SC',
    },
  ],

  lastUpdated: '2024-01',
  analyst: 'Satya Bio',
};

// ============================================
// B7-H3 Target Analysis
// ============================================

export const B7H3_ANALYSIS: TargetAnalysis = {
  target: 'B7-H3',
  aliases: ['CD276', 'B7H3'],

  investmentThesis: {
    headline: 'B7-H3 is the leading next-gen ADC target with $22B Merck deal and limited normal tissue expression',
    keyPoints: [
      'Ideal ADC target: High tumor expression, minimal normal tissue expression',
      'Merck mega-deal: $22B collaboration with Daiichi Sankyo for I-DXd',
      'Multiple modalities: ADCs, CAR-T, bispecifics, radioconjugates all in development',
      'Best clinical data: 52% ORR in ES-SCLC with ifinatamab deruxtecan',
      'Regulatory momentum: BTD and ODD designations for lead programs',
    ],
    fullText: `B7-H3 (CD276) is emerging as the premier target for next-generation oncology therapeutics,
particularly antibody-drug conjugates. The immune checkpoint protein is highly expressed across multiple
solid tumors (lung, prostate, breast, pediatric cancers) while showing minimal expression on normal tissues -
making it an ideal target for cytotoxic payloads.

The Merck-Daiichi Sankyo $22B collaboration (October 2023) represents the largest ADC deal in history,
validating the target's commercial potential. Lead asset ifinatamab deruxtecan (I-DXd, DS-7300) has shown
impressive efficacy with 52% ORR in extensive-stage small cell lung cancer and is advancing through
registrational trials.

The competitive landscape includes multiple modalities: ADCs from GSK, BioNTech, and Chinese biotechs;
CAR-T programs from academic centers; bispecifics from MacroGenics; and the only approved radioconjugate
omburtamab for CNS tumors. This diversity suggests confidence in the target across the industry.`,
  },

  mechanism: {
    biology: 'B7-H3 is an immune checkpoint protein that inhibits T-cell activation and promotes tumor immune evasion. It is overexpressed in >70% of solid tumors.',
    rationale: 'High tumor expression + low normal tissue expression = ideal therapeutic window for ADCs. The DXd payload has proven efficacy with Enhertu.',
    uniqueValue: 'Unlike PD-L1 or HER2, B7-H3 is broadly expressed across tumor types with minimal toxicity concerns.',
  },

  marketOpportunity: {
    totalMarket: '$80B+ oncology biologics market',
    targetShare: '$5-10B peak revenue potential for best-in-class B7-H3 ADC',
    patientPopulation: 'Broad applicability: SCLC, NSCLC, prostate, breast, pediatric tumors',
    unmetNeed: 'ES-SCLC has no targeted therapies; 2L+ solid tumors need new options',
  },

  keyRisks: [
    {
      risk: 'Competition from other ADC targets (TROP2, HER3, etc.)',
      severity: 'Medium',
      mitigation: 'B7-H3 expression is broader and more consistent than alternatives',
    },
    {
      risk: 'Merck/Daiichi dominance may crowd out other players',
      severity: 'High',
      mitigation: 'Differentiation through indication focus or modality',
    },
  ],

  catalystsToWatch: [
    {
      event: 'TROPION-Lung08 Phase 3 readout (NSCLC)',
      timing: 'H2 2025',
      drug: 'Ifinatamab deruxtecan',
      significance: 'High',
    },
    {
      event: 'Potential accelerated approval in ES-SCLC',
      timing: '2025',
      drug: 'Ifinatamab deruxtecan',
      significance: 'High',
    },
    {
      event: 'BLA decision for omburtamab (CNS tumors)',
      timing: '2024',
      drug: 'Omburtamab',
      significance: 'High',
    },
  ],

  efficacyComparison: [
    {
      drug: 'Ifinatamab deruxtecan (DS-7300)',
      trial: 'Phase 1/2',
      nctId: 'NCT04145622',
      phase: 'Phase 1/2',
      dose: '8 mg/kg Q3W',
      endpoint: 'ORR',
      result: 52,
      placebo: 0,
      placeboAdjusted: 52,
      indication: 'ES-SCLC',
      source: 'ASCO 2024',
      notes: 'Best-in-class response rate',
    },
    {
      drug: 'HS-20093 (GSK)',
      trial: 'Phase 1/2',
      nctId: 'NCT05276609',
      phase: 'Phase 1/2',
      dose: 'Dose escalation',
      endpoint: 'ORR',
      result: 75,
      placebo: 0,
      placeboAdjusted: 75,
      indication: 'ES-SCLC 2L+',
      source: 'WCLC 2023',
      notes: 'Impressive early data from Chinese program',
    },
  ],

  differentiators: [
    {
      drug: 'Ifinatamab deruxtecan',
      strategy: 'Platform leader',
      dosing: '8-16 mg/kg Q3W IV',
      biomarker: 'No',
      halfLife: '~6 days',
      beyondIndication: 'Pan-solid tumor',
      mechanism: 'DXd Topo I payload',
      administration: 'IV',
    },
    {
      drug: 'HS-20093',
      strategy: 'Fast follower',
      dosing: 'TBD',
      biomarker: 'No',
      halfLife: 'TBD',
      beyondIndication: 'Solid tumors',
      mechanism: 'Topo I payload',
      administration: 'IV',
    },
  ],

  lastUpdated: '2024-01',
  analyst: 'Satya Bio',
};

// ============================================
// Target Analysis Registry
// ============================================

export const TARGET_ANALYSES: Record<string, TargetAnalysis> = {
  'TL1A': TL1A_ANALYSIS,
  'TNFSF15': TL1A_ANALYSIS,
  'B7-H3': B7H3_ANALYSIS,
  'B7H3': B7H3_ANALYSIS,
  'CD276': B7H3_ANALYSIS,
};

export function getTargetAnalysis(target: string): TargetAnalysis | null {
  const normalized = target.toUpperCase().replace(/[-\s]/g, '');
  for (const [key, analysis] of Object.entries(TARGET_ANALYSES)) {
    if (key.toUpperCase().replace(/[-\s]/g, '') === normalized) {
      return analysis;
    }
  }
  return null;
}
