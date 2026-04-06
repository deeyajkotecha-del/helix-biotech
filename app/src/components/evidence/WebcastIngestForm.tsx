import { useState } from 'react'
import type { Company } from './types'

interface Props {
  company: Company
  onIngested: () => void
}

export default function WebcastIngestForm({ company, onIngested }: Props) {
  const [form, setForm] = useState({
    url: '',
    title: '',
    event_date: '',
    event_type: 'earnings_call',
    transcript_text: '',
  })
  const [ingesting, setIngesting] = useState(false)
  const [message, setMessage] = useState('')

  const wordCount = form.transcript_text.trim()
    ? form.transcript_text.trim().split(/\s+/).length
    : 0

  async function handleIngest() {
    setIngesting(true)
    setMessage('')

    const hasTranscript = form.transcript_text.trim().length > 0
    const hasUrl = form.url.trim().length > 0

    try {
      let res: Response

      if (hasTranscript) {
        res = await fetch('/extract/api/webcasts/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            transcript_text: form.transcript_text,
            title: form.title || `${company.ticker} ${form.event_type.replace(/_/g, ' ')}`,
            ticker: company.ticker,
            company_name: company.name,
            event_date: form.event_date || new Date().toISOString().split('T')[0],
            event_type: form.event_type,
            source_url: form.url,
          }),
        })
      } else if (hasUrl) {
        res = await fetch('/extract/api/webcasts/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: form.url,
            title: form.title || `${company.ticker} ${form.event_type.replace(/_/g, ' ')}`,
            ticker: company.ticker,
            company_name: company.name,
            event_date: form.event_date || new Date().toISOString().split('T')[0],
            event_type: form.event_type,
          }),
        })
      } else {
        setMessage('Paste a transcript below or provide a webcast URL.')
        setIngesting(false)
        return
      }

      const data = await res.json()
      if (data.status === 'ok') {
        setMessage(`Ingested! ${data.chunks_stored || '?'} chunks, ${data.word_count?.toLocaleString() || wordCount.toLocaleString()} words.`)
        setForm({ url: '', title: '', event_date: '', event_type: 'earnings_call', transcript_text: '' })
        onIngested()
      } else if (data.status === 'already_exists') {
        setMessage(data.message || 'This transcript has already been ingested.')
      } else {
        setMessage(`Error: ${data.error || 'Ingestion failed'}`)
      }
    } catch {
      setMessage('Network error — check if the backend is running.')
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="ev-webcast-ingest-section">
      <div className="ev-ingest-tip">
        Paste an earnings call transcript or conference presentation transcript below.
        Find transcripts on the company's IR page or financial news sites.
      </div>

      <input
        className="ev-forecast-input ev-webcast-form-input"
        placeholder="Title (e.g., Q4 2025 Earnings Call, JPM 2026 Presentation)"
        value={form.title}
        onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
      />

      <div className="ev-webcast-form-row">
        <input
          className="ev-forecast-input"
          type="date"
          value={form.event_date}
          onChange={e => setForm(p => ({ ...p, event_date: e.target.value }))}
          style={{ flex: 1 }}
        />
        <select
          className="ev-param-select"
          value={form.event_type}
          onChange={e => setForm(p => ({ ...p, event_type: e.target.value }))}
          style={{ flex: 1 }}
        >
          <option value="earnings_call">Earnings Call</option>
          <option value="webcast">Webcast</option>
          <option value="investor_day">Investor Day</option>
          <option value="conference">Conference</option>
          <option value="r_and_d_day">R&D Day</option>
        </select>
      </div>

      <input
        className="ev-forecast-input ev-webcast-form-input"
        placeholder="Source URL (optional — link to original webcast or IR page)"
        value={form.url}
        onChange={e => setForm(p => ({ ...p, url: e.target.value }))}
      />

      <div className="ev-ingest-textarea-wrapper">
        <textarea
          className="ev-webcast-textarea"
          placeholder={`Paste the full transcript for ${company.name} here...\n\nTip: Copy from earnings call transcripts, conference presentations, or investor day transcripts. The more text, the better the search results.`}
          value={form.transcript_text}
          onChange={e => setForm(p => ({ ...p, transcript_text: e.target.value }))}
          rows={10}
        />
        {wordCount > 0 && (
          <div className={`ev-ingest-word-count ${wordCount > 500 ? 'good' : 'low'}`}>
            {wordCount.toLocaleString()} words
            {wordCount < 500 && ' — transcripts are typically 3,000+ words'}
          </div>
        )}
      </div>

      <button
        className="ev-forecast-btn"
        onClick={handleIngest}
        disabled={ingesting || (!form.url.trim() && !form.transcript_text.trim())}
        style={{ marginTop: '8px', width: '100%' }}
      >
        {ingesting ? 'Processing & embedding...' : `Ingest transcript${wordCount > 0 ? ` (${wordCount.toLocaleString()} words)` : ''}`}
      </button>

      {message && (
        <div className={`ev-webcast-ingest-result ${message.startsWith('Error') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}
    </div>
  )
}
