// Negative tests: confirm the validator rejects malformed data.
// Tests v0.4 changes: control_arm conditional, line_of_therapy union,
// id fields, duplicate id detection.

import { parseTargetComparison } from "./target-comparison";

function test(name: string, data: unknown, expectedErrors: string[]): void {
  const result = parseTargetComparison(data);
  if (result.success && expectedErrors.length > 0) {
    console.error(`[FAIL] "${name}": expected errors but validation passed`);
    process.exit(1);
  }
  if (!result.success && expectedErrors.length === 0) {
    console.error(`[FAIL] "${name}": expected pass but got errors:`, result.errors);
    process.exit(1);
  }
  if (!result.success) {
    for (const expected of expectedErrors) {
      const found = result.errors.some((e) => e.includes(expected));
      if (!found) {
        console.error(`[FAIL] "${name}": expected error containing "${expected}"\n  Got: ${result.errors.join("; ")}`);
        process.exit(1);
      }
    }
  }
  console.log(`[PASS] ${name} (${result.errors.length} error(s) caught)`);
}

// Helper: minimal valid comparator shell
function makeComparator(overrides: Record<string, unknown> = {}, trialOverrides: Record<string, unknown> = {}) {
  return {
    id: "test-drug",
    drug_name: "TestDrug",
    company: "TestCo",
    ticker: "TEST",
    mechanism_class: "test",
    route: "oral",
    indications: ["TestIndication"],
    combination_partners: [],
    trials: [{
      id: "test-trial",
      trial_name: "TEST-1",
      phase: "3",
      study_design: "rct_double_blind",
      control_arm: "placebo",
      n_enrolled: 100,
      duration: "30 weeks",
      population_summary: "test",
      primary_endpoint_ids: ["test_ep"],
      primary_endpoint_strategy: "single",
      endpoints: [{
        endpoint_id: "test_ep",
        timepoint: "Week 30",
        value: -36,
        unit: "mmHg",
        change_type: "absolute_change",
        analysis_type: "final",
        source: "test",
        data_maturity: "peer_reviewed",
      }],
      data_events: [],
      ...trialOverrides,
    }],
    safety_profile: { ae_categories: [] },
    regulatory_status: {
      approval_status: "phase_3",
      approved_indications: [],
      label_restrictions: [],
      regulatory_designations: [],
      regulatory_pathway: "standard",
    },
    commercial: { key_commercial_risks: [] },
    ...overrides,
  };
}

function makeDoc(comparators: unknown[], registryKeys: string[] = ["test_ep"]) {
  const registry: Record<string, unknown> = {};
  for (const k of registryKeys) {
    registry[k] = {
      label: k,
      category: "cardiac_function",
      display_format: "number",
      sort_order: 1,
      higher_is_better: false,
      endpoint_class: "primary",
      outcome_type: "surrogate",
      regulatory_precedent: true,
    };
  }
  return {
    target_disease: "Test",
    target_mechanism: "Test",
    last_updated: "2026-02-09",
    endpoint_registry: registry,
    comparators,
    cross_trial_caveats: [],
    key_debates: [],
  };
}

console.log("=== Negative Tests (v0.4) ===\n");

// 1. Empty object
test("Empty object", {}, ["target_disease"]);

// 2. Dangling endpoint_id
test("Dangling endpoint_id",
  makeDoc([makeComparator({}, {
    primary_endpoint_ids: ["nonexistent"],
    endpoints: [{
      endpoint_id: "also_nonexistent",
      timepoint: "Week 30", value: -36, unit: "mmHg",
      change_type: "absolute_change", analysis_type: "final",
      source: "test", data_maturity: "peer_reviewed",
    }],
  })]),
  ["nonexistent"],
);

// 3. co_primary with only 1 endpoint
test("co_primary needs ≥2 endpoints",
  makeDoc([makeComparator({}, {
    primary_endpoint_ids: ["test_ep"],
    primary_endpoint_strategy: "co_primary",
  })]),
  ["co_primary"],
);

// 4. Invalid change_type enum
test("Invalid change_type",
  makeDoc([makeComparator({}, {
    endpoints: [{
      endpoint_id: "test_ep",
      timepoint: "Week 30", value: -36, unit: "mmHg",
      change_type: "INVALID_TYPE", analysis_type: "final",
      source: "test", data_maturity: "peer_reviewed",
    }],
  })]),
  ["change_type"],
);

// 5. single_arm study WITH control_arm → must reject
test("single_arm must not have control_arm",
  makeDoc([makeComparator({}, {
    study_design: "single_arm",
    control_arm: "placebo",
  })]),
  ["control_arm must be omitted for single_arm"],
);

// 6. rct_double_blind WITHOUT control_arm → must reject
test("RCT must have control_arm",
  makeDoc([makeComparator({}, {
    study_design: "rct_double_blind",
    control_arm: undefined,
  })]),
  ["control_arm is required"],
);

// 7. Invalid line_of_therapy (loose string instead of union value)
test("Invalid line_of_therapy",
  makeDoc([makeComparator({}, {
    line_of_therapy: "first-line",
  })]),
  ["line_of_therapy"],
);

// 8. Duplicate comparator ids
test("Duplicate comparator ids",
  makeDoc([
    makeComparator({ id: "same-id" }),
    makeComparator({ id: "same-id", drug_name: "OtherDrug" }),
  ]),
  ["Duplicate comparator id"],
);

// 9. Duplicate trial ids within a comparator
test("Duplicate trial ids",
  makeDoc([makeComparator({
    trials: [
      {
        id: "same-trial",
        trial_name: "TRIAL-A",
        phase: "3", study_design: "rct_double_blind", control_arm: "placebo",
        n_enrolled: 100, duration: "30 weeks", population_summary: "test",
        primary_endpoint_ids: ["test_ep"], primary_endpoint_strategy: "single",
        endpoints: [{ endpoint_id: "test_ep", timepoint: "W30", value: 1, unit: "%", change_type: "responder_rate", analysis_type: "final", source: "t", data_maturity: "peer_reviewed" }],
        data_events: [],
      },
      {
        id: "same-trial",
        trial_name: "TRIAL-B",
        phase: "2", study_design: "rct_double_blind", control_arm: "placebo",
        n_enrolled: 50, duration: "16 weeks", population_summary: "test",
        primary_endpoint_ids: ["test_ep"], primary_endpoint_strategy: "single",
        endpoints: [{ endpoint_id: "test_ep", timepoint: "W16", value: 2, unit: "%", change_type: "responder_rate", analysis_type: "final", source: "t", data_maturity: "peer_reviewed" }],
        data_events: [],
      },
    ],
  })]),
  ["duplicate trial id"],
);

// 10. single_arm without control_arm → should pass
test("single_arm without control_arm passes", (() => {
  const doc = makeDoc([makeComparator({}, {
    study_design: "single_arm",
    control_arm: undefined,
  })]);
  return doc;
})(), []);

console.log("\n=== All negative tests passed ===");
