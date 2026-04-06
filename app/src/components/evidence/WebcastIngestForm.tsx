import { useState, useRef, useEffect } from 'react'
import type { Company } from './types'

interface Props {
  company: Company
  onIngested: () => void
}

interface PipelineStatus {
  ready: boolean
  openai_whisper_api: boolean
  local_whisper_available: boolean
  transcription_ready: boolean
  transcription_method: string
  database_available: boolean
  voyage_available: boolean
  ffmpeg_available: boolean
  yt_dlp_available: boolean
  upload_enabled: boolean
  max_upload_mb: number
}

type IngestMode = 'upload' | 'url' | 'paste'

export default function WebcastIngestForm({ company, onIngested }: Props) {
  const [mode, setMode] = useState<IngestMode>('upload')
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)

  const [form, setForm] = useState({
    url: '',
    title: '',
    event_date: '',
    event_type: 'earnings_call',
    transcript_text: '',
  })

  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [ingesting, setIngesting] = useState(false)
  const [progress, setProgress] = useState('')
  const [message, setMessage] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const wordCount = form.transcript_text.trim()
    ? form.transcript_text.trim().split(/\s+/).length
    : 0

  // Check pipeline status on mount
  useEffect(() => {
    fetch('/extract/api/webcasts/status')
      .then(r => r.json())
      .then(data => {
        setStatus(data)
        setStatusLoading(false)
      })
      .catch(() => setStatusLoading(false))
  }, [])

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) validateAndSetFile(file)
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) validateAndSetFile(file)
  }

  function validateAndSetFile(file: File) {
    const allowed = ['.mp3', '.webm', '.wav', '.m4a', '.ogg', '.mp4', '.flac', '.opus']
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!allowed.includes(ext)) {
      setMessage(`Unsupported file type. Accepted: ${allowed.join(', ')}`)
      return
    }
    if (file.size > 100 * 1024 * 1024) {
      setMessage('File too large. Maximum 100 MB.')
      return
    }
    setAudioFile(file)
    setMessage('')
    // Auto-populate title from filename if empty
    if (!form.title) {
      const name = file.name.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ')
      setForm(p => ({ ...p, title: name }))
    }
  }

  async function handleIngest() {
    setIngesting(true)
    setMessage('')
    setProgress('')

    try {
      let res: Response

      if (mode === 'upload' && audioFile) {
        // Audio file upload → backend transcribes via Whisper
        setProgress('Uploading audio...')
        const formData = new FormData()
        formData.append('audio_file', audioFile)
        formData.append('title', form.title || `${company.ticker} ${form.event_type.replace(/_/g, ' ')}`)
        formData.append('ticker', company.ticker)
        formData.append('company_name', company.name)
        formData.append('event_date', form.event_date || new Date().toISOString().split('T')[0])
        formData.append('event_type', form.event_type)
        formData.append('source_url', form.url)

        setProgress('Transcribing audio (this may take 1-3 minutes)...')
        res = await fetch('/extract/api/webcasts/upload-audio', {
          method: 'POST',
          body: formData,
        })
      } else if (mode === 'paste' && form.transcript_text.trim()) {
        // Direct transcript paste
        setProgress('Embedding transcript...')
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
      } else if (mode === 'url' && form.url.trim()) {
        // URL-based download + transcription
        setProgress('Downloading audio from URL...')
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
        setMessage('Please provide an audio file, URL, or transcript.')
        setIngesting(false)
        return
      }

      const data = await res.json()
      if (data.status === 'ok') {
        const method = data.method ? ` (${data.method})` : ''
        setMessage(
          `✓ Ingested! ${data.chunks_stored || '?'} chunks, ` +
          `${data.word_count?.toLocaleString() || wordCount.toLocaleString()} words` +
          `${data.duration ? `, ${Math.round(data.duration / 60)}m audio` : ''}` +
          method
        )
        setForm({ url: '', title: '', event_date: '', event_type: 'earnings_call', transcript_text: '' })
        setAudioFile(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
        onIngested()
      } else if (data.status === 'already_exists') {
        setMessage(data.message || 'This webcast has already been ingested.')
      } else {
        setMessage(`Error: ${data.error || 'Ingestion failed'}`)
      }
    } catch {
      setMessage('Network error — check if the backend is running.')
    } finally {
      setIngesting(false)
      setProgress('')
    }
  }

  const canSubmit = mode === 'upload'
    ? !!audioFile
    : mode === 'url'
    ? !!form.url.trim()
    : !!form.transcript_text.trim()

  return (
    <div className="ev-webcast-ingest-section">
      {/* Pipeline status indicator */}
      {!statusLoading && status && (
        <div className={`ev-pipeline-status ${status.transcription_ready ? 'ready' : 'not-ready'}`}>
          <span className="ev-pipeline-dot" />
          {status.transcription_ready
            ? `Transcription: ${status.transcription_method}`
            : 'Transcription not available — set OPENAI_API_KEY'}
        </div>
      )}

      {/* Mode tabs */}
      <div className="ev-ingest-tabs">
        <button
          className={`ev-ingest-tab ${mode === 'upload' ? 'active' : ''}`}
          onClick={() => setMode('upload')}
        >
          Upload Audio
        </button>
        <button
          className={`ev-ingest-tab ${mode === 'url' ? 'active' : ''}`}
          onClick={() => setMode('url')}
        >
          From URL
        </button>
        <button
          className={`ev-ingest-tab ${mode === 'paste' ? 'active' : ''}`}
          onClick={() => setMode('paste')}
        >
          Paste Transcript
        </button>
      </div>

      {/* Common fields: title, date, type */}
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

      {/* Mode-specific content */}
      {mode === 'upload' && (
        <div
          className={`ev-audio-dropzone ${audioFile ? 'has-file' : ''}`}
          onDragOver={e => e.preventDefault()}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp3,.webm,.wav,.m4a,.ogg,.mp4,.flac,.opus"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          {audioFile ? (
            <div className="ev-audio-file-info">
              <span className="ev-audio-file-icon">🎵</span>
              <div>
                <div className="ev-audio-file-name">{audioFile.name}</div>
                <div className="ev-audio-file-size">
                  {(audioFile.size / 1024 / 1024).toFixed(1)} MB
                </div>
              </div>
              <button
                className="ev-audio-file-remove"
                onClick={e => {
                  e.stopPropagation()
                  setAudioFile(null)
                  if (fileInputRef.current) fileInputRef.current.value = ''
                }}
              >
                ×
              </button>
            </div>
          ) : (
            <div className="ev-audio-dropzone-prompt">
              <span style={{ fontSize: '28px' }}>🎤</span>
              <div>
                Drop audio file here or <strong>click to browse</strong>
              </div>
              <div className="ev-audio-dropzone-hint">
                .mp3, .webm, .wav, .m4a — max 100 MB
              </div>
            </div>
          )}
        </div>
      )}

      {mode === 'url' && (
        <>
          <input
            className="ev-forecast-input ev-webcast-form-input"
            placeholder="Webcast URL (YouTube, direct audio link, or IR page stream)"
            value={form.url}
            onChange={e => setForm(p => ({ ...p, url: e.target.value }))}
          />
          <div className="ev-ingest-tip">
            Works for YouTube, direct audio/video URLs, and some HLS/DASH streams.
            For gated webcasts (Notified, Q4), use the Audio Upload or browser capture instead.
          </div>
        </>
      )}

      {mode === 'paste' && (
        <>
          <div className="ev-ingest-textarea-wrapper">
            <textarea
              className="ev-webcast-textarea"
              placeholder={`Paste the full transcript for ${company.name} here...\n\nTip: Copy from earnings call transcripts, conference presentations, or investor day transcripts.`}
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
          <input
            className="ev-forecast-input ev-webcast-form-input"
            placeholder="Source URL (optional — link to original webcast or IR page)"
            value={form.url}
            onChange={e => setForm(p => ({ ...p, url: e.target.value }))}
          />
        </>
      )}

      {/* Submit button */}
      <button
        className="ev-forecast-btn"
        onClick={handleIngest}
        disabled={ingesting || !canSubmit}
        style={{ marginTop: '8px', width: '100%' }}
      >
        {ingesting
          ? progress || 'Processing...'
          : mode === 'upload'
          ? `Transcribe & ingest${audioFile ? ` (${(audioFile.size / 1024 / 1024).toFixed(1)} MB)` : ''}`
          : mode === 'url'
          ? 'Download, transcribe & ingest'
          : `Ingest transcript${wordCount > 0 ? ` (${wordCount.toLocaleString()} words)` : ''}`
        }
      </button>

      {/* Result message */}
      {message && (
        <div className={`ev-webcast-ingest-result ${message.startsWith('Error') || message.startsWith('⚠') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}
    </div>
  )
}
