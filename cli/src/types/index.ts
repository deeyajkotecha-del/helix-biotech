/**
 * Type definitions for the Helix CLI
 */

// Company data from our backend API
export interface Company {
  ticker: string;
  name: string;
  description?: string;
  sector?: string;
  lead_asset?: string;
  indication?: string;
  stage?: string;
  weight?: number;
  website?: string;
}

// SEC EDGAR filing information
export interface Filing {
  accessionNumber: string;  // Unique ID for the filing
  filingDate: string;       // When it was filed
  reportDate: string;       // Period the report covers
  form: string;             // "10-K", "10-Q", etc.
  primaryDocument: string;  // Main document filename
  fileUrl: string;          // Full URL to the filing
}

// SEC company submission data (from SEC API)
export interface SECSubmission {
  cik: string;
  entityType: string;
  name: string;
  tickers: string[];
  filings: {
    recent: {
      accessionNumber: string[];
      filingDate: string[];
      reportDate: string[];
      form: string[];
      primaryDocument: string[];
    };
  };
}

// ============================================
// NEW: Biotech-specific analysis types
// ============================================

// Company info from analysis
export interface AnalyzedCompany {
  name: string;
  ticker: string;
  marketCap: string | null;
  employees: number | null;
}

// Pipeline drug information
export interface PipelineItem {
  drug: string;                    // Drug name or code (e.g., "mRNA-1273", "Keytruda")
  phase: string;                   // Preclinical | Phase 1 | Phase 2 | Phase 3 | NDA/BLA Filed | Approved
  indication: string;              // What disease/condition it treats
  status?: string;                 // Brief status update
  catalyst?: string | null;        // Next expected event (data readout, PDUFA date, etc.)
}

// Financial health metrics
export interface Financials {
  cash: string | null;             // Cash and equivalents (e.g., "$2.1B")
  cashDate: string | null;         // As of date for cash position
  quarterlyBurnRate: string | null; // Estimated quarterly burn rate
  runwayMonths: number | null;     // Estimated months of cash runway
  revenue: string | null;          // Latest revenue if any
  revenueSource: string | null;    // Where revenue comes from (product sales, royalties, etc.)
}

// Partnership/collaboration info
export interface Partnership {
  partner: string;                 // Partner company name
  type: string;                    // licensing, collaboration, acquisition, etc.
  value: string | null;            // Deal value if mentioned
  details: string;                 // Brief description
}

// Full analysis result from LLM
export interface AnalysisResult {
  company: AnalyzedCompany;
  pipeline: PipelineItem[];
  financials: Financials;
  fdaInteractions: string[];       // Approvals, CRLs, breakthrough designations, etc.
  partnerships: Partnership[];
  risks: string[];                 // Top 3-5 key risks
  recentEvents: string[];          // Material events from reporting period
  analystSummary: string;          // 2-3 sentence investment thesis
  rawResponse?: string;            // Full LLM response for debugging
}

// LLM provider interface - allows swapping between Ollama/Claude
export interface LLMProvider {
  name: string;
  analyze(filingContent: string, ticker: string): Promise<AnalysisResult>;
}

// Configuration
export interface Config {
  apiUrl: string;
  llmProvider: 'ollama' | 'claude';
  ollamaUrl: string;
  ollamaModel: string;
  claudeApiKey?: string;
  claudeModel: string;
  secUserAgent: string;
}
