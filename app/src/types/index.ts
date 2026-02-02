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

export interface TrialResult {
  trial_name: string;
  nct_id?: string;
  phase?: string;
  n: number;
  endpoint: string;
  result: string;
  comparator?: string;
  p_value?: string;
  citation_number?: number;
}

export interface TrialDesign {
  n_enrolled: number;
  arms?: string[];
  duration?: string;
  primary_endpoint?: string;
}

export interface TrialSafety {
  any_ae_percent?: number;
  serious_ae_percent?: number;
  discontinuations_percent?: number;
  notable_signals?: string[];
  citation_number?: number;
}

export interface ClinicalTrialData {
  trial_name: string;
  nct_id?: string;
  phase: string;
  indication: string;
  design?: TrialDesign;
  results?: {
    primary?: {
      endpoint: string;
      result: string;
      comparator?: string;
      p_value?: string;
      citation_number?: number;
    };
    secondary?: Array<{
      endpoint: string;
      result: string;
      citation_number?: number;
    }>;
    safety?: TrialSafety;
  };
  presentation_date?: string;
  conference?: string;
}

export interface Catalyst {
  event: string;
  expected_date?: string;
  actual_date?: string;
  status: 'completed' | 'upcoming' | 'planned';
  outcome?: string;
  significance?: string;
  stock_reaction_1d?: string;
}

export interface Competitor {
  drug_name: string;
  company: string;
  mechanism?: string;
  stage: string;
  efficacy?: string;
  differentiation?: string;
  citation_number?: number;
}

export interface SatyaView {
  bull_thesis: string;
  bear_thesis: string;
  key_question: string;
}

export interface ProgramMechanism {
  modality?: string;
  delivery?: string;
  description: string;
  target_biology?: string;
  dosing?: string;
}

export interface PartnershipFinancials {
  upfront?: number;
  equity_investment?: number;
  development_milestones_potential?: number;
  commercial_milestones_potential?: number;
  total_deal_value?: number;
  royalties?: string;
  received_to_date?: number;
}

export interface Partnership {
  partner: string;
  established?: string;
  status?: string;
  programs?: string[];
  programs_covered?: string[];
  financial_terms?: PartnershipFinancials;
  responsibilities?: {
    arwr?: string;
    partner?: string;
  };
  key_terms?: string;
  citation_number?: number;
}

export interface ClinicalFigure {
  id: string;
  source: string;
  source_url?: string;
  slide_number: number;
  image_path: string;
  figure_type?: string;
  title?: string;
  description?: string;
  extracted_data?: Record<string, string | number>;
  analysis?: string[];
  limitations?: string[];
  competitive_context?: string;
  trial?: string;
  citation_number?: number;
}

export interface PipelineProgram {
  name: string;
  aliases?: string[];
  indication: string;
  stage: string;
  description?: string;
  target?: string;
  partner?: string;
  key_data?: string;
  next_catalyst?: string;
  // Expanded data
  satya_view?: SatyaView;
  mechanism?: ProgramMechanism;
  clinical_data?: ClinicalTrialData[];
  competitors?: Competitor[];
  catalysts?: Catalyst[];
  partnership?: Partnership;
  figures?: ClinicalFigure[];
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
  partnerships?: Partnership[];
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

export type {
  Source,
  Citation,
  CitationWithSource,
  ReportCitationsResponse,
  CitationContextValue,
} from './citation';
