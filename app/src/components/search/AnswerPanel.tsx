import { useMemo, ReactNode } from 'react'
import type { SearchSource, QueryPlan } from './types'

interface AnswerPanelProps {
  answer: string
  sources: SearchSource[]
  queryPlan: QueryPlan | null
  onCitationHover: (index: number | null) => void
  followups?: string[]
  onFollowupClick?: (q: string) => void
  streaming?: boolean
}

export default function AnswerPanel({
  answer,
  sources,
  queryPlan,
  onCitationHover,
  followups,
  onFollowupClick,
  streaming,
}: AnswerPanelProps) {
  const renderedBlocks = useMemo(() => {
    if (!answer) return []
    return parseAnswer(answer, sources, onCitationHover)
  }, [answer, sources, onCitationHover])

  const queryType = queryPlan?.query_type || 'general'
  const sourcesUsed = queryPlan?.sources || []

  return (
    <div className="answer-panel">
      <div className="answer-header">
        <span className={`query-type-badge badge-${queryType}`}>
          {queryType.replace('_', ' ')}
        </span>
        <div className="sources-used">
          {sourcesUsed.map(s => (
            <span key={s} className={`source-pill pill-${s.toLowerCase()}`}>{s}</span>
          ))}
        </div>
      </div>
      <div className="answer-content">
        {renderedBlocks}
      </div>
      {followups && followups.length > 0 && !streaming && (
        <div className="followup-section">
          <h4 className="followup-title">Explore further</h4>
          <div className="followup-chips">
            {followups.map((q, i) => (
              <button
                key={i}
                className="followup-chip"
                onClick={() => onFollowupClick?.(q)}
              >
                <span className="followup-arrow">&rarr;</span>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Source type -> badge style mapping
const SOURCE_STYLES: Record<string, { icon: string; color: string; bg: string; label: string }> = {
  pubmed:  { icon: '\u{1F4D6}', color: '#7B5EA7', bg: '#F3EFF8', label: '' },
  trial:   { icon: '\u{1F3E5}', color: '#3B6DAB', bg: '#EBF2FA', label: '' },
  fda:     { icon: '\u{1F3E5}', color: '#3D8B5E', bg: '#EDF7F0', label: 'FDA' },
  doc:     { icon: '\u{1F4C4}', color: '#C4603C', bg: '#FDF2ED', label: '' },
  entity:  { icon: '\u{1F9EC}', color: '#8B8680', bg: '#F0EBE4', label: '' },
}

function parsePubmedLabel(label: string) {
  if (label.includes('|')) {
    const [pmid, displayName] = label.split('|', 2)
    return { pmid: pmid.trim(), displayName: displayName.trim() }
  }
  if (/^\d{5,}$/.test(label)) {
    return { pmid: label, displayName: label }
  }
  return { pmid: null, displayName: label }
}

function getBadgeUrl(sourceType: string, label: string, sources: SearchSource[]): string | null {
  switch (sourceType) {
    case 'pubmed': {
      const { pmid } = parsePubmedLabel(label)
      if (pmid) return `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`
      if (sources && sources.length > 0) {
        const match = sources.find(s =>
          s.type === 'pubmed' && (
            (s.company || '').toLowerCase().includes(label.toLowerCase()) ||
            (s.ref || '').includes(label) ||
            (s.title || '').toLowerCase().includes(label.toLowerCase())
          )
        )
        if (match?.url) return match.url
        if (match?.ref) {
          const refPmid = match.ref.replace(/^PMID\s*/i, '')
          if (/^\d+$/.test(refPmid)) return `https://pubmed.ncbi.nlm.nih.gov/${refPmid}/`
        }
      }
      return `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(label)}`
    }
    case 'trial':
      if (/^NCT\d+$/i.test(label)) return `https://clinicaltrials.gov/study/${label}`
      return `https://clinicaltrials.gov/search?term=${encodeURIComponent(label)}`
    case 'fda':
      return `https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=BasicSearch.process&owner=${encodeURIComponent(label)}`
    case 'doc':
    case 'entity':
    default:
      return null
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
  onCitationHover: (index: number | null) => void,
  keyPrefix: string
): ReactNode {
  const headers: string[] = []
  const rows: string[][] = []

  for (let i = 0; i < tableLines.length; i++) {
    const line = tableLines[i]
    if (isTableSeparator(line)) continue // Skip separator row (|---|---|)
    const cells = parseTableRow(line)
    if (headers.length === 0) {
      headers.push(...cells)
    } else {
      rows.push(cells)
    }
  }

  if (headers.length === 0) return null

  return (
    <div key={keyPrefix} className="answer-table-wrapper">
      <table className="answer-table">
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i}>{renderInlineContent(h, sources, onCitationHover)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci}>{renderInlineContent(cell, sources, onCitationHover)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function parseAnswer(
  text: string,
  sources: SearchSource[],
  onCitationHover: (index: number | null) => void
): ReactNode[] {
  const lines = text.split('\n')
  const elements: ReactNode[] = []
  let currentParagraph: string[] = []
  let inList = false
  let listItems: string[] = []
  let inTable = false
  let tableLines: string[] = []
  let justFlushedTable = false

  function flushParagraph() {
    if (currentParagraph.length > 0) {
      const content = currentParagraph.join(' ')
      if (content.trim()) {
        elements.push(
          <p key={`p-${elements.length}`} className="answer-paragraph">
            {renderInlineContent(content, sources, onCitationHover)}
          </p>
        )
      }
      currentParagraph = []
    }
  }

  function flushList() {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="answer-list">
          {listItems.map((item, i) => (
            <li key={i} className="answer-list-item">
              {renderInlineContent(item, sources, onCitationHover)}
            </li>
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

    // Table detection: lines starting and ending with |
    if (isTableRow(trimmed)) {
      if (!inTable) {
        flushList()
        flushParagraph()
        inTable = true
      }
      tableLines.push(trimmed)
      continue
    } else if (inTable) {
      flushTable()
      justFlushedTable = true
    }

    if (!trimmed) {
      flushList()
      flushParagraph()
      justFlushedTable = false
      continue
    }

    // Skip lines that are ONLY citation badges right after a table (redundant citations)
    if (justFlushedTable && /^(\{\{\w+:[^}]+\}\}\s*)+$/.test(trimmed)) {
      justFlushedTable = false
      continue
    }
    justFlushedTable = false

    if (trimmed.startsWith('### ')) {
      flushList(); flushParagraph()
      elements.push(<h4 key={`h4-${elements.length}`} className="answer-h4">{trimmed.replace(/^###\s*/, '')}</h4>)
      continue
    }
    if (trimmed.startsWith('## ')) {
      flushList(); flushParagraph()
      elements.push(<h3 key={`h3-${elements.length}`} className="answer-h3">{trimmed.replace(/^##\s*/, '')}</h3>)
      continue
    }
    if (trimmed.startsWith('# ')) {
      flushList(); flushParagraph()
      elements.push(<h2 key={`h2-${elements.length}`} className="answer-h2">{trimmed.replace(/^#\s*/, '')}</h2>)
      continue
    }

    if (/^\*\*[^*]+\*\*$/.test(trimmed)) {
      flushList(); flushParagraph()
      elements.push(<h4 key={`bh-${elements.length}`} className="answer-h4">{trimmed.replace(/\*\*/g, '')}</h4>)
      continue
    }

    if (/^[-*]\s/.test(trimmed)) {
      flushParagraph()
      inList = true
      listItems.push(trimmed.replace(/^[-*]\s/, ''))
      continue
    }

    if (/^\d+\.\s/.test(trimmed)) {
      flushParagraph()
      inList = true
      listItems.push(trimmed.replace(/^\d+\.\s/, ''))
      continue
    }

    if (inList) flushList()
    currentParagraph.push(trimmed)
  }

  flushTable()
  flushList()
  flushParagraph()
  return elements
}

type InlinePart =
  | { type: 'text'; value: string }
  | { type: 'source_badge'; sourceType: string; label: string }
  | { type: 'numbered_cite'; num: number }
  | { type: 'caveat' }
  | { type: 'bold'; value: string }
  | { type: 'italic'; value: string }
  | { type: 'nct_link'; nctId: string }
  | { type: 'md_link'; text: string; url: string }

function renderInlineContent(
  text: string,
  sources: SearchSource[],
  onCitationHover: (index: number | null) => void
): ReactNode[] {
  // Extended pattern: also matches NCT IDs and markdown links [text](url)
  const pattern = /(\{\{(\w+):([^}]+)\}\}|\[\d+\]|\[!\]|\*\*[^*]+\*\*|\*[^*]+\*|NCT\d{8,}|\[([^\]]+)\]\((https?:\/\/[^)]+)\))/g
  const parts: InlinePart[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }

    const full = match[0]

    if (full.startsWith('{{') && full.endsWith('}}')) {
      // Suppress unhelpful generic badges like {entity:db}
      const badgeType = match[2]
      const badgeLabel = match[3]
      if (badgeType === 'entity' && badgeLabel.toLowerCase() === 'db') {
        // Skip — "entity:db" renders as a meaningless badge
      } else {
        parts.push({ type: 'source_badge', sourceType: badgeType, label: badgeLabel })
      }
    } else if (/^\[\d+\]$/.test(full)) {
      const num = parseInt(full.match(/\d+/)![0])
      parts.push({ type: 'numbered_cite', num })
    } else if (full === '[!]') {
      parts.push({ type: 'caveat' })
    } else if (full.startsWith('**') && full.endsWith('**')) {
      parts.push({ type: 'bold', value: full.slice(2, -2) })
    } else if (full.startsWith('*') && full.endsWith('*')) {
      parts.push({ type: 'italic', value: full.slice(1, -1) })
    } else if (/^NCT\d{8,}$/.test(full)) {
      parts.push({ type: 'nct_link', nctId: full })
    } else if (match[4] && match[5]) {
      // Markdown link: [text](url)
      parts.push({ type: 'md_link', text: match[4], url: match[5] })
    }

    lastIndex = match.index + full.length
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }

  return parts.map((part, i) => {
    switch (part.type) {
      case 'source_badge': {
        const style = SOURCE_STYLES[part.sourceType] || SOURCE_STYLES.entity
        let rawLabel = part.label
        if (part.sourceType === 'pubmed') {
          const { displayName } = parsePubmedLabel(part.label)
          rawLabel = displayName
        }
        const displayLabel = rawLabel.length > 20 ? rawLabel.slice(0, 18) + '...' : rawLabel
        const url = getBadgeUrl(part.sourceType, part.label, sources)
        const inner = (
          <>
            <span className="badge-icon">{style.icon}</span>
            {' '}{style.label || displayLabel}
          </>
        )
        return url ? (
          <a
            key={i}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="source-badge-inline source-badge-link"
            style={{ color: style.color, background: style.bg }}
            title={`${part.sourceType}: ${part.label} — click to view source`}
          >
            {inner}
          </a>
        ) : (
          <span
            key={i}
            className="source-badge-inline"
            style={{ color: style.color, background: style.bg }}
            title={`${part.sourceType}: ${part.label}`}
          >
            {inner}
          </span>
        )
      }
      case 'numbered_cite': {
        const source = sources?.[part.num - 1]
        return (
          <span
            key={i}
            className="citation-chip"
            onMouseEnter={() => onCitationHover(part.num - 1)}
            onMouseLeave={() => onCitationHover(null)}
            title={source ? `${source.title} (${source.source_name})` : `Source ${part.num}`}
          >
            {part.num}
          </span>
        )
      }
      case 'caveat':
        return <span key={i} className="caveat-flag" title="Data limitation or caveat">!</span>
      case 'bold':
        return <strong key={i}>{part.value}</strong>
      case 'italic':
        return <em key={i}>{part.value}</em>
      case 'nct_link':
        return (
          <a
            key={i}
            href={`https://clinicaltrials.gov/study/${part.nctId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="nct-link"
            title={`View ${part.nctId} on ClinicalTrials.gov`}
          >
            {part.nctId}
          </a>
        )
      case 'md_link':
        return (
          <a
            key={i}
            href={part.url}
            target="_blank"
            rel="noopener noreferrer"
            className="answer-link"
          >
            {part.text}
          </a>
        )
      default:
        return <span key={i}>{part.value}</span>
    }
  })
}
