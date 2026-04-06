import { useState, useEffect } from 'react'

interface Trial {
  nct_id: string
  title: string
  official_title?: string
  status: string
  phase: string
  conditions: string[]
  interventions: { name: string; type: string }[]
  sponsor: string
  start_date: string
  enrollment: number
  study_type?: string
  summary?: string
  primary_outcomes?: string[]
  url: string
}

interface Props {
  ticker: string
  companyName: string
}

const STATUS_COLORS: Record<string, string> = {
  RECRUITING: '#2E7D32',
  ACTIVE_NOT_RECRUITING: '#1565C0',
  COMPLETED: '#6A6A6A',
  ENROLLING_BY_INVITATION: '#7B1FA2',
  NOT_YET_RECRUITING: '#E65100',
  SUSPENDED: '#C62828',
  TERMINATED: '#C62828',
  WITHDRAWN: '#9E9E9E',
}

const PHASE_ORDER: Record<string, number> = {
  'PHASE4': 5, 'PHASE3': 4, 'PHASE2': 3,
  'PHASE2,PHASE3': 3.5, 'PHASE1,PHASE2': 2.5,
  'PHASE1': 2, 'EARLY_PHASE1': 1, 'NA': 0,
}

function formatPhase(raw: string): string {
  if (!raw) return '—'
  return raw
    .replace(/PHASE/g, 'Ph ')
    .replace(/EARLY_Ph 1/g, 'Early Ph1')
    .replace(/,/g, '/')
    .replace(/NA/g, 'N/A')
    .trim()
}

function formatStatus(raw: string): string {
  return raw
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}

export default function ClinicalTrialsTable({ ticker, companyName }: Props) {
  const [trials, setTrials] = useState<Trial[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sortBy, setSortBy] = useState<'phase' | 'status' | 'date'>('phase')
  const [filterPhase, setFilterPhase] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [expandedTrial, setExpandedTrial] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError('')
    fetch(`/extract/api/clinical-trials?ticker=${ticker}&company=${encodeURIComponent(companyName)}`)
      .then(r => r.json())
      .then(data => {
        setTrials(data.trials || [])
        if (data.error) setError(data.error)
      })
      .catch(() => setError('Failed to fetch clinical trials'))
      .finally(() => setLoading(false))
  }, [ticker, companyName])

  // Get unique phases and statuses for filters
  const allPhases = [...new Set(trials.map(t => t.phase).filter(Boolean))].sort(
    (a, b) => (PHASE_ORDER[b] || 0) - (PHASE_ORDER[a] || 0)
  )
  const allStatuses = [...new Set(trials.map(t => t.status).filter(Boolean))].sort()

  // Filter
  let filtered = trials
  if (filterPhase) filtered = filtered.filter(t => t.phase === filterPhase)
  if (filterStatus) filtered = filtered.filter(t => t.status === filterStatus)

  // Sort
  filtered = [...filtered].sort((a, b) => {
    if (sortBy === 'phase') return (PHASE_ORDER[b.phase] || 0) - (PHASE_ORDER[a.phase] || 0)
    if (sortBy === 'status') return a.status.localeCompare(b.status)
    if (sortBy === 'date') return (b.start_date || '').localeCompare(a.start_date || '')
    return 0
  })

  if (loading) {
    return (
      <div className="ct-loading">
        <div className="ct-loading-spinner" />
        Fetching clinical trials from ClinicalTrials.gov...
      </div>
    )
  }

  if (error && trials.length === 0) {
    return <div className="ct-error">{error}</div>
  }

  if (trials.length === 0) {
    return <div className="ct-empty">No clinical trials found for {companyName}.</div>
  }

  // Count by phase for summary bar
  const phaseCounts: Record<string, number> = {}
  trials.forEach(t => {
    const p = formatPhase(t.phase) || 'Other'
    phaseCounts[p] = (phaseCounts[p] || 0) + 1
  })

  const recruitingCount = trials.filter(t => t.status === 'RECRUITING').length

  return (
    <div className="ct-container">
      {/* Summary bar */}
      <div className="ct-summary">
        <span className="ct-summary-total">{trials.length} trials</span>
        <span className="ct-summary-recruiting">{recruitingCount} recruiting</span>
        <div className="ct-summary-phases">
          {Object.entries(phaseCounts)
            .sort((a, b) => b[1] - a[1])
            .map(([phase, count]) => (
              <span key={phase} className="ct-phase-chip">{phase}: {count}</span>
            ))}
        </div>
      </div>

      {/* Filters + sort */}
      <div className="ct-controls">
        <select
          className="ct-filter-select"
          value={filterPhase}
          onChange={e => setFilterPhase(e.target.value)}
        >
          <option value="">All phases</option>
          {allPhases.map(p => (
            <option key={p} value={p}>{formatPhase(p)}</option>
          ))}
        </select>
        <select
          className="ct-filter-select"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          {allStatuses.map(s => (
            <option key={s} value={s}>{formatStatus(s)}</option>
          ))}
        </select>
        <div className="ct-sort-btns">
          {(['phase', 'status', 'date'] as const).map(s => (
            <button
              key={s}
              className={`ct-sort-btn ${sortBy === s ? 'active' : ''}`}
              onClick={() => setSortBy(s)}
            >
              {s === 'phase' ? 'Phase' : s === 'status' ? 'Status' : 'Date'}
            </button>
          ))}
        </div>
      </div>

      {/* Trials table */}
      <div className="ct-table">
        <div className="ct-table-header">
          <span className="ct-col-phase">Phase</span>
          <span className="ct-col-status">Status</span>
          <span className="ct-col-title">Trial</span>
          <span className="ct-col-conditions">Indication</span>
          <span className="ct-col-enrollment">N</span>
          <span className="ct-col-date">Start</span>
        </div>

        {filtered.map(trial => (
          <div key={trial.nct_id} className="ct-trial-group">
            <div
              className={`ct-trial-row ${expandedTrial === trial.nct_id ? 'expanded' : ''}`}
              onClick={() => setExpandedTrial(
                expandedTrial === trial.nct_id ? null : trial.nct_id
              )}
            >
              <span className="ct-col-phase">
                <span className="ct-phase-badge">{formatPhase(trial.phase)}</span>
              </span>
              <span className="ct-col-status">
                <span
                  className="ct-status-dot"
                  style={{ background: STATUS_COLORS[trial.status] || '#9E9E9E' }}
                />
                <span className="ct-status-text">{formatStatus(trial.status)}</span>
              </span>
              <span className="ct-col-title">
                <span className="ct-trial-title">{trial.title}</span>
                <span className="ct-nct-id">{trial.nct_id}</span>
              </span>
              <span className="ct-col-conditions">
                {trial.conditions?.slice(0, 2).join(', ') || '—'}
              </span>
              <span className="ct-col-enrollment">
                {trial.enrollment ? trial.enrollment.toLocaleString() : '—'}
              </span>
              <span className="ct-col-date">
                {trial.start_date || '—'}
              </span>
            </div>

            {/* Expanded details */}
            {expandedTrial === trial.nct_id && (
              <div className="ct-trial-detail">
                {trial.official_title && (
                  <div className="ct-detail-row">
                    <span className="ct-detail-label">Full Title</span>
                    <span className="ct-detail-value">{trial.official_title}</span>
                  </div>
                )}
                {trial.interventions?.length > 0 && (
                  <div className="ct-detail-row">
                    <span className="ct-detail-label">Interventions</span>
                    <span className="ct-detail-value">
                      {trial.interventions.map(i =>
                        `${i.name}${i.type ? ` (${i.type})` : ''}`
                      ).join('; ')}
                    </span>
                  </div>
                )}
                {trial.conditions?.length > 0 && (
                  <div className="ct-detail-row">
                    <span className="ct-detail-label">Conditions</span>
                    <span className="ct-detail-value">{trial.conditions.join(', ')}</span>
                  </div>
                )}
                {trial.primary_outcomes && trial.primary_outcomes.length > 0 && (
                  <div className="ct-detail-row">
                    <span className="ct-detail-label">Primary Endpoints</span>
                    <span className="ct-detail-value">{trial.primary_outcomes.join('; ')}</span>
                  </div>
                )}
                {trial.summary && (
                  <div className="ct-detail-row">
                    <span className="ct-detail-label">Summary</span>
                    <span className="ct-detail-value ct-detail-summary">{trial.summary}</span>
                  </div>
                )}
                <div className="ct-detail-row">
                  <span className="ct-detail-label">Sponsor</span>
                  <span className="ct-detail-value">{trial.sponsor}</span>
                </div>
                <a
                  href={trial.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ct-clinicaltrials-link"
                >
                  View on ClinicalTrials.gov &rarr;
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="ct-footer">
        Data from ClinicalTrials.gov &middot; {filtered.length} of {trials.length} shown
      </div>
    </div>
  )
}
