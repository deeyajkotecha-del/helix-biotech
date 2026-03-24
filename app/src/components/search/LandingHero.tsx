interface LandingHeroProps {
  examples: string[]
  onExampleClick: (q: string) => void
}

export default function LandingHero({ examples, onExampleClick }: LandingHeroProps) {
  return (
    <div className="landing-hero">
      <div className="hero-content">
        <h1 className="hero-title">
          Diligence intelligence<br />
          <span className="hero-accent">for biopharma</span>
        </h1>
        <p className="hero-subtitle">
          Ask questions across clinical trials, SEC filings, literature, and competitive landscapes.
          Get cited answers backed by real data.
        </p>
        <div className="example-grid">
          {examples.map((q, i) => (
            <button
              key={i}
              className="example-chip"
              onClick={() => onExampleClick(q)}
            >
              <span className="chip-icon">
                {i < 2 ? '\u{1F3AF}' : i < 4 ? '\u{1F52C}' : '\u{1F4CA}'}
              </span>
              {q}
            </button>
          ))}
        </div>
      </div>
      <div className="hero-sources">
        <span className="source-badge">ClinicalTrials.gov</span>
        <span className="source-badge">PubMed</span>
        <span className="source-badge">FDA</span>
        <span className="source-badge">Document Library</span>
        <span className="source-badge">Drug Entity DB</span>
      </div>
    </div>
  )
}
