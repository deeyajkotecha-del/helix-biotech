import type { TranscriptView } from './types'

interface Props {
  transcript: TranscriptView
  onBack: () => void
}

function formatDate(d: string) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch { return d }
}

export default function TranscriptViewer({ transcript, onBack }: Props) {
  return (
    <div className="ev-company-panel">
      <div className="ev-panel-header">
        <button className="ev-back-btn" onClick={onBack}>
          &larr; Back
        </button>
        <h3>Transcript</h3>
      </div>

      <div className="ev-transcript-meta">
        <div className="ev-trial-nct">{transcript.document?.ticker}</div>
        <h4 className="ev-webcast-card-title">{transcript.document?.title}</h4>
        <div className="ev-webcast-card-meta">
          <span>{formatDate(transcript.document?.date)}</span>
          <span>{transcript.document?.word_count?.toLocaleString()} words</span>
        </div>
      </div>

      <div className="ev-transcript-text">
        {transcript.chunks?.map((chunk, i) => (
          <div key={i} className="ev-transcript-chunk">
            {chunk.section_title && (
              <div className="ev-transcript-section">{chunk.section_title}</div>
            )}
            <p>{chunk.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
