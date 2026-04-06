import { useState, useRef, useEffect } from 'react'
import EvidenceSearchBar from './EvidenceSearchBar'
import EvidenceAnswerPanel from './EvidenceAnswerPanel'
import EvidenceSourceSidebar from './EvidenceSourceSidebar'
import EvidenceLanding from './EvidenceLanding'
import type { SearchResult, SearchSource, QueryPlan, SearchMetadata, SearchTiming } from './types'
import './evidence.css'

function extractFollowups(text: string) {
  const match = text.match(/\{?\{followup\}?\}([\s\S]*?)\{?\{\/followup\}?\}/)
  if (!match) return { cleanAnswer: text, followups: [] as string[] }
  const cleanAnswer = text.replace(/\{?\{followup\}?\}[\s\S]*?\{?\{\/followup\}?\}/, '').trimEnd()
  const followups = match[1].trim().split('\n').map(q => q.trim()).filter(Boolean)
  return { cleanAnswer, followups }
}

const EXAMPLE_QUERIES = [
  "What is the KRAS inhibitor landscape in NSCLC?",
  "Compare ADC platforms across Daiichi Sankyo, AbbVie, and Pfizer",
  "What are the latest Phase 3 readouts in oncology?",
  "Find under-the-radar biotech assets from China and Korea",
  "What is Nuvalent's clinical pipeline and upcoming catalysts?",
  "Show me GLP-1 competitive landscape including Asian biotechs",
]

export default function EvidencePage() {
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
      const res = await fetch('/extract/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        if (res.status === 503) {
          throw new Error('Search is being set up — the document library and company browser are available now. Full AI search is coming soon.')
        }
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
        buffer = lines.pop() || ''

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
              // Use corrected answer if post-processing changed it
              if (event.corrected_answer) {
                fullText = event.corrected_answer
              }
            }
          } catch { /* skip malformed */ }
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


  useEffect(() => {
    if (result && answerRef.current) {
      answerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [result])

  const hasResult = !!(result || loading || error || streamingText)

  return (
    <div className="search-page">
      {/* Search bar */}
      <div className={`ev-search-container ${hasResult ? 'ev-search-compact' : 'ev-search-hero'}`}>
        <EvidenceSearchBar
          query={query}
          setQuery={setQuery}
          onSearch={() => handleSearch()}
          loading={loading}
          compact={hasResult}
        />
      </div>

      {/* Landing or Results */}
      {!hasResult ? (
        <EvidenceLanding examples={EXAMPLE_QUERIES} onExampleClick={handleExampleClick} />
      ) : (
        <div className="ev-results-layout" ref={answerRef}>
          <main className="ev-answer-main">
            {loading && !streamingText && <LoadingState query={query} step={loadingStep} />}
            {error && <ErrorState message={error} />}
            {streamingText && !result && (
              <EvidenceAnswerPanel
                answer={streamingText.replace(/\{?\{followup\}?\}[\s\S]*$/, '').trimEnd()}
                sources={[]}
                queryPlan={null}
                onCitationHover={setHighlightedSource}
                streaming={true}
              />
            )}
            {result && (() => {
              const { cleanAnswer, followups } = extractFollowups(result.answer)
              return (
                <EvidenceAnswerPanel
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
            <aside className="ev-source-sidebar">
              <EvidenceSourceSidebar
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
    { label: 'Searching clinical trials, documents, enrichment & regional data' },
    { label: 'Synthesizing evidence with citations' },
  ]

  return (
    <div className="ev-loading-state">
      <p className="ev-loading-query">{query}</p>
      <div className="ev-loading-steps">
        {steps.map((s, i) => {
          const isDone = i < currentIdx
          const isActive = i === currentIdx
          const cls = isDone ? 'step-done' : isActive ? 'step-active' : 'step-pending'
          return (
            <div key={i} className={`ev-loading-step ${cls}`}>
              <div className="ev-step-icon">
                {isDone ? '\u2713' : isActive ? '\u25CF' : '\u25CB'}
              </div>
              <span className="ev-step-label">{s.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  const isSetup = message.includes('being set up')
  return (
    <div className="ev-error-state">
      <p className="ev-error-title">{isSetup ? 'Coming Soon' : 'Something went wrong'}</p>
      <p className="ev-error-message">{message}</p>
    </div>
  )
}
