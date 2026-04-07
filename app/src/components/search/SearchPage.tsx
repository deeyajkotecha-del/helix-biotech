import { useState, useRef, useEffect, useCallback } from 'react'
import SearchBar from './SearchBar'
import AnswerPanel from './AnswerPanel'
import SourceSidebar from './SourceSidebar'
import LandingHero from './LandingHero'
import type { SearchResult, SearchSource, QueryPlan, SearchMetadata, SearchTiming } from './types'
import './search.css'

// Extract follow-up questions from answer text
function extractFollowups(text: string) {
  const match = text.match(/\{?\{followup\}?\}([\s\S]*?)\{?\{\/followup\}?\}/)
  if (!match) return { cleanAnswer: text, followups: [] as string[] }
  const cleanAnswer = text.replace(/\{?\{followup\}?\}[\s\S]*?\{?\{\/followup\}?\}/, '').trimEnd()
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

function generateId(): string {
  return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

// ── Types ──

interface ThreadTurn {
  id: number
  query: string
  result: SearchResult | null
  streamingText: string
  loading: boolean
  loadingStep: string
  error: string | null
}

interface ConversationSummary {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
  message_count: number
}

// ── API helpers ──

async function fetchConversations(): Promise<ConversationSummary[]> {
  try {
    const res = await fetch('/api/search/conversations')
    if (!res.ok) return []
    const data = await res.json()
    return data.conversations || []
  } catch { return [] }
}

async function fetchConversation(id: string) {
  try {
    const res = await fetch(`/api/search/conversations/${id}`)
    if (!res.ok) return null
    return await res.json()
  } catch { return null }
}

async function saveMessage(payload: {
  conversation_id: string
  turn_index: number
  query: string
  answer?: string
  sources?: SearchSource[]
  metadata?: SearchMetadata
  timing?: SearchTiming
  query_plan?: QueryPlan
  title?: string
}) {
  try {
    await fetch('/api/search/conversations/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch { /* silent fail — don't break UX for persistence issues */ }
}

async function deleteConversation(id: string) {
  try {
    await fetch(`/api/search/conversations/${id}`, { method: 'DELETE' })
  } catch { /* silent */ }
}


// ============================================================
// MAIN COMPONENT
// ============================================================

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [thread, setThread] = useState<ThreadTurn[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [activeTurnId, setActiveTurnId] = useState<number | null>(null)
  const [highlightedSource, setHighlightedSource] = useState<number | null>(null)

  // History sidebar
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [showHistory, setShowHistory] = useState(false)

  const threadEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null!)
  const nextId = useRef(0)

  // Load conversation list on mount
  useEffect(() => {
    fetchConversations().then(setConversations)
  }, [])

  // Refresh conversation list when a thread completes
  const refreshConversations = useCallback(() => {
    fetchConversations().then(setConversations)
  }, [])

  // Build conversation history for context passing
  function getHistory(): Array<{ role: string; query: string; answer: string }> {
    return thread
      .filter(t => t.result && t.result.answer)
      .map(t => ({
        role: 'conversation',
        query: t.query,
        answer: t.result!.answer.slice(0, 1500),
      }))
  }

  async function handleSearch(searchQuery?: string) {
    const q = (searchQuery || query).trim()
    if (!q) return

    // Create conversation ID if this is the first turn
    let convId = conversationId
    if (!convId) {
      convId = generateId()
      setConversationId(convId)
    }

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

    const updateTurn = (updates: Partial<ThreadTurn>) => {
      setThread(prev => prev.map(t => t.id === turnId ? { ...t, ...updates } : t))
    }

    // Save the query immediately (answer will be updated when done)
    saveMessage({
      conversation_id: convId,
      turn_index: turnId,
      query: q,
      title: turnId === 0 ? q.slice(0, 80) : undefined,
    })

    try {
      const history = getHistory()
      const res = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, history: history.length > 0 ? history : undefined }),
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
          } catch { /* skip */ }
        }
      }

      const result: SearchResult = {
        answer: fullText,
        sources: finalSources,
        query_plan: finalPlan,
        timing: finalTiming,
        metadata: finalMetadata,
      }

      updateTurn({ result, streamingText: '', loading: false, loadingStep: '' })

      // Persist the completed answer
      saveMessage({
        conversation_id: convId,
        turn_index: turnId,
        query: q,
        answer: fullText,
        sources: finalSources,
        metadata: finalMetadata,
        timing: finalTiming,
        query_plan: finalPlan,
      })
      refreshConversations()

    } catch (err) {
      updateTurn({
        error: err instanceof Error ? err.message : String(err),
        loading: false,
        loadingStep: '',
      })
    }
  }

  // Load a past conversation
  async function loadConversation(id: string) {
    const data = await fetchConversation(id)
    if (!data || !data.messages) return

    setConversationId(id)
    const turns: ThreadTurn[] = data.messages.map((m: { turn_index: number; query: string; answer: string; sources: SearchSource[]; metadata: SearchMetadata; timing: SearchTiming; query_plan: QueryPlan }) => ({
      id: m.turn_index,
      query: m.query,
      result: m.answer ? {
        answer: m.answer,
        sources: m.sources || [],
        metadata: m.metadata || {},
        timing: m.timing || {},
        query_plan: m.query_plan || {},
      } : null,
      streamingText: '',
      loading: false,
      loadingStep: '',
      error: null,
    }))

    setThread(turns)
    nextId.current = turns.length > 0 ? Math.max(...turns.map(t => t.id)) + 1 : 0
    setActiveTurnId(turns.length > 0 ? turns[turns.length - 1].id : null)
    setShowHistory(false)
  }

  function startNewThread() {
    setThread([])
    setConversationId(null)
    setActiveTurnId(null)
    setQuery('')
    nextId.current = 0
    setShowHistory(false)
    refreshConversations()
  }

  async function handleDeleteConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    await deleteConversation(id)
    if (conversationId === id) startNewThread()
    refreshConversations()
  }

  // Auto-scroll
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

  const activeTurn = thread.find(t => t.id === activeTurnId)
  const activeSources = activeTurn?.result?.sources || []
  const hasThread = thread.length > 0
  const isAnyLoading = thread.some(t => t.loading)

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
          {activeTurn?.result && (
            <div className="query-meta">
              {activeTurn.result.metadata && (
                <span className="meta-badge">
                  {activeTurn.result.metadata.trials_found ?? 0} trials
                  {' \u00B7 '}
                  {activeTurn.result.metadata.papers_found ?? 0} papers
                  {(activeTurn.result.metadata.rag_chunks_retrieved ?? 0) > 0 &&
                    ` \u00B7 ${activeTurn.result.metadata.rag_chunks_retrieved} docs`}
                </span>
              )}
              {activeTurn.result.timing && (
                <span className="meta-time">{activeTurn.result.timing.total}s</span>
              )}
            </div>
          )}
          <button
            className="thread-history-btn"
            onClick={() => { setShowHistory(!showHistory); refreshConversations() }}
            title="Chat history"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 8v4l3 3"/>
              <circle cx="12" cy="12" r="10"/>
            </svg>
            History
          </button>
          {hasThread && (
            <button className="thread-new-btn" onClick={startNewThread} title="New search thread">
              + New
            </button>
          )}
        </div>
      </nav>

      {/* History sidebar overlay */}
      {showHistory && (
        <div className="history-overlay" onClick={() => setShowHistory(false)}>
          <div className="history-sidebar" onClick={e => e.stopPropagation()}>
            <div className="history-header">
              <h3>Search History</h3>
              <button className="history-close" onClick={() => setShowHistory(false)}>&times;</button>
            </div>
            <button className="history-new-btn" onClick={startNewThread}>
              + New Search
            </button>
            <div className="history-list">
              {conversations.length === 0 && (
                <p className="history-empty">No previous searches yet</p>
              )}
              {conversations.map(conv => (
                <div
                  key={conv.id}
                  className={`history-item ${conv.id === conversationId ? 'history-item-active' : ''}`}
                  onClick={() => loadConversation(conv.id)}
                >
                  <div className="history-item-title">{conv.title}</div>
                  <div className="history-item-meta">
                    {conv.message_count} {conv.message_count === 1 ? 'turn' : 'turns'}
                    {conv.updated_at && (
                      <> &middot; {formatTimeAgo(conv.updated_at)}</>
                    )}
                    <button
                      className="history-item-delete"
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      title="Delete conversation"
                    >
                      &times;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Landing or Thread */}
      {!hasThread ? (
        <>
          <div className="search-container search-hero">
            <SearchBar
              query={query}
              setQuery={setQuery}
              onSearch={() => handleSearch()}
              loading={false}
              compact={false}
              inputRef={inputRef}
            />
          </div>
          <LandingHero examples={EXAMPLE_QUERIES} onExampleClick={(q) => handleSearch(q)} />
        </>
      ) : (
        <div className="thread-layout">
          <div className="thread-content-area">
            <div className="thread-scroll">
              {thread.map(turn => {
                const isActive = turn.id === activeTurnId
                return (
                  <div
                    key={turn.id}
                    className={`thread-turn ${isActive ? 'thread-turn-active' : ''}`}
                    onClick={() => !turn.loading && turn.result && setActiveTurnId(turn.id)}
                  >
                    <div className="thread-query">
                      <div className="thread-query-text">{turn.query}</div>
                    </div>
                    <div className="thread-answer">
                      {turn.loading && !turn.streamingText && (
                        <LoadingState query={turn.query} step={turn.loadingStep} />
                      )}
                      {turn.error && <ErrorState message={turn.error} />}
                      {turn.streamingText && !turn.result && (
                        <AnswerPanel
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
                          <AnswerPanel
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

            {activeSources.length > 0 && (
              <aside className="source-sidebar">
                <SourceSidebar
                  sources={activeSources}
                  highlightedSource={highlightedSource}
                />
              </aside>
            )}
          </div>

          <div className="thread-input-bar">
            <SearchBar
              query={query}
              setQuery={setQuery}
              onSearch={() => handleSearch()}
              loading={isAnyLoading}
              compact={true}
              inputRef={inputRef}
              placeholder="Ask a follow-up question..."
            />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Helper components ──

function formatTimeAgo(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = now - then
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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
