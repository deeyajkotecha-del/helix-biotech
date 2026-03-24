interface Props {
  examples: string[]
  onExampleClick: (q: string) => void
}

export default function EvidenceLanding({ examples, onExampleClick }: Props) {
  return (
    <div className="ev-landing">
      <div className="ev-hero-content">
        <h1 className="ev-hero-title">
          Open Evidence<br />
          <span className="ev-hero-accent">for biopharma intelligence</span>
        </h1>
        <p className="ev-hero-subtitle">
          Search across 60 companies, clinical trials, SEC filings, drug entity databases,
          enrichment pipelines, and regional biotech trackers. Get cited answers backed by real data.
        </p>

        <div className="ev-capability-badges">
          <div className="ev-cap-badge">
            <span className="ev-cap-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            </span>
            60 Companies
          </div>
          <div className="ev-cap-badge">
            <span className="ev-cap-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            </span>
            Drug Enrichment
          </div>
          <div className="ev-cap-badge">
            <span className="ev-cap-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg>
            </span>
            Global Trackers
          </div>
          <div className="ev-cap-badge">
            <span className="ev-cap-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
            </span>
            Document Library
          </div>
        </div>

        <div className="ev-source-badges">
          <span className="ev-src-badge">ClinicalTrials.gov</span>
          <span className="ev-src-badge">PubMed</span>
          <span className="ev-src-badge">FDA</span>
          <span className="ev-src-badge">Drug Entity DB</span>
          <span className="ev-src-badge">IR Documents</span>
          <span className="ev-src-badge">China</span>
          <span className="ev-src-badge">Korea</span>
          <span className="ev-src-badge">Europe</span>
        </div>

        <div className="ev-example-grid">
          {examples.map((q, i) => (
            <button
              key={i}
              className="ev-example-chip"
              onClick={() => onExampleClick(q)}
            >
              <span className="ev-chip-icon">
                {i < 2 ? '\u{1F3AF}' : i < 4 ? '\u{1F30F}' : '\u{1F52C}'}
              </span>
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
