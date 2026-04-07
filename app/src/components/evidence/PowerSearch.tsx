import { useState, useEffect, useMemo } from 'react'

// ============================================================
// Types
// ============================================================

interface Asset {
  drug_name: string
  type: string
  highest_phase: string
  trial_count: number
  phases: Record<string, number>
  statuses: Record<string, number>
  conditions: string[]
  active_count: number
}

interface DrillTrial {
  nct_id: string
  title: string
  official_title?: string
  status: string
  phase: string
  conditions: string[]
  interventions: { name: string; type: string }[]
  enrollment: number
  start_date: string
  sponsor: string
  summary?: string
  url: string
}

// ============================================================
// Helpers
// ============================================================

const PHASE_RANK: Record<string, number> = {
  'PHASE4': 5, 'PHASE3': 4, 'PHASE2,PHASE3': 3.5,
  'PHASE2': 3, 'PHASE1,PHASE2': 2.5,
  'PHASE1': 2, 'EARLY_PHASE1': 1, 'NA': 0, '': 0,
}

const PHASE_COLORS: Record<string, string> = {
  'PHASE4': '#1B5E20',
  'PHASE3': '#2E7D32',
  'PHASE2,PHASE3': '#388E3C',
  'PHASE2': '#1565C0',
  'PHASE1,PHASE2': '#1976D2',
  'PHASE1': '#7B1FA2',
  'EARLY_PHASE1': '#9C27B0',
  'NA': '#757575',
  '': '#9E9E9E',
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

function formatPhase(raw: string): string {
  if (!raw) return '—'
  return raw.replace(/PHASE/g, 'Ph ').replace(/EARLY_Ph 1/g, 'Early Ph1').replace(/,/g, '/').replace(/NA/g, 'N/A').trim()
}

function formatStatus(raw: string): string {
  return raw.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

// ============================================================
// Main Power Search Component
// ============================================================

interface Props {
  ticker: string
  companyName: string
}

export default function PowerSearch({ ticker, companyName }: Props) {
  // Step 1 state — asset discovery
  const [assets, setAssets] = useState<Asset[]>([])
  const [totalTrials, setTotalTrials] = useState(0)
  const [loading, setLoading] = useState(true) // Start loading immediately
  const [error, setError] = useState('')
  const [discovered, setDiscovered] = useState(false)
  const [cached, setCached] = useState(false)
  const [cacheAge, setCacheAge] = useState<string | null>(null)

  // Filters
  const [searchFilter, setSearchFilter] = useState('')
  const [phaseFilter, setPhaseFilter] = useState<string>('')
  const [showActiveOnly, setShowActiveOnly] = useState(false)

  // Step 2 state — drug drill-down
  const [selectedDrug, setSelectedDrug] = useState<string | null>(null)
  const [drugTrials, setDrugTrials] = useState<DrillTrial[]>([])
  const [drugLoading, setDrugLoading] = useState(false)
  const [expandedTrial, setExpandedTrial] = useState<string | null>(null)

  // ── Auto-load on mount (from cache = instant, or live = ~15s) ──
  const fetchAssets = async (refresh = false) => {
    setLoading(true)
    setError('')
    try {
      const url = `/extract/api/power-search/assets?ticker=${ticker}&company=${encodeURIComponent(companyName)}${refresh ? '&refresh=true' : ''}`
      const res = await fetch(url)
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setAssets(data.assets || [])
      setTotalTrials(data.total_trials || 0)
      setCached(data.cached || false)
      setCacheAge(data.cache_age || null)
      setDiscovered(true)
    } catch (e: any) {
      setError(e.message || 'Failed to discover assets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAssets()
  }, [ticker])

  // ── Step 2: Drill into a specific drug ──
  const drillIntoDrug = async (drugName: string) => {
    setSelectedDrug(drugName)
    setDrugLoading(true)
    setExpandedTrial(null)
    try {
      const res = await fetch(
        `/extract/api/power-search/drug-trials?drug=${encodeURIComponent(drugName)}&ticker=${ticker}`
      )
      const data = await res.json()
      setDrugTrials(data.trials || [])
    } catch {
      setDrugTrials([])
    } finally {
      setDrugLoading(false)
    }
  }

  // ── Filtered + sorted assets ──
  const filteredAssets = useMemo(() => {
    let result = assets
    if (searchFilter) {
      const q = searchFilter.toLowerCase()
      result = result.filter(a =>
        a.drug_name.toLowerCase().includes(q) ||
        a.conditions.some(c => c.toLowerCase().includes(q))
      )
    }
    if (phaseFilter) {
      result = result.filter(a => a.highest_phase === phaseFilter)
    }
    if (showActiveOnly) {
      result = result.filter(a => a.active_count > 0)
    }
    return result
  }, [assets, searchFilter, phaseFilter, showActiveOnly])

  // Phase breakdown for summary
  const phaseSummary = useMemo(() => {
    const counts: Record<string, number> = {}
    assets.forEach(a => {
      const ph = a.highest_phase || ''
      counts[ph] = (counts[ph] || 0) + 1
    })
    return Object.entries(counts).sort(
      (a, b) => (PHASE_RANK[b[0]] || 0) - (PHASE_RANK[a[0]] || 0)
    )
  }, [assets])

  // ── Drug drill-down view ──
  if (selectedDrug) {
    return (
      <div className="ps-container">
        <button className="ps-back-btn" onClick={() => setSelectedDrug(null)}>
          ← Back to Asset Tracker
        </button>

        <div className="ps-drug-header">
          <h3 className="ps-drug-name">{selectedDrug}</h3>
          <span className="ps-drug-count">
            {drugTrials.length} registered trial{drugTrials.length !== 1 ? 's' : ''}
          </span>
        </div>

        {drugLoading ? (
          <div className="ps-loading">
            <div className="ps-loading-spinner" />
            Searching ClinicalTrials.gov for all {selectedDrug} trials...
          </div>
        ) : drugTrials.length === 0 ? (
          <div className="ps-empty">No trials found for {selectedDrug}.</div>
        ) : (
          <div className="ps-drill-table">
            <div className="ps-drill-header-row">
              <span className="ps-d-phase">Phase</span>
              <span className="ps-d-status">Status</span>
              <span className="ps-d-title">Trial</span>
              <span className="ps-d-conditions">Indication</span>
              <span className="ps-d-enrollment">N</span>
              <span className="ps-d-date">Start</span>
            </div>
            {drugTrials.map(trial => (
              <div key={trial.nct_id} className="ps-drill-group">
                <div
                  className={`ps-drill-row ${expandedTrial === trial.nct_id ? 'expanded' : ''}`}
                  onClick={() => setExpandedTrial(
                    expandedTrial === trial.nct_id ? null : trial.nct_id
                  )}
                >
                  <span className="ps-d-phase">
                    <span className="ps-phase-badge" style={{ background: PHASE_COLORS[trial.phase] || '#9E9E9E' }}>
                      {formatPhase(trial.phase)}
                    </span>
                  </span>
                  <span className="ps-d-status">
                    <span className="ps-status-dot" style={{ background: STATUS_COLORS[trial.status] || '#9E9E9E' }} />
                    {formatStatus(trial.status)}
                  </span>
                  <span className="ps-d-title">
                    <span className="ps-trial-title">{trial.title}</span>
                    <span className="ps-nct-id">{trial.nct_id}</span>
                  </span>
                  <span className="ps-d-conditions">
                    {trial.conditions?.slice(0, 2).join(', ') || '—'}
                  </span>
                  <span className="ps-d-enrollment">
                    {trial.enrollment ? trial.enrollment.toLocaleString() : '—'}
                  </span>
                  <span className="ps-d-date">{trial.start_date || '—'}</span>
                </div>
                {expandedTrial === trial.nct_id && (
                  <div className="ps-detail-panel">
                    {trial.official_title && (
                      <div className="ps-detail-row">
                        <span className="ps-detail-label">Full Title</span>
                        <span className="ps-detail-value">{trial.official_title}</span>
                      </div>
                    )}
                    {trial.interventions?.length > 0 && (
                      <div className="ps-detail-row">
                        <span className="ps-detail-label">Interventions</span>
                        <span className="ps-detail-value">
                          {trial.interventions.map(i => `${i.name}${i.type ? ` (${i.type})` : ''}`).join('; ')}
                        </span>
                      </div>
                    )}
                    {trial.conditions?.length > 0 && (
                      <div className="ps-detail-row">
                        <span className="ps-detail-label">Conditions</span>
                        <span className="ps-detail-value">{trial.conditions.join(', ')}</span>
                      </div>
                    )}
                    {trial.summary && (
                      <div className="ps-detail-row">
                        <span className="ps-detail-label">Summary</span>
                        <span className="ps-detail-value ps-summary-text">{trial.summary}</span>
                      </div>
                    )}
                    <div className="ps-detail-row">
                      <span className="ps-detail-label">Sponsor</span>
                      <span className="ps-detail-value">{trial.sponsor}</span>
                    </div>
                    <a href={trial.url} target="_blank" rel="noopener noreferrer" className="ps-ct-link">
                      View on ClinicalTrials.gov →
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Main view: discovery + asset tracker ──
  return (
    <div className="ps-container">
      {/* Header */}
      <div className="ps-header">
        <div className="ps-header-text">
          <h3 className="ps-title">Pipeline Tracker</h3>
          <p className="ps-subtitle">
            Every drug asset for {companyName} — click any to see all registered trials.
            {cached && cacheAge && (
              <span className="ps-cache-tag"> Cached {new Date(cacheAge).toLocaleDateString()}</span>
            )}
          </p>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="ps-loading">
          <div className="ps-loading-spinner" />
          {cached === false && !discovered
            ? <>Loading asset map...</>
            : <>Scanning ClinicalTrials.gov for all {companyName} trials...</>
          }
          <span className="ps-loading-sub">
            {cached === false && !discovered ? 'Checking cache...' : 'This may take 10-20 seconds'}
          </span>
        </div>
      )}

      {/* Error */}
      {error && <div className="ps-error">{error}</div>}

      {/* Asset tracker */}
      {discovered && !loading && (
        <>
          {/* Summary bar */}
          <div className="ps-summary">
            <div className="ps-summary-stat">
              <span className="ps-stat-num">{totalTrials.toLocaleString()}</span>
              <span className="ps-stat-label">Total Trials</span>
            </div>
            <div className="ps-summary-stat">
              <span className="ps-stat-num">{assets.length}</span>
              <span className="ps-stat-label">Drug Assets</span>
            </div>
            <div className="ps-summary-stat">
              <span className="ps-stat-num">{assets.filter(a => a.active_count > 0).length}</span>
              <span className="ps-stat-label">Active Assets</span>
            </div>
            <div className="ps-phase-chips">
              {phaseSummary.map(([phase, count]) => (
                <button
                  key={phase}
                  className={`ps-phase-chip ${phaseFilter === phase ? 'active' : ''}`}
                  style={{ borderColor: PHASE_COLORS[phase] || '#9E9E9E' }}
                  onClick={() => setPhaseFilter(prev => prev === phase ? '' : phase)}
                >
                  {formatPhase(phase) || 'Other'}: {count}
                </button>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div className="ps-filters">
            <input
              className="ps-search-input"
              placeholder="Search drugs or indications (e.g. donanemab, KRAS, obesity)..."
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
            />
            <label className="ps-active-toggle">
              <input
                type="checkbox"
                checked={showActiveOnly}
                onChange={e => setShowActiveOnly(e.target.checked)}
              />
              Active trials only
            </label>
            <button className="ps-refresh-btn" onClick={() => fetchAssets(true)} title="Re-fetch from ClinicalTrials.gov">
              {cached ? 'Refresh Live' : 'Refresh'}
            </button>
          </div>

          {/* Asset grid */}
          <div className="ps-asset-grid">
            {filteredAssets.length === 0 ? (
              <div className="ps-empty">No assets match your filters.</div>
            ) : (
              filteredAssets.map(asset => (
                <button
                  key={asset.drug_name}
                  className="ps-asset-card"
                  onClick={() => drillIntoDrug(asset.drug_name)}
                >
                  <div className="ps-asset-top">
                    <span className="ps-asset-name">{asset.drug_name}</span>
                    <span
                      className="ps-asset-phase"
                      style={{ background: PHASE_COLORS[asset.highest_phase] || '#9E9E9E' }}
                    >
                      {formatPhase(asset.highest_phase)}
                    </span>
                  </div>
                  <div className="ps-asset-meta">
                    <span className="ps-asset-trials">{asset.trial_count} trial{asset.trial_count !== 1 ? 's' : ''}</span>
                    {asset.active_count > 0 && (
                      <span className="ps-asset-active">{asset.active_count} active</span>
                    )}
                  </div>
                  <div className="ps-asset-conditions">
                    {asset.conditions.slice(0, 3).join(' · ') || 'No conditions listed'}
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="ps-footer">
            Showing {filteredAssets.length} of {assets.length} assets · Data from ClinicalTrials.gov
          </div>
        </>
      )}
    </div>
  )
}
