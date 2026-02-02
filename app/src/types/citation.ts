export interface Source {
  id: number;
  title: string;
  authors: string[] | null;
  publication_date: string | null;
  source_type: 'journal_article' | 'sec_filing' | 'conference_poster' | 'internal_document' | 'presentation';
  journal_name: string | null;
  doi: string | null;
  pmid: string | null;
  url: string | null;
  pdf_path: string | null;
  abstract: string | null;
  uploaded_by: number;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  id: number;
  source_id: number;
  report_ticker: string;
  section_name: string;
  citation_number: number;
  context_text: string | null;
  pdf_page: number | null;
  pdf_highlight: string | null;
  created_at: string;
}

export interface CitationWithSource extends Citation {
  source: Source;
}

export interface ReportCitationsResponse {
  report_ticker: string;
  citations: CitationWithSource[];
  total: number;
}

export interface CitationContextValue {
  citations: CitationWithSource[];
  activeSource: Source | null;
  activePdfPage: number | null;
  sidebarOpen: boolean;
  loadCitations: (ticker: string) => Promise<void>;
  openSource: (citation: CitationWithSource) => void;
  closeSidebar: () => void;
  getCitationByNumber: (section: string, number: number) => CitationWithSource | undefined;
}
