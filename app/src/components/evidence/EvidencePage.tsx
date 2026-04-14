import { useState, useRef, useEffect, useCallback, FormEvent } from 'react'
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

/* ── Types ── */

interface ThreadTurn {
  id: number
  query: string
  result: SearchResult | null
  streamingText: string
  loading: boolean
  loadingStep: string
  error: string | null
}

/* ── Main Component ── */

export default function EvidencePage() {
  const [query, setQuery] = useState('')
  const [thread, setThread] = useState<ThreadTurn[]>([])
  const [activeTurnId, setActiveTurnId] = useState<number | null>(null)
  const [highlightedSource, setHighlightedSource] = useState<number | null>(null)

  const threadEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const nextId = useRef(0)

  // Build conversation history for follow-ups
  function getHistory(): Array<{ query: string; answer: string }> {
    return thread
      .filter(t => t.result && t.result.answer)
      .slice(-4)
      .map(t => ({
        query: t.query,
        answer: t.result!.answer.slice(0, 2000),
      }))
  }

  async function handleSearch(searchQuery?: string) {
    const q = (searchQuery || query).trim()
    if (!q) return

    const turnId = nextId.current++
    const newTurn: ThreadTurn = {
      id: turnId,
      query: q,
      result: null,
      streamingText: '',
      loading: true,
      loadingStep: 'classifying',
      error: null,
    }

    setThread(prev => [...prev, newTurn])
    setQuery('')
    setActiveTurnId(turnId)
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }

    const updateTurn = (updates: Partial<ThreadTurn>) => {
      setThread(prev => prev.map(t => t.id === turnId ? { ...t, ...updates } : t))
    }

    try {
      const history = getHistory()
      const res = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, history: history.length > 0 ? history : undefined }),
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
              updateTurn({ loadingStep: event.step })
              if (event.plan) finalPlan = event.plan
              if (event.metadata) finalMetadata = event.metadata
            } else if (event.type === 'token') {
              fullText += event.text
              updateTurn({ streamingText: fullText, loadingStep: 'streaming' })
            } else if (event.type === 'done') {
              finalSources = event.sources || []
              finalPlan = { ...finalPlan, ...event.query_plan }
              finalMetadata = event.metadata || finalMetadata
              finalTiming = event.timing || {}
              if (event.corrected_answer) fullText = event.corrected_answer
            }
          } catch { /* skip malformed */ }
        }
      }

      updateTurn({
        result: {
          answer: fullText,
          sources: finalSources,
          query_plan: finalPlan,
          timing: finalTiming,
          metadata: finalMetadata,
        },
        streamingText: '',
        loading: false,
        loadingStep: '',
      })
    } catch (err) {
      updateTurn({
        error: err instanceof Error ? err.message : String(err),
        loading: false,
        loadingStep: '',
      })
    }
  }

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (thread.length > 0 && threadEndRef.current) {
      threadEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [thread, thread[thread.length - 1]?.streamingText, thread[thread.length - 1]?.result])

  // Focus input after search completes
  useEffect(() => {
    const lastTurn = thread[thread.length - 1]
    if (lastTurn && !lastTurn.loading && inputRef.current) {
      inputRef.current.focus()
    }
  }, [thread])

  // Textarea auto-resize
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuery(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
  }, [])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    handleSearch()
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const activeTurn = thread.find(t => t.id === activeTurnId)
  const activeSources = activeTurn?.result?.sources || []
  const hasThread = thread.length > 0
  const isAnyLoading = thread.some(t => t.loading)

  return (
    <div className="search-page">
      {!hasThread ? (
        /* ── Landing state: centered search + examples ── */
        <>
          <div className="ev-search-container ev-search-hero">
            <form className="ev-search-bar" onSubmit={handleSubmit}>
              <div className="ev-search-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.3-4.3"/>
                </svg>
              </div>
              <input
                type="text"
                className="ev-search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search across 60 companies, trials, enrichment data, and global biotech..."
                autoFocus
              />
              <button type="submit" className="ev-search-button" disabled={!query.trim()}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14"/>
                  <path d="m12 5 7 7-7 7"/>
                </svg>
              </button>
            </form>
          </div>
          <EvidenceLanding examples={EXAMPLE_QUERIES} onExampleClick={(q) => handleSearch(q)} />
        </>
      ) : (
        /* ── Thread state: messages + persistent input bar ── */
        <div className="ev-thread-layout">
          <div className="ev-thread-content">
            {/* Scrollable messages area */}
            <div className="ev-thread-scroll">
              {thread.map(turn => {
                const isActive = turn.id === activeTurnId
                return (
                  <div
                    key={turn.id}
                    className={`ev-thread-turn ${isActive ? 'ev-thread-turn-active' : ''}`}
                    onClick={() => !turn.loading && turn.result && setActiveTurnId(turn.id)}
                  >
                    {/* User query bubble */}
                    <div className="ev-thread-query">
                      <div className="ev-thread-query-text">{turn.query}</div>
                    </div>

                    {/* Assistant response */}
                    <div className="ev-thread-answer">
                      {turn.loading && !turn.streamingText && (
                        <LoadingState query={turn.query} step={turn.loadingStep} />
                      )}
                      {turn.error && <ErrorState message={turn.error} />}
                      {turn.streamingText && !turn.result && (
                        <EvidenceAnswerPanel
                          answer={turn.streamingText.replace(/\{?\{followup\}?\}[\s\S]*$/, '').trimEnd()}
                          sources={[]}
                          queryPlan={null}
                          onCitationHover={setHighlightedSource}
                          streaming={true}
                        />
                      )}
                      {turn.result && (() => {
                        const { cleanAnswer, followups } = extractFollowups(turn.result.answer)
                        return (
                          <EvidenceAnswerPanel
                            answer={cleanAnswer}
                            sources={turn.result.sources}
                            queryPlan={turn.result.query_plan}
                            onCitationHover={setHighlightedSource}
                            followups={followups}
                            onFollowupClick={(q) => handleSearch(q)}
                          />
                        )
                      })()}
                    </div>
                  </div>
                )
              })}
              <div ref={threadEndRef} />
            </div>

            {/* Source sidebar for active turn */}
            {activeSources.length > 0 && (
              <aside className="ev-source-sidebar">
                <EvidenceSourceSidebar
                  sources={activeSources}
                  highlightedSource={highlightedSource}
                />
              </aside>
            )}
          </div>

          {/* Persistent input bar at bottom */}
          <div className="ev-thread-input-bar">
            <form className="ev-thread-input-form" onSubmit={handleSubmit}>
              <textarea
                ref={inputRef}
                className="ev-thread-input"
                value={query}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask a follow-up question..."
                rows={1}
                disabled={isAnyLoading}
              />
              <button
                type="submit"
                className="ev-thread-send-btn"
                disabled={!query.trim() || isAnyLoading}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Helper components ── */

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
