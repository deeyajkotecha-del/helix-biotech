// ============================================================
// Smoke test: minimal HCM TargetComparison
// ============================================================
// Mavacamten + EXPLORER-HCM + 2 endpoints + 1 subgroup.
// Validates BOTH compile-time types AND runtime Zod validation.
//
// All types derived from Zod (single source of truth).
// ============================================================

import type { TargetComparison } from "./target-comparison";
import { parseTargetComparison } from "./target-comparison";

// --- The test data ---
// This object is typed as TargetComparison at compile time.
// Any shape mismatch = tsc error.

const hcmComparison: TargetComparison = {
  target_disease: "HCM",
  target_mechanism: "Cardiac myosin inhibitor",
  last_updated: "2026-02-09",

  endpoint_registry: {
    lvot_gradient_change: {
      label: "LVOT Gradient Reduction (Resting)",
      category: "cardiac_function",
      display_format: "number",
      sort_order: 1,
      higher_is_better: false,
      description: "Change in resting left ventricular outflow tract gradient from baseline",
      endpoint_class: "primary",
      outcome_type: "surrogate",
      regulatory_precedent: true,
    },
    kccq_css_change: {
      label: "KCCQ-CSS Change",
      category: "patient_reported",
      display_format: "number",
      sort_order: 5,
      higher_is_better: true,
      description: "Kansas City Cardiomyopathy Questionnaire Clinical Summary Score change from baseline",
      endpoint_class: "secondary",
      outcome_type: "pro",
      regulatory_precedent: false,
    },
  },

  comparators: [
    {
      id: "mavacamten",
      drug_name: "CAMZYOS",
      generic_name: "mavacamten",
      company: "Bristol-Myers Squibb",
      ticker: "BMY",
      mechanism_class: "Cardiac myosin inhibitor (allosteric)",
      route: "oral",
      dosing_summary: "5mg QD, titrated to 2.5-15mg based on LVOT gradient and LVEF",
      indications: ["Symptomatic obstructive HCM (NYHA II-III)"],
      combination_partners: [],

      trials: [
        {
          id: "explorer-hcm",
          trial_name: "EXPLORER-HCM",
          nct_id: "NCT03470545",
          phase: "3",
          study_design: "rct_double_blind",
          n_enrolled: 251,
          n_randomized: 251,
          duration: "30 weeks",
          control_arm: "placebo",
          population_summary: "Symptomatic oHCM, NYHA II-III, LVEF ≥55%, resting or provoked LVOT gradient ≥50 mmHg",
          key_inclusion_criteria: [
            "NYHA class II or III",
            "LVEF ≥55%",
            "Peak LVOT gradient ≥50 mmHg",
          ],
          primary_endpoint_ids: ["lvot_gradient_change"],
          primary_endpoint_strategy: "single",
          line_of_therapy: "1L",
          crossover_allowed: false,

          endpoints: [
            {
              endpoint_id: "lvot_gradient_change",
              timepoint: "Week 30",
              value: -47.0,
              unit: "mmHg",
              change_type: "absolute_change",
              control_value: -10.0,
              delta: -36.0,
              assessment_method: "resting",
              p_value: 0.0001,
              confidence_interval: [-43.2, -28.1],
              statistical_test: "ANCOVA",
              multiplicity_adjusted: true,
              analysis_type: "final",
              source: "Olivotto I, et al. Lancet 2020;396:759-69",
              data_maturity: "peer_reviewed",
            },
            {
              endpoint_id: "kccq_css_change",
              timepoint: "Week 30",
              value: 9.1,
              unit: "points",
              change_type: "absolute_change",
              control_value: 5.5,
              delta: 3.6,
              p_value: 0.05,
              statistical_test: "ANCOVA",
              multiplicity_adjusted: false,
              analysis_type: "final",
              source: "Olivotto I, et al. Lancet 2020;396:759-69",
              data_maturity: "peer_reviewed",
            },
          ],

          subgroups: [
            {
              subgroup_name: "NYHA Class III at baseline",
              n: 67,
              pre_specified: true,
              powered: false,
              endpoints: [
                {
                  endpoint_id: "lvot_gradient_change",
                  timepoint: "Week 30",
                  value: -52.0,
                  unit: "mmHg",
                  change_type: "absolute_change",
                  control_value: -8.0,
                  delta: -44.0,
                  assessment_method: "resting",
                  analysis_type: "post_hoc",
                  source: "Olivotto I, et al. Lancet 2020;396:759-69 (supplementary)",
                  data_maturity: "peer_reviewed",
                },
              ],
            },
          ],

          data_events: [
            {
              event_date: "2020-08-29",
              event_type: "full_data_presentation",
              event_description: "EXPLORER-HCM primary results presented at ESC 2020",
              endpoints_reported: [
                {
                  endpoint_id: "lvot_gradient_change",
                  timepoint: "Week 30",
                  value: -47.0,
                  unit: "mmHg",
                  change_type: "absolute_change",
                  control_value: -10.0,
                  delta: -36.0,
                  assessment_method: "resting",
                  p_value: 0.0001,
                  statistical_test: "ANCOVA",
                  multiplicity_adjusted: true,
                  analysis_type: "final",
                  source: "ESC 2020 Hot Line Session",
                  data_maturity: "conference_presentation",
                },
              ],
            },
            {
              event_date: "2022-04-28",
              event_type: "approval_decision",
              event_description: "FDA approves CAMZYOS for symptomatic oHCM",
              endpoints_reported: [],
            },
          ],
        },
      ],

      safety_profile: {
        discontinuation_rate: { pct: 2.4, n: 6 },
        serious_ae_rate: { pct: 7.9, n: 10 },
        ae_categories: [
          {
            category: "Cardiac",
            events: [
              {
                event_name: "LVEF <50%",
                incidence_pct: 5.6,
                vs_control_pct: 0.8,
                is_class_effect: true,
              },
              {
                event_name: "Systolic dysfunction",
                incidence_pct: 3.2,
                vs_control_pct: 0.0,
                is_class_effect: true,
              },
            ],
          },
        ],
        regulatory_warnings: [
          "REMS: Mandatory echocardiography before and during treatment",
          "Contraindicated with strong/moderate CYP2C19 inhibitors",
        ],
      },

      regulatory_status: {
        approval_status: "approved",
        approved_indications: ["Symptomatic obstructive HCM (NYHA II-III)"],
        label_restrictions: [
          "REMS: Echo required at initiation, weeks 4, 8, 12, and every 12 weeks thereafter",
          "Must verify LVEF ≥55% before each dose change",
          "CYP2C19 poor metabolizers: max dose 2.5mg",
        ],
        next_regulatory_catalyst: "2026-06-15",
        catalyst_description: "sNDA for nHCM expansion (VALOR-HCM data)",
        regulatory_designations: ["breakthrough_therapy", "priority_review"],
        regulatory_pathway: "standard",
      },

      commercial: {
        tam_patients: 300000,
        tam_revenue_mm: 4000,
        peak_sales_consensus_mm: 2800,
        current_annual_revenue_mm: 450,
        pricing_annual_usd: 93000,
        launch_date: "2022-06-01",
        formulary_status: "restricted",
        key_commercial_risks: [
          "REMS limits prescriber adoption",
          "Aficamten (Cytokinetics) Phase 3 without REMS overhead",
          "EDG-7500 (Edgewise) sarcomere modulator without LVEF signal",
        ],
      },
    },
  ],

  cross_trial_caveats: [
    "No head-to-head trials between cardiac myosin inhibitors exist",
    "EXPLORER-HCM and SEQUOIA-HCM had different inclusion criteria for peak LVOT gradient",
  ],

  key_debates: [
    {
      question: "Can aficamten's selectivity advantage overcome mavacamten's first-mover and real-world data?",
      bull_view: "No REMS + better therapeutic window = faster uptake, especially with cardiologists burned by mava echo burden",
      bear_view: "CAMZYOS has 2+ years of real-world safety data; payers and physicians prefer known quantities",
      resolution_catalyst: "SEQUOIA-HCM 52-week extension data + aficamten commercial launch trajectory (H2 2025)",
    },
  ],
};

// --- Runtime validation ---

function runSmokeTest(): void {
  console.log("=== Smoke Test: HCM TargetComparison (v0.4 Zod-first) ===\n");

  console.log("[PASS] Compile-time type check: hcmComparison satisfies TargetComparison (derived from Zod)");

  const result = parseTargetComparison(hcmComparison);

  if (result.success) {
    console.log("[PASS] Runtime Zod validation: schema shape OK");
    console.log("[PASS] Referential integrity: all endpoint_ids resolve to registry");
    console.log("[PASS] Strategy consistency: single primary with 1 endpoint_id");
    console.log("[PASS] control_arm present for rct_double_blind study");
    console.log("[PASS] Unique ids: comparator and trial ids are unique");
  } else {
    console.error("[FAIL] Validation errors:");
    for (const err of result.errors) {
      console.error(`  - ${err}`);
    }
    process.exit(1);
  }

  const comp = hcmComparison.comparators[0];
  const trial = comp.trials[0];

  console.log(`\n--- Data summary ---`);
  console.log(`Disease:     ${hcmComparison.target_disease}`);
  console.log(`Drug:        ${comp.drug_name} (${comp.generic_name}) [id: ${comp.id}]`);
  console.log(`Trial:       ${trial.trial_name} (n=${trial.n_enrolled}) [id: ${trial.id}]`);
  console.log(`Design:      Phase ${trial.phase} ${trial.study_design} vs ${trial.control_arm}`);
  console.log(`Strategy:    ${trial.primary_endpoint_strategy} → [${trial.primary_endpoint_ids.join(", ")}]`);
  console.log(`Line:        ${trial.line_of_therapy ?? "not specified"}`);
  console.log(`Endpoints:   ${trial.endpoints.length}`);
  console.log(`Subgroups:   ${trial.subgroups?.length ?? 0}`);
  console.log(`Data events: ${trial.data_events.length}`);
  console.log(`Registry:    ${Object.keys(hcmComparison.endpoint_registry).length} endpoints registered`);
  console.log(`\n=== All checks passed ===`);
}

runSmokeTest();
