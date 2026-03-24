import { useState, useEffect } from 'react'
import type { RegionalStatus, RegionalAlert } from './types'

interface Props {
  onAlertClick: (query: string) => void
}

const REGION_FLAGS: Record<string, string> = {
  china: '\u{1F1E8}\u{1F1F3}',
  korea: '\u{1F1F0}\u{1F1F7}',
  japan: '\u{1F1EF}\u{1F1F5}',
  india: '\u{1F1EE}\u{1F1F3}',
  europe: '\u{1F1EA}\u{1F1FA}',
}

export default function RegionalPanel({ onAlertClick }: Props) {
  const [status, setStatus] = useState<RegionalStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [miningRegion, setMiningRegion] = useState<string | null>(null)

  useEffect(() => {
    fetch('/extract/api/regional/status')
      .then(r => r.json())
      .then(d => { setStatus(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  async function handleMine(region: string) {
    setMiningRegion(region)
    try {
      await fetch('/extract/api/regional/mine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ region }),
      })
      // Refresh status
      const res = await fetch('/extract/api/regional/status')
      const data = await res.json()
      setStatus(data)
    } catch { /* ignore */ }
    finally { setMiningRegion(null) }
  }

  return (
    <div className="ev-regional-panel">
      <div className="ev-panel-header">
        <h3>Global Biotech Tracker</h3>
        <span className="ev-panel-subtitle">Hunt globally for under-the-radar assets</span>
      </div>

      {/* Region buttons */}
      <div className="ev-region-grid">
        {['china', 'korea', 'japan', 'india', 'europe'].map(region => (
          <button
            key={region}
            className="ev-region-btn"
            onClick={() => handleMine(region)}
            disabled={miningRegion !== null}
          >
            <span className="ev-region-flag">{REGION_FLAGS[region]}</span>
            <span className="ev-region-name">{region.charAt(0).toUpperCase() + region.slice(1)}</span>
            {miningRegion === region && <span className="ev-mining-indicator">mining...</span>}
          </button>
        ))}
      </div>

      {/* Status */}
      <div className="ev-regional-status">
        <div className="ev-status-item">
          <span className={`ev-status-dot ${status?.news_miner_ready ? 'ready' : 'not-ready'}`} />
          <span className="ev-status-label">Regional News Miner</span>
        </div>
        <div className="ev-status-item">
          <span className={`ev-status-dot ${status?.global_discovery_ready ? 'ready' : 'not-ready'}`} />
          <span className="ev-status-label">Global Asset Discovery</span>
        </div>
      </div>

      {/* Recent alerts */}
      {status?.recent_alerts && status.recent_alerts.length > 0 && (
        <div className="ev-alerts-section">
          <h4 className="ev-alerts-title">Recent Discoveries</h4>
          <div className="ev-alerts-list">
            {status.recent_alerts.map((alert: RegionalAlert, i: number) => (
              <button
                key={i}
                className="ev-alert-card"
                onClick={() => onAlertClick(`Tell me about ${alert.drug_name} from ${alert.company}`)}
              >
                <div className="ev-alert-top">
                  <span className="ev-alert-flag">{REGION_FLAGS[alert.region] || '\u{1F310}'}</span>
                  <span className="ev-alert-drug">{alert.drug_name}</span>
                  <span className="ev-alert-company">{alert.company}</span>
                </div>
                <p className="ev-alert-summary">{alert.summary}</p>
                <span className="ev-alert-date">{alert.date}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && <div className="ev-panel-loading">Loading tracker status...</div>}

      {!loading && (!status?.recent_alerts || status.recent_alerts.length === 0) && (
        <div className="ev-panel-empty-msg">
          <p>No recent alerts yet. Click a region above to mine for new biotech assets, or search for regional data using the search bar.</p>
          <p className="ev-panel-tip">Try: "Find under-the-radar biotech assets from China and Korea"</p>
        </div>
      )}
    </div>
  )
}
