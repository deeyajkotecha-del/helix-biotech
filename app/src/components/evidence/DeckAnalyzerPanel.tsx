import { useState, useEffect } from 'react'

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

// ============================================================
// Component
// ============================================================

interface Props {
  document: DeckDocument
  onBack: () => void
  allDocuments?: DeckDocument[]
}

export default function DeckAnalyzerPanel({ document, onBack, allDocuments }: Props) {
  const [slides, setSlides] = useState<SlideData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentSlide, setCurrentSlide] = useState(0)
  const [textOnly, setTextOnly] = useState(false)

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzedSlides, setAnalyzedSlides] = useState<Record<number, SlideData>>({})

  // Compare state
  const [compareDocId, setCompareDocId] = useState<number | null>(null)
  const [comparing, setComparing] = useState(false)
  const [comparison, setComparison] = useState<string>('')

  // Load slides
  useEffect(() => {
    async function loadSlides() {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(`/extract/api/deck/slides/${document.id}?images=true`)
        if (!res.ok) {
          const data = await res.json()
          setError(data.error || 'Failed to load slides')
          return
        }
        const data = await res.json()
        setSlides(data.slides || [])
        setTextOnly(!!data.text_only)
      } catch (e) {
        setError('Network error loading slides')
      } finally {
        setLoading(false)
      }
    }
    loadSlides()
  }, [document.id])

  // Analyze current slide
  async function analyzeSlide(slideNum: number) {
    if (analyzedSlides[slideNum]) return // Already analyzed
    setAnalyzing(true)
    try {
      const res = await fetch('/extract/api/deck/analyze-slide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_id: document.id,
          slide_number: slideNum,
          ticker: document.ticker,
          company_name: document.company_name,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setAnalyzedSlides(prev => ({ ...prev, [slideNum]: data }))
      }
    } catch (e) {
      console.error('Analyze slide failed:', e)
    } finally {
      setAnalyzing(false)
    }
  }

  // Compare slide to another document
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
          compare_doc_id: compareDocId,
          ticker: document.ticker,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setComparison(data.comparison || data.error || 'No comparison available')
      }
    } catch (e) {
      setComparison('Comparison failed')
    } finally {
      setComparing(false)
    }
  }

  const slide = slides[currentSlide]
  const analysis = analyzedSlides[currentSlide + 1] // slide_number is 1-indexed

  // Companion docs for comparison (same ticker, exclude current)
  const compareDocs = (allDocuments || []).filter(
    d => d.id !== document.id && d.ticker === document.ticker
  )

  // ============================================================
  // Render
  // ============================================================

  if (loading) {
    return (
      <div className="ev-deck-panel">
        <div className="ev-panel-header">
          <button className="ev-back-btn" onClick={onBack}>&larr; Back</button>
          <h3>Loading deck...</h3>
        </div>
        <div className="ev-panel-loading">Extracting slides...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="ev-deck-panel">
        <div className="ev-panel-header">
          <button className="ev-back-btn" onClick={onBack}>&larr; Back</button>
          <h3>Deck Analyzer</h3>
        </div>
        <div className="ev-deck-error">
          <p>{error}</p>
          <p className="ev-panel-tip">
            The PDF file may not be available on disk. Try re-downloading the document.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="ev-deck-panel">
      {/* Header */}
      <div className="ev-panel-header">
        <button className="ev-back-btn" onClick={onBack}>&larr; Back</button>
        <h3 className="ev-deck-title">{document.title}</h3>
      </div>

      <div className="ev-deck-meta">
        <span className="ev-company-ticker">{document.ticker}</span>
        <span className="ev-deck-slide-count">
          {slides.length} {textOnly ? 'sections' : 'slides'}
        </span>
        {textOnly && (
          <span className="ev-deck-text-only-badge">Text only</span>
        )}
      </div>

      {/* Slide navigation */}
      <div className="ev-deck-nav">
        <button
          className="ev-deck-nav-btn"
          disabled={currentSlide === 0}
          onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))}
        >
          &lsaquo; Prev
        </button>
        <span className="ev-deck-nav-label">
          {textOnly ? 'Section' : 'Slide'} {currentSlide + 1} of {slides.length}
        </span>
        <button
          className="ev-deck-nav-btn"
          disabled={currentSlide >= slides.length - 1}
          onClick={() => setCurrentSlide(prev => Math.min(slides.length - 1, prev + 1))}
        >
          Next &rsaquo;
        </button>
      </div>

      {/* Slide/section thumbnail strip */}
      <div className={`ev-deck-thumbstrip ${textOnly ? 'text-only' : ''}`}>
        {slides.map((s, i) => (
          <div
            key={i}
            className={`ev-deck-thumb ${i === currentSlide ? 'active' : ''} ${textOnly ? 'text-thumb' : ''}`}
            onClick={() => setCurrentSlide(i)}
            title={s.section_title || `${textOnly ? 'Section' : 'Slide'} ${i + 1}`}
          >
            {s.image_b64 ? (
              <img src={`data:image/jpeg;base64,${s.image_b64}`} alt={`Slide ${i + 1}`} />
            ) : (
              <span className="ev-deck-thumb-label">
                {s.section_title ? s.section_title.slice(0, 20) : `${i + 1}`}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Current slide */}
      {slide && (
        <div className="ev-deck-slide-view">
          {/* Slide image (when PDF is available) */}
          {slide.image_b64 && (
            <div className="ev-deck-slide-image">
              <img
                src={`data:image/jpeg;base64,${slide.image_b64}`}
                alt={`Slide ${currentSlide + 1}`}
              />
            </div>
          )}

          {/* Section header for text-only mode */}
          {textOnly && slide.section_title && (
            <div className="ev-deck-section-header">{slide.section_title}</div>
          )}

          {/* Slide/section text */}
          {slide.text && (
            textOnly ? (
              <div className="ev-deck-slide-text ev-deck-text-prominent">
                <p>{slide.text}</p>
              </div>
            ) : (
              <details className="ev-deck-slide-text-toggle">
                <summary>Extracted text ({slide.text.split(' ').length} words)</summary>
                <div className="ev-deck-slide-text">
                  <p>{slide.text}</p>
                </div>
              </details>
            )
          )}

          {/* Analyze button */}
          <div className="ev-deck-actions">
            <button
              className="ev-forecast-btn"
              onClick={() => analyzeSlide(currentSlide + 1)}
              disabled={analyzing || !!analysis}
            >
              {analyzing ? 'Analyzing...' : analysis ? 'Analyzed' : 'Analyze this slide'}
            </button>

            {/* Compare dropdown */}
            {compareDocs.length > 0 && (
              <div className="ev-deck-compare-section">
                <select
                  className="ev-param-select"
                  value={compareDocId || ''}
                  onChange={e => setCompareDocId(e.target.value ? parseInt(e.target.value) : null)}
                >
                  <option value="">Compare with...</option>
                  {compareDocs.map(d => (
                    <option key={d.id} value={d.id}>{d.title}</option>
                  ))}
                </select>
                {compareDocId && (
                  <button
                    className="ev-forecast-btn ev-btn-secondary"
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
            <div className="ev-deck-analysis">
              <h4 className="ev-deck-analysis-title">Investor Commentary</h4>
              <div className="ev-deck-commentary">
                {renderMarkdown(analysis.commentary || '')}
              </div>

              {/* RAG context */}
              {analysis.rag_context && analysis.rag_context.length > 0 && (
                <div className="ev-deck-rag-context">
                  <h5 className="ev-deck-rag-title">Related from library</h5>
                  {analysis.rag_context.map((ctx: RagContext, i: number) => (
                    <div key={i} className="ev-deck-rag-item">
                      <div className="ev-deck-rag-header">
                        <span className="ev-company-ticker">{ctx.ticker}</span>
                        <span className="ev-deck-rag-doc">{ctx.title}</span>
                        <span className="ev-webcast-score">
                          {(ctx.similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="ev-deck-rag-excerpt">{ctx.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Comparison results */}
          {comparison && (
            <div className="ev-deck-analysis">
              <h4 className="ev-deck-analysis-title">Cross-Document Comparison</h4>
              <div className="ev-deck-commentary">
                {renderMarkdown(comparison)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Simple markdown renderer for commentary
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
