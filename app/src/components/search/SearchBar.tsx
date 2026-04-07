import { useEffect, FormEvent, RefObject } from 'react'

interface SearchBarProps {
  query: string
  setQuery: (q: string) => void
  onSearch: () => void
  loading: boolean
  compact: boolean
  inputRef?: RefObject<HTMLInputElement>
  placeholder?: string
}

export default function SearchBar({ query, setQuery, onSearch, loading, compact, inputRef, placeholder }: SearchBarProps) {

  useEffect(() => {
    if (!compact && inputRef?.current) {
      inputRef.current.focus()
    }
  }, [compact, inputRef])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!loading && query.trim()) {
      onSearch()
    }
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <div className="search-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.3-4.3"/>
        </svg>
      </div>
      <input
        ref={inputRef}
        type="text"
        className="search-input"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder || "Ask anything about biotech — drugs, trials, landscapes, targets..."}
        disabled={loading}
      />
      <button
        type="submit"
        className="search-button"
        disabled={loading || !query.trim()}
      >
        {loading ? (
          <div className="button-spinner" />
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
