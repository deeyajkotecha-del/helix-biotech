# Company Data Schema v2.0

This document defines the expected JSON structure for company and asset data files.

## Directory Structure
```
data/companies/{TICKER}/
├── company.json          # Company-level data
├── {asset1}.json         # Asset file (e.g., kt621.json, zidesamtinib.json)
├── {asset2}.json
└── ...
```

---

## company.json

```json
{
  "_metadata": {
    "version": "2.0",
    "ticker": "KYMR",
    "company_name": "Company Name",
    "data_source": "Source presentation/document",
    "extraction_date": "2026-02-04"
  },

  "company": {
    "name": "Company Name",
    "ticker": "KYMR",
    "exchange": "NASDAQ",
    "headquarters": "City, State",
    "website": "https://...",
    "one_liner": "Brief company description for cards/headers"   // IMPORTANT: displays in header
  },

  "investment_thesis_summary": {
    "core_thesis": "One paragraph thesis statement",
    "key_value_drivers": ["Driver 1", "Driver 2", "Driver 3"]
  },

  "investment_analysis": {
    "bull_case": ["Point 1", "Point 2", "Point 3"],              // SIMPLE LIST preferred
    // OR nested format (also supported):
    "bull_case": {
      "thesis": "Summary thesis",
      "key_points": ["Point 1", "Point 2", "Point 3"]            // key_points is required if dict
    },

    "bear_case": ["Risk 1", "Risk 2", "Risk 3"],                 // Same format as bull_case

    "key_debates": [
      {
        "question": "Key question?",
        "bull_view": "Positive view",
        "bear_view": "Negative view",
        "what_resolves_it": "Catalyst/data"
      }
    ],

    "valuation_framework": {
      "approach": "Sum-of-parts risk-adjusted NPV",
      "key_assumptions": { ... }
    }
  },

  "pipeline_summary": {
    "total_programs": 4,
    "clinical_stage": 3,
    "programs": [
      {
        "asset": "KT-621",
        "target": "STAT6",
        "stage": "Phase 2b",                                      // REQUIRED: displays in pipeline table
        "indications": "AD, Asthma, COPD",                        // plural, comma-separated
        "ownership": "Wholly-owned",
        "market_opportunity": ">$20B",
        "next_catalyst": "Phase 2b data - Mid-2027"
      }
    ]
  },

  "platform": {
    "name": "Platform Name",
    "description": "Platform description"
  },

  "financials": {
    "cash_runway": "Into 2029"
  }
}
```

---

## {asset}.json

```json
{
  "_metadata": {
    "version": "2.0",
    "ticker": "KYMR",
    "asset_name": "KT-621"
  },

  "asset": {
    "name": "KT-621",                                             // REQUIRED
    "ticker": "KYMR",
    "modality": "Small molecule degrader",
    "stage": "Phase 2b",                                          // REQUIRED: shows in pipeline table
    "one_liner": "Brief asset description",
    "ownership": "Wholly-owned"
  },

  "target": {
    "name": "STAT6",                                              // REQUIRED (or "primary_target")
    "full_name": "Signal Transducer and Activator of Transcription 6",
    "class": "Transcription Factor",
    "pathway": "IL-4/IL-13 → Type 2 inflammation",

    "biology": {
      "simple_explanation": "Plain English explanation",          // REQUIRED (or "function")
      "pathway_detail": "Technical pathway description",
      "downstream_effects": ["Effect 1", "Effect 2"]
    },

    "why_good_target": {
      "clinical_validation": "Existing drugs validate pathway",
      "genetic_validation": {
        "gain_of_function": "GoF mutation phenotype",
        "loss_of_function": "LoF protective effect"
      }
    }
  },

  "indications": {
    "lead": {
      "name": "Atopic Dermatitis",
      "stage": "Phase 2b",
      "rationale": "Why this indication"
    },
    "expansion": [
      { "name": "Asthma", "stage": "Planned" }
    ]
  },

  "clinical_data": {
    // OPTION A: Named trial sections (KYMR style - preferred for complex trials)
    "phase1_healthy_volunteer": {
      "design": { "description": "SAD/MAD study" },
      "population": { "n": 64 },
      "results": { ... }
    },
    "phase1b_ad": {
      "design": { ... },
      "key_findings": [ ... ],
      "efficacy_endpoints": {
        "EASI": {
          "full_name": "Eczema Area and Severity Index",
          "results": { "mean_change_overall": "-65%" }
        }
      }
    },
    "ongoing_trials": [
      { "trial_name": "BROADEN2", "phase": "Phase 2b", "status": "Enrolling" }
    ],

    // OPTION B: Flat structure (NUVL style - simpler but less structured)
    "trial_name": "ARROS-1",
    "trial_design": {
      "phase": "Phase 1/2",                                       // Shows as stage badge
      "design": "Global open-label multi-cohort"
    },
    "populations": {
      "pivotal_safety": { "n": 432, "description": "..." }
    },
    "tki_pretreated_results": {
      "orr": "44%",                                                // Simple key-value preferred
      "dor_median": "22 months",
      "pfs_median": "9.7 months"
    },
    "safety": {
      "dose_reduction": "10%",
      "discontinuation": "2%"
    }
  },

  "catalysts": [
    {
      "event": "Phase 2b data readout",
      "timing": "Mid-2027",
      "importance": "critical",
      "what_to_watch": "EASI-75 response rate at Week 16"
    }
  ],

  "investment_analysis": {
    "probability_of_success": "36%",
    "peak_sales_estimate": "$3-5B",
    "key_risks": ["Risk 1", "Risk 2"]
  },

  "market_opportunity": {
    "tam": "$20B+",
    "unmet_need": "Need for oral alternatives to biologics"
  }
}
```

---

## Key Field Mappings (Template Expectations)

| What Displays | Primary Field | Fallback Fields |
|--------------|---------------|-----------------|
| **Target name** | `target.name` | `target.primary_target` |
| **Target biology** | `target.biology.simple_explanation` | `target.biology.function`, `target.biology.pathway_detail` |
| **Asset stage** | `asset.stage` | `clinical_data.trial_design.phase` |
| **Lead indication** | `indications.lead.name` | `clinical_data.trial_design.registration_intent` |
| **Bull case points** | `investment_analysis.bull_case[]` | `investment_analysis.bull_case.key_points[]` |
| **Pipeline table** | `pipeline_summary.programs[].stage` | Individual asset files |

---

## Best Practices

1. **Keep result values simple**: Use `"orr": "44%"` not `"orr": {"value": "44%", "n": 117, ...}`
2. **Use consistent field names**: Prefer `name` over `primary_target`, `simple_explanation` over `function`
3. **Include `stage` in asset object**: Required for pipeline table display
4. **List bull/bear as arrays**: Simpler to render than nested objects
5. **Provide `one_liner`**: Shows in company header and asset cards
