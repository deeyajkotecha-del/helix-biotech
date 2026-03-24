/** Shared types for the SatyaBio search feature */

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
