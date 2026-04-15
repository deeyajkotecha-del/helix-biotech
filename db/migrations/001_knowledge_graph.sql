-- ============================================================================
-- SatyaBio Knowledge Graph Schema
-- Migration 001: Core entities, relationships, temporal versioning,
--                clinical data extraction, competitive landscape
-- ============================================================================
-- Run against your Neon Postgres instance:
--   psql $DATABASE_URL -f 001_knowledge_graph.sql
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================
-- NOTE: drugs, targets, drug_aliases, drug_targets, indications already exist
-- with UUID PKs (from 000_uuid_migration.py). We add new columns and create
-- only the truly new tables.
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    company_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker          TEXT UNIQUE,
    name            TEXT NOT NULL,
    hq_country      TEXT,
    market_cap_mm   NUMERIC,
    stage           TEXT,  -- 'commercial', 'clinical', 'preclinical'
    therapeutic_focus TEXT[],
    website         TEXT,
    ir_page_url     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Add new columns to existing targets table
ALTER TABLE targets ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE targets ADD COLUMN IF NOT EXISTS pathway TEXT;
ALTER TABLE targets ADD COLUMN IF NOT EXISTS druggability TEXT;

-- Add new columns to existing indications table
ALTER TABLE indications ADD COLUMN IF NOT EXISTS disease_name TEXT;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS disease_subtype TEXT;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS icd10_code TEXT;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS therapeutic_area TEXT;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS organ_system TEXT;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS parent_indication_id UUID REFERENCES indications(indication_id);
ALTER TABLE indications ADD COLUMN IF NOT EXISTS us_incidence INTEGER;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS us_prevalence INTEGER;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS standard_of_care JSONB;
ALTER TABLE indications ADD COLUMN IF NOT EXISTS unmet_need TEXT;

-- Backfill disease_name from display_name if not set
UPDATE indications SET disease_name = display_name WHERE disease_name IS NULL AND display_name IS NOT NULL;

-- Add new columns to existing drugs table
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(company_id);
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS modality_detail TEXT;
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS highest_phase TEXT;
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS first_disclosed DATE;
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS route TEXT;
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS dosing_schedule TEXT;

-- Backfill highest_phase from phase_highest if not set
UPDATE drugs SET highest_phase = phase_highest WHERE highest_phase IS NULL AND phase_highest IS NOT NULL;

-- Add new column to existing drug_targets table
ALTER TABLE drug_targets ADD COLUMN IF NOT EXISTS mechanism TEXT;

-- Drug-indication programs (the development arc)
CREATE TABLE programs (
    program_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_id                 UUID NOT NULL REFERENCES drugs(drug_id) ON DELETE CASCADE,
    indication_id           UUID NOT NULL REFERENCES indications(indication_id),
    program_name            TEXT,           -- 'ADMIRAL program', 'gilteritinib R/R AML'
    highest_phase           TEXT,
    regulatory_status       TEXT,           -- 'preclinical', 'IND_filed', 'active', 'on_hold', 'approved', 'withdrawn', 'voluntarily_withdrawn'
    designations            TEXT[],         -- ['breakthrough_therapy', 'fast_track', 'orphan', 'RMAT', 'priority_review']
    first_patient_dosed     DATE,
    registration_strategy   TEXT,           -- 'accelerated_approval', 'standard', 'breakthrough'
    primary_endpoint        TEXT,           -- 'OS', 'PFS', 'ORR', 'CR rate', 'MRD negativity'
    catalyst_timeline       JSONB,          -- [{event: "Ph3 topline", expected: "2025-Q2", status: "pending"}]
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(drug_id, indication_id)
);

-- ============================================================================
-- TRIALS (expanded)
-- ============================================================================

CREATE TABLE trials (
    trial_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    program_id              UUID REFERENCES programs(program_id),
    nct_id                  TEXT UNIQUE,
    trial_name              TEXT,           -- 'ADMIRAL', 'CHRYSALIS', 'CodeBreaK 200'
    phase                   TEXT NOT NULL,
    trial_type              TEXT NOT NULL,  -- 'sponsor_interventional', 'IST', 'expanded_access', 'compassionate_use', 'registry', 'real_world'
    sponsor_type            TEXT,           -- 'company', 'academic', 'cooperative_group', 'NCI'
    principal_investigator  TEXT,
    pi_institution          TEXT,
    design                  TEXT,           -- 'single_arm', 'randomized_controlled', 'platform', 'basket', 'umbrella', 'adaptive', 'dose_escalation', 'dose_expansion'
    randomization_ratio     TEXT,           -- '1:1', '2:1', '1:1:1'
    blinding                TEXT,           -- 'open_label', 'single_blind', 'double_blind'
    control_arm             TEXT,           -- null for single-arm; 'placebo', 'physician_choice', 'docetaxel', etc.
    combination_drug_ids    UUID[],         -- FK references to drugs table
    biomarker_selection     JSONB,          -- {marker: "FLT3-ITD", required: true, method: "PCR", cutoff: "ratio >= 0.05"}
    line_of_therapy         TEXT,           -- '1L', '2L', '3L_plus', 'maintenance', 'adjuvant', 'neoadjuvant', 'perioperative'
    patient_population      TEXT,           -- free text describing key eligibility
    enrollment_target       INTEGER,
    enrollment_actual       INTEGER,
    status                  TEXT,           -- 'not_yet_recruiting', 'recruiting', 'active_not_recruiting', 'completed', 'terminated', 'suspended', 'withdrawn'
    start_date              DATE,
    primary_completion_date DATE,
    study_completion_date   DATE,
    -- IST-specific fields
    ist_support_type        TEXT,           -- 'drug_supply_only', 'drug_plus_funding', 'no_support', 'unknown'
    novel_indication        BOOLEAN DEFAULT FALSE,  -- true if indication differs from sponsor's programs
    novel_combination       BOOLEAN DEFAULT FALSE,  -- true if combo partner differs from sponsor's trials
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trials_program ON trials(program_id);
CREATE INDEX idx_trials_nct ON trials(nct_id);

-- ============================================================================
-- TEMPORAL VERSIONING (data vintages)
-- ============================================================================

CREATE TABLE data_vintages (
    vintage_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    event_date              DATE,           -- when data was generated (data cutoff)
    disclosure_date         DATE NOT NULL,  -- when data was publicly available
    disclosure_venue        TEXT,           -- 'ASCO', 'ESMO', 'ASH', 'AACR', 'EHA', 'WCLC', 'SEC_8K', 'press_release', 'publication', 'FDA'
    disclosure_detail       TEXT,           -- 'ASCO 2024 oral #LBA9012', 'NEJM 2024;391:1234'
    data_maturity           NUMERIC,        -- % events / expected events
    median_followup_months  NUMERIC,
    supersedes_vintage_id   UUID REFERENCES data_vintages(vintage_id),
    is_latest               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vintages_trial ON data_vintages(trial_id);
CREATE INDEX idx_vintages_latest ON data_vintages(trial_id, is_latest) WHERE is_latest = TRUE;

-- ============================================================================
-- SOURCE DOCUMENTS
-- ============================================================================

CREATE TABLE source_documents (
    source_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id            UUID REFERENCES trials(trial_id),
    vintage_id          UUID REFERENCES data_vintages(vintage_id),
    source_type         TEXT NOT NULL,  -- 'poster', 'oral_presentation', 'publication', 'press_release', 'SEC_filing', 'CRL', 'label', 'IR_deck', 'IST_abstract'
    title               TEXT,
    venue               TEXT,           -- 'ASCO 2024', 'Blood', 'NEJM', 'SEC 8-K'
    publication_date    DATE,
    authors             TEXT[],
    doi                 TEXT,
    pmid                TEXT,
    url                 TEXT,
    raw_document_path   TEXT,           -- S3 or local path to original PDF
    page_count          INTEGER,
    embedded_chunk_ids  UUID[],         -- links to vector store chunks
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_source_docs_trial ON source_documents(trial_id);

-- ============================================================================
-- CLINICAL RESULTS: KM CURVES (rigorous)
-- ============================================================================

CREATE TABLE km_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    endpoint                TEXT NOT NULL,  -- 'OS', 'PFS', 'DFS', 'EFS', 'RFS', 'TTP', 'DOR'
    analysis_type           TEXT,           -- 'ITT', 'mITT', 'per_protocol', 'as_treated'
    stratification_factors  TEXT[],
    crossover_allowed       BOOLEAN,
    crossover_rate          NUMERIC,        -- fraction that crossed over
    -- Comparison metrics (between arms)
    hazard_ratio            NUMERIC,
    hr_ci_lower             NUMERIC,
    hr_ci_upper             NUMERIC,
    hr_method               TEXT,           -- 'cox_proportional', 'stratified_cox', 'log_rank'
    p_value                 NUMERIC,
    p_value_type            TEXT,           -- 'one_sided', 'two_sided'
    proportional_hazards_met BOOLEAN,
    separation_time_months  NUMERIC,        -- when curves first diverge
    crossing_events         JSONB,          -- [{month: 14, interpretation: "..."}]
    rmst_diff_months        NUMERIC,        -- restricted mean survival time difference
    curve_shape             TEXT,           -- 'early_sep', 'late_sep', 'crossing', 'converging', 'parallel', 'tail_benefit'
    -- Per-arm data stored as JSONB array
    arms                    JSONB NOT NULL, -- see km_arm_detail structure below
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- km_results.arms[] element structure:
-- {
--   arm_name: "seralutinib 60mg",
--   arm_type: "experimental",  -- experimental, control, combo, monotherapy
--   n_enrolled: 218,
--   n_evaluable: 210,
--   median_survival_months: 14.2,  -- null if NR
--   median_ci_lower: 11.8,
--   median_ci_upper: 17.1,
--   events_count: 142,
--   landmark_rates: [{month: 6, rate: 0.72, ci: [0.65, 0.79]}, {month: 12, rate: 0.51}],
--   number_at_risk: [{month: 0, n: 218}, {month: 6, n: 142}, {month: 12, n: 89}],
--   censoring_pattern: {total_censored: 76, total_pct: 0.35, early_pct: 0.12, late_pct: 0.31},
--   curve_shape: "early_sep"
-- }

COMMENT ON TABLE km_results IS 'Rigorous KM curve extraction with censoring patterns, curve shape, PH assessment, and per-arm detail including number-at-risk series';

CREATE INDEX idx_km_trial ON km_results(trial_id);

-- ============================================================================
-- CLINICAL RESULTS: WATERFALL PLOTS
-- ============================================================================

CREATE TABLE waterfall_results (
    result_id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                    UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id                  UUID REFERENCES data_vintages(vintage_id),
    source_id                   UUID REFERENCES source_documents(source_id),
    source_page                 INTEGER,
    measurement_type            TEXT,       -- 'target_lesion_SLD', 'PSA_change', 'ctDNA_change', 'M_protein_change'
    assessment_criteria         TEXT,       -- 'RECIST_1.1', 'iRECIST', 'mRECIST', 'RANO', 'Lugano', 'IMWG', 'IWG_AML', 'iwCLL'
    -- Summary statistics
    orr                         NUMERIC,
    orr_ci                      NUMERIC[2],
    cr_rate                     NUMERIC,
    dcr                         NUMERIC,    -- disease control rate
    cbr                         NUMERIC,    -- clinical benefit rate
    median_depth_of_response    NUMERIC,
    -- Per-patient data
    individual_responses        JSONB,      -- [{patient_index: 1, pct_change: -72, best_response: "PR", biomarker_status: {...}, prior_lines: 2}]
    -- Biomarker correlation
    biomarker_correlations      JSONB,      -- [{marker: "PD-L1 TPS>=50%", orr_subgroup: 0.58, n: 42}]
    prior_therapy_correlations  JSONB,      -- [{prior: "anti-PD1", orr_subgroup: 0.31, n: 67}]
    extraction_confidence       NUMERIC,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_waterfall_trial ON waterfall_results(trial_id);

-- ============================================================================
-- CLINICAL RESULTS: SWIMMER PLOTS
-- ============================================================================

CREATE TABLE swimmer_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    measurement_type        TEXT,       -- 'time_on_treatment', 'time_in_response', 'both'
    -- Per-patient lanes
    lanes                   JSONB,      -- [{patient_index: 1, total_duration_months: 14.2, still_ongoing: true, best_response: "CR", events: [{month: 2.1, type: "PR"}, ...], reason_off_study: null}]
    -- Aggregate metrics (computed)
    median_dor              NUMERIC,
    median_dor_ci           NUMERIC[2],
    dor_censoring_rate      NUMERIC,
    pct_ongoing_6mo         NUMERIC,
    pct_ongoing_12mo        NUMERIC,
    longest_responder_months NUMERIC,
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_swimmer_trial ON swimmer_results(trial_id);

-- ============================================================================
-- CLINICAL RESULTS: SPIDER PLOTS
-- ============================================================================

CREATE TABLE spider_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    y_axis_measure          TEXT,       -- 'SLD_pct_change', 'target_lesion_pct', 'PSA_pct', 'ctDNA_pct'
    x_axis_unit             TEXT,       -- 'weeks', 'cycles', 'months'
    -- Per-patient traces
    traces                  JSONB,      -- [{patient_index: 1, datapoints: [{time: 0, value: 0}, {time: 8, value: -42}], nadir_value: -58, nadir_time: 16, trajectory_class: "rapid_deep", regrowth_onset_time: null}]
    -- Population kinetics (computed)
    median_nadir_pct        NUMERIC,
    median_time_to_nadir    NUMERIC,
    trajectory_distribution JSONB,      -- {rapid_deep: 0.25, gradual_deep: 0.15, shallow_sustained: 0.30, initial_then_regrowth: 0.20, primary_refractory: 0.10}
    early_response_8wk_rate NUMERIC,
    regrowth_pattern        TEXT,       -- 'uniform_timing', 'bimodal', 'rare', 'no_regrowth_observed'
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_spider_trial ON spider_results(trial_id);

-- ============================================================================
-- CLINICAL RESULTS: FOREST PLOTS
-- ============================================================================

CREATE TABLE forest_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_km_result_id     UUID REFERENCES km_results(result_id),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    effect_measure          TEXT,       -- 'HR', 'OR', 'RR', 'risk_diff'
    -- Subgroup data
    subgroups               JSONB,      -- [{name: "PD-L1>=1%", n: 89, effect: 0.61, ci: [0.42, 0.88], events_exp: 34, events_ctrl: 52}]
    interaction_p_values    JSONB,      -- [{subgroup: "PD-L1", p_interaction: 0.04}]
    consistency_flag        TEXT,       -- 'consistent', 'heterogeneous', 'signal_in_subgroup'
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_forest_trial ON forest_results(trial_id);

-- ============================================================================
-- CLINICAL RESULTS: ENDPOINT TIMECOURSE (score/value over time)
-- Primary figure type for: metabolic, autoimmune, neuropsych, rare disease
-- Examples: body weight change over 52 weeks, EASI score over 16 weeks,
--           PANSS total over 6 weeks, eGFR slope over 2 years
-- ============================================================================

CREATE TABLE endpoint_timecourse_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    -- What's being measured
    endpoint_name           TEXT NOT NULL,       -- 'body_weight_pct_change', 'EASI', 'PANSS_total', 'eGFR', 'GL3'
    endpoint_display        TEXT,                -- 'Body weight % change from baseline'
    unit                    TEXT,                -- 'percent_change', 'score', 'mL/min/1.73m2', 'nmol/L'
    direction               TEXT,                -- 'lower_is_better', 'higher_is_better'
    baseline_value          NUMERIC,             -- mean baseline across arms (for context)
    -- Per-arm timecourse data
    arms                    JSONB NOT NULL,
    -- arms[] structure:
    -- {
    --   arm_name: "orforglipron 40mg",
    --   arm_type: "experimental",
    --   n_patients: 272,
    --   timepoints: [
    --     {week: 0, value: 0, se: 0, ci_lower: null, ci_upper: null, n_evaluable: 272},
    --     {week: 12, value: -8.2, se: 0.6, n_evaluable: 258},
    --     {week: 24, value: -12.1, se: 0.7, n_evaluable: 241},
    --     {week: 52, value: -14.7, se: 0.8, n_evaluable: 220}
    --   ]
    -- }
    -- Primary endpoint comparison
    primary_timepoint_week  INTEGER,             -- the protocol-specified primary timepoint
    primary_delta_vs_placebo NUMERIC,            -- treatment effect at primary timepoint
    primary_delta_ci        NUMERIC[2],
    primary_p_value         NUMERIC,
    -- Derived metrics
    time_to_plateau_weeks   INTEGER,             -- when the curve flattens
    max_effect              NUMERIC,             -- best value achieved (any timepoint)
    effect_sustained        BOOLEAN,             -- does the effect hold at last timepoint?
    placebo_adjusted        BOOLEAN DEFAULT TRUE,
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_timecourse_trial ON endpoint_timecourse_results(trial_id);
COMMENT ON TABLE endpoint_timecourse_results IS 'Mean change from baseline over time — primary figure type for metabolic, autoimmune, neuropsych, and rare disease trials';

-- ============================================================================
-- CLINICAL RESULTS: RESPONDER ANALYSIS (bar charts of % achieving threshold)
-- Primary figure type for: autoimmune (EASI-75, PASI-90), metabolic (>=10% weight loss),
--     neuropsych (PANSS >=30% reduction), and some oncology (ORR by subgroup)
-- ============================================================================

CREATE TABLE responder_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    -- What's being measured
    endpoint_name           TEXT NOT NULL,       -- 'EASI', 'PASI', 'body_weight', 'PANSS'
    assessment_timepoint    TEXT,                -- 'week 16', 'week 52', 'month 12'
    -- Per-arm responder rates at multiple thresholds
    arms                    JSONB NOT NULL,
    -- arms[] structure:
    -- {
    --   arm_name: "dupilumab 300mg Q2W",
    --   arm_type: "experimental",
    --   n_patients: 245,
    --   thresholds: [
    --     {threshold: "EASI-50", rate: 0.69, ci_lower: 0.63, ci_upper: 0.75, n_responders: 169},
    --     {threshold: "EASI-75", rate: 0.44, ci_lower: 0.38, ci_upper: 0.50, n_responders: 108},
    --     {threshold: "EASI-90", rate: 0.22, ci_lower: 0.17, ci_upper: 0.28, n_responders: 54},
    --     {threshold: "IGA 0/1", rate: 0.37, ci_lower: 0.31, ci_upper: 0.43, n_responders: 91}
    --   ]
    -- }
    -- Statistical comparison (typically vs placebo)
    comparisons             JSONB,
    -- comparisons[] structure:
    -- {
    --   threshold: "EASI-75",
    --   experimental_rate: 0.44,
    --   control_rate: 0.12,
    --   difference: 0.32,
    --   difference_ci: [0.24, 0.40],
    --   p_value: 0.0001,
    --   nnt: 3.1
    -- }
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_responder_trial ON responder_results(trial_id);
COMMENT ON TABLE responder_results IS 'Responder analysis — % achieving clinical thresholds (EASI-75, PASI-90, ACR50, >=10% weight loss, PANSS >=30% reduction)';

-- ============================================================================
-- CLINICAL RESULTS: DOSE-RESPONSE
-- Relevant across all TAs but especially metabolic, autoimmune, early oncology
-- ============================================================================

CREATE TABLE dose_response_results (
    result_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    source_id               UUID REFERENCES source_documents(source_id),
    source_page             INTEGER,
    endpoint_name           TEXT NOT NULL,       -- what's on the y-axis
    dose_unit               TEXT,                -- 'mg', 'mg/kg', 'mg QD', 'mg Q2W'
    -- Per-dose data
    dose_levels             JSONB NOT NULL,
    -- dose_levels[] structure:
    -- {
    --   dose: "36mg",
    --   dose_numeric: 36,
    --   n_patients: 48,
    --   response_value: -12.4,
    --   response_ci: [-14.8, -10.0],
    --   key_safety: {any_AE_pct: 0.72, serious_AE_pct: 0.04, discontinuation_pct: 0.06}
    -- }
    -- Dose-response relationship
    dose_response_trend     TEXT,                -- 'monotonic_increasing', 'plateau', 'inverted_u', 'flat', 'unclear'
    plateau_dose            TEXT,                -- dose at which response plateaus
    recommended_phase3_dose TEXT,                -- RP2D or proposed registrational dose
    therapeutic_index_note  TEXT,                -- balance of efficacy vs safety across doses
    extraction_confidence   NUMERIC,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dose_response_trial ON dose_response_results(trial_id);
COMMENT ON TABLE dose_response_results IS 'Dose-response relationships — especially important for Phase 1/2 data in metabolic, autoimmune, and rare disease';

-- ============================================================================
-- PATIENT-LEVEL RESPONSE RECORDS (cross-linked)
-- ============================================================================

CREATE TABLE patient_responses (
    patient_response_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id              UUID REFERENCES data_vintages(vintage_id),
    arm_name                TEXT,
    patient_index           INTEGER,    -- bar position on waterfall, lane on swimmer, trace on spider

    -- Cross-link confidence (only populate when high)
    cross_link_confidence   NUMERIC,    -- 0-1; only populate patient_responses when > 0.7

    -- Response depth (from waterfall)
    best_pct_change         NUMERIC,
    best_overall_response   TEXT,       -- 'CR', 'CRi', 'CRh', 'nCR', 'VGPR', 'sCR', 'PR', 'MR', 'SD', 'PD', 'NE'
    confirmed_response      BOOLEAN,
    time_to_response_months NUMERIC,
    assessment_criteria     TEXT,

    -- Response durability (from swimmer)
    duration_of_response_months NUMERIC,
    dor_censored                BOOLEAN,
    time_on_treatment_months    NUMERIC,
    reason_off_treatment        TEXT,    -- 'PD', 'toxicity', 'death', 'withdrawal', 'CR_protocol_stop', 'other'
    still_on_treatment          BOOLEAN,
    response_deepened           BOOLEAN,
    response_deepening_timeline JSONB,   -- [{month: 3, status: "PR"}, {month: 9, status: "CR"}]

    -- Tumor dynamics (from spider)
    tumor_measurements      JSONB,      -- [{week: 0, pct_change: 0}, {week: 8, pct_change: -42}]
    nadir_pct_change        NUMERIC,
    nadir_timepoint_weeks   INTEGER,
    post_nadir_trajectory   TEXT,       -- 'sustained', 'slow_regrowth', 'rapid_regrowth', 'mixed'

    -- Biomarker context (from waterfall color-coding)
    biomarker_status        JSONB,      -- {PD_L1_TPS: ">=50%", TMB: "high", MSI: "MSS", driver: "KRAS G12C"}
    prior_therapies         JSONB,      -- [{drug_class: "anti-PD1", drug: "pembro", best_response: "PD"}]
    prior_lines_count       INTEGER,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trial_id, vintage_id, patient_index)
);

CREATE INDEX idx_patient_resp_trial ON patient_responses(trial_id);

-- ============================================================================
-- RESPONSE-DURABILITY CROSS-ANALYSIS (computed, per trial per vintage)
-- ============================================================================

CREATE TABLE response_durability_analyses (
    analysis_id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id                    UUID NOT NULL REFERENCES trials(trial_id) ON DELETE CASCADE,
    vintage_id                  UUID REFERENCES data_vintages(vintage_id),
    waterfall_result_id         UUID REFERENCES waterfall_results(result_id),
    swimmer_result_id           UUID REFERENCES swimmer_results(result_id),
    spider_result_id            UUID REFERENCES spider_results(result_id),

    -- Disease context thresholds used
    indication_id               UUID REFERENCES indications(indication_id),
    threshold_context           TEXT,       -- '2L NSCLC IO-pretreated'
    meaningful_threshold        NUMERIC,    -- -30 for RECIST
    deep_threshold              NUMERIC,    -- -50 for 2L NSCLC
    exceptional_threshold       NUMERIC,    -- -80 for 2L NSCLC

    -- Depth-durability correlation (patient-level only when cross_link_confidence > 0.7)
    depth_durability_corr       NUMERIC,    -- Spearman rho
    deep_responder_count        INTEGER,
    deep_responder_median_dor   NUMERIC,
    shallow_responder_median_dor NUMERIC,
    dor_by_response_depth       JSONB,      -- [{bucket: "CR", median_dor: 18.2, n: 12, censored_pct: 0.5}, ...]

    -- Response quality
    cr_durability_median        NUMERIC,
    cr_conversion_rate          NUMERIC,    -- % of PRs that deepened to CR
    cr_conversion_median_time   NUMERIC,
    durable_response_rate       NUMERIC,    -- % with DoR >= threshold
    durable_response_threshold  NUMERIC,    -- 6 or 12 months typically

    -- Kinetics
    median_time_to_response     NUMERIC,
    median_time_to_best_response NUMERIC,
    early_response_rate_8wk     NUMERIC,
    rapid_progressors_pct       NUMERIC,

    -- Resistance
    median_time_to_progression  NUMERIC,
    progression_pattern         TEXT,       -- 'gradual_regrowth', 'sudden_flare', 'new_lesions', 'mixed'
    regrowth_onset_weeks        NUMERIC,

    computed_at                 TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rda_trial ON response_durability_analyses(trial_id);

-- ============================================================================
-- DISEASE-LEVEL COMPETITIVE MODEL
-- ============================================================================

CREATE TABLE treatment_paradigms (
    paradigm_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indication_id           UUID NOT NULL REFERENCES indications(indication_id),
    line_of_therapy         TEXT NOT NULL,
    biomarker_context       TEXT,           -- 'all comers', 'PD-L1>=50%', 'MSI-H', 'del(17p)'
    current_soc_drug_ids    UUID[],         -- FK references to drugs
    emerging_challenger_ids UUID[],
    selection_factors       JSONB,          -- [{factor: "del(17p)", favors_drug_id: "...", reason: "..."}]
    paradigm_shift_risk     TEXT,           -- 'low', 'moderate', 'high', 'imminent'
    key_differentiators     TEXT[],         -- ["oral vs IV", "fixed duration vs continuous"]
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(indication_id, line_of_therapy, biomarker_context)
);

-- ============================================================================
-- REGULATORY EVENTS
-- ============================================================================

CREATE TABLE regulatory_events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_id         UUID NOT NULL REFERENCES drugs(drug_id) ON DELETE CASCADE,
    indication_id   UUID REFERENCES indications(indication_id),
    event_type      TEXT NOT NULL,  -- 'IND_filing', 'breakthrough_therapy', 'fast_track', 'orphan', 'RMAT', 'priority_review', 'NDA_filing', 'BLA_filing', 'approval', 'CRL', 'withdrawal', 'label_expansion', 'PDUFA'
    event_date      DATE,
    agency          TEXT,           -- 'FDA', 'EMA', 'PMDA', 'NMPA'
    details         TEXT,
    source_url      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reg_events_drug ON regulatory_events(drug_id);

-- ============================================================================
-- ADAPTIVE RESPONSE THRESHOLDS
-- ============================================================================

CREATE TABLE response_thresholds (
    threshold_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indication_id       UUID REFERENCES indications(indication_id),
    modality_class      TEXT,       -- 'IO', 'TKI', 'chemo', 'ADC', 'bispecific', 'CAR_T', 'degrader'
    response_criteria   TEXT,       -- 'RECIST_1.1', 'iRECIST', 'IMWG', 'IWG_AML', 'iwCLL', 'Lugano'
    meaningful_threshold NUMERIC,   -- floor for "this drug does something"
    deep_threshold      NUMERIC,    -- 75th percentile for this context
    exceptional_threshold NUMERIC,  -- 90th percentile
    is_categorical      BOOLEAN DEFAULT FALSE,  -- true for heme (CR/VGPR/PR rather than %)
    categorical_levels  TEXT[],     -- ['CR+MRD_neg', 'CR', 'CRi', 'VGPR', 'PR', 'MR', 'SD', 'PD'] for IMWG
    derived_from_n_trials INTEGER,
    percentile_method   TEXT,       -- 'landscape_p75', 'landscape_p90', 'clinical_convention'
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(indication_id, modality_class, response_criteria)
);

-- ============================================================================
-- RSS / NEWS INGESTION TRACKING
-- ============================================================================

CREATE TABLE rss_feeds (
    feed_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feed_name       TEXT NOT NULL,
    feed_url        TEXT NOT NULL UNIQUE,
    feed_type       TEXT,           -- 'company_PR', 'biopharma_news', 'FDA', 'SEC', 'conference'
    poll_interval_minutes INTEGER DEFAULT 30,
    last_polled_at  TIMESTAMPTZ,
    last_item_date  TIMESTAMPTZ,
    active          BOOLEAN DEFAULT TRUE
);

CREATE TABLE rss_items (
    item_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feed_id         UUID REFERENCES rss_feeds(feed_id),
    title           TEXT,
    url             TEXT UNIQUE,
    published_at    TIMESTAMPTZ,
    content_text    TEXT,
    -- Entity resolution results
    resolved_drug_ids   UUID[],
    resolved_company_ids UUID[],
    resolved_target_ids UUID[],
    processing_status   TEXT DEFAULT 'pending',  -- 'pending', 'processed', 'failed', 'irrelevant'
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rss_items_status ON rss_items(processing_status);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- Latest data for each trial (most common query pattern)
CREATE VIEW latest_trial_data AS
SELECT
    t.trial_id, t.trial_name, t.nct_id, t.phase, t.trial_type,
    t.design, t.control_arm, t.line_of_therapy,
    d.canonical_name AS drug_name, d.modality,
    c.ticker, c.name AS company_name,
    ind.disease_name, ind.disease_subtype,
    v.vintage_id, v.disclosure_venue, v.disclosure_date,
    v.data_maturity, v.median_followup_months
FROM trials t
JOIN programs p ON t.program_id = p.program_id
JOIN drugs d ON p.drug_id = d.drug_id
JOIN companies c ON d.company_id = c.company_id
JOIN indications ind ON p.indication_id = ind.indication_id
LEFT JOIN data_vintages v ON v.trial_id = t.trial_id AND v.is_latest = TRUE;

-- Competitive landscape by target
CREATE VIEW target_landscape AS
SELECT
    tgt.gene_symbol AS target,
    tgt.pathway,
    d.canonical_name AS drug_name,
    d.modality,
    c.ticker, c.name AS company_name,
    p.highest_phase,
    p.regulatory_status,
    ind.disease_name,
    p.catalyst_timeline
FROM drug_targets dt
JOIN targets tgt ON dt.target_id = tgt.target_id
JOIN drugs d ON dt.drug_id = d.drug_id
JOIN companies c ON d.company_id = c.company_id
JOIN programs p ON d.drug_id = p.drug_id
JOIN indications ind ON p.indication_id = ind.indication_id
ORDER BY tgt.gene_symbol, p.highest_phase DESC;

-- Competitive landscape by disease
CREATE VIEW disease_landscape AS
SELECT
    ind.disease_name,
    ind.disease_subtype,
    tp.line_of_therapy,
    tp.biomarker_context,
    tgt.gene_symbol AS target,
    d.canonical_name AS drug_name,
    d.modality,
    c.ticker,
    p.highest_phase,
    tp.paradigm_shift_risk
FROM treatment_paradigms tp
JOIN indications ind ON tp.indication_id = ind.indication_id
CROSS JOIN LATERAL unnest(
    COALESCE(tp.current_soc_drug_ids, '{}') || COALESCE(tp.emerging_challenger_ids, '{}')
) AS drug_uid(drug_id)
JOIN drugs d ON d.drug_id = drug_uid.drug_id
JOIN companies c ON d.company_id = c.company_id
JOIN programs p ON d.drug_id = p.drug_id AND p.indication_id = ind.indication_id
LEFT JOIN drug_targets dt ON d.drug_id = dt.drug_id
LEFT JOIN targets tgt ON dt.target_id = tgt.target_id
ORDER BY ind.disease_name, tp.line_of_therapy, p.highest_phase DESC;

-- ISTs in novel indications (BD opportunity signal)
CREATE VIEW ist_novel_indications AS
SELECT
    d.canonical_name AS drug_name,
    c.ticker,
    t.trial_name,
    t.principal_investigator,
    t.pi_institution,
    ind_ist.disease_name AS ist_indication,
    ind_sponsor.disease_name AS sponsor_indication,
    t.phase,
    t.status
FROM trials t
JOIN programs p ON t.program_id = p.program_id
JOIN drugs d ON p.drug_id = d.drug_id
JOIN companies c ON d.company_id = c.company_id
JOIN indications ind_ist ON p.indication_id = ind_ist.indication_id
CROSS JOIN LATERAL (
    SELECT DISTINCT p2.indication_id
    FROM programs p2
    WHERE p2.drug_id = d.drug_id
    AND p2.program_id != p.program_id
) sponsor_progs
JOIN indications ind_sponsor ON sponsor_progs.indication_id = ind_sponsor.indication_id
WHERE t.trial_type = 'IST'
AND t.novel_indication = TRUE;
