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
    event_type: 'webcast',
    transcript_text: '',
  })
  const [ingesting, setIngesting] = useState(false)
  const [message, setMessage] = useState('')

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
            title: form.title,
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
            title: form.title,
            ticker: company.ticker,
            company_name: company.name,
            event_date: form.event_date || new Date().toISOString().split('T')[0],
            event_type: form.event_type,
          }),
        })
      } else {
        setMessage('Provide a URL or paste a transcript.')
        setIngesting(false)
        return
      }

      const data = await res.json()
      if (data.status === 'ok') {
        setMessage(`Done! ${data.chunks_stored} chunks, ${data.word_count} words.`)
        setForm({ url: '', title: '', event_date: '', event_type: 'webcast', transcript_text: '' })
        onIngested()
      } else if (data.status === 'already_exists') {
        setMessage(data.message || 'Already ingested.')
      } else {
        setMessage(`Error: ${data.error || 'Failed'}`)
      }
    } catch {
      setMessage('Network error.')
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="ev-webcast-ingest-section">
      <input
        className="ev-forecast-input ev-webcast-form-input"
        placeholder="Title (e.g., Q4 2025 Earnings Call)"
        value={form.title}
        onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
      />
      <div className="ev-webcast-form-row">
        <input
          className="ev-forecast-input"
          type="date"
          value={form.event_date}
          onChange={e => setForm(p => ({ ...p, event_date: e.target.value }))}
          style={{ width: '50%' }}
        />
        <select
          className="ev-param-select"
          value={form.event_type}
          onChange={e => setForm(p => ({ ...p, event_type: e.target.value }))}
          style={{ width: '48%' }}
        >
          <option value="webcast">Webcast</option>
          <option value="earnings_call">Earnings Call</option>
          <option value="investor_day">Investor Day</option>
          <option value="conference">Conference</option>
          <option value="r_and_d_day">R&D Day</option>
        </select>
      </div>

      <input
        className="ev-forecast-input ev-webcast-form-input"
        placeholder="Webcast URL (optional)"
        value={form.url}
        onChange={e => setForm(p => ({ ...p, url: e.target.value }))}
      />

      <textarea
        className="ev-webcast-textarea"
        placeholder="Or paste transcript text here..."
        value={form.transcript_text}
        onChange={e => setForm(p => ({ ...p, transcript_text: e.target.value }))}
        rows={5}
      />

      <button
        className="ev-forecast-btn"
        onClick={handleIngest}
        disabled={ingesting || (!form.url.trim() && !form.transcript_text.trim())}
        style={{ marginTop: '6px' }}
      >
        {ingesting ? 'Processing...' : 'Ingest'}
      </button>

      {message && (
        <div className={`ev-webcast-ingest-result ${message.startsWith('Error') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}
    </div>
  )
}
