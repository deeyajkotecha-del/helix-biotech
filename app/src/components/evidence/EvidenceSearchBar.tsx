import { useRef, useEffect, FormEvent } from 'react'

interface Props {
  query: string
  setQuery: (q: string) => void
  onSearch: () => void
  loading: boolean
  compact: boolean
}

export default function EvidenceSearchBar({ query, setQuery, onSearch, loading, compact }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!compact && inputRef.current) {
      inputRef.current.focus()
    }
  }, [compact])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!loading && query.trim()) {
      onSearch()
    }
  }

  return (
    <form className="ev-search-bar" onSubmit={handleSubmit}>
      <div className="ev-search-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.3-4.3"/>
        </svg>
      </div>
      <input
        ref={inputRef}
        type="text"
        className="ev-search-input"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search across 60 companies, trials, enrichment data, and global biotech..."
        disabled={loading}
      />
      <button type="submit" className="ev-search-button" disabled={loading || !query.trim()}>
        {loading ? (
          <div className="ev-button-spinner" />
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14"/>
            <path d="m12 5 7 7-7 7"/>
          </svg>
        )}
      </button>
    </form>
  )
}
