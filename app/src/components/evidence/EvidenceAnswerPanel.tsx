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

// Source type -> badge style mapping (OpenEvidence-style: no emojis, clean text pills)
const SOURCE_STYLES: Record<string, { color: string; bg: string }> = {
  pubmed:  { color: '#7B5EA7', bg: '#F3EFF8' },
  trial:   { color: '#3B6DAB', bg: '#EBF2FA' },
  fda:     { color: '#3D8B5E', bg: '#EDF7F0' },
  doc:     { color: '#9E6B54', bg: '#F8F0EB' },
  sec:     { color: '#8B6914', bg: '#FFF8E7' },
  entity:  { color: '#8B8680', bg: '#F0EBE4' },
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
    case 'fda_crl':
      return `https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=BasicSearch.process&owner=${encodeURIComponent(label)}`
    default:
      return null
  }
}

/** Find the sidebar source index that matches a doc/sec badge label */
function findSourceIndex(_sourceType: string, label: string, sources: SearchSource[]): number {
  if (!sources?.length) return -1
  // label format: "TICKER|DocTitle" or just "DocTitle"
  const parts = label.split('|')
  const ticker = parts.length > 1 ? parts[0].trim().toUpperCase() : ''
  const title = (parts.length > 1 ? parts.slice(1).join('|') : label).trim().toLowerCase()

  for (let i = 0; i < sources.length; i++) {
    const s = sources[i]
    // Match by ticker + title substring
    if (ticker && s.ticker?.toUpperCase() === ticker) {
      if (!title || s.title?.toLowerCase().includes(title)) return i
    }
    // Match by title alone
    if (title && s.title?.toLowerCase().includes(title)) return i
  }
  return -1
}

function scrollToSource(index: number) {
  const cards = document.querySelectorAll('.ev-source-card')
  if (cards[index]) {
    cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
    cards[index].classList.add('ev-source-highlighted')
    setTimeout(() => cards[index].classList.remove('ev-source-highlighted'), 2000)
  }
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim()
  return trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')
}

function isTableSeparator(line: string): boolean {
  return /^\|[\s:?-]+(\|[\s:?-]+)+\|$/.test(line.trim())
}

function parseTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim())
}

function renderTable(
  tableLines: string[],
  sources: SearchSource[],
  onCitationHover: (i: number | null) => void,
  keyPrefix: string
): ReactNode {
  const headers: string[] = []
  const rows: string[][] = []

  for (let i = 0; i < tableLines.length; i++) {
    if (isTableSeparator(tableLines[i])) continue
    const cells = parseTableRow(tableLines[i])
    if (headers.length === 0) headers.push(...cells)
    else rows.push(cells)
  }

  if (headers.length === 0) return null

  return (
    <div key={keyPrefix} className="answer-table-wrapper">
      <table className="answer-table">
        <thead>
          <tr>{headers.map((h, i) => <th key={i}>{renderInline(h, sources, onCitationHover)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>{row.map((cell, ci) => <td key={ci}>{renderInline(cell, sources, onCitationHover)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function parseAnswer(text: string, sources: SearchSource[], onCitationHover: (i: number | null) => void): ReactNode[] {
  const lines = text.split('\n')
  const elements: ReactNode[] = []
  let currentParagraph: string[] = []
  let listItems: string[] = []
  let inList = false
  let inTable = false
  let tableLines: string[] = []
  let justFlushedTable = false

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

  function flushTable() {
    if (tableLines.length >= 2) {
      const table = renderTable(tableLines, sources, onCitationHover, `tbl-${elements.length}`)
      if (table) elements.push(table)
    }
    tableLines = []
    inTable = false
  }

  for (const line of lines) {
    const trimmed = line.trim()

    if (isTableRow(trimmed)) {
      if (!inTable) { flushList(); flushParagraph(); inTable = true }
      tableLines.push(trimmed)
      continue
    } else if (inTable) {
      flushTable()
      justFlushedTable = true
    }

    if (!trimmed) { flushList(); flushParagraph(); justFlushedTable = false; continue }

    // Skip lines that are ONLY citation badges right after a table (redundant citations)
    if (justFlushedTable && /^(\{?\{\w+:[^}]+\}?\}\s*)+$/.test(trimmed)) {
      justFlushedTable = false
      continue
    }
    justFlushedTable = false
    if (trimmed.startsWith('### ')) { flushList(); flushParagraph(); elements.push(<h4 key={`h4-${elements.length}`} className="ev-h4">{trimmed.replace(/^###\s*/, '')}</h4>); continue }
    if (trimmed.startsWith('## '))  { flushList(); flushParagraph(); elements.push(<h3 key={`h3-${elements.length}`} className="ev-h3">{trimmed.replace(/^##\s*/, '')}</h3>); continue }
    if (trimmed.startsWith('# '))   { flushList(); flushParagraph(); elements.push(<h2 key={`h2-${elements.length}`} className="ev-h2">{trimmed.replace(/^#\s*/, '')}</h2>); continue }
    if (/^\*\*[^*]+\*\*$/.test(trimmed)) { flushList(); flushParagraph(); elements.push(<h4 key={`bh-${elements.length}`} className="ev-h4">{trimmed.replace(/\*\*/g, '')}</h4>); continue }
    if (/^[-*]\s/.test(trimmed))    { flushParagraph(); inList = true; listItems.push(trimmed.replace(/^[-*]\s/, '')); continue }
    if (/^\d+\.\s/.test(trimmed))   { flushParagraph(); inList = true; listItems.push(trimmed.replace(/^\d+\.\s/, '')); continue }
    if (inList) flushList()
    currentParagraph.push(trimmed)
  }
  flushTable(); flushList(); flushParagraph()
  return elements
}

function renderInline(text: string, sources: SearchSource[], onCitationHover: (i: number | null) => void): ReactNode[] {
  // Matches both {type:label} and {{type:label}}, NCT IDs, markdown links
  const pattern = /(\{\{?(\w+):([^}]+)\}?\}|\[\d+\]|\[!\]|\*\*[^*]+\*\*|\*[^*]+\*|NCT\d{8,}|\[([^\]]+)\]\((https?:\/\/[^)]+)\))/g
  const parts: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(<span key={`t-${parts.length}`}>{text.slice(lastIndex, match.index)}</span>)
    const full = match[0]

    if (match[2] && match[3] && (full.startsWith('{{') || full.startsWith('{'))) {
      const sourceType = match[2]
      const label = match[3]
      // Suppress unhelpful generic badges like {entity:db}
      if (sourceType === 'entity' && label.toLowerCase() === 'db') {
        lastIndex = match.index + full.length
        continue
      }
      const style = SOURCE_STYLES[sourceType] || SOURCE_STYLES.entity
      // Build clean display label (OpenEvidence style)
      let displayLabel = label
      if (sourceType === 'pubmed' && label.includes('|')) {
        displayLabel = label.split('|')[1]?.trim() || label
      } else if ((sourceType === 'doc' || sourceType === 'sec') && label.includes('|')) {
        displayLabel = label.split('|').slice(1).join('|')
      }
      if (displayLabel.length > 24) displayLabel = displayLabel.slice(0, 22) + '...'
      const url = getBadgeUrl(sourceType, label, sources)
      if (url) {
        parts.push(
          <a key={`b-${parts.length}`} href={url} target="_blank" rel="noopener noreferrer"
            className="ev-source-badge-inline ev-source-badge-link" style={{ color: style.color, background: style.bg }}
            title={`${sourceType}: ${label}`}>{displayLabel}</a>
        )
      } else if (sourceType === 'doc' || sourceType === 'sec') {
        // Internal docs — make clickable to scroll to the matching source card
        const srcIdx = findSourceIndex(sourceType, label, sources)
        parts.push(
          <span key={`b-${parts.length}`}
            className="ev-source-badge-inline ev-source-badge-link"
            style={{ color: style.color, background: style.bg, cursor: 'pointer' }}
            title={`${sourceType}: ${label} — click to see source`}
            onClick={() => {
              if (srcIdx >= 0) { scrollToSource(srcIdx); onCitationHover(srcIdx) }
            }}
            onMouseEnter={() => srcIdx >= 0 && onCitationHover(srcIdx)}
            onMouseLeave={() => onCitationHover(null)}
          >{displayLabel}</span>
        )
      } else {
        parts.push(
          <span key={`b-${parts.length}`} className="ev-source-badge-inline" style={{ color: style.color, background: style.bg }}
            title={`${sourceType}: ${label}`}>{displayLabel}</span>
        )
      }
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
    } else if (/^NCT\d{8,}$/.test(full)) {
      parts.push(
        <a key={`nct-${parts.length}`} href={`https://clinicaltrials.gov/study/${full}`}
          target="_blank" rel="noopener noreferrer" className="nct-link"
          title={`View ${full} on ClinicalTrials.gov`}>{full}</a>
      )
    } else if (match[4] && match[5]) {
      parts.push(
        <a key={`ml-${parts.length}`} href={match[5]} target="_blank" rel="noopener noreferrer"
          className="answer-link">{match[4]}</a>
      )
    }
    lastIndex = match.index + full.length
  }
  if (lastIndex < text.length) parts.push(<span key={`t-${parts.length}`}>{text.slice(lastIndex)}</span>)
  return parts
}
