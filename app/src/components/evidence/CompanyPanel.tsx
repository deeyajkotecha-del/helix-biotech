import { useState, useEffect } from 'react'
import type { Company, CompanyListResponse } from './types'
import CompanyDetailView from './CompanyDetailView'

// ============================================================
// Main Component — company list + detail orchestrator
// ============================================================

interface Props {
  onCompanySearch: (ticker: string, name: string) => void
}

export default function CompanyPanel({ onCompanySearch }: Props) {
  const [data, setData] = useState<CompanyListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedCat, setExpandedCat] = useState<string | null>(null)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)

  // Webcast counts per ticker (for badges in the list)
  const [webcastCounts, setWebcastCounts] = useState<Record<string, number>>({})

  useEffect(() => {
    async function init() {
      try {
        const [compRes, wcRes] = await Promise.all([
          fetch('/extract/api/companies'),
          fetch('/extract/api/webcasts/library?limit=200'),
        ])
        if (compRes.ok) setData(await compRes.json())
        if (wcRes.ok) {
          const wcData = await wcRes.json()
          const counts: Record<string, number> = {}
          for (const w of (wcData.webcasts || [])) {
            const t = (w.ticker || '').toUpperCase()
            if (t) counts[t] = (counts[t] || 0) + 1
          }
          setWebcastCounts(counts)
        }
      } catch (e) {
        console.error('CompanyPanel init:', e)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  if (loading) return <div className="ev-panel-loading">Loading companies...</div>
  if (!data) return <div className="ev-panel-empty">Could not load companies</div>

  // Detail view for selected company
  if (selectedCompany) {
    return (
      <CompanyDetailView
        company={selectedCompany}
        onBack={() => setSelectedCompany(null)}
        onCompanySearch={onCompanySearch}
      />
    )
  }

  // Company list (default view)
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
          filtered.map(c => (
            <CompanyRow
              key={c.ticker}
              company={c}
              webcastCount={webcastCounts[c.ticker.toUpperCase()] || 0}
              onClick={() => setSelectedCompany(c)}
            />
          ))
        ) : (
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
                    <CompanyRow
                      key={c.ticker}
                      company={c}
                      webcastCount={webcastCounts[c.ticker.toUpperCase()] || 0}
                      onClick={() => setSelectedCompany(c)}
                    />
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

// ============================================================
// Company Row — shows doc pages + webcast count
// ============================================================

function CompanyRow({ company, webcastCount, onClick }: {
  company: Company
  webcastCount: number
  onClick: () => void
}) {
  return (
    <button className="ev-company-row" onClick={onClick}>
      <span className="ev-company-ticker">{company.ticker}</span>
      <span className="ev-company-name">{company.name}</span>
      <span className="ev-company-stats">
        <span className="ev-company-pages">{company.doc_page_count} pages</span>
        {webcastCount > 0 && (
          <span className="ev-company-webcasts">{webcastCount} wc</span>
        )}
      </span>
    </button>
  )
}
