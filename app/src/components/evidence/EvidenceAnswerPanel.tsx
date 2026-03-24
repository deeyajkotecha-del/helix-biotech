import { useMemo, ReactNode } from 'react'
import type { SearchSource, QueryPlan } from './types'

interface Props {
  answer: string
  sources: SearchSource[]
  queryPlan: QueryPlan | null
  onCitationHover: (index: number | null) => void
  followups?: string[]
  onFollowupClick?: (q: string) => void
  streaming?: boolean
}

// Source type -> badge style mapping
const SOURCE_STYLES: Record<string, { icon: string; color: string; bg: string; label: string }> = {
  pubmed:  { icon: '\u{1F4D6}', color: '#7B5EA7', bg: '#F3EFF8', label: '' },
  trial:   { icon: '\u{1F3E5}', color: '#3B6DAB', bg: '#EBF2FA', label: '' },
  fda:     { icon: '\u{1F3E5}', color: '#3D8B5E', bg: '#EDF7F0', label: 'FDA' },
  doc:     { icon: '\u{1F4C4}', color: '#C4603C', bg: '#FDF2ED', label: '' },
  entity:  { icon: '\u{1F9EC}', color: '#8B8680', bg: '#F0EBE4', label: 'DB' },
}

export default function EvidenceAnswerPanel({
  answer, sources, queryPlan, onCitationHover, followups, onFollowupClick, streaming,
}: Props) {
  const renderedBlocks = useMemo(() => {
    if (!answer) return []
    return parseAnswer(answer, sources, onCitationHover)
  }, [answer, sources, onCitationHover])

  const queryType = queryPlan?.query_type || 'general'
  const sourcesUsed = queryPlan?.sources || []

  return (
    <div className="ev-answer-panel">
      <div className="ev-answer-header">
        <span className={`ev-query-type-badge badge-${queryType}`}>
          {queryType.replace('_', ' ')}
        </span>
        <div className="ev-sources-used">
          {sourcesUsed.map(s => (
            <span key={s} className={`ev-source-pill pill-${s.toLowerCase()}`}>{s}</span>
          ))}
        </div>
      </div>
      <div className="ev-answer-content">
        {renderedBlocks}
      </div>
      {followups && followups.length > 0 && !streaming && (
        <div className="ev-followup-section">
          <h4 className="ev-followup-title">Explore further</h4>
          <div className="ev-followup-chips">
            {followups.map((q, i) => (
              <button key={i} className="ev-followup-chip" onClick={() => onFollowupClick?.(q)}>
                <span className="ev-followup-arrow">&rarr;</span>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function getBadgeUrl(sourceType: string, label: string, _sources: SearchSource[]): string | null {
  switch (sourceType) {
    case 'pubmed': {
      const pmidMatch = label.match(/^(\d{5,})/)
      if (pmidMatch) return `https://pubmed.ncbi.nlm.nih.gov/${pmidMatch[1]}/`
      return `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(label)}`
    }
    case 'trial':
      if (/^NCT\d+$/i.test(label)) return `https://clinicaltrials.gov/study/${label}`
      return `https://clinicaltrials.gov/search?term=${encodeURIComponent(label)}`
    case 'fda':
      return `https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=BasicSearch.process&owner=${encodeURIComponent(label)}`
    default:
      return null
  }
}

function parseAnswer(text: string, sources: SearchSource[], onCitationHover: (i: number | null) => void): ReactNode[] {
  const lines = text.split('\n')
  const elements: ReactNode[] = []
  let currentParagraph: string[] = []
  let listItems: string[] = []
  let inList = false

  function flushParagraph() {
    if (currentParagraph.length > 0) {
      const content = currentParagraph.join(' ')
      if (content.trim()) {
        elements.push(
          <p key={`p-${elements.length}`} className="ev-answer-paragraph">
            {renderInline(content, sources, onCitationHover)}
          </p>
        )
      }
      currentParagraph = []
    }
  }

  function flushList() {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="ev-answer-list">
          {listItems.map((item, i) => (
            <li key={i}>{renderInline(item, sources, onCitationHover)}</li>
          ))}
        </ul>
      )
      listItems = []
      inList = false
    }
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) { flushList(); flushParagraph(); continue }
    if (trimmed.startsWith('### ')) { flushList(); flushParagraph(); elements.push(<h4 key={`h4-${elements.length}`} className="ev-h4">{trimmed.replace(/^###\s*/, '')}</h4>); continue }
    if (trimmed.startsWith('## '))  { flushList(); flushParagraph(); elements.push(<h3 key={`h3-${elements.length}`} className="ev-h3">{trimmed.replace(/^##\s*/, '')}</h3>); continue }
    if (trimmed.startsWith('# '))   { flushList(); flushParagraph(); elements.push(<h2 key={`h2-${elements.length}`} className="ev-h2">{trimmed.replace(/^#\s*/, '')}</h2>); continue }
    if (/^\*\*[^*]+\*\*$/.test(trimmed)) { flushList(); flushParagraph(); elements.push(<h4 key={`bh-${elements.length}`} className="ev-h4">{trimmed.replace(/\*\*/g, '')}</h4>); continue }
    if (/^[-*]\s/.test(trimmed))    { flushParagraph(); inList = true; listItems.push(trimmed.replace(/^[-*]\s/, '')); continue }
    if (/^\d+\.\s/.test(trimmed))   { flushParagraph(); inList = true; listItems.push(trimmed.replace(/^\d+\.\s/, '')); continue }
    if (inList) flushList()
    currentParagraph.push(trimmed)
  }
  flushList(); flushParagraph()
  return elements
}

function renderInline(text: string, sources: SearchSource[], onCitationHover: (i: number | null) => void): ReactNode[] {
  const pattern = /(\{\{(\w+):([^}]+)\}\}|\[\d+\]|\[!\]|\*\*[^*]+\*\*|\*[^*]+\*)/g
  const parts: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(<span key={`t-${parts.length}`}>{text.slice(lastIndex, match.index)}</span>)
    const full = match[0]

    if (full.startsWith('{{') && full.endsWith('}}')) {
      const sourceType = match[2]
      const label = match[3]
      const style = SOURCE_STYLES[sourceType] || SOURCE_STYLES.entity
      const displayLabel = label.length > 20 ? label.slice(0, 18) + '...' : label
      const url = getBadgeUrl(sourceType, label, sources)
      const inner = <><span className="ev-badge-icon">{style.icon}</span> {style.label || displayLabel}</>
      parts.push(
        url ? (
          <a key={`b-${parts.length}`} href={url} target="_blank" rel="noopener noreferrer"
            className="ev-source-badge-inline ev-source-badge-link" style={{ color: style.color, background: style.bg }}>{inner}</a>
        ) : (
          <span key={`b-${parts.length}`} className="ev-source-badge-inline" style={{ color: style.color, background: style.bg }}>{inner}</span>
        )
      )
    } else if (/^\[\d+\]$/.test(full)) {
      const num = parseInt(full.match(/\d+/)![0])
      const source = sources?.[num - 1]
      parts.push(
        <span key={`c-${parts.length}`} className="ev-citation-chip"
          onMouseEnter={() => onCitationHover(num - 1)} onMouseLeave={() => onCitationHover(null)}
          title={source ? `${source.title} (${source.source_name})` : `Source ${num}`}>{num}</span>
      )
    } else if (full === '[!]') {
      parts.push(<span key={`cav-${parts.length}`} className="ev-caveat-flag">!</span>)
    } else if (full.startsWith('**') && full.endsWith('**')) {
      parts.push(<strong key={`b-${parts.length}`}>{full.slice(2, -2)}</strong>)
    } else if (full.startsWith('*') && full.endsWith('*')) {
      parts.push(<em key={`i-${parts.length}`}>{full.slice(1, -1)}</em>)
    }
    lastIndex = match.index + full.length
  }
  if (lastIndex < text.length) parts.push(<span key={`t-${parts.length}`}>{text.slice(lastIndex)}</span>)
  return parts
}
