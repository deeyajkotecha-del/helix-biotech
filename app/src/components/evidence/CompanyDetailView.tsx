import { useState, useEffect, useMemo } from 'react'
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

// ============================================================
// Title Cleanup — decode URLs, remove junk, humanize
// ============================================================

function cleanTitle(title: string, ticker: string, companyName: string): string {
  if (!title) return 'Untitled'

  let t = title

  // URL-decode (handle %27, %28, %29, %3B, + as space, etc.)
  try { t = decodeURIComponent(t.replace(/\+/g, ' ')) } catch { /* keep as-is */ }

  // Remove file extensions
  t = t.replace(/\.(pdf|docx?|xlsx?|pptx?|html?|txt|csv)$/i, '')

  // Remove leading [Trials] or [type] tags — we show type separately
  t = t.replace(/^\[.*?\]\s*/, '')

  // Remove ticker prefix if it starts the title (e.g. "DFTX 10-K (2026-02-26)")
  // Keep these as-is since they're SEC filing titles that are already clear

  // Replace underscores with spaces
  t = t.replace(/_/g, ' ')

  // Clean up multiple spaces
  t = t.replace(/\s{2,}/g, ' ').trim()

  // If the title is just a UUID or hash, replace with something useful
  if (/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(t)) {
    return `${companyName} Document`
  }
  if (/^[0-9a-f]{32,}$/i.test(t)) {
    return `${companyName} Document`
  }

  // If title is just a number (like "135542"), label it
  if (/^\d{4,}$/.test(t)) {
    return `${companyName} Document #${t}`
  }

  return t
}


// ============================================================
// Document Categorization
// ============================================================

interface DocCategory {
  key: string
  label: string
  icon: string
  docs: DocumentItem[]
}

const CATEGORY_ORDER = [
  'presentations',
  'sec_annual',
  'sec_quarterly',
  'sec_current',
  'clinical',
  'fda',
  'publications',
  'webcasts_section',
  'other',
]

function categorizeDoc(doc: DocumentItem): string {
  const dt = (doc.doc_type || '').toLowerCase()
  const title = (doc.title || '').toLowerCase()

  // Presentations / Decks
  if (dt.includes('deck') || dt.includes('presentation') || dt.includes('poster')
    || title.includes('presentation') || title.includes('corporate deck')
    || title.includes('investor day') || title.includes('poster')) {
    return 'presentations'
  }

  // SEC Annual (10-K, 20-F)
  if (dt === 'sec_10k' || dt.includes('10-k') || dt.includes('10k')
    || dt.includes('20-f') || dt.includes('20f')
    || title.includes('10-k') || title.includes('20-f')) {
    return 'sec_annual'
  }

  // SEC Quarterly (10-Q, 6-K)
  if (dt === 'sec_10q' || dt.includes('10-q') || dt.includes('10q')
    || dt.includes('6-k') || dt.includes('6k')
    || title.includes('10-q') || title.includes('6-k')) {
    return 'sec_quarterly'
  }

  // SEC Current (8-K)
  if (dt === 'sec_8k' || dt.includes('8-k') || dt.includes('8k')
    || title.includes('8-k')) {
    return 'sec_current'
  }

  // Clinical trials
  if (dt.includes('trial') || dt.includes('clinical')
    || title.includes('clinical trial') || title.includes('active clinical')) {
    return 'clinical'
  }

  // FDA
  if (dt.includes('fda') || title.includes('fda') || title.includes('approval')
    || title.includes('drug label') || title.includes('dailymed')) {
    return 'fda'
  }

  // Publications / Papers
  if (dt.includes('publication') || dt.includes('paper') || dt.includes('pubmed')
    || title.includes('pubmed') || title.includes('journal')) {
    return 'publications'
  }

  return 'other'
}

const CATEGORY_META: Record<string, { label: string; icon: string }> = {
  presentations:   { label: 'Corporate Presentations & Posters', icon: '📊' },
  sec_annual:      { label: 'SEC Annual Filings (10-K / 20-F)',  icon: '📋' },
  sec_quarterly:   { label: 'SEC Quarterly Filings (10-Q / 6-K)', icon: '📄' },
  sec_current:     { label: 'SEC Current Reports (8-K)',          icon: '📑' },
  clinical:        { label: 'Clinical Trials',                    icon: '🧪' },
  fda:             { label: 'FDA & Regulatory',                   icon: '🏛' },
  publications:    { label: 'Publications & Research',            icon: '📚' },
  other:           { label: 'Other Documents',                    icon: '📁' },
}

function groupDocsByCategory(docs: DocumentItem[], ticker: string, companyName: string): DocCategory[] {
  const groups: Record<string, DocumentItem[]> = {}

  for (const doc of docs) {
    const cat = categorizeDoc(doc)
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(doc)
  }

  // Sort each group by date (newest first)
  for (const cat of Object.keys(groups)) {
    groups[cat].sort((a, b) => {
      if (!a.date && !b.date) return 0
      if (!a.date) return 1
      if (!b.date) return -1
      return new Date(b.date).getTime() - new Date(a.date).getTime()
    })
  }

  // Build ordered categories
  const result: DocCategory[] = []
  for (const key of CATEGORY_ORDER) {
    if (groups[key] && groups[key].length > 0) {
      const meta = CATEGORY_META[key] || { label: key, icon: '📄' }
      result.push({
        key,
        label: meta.label,
        icon: meta.icon,
        docs: groups[key],
      })
    }
  }

  return result
}


// ============================================================
// Formatting helpers
// ============================================================

function formatDate(d: string) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch { return d }
}

function formatDateShort(d: string) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  } catch { return d }
}

function formatDocTypeBadge(dt: string) {
  const map: Record<string, string> = {
    sec_10k: '10-K', sec_10q: '10-Q', sec_8k: '8-K',
    sec_20f: '20-F', sec_6k: '6-K',
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


// ============================================================
// Component
// ============================================================

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

  // Collapsed categories
  const [collapsedCats, setCollapsedCats] = useState<Set<string>>(new Set())

  // Group documents into categories
  const docCategories = useMemo(
    () => groupDocsByCategory(companyDocs, company.ticker, company.name),
    [companyDocs, company.ticker, company.name]
  )

  const totalDocs = companyDocs.length

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
      setCollapsedCats(new Set())

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

  function toggleCategory(key: string) {
    setCollapsedCats(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

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
    fetch(`/extract/api/webcasts/library?ticker=${company.ticker}&limit=50`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setCompanyWebcasts(data.webcasts || []) })
      .catch(() => {})
    setShowIngest(false)
  }

  function openDeckAnalyzer(doc: DocumentItem) {
    const params = new URLSearchParams({
      doc: String(doc.id),
      ticker: doc.ticker,
      company: doc.company_name || company.name,
      title: cleanTitle(doc.title, doc.ticker, company.name),
    })
    navigateTo(`/deck-analyzer?${params.toString()}`)
  }

  // --- Sub-view: Transcript ---
  if (viewingTranscript) {
    return <TranscriptViewer transcript={viewingTranscript} onBack={() => setViewingTranscript(null)} />
  }

  // --- Sub-view: Deck Analyzer (legacy fallback) ---
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
          id: d.id, ticker: d.ticker,
          company_name: d.company_name || company.name,
          title: d.title, doc_type: d.doc_type,
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

      {/* Company header */}
      <div className="ev-company-detail-header">
        <span className="ev-company-ticker">{company.ticker}</span>
        <h3 className="ev-company-detail-name">{company.name}</h3>
        <div className="ev-company-detail-stats">
          <span>{totalDocs} documents</span>
          <span>{companyWebcasts.length} webcasts</span>
          <span>{company.doc_page_count} pages indexed</span>
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

      {showIngest && <WebcastIngestForm company={company} onIngested={refreshWebcasts} />}

      {loadingData && <div className="ev-panel-loading">Loading...</div>}

      {/* ---- GROUPED DOCUMENTS ---- */}
      {docCategories.map(cat => (
        <div key={cat.key} className="ev-docgroup">
          <button
            className={`ev-docgroup-header ${collapsedCats.has(cat.key) ? 'collapsed' : ''}`}
            onClick={() => toggleCategory(cat.key)}
          >
            <span className="ev-docgroup-icon">{cat.icon}</span>
            <span className="ev-docgroup-label">{cat.label}</span>
            <span className="ev-docgroup-count">{cat.docs.length}</span>
            <span className="ev-docgroup-arrow">{collapsedCats.has(cat.key) ? '▸' : '▾'}</span>
          </button>

          {!collapsedCats.has(cat.key) && (
            <div className="ev-docgroup-list">
              {cat.docs.map(doc => (
                <div key={doc.id} className="ev-docgroup-row">
                  <div className="ev-docgroup-row-main">
                    <span className="ev-docgroup-type-badge">{formatDocTypeBadge(doc.doc_type)}</span>
                    <span className="ev-docgroup-doc-title">
                      {cleanTitle(doc.title, doc.ticker, company.name)}
                    </span>
                  </div>
                  <div className="ev-docgroup-row-meta">
                    {doc.date && (
                      <span className="ev-docgroup-date">{formatDateShort(doc.date)}</span>
                    )}
                    <button
                      className="ev-deck-analyze-btn"
                      onClick={() => openDeckAnalyzer(doc)}
                      title="Analyze slide by slide"
                    >
                      Analyze
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* ---- WEBCASTS SECTION ---- */}
      {(companyWebcasts.length > 0 || !loadingData) && (
        <div className="ev-docgroup">
          <div className="ev-docgroup-header" style={{ cursor: 'default' }}>
            <span className="ev-docgroup-icon">🎙</span>
            <span className="ev-docgroup-label">Webcasts & Transcripts</span>
            <span className="ev-docgroup-count">{companyWebcasts.length}</span>
          </div>

          {/* Webcast search */}
          {companyWebcasts.length > 0 && (
            <div className="ev-webcast-company-search">
              <div className="ev-forecast-input-row">
                <input
                  className="ev-forecast-input"
                  placeholder="Search transcripts..."
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
        </div>
      )}

      {loadingTranscript && <div className="ev-panel-loading">Loading transcript...</div>}
    </div>
  )
}
