import { useState, useEffect } from 'react'
import type { EnrichmentStatus } from './types'

export default function EnrichmentPanel() {
  const [status, setStatus] = useState<EnrichmentStatus | null>(null)
  const [drugName, setDrugName] = useState('')
  const [lookupResult, setLookupResult] = useState<any>(null)
  const [lookupLoading, setLookupLoading] = useState(false)

  useEffect(() => {
    fetch('/extract/api/enrichment/status')
      .then(r => r.json())
      .then(setStatus)
      .catch(() => {})
  }, [])

  async function handleLookup() {
    if (!drugName.trim()) return
    setLookupLoading(true)
    setLookupResult(null)
    try {
      const res = await fetch('/extract/api/enrichment/lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drug_name: drugName.trim() }),
      })
      const data = await res.json()
      setLookupResult(data)
    } catch (e) {
      setLookupResult({ error: 'Lookup failed' })
    } finally {
      setLookupLoading(false)
    }
  }

  return (
    <div className="ev-enrichment-panel">
      <div className="ev-panel-header">
        <h3>Drug Enrichment</h3>
        <span className="ev-panel-subtitle">ClinicalTrials.gov + Drug Entity DB</span>
      </div>

      {/* Status indicators */}
      <div className="ev-status-grid">
        <StatusDot label="Search Engine" ready={status?.search_ready} />
        <StatusDot label="Drug Entity DB" ready={status?.drug_db_available} />
        <StatusDot label="Enrichment Agent" ready={status?.enrichment_ready} />
        <StatusDot label="RAG Library" ready={status?.rag_available} />
      </div>

      {/* Drug lookup */}
      <div className="ev-enrichment-lookup">
        <label className="ev-lookup-label">Look up a drug candidate</label>
        <div className="ev-lookup-row">
          <input
            className="ev-lookup-input"
            placeholder="e.g. RMC-6236, inavolisib, datopotamab..."
            value={drugName}
            onChange={e => setDrugName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLookup()}
          />
          <button className="ev-lookup-btn" onClick={handleLookup} disabled={lookupLoading || !drugName.trim()}>
            {lookupLoading ? '...' : 'Look up'}
          </button>
        </div>
      </div>

      {/* Result */}
      {lookupResult && (
        <div className="ev-lookup-result">
          {lookupResult.error ? (
            <p className="ev-lookup-error">{lookupResult.error}</p>
          ) : (
            <>
              <h4 className="ev-lookup-drug">{lookupResult.drug_name}</h4>

              {lookupResult.entity_db && (
                <div className="ev-lookup-section">
                  <span className="ev-lookup-tag">Entity DB</span>
                  <p><strong>{lookupResult.entity_db.canonical_name}</strong></p>
                  {lookupResult.entity_db.company_name && <p>Company: {lookupResult.entity_db.company_name} ({lookupResult.entity_db.company_ticker})</p>}
                  {lookupResult.entity_db.modality && <p>Modality: {lookupResult.entity_db.modality}</p>}
                  {lookupResult.entity_db.mechanism && <p>Mechanism: {lookupResult.entity_db.mechanism}</p>}
                  {lookupResult.entity_db.phase_highest && <p>Phase: {lookupResult.entity_db.phase_highest}</p>}
                </div>
              )}

              {lookupResult.ctgov && (
                <div className="ev-lookup-section">
                  <span className="ev-lookup-tag">ClinicalTrials.gov</span>
                  {lookupResult.ctgov.trials_found !== undefined && (
                    <p>{lookupResult.ctgov.trials_found} trials found</p>
                  )}
                  {lookupResult.ctgov.best_match && (
                    <p>Best match: {lookupResult.ctgov.best_match.phase} — {lookupResult.ctgov.best_match.status}</p>
                  )}
                </div>
              )}

              {!lookupResult.entity_db && !lookupResult.ctgov && (
                <p className="ev-lookup-empty">No data found for this drug candidate.</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function StatusDot({ label, ready }: { label: string; ready?: boolean }) {
  return (
    <div className="ev-status-item">
      <span className={`ev-status-dot ${ready ? 'ready' : 'not-ready'}`} />
      <span className="ev-status-label">{label}</span>
    </div>
  )
}
