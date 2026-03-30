import { useState, useEffect } from 'react'

// ============================================================
// Type definitions for Trial Forecaster
// ============================================================

interface TrialForecasterStatus {
  ready: boolean
  message?: string
}

interface TrialInfo {
  nct_id: string
  title: string
  phase: string
  condition: string
  sponsor: string
  enrollment: number
  status: string
}

interface Anchor {
  name: string
  estimate: string
  weight: number
}

interface RiskFactor {
  title: string
  description: string
  severity: 'high' | 'medium' | 'low'
}

interface ForecastResult {
  probability_of_success: number
  true_effect_estimate: string
  winners_curse_estimate: string
  anchors: Anchor[]
  risk_factors: RiskFactor[]
  power_curve?: string[]
}

interface Parameter {
  name: string
  type: 'numeric' | 'categorical'
  label: string
  default: number | string
  min?: number
  max?: number
  step?: number
  options?: string[]
  description?: string
}

interface ParameterDefinitions {
  parameters: Parameter[]
}

// ============================================================
// Main Component
// ============================================================

interface Props {
  onTrialSearch?: (query: string) => void
}

export default function TrialForecasterPanel({ onTrialSearch: _onTrialSearch }: Props) {
  // Panel state
  const [status, setStatus] = useState<TrialForecasterStatus | null>(null)
  const [loading, setLoading] = useState(true)

  // Search and quick info state
  const [searchQuery, setSearchQuery] = useState('')
  const [trialInfo, setTrialInfo] = useState<TrialInfo | null>(null)
  const [quickSearchLoading, setQuickSearchLoading] = useState(false)
  const [quickSearchError, setQuickSearchError] = useState('')

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisSteps, setAnalysisSteps] = useState<string[]>([])
  const [forecastResult, setForecastResult] = useState<ForecastResult | null>(null)
  const [analyzeError, setAnalyzeError] = useState('')

  // Parameters state
  const [paramDefinitions, setParamDefinitions] = useState<Parameter[]>([])
  const [paramValues, setParamValues] = useState<Record<string, number | string>>({})
  const [showParameterSliders, setShowParameterSliders] = useState(false)

  // Initial fetch: check status and load parameter definitions
  useEffect(() => {
    async function fetchInitial() {
      try {
        const [statusRes, paramsRes] = await Promise.all([
          fetch('/extract/api/trial-forecaster/status'),
          fetch('/extract/api/trial-forecaster/parameters'),
        ])

        if (statusRes.ok) {
          const statusData = await statusRes.json()
          setStatus(statusData)
        }

        if (paramsRes.ok) {
          const paramsData: ParameterDefinitions = await paramsRes.json()
          setParamDefinitions(paramsData.parameters)
          // Initialize parameter values with defaults
          const defaults: Record<string, number | string> = {}
          paramsData.parameters.forEach(p => {
            defaults[p.name] = p.default
          })
          setParamValues(defaults)
        }
      } catch (e) {
        console.error('Failed to fetch initial data:', e)
      } finally {
        setLoading(false)
      }
    }

    fetchInitial()
  }, [])

  // Quick search handler
  async function handleQuickSearch() {
    if (!searchQuery.trim()) return

    setQuickSearchLoading(true)
    setQuickSearchError('')
    setTrialInfo(null)

    try {
      const res = await fetch('/extract/api/trial-forecaster/quick-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim() }),
      })

      if (!res.ok) {
        setQuickSearchError('Trial not found. Please check the NCT ID or drug name.')
        return
      }

      const data = await res.json()
      setTrialInfo(data)
    } catch (e) {
      setQuickSearchError('Error searching for trial')
      console.error(e)
    } finally {
      setQuickSearchLoading(false)
    }
  }

  // Full analysis handler with SSE streaming
  async function handleAnalyze() {
    if (!trialInfo) return

    setAnalyzing(true)
    setAnalysisSteps([])
    setForecastResult(null)
    setAnalyzeError('')

    try {
      const res = await fetch('/extract/api/trial-forecaster/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery.trim(),
          params: paramValues,
          n_iterations: 10000,
        }),
      })

      if (!res.ok) {
        setAnalyzeError('Analysis failed')
        setAnalyzing(false)
        return
      }

      // Handle SSE streaming
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6)
              const data = JSON.parse(jsonStr)

              if (data.type === 'step') {
                setAnalysisSteps(prev => [...prev, data.step])
              } else if (data.type === 'result') {
                setForecastResult(data.data)
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (e) {
      setAnalyzeError('Error running analysis')
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  // Handle parameter value changes
  function handleParamChange(paramName: string, value: string | number) {
    setParamValues(prev => ({
      ...prev,
      [paramName]: value,
    }))
  }

  // Reset parameters to defaults
  function handleResetParams() {
    const defaults: Record<string, number | string> = {}
    paramDefinitions.forEach(p => {
      defaults[p.name] = p.default
    })
    setParamValues(defaults)
  }

  // Re-run analysis with current parameters
  async function handleRerun() {
    await handleAnalyze()
  }

  return (
    <div className="ev-trial-forecaster-panel">
      {/* Header */}
      <div className="ev-panel-header">
        <h3>Trial Forecaster</h3>
        <span className="ev-panel-subtitle">Monte Carlo probability of success</span>
      </div>

      {/* Status indicator */}
      {!loading && status && (
        <div className="ev-forecast-status">
          <span
            className={`ev-status-dot ${status.ready ? 'ready' : 'not-ready'}`}
          />
          <span className="ev-status-label">
            {status.ready ? 'Ready to forecast' : status.message || 'Loading...'}
          </span>
        </div>
      )}

      {/* Search input */}
      <div className="ev-forecast-search">
        <label className="ev-forecast-label">Find a trial</label>
        <div className="ev-forecast-input-row">
          <input
            className="ev-forecast-input"
            type="text"
            placeholder="NCT05202860 or obicetrapib PREVAIL"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleQuickSearch()}
            disabled={quickSearchLoading}
          />
          <button
            className="ev-forecast-btn"
            onClick={handleQuickSearch}
            disabled={quickSearchLoading || !searchQuery.trim()}
          >
            {quickSearchLoading ? '...' : 'Analyze'}
          </button>
        </div>
        {quickSearchError && (
          <p className="ev-forecast-error">{quickSearchError}</p>
        )}
      </div>

      {/* Quick trial info card */}
      {trialInfo && !forecastResult && (
        <div className="ev-forecast-trial-info">
          <div className="ev-trial-info-header">
            <div className="ev-trial-nct">{trialInfo.nct_id}</div>
            <div className="ev-trial-phase">{trialInfo.phase}</div>
          </div>
          <h4 className="ev-trial-title">{trialInfo.title}</h4>
          <div className="ev-trial-details">
            <div className="ev-detail-row">
              <span className="ev-detail-label">Condition:</span>
              <span className="ev-detail-value">{trialInfo.condition}</span>
            </div>
            <div className="ev-detail-row">
              <span className="ev-detail-label">Sponsor:</span>
              <span className="ev-detail-value">{trialInfo.sponsor}</span>
            </div>
            <div className="ev-detail-row">
              <span className="ev-detail-label">Enrollment:</span>
              <span className="ev-detail-value">{trialInfo.enrollment} patients</span>
            </div>
            <div className="ev-detail-row">
              <span className="ev-detail-label">Status:</span>
              <span className="ev-detail-value">{trialInfo.status}</span>
            </div>
          </div>
        </div>
      )}

      {/* Forecast results section */}
      {forecastResult && (
        <div className="ev-forecast-results">
          {/* Probability of success - big number */}
          <div className="ev-forecast-hero">
            <div className={`ev-pos-circle ${getPOSColor(forecastResult.probability_of_success)}`}>
              <div className="ev-pos-percentage">
                {(forecastResult.probability_of_success * 100).toFixed(1)}%
              </div>
              <div className="ev-pos-label">Probability<br />of Success</div>
            </div>
          </div>

          {/* Effect estimate */}
          <div className="ev-forecast-section">
            <h5 className="ev-forecast-section-title">Effect Estimate</h5>
            <p className="ev-effect-estimate">
              <strong>{forecastResult.true_effect_estimate}</strong>
            </p>
            {forecastResult.winners_curse_estimate && (
              <p className="ev-winners-curse-note">
                ⚠️ If positive, expect observed:<br />
                <strong>{forecastResult.winners_curse_estimate}</strong>
              </p>
            )}
          </div>

          {/* Anchors */}
          {forecastResult.anchors && forecastResult.anchors.length > 0 && (
            <div className="ev-forecast-section">
              <h5 className="ev-forecast-section-title">Analytical Anchors</h5>
              <div className="ev-anchors-list">
                {forecastResult.anchors.map((anchor, i) => (
                  <div key={i} className="ev-anchor-card">
                    <div className="ev-anchor-header">
                      <span className="ev-anchor-name">{anchor.name}</span>
                      <span className="ev-anchor-weight">{(anchor.weight * 100).toFixed(0)}%</span>
                    </div>
                    <div className="ev-anchor-estimate">{anchor.estimate}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk factors */}
          {forecastResult.risk_factors && forecastResult.risk_factors.length > 0 && (
            <div className="ev-forecast-section">
              <h5 className="ev-forecast-section-title">Risk Factors</h5>
              <div className="ev-risk-factors">
                {forecastResult.risk_factors.map((factor, i) => (
                  <div
                    key={i}
                    className={`ev-risk-factor-card ev-risk-${factor.severity}`}
                  >
                    <div className="ev-risk-severity">{factor.severity.toUpperCase()}</div>
                    <h6 className="ev-risk-title">{factor.title}</h6>
                    <p className="ev-risk-description">{factor.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Power curve (if available) */}
          {forecastResult.power_curve && forecastResult.power_curve.length > 0 && (
            <div className="ev-forecast-section">
              <h5 className="ev-forecast-section-title">Power Curve</h5>
              <div className="ev-power-curve">
                {forecastResult.power_curve.map((line, i) => (
                  <div key={i} className="ev-power-curve-line">{line}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Parameter sliders section */}
      {trialInfo && paramDefinitions.length > 0 && (
        <div className="ev-forecast-params-section">
          <button
            className="ev-forecast-params-toggle"
            onClick={() => setShowParameterSliders(!showParameterSliders)}
          >
            <span>⚙️ Adjust Parameters</span>
            <span className="ev-toggle-arrow">
              {showParameterSliders ? '▼' : '▶'}
            </span>
          </button>

          {showParameterSliders && (
            <div className="ev-forecast-params">
              {paramDefinitions.map(param => (
                <div key={param.name} className="ev-param-control">
                  <label className="ev-param-label">
                    {param.label}
                    {param.description && (
                      <span className="ev-param-desc">{param.description}</span>
                    )}
                  </label>

                  {param.type === 'numeric' && (
                    <div className="ev-param-numeric">
                      <input
                        type="range"
                        min={param.min}
                        max={param.max}
                        step={param.step}
                        value={paramValues[param.name] as number}
                        onChange={e =>
                          handleParamChange(param.name, parseFloat(e.target.value))
                        }
                        className="ev-param-slider"
                      />
                      <span className="ev-param-value">
                        {(paramValues[param.name] as number).toFixed(2)}
                      </span>
                    </div>
                  )}

                  {param.type === 'categorical' && (
                    <select
                      value={paramValues[param.name] as string}
                      onChange={e => handleParamChange(param.name, e.target.value)}
                      className="ev-param-select"
                    >
                      {param.options?.map(opt => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              ))}

              <div className="ev-forecast-param-actions">
                <button
                  className="ev-forecast-btn ev-forecast-rerun-btn"
                  onClick={handleRerun}
                  disabled={analyzing}
                >
                  {analyzing ? 'Running...' : 'Re-run'}
                </button>
                <button
                  className="ev-forecast-btn ev-forecast-reset-btn"
                  onClick={handleResetParams}
                  disabled={analyzing}
                >
                  Reset
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Loading state during analysis */}
      {analyzing && (
        <div className="ev-forecast-loading">
          <div className="ev-forecast-loading-title">Running simulation...</div>
          <div className="ev-loading-steps">
            {analysisSteps.map((step, i) => (
              <div key={i} className="ev-loading-step step-done">
                <span className="ev-step-icon">✓</span>
                <span className="ev-step-label">{step}</span>
              </div>
            ))}
            <div className="ev-loading-step step-active">
              <span className="ev-step-icon">⟳</span>
              <span className="ev-step-label">Simulating outcomes...</span>
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {analyzeError && (
        <div className="ev-forecast-error-state">
          <p>{analyzeError}</p>
        </div>
      )}

      {/* Empty/initial state */}
      {loading && (
        <div className="ev-panel-loading">Loading forecaster...</div>
      )}

      {!loading && !trialInfo && !forecastResult && !analyzing && (
        <div className="ev-panel-empty-msg">
          <p>Enter an NCT ID or drug name to run a probability of success forecast.</p>
          <p className="ev-panel-tip">Try: "NCT05202860" or "obicetrapib"</p>
        </div>
      )}
    </div>
  )
}

// ============================================================
// Helper functions
// ============================================================

function getPOSColor(probability: number): string {
  if (probability > 0.6) return 'ev-pos-green'
  if (probability >= 0.3) return 'ev-pos-yellow'
  return 'ev-pos-red'
}
