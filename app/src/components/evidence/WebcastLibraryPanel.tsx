import { useState, useEffect } from 'react'

// ============================================================
// Types
// ============================================================

interface WebcastStatus {
  ready: boolean
  whisper_available: boolean
  database_available: boolean
  voyage_available: boolean
  ffmpeg_available: boolean
  yt_dlp_available: boolean
  whisper_model: string
}

interface WebcastItem {
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

interface SearchResult {
  chunk_id: number
  content: string
  section_title: string
  ticker: string
  company_name: string
  title: string
  date: string
  score: number
}

interface TranscriptView {
  document: WebcastItem
  chunks: Array<{
    chunk_index: number
    section_title: string
    content: string
    token_count: number
  }>
  full_transcript: string
}

// ============================================================
// Main Component
// ============================================================

interface Props {
  onSearch?: (query: string) => void
}

export default function WebcastLibraryPanel({ onSearch: _onSearch }: Props) {
  // Status
  const [status, setStatus] = useState<WebcastStatus | null>(null)
  const [loading, setLoading] = useState(true)

  // Library view
  const [webcasts, setWebcasts] = useState<WebcastItem[]>([])
  const [totalWebcasts, setTotalWebcasts] = useState(0)

  // Search
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  // Transcript viewer
  const [viewingTranscript, setViewingTranscript] = useState<TranscriptView | null>(null)
  const [loadingTranscript, setLoadingTranscript] = useState(false)

  // Ingest form
  const [ingestForm, setIngestForm] = useState({
    url: '',
    title: '',
    ticker: '',
    company_name: '',
    event_date: '',
    event_type: 'webcast',
    transcript_text: '',
  })
  const [ingesting, setIngesting] = useState(false)
  const [ingestResult, setIngestResult] = useState<string>('')

  // Tab state
  const [activeTab, setActiveTab] = useState<'library' | 'search' | 'add'>('library')

  // Initial load
  useEffect(() => {
    async function init() {
      try {
        const [statusRes, libraryRes] = await Promise.all([
          fetch('/extract/api/webcasts/status'),
          fetch('/extract/api/webcasts/library?limit=20'),
        ])

        if (statusRes.ok) {
          setStatus(await statusRes.json())
        }
        if (libraryRes.ok) {
          const data = await libraryRes.json()
          setWebcasts(data.webcasts || [])
          setTotalWebcasts(data.total || 0)
        }
      } catch (e) {
        console.error('Webcast init failed:', e)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  // Search handler
  async function handleSearch() {
    if (!searchQuery.trim()) return
    setSearching(true)
    setSearchResults([])

    try {
      const res = await fetch('/extract/api/webcasts/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim(), top_k: 15 }),
      })
      if (res.ok) {
        const data = await res.json()
        setSearchResults(data.results || [])
      }
    } catch (e) {
      console.error('Webcast search failed:', e)
    } finally {
      setSearching(false)
    }
  }

  // View transcript
  async function handleViewTranscript(documentId: number) {
    setLoadingTranscript(true)
    try {
      const res = await fetch(`/extract/api/webcasts/transcript/${documentId}`)
      if (res.ok) {
        const data = await res.json()
        setViewingTranscript(data)
      }
    } catch (e) {
      console.error('Failed to load transcript:', e)
    } finally {
      setLoadingTranscript(false)
    }
  }

  // Ingest: submit transcript text directly
  async function handleIngestText() {
    if (!ingestForm.transcript_text.trim()) return
    setIngesting(true)
    setIngestResult('')

    try {
      const res = await fetch('/extract/api/webcasts/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript_text: ingestForm.transcript_text,
          title: ingestForm.title,
          ticker: ingestForm.ticker,
          company_name: ingestForm.company_name,
          event_date: ingestForm.event_date || new Date().toISOString().split('T')[0],
          event_type: ingestForm.event_type,
          source_url: ingestForm.url,
        }),
      })
      const data = await res.json()
      if (data.status === 'ok') {
        setIngestResult(`Ingested! ${data.chunks_stored} chunks, ${data.word_count} words.`)
        // Refresh library
        refreshLibrary()
      } else if (data.status === 'already_exists') {
        setIngestResult(data.message || 'Already ingested.')
      } else {
        setIngestResult(`Error: ${data.error || 'Unknown error'}`)
      }
    } catch (e) {
      setIngestResult('Failed to ingest transcript.')
    } finally {
      setIngesting(false)
    }
  }

  // Ingest: process URL via pipeline
  async function handleProcessUrl() {
    if (!ingestForm.url.trim()) return
    setIngesting(true)
    setIngestResult('')

    try {
      const res = await fetch('/extract/api/webcasts/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: ingestForm.url,
          title: ingestForm.title,
          ticker: ingestForm.ticker,
          company_name: ingestForm.company_name,
          event_date: ingestForm.event_date || new Date().toISOString().split('T')[0],
          event_type: ingestForm.event_type,
        }),
      })
      const data = await res.json()
      if (data.status === 'ok') {
        setIngestResult(
          `Transcribed & ingested! ${data.chunks_stored} chunks, ` +
          `${data.word_count} words, ${Math.round(data.duration / 60)}min audio.`
        )
        refreshLibrary()
      } else if (data.capture_js) {
        setIngestResult(
          'Direct download failed. Use the browser capture method: ' +
          'open the webcast in Chrome, then use the "Capture Audio" button.'
        )
      } else {
        setIngestResult(`Error: ${data.error || 'Unknown error'}`)
      }
    } catch (e) {
      setIngestResult('Failed to process webcast URL.')
    } finally {
      setIngesting(false)
    }
  }

  async function refreshLibrary() {
    try {
      const res = await fetch('/extract/api/webcasts/library?limit=20')
      if (res.ok) {
        const data = await res.json()
        setWebcasts(data.webcasts || [])
        setTotalWebcasts(data.total || 0)
      }
    } catch (e) {
      // silent
    }
  }

  // Format date display
  function formatDate(dateStr: string) {
    if (!dateStr) return ''
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  // ============================================================
  // Render: Transcript Viewer overlay
  // ============================================================
  if (viewingTranscript) {
    return (
      <div className="ev-webcast-panel">
        <div className="ev-panel-header">
          <button
            className="ev-back-btn"
            onClick={() => setViewingTranscript(null)}
          >
            &larr; Back
          </button>
          <h3>Transcript</h3>
        </div>

        <div className="ev-transcript-viewer">
          <div className="ev-transcript-meta">
            <div className="ev-trial-nct">{viewingTranscript.document?.ticker}</div>
            <h4 className="ev-trial-title">{viewingTranscript.document?.title}</h4>
            <div className="ev-detail-row">
              <span className="ev-detail-label">Date:</span>
              <span className="ev-detail-value">{formatDate(viewingTranscript.document?.date)}</span>
            </div>
            <div className="ev-detail-row">
              <span className="ev-detail-label">Words:</span>
              <span className="ev-detail-value">{viewingTranscript.document?.word_count?.toLocaleString()}</span>
            </div>
          </div>

          <div className="ev-transcript-text">
            {viewingTranscript.chunks?.map((chunk, i) => (
              <div key={i} className="ev-transcript-chunk">
                {chunk.section_title && (
                  <div className="ev-transcript-section">{chunk.section_title}</div>
                )}
                <p>{chunk.content}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ============================================================
  // Render: Main panel
  // ============================================================
  return (
    <div className="ev-webcast-panel">
      {/* Header */}
      <div className="ev-panel-header">
        <h3>Webcast Library</h3>
        <span className="ev-panel-subtitle">Transcription & search</span>
      </div>

      {/* Status */}
      {!loading && status && (
        <div className="ev-forecast-status">
          <span className={`ev-status-dot ${status.ready ? 'ready' : 'not-ready'}`} />
          <span className="ev-status-label">
            {status.ready
              ? `Ready (Whisper ${status.whisper_model})`
              : 'Pipeline loading...'}
          </span>
          {totalWebcasts > 0 && (
            <span className="ev-webcast-count">{totalWebcasts} webcasts</span>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="ev-webcast-tabs">
        <button
          className={`ev-webcast-tab ${activeTab === 'library' ? 'active' : ''}`}
          onClick={() => setActiveTab('library')}
        >
          Library ({totalWebcasts})
        </button>
        <button
          className={`ev-webcast-tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Search
        </button>
        <button
          className={`ev-webcast-tab ${activeTab === 'add' ? 'active' : ''}`}
          onClick={() => setActiveTab('add')}
        >
          + Add
        </button>
      </div>

      {/* ============ Library Tab ============ */}
      {activeTab === 'library' && (
        <div className="ev-webcast-library">
          {webcasts.length === 0 && !loading && (
            <div className="ev-panel-empty-msg">
              <p>No webcasts transcribed yet.</p>
              <p className="ev-panel-tip">Use the "+ Add" tab to transcribe a webcast.</p>
            </div>
          )}
          {webcasts.map(w => (
            <div
              key={w.id}
              className="ev-webcast-card"
              onClick={() => handleViewTranscript(w.id)}
            >
              <div className="ev-webcast-card-header">
                <span className="ev-trial-nct">{w.ticker}</span>
                <span className="ev-webcast-date">{formatDate(w.date)}</span>
              </div>
              <h4 className="ev-webcast-card-title">{w.title || 'Untitled Webcast'}</h4>
              <div className="ev-webcast-card-meta">
                <span>{w.company_name}</span>
                {w.duration_display && <span>{w.duration_display}</span>}
                <span>{w.word_count?.toLocaleString()} words</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ============ Search Tab ============ */}
      {activeTab === 'search' && (
        <div className="ev-webcast-search-tab">
          <div className="ev-forecast-search">
            <div className="ev-forecast-input-row">
              <input
                className="ev-forecast-input"
                type="text"
                placeholder="Search webcast transcripts..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                disabled={searching}
              />
              <button
                className="ev-forecast-btn"
                onClick={handleSearch}
                disabled={searching || !searchQuery.trim()}
              >
                {searching ? '...' : 'Search'}
              </button>
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="ev-webcast-results">
              {searchResults.map((r, i) => (
                <div key={i} className="ev-webcast-result-card">
                  <div className="ev-webcast-result-header">
                    <span className="ev-trial-nct">{r.ticker}</span>
                    <span className="ev-webcast-date">{formatDate(r.date)}</span>
                    <span className="ev-webcast-score">{(r.score * 100).toFixed(0)}%</span>
                  </div>
                  <h5 className="ev-webcast-result-title">{r.title}</h5>
                  {r.section_title && (
                    <div className="ev-webcast-section-tag">{r.section_title}</div>
                  )}
                  <p className="ev-webcast-result-excerpt">
                    {r.content.slice(0, 300)}
                    {r.content.length > 300 ? '...' : ''}
                  </p>
                </div>
              ))}
            </div>
          )}

          {searchResults.length === 0 && !searching && searchQuery && (
            <div className="ev-panel-empty-msg">
              <p>No results. Try different search terms.</p>
            </div>
          )}
        </div>
      )}

      {/* ============ Add Tab ============ */}
      {activeTab === 'add' && (
        <div className="ev-webcast-add-tab">
          <div className="ev-webcast-form">
            <label className="ev-forecast-label">Webcast Details</label>

            <input
              className="ev-forecast-input ev-webcast-form-input"
              type="text"
              placeholder="Title (e.g., Structure Q4 Earnings Call)"
              value={ingestForm.title}
              onChange={e => setIngestForm(prev => ({ ...prev, title: e.target.value }))}
            />

            <div className="ev-webcast-form-row">
              <input
                className="ev-forecast-input"
                type="text"
                placeholder="Ticker (e.g., GPCR)"
                value={ingestForm.ticker}
                onChange={e => setIngestForm(prev => ({ ...prev, ticker: e.target.value }))}
                style={{ width: '35%' }}
              />
              <input
                className="ev-forecast-input"
                type="text"
                placeholder="Company name"
                value={ingestForm.company_name}
                onChange={e => setIngestForm(prev => ({ ...prev, company_name: e.target.value }))}
                style={{ width: '63%' }}
              />
            </div>

            <div className="ev-webcast-form-row">
              <input
                className="ev-forecast-input"
                type="date"
                value={ingestForm.event_date}
                onChange={e => setIngestForm(prev => ({ ...prev, event_date: e.target.value }))}
                style={{ width: '50%' }}
              />
              <select
                className="ev-param-select"
                value={ingestForm.event_type}
                onChange={e => setIngestForm(prev => ({ ...prev, event_type: e.target.value }))}
                style={{ width: '48%' }}
              >
                <option value="webcast">Webcast</option>
                <option value="earnings_call">Earnings Call</option>
                <option value="investor_day">Investor Day</option>
                <option value="conference">Conference</option>
                <option value="r_and_d_day">R&D Day</option>
              </select>
            </div>

            {/* Method 1: URL processing */}
            <div className="ev-webcast-method">
              <label className="ev-forecast-label">Option A: Webcast URL</label>
              <div className="ev-forecast-input-row">
                <input
                  className="ev-forecast-input"
                  type="text"
                  placeholder="https://edge.media-server.com/mmc/p/..."
                  value={ingestForm.url}
                  onChange={e => setIngestForm(prev => ({ ...prev, url: e.target.value }))}
                />
                <button
                  className="ev-forecast-btn"
                  onClick={handleProcessUrl}
                  disabled={ingesting || !ingestForm.url.trim()}
                >
                  {ingesting ? '...' : 'Process'}
                </button>
              </div>
            </div>

            {/* Method 2: Paste transcript */}
            <div className="ev-webcast-method">
              <label className="ev-forecast-label">Option B: Paste Transcript</label>
              <textarea
                className="ev-webcast-textarea"
                placeholder="Paste the full transcript text here..."
                value={ingestForm.transcript_text}
                onChange={e => setIngestForm(prev => ({ ...prev, transcript_text: e.target.value }))}
                rows={8}
              />
              <button
                className="ev-forecast-btn"
                onClick={handleIngestText}
                disabled={ingesting || !ingestForm.transcript_text.trim()}
                style={{ marginTop: '8px' }}
              >
                {ingesting ? 'Ingesting...' : 'Ingest Transcript'}
              </button>
            </div>

            {/* Result message */}
            {ingestResult && (
              <div className={`ev-webcast-ingest-result ${ingestResult.startsWith('Error') ? 'error' : 'success'}`}>
                {ingestResult}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading states */}
      {loading && <div className="ev-panel-loading">Loading webcast library...</div>}
      {loadingTranscript && <div className="ev-panel-loading">Loading transcript...</div>}
    </div>
  )
}
