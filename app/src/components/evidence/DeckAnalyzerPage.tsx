import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'

// ============================================================
// Types
// ============================================================

interface SlideData {
  slide_number: number
  text: string
  image_b64: string
  word_count?: number
  section_title?: string
  rag_context?: RagContext[]
  commentary?: string
  page_number?: number
  has_image?: boolean
}

interface RagContext {
  content: string
  title: string
  ticker: string
  doc_type: string
  page_number: number
  similarity: number
}

interface DeckDocument {
  id: number
  ticker: string
  company_name: string
  title: string
  doc_type: string
}

interface SlideReference {
  raw: string
  authors: string
  title: string
  journal: string
  year: number
  volume: string
  pages: string
  doi: string
  pmid: string
  pubmed_url: string
  doi_url: string
  data_on_file: boolean
}

// ============================================================
// Main Page Component — 60/40 split-view
// ============================================================

export default function DeckAnalyzerPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const docId = parseInt(searchParams.get('doc') || '0')
  const ticker = searchParams.get('ticker') || ''
  const companyName = searchParams.get('company') || ''
  const docTitle = searchParams.get('title') || 'Document'

  // Slide data
  const [slides, setSlides] = useState<SlideData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentSlide, setCurrentSlide] = useState(0)
  const [textOnly, setTextOnly] = useState(false)
  const [lazyImages, setLazyImages] = useState(false)

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzedSlides, setAnalyzedSlides] = useState<Record<number, SlideData>>({})
  const [analyzeError, setAnalyzeError] = useState('')

  // Compare state
  const [compareDocId, setCompareDocId] = useState<number | null>(null)
  const [comparing, setComparing] = useState(false)
  const [comparison, setComparison] = useState('')
  const [allDocuments, setAllDocuments] = useState<DeckDocument[]>([])

  // Reference bank state
  const [references, setReferences] = useState<Record<number, SlideReference[]>>({})
  const [extractingRefs, setExtractingRefs] = useState(false)
  const [refError, setRefError] = useState('')

  // Refs
  const slideViewRef = useRef<HTMLDivElement>(null)
  const thumbContainerRef = useRef<HTMLDivElement>(null)

  // ---- Load slides ----
  useEffect(() => {
    if (!docId) return
    async function loadSlides() {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(`/extract/api/deck/slides/${docId}?images=true`)
        if (!res.ok) {
          const data = await res.json()
          setError(data.error || 'Failed to load slides')
          return
        }
        const data = await res.json()
        setSlides(data.slides || [])
        setTextOnly(!!data.text_only)
        setLazyImages(!!data.lazy_images)
      } catch {
        setError('Network error loading slides')
      } finally {
        setLoading(false)
      }
    }
    loadSlides()
  }, [docId])

  // ---- Load companion docs for compare ----
  useEffect(() => {
    if (!ticker) return
    fetch(`/extract/api/documents?ticker=${ticker}&limit=50`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.documents) {
          setAllDocuments(data.documents.filter((d: any) => d.id !== docId).map((d: any) => ({
            id: d.id, ticker: d.ticker,
            company_name: d.company_name || companyName,
            title: d.title, doc_type: d.doc_type,
          })))
        }
      })
      .catch(() => {})
  }, [ticker, docId])

  // ---- Lazy-load image for current slide ----
  useEffect(() => {
    if (!lazyImages || !slides.length) return
    const slide = slides[currentSlide]
    if (!slide || slide.image_b64 || !slide.has_image) return

    fetch(`/extract/api/deck/slide-image/${docId}/${slide.page_number}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.image_b64) {
          setSlides(prev => prev.map((s, i) =>
            i === currentSlide ? { ...s, image_b64: data.image_b64 } : s
          ))
        }
      })
      .catch(() => {})
  }, [currentSlide, lazyImages, slides.length])

  // ---- Keyboard navigation ----
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault()
      setCurrentSlide(prev => Math.max(0, prev - 1))
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault()
      setCurrentSlide(prev => Math.min(slides.length - 1, prev + 1))
    }
  }, [slides.length])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // ---- Scroll active thumbnail into view ----
  useEffect(() => {
    if (!thumbContainerRef.current) return
    const activeThumb = thumbContainerRef.current.querySelector('.deck-split-thumb.active')
    if (activeThumb) {
      activeThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [currentSlide])

  // ---- Analyze slide ----
  async function analyzeSlide(slideNum: number) {
    if (analyzedSlides[slideNum]) return
    setAnalyzing(true)
    setAnalyzeError('')
    try {
      const res = await fetch('/extract/api/deck/analyze-slide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: docId, slide_number: slideNum,
          ticker, company_name: companyName,
        }),
      })
      const data = await res.json()
      if (res.ok) {
        setAnalyzedSlides(prev => ({ ...prev, [slideNum]: data }))
      } else {
        setAnalyzeError(data.error || `Analysis failed (${res.status})`)
      }
    } catch (e) {
      setAnalyzeError(`Network error: ${e}`)
    } finally {
      setAnalyzing(false)
    }
  }

  // ---- Compare slide ----
  async function compareSlide() {
    if (!compareDocId || !slides[currentSlide]) return
    setComparing(true)
    setComparison('')
    try {
      const res = await fetch('/extract/api/deck/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slide_text: slides[currentSlide].text,
          compare_doc_id: compareDocId, ticker,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setComparison(data.comparison || data.error || 'No comparison available')
      }
    } catch {
      setComparison('Comparison failed')
    } finally {
      setComparing(false)
    }
  }

  // ---- Extract references from slide ----
  async function extractReferences(slideNum: number) {
    if (references[slideNum]) return // Already extracted
    setExtractingRefs(true)
    setRefError('')
    try {
      const slide = slides[slideNum - 1]
      const res = await fetch('/extract/api/deck/extract-references', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: docId,
          slide_number: slideNum,
          slide_text: slide?.text || '',
          slide_image_b64: slide?.image_b64 || '',
        }),
      })
      const data = await res.json()
      if (res.ok && data.references) {
        setReferences(prev => ({ ...prev, [slideNum]: data.references }))
      } else {
        setRefError(data.error || data.message || 'No references found')
      }
    } catch (e) {
      setRefError(`Failed to extract references: ${e}`)
    } finally {
      setExtractingRefs(false)
    }
  }

  // ---- Auto-analyze on slide change (if not already analyzed) ----
  // Commented out for now — user clicks "Analyze" manually
  // useEffect(() => { if (slide) analyzeSlide(currentSlide + 1) }, [currentSlide])

  const slide = slides[currentSlide]
  const analysis = analyzedSlides[currentSlide + 1]
  const slideRefs = references[currentSlide + 1] || []

  // ============================================================
  // Render
  // ============================================================

  if (!docId) {
    return (
      <div className="deck-split-empty">
        <h3>Deck Analyzer</h3>
        <p>Select a document from the Companies page to analyze.</p>
        <button className="ev-forecast-btn" onClick={() => navigate('/companies')}>
          Go to Companies
        </button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="deck-split-loading">
        <div className="deck-split-loading-spinner" />
        <p>Extracting slides from <strong>{docTitle}</strong>...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="deck-split-empty">
        <h3>Error Loading Deck</h3>
        <p>{error}</p>
        <p style={{ fontSize: '13px', color: 'var(--ev-text-light)' }}>
          The PDF file may not be available on disk. Try re-downloading the document.
        </p>
        <button className="ev-forecast-btn" onClick={() => navigate(-1)}>
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="deck-split-container">
      {/* ---- LEFT PANEL: Slide Visual (50%) ---- */}
      <div className="deck-split-left">
        {/* Header bar */}
        <div className="deck-split-left-header">
          <button className="ev-back-btn" onClick={() => navigate(-1)}>&larr; Back</button>
          <div className="deck-split-doc-info">
            <span className="ev-company-ticker">{ticker}</span>
            <span className="deck-split-slide-count">
              {slides.length} {textOnly ? 'sections' : 'slides'}
            </span>
          </div>
        </div>

        {/* Navigation bar */}
        <div className="deck-split-nav">
          <button
            className="ev-deck-nav-btn"
            disabled={currentSlide === 0}
            onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))}
          >
            ‹ Prev
          </button>
          <span className="ev-deck-nav-label">
            {textOnly ? 'Section' : 'Slide'} {currentSlide + 1} of {slides.length}
          </span>
          <button
            className="ev-deck-nav-btn"
            disabled={currentSlide >= slides.length - 1}
            onClick={() => setCurrentSlide(prev => Math.min(slides.length - 1, prev + 1))}
          >
            Next ›
          </button>
        </div>

        {/* Current slide image — sticky visible area */}
        {slide && (
          <div className="deck-split-slide-area">
            {slide.image_b64 ? (
              <div className="deck-split-slide-image">
                <img
                  src={`data:image/jpeg;base64,${slide.image_b64}`}
                  alt={`Slide ${currentSlide + 1}`}
                />
              </div>
            ) : textOnly && slide.section_title ? (
              <div className="deck-split-text-prominent">
                <div className="ev-deck-section-header">{slide.section_title}</div>
                <p>{slide.text}</p>
              </div>
            ) : slide.text ? (
              <div className="deck-split-text-prominent">
                <p>{slide.text}</p>
              </div>
            ) : null}

            {/* Extracted text (collapsible, under slide) */}
            {slide.text && !textOnly && (
              <details className="deck-split-text-toggle">
                <summary>Extracted text ({slide.text.split(' ').length} words)</summary>
                <div className="deck-split-text-content">
                  <p>{slide.text}</p>
                </div>
              </details>
            )}
          </div>
        )}

        {/* Thumbnail strip — horizontal scroll at bottom */}
        <div className="deck-split-thumbstrip" ref={thumbContainerRef}>
          {slides.map((s, i) => {
            const isAnalyzed = !!analyzedSlides[i + 1]
            return (
              <div
                key={i}
                className={`deck-split-thumb-mini ${i === currentSlide ? 'active' : ''} ${isAnalyzed ? 'analyzed' : ''}`}
                onClick={() => setCurrentSlide(i)}
                title={s.section_title || `Slide ${i + 1}`}
              >
                {s.image_b64 ? (
                  <img src={`data:image/jpeg;base64,${s.image_b64}`} alt={`${i + 1}`} />
                ) : (
                  <span>{i + 1}</span>
                )}
                {isAnalyzed && <div className="deck-split-thumb-check">✓</div>}
              </div>
            )
          })}
        </div>

        <div className="deck-split-keyboard-hint">
          <kbd>←</kbd> <kbd>→</kbd> to navigate slides
        </div>
      </div>

      {/* ---- RIGHT PANEL: Analysis & References (50%) ---- */}
      <div className="deck-split-right" ref={slideViewRef}>
        {/* Document title */}
        <h3 className="deck-split-doc-title">{docTitle}</h3>

        {slide && (
          <>
            {/* Action bar */}
            <div className="deck-split-actions">
              <button
                className="deck-split-analyze-btn"
                onClick={() => analyzeSlide(currentSlide + 1)}
                disabled={analyzing}
              >
                {analyzing ? (
                  <><span className="deck-split-spinner" /> Analyzing...</>
                ) : analysis ? (
                  '↻ Re-analyze'
                ) : (
                  'Analyze this slide'
                )}
              </button>

              <button
                className="deck-split-refbank-btn"
                onClick={() => extractReferences(currentSlide + 1)}
                disabled={extractingRefs}
              >
                {extractingRefs ? (
                  <><span className="deck-split-spinner" /> Refs...</>
                ) : slideRefs.length > 0 ? (
                  `Refs (${slideRefs.length})`
                ) : (
                  'Extract Refs'
                )}
              </button>

              {analyzeError && (
                <p className="deck-split-error">{analyzeError}</p>
              )}

              {/* Compare */}
              {allDocuments.length > 0 && (
                <div className="deck-split-compare">
                  <select
                    className="deck-split-compare-select"
                    value={compareDocId || ''}
                    onChange={e => setCompareDocId(e.target.value ? parseInt(e.target.value) : null)}
                  >
                    <option value="">Compare with...</option>
                    {allDocuments.map(d => (
                      <option key={d.id} value={d.id}>{d.title}</option>
                    ))}
                  </select>
                  {compareDocId && (
                    <button
                      className="deck-split-compare-btn"
                      onClick={compareSlide}
                      disabled={comparing}
                    >
                      {comparing ? '...' : 'Compare'}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Analysis results */}
            {analysis && (
              <div className="deck-split-analysis">
                <div className="deck-split-analysis-header">
                  <span className="deck-split-analysis-badge">MD/PhD</span>
                  <h4>Clinical & Investment Analysis</h4>
                </div>
                <div className="deck-split-commentary">
                  {renderMarkdown(analysis.commentary || '')}
                </div>

                {/* RAG context */}
                {analysis.rag_context && analysis.rag_context.length > 0 && (
                  <details className="deck-split-rag">
                    <summary className="deck-split-rag-title">
                      Cross-Referenced Sources ({analysis.rag_context.length})
                    </summary>
                    <div className="deck-split-rag-list">
                      {analysis.rag_context.map((ctx, i) => (
                        <div key={i} className="deck-split-rag-item">
                          <div className="deck-split-rag-header">
                            <span className="ev-company-ticker">{ctx.ticker}</span>
                            <span className="deck-split-rag-type">{ctx.doc_type}</span>
                            <span className="deck-split-rag-doc">{ctx.title}</span>
                            <span className="deck-split-rag-score">
                              {(ctx.similarity * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="deck-split-rag-excerpt">{ctx.content}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )}

            {/* Reference Bank */}
            {slideRefs.length > 0 && (
              <div className="deck-split-refbank">
                <div className="deck-split-refbank-header">
                  <h4>Reference Bank</h4>
                  <span className="deck-split-refbank-count">{slideRefs.length} references</span>
                </div>
                <div className="deck-split-refbank-list">
                  {slideRefs.map((ref, i) => (
                    <div key={i} className={`deck-split-ref-item ${ref.data_on_file ? 'data-on-file' : ''}`}>
                      <div className="deck-split-ref-num">{i + 1}</div>
                      <div className="deck-split-ref-body">
                        <div className="deck-split-ref-citation">
                          <span className="deck-split-ref-authors">{ref.authors}</span>
                          {ref.journal && (
                            <span className="deck-split-ref-journal">{ref.journal}</span>
                          )}
                          {ref.year > 0 && (
                            <span className="deck-split-ref-year">{ref.year}</span>
                          )}
                          {ref.volume && (
                            <span className="deck-split-ref-detail">{ref.volume}{ref.pages ? `:${ref.pages}` : ''}</span>
                          )}
                        </div>
                        {ref.title && (
                          <div className="deck-split-ref-title">{ref.title}</div>
                        )}
                        <div className="deck-split-ref-links">
                          {ref.pubmed_url && (
                            <a href={ref.pubmed_url} target="_blank" rel="noopener noreferrer" className="deck-split-ref-link pubmed">
                              PubMed
                            </a>
                          )}
                          {ref.doi_url && (
                            <a href={ref.doi_url} target="_blank" rel="noopener noreferrer" className="deck-split-ref-link doi">
                              DOI
                            </a>
                          )}
                          {ref.data_on_file && (
                            <span className="deck-split-ref-tag dof">Data on file</span>
                          )}
                          {!ref.pubmed_url && !ref.doi_url && !ref.data_on_file && (
                            <span className="deck-split-ref-tag unresolved">No link found</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {refError && !slideRefs.length && (
              <p className="deck-split-refbank-empty">{refError}</p>
            )}

            {/* Comparison results */}
            {comparison && (
              <div className="deck-split-analysis">
                <div className="deck-split-analysis-header">
                  <h4>Cross-Document Comparison</h4>
                </div>
                <div className="deck-split-commentary">
                  {renderMarkdown(comparison)}
                </div>
              </div>
            )}

            {/* Empty state — no analysis yet */}
            {!analysis && !analyzing && !comparison && !slideRefs.length && (
              <div className="deck-split-empty-right">
                <p>Click <strong>Analyze this slide</strong> to get an MD/PhD-level clinical and investment assessment, or <strong>Extract Refs</strong> to pull citations with PubMed links.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ============================================================
// Simple markdown renderer
// ============================================================

function renderMarkdown(text: string) {
  if (!text) return null
  const lines = text.split('\n')
  const elements: JSX.Element[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue

    if (line.startsWith('### ')) {
      elements.push(<h5 key={i} className="ev-deck-md-h3">{line.slice(4)}</h5>)
    } else if (line.startsWith('## ')) {
      elements.push(<h4 key={i} className="ev-deck-md-h2">{line.slice(3)}</h4>)
    } else if (line.startsWith('- **') || line.startsWith('* **')) {
      const content = line.slice(2)
      elements.push(
        <div key={i} className="ev-deck-md-bullet">
          <span className="ev-deck-md-bullet-dot" />
          <span dangerouslySetInnerHTML={{
            __html: content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
          }} />
        </div>
      )
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <div key={i} className="ev-deck-md-bullet">
          <span className="ev-deck-md-bullet-dot" />
          <span>{line.slice(2)}</span>
        </div>
      )
    } else {
      elements.push(
        <p key={i} className="ev-deck-md-p" dangerouslySetInnerHTML={{
          __html: line.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        }} />
      )
    }
  }

  return <>{elements}</>
}
