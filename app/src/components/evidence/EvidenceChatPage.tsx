import { useState, useRef, useEffect, useCallback, FormEvent } from 'react'
import EvidenceAnswerPanel from './EvidenceAnswerPanel'
import EvidenceSourceSidebar from './EvidenceSourceSidebar'
import type { SearchSource, QueryPlan, SearchMetadata, SearchTiming } from './types'
import './evidence.css'

/* ───────── Types ───────── */

interface ChatTurn {
  id: string
  query: string
  answer: string
  sources: SearchSource[]
  queryPlan: QueryPlan
  timing: SearchTiming
  metadata: SearchMetadata
  loading: boolean
  streamingText: string
  loadingStep: string
  error: string | null
}

function extractFollowups(text: string) {
  const match = text.match(/\{?\{followup\}?\}([\s\S]*?)\{?\{\/followup\}?\}/)
  if (!match) return { cleanAnswer: text, followups: [] as string[] }
  const cleanAnswer = text.replace(/\{?\{followup\}?\}[\s\S]*?\{?\{\/followup\}?\}/, '').trimEnd()
  const followups = match[1].trim().split('\n').map((q: string) => q.trim()).filter(Boolean)
  return { cleanAnswer, followups }
}

/* ───────── Suggested Queries (landing state) ───────── */

const EXAMPLE_QUERIES = [
  "What is the KRAS inhibitor landscape in NSCLC?",
  "Compare ADC platforms across Daiichi Sankyo, AbbVie, and Pfizer",
  "What are the latest Phase 3 readouts in oncology?",
  "What is Nuvalent's clinical pipeline and upcoming catalysts?",
  "Show me GLP-1 competitive landscape including Asian biotechs",
  "Find under-the-radar biotech assets from China and Korea",
]

/* ───────── Main Chat Component ───────── */

export default function EvidenceChatPage() {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [inputQuery, setInputQuery] = useState('')
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null)
  const [highlightedSource, setHighlightedSource] = useState<number | null>(null)

  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputQuery(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
  }, [])

  // Build conversation history for context
  function buildHistory(): Array<{ query: string; answer: string }> {
    return turns
      .filter(t => !t.loading && t.answer)
      .slice(-4) // Last 4 turns for context window
      .map(t => ({
        query: t.query,
        answer: t.answer.slice(0, 2000), // Truncate for token limits
      }))
  }

  // ── Execute a search query ──
  async function executeQuery(queryText: string) {
    const q = queryText.trim()
    if (!q) return

    const turnId = `turn-${Date.now()}`
    const newTurn: ChatTurn = {
      id: turnId,
      query: q,
      answer: '',
      sources: [],
      queryPlan: {},
      timing: {},
      metadata: {},
      loading: true,
      streamingText: '',
      loadingStep: 'classifying',
      error: null,
    }

    setTurns(prev => [...prev, newTurn])
    setActiveTurnId(turnId)
    setInputQuery('')
    // Reset textarea height
    if (inputRef.current) inputRef.current.style.height = 'auto'

    try {
      const history = buildHistory()
      const res = await fetch('/extract/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, history }),
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
              setTurns(prev => prev.map(t =>
                t.id === turnId ? { ...t, loadingStep: event.step } : t
              ))
              if (event.plan) finalPlan = event.plan
              if (event.metadata) finalMetadata = event.metadata
            } else if (event.type === 'token') {
              fullText += event.text
              setTurns(prev => prev.map(t =>
                t.id === turnId ? { ...t, streamingText: fullText, loadingStep: 'streaming' } : t
              ))
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

      setTurns(prev => prev.map(t =>
        t.id === turnId
          ? {
              ...t,
              answer: fullText,
              sources: finalSources,
              queryPlan: finalPlan,
              timing: finalTiming,
              metadata: finalMetadata,
              loading: false,
              streamingText: '',
              loadingStep: '',
            }
          : t
      ))
    } catch (err) {
      setTurns(prev => prev.map(t =>
        t.id === turnId
          ? { ...t, loading: false, error: err instanceof Error ? err.message : String(err) }
          : t
      ))
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    executeQuery(inputQuery)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      executeQuery(inputQuery)
    }
  }

  function handleFollowup(q: string) {
    executeQuery(q)
  }

  // Get sources for the active/latest turn (for sidebar)
  const activeTurn = activeTurnId
    ? turns.find(t => t.id === activeTurnId)
    : turns[turns.length - 1]
  const sidebarSources = activeTurn?.sources || []

  const isEmpty = turns.length === 0

  return (
    <div className="chat-page">
      {/* Main chat area */}
      <div className="chat-main">
        {/* Chat messages scroll area */}
        <div className="chat-messages">
          {isEmpty && (
            <div className="chat-landing">
              <div className="chat-landing-inner">
                <h1 className="chat-landing-title">SatyaBio Intelligence</h1>
                <p className="chat-landing-subtitle">
                  Ask anything about biotech — clinical trials, pipelines, competitive landscapes.
                  Follow up to dig deeper.
                </p>
                <div className="chat-example-grid">
                  {EXAMPLE_QUERIES.map((q, i) => (
                    <button key={i} className="chat-example-chip" onClick={() => executeQuery(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {turns.map(turn => (
            <div key={turn.id} className="chat-turn" onClick={() => setActiveTurnId(turn.id)}>
              {/* User message */}
              <div className="chat-user-msg">
                <div className="chat-user-bubble">{turn.query}</div>
              </div>

              {/* Assistant response */}
              <div className={`chat-assistant-msg ${turn.id === activeTurnId ? 'chat-active-turn' : ''}`}>
                {turn.loading && !turn.streamingText && (
                  <ChatLoadingState step={turn.loadingStep} />
                )}
                {turn.error && (
                  <div className="chat-error">{turn.error}</div>
                )}
                {(turn.streamingText || turn.answer) && (() => {
                  const text = turn.answer || turn.streamingText
                  const { cleanAnswer, followups } = extractFollowups(text)
                  return (
                    <EvidenceAnswerPanel
                      answer={cleanAnswer.replace(/\{?\{followup\}?\}[\s\S]*$/, '').trimEnd()}
                      sources={turn.sources}
                      queryPlan={turn.queryPlan}
                      onCitationHover={setHighlightedSource}
                      followups={!turn.loading ? followups : undefined}
                      onFollowupClick={handleFollowup}
                      streaming={turn.loading}
                    />
                  )
                })()}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Persistent input bar at bottom */}
        <div className="chat-input-bar">
          <form className="chat-input-form" onSubmit={handleSubmit}>
            <textarea
              ref={inputRef}
              className="chat-input"
              value={inputQuery}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={isEmpty ? "Ask about biotech..." : "Follow up..."}
              rows={1}
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={!inputQuery.trim() || turns.some(t => t.loading)}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </form>
          <p className="chat-disclaimer">
            SatyaBio searches clinical trials, documents, FDA data, PubMed, and global biotech intelligence.
          </p>
        </div>
      </div>

      {/* Source sidebar — shows sources for the active turn */}
      {sidebarSources.length > 0 && (
        <aside className="chat-sidebar">
          <EvidenceSourceSidebar
            sources={sidebarSources}
            highlightedSource={highlightedSource}
          />
        </aside>
      )}
    </div>
  )
}

/* ───────── Loading indicator ───────── */

function ChatLoadingState({ step }: { step: string }) {
  const steps: Record<string, string> = {
    classifying: 'Analyzing your question...',
    searching: 'Searching trials, documents & databases...',
    synthesizing: 'Synthesizing evidence...',
    streaming: 'Writing response...',
  }

  return (
    <div className="chat-loading">
      <div className="chat-loading-dots">
        <span /><span /><span />
      </div>
      <span className="chat-loading-label">{steps[step] || 'Thinking...'}</span>
    </div>
  )
}
