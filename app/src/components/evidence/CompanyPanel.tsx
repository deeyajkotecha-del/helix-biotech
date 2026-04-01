import { useState, useEffect } from 'react'
import type { Company, CompanyListResponse } from './types'
import DeckAnalyzerPanel from './DeckAnalyzerPanel'

// ============================================================
// Types for documents + webcasts
// ============================================================

interface DocumentItem {
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

// ============================================================
// Types for webcast data
// ============================================================

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

interface WebcastSearchResult {
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
  onCompanySearch: (ticker: string, name: string) => void
}

export default function CompanyPanel({ onCompanySearch }: Props) {
  const [data, setData] = useState<CompanyListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedCat, setExpandedCat] = useState<string | null>(null)

  // Company detail view
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [companyDocs, setCompanyDocs] = useState<DocumentItem[]>([])
  const [companyWebcasts, setCompanyWebcasts] = useState<WebcastItem[]>([])
  const [loadingWebcasts, setLoadingWebcasts] = useState(false)

  // Deck analyzer
  const [analyzingDoc, setAnalyzingDoc] = useState<DocumentItem | null>(null)

  // Webcast counts per ticker (fetched once)
  const [webcastCounts, setWebcastCounts] = useState<Record<string, number>>({})

  // Transcript viewer
  const [viewingTranscript, setViewingTranscript] = useState<TranscriptView | null>(null)
  const [loadingTranscript, setLoadingTranscript] = useState(false)

  // Search within company webcasts
  const [webcastSearch, setWebcastSearch] = useState('')
  const [searchResults, setSearchResults] = useState<WebcastSearchResult[]>([])
  const [searching, setSearching] = useState(false)

  // Ingest form
  const [showIngest, setShowIngest] = useState(false)
  const [ingestForm, setIngestForm] = useState({
    url: '',
    title: '',
    event_date: '',
    event_type: 'webcast',
    transcript_text: '',
  })
  const [ingesting, setIngesting] = useState(false)
  const [ingestMsg, setIngestMsg] = useState('')

  // Load companies + webcast counts
  useEffect(() => {
    async function init() {
      try {
        const [compRes, wcRes] = await Promise.all([
          fetch('/extract/api/companies'),
          fetch('/extract/api/webcasts/library?limit=200'),
        ])
        if (compRes.ok) {
          setData(await compRes.json())
        }
        if (wcRes.ok) {
          const wcData = await wcRes.json()
          const counts: Record<string, number> = {}
          for (const w of (wcData.webcasts || [])) {
            const t = (w.ticker || '').toUpperCase()
            if (t) counts[t] = (counts[t] || 0) + 1
          }
          setWebcastCounts(counts)
        }
      } catch (e) {
        console.error('CompanyPanel init:', e)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  // Load documents + webcasts for selected company
  async function selectCompany(company: Company) {
    setSelectedCompany(company)
    setCompanyDocs([])
    setCompanyWebcasts([])
    setSearchResults([])
    setWebcastSearch('')
    setViewingTranscript(null)
    setAnalyzingDoc(null)
    setShowIngest(false)
    setIngestMsg('')
    setLoadingWebcasts(true)

    try {
      const [docsRes, wcRes] = await Promise.all([
        fetch(`/extract/api/documents?ticker=${company.ticker}&limit=50`),
        fetch(`/extract/api/webcasts/library?ticker=${company.ticker}&limit=50`),
      ])
      if (docsRes.ok) {
        const data = await docsRes.json()
        setCompanyDocs(data.documents || [])
      }
      if (wcRes.ok) {
        const data = await wcRes.json()
        setCompanyWebcasts(data.webcasts || [])
      }
    } catch (e) {
      console.error('Load company data:', e)
    } finally {
      setLoadingWebcasts(false)
    }
  }

  // View transcript
  async function handleViewTranscript(docId: number) {
    setLoadingTranscript(true)
    try {
      const res = await fetch(`/extract/api/webcasts/transcript/${docId}`)
      if (res.ok) {
        setViewingTranscript(await res.json())
      }
    } catch (e) {
      console.error('Load transcript:', e)
    } finally {
      setLoadingTranscript(false)
    }
  }

  // Search within company webcasts
  async function handleWebcastSearch() {
    if (!webcastSearch.trim() || !selectedCompany) return
    setSearching(true)
    setSearchResults([])

    try {
      const res = await fetch('/extract/api/webcasts/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: webcastSearch.trim(),
          ticker: selectedCompany.ticker,
          top_k: 10,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setSearchResults(data.results || [])
      }
    } catch (e) {
      console.error('Webcast search:', e)
    } finally {
      setSearching(false)
    }
  }

  // Ingest a webcast for this company
  async function handleIngest() {
    if (!selectedCompany) return
    setIngesting(true)
    setIngestMsg('')

    const hasTranscript = ingestForm.transcript_text.trim().length > 0
    const hasUrl = ingestForm.url.trim().length > 0

    try {
      let res: Response

      if (hasTranscript) {
        // Direct ingest
        res = await fetch('/extract/api/webcasts/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcript_text: ingestForm.transcript_text,
            title: ingestForm.title,
            ticker: selectedCompany.ticker,
            company_name: selectedCompany.name,
            event_date: ingestForm.event_date || new Date().toISOString().split('T')[0],
            event_type: ingestForm.event_type,
            source_url: ingestForm.url,
          }),
        })
      } else if (hasUrl) {
        // Process URL
        res = await fetch('/extract/api/webcasts/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: ingestForm.url,
            title: ingestForm.title,
            ticker: selectedCompany.ticker,
            company_name: selectedCompany.name,
            event_date: ingestForm.event_date || new Date().toISOString().split('T')[0],
            event_type: ingestForm.event_type,
          }),
        })
      } else {
        setIngestMsg('Provide a URL or paste a transcript.')
        setIngesting(false)
        return
      }

      const data = await res.json()
      if (data.status === 'ok') {
        setIngestMsg(`Done! ${data.chunks_stored} chunks, ${data.word_count} words.`)
        setShowIngest(false)
        setIngestForm({ url: '', title: '', event_date: '', event_type: 'webcast', transcript_text: '' })
        // Refresh
        selectCompany(selectedCompany)
        // Update count
        setWebcastCounts(prev => ({
          ...prev,
          [selectedCompany.ticker.toUpperCase()]: (prev[selectedCompany.ticker.toUpperCase()] || 0) + 1,
        }))
      } else if (data.status === 'already_exists') {
        setIngestMsg(data.message || 'Already ingested.')
      } else {
        setIngestMsg(`Error: ${data.error || 'Failed'}`)
      }
    } catch (e) {
      setIngestMsg('Network error.')
    } finally {
      setIngesting(false)
    }
  }

  function formatDate(d: string) {
    if (!d) return ''
    try {
      return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    } catch { return d }
  }

  function formatDocType(dt: string) {
    const map: Record<string, string> = {
      sec_10k: '10-K', sec_10q: '10-Q', sec_8k: '8-K',
      investor_deck: 'Deck', clinical_trials: 'Trials',
      poster: 'Poster', publication: 'Paper', other: 'Doc',
    }
    return map[dt] || dt?.replace(/_/g, ' ') || 'Doc'
  }

  function eventTypeLabel(t: string) {
    const map: Record<string, string> = {
      webcast: 'Webcast',
      earnings_call: 'Earnings',
      investor_day: 'Investor Day',
      conference: 'Conference',
      r_and_d_day: 'R&D Day',
    }
    return map[t] || t
  }

  if (loading) return <div className="ev-panel-loading">Loading companies...</div>
  if (!data) return <div className="ev-panel-empty">Could not load companies</div>

  // ============================================================
  // Render: Transcript viewer
  // ============================================================
  if (viewingTranscript) {
    return (
      <div className="ev-company-panel">
        <div className="ev-panel-header">
          <button className="ev-back-btn" onClick={() => setViewingTranscript(null)}>
            &larr; Back
          </button>
          <h3>Transcript</h3>
        </div>

        <div className="ev-transcript-meta">
          <div className="ev-trial-nct">{viewingTranscript.document?.ticker}</div>
          <h4 className="ev-webcast-card-title">{viewingTranscript.document?.title}</h4>
          <div className="ev-webcast-card-meta">
            <span>{formatDate(viewingTranscript.document?.date)}</span>
            <span>{viewingTranscript.document?.word_count?.toLocaleString()} words</span>
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
    )
  }

  // ============================================================
  // Render: Deck Analyzer (full takeover)
  // ============================================================
  if (analyzingDoc && selectedCompany) {
    return (
      <DeckAnalyzerPanel
        document={{
          id: analyzingDoc.id,
          ticker: analyzingDoc.ticker,
          company_name: analyzingDoc.company_name || selectedCompany.name,
          title: analyzingDoc.title,
          doc_type: analyzingDoc.doc_type,
        }}
        onBack={() => setAnalyzingDoc(null)}
        allDocuments={companyDocs.map(d => ({
          id: d.id,
          ticker: d.ticker,
          company_name: d.company_name || selectedCompany.name,
          title: d.title,
          doc_type: d.doc_type,
        }))}
      />
    )
  }

  // ============================================================
  // Render: Company detail view (docs + webcasts)
  // ============================================================
  if (selectedCompany) {
    return (
      <div className="ev-company-panel">
        <div className="ev-panel-header">
          <button className="ev-back-btn" onClick={() => setSelectedCompany(null)}>
            &larr; All Companies
          </button>
        </div>

        {/* Company info */}
        <div className="ev-company-detail-header">
          <span className="ev-company-ticker">{selectedCompany.ticker}</span>
          <h3 className="ev-company-detail-name">{selectedCompany.name}</h3>
          <div className="ev-company-detail-stats">
            <span>{selectedCompany.doc_page_count} doc pages</span>
            <span>{companyWebcasts.length} webcasts</span>
          </div>
        </div>

        {/* Actions */}
        <div className="ev-company-actions">
          <button
            className="ev-forecast-btn"
            onClick={() => onCompanySearch(selectedCompany.ticker, selectedCompany.name)}
          >
            Search docs
          </button>
          <button
            className="ev-forecast-btn ev-btn-secondary"
            onClick={() => { setShowIngest(!showIngest); setIngestMsg('') }}
          >
            + Add webcast
          </button>
        </div>

        {/* Ingest form (collapsible) */}
        {showIngest && (
          <div className="ev-webcast-ingest-section">
            <input
              className="ev-forecast-input ev-webcast-form-input"
              placeholder="Title (e.g., Q4 2025 Earnings Call)"
              value={ingestForm.title}
              onChange={e => setIngestForm(p => ({ ...p, title: e.target.value }))}
            />
            <div className="ev-webcast-form-row">
              <input
                className="ev-forecast-input"
                type="date"
                value={ingestForm.event_date}
                onChange={e => setIngestForm(p => ({ ...p, event_date: e.target.value }))}
                style={{ width: '50%' }}
              />
              <select
                className="ev-param-select"
                value={ingestForm.event_type}
                onChange={e => setIngestForm(p => ({ ...p, event_type: e.target.value }))}
                style={{ width: '48%' }}
              >
                <option value="webcast">Webcast</option>
                <option value="earnings_call">Earnings Call</option>
                <option value="investor_day">Investor Day</option>
                <option value="conference">Conference</option>
                <option value="r_and_d_day">R&D Day</option>
              </select>
            </div>

            <input
              className="ev-forecast-input ev-webcast-form-input"
              placeholder="Webcast URL (optional)"
              value={ingestForm.url}
              onChange={e => setIngestForm(p => ({ ...p, url: e.target.value }))}
            />

            <textarea
              className="ev-webcast-textarea"
              placeholder="Or paste transcript text here..."
              value={ingestForm.transcript_text}
              onChange={e => setIngestForm(p => ({ ...p, transcript_text: e.target.value }))}
              rows={5}
            />

            <button
              className="ev-forecast-btn"
              onClick={handleIngest}
              disabled={ingesting || (!ingestForm.url.trim() && !ingestForm.transcript_text.trim())}
              style={{ marginTop: '6px' }}
            >
              {ingesting ? 'Processing...' : 'Ingest'}
            </button>

            {ingestMsg && (
              <div className={`ev-webcast-ingest-result ${ingestMsg.startsWith('Error') ? 'error' : 'success'}`}>
                {ingestMsg}
              </div>
            )}
          </div>
        )}

        {/* Document library */}
        {companyDocs.length > 0 && (
          <div className="ev-deck-docs-section">
            <h4 className="ev-deck-section-title">Documents ({companyDocs.length})</h4>
            {companyDocs.map(doc => (
              <div key={doc.id} className="ev-deck-doc-row">
                <div className="ev-deck-doc-info">
                  <span className="ev-webcast-type-tag">{formatDocType(doc.doc_type)}</span>
                  <span className="ev-deck-doc-title">{doc.title}</span>
                </div>
                <div className="ev-deck-doc-actions">
                  {doc.date && <span className="ev-webcast-date">{formatDate(doc.date)}</span>}
                  <button
                    className="ev-deck-analyze-btn"
                    onClick={() => setAnalyzingDoc(doc)}
                    title="Analyze slide by slide"
                  >
                    Analyze
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Webcast search */}
        {companyWebcasts.length > 0 && (
          <div className="ev-webcast-company-search">
            <div className="ev-forecast-input-row">
              <input
                className="ev-forecast-input"
                placeholder="Search this company's webcasts..."
                value={webcastSearch}
                onChange={e => setWebcastSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleWebcastSearch()}
                disabled={searching}
              />
              <button
                className="ev-forecast-btn"
                onClick={handleWebcastSearch}
                disabled={searching || !webcastSearch.trim()}
              >
                {searching ? '...' : 'Go'}
              </button>
            </div>
          </div>
        )}

        {/* Search results */}
        {searchResults.length > 0 && (
          <div className="ev-webcast-results">
            <div className="ev-webcast-results-header">
              <span>Search results</span>
              <button className="ev-back-btn" onClick={() => { setSearchResults([]); setWebcastSearch('') }}>
                Clear
              </button>
            </div>
            {searchResults.map((r, i) => (
              <div key={i} className="ev-webcast-result-card">
                <div className="ev-webcast-result-header">
                  <span className="ev-webcast-date">{formatDate(r.date)}</span>
                  {r.section_title && <span className="ev-webcast-section-tag">{r.section_title}</span>}
                  <span className="ev-webcast-score">{(r.score * 100).toFixed(0)}%</span>
                </div>
                <h5 className="ev-webcast-result-title">{r.title}</h5>
                <p className="ev-webcast-result-excerpt">
                  {r.content.slice(0, 250)}{r.content.length > 250 ? '...' : ''}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Webcast list */}
        {!searchResults.length && (
          <div className="ev-webcast-library">
            {loadingWebcasts && <div className="ev-panel-loading">Loading webcasts...</div>}

            {!loadingWebcasts && companyWebcasts.length === 0 && (
              <div className="ev-panel-empty-msg">
                <p>No webcasts yet for {selectedCompany.ticker}.</p>
                <p className="ev-panel-tip">Use "+ Add webcast" above to transcribe one.</p>
              </div>
            )}

            {companyWebcasts.map(w => (
              <div
                key={w.id}
                className="ev-webcast-card"
                onClick={() => handleViewTranscript(w.id)}
              >
                <div className="ev-webcast-card-header">
                  <span className="ev-webcast-type-tag">{eventTypeLabel(w.event_type || 'webcast')}</span>
                  <span className="ev-webcast-date">{formatDate(w.date)}</span>
                </div>
                <h4 className="ev-webcast-card-title">{w.title || 'Untitled'}</h4>
                <div className="ev-webcast-card-meta">
                  {w.duration_display && <span>{w.duration_display}</span>}
                  <span>{w.word_count?.toLocaleString()} words</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {loadingTranscript && <div className="ev-panel-loading">Loading transcript...</div>}
      </div>
    )
  }

  // ============================================================
  // Render: Company list (default view)
  // ============================================================
  const filtered = filter.trim()
    ? data.companies.filter(c =>
        c.ticker.toLowerCase().includes(filter.toLowerCase()) ||
        c.name.toLowerCase().includes(filter.toLowerCase()) ||
        c.category_label.toLowerCase().includes(filter.toLowerCase())
      )
    : null

  return (
    <div className="ev-company-panel">
      <div className="ev-panel-header">
        <h3>Company Universe</h3>
        <span className="ev-panel-count">{data.total} companies</span>
      </div>

      <input
        className="ev-panel-search"
        placeholder="Filter by ticker, name, or category..."
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />

      <div className="ev-panel-list">
        {filtered ? (
          filtered.map(c => (
            <CompanyRow
              key={c.ticker}
              company={c}
              webcastCount={webcastCounts[c.ticker.toUpperCase()] || 0}
              onClick={() => selectCompany(c)}
            />
          ))
        ) : (
          Object.entries(data.by_category).map(([cat, group]) => (
            <div key={cat} className="ev-cat-group">
              <button
                className={`ev-cat-header ${expandedCat === cat ? 'expanded' : ''}`}
                onClick={() => setExpandedCat(prev => prev === cat ? null : cat)}
              >
                <span className="ev-cat-label">{group.label}</span>
                <span className="ev-cat-count">{group.count}</span>
                <span className="ev-cat-arrow">{expandedCat === cat ? '\u25BC' : '\u25B6'}</span>
              </button>
              {expandedCat === cat && (
                <div className="ev-cat-companies">
                  {group.companies.map((c: any) => (
                    <CompanyRow
                      key={c.ticker}
                      company={c}
                      webcastCount={webcastCounts[c.ticker.toUpperCase()] || 0}
                      onClick={() => selectCompany(c)}
                    />
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ============================================================
// Company Row — shows doc pages + webcast count
// ============================================================

function CompanyRow({ company, webcastCount, onClick }: {
  company: Company
  webcastCount: number
  onClick: () => void
}) {
  return (
    <button className="ev-company-row" onClick={onClick}>
      <span className="ev-company-ticker">{company.ticker}</span>
      <span className="ev-company-name">{company.name}</span>
      <span className="ev-company-stats">
        <span className="ev-company-pages">{company.doc_page_count} pages</span>
        {webcastCount > 0 && (
          <span className="ev-company-webcasts">{webcastCount} wc</span>
        )}
      </span>
    </button>
  )
}
