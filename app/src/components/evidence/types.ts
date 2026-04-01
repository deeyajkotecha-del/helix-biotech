/** Types for the Open Evidence page */

export interface Company {
  ticker: string
  name: string
  category: string
  category_label: string
  doc_page_count: number
  total_page_count: number
  ir_url: string | null
  publications_url: string | null
}

export interface CategoryGroup {
  label: string
  count: number
  companies: Company[]
}

export interface CompanyListResponse {
  total: number
  companies: Company[]
  by_category: Record<string, CategoryGroup>
}

export interface SearchSource {
  type: string
  title?: string
  url?: string
  company?: string
  ticker?: string
  doc_type?: string
  ref?: string
  source_name?: string
  pmid?: string
}

export interface QueryPlan {
  query_type?: string
  sources?: string[]
  reasoning?: string
}

export interface SearchMetadata {
  trials_found?: number
  papers_found?: number
  rag_chunks_retrieved?: number
  fda_drugs_found?: number
  global_landscape_assets?: number
  enrichment_available?: boolean
  regional_tracker_available?: boolean
  companies_loaded?: boolean
}

export interface SearchTiming {
  total?: number
  [key: string]: number | undefined
}

export interface SearchResult {
  answer: string
  sources: SearchSource[]
  query_plan: QueryPlan
  timing: SearchTiming
  metadata: SearchMetadata
}

export interface EnrichmentStatus {
  enrichment_ready: boolean
  news_miner_ready: boolean
  global_discovery_ready: boolean
  search_ready: boolean
  drug_db_available: boolean
  rag_available: boolean
}

export interface RegionalStatus {
  news_miner_ready: boolean
  global_discovery_ready: boolean
  regions: string[]
  recent_alerts?: RegionalAlert[]
}

export interface RegionalAlert {
  drug_name: string
  company: string
  region: string
  source: string
  date: string
  summary: string
}

// ============================================================
// Document + Webcast types (used by CompanyPanel subcomponents)
// ============================================================

export interface DocumentItem {
  id: number
  ticker: string
  company_name: string
  title: string
  doc_type: string
  date: string
  word_count: number
  page_count: number
  filename: string
}

export interface WebcastItem {
  id: number
  ticker: string
  company_name: string
  title: string
  date: string
  word_count: number
  embedded_at: string
  source_url?: string
  event_type?: string
  duration_seconds?: number
  duration_display?: string
}

export interface WebcastSearchResult {
  chunk_id: number
  content: string
  section_title: string
  ticker: string
  company_name: string
  title: string
  date: string
  score: number
}

export interface TranscriptView {
  document: WebcastItem
  chunks: Array<{
    chunk_index: number
    section_title: string
    content: string
    token_count: number
  }>
  full_transcript: string
}
