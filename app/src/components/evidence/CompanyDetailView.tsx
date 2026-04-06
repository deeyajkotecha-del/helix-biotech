import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Company, DocumentItem, WebcastItem, WebcastSearchResult, TranscriptView } from './types'
import DeckAnalyzerPanel from './DeckAnalyzerPanel'
import TranscriptViewer from './TranscriptViewer'
import WebcastIngestForm from './WebcastIngestForm'

interface Props {
  company: Company
  onBack: () => void
  onCompanySearch: (ticker: string, name: string) => void
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
    investor_deck: 'Deck', investor_presentation: 'Deck',
    clinical_trials: 'Trials', poster: 'Poster',
    publication: 'Paper', news_article: 'News',
    press_release: 'Press', sec_filing: 'SEC',
    other: 'Doc',
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

export default function CompanyDetailView({ company, onBack, onCompanySearch }: Props) {
  const navigateTo = useNavigate()
  const [companyDocs, setCompanyDocs] = useState<DocumentItem[]>([])
  const [companyWebcasts, setCompanyWebcasts] = useState<WebcastItem[]>([])
  const [loadingData, setLoadingData] = useState(true)

  // Sub-views
  const [analyzingDoc, setAnalyzingDoc] = useState<DocumentItem | null>(null)
  const [viewingTranscript, setViewingTranscript] = useState<TranscriptView | null>(null)
  const [loadingTranscript, setLoadingTranscript] = useState(false)

  // Webcast search
  const [webcastSearch, setWebcastSearch] = useState('')
  const [searchResults, setSearchResults] = useState<WebcastSearchResult[]>([])
  const [searching, setSearching] = useState(false)

  // Ingest
  const [showIngest, setShowIngest] = useState(false)

  // Load docs + webcasts when company changes
  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoadingData(true)
      setCompanyDocs([])
      setCompanyWebcasts([])
      setSearchResults([])
      setWebcastSearch('')
      setViewingTranscript(null)
      setAnalyzingDoc(null)
      setShowIngest(false)

      try {
        const [docsRes, wcRes] = await Promise.all([
          fetch(`/extract/api/documents?ticker=${company.ticker}&limit=50`),
          fetch(`/extract/api/webcasts/library?ticker=${company.ticker}&limit=50`),
        ])
        if (cancelled) return
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
        if (!cancelled) setLoadingData(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [company.ticker])

  async function handleViewTranscript(docId: number) {
    setLoadingTranscript(true)
    try {
      const res = await fetch(`/extract/api/webcasts/transcript/${docId}`)
      if (res.ok) setViewingTranscript(await res.json())
    } catch (e) {
      console.error('Load transcript:', e)
    } finally {
      setLoadingTranscript(false)
    }
  }

  async function handleWebcastSearch() {
    if (!webcastSearch.trim()) return
    setSearching(true)
    setSearchResults([])
    try {
      const res = await fetch('/extract/api/webcasts/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: webcastSearch.trim(), ticker: company.ticker, top_k: 10 }),
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

  function refreshWebcasts() {
    // Re-fetch webcasts after ingest
    fetch(`/extract/api/webcasts/library?ticker=${company.ticker}&limit=50`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setCompanyWebcasts(data.webcasts || []) })
      .catch(() => {})
    setShowIngest(false)
  }

  // --- Sub-view: Transcript ---
  if (viewingTranscript) {
    return <TranscriptViewer transcript={viewingTranscript} onBack={() => setViewingTranscript(null)} />
  }

  // --- Sub-view: Deck Analyzer ---
  if (analyzingDoc) {
    return (
      <DeckAnalyzerPanel
        document={{
          id: analyzingDoc.id,
          ticker: analyzingDoc.ticker,
          company_name: analyzingDoc.company_name || company.name,
          title: analyzingDoc.title,
          doc_type: analyzingDoc.doc_type,
        }}
        onBack={() => setAnalyzingDoc(null)}
        allDocuments={companyDocs.map(d => ({
          id: d.id,
          ticker: d.ticker,
          company_name: d.company_name || company.name,
          title: d.title,
          doc_type: d.doc_type,
        }))}
      />
    )
  }

  // --- Main detail view ---
  return (
    <div className="ev-company-panel">
      <div className="ev-panel-header">
        <button className="ev-back-btn" onClick={onBack}>&larr; All Companies</button>
      </div>

      {/* Company info */}
      <div className="ev-company-detail-header">
        <span className="ev-company-ticker">{company.ticker}</span>
        <h3 className="ev-company-detail-name">{company.name}</h3>
        <div className="ev-company-detail-stats">
          <span>{company.doc_page_count} doc pages</span>
          <span>{companyWebcasts.length} webcasts</span>
        </div>
      </div>

      {/* Actions */}
      <div className="ev-company-actions">
        <button className="ev-forecast-btn" onClick={() => onCompanySearch(company.ticker, company.name)}>
          Search docs
        </button>
        <button className="ev-forecast-btn ev-btn-secondary" onClick={() => setShowIngest(!showIngest)}>
          + Add webcast
        </button>
      </div>

      {/* Ingest form */}
      {showIngest && <WebcastIngestForm company={company} onIngested={refreshWebcasts} />}

      {loadingData && <div className="ev-panel-loading">Loading...</div>}

      {/* Documents */}
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
                <button className="ev-deck-analyze-btn" onClick={() => {
                  const params = new URLSearchParams({
                    doc: String(doc.id),
                    ticker: doc.ticker,
                    company: doc.company_name || company.name,
                    title: doc.title,
                  })
                  navigateTo(`/deck-analyzer?${params.toString()}`)
                }} title="Analyze slide by slide (full view)">
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
            <button className="ev-forecast-btn" onClick={handleWebcastSearch} disabled={searching || !webcastSearch.trim()}>
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
            <button className="ev-back-btn" onClick={() => { setSearchResults([]); setWebcastSearch('') }}>Clear</button>
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
          {!loadingData && companyWebcasts.length === 0 && (
            <div className="ev-panel-empty-msg">
              <p>No webcasts yet for {company.ticker}.</p>
              <p className="ev-panel-tip">Use "+ Add webcast" above to transcribe one.</p>
            </div>
          )}
          {companyWebcasts.map(w => (
            <div key={w.id} className="ev-webcast-card" onClick={() => handleViewTranscript(w.id)}>
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
