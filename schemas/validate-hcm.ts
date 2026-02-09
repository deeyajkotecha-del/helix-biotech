// Validate hcm.json against the TargetComparison Zod schema.
// Run: npx tsx schemas/validate-hcm.ts

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { parseTargetComparison } from "./target-comparison";

const __dirname = dirname(fileURLToPath(import.meta.url));
const jsonPath = join(__dirname, "../data/comparisons/hcm.json");

console.log("=== Validating HCM Comparison JSON ===\n");
console.log(`File: ${jsonPath}\n`);

const raw = JSON.parse(readFileSync(jsonPath, "utf-8"));
const result = parseTargetComparison(raw);

if (result.success) {
  console.log("[PASS] Schema shape validation (Zod)");
  console.log("[PASS] Referential integrity (all endpoint_ids resolve to registry)");
  console.log("[PASS] Strategy consistency (primary_endpoint_strategy vs ids count)");
  console.log("[PASS] Unique ids (no duplicate comparator or trial ids)");
  console.log("[PASS] Conditional control_arm validation");

  const data = result.data!;
  console.log(`\n--- Data Summary ---`);
  console.log(`Disease:         ${data.target_disease}`);
  console.log(`Mechanism:       ${data.target_mechanism}`);
  console.log(`Last updated:    ${data.last_updated}`);
  console.log(`Registry:        ${Object.keys(data.endpoint_registry).length} endpoints registered`);
  console.log(`Comparators:     ${data.comparators.length}`);

  for (const comp of data.comparators) {
    console.log(`\n  ${comp.drug_name} (${comp.generic_name}) [${comp.ticker}]`);
    console.log(`    id:            ${comp.id}`);
    console.log(`    Mechanism:     ${comp.mechanism_class}`);
    console.log(`    Route:         ${comp.route}`);
    console.log(`    Approval:      ${comp.regulatory_status.approval_status}`);
    for (const trial of comp.trials) {
      console.log(`    Trial:         ${trial.trial_name} (${trial.nct_id ?? "no NCT"}) [id: ${trial.id}]`);
      console.log(`      Phase:       ${trial.phase} ${trial.study_design} vs ${trial.control_arm ?? "N/A"}`);
      console.log(`      n:           ${trial.n_enrolled} enrolled${trial.n_randomized ? `, ${trial.n_randomized} randomized` : ""}`);
      console.log(`      Duration:    ${trial.duration}`);
      console.log(`      Strategy:    ${trial.primary_endpoint_strategy} → [${trial.primary_endpoint_ids.join(", ")}]`);
      console.log(`      Endpoints:   ${trial.endpoints.length}`);
      console.log(`      Data events: ${trial.data_events.length}`);
    }
    console.log(`    Safety AE cats: ${comp.safety_profile.ae_categories.length}`);
    console.log(`    Warnings:      ${comp.safety_profile.regulatory_warnings?.length ?? 0}`);
  }

  console.log(`\nCross-trial caveats: ${data.cross_trial_caveats.length}`);
  console.log(`Key debates:         ${data.key_debates.length}`);
  console.log(`\n=== All checks passed ===`);
} else {
  console.error("[FAIL] Validation errors:\n");
  for (const err of result.errors) {
    console.error(`  - ${err}`);
  }
  process.exit(1);
}
