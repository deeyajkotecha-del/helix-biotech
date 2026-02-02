export interface Company {
  ticker: string;
  name: string;
  description?: string;
  sector?: string;
  website?: string;
  lead_asset?: string;
}

export interface PubMedArticle {
  pmid: string;
  title: string;
  authors: string[];
  journal: string;
  pub_date: string;
  abstract?: string;
  doi?: string;
}

export interface ClinicalTrial {
  nct_id: string;
  title: string;
  status: string;
  phase?: string;
  conditions: string[];
  interventions: string[];
  start_date?: string;
  completion_date?: string;
  enrollment?: number;
  sponsor?: string;
}

export interface PipelineProgram {
  name: string;
  indication: string;
  stage: string;
  description?: string;
}

export interface Patent {
  patent_number?: string;
  title: string;
  expiry_date?: string;
  status?: string;
}

export interface Executive {
  name: string;
  title: string;
  background?: string;
}

export interface BLUFSection {
  summary: string;
  investment_thesis: string;
  key_catalysts: string[];
  key_risks: string[];
  recommendation?: string;
}

export interface PipelineSection {
  lead_asset?: string;
  lead_asset_stage?: string;
  lead_asset_indication?: string;
  programs: PipelineProgram[];
  total_programs: number;
}

export interface PatentLegalSection {
  key_patents: Patent[];
  nearest_expiry?: string;
  litigation: string[];
  regulatory_notes: string[];
}

export interface ManagementSection {
  ceo?: Executive;
  key_executives: Executive[];
  recent_changes: string[];
  board_highlights: string[];
}

export interface PreclinicalSection {
  pubmed_articles: PubMedArticle[];
  conference_posters: Record<string, unknown>[];
  key_findings: string[];
  mechanism_of_action?: string;
}

export interface ClinicalTrialsSection {
  active_trials: ClinicalTrial[];
  completed_trials: ClinicalTrial[];
  upcoming_readouts: {
    trial_id: string;
    title: string;
    expected_date: string;
    phase?: string;
  }[];
  total_trials: number;
  phases_summary: Record<string, number>;
}

export interface ReportSections {
  bluf?: BLUFSection;
  pipeline?: PipelineSection;
  patent_legal?: PatentLegalSection;
  management?: ManagementSection;
  preclinical?: PreclinicalSection;
  clinical_trials?: ClinicalTrialsSection;
}

export interface Report {
  ticker: string;
  company_name: string;
  generated_at: string;
  sections: ReportSections;
  data_sources: string[];
  cache_expires_at?: string;
}
