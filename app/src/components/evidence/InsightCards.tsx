import { useState, useEffect } from 'react'

interface Insight {
  type: string
  title: string
  body: string
  confidence_label: 'confirmed' | 'likely' | 'speculative'
  confidence_score: number
  evidence: string[]
  is_new: boolean
  drug?: string
  ranking?: {
    area: string
    drugs: number
    active_trials: number
    total_trials: number
    phase3_plus: number
    score: number
  }[]
}

interface InsightData {
  ticker: string
  company: string
  total_trials: number
  total_assets: number
  total_active: number
  insight_count: number
  insights: Insight[]
}

const TYPE_META: Record<string, { icon: string; label: string; color: string }> = {
  pipeline_shift:     { icon: '🔄', label: 'Pipeline Shift',     color: '#1565C0' },
  strategic_emphasis:  { icon: '🎯', label: 'Strategic Focus',    color: '#2E7D32' },
  competitive_gap:     { icon: '⚠️', label: 'Competitive Gap',    color: '#E65100' },
  data_inconsistency:  { icon: '🔍', label: 'Data Inconsistency', color: '#7B1FA2' },
  risk_signal:         { icon: '🚨', label: 'Risk Signal',        color: '#C62828' },
  catalyst_alert:      { icon: '📅', label: 'Catalyst Alert',     color: '#00695C' },
  portfolio_ranking:   { icon: '📊', label: 'Portfolio Ranking',  color: '#37474F' },
}

const CONFIDENCE_STYLES: Record<string, { bg: string; text: string }> = {
  confirmed:   { bg: '#E8F5E9', text: '#2E7D32' },
  likely:      { bg: '#FFF3E0', text: '#E65100' },
  speculative: { bg: '#FCE4EC', text: '#C62828' },
}

interface Props {
  ticker: string
  companyName: string
}

export default function InsightCards({ ticker, companyName }: Props) {
  const [data, setData] = useState<InsightData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    setError('')
    fetch(`/extract/api/insights?ticker=${ticker}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) throw new Error(d.error)
        setData(d)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [ticker])

  if (loading) {
    return (
      <div className="ic-loading">
        <div className="ic-loading-spinner" />
        Generating insights for {companyName}...
      </div>
    )
  }

  if (error) return <div className="ic-error">{error}</div>
  if (!data || data.insights.length === 0) {
    return <div className="ic-empty">No insights available. Run the asset pre-compute pipeline first.</div>
  }

  // Count by type for filter chips
  const typeCounts: Record<string, number> = {}
  data.insights.forEach(i => {
    typeCounts[i.type] = (typeCounts[i.type] || 0) + 1
  })

  const filtered = typeFilter
    ? data.insights.filter(i => i.type === typeFilter)
    : data.insights

  return (
    <div className="ic-container">
      {/* Type filter chips */}
      <div className="ic-filters">
        <button
          className={`ic-type-chip ${!typeFilter ? 'active' : ''}`}
          onClick={() => setTypeFilter('')}
        >
          All ({data.insights.length})
        </button>
        {Object.entries(typeCounts).map(([type, count]) => {
          const meta = TYPE_META[type] || { icon: '•', label: type, color: '#666' }
          return (
            <button
              key={type}
              className={`ic-type-chip ${typeFilter === type ? 'active' : ''}`}
              onClick={() => setTypeFilter(prev => prev === type ? '' : type)}
              style={typeFilter === type ? { borderColor: meta.color, color: meta.color } : {}}
            >
              {meta.icon} {meta.label} ({count})
            </button>
          )
        })}
      </div>

      {/* Insight cards */}
      <div className="ic-cards">
        {filtered.map((insight, idx) => {
          const meta = TYPE_META[insight.type] || { icon: '•', label: insight.type, color: '#666' }
          const confStyle = CONFIDENCE_STYLES[insight.confidence_label] || CONFIDENCE_STYLES.speculative
          const isExpanded = expandedIdx === idx

          return (
            <div
              key={idx}
              className={`ic-card ${isExpanded ? 'expanded' : ''}`}
              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
            >
              <div className="ic-card-header">
                <div className="ic-card-tags">
                  <span className="ic-type-tag" style={{ color: meta.color }}>{meta.icon} {meta.label}</span>
                  <span className="ic-conf-tag" style={{ background: confStyle.bg, color: confStyle.text }}>
                    {insight.confidence_label} {insight.confidence_score}%
                  </span>
                  {insight.is_new && <span className="ic-new-tag">NEW</span>}
                </div>
                <h4 className="ic-card-title">{insight.title}</h4>
              </div>

              <p className="ic-card-body">{insight.body}</p>

              {isExpanded && insight.evidence && insight.evidence.length > 0 && (
                <div className="ic-evidence">
                  <span className="ic-evidence-label">Evidence:</span>
                  {insight.evidence.map((ev, i) => (
                    <div key={i} className="ic-evidence-item">→ {ev}</div>
                  ))}
                </div>
              )}

              {isExpanded && insight.ranking && (
                <div className="ic-ranking">
                  <table className="ic-ranking-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Therapeutic Area</th>
                        <th>Drugs</th>
                        <th>Active</th>
                        <th>Ph3+</th>
                        <th>Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {insight.ranking.map((r, i) => (
                        <tr key={i}>
                          <td>{i + 1}</td>
                          <td>{r.area}</td>
                          <td>{r.drugs}</td>
                          <td>{r.active_trials}</td>
                          <td>{r.phase3_plus}</td>
                          <td>{r.score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
