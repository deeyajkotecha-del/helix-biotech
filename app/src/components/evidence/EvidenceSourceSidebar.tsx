import type { SearchSource } from './types'

interface Props {
  sources: SearchSource[]
  highlightedSource: number | null
}

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

export default function EvidenceSourceSidebar({ sources, highlightedSource }: Props) {
  if (!sources || sources.length === 0) return null

  const grouped: Record<string, (SearchSource & { index: number })[]> = {}
  sources.forEach((s, i) => {
    const type = s.type || 'other'
    if (!grouped[type]) grouped[type] = []
    grouped[type].push({ ...s, index: i })
  })

  return (
    <div className="ev-sidebar-content">
      <h3 className="ev-sidebar-title">
        Sources
        <span className="ev-source-count">{sources.length}</span>
      </h3>
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type} className="ev-source-group">
          <h4 className="ev-source-group-title">
            <span>{typeIcons[type] || '\u{1F4CE}'}</span>
            {typeLabels[type] || type}
            <span className="ev-source-group-count">{items.length}</span>
          </h4>
          {items.map((source) => (
            <div key={source.index} className={`ev-source-card ${highlightedSource === source.index ? 'ev-source-highlighted' : ''}`}>
              <div className="ev-source-card-header">
                <span className="ev-source-number">{source.index + 1}</span>
                <span className="ev-source-type-label">{source.source_name}</span>
              </div>
              <div className="ev-source-card-body">
                <p className="ev-source-title">
                  {source.url?.startsWith('http') ? (
                    <a href={source.url} target="_blank" rel="noopener noreferrer">{source.title || 'Untitled'}</a>
                  ) : (source.title || 'Untitled')}
                </p>
                {source.company && (
                  <p className="ev-source-company">
                    {source.ticker && <span className="ev-ticker-badge">{source.ticker}</span>}
                    {source.company}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
