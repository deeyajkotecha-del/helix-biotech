import type { SearchSource } from './types'

interface SourceSidebarProps {
  sources: SearchSource[]
  highlightedSource: number | null
}

export default function SourceSidebar({ sources, highlightedSource }: SourceSidebarProps) {
  if (!sources || sources.length === 0) return null

  // Group sources by type
  const grouped: Record<string, (SearchSource & { index: number })[]> = {}
  sources.forEach((s, i) => {
    const type = s.type || 'other'
    if (!grouped[type]) grouped[type] = []
    grouped[type].push({ ...s, index: i })
  })

  const typeLabels: Record<string, string> = {
    internal: 'Document Library',
    clinical_trial: 'Clinical Trials',
    fda: 'FDA',
    pubmed: 'Literature',
  }

  const typeIcons: Record<string, string> = {
    internal: '\u{1F4C4}',
    clinical_trial: '\u{1F3E5}',
    fda: '\u{2705}',
    pubmed: '\u{1F4DA}',
  }

  return (
    <div className="sidebar-content">
      <h3 className="sidebar-title">
        Sources
        <span className="source-count">{sources.length}</span>
      </h3>
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type} className="source-group">
          <h4 className="source-group-title">
            <span className="source-group-icon">{typeIcons[type] || '\u{1F4CE}'}</span>
            {typeLabels[type] || type}
            <span className="source-group-count">{items.length}</span>
          </h4>
          {items.map((source) => (
            <SourceCard
              key={source.index}
              source={source}
              number={source.index + 1}
              highlighted={highlightedSource === source.index}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

interface SourceCardProps {
  source: SearchSource
  number: number
  highlighted: boolean
}

function SourceCard({ source, number, highlighted }: SourceCardProps) {
  const hasUrl = source.url?.startsWith('http')

  return (
    <div className={`source-card ${highlighted ? 'source-highlighted' : ''}`}>
      <div className="source-card-header">
        <span className="source-number">{number}</span>
        <span className="source-type-label">{source.source_name}</span>
      </div>
      <div className="source-card-body">
        <p className="source-title">
          {hasUrl ? (
            <a href={source.url} target="_blank" rel="noopener noreferrer">
              {source.title || 'Untitled'}
            </a>
          ) : (
            source.title || 'Untitled'
          )}
        </p>
        {source.company && (
          <p className="source-company">
            {source.ticker && <span className="ticker-badge">{source.ticker}</span>}
            {source.company}
          </p>
        )}
        {source.doc_type && (
          <p className="source-meta">{source.doc_type}</p>
        )}
        {source.ref && (
          <p className="source-ref">{source.ref}</p>
        )}
      </div>
    </div>
  )
}
