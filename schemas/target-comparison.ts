// ============================================================
// Universal Target Comparison Schema v0.4
// ============================================================
// Single source of truth: Zod schemas define the shape,
// TypeScript types are derived via z.infer. No parallel
// interfaces to drift out of sync.
//
// One shape for HCM, AD, NSCLC, or any future therapeutic area.
// The frontend renderer iterates arrays — no disease-specific
// code paths. Adding a new disease = filling in JSON + registering
// endpoints in the registry.
//
// v0.1: Core architecture — endpoint registry, self-describing results.
// v0.2: Investment reasoning — regulatory, statistical rigor, temporal.
// v0.3: Stress-tested against real data (EWTX HCM, KYMR AD, NUVL NSCLC).
//       Fixes: co-primaries, multi-arm trials, line of therapy,
//       assessment method, crossover, combination therapy, PD endpoints.
// v0.4: Zod-first rewrite (single source of truth), line_of_therapy
//       as union type, id fields on Comparator/Trial, optional
//       control_arm with conditional validation, display-only comments.
// ============================================================

import { z } from "zod";

// ============================================================
// Enum / union schemas
// ============================================================

export const EndpointClassSchema = z.enum(["primary", "secondary", "exploratory"]);
export type EndpointClass = z.infer<typeof EndpointClassSchema>;

export const OutcomeTypeSchema = z.enum(["surrogate", "clinical", "pro"]);
export type OutcomeType = z.infer<typeof OutcomeTypeSchema>;

// Closed union — intentional friction. Adding a disease area requires
// editing this list and reviewing what the new category means for the
// renderer. Revisit if this grows past 10+ entries.
//
// "pharmacodynamic" is distinct from "biomarker":
//   biomarker = disease measurement (NT-proBNP, TARC)
//   PD = target engagement proof (STAT6 degradation, SRX state shift)
//   For degrader platforms (KYMR) PD is THE primary proof of mechanism.
export const EndpointCategorySchema = z.enum([
  "cardiac_function",
  "functional_capacity",
  "patient_reported",
  "skin_clearance",
  "itch_severity",
  "tumor_response",
  "survival",
  "biomarker",
  "pharmacodynamic",
  "composite",
]);
export type EndpointCategory = z.infer<typeof EndpointCategorySchema>;

export const DisplayFormatSchema = z.enum(["number", "percentage", "months", "ratio"]);
export type DisplayFormat = z.infer<typeof DisplayFormatSchema>;

export const RouteOfAdministrationSchema = z.enum([
  "oral", "iv", "subq", "intrathecal", "topical", "inhaled",
]);
export type RouteOfAdministration = z.infer<typeof RouteOfAdministrationSchema>;

export const ApprovalStatusSchema = z.enum([
  "approved", "filed", "phase_3", "phase_2", "phase_1", "preclinical",
]);
export type ApprovalStatus = z.infer<typeof ApprovalStatusSchema>;

// Designations are additive — mavacamten had breakthrough + priority review.
export const RegulatoryDesignationSchema = z.enum([
  "breakthrough_therapy", "fast_track", "priority_review",
  "orphan_drug", "rare_pediatric", "regenerative_medicine",
]);
export type RegulatoryDesignation = z.infer<typeof RegulatoryDesignationSchema>;

export const RegulatoryPathwaySchema = z.enum([
  "standard",          // 10-month review
  "accelerated",       // surrogate endpoint, confirmatory trial required
  "priority",          // 6-month review
  "real_time_oncology_review",
]);
export type RegulatoryPathway = z.infer<typeof RegulatoryPathwaySchema>;

export const PrimaryEndpointStrategySchema = z.enum([
  "single",            // one primary endpoint
  "co_primary",        // ALL must hit (AD: EASI-75 AND vIGA 0/1)
  "hierarchical",      // test in order, gate on each (common in cardiology)
]);
export type PrimaryEndpointStrategy = z.infer<typeof PrimaryEndpointStrategySchema>;

export const TrialPhaseSchema = z.enum(["1", "1b", "2", "2b", "3", "4"]);
export type TrialPhase = z.infer<typeof TrialPhaseSchema>;

export const StudyDesignSchema = z.enum([
  "rct_double_blind", "rct_open_label", "single_arm",
  "crossover", "platform", "real_world",
]);
export type StudyDesign = z.infer<typeof StudyDesignSchema>;

export const AnalysisTypeSchema = z.enum([
  "final",             // pre-specified final analysis
  "interim",           // pre-specified interim look
  "post_hoc",          // unplanned analysis — treat as hypothesis-generating
]);
export type AnalysisType = z.infer<typeof AnalysisTypeSchema>;

export const ChangeTypeSchema = z.enum([
  "absolute_change",   // -36.2 mmHg
  "percent_change",    // -72.5%
  "responder_rate",    // 74.3% achieved EASI-75
  "hazard_ratio",      // 0.68 (PFS, OS)
  "median_time",       // 18.4 months (PFS, OS)
  "odds_ratio",
  "raw_value",         // baseline or absolute measurement
]);
export type ChangeType = z.infer<typeof ChangeTypeSchema>;

// DataMaturity = publication status, NOT analysis timing (that's AnalysisType).
export const DataMaturitySchema = z.enum([
  "peer_reviewed",             // published in journal
  "conference_presentation",   // ASH oral, ASCO poster
  "press_release",             // topline only
  "preclinical",
]);
export type DataMaturity = z.infer<typeof DataMaturitySchema>;

export const DataEventTypeSchema = z.enum([
  "topline_readout", "full_data_presentation", "publication",
  "regulatory_submission", "advisory_committee",
  "approval_decision", "label_update",
]);
export type DataEventType = z.infer<typeof DataEventTypeSchema>;

export const FormularyStatusSchema = z.enum([
  "preferred",         // broad unrestricted access
  "non_preferred",     // covered but with higher copay or step-through
  "restricted",        // prior auth, step therapy, or specialty pharmacy only
  "not_listed",        // not on major formularies
]);
export type FormularyStatus = z.infer<typeof FormularyStatusSchema>;

// v0.4: Union type instead of loose string. Prevents "1L" vs "first-line"
// vs "frontline" inconsistencies that break renderer grouping.
export const LineOfTherapySchema = z.enum([
  "1L", "2L", "3L+", "adjuvant", "neoadjuvant", "maintenance",
]);
export type LineOfTherapy = z.infer<typeof LineOfTherapySchema>;

// ============================================================
// Compound schemas
// ============================================================

// --- Endpoint registry entry ---
// Display config + investment-grade classification.
//
// Convention: endpoint_class on the registry represents the TYPICAL
// classification for this disease area's pivotal trials (e.g., LVOT
// gradient is always primary in HCM Phase 3s, EASI-75 is always
// co-primary in AD Phase 3s). This works because comparisons are
// within disease areas where hierarchies are stable.
//
// If a per-trial override is ever needed (e.g., an endpoint is primary
// in Phase 3 but exploratory in Phase 1b), add an optional
// endpoint_class_override field to EndpointResult at that time.
export const EndpointMetaSchema = z.object({
  label: z.string().min(1),                       // "LVOT Gradient Change", "EASI-75"
  category: EndpointCategorySchema,
  display_format: DisplayFormatSchema,
  sort_order: z.number().int(),                   // controls column/row order in the renderer
  higher_is_better: z.boolean(),                  // drives color coding (true for ORR, false for LVOT gradient)
  description: z.string().optional(),             // tooltip text

  // FDA hierarchy: primary miss with secondary hit ≠ trial success,
  // but Wall Street routinely misprices this.
  endpoint_class: EndpointClassSchema,

  // Surrogate vs clinical vs PRO determines approvability read-through.
  // A surrogate hit may not support full approval without confirmatory data.
  outcome_type: OutcomeTypeSchema,

  // Has FDA accepted this specific endpoint for approval in this indication?
  // true = strong regulatory precedent (e.g., ORR in oncology, LVOT gradient in oHCM).
  // false = novel or exploratory (e.g., serum biomarker as primary in early fibrosis).
  regulatory_precedent: z.boolean(),
});
export type EndpointMeta = z.infer<typeof EndpointMetaSchema>;

// --- Endpoint result ---
// Self-describing: carries its own ID, value, statistical context.
// The renderer looks up display hints from endpoint_registry[endpoint_id].
export const EndpointResultSchema = z.object({
  endpoint_id: z.string().min(1),                 // key into TargetComparison.endpoint_registry
  // Display-only string. Add timepoint_weeks: number when sort/filter is needed.
  timepoint: z.string().min(1),                   // "Week 30", "Month 12", "Median follow-up 18.4mo"

  // Multi-arm trial support. CIRRUS-HCM has 50mg and 100mg cohorts
  // with different results (43% vs 89%). BroADen has 100mg and 200mg.
  // For simple RCTs, arm = drug name or omit (single treatment arm).
  arm: z.string().optional(),                     // "EDG-7500 50mg", "KT-621 200mg"

  // Treatment arm
  value: z.number(),
  unit: z.string().min(1),                        // "mmHg", "%", "months", "ratio"
  change_type: ChangeTypeSchema,

  // Control arm (omitted for single-arm studies)
  control_value: z.number().optional(),
  delta: z.number().optional(),                   // treatment effect vs control

  // Assessment methodology. Handles:
  // - HCM: "resting" vs "post-Valsalva" LVOT gradient (same endpoint, different conditions)
  // - Oncology: "RECIST 1.1" vs "iRECIST" (response criteria version)
  // Without this, cross-trial comparison is misleading when methods differ.
  assessment_method: z.string().optional(),        // "resting", "post-Valsalva", "RECIST 1.1"

  // --- Statistics ---
  p_value: z.number().optional(),
  confidence_interval: z.tuple([z.number(), z.number()]).optional(),
  statistical_test: z.string().optional(),         // "log-rank", "ANCOVA", "MMRM", "CMH"

  // One of the biggest mispricing sources in biotech.
  // Nominal p=0.03 across six endpoints ≠ multiplicity-adjusted p=0.03.
  // true = survives hierarchical testing / Bonferroni / Hochberg.
  // false = nominal only, interpret with caution.
  // undefined = not reported (flag this in the UI).
  multiplicity_adjusted: z.boolean().optional(),

  // Per-endpoint analysis timing. An interim OS look can coexist with
  // final PFS in the same trial.
  analysis_type: AnalysisTypeSchema,

  // Provenance
  source: z.string().min(1),                      // "NEJM 2023;388:1421-32"
  data_maturity: DataMaturitySchema,
});
export type EndpointResult = z.infer<typeof EndpointResultSchema>;

// --- Subgroups ---
export const SubgroupAnalysisSchema = z.object({
  subgroup_name: z.string().min(1),               // "oHCM", "PD-L1 ≥50%", "1 prior TKI"
  n: z.number().int().positive(),

  // Was this subgroup in the statistical analysis plan before unblinding?
  // Post-hoc subgroups are hypothesis-generating at best.
  pre_specified: z.boolean(),

  // Was the trial powered to detect a difference in this subgroup?
  // false = underpowered "trend toward benefit" — companies spin these.
  powered: z.boolean(),

  endpoints: z.array(EndpointResultSchema),
});
export type SubgroupAnalysis = z.infer<typeof SubgroupAnalysisSchema>;

// --- Temporal data events ---
// Models the catalyst timeline for a trial. Each event captures
// what was known at a specific point in time.
export const DataEventSchema = z.object({
  event_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "ISO date required (YYYY-MM-DD)"),
  event_type: DataEventTypeSchema,
  event_description: z.string().min(1),

  // Endpoints as reported at this event. May be a subset — e.g., a press
  // release might only report the primary, with full data at a conference.
  // These are HISTORICAL snapshots; trial.endpoints holds the latest.
  endpoints_reported: z.array(EndpointResultSchema),
});
export type DataEvent = z.infer<typeof DataEventSchema>;

// --- Trial ---
// Efficacy lives HERE, not at the drug level.
// Each trial carries its own endpoint results.
const TrialBaseSchema = z.object({
  // v0.4: Stable identifier for renderer cross-referencing.
  id: z.string().min(1),                          // "explorer-hcm", "arros-1", "broaden-1b"

  trial_name: z.string().min(1),                  // "EXPLORER-HCM", "LIBERTY AD HELO"
  nct_id: z.string().optional(),
  phase: TrialPhaseSchema,
  study_design: StudyDesignSchema,
  n_enrolled: z.number().int().positive(),
  n_randomized: z.number().int().positive().optional(),

  // Display-only string. Add duration_weeks: number when sort/filter is needed.
  duration: z.string().min(1),                    // "30 weeks", "24 months"

  // v0.4: Optional. Must be omitted for single-arm studies (enforced by refine).
  // For RCTs: "placebo", "sotorasib", "best supportive care", etc.
  control_arm: z.string().min(1).optional(),

  population_summary: z.string().min(1),          // "Symptomatic oHCM, LVEF ≥55%"
  key_inclusion_criteria: z.array(z.string()).optional(),

  // Co-primary support. AD trials universally use co-primaries
  // (EASI-75 AND vIGA 0/1). Missing one = trial failure.
  // "single" = one primary; "co_primary" = ALL must hit;
  // "hierarchical" = test in order, stop at first miss.
  primary_endpoint_ids: z.array(z.string().min(1)).min(1),
  primary_endpoint_strategy: PrimaryEndpointStrategySchema,

  // Critical for oncology investment thesis.
  // 1L vs 2L+ approval changes revenue estimate by 3-5x.
  line_of_therapy: LineOfTherapySchema.optional(),

  // When the control arm crosses over to treatment, it confounds OS analysis.
  // Central to ALK+ NSCLC investment debates (CROWN trial).
  crossover_allowed: z.boolean().optional(),

  // The core data: LATEST / MOST MATURE read of each endpoint.
  // For historical progression, see data_events.
  endpoints: z.array(EndpointResultSchema).min(1),

  subgroups: z.array(SubgroupAnalysisSchema).optional(),

  // Temporal catalyst structure — tracks data evolution across readouts.
  data_events: z.array(DataEventSchema),
});

export const TrialSchema = TrialBaseSchema.superRefine((trial, ctx) => {
  // control_arm must be omitted for single-arm, required for everything else
  if (trial.study_design === "single_arm" && trial.control_arm !== undefined) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "control_arm must be omitted for single_arm studies",
      path: ["control_arm"],
    });
  }
  if (trial.study_design !== "single_arm" && trial.control_arm === undefined) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "control_arm is required for non-single-arm studies",
      path: ["control_arm"],
    });
  }
});
export type Trial = z.infer<typeof TrialSchema>;

// --- Safety ---
export const PercentWithNSchema = z.object({
  pct: z.number(),
  n: z.number().int().nonnegative(),
});
export type PercentWithN = z.infer<typeof PercentWithNSchema>;

export const AdverseEventSchema = z.object({
  event_name: z.string().min(1),                  // "Systolic dysfunction", "ALT elevation ≥3x ULN"
  incidence_pct: z.number(),
  grade_3_plus_pct: z.number().optional(),        // oncology cares about this
  vs_control_pct: z.number().optional(),           // placebo/comparator arm rate
  is_class_effect: z.boolean(),                   // true = expected for mechanism, not drug-specific
});
export type AdverseEvent = z.infer<typeof AdverseEventSchema>;

export const AECategorySchema = z.object({
  category: z.string().min(1),                    // "Cardiac", "Hepatic", "GI", "Skin"
  events: z.array(AdverseEventSchema).min(1),
});
export type AECategory = z.infer<typeof AECategorySchema>;

export const SafetyProfileSchema = z.object({
  discontinuation_rate: PercentWithNSchema.optional(),
  serious_ae_rate: PercentWithNSchema.optional(),
  dose_reduction_rate: PercentWithNSchema.optional(),
  ae_categories: z.array(AECategorySchema),
  regulatory_warnings: z.array(z.string()).optional(),
});
export type SafetyProfile = z.infer<typeof SafetyProfileSchema>;

// --- Regulatory status ---
export const RegulatoryStatusSchema = z.object({
  approval_status: ApprovalStatusSchema,
  approved_indications: z.array(z.string()),

  // Label baggage that throttles commercial uptake.
  // REMS, black box warnings, mandatory monitoring (e.g. CAMZYOS echo REMS).
  label_restrictions: z.array(z.string()),

  // Next binary event the market is pricing.
  next_regulatory_catalyst: z.string().optional(),     // ISO date
  catalyst_description: z.string().optional(),

  // These stack — mavacamten had breakthrough + priority review.
  regulatory_designations: z.array(RegulatoryDesignationSchema),
  regulatory_pathway: RegulatoryPathwaySchema,
});
export type RegulatoryStatus = z.infer<typeof RegulatoryStatusSchema>;

// --- Commercial ---
export const CommercialDataSchema = z.object({
  // Patient population count. HCM ~300K vs AD ~43M vs ROS1+ NSCLC ~4.5K.
  // This 10,000x range fundamentally changes the investment thesis.
  tam_patients: z.number().positive().optional(),
  tam_revenue_mm: z.number().positive().optional(),       // millions USD

  peak_sales_consensus_mm: z.number().positive().optional(),   // millions USD
  current_annual_revenue_mm: z.number().nonnegative().optional(),
  pricing_annual_usd: z.number().positive().optional(),
  launch_date: z.string().optional(),                     // ISO date

  formulary_status: FormularyStatusSchema.optional(),

  key_commercial_risks: z.array(z.string()),
  deal_terms: z.string().optional(),
});
export type CommercialData = z.infer<typeof CommercialDataSchema>;

// --- Comparator (one per drug) ---
export const ComparatorSchema = z.object({
  // v0.4: Stable identifier for renderer cross-referencing.
  id: z.string().min(1),                          // "mavacamten", "aficamten", "edg-7500"

  drug_name: z.string().min(1),
  generic_name: z.string().optional(),
  company: z.string().min(1),
  ticker: z.string().min(1),
  mechanism_class: z.string().min(1),             // "cardiac myosin inhibitor", "allosteric"
  route: RouteOfAdministrationSchema,
  dosing_summary: z.string().optional(),          // "5mg BID, titrated to 15mg"
  indications: z.array(z.string()).min(1),

  // Combination therapy. In oncology, regimens matter — lorlatinib + chemo
  // vs monotherapy are different comparators. Empty array = monotherapy.
  combination_partners: z.array(z.string()),

  trials: z.array(TrialSchema).min(1),
  safety_profile: SafetyProfileSchema,
  regulatory_status: RegulatoryStatusSchema,
  commercial: CommercialDataSchema,
});
export type Comparator = z.infer<typeof ComparatorSchema>;

// --- Key debates ---
export const DebateSchema = z.object({
  question: z.string().min(1),
  bull_view: z.string().min(1),
  bear_view: z.string().min(1),
  resolution_catalyst: z.string().min(1),
});
export type Debate = z.infer<typeof DebateSchema>;

// ============================================================
// Top-level schema
// ============================================================

export const TargetComparisonSchema = z.object({
  target_disease: z.string().min(1),              // "HCM", "Atopic Dermatitis", "ALK+ NSCLC"
  target_mechanism: z.string().min(1),            // "Cardiac myosin inhibitor", "ALK TKI"
  last_updated: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "ISO date required (YYYY-MM-DD)"),

  // Endpoint registry: tells the renderer what to expect and how to display it.
  // Keyed by endpoint_id (e.g. "lvot_gradient_change", "easi_75").
  endpoint_registry: z.record(z.string(), EndpointMetaSchema),

  comparators: z.array(ComparatorSchema).min(1),
  cross_trial_caveats: z.array(z.string()),
  key_debates: z.array(DebateSchema),
});
export type TargetComparison = z.infer<typeof TargetComparisonSchema>;

// ============================================================
// Runtime validation
// ============================================================
// Shape validation (Zod) + referential integrity checks.
// Use in the extraction pipeline to fail loud on malformed JSON.

export interface ValidationResult {
  success: boolean;
  data?: TargetComparison;
  errors: string[];
}

export function parseTargetComparison(raw: unknown): ValidationResult {
  // Step 1: Shape validation
  const parsed = TargetComparisonSchema.safeParse(raw);
  if (!parsed.success) {
    return {
      success: false,
      errors: parsed.error.issues.map(
        (i) => `${i.path.join(".")}: ${i.message}`
      ),
    };
  }

  const data = parsed.data;
  const errors: string[] = [];
  const registryKeys = new Set(Object.keys(data.endpoint_registry));

  // Step 2: Every endpoint_id referenced in results must exist in the registry
  for (const comp of data.comparators) {
    for (const trial of comp.trials) {
      for (const pid of trial.primary_endpoint_ids) {
        if (!registryKeys.has(pid)) {
          errors.push(
            `${comp.drug_name} / ${trial.trial_name}: primary_endpoint_id "${pid}" not in endpoint_registry`
          );
        }
      }

      const checkEndpoints = (endpoints: EndpointResult[], context: string) => {
        for (const ep of endpoints) {
          if (!registryKeys.has(ep.endpoint_id)) {
            errors.push(
              `${context}: endpoint_id "${ep.endpoint_id}" not in endpoint_registry`
            );
          }
        }
      };

      checkEndpoints(trial.endpoints, `${comp.drug_name} / ${trial.trial_name}`);

      if (trial.subgroups) {
        for (const sg of trial.subgroups) {
          checkEndpoints(
            sg.endpoints,
            `${comp.drug_name} / ${trial.trial_name} / subgroup "${sg.subgroup_name}"`
          );
        }
      }

      for (const event of trial.data_events) {
        checkEndpoints(
          event.endpoints_reported,
          `${comp.drug_name} / ${trial.trial_name} / event "${event.event_description}"`
        );
      }
    }
  }

  // Step 3: primary_endpoint_strategy consistency
  for (const comp of data.comparators) {
    for (const trial of comp.trials) {
      if (trial.primary_endpoint_strategy === "single" && trial.primary_endpoint_ids.length !== 1) {
        errors.push(
          `${comp.drug_name} / ${trial.trial_name}: strategy is "single" but has ${trial.primary_endpoint_ids.length} primary endpoints`
        );
      }
      if (trial.primary_endpoint_strategy === "co_primary" && trial.primary_endpoint_ids.length < 2) {
        errors.push(
          `${comp.drug_name} / ${trial.trial_name}: strategy is "co_primary" but has only ${trial.primary_endpoint_ids.length} primary endpoint(s)`
        );
      }
    }
  }

  // Step 4: Unique ids
  const comparatorIds = data.comparators.map((c) => c.id);
  const dupComps = comparatorIds.filter((id, i) => comparatorIds.indexOf(id) !== i);
  for (const dup of dupComps) {
    errors.push(`Duplicate comparator id: "${dup}"`);
  }

  for (const comp of data.comparators) {
    const trialIds = comp.trials.map((t) => t.id);
    const dupTrials = trialIds.filter((id, i) => trialIds.indexOf(id) !== i);
    for (const dup of dupTrials) {
      errors.push(`${comp.drug_name}: duplicate trial id "${dup}"`);
    }
  }

  return {
    success: errors.length === 0,
    data,
    errors,
  };
}
