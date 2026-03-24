import { useState, useRef, useEffect } from 'react'
import SearchBar from './SearchBar'
import AnswerPanel from './AnswerPanel'
import SourceSidebar from './SourceSidebar'
import LandingHero from './LandingHero'
import type { SearchResult, SearchSource, QueryPlan, SearchMetadata, SearchTiming } from './types'
import './search.css'

// Extract follow-up questions from answer text
function extractFollowups(text: string) {
  const match = text.match(/\{\{followup\}\}([\s\S]*?)\{\{\/followup\}\}/)
  if (!match) return { cleanAnswer: text, followups: [] as string[] }
  const cleanAnswer = text.replace(/\{\{followup\}\}[\s\S]*?\{\{\/followup\}\}/, '').trimEnd()
  const followups = match[1].trim().split('\n').map(q => q.trim()).filter(Boolean)
  return { cleanAnswer, followups }
}

const EXAMPLE_QUERIES = [
  "What is the KRAS landscape in NSCLC?",
  "Compare inavolisib vs alpelisib vs RLY-2608 in HR+ breast cancer",
  "What are the Alzheimer's drug targets and approaches?",
  "Tell me about daraxonrasib (RMC-6236)",
  "What Phase 3 ADC trials are active in solid tumors?",
  "What is Nuvalent's clinical pipeline?",
]

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [loadingStep, setLoadingStep] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [highlightedSource, setHighlightedSource] = useState<number | null>(null)
  const answerRef = useRef<HTMLDivElement>(null)

  async function handleSearch(searchQuery?: string) {
    const q = searchQuery || query
    if (!q.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)
    setStreamingText('')
    setLoadingStep('classifying')
    setQuery(q)

    try {
      const res = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `Server error: ${res.status}`)
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullText = ''
      let finalSources: SearchSource[] = []
      let finalPlan: QueryPlan = {}
      let finalMetadata: SearchMetadata = {}
      let finalTiming: SearchTiming = {}

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))

            if (event.type === 'step') {
              setLoadingStep(event.step)
              if (event.plan) finalPlan = event.plan
              if (event.metadata) finalMetadata = event.metadata
            } else if (event.type === 'token') {
              fullText += event.text
              setStreamingText(fullText)
              setLoadingStep('streaming')
            } else if (event.type === 'done') {
              finalSources = event.sources || []
              finalPlan = { ...finalPlan, ...event.query_plan }
              finalMetadata = event.metadata || finalMetadata
              finalTiming = event.timing || {}
            }
          } catch {
            // skip malformed lines
          }
        }
      }

      setResult({
        answer: fullText,
        sources: finalSources,
        query_plan: finalPlan,
        timing: finalTiming,
        metadata: finalMetadata,
      })
      setStreamingText('')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
      setLoadingStep('')
    }
  }

  function handleExampleClick(q: string) {
    setQuery(q)
    handleSearch(q)
  }

  // Scroll to answer when it loads
  useEffect(() => {
    if (result && answerRef.current) {
      answerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [result])

  const hasResult = !!(result || loading || error || streamingText)

  return (
    <div className="search-app">
      {/* Navbar */}
      <nav className="navbar">
        <div className="nav-left">
          <a href="/" className="nav-logo">
            Satya<span>Bio</span>
          </a>
          <div className="nav-links">
            <a href="/search" className="active">Search</a>
            <a href="/extract/">Analyst</a>
            <a href="/companies">Companies</a>
            <a href="/targets">Landscapes</a>
          </div>
        </div>
        <div className="nav-right">
          {result && (
            <div className="query-meta">
              {result.metadata && (
                <span className="meta-badge">
                  {result.metadata.trials_found ?? 0} trials
                  {' \u00B7 '}
                  {result.metadata.papers_found ?? 0} papers
                  {(result.metadata.rag_chunks_retrieved ?? 0) > 0 &&
                    ` \u00B7 ${result.metadata.rag_chunks_retrieved} docs`}
                </span>
              )}
              {result.timing && (
                <span className="meta-time">{result.timing.total}s</span>
              )}
            </div>
          )}
        </div>
      </nav>

      {/* Search bar — always visible */}
      <div className={`search-container ${hasResult ? 'search-compact' : 'search-hero'}`}>
        <SearchBar
          query={query}
          setQuery={setQuery}
          onSearch={() => handleSearch()}
          loading={loading}
          compact={hasResult}
        />
      </div>

      {/* Landing or Results */}
      {!hasResult ? (
        <LandingHero examples={EXAMPLE_QUERIES} onExampleClick={handleExampleClick} />
      ) : (
        <div className="results-layout" ref={answerRef}>
          <main className="answer-main">
            {loading && !streamingText && <LoadingState query={query} step={loadingStep} />}
            {error && <ErrorState message={error} />}
            {streamingText && !result && (
              <AnswerPanel
                answer={streamingText.replace(/\{\{followup\}\}[\s\S]*$/, '').trimEnd()}
                sources={[]}
                queryPlan={null}
                onCitationHover={setHighlightedSource}
                streaming={true}
              />
            )}
            {result && (() => {
              const { cleanAnswer, followups } = extractFollowups(result.answer)
              return (
                <AnswerPanel
                  answer={cleanAnswer}
                  sources={result.sources}
                  queryPlan={result.query_plan}
                  onCitationHover={setHighlightedSource}
                  followups={followups}
                  onFollowupClick={handleExampleClick}
                />
              )
            })()}
          </main>
          {result && result.sources && result.sources.length > 0 && (
            <aside className="source-sidebar">
              <SourceSidebar
                sources={result.sources}
                highlightedSource={highlightedSource}
              />
            </aside>
          )}
        </div>
      )}
    </div>
  )
}

function LoadingState({ query, step }: { query: string; step: string }) {
  const stepOrder: Record<string, number> = { classifying: 0, searching: 1, synthesizing: 2, streaming: 3 }
  const currentIdx = stepOrder[step] ?? 0

  const steps = [
    { label: 'Analyzing query' },
    { label: 'Searching clinical trials, literature, FDA, and documents' },
    { label: 'Synthesizing relevant information' },
  ]

  return (
    <div className="loading-state">
      <p className="loading-query">{query}</p>
      <div className="loading-steps">
        {steps.map((s, i) => {
          const isDone = i < currentIdx
          const isActive = i === currentIdx
          const cls = isDone ? 'step-done' : isActive ? 'step-active' : 'step-pending'
          return (
            <div key={i} className={`loading-step ${cls}`}>
              <div className="step-icon">
                {isDone ? '\u2713' : isActive ? '\u25CF' : '\u25CB'}
              </div>
              <span className="step-label">{s.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-state">
      <p className="error-title">Something went wrong</p>
      <p className="error-message">{message}</p>
    </div>
  )
}
