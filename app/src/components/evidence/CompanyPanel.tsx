import { useState, useEffect } from 'react'
import type { Company, CompanyListResponse } from './types'

interface Props {
  onCompanySearch: (ticker: string, name: string) => void
}

export default function CompanyPanel({ onCompanySearch }: Props) {
  const [data, setData] = useState<CompanyListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedCat, setExpandedCat] = useState<string | null>(null)

  useEffect(() => {
    fetch('/extract/api/companies')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="ev-panel-loading">Loading companies...</div>
  if (!data) return <div className="ev-panel-empty">Could not load companies</div>

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
          /* Flat filtered list */
          filtered.map(c => (
            <CompanyRow key={c.ticker} company={c} onClick={() => onCompanySearch(c.ticker, c.name)} />
          ))
        ) : (
          /* Grouped by category */
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
                    <CompanyRow key={c.ticker} company={c} onClick={() => onCompanySearch(c.ticker, c.name)} />
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

function CompanyRow({ company, onClick }: { company: Company; onClick: () => void }) {
  return (
    <button className="ev-company-row" onClick={onClick}>
      <span className="ev-company-ticker">{company.ticker}</span>
      <span className="ev-company-name">{company.name}</span>
      <span className="ev-company-pages">{company.doc_page_count} pages</span>
    </button>
  )
}
