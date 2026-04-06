"""
Webcast Transcription & RAG Pipeline
=====================================
Captures audio from biotech IR webcasts (Notified / edge.media-server.com),
transcribes via OpenAI Whisper API (primary) or local Whisper (fallback),
and stores in the existing RAG database (Neon pgvector) for semantic +
keyword search across all webcasts.

Audio capture methods:
  1. Audio file upload — user uploads .mp3/.webm/.wav/.m4a recording
  2. MediaRecorder bookmarklet — JS captures audio from browser tab,
     auto-uploads to /api/webcasts/upload-audio
  3. yt-dlp — downloads HLS/DASH streams when available (public only)

Transcription (priority order):
  1. OpenAI Whisper API — fast, reliable, no local deps ($0.006/min)
  2. Local openai-whisper — free, requires ffmpeg + ~1.5GB RAM

Storage:
  - Reuses existing documents + chunks tables (doc_type="webcast")
  - Voyage-3 embeddings (1024-dim), HNSW index, tsvector for keyword search
"""

import os
import re
import json
import subprocess
import tempfile
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("NEON_DATABASE_URL", "")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EMBED_MODEL = "voyage-3"        # 1024 dims, same as rest of RAG
EMBED_BATCH_SIZE = 16
CHUNK_WORDS = 600               # Smaller for spoken content (more granular)
CHUNK_OVERLAP = 100

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
WHISPER_LANGUAGE = "en"

# Where audio files are temporarily stored during processing
AUDIO_TEMP_DIR = os.getenv("AUDIO_TEMP_DIR", "/tmp/helix-webcasts")

# Max upload size: 100 MB (OpenAI Whisper API limit is 25 MB per request,
# but we split larger files with ffmpeg before sending)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

# ---------------------------------------------------------------------------
# Lazy-init globals
# ---------------------------------------------------------------------------

_db_conn = None
_vo_client = None
_whisper_model = None
_whisper_available = False
_openai_client = None

try:
    import whisper as _whisper_module
    _whisper_available = True
except ImportError:
    _whisper_module = None
    print("  [webcast] openai-whisper not installed — will use API transcription")

# Check for OpenAI Whisper API availability
_openai_whisper_available = False
try:
    import openai as _openai_module
    if OPENAI_API_KEY:
        _openai_whisper_available = True
        print("  [webcast] OpenAI Whisper API available (primary transcription)")
    else:
        print("  [webcast] OPENAI_API_KEY not set — OpenAI Whisper API disabled")
except ImportError:
    _openai_module = None
    print("  [webcast] openai package not installed — API transcription disabled")


def _get_db():
    """Get or create a database connection with health check."""
    global _db_conn
    try:
        if _db_conn is not None and not _db_conn.closed:
            _db_conn.cursor().execute("SELECT 1")
            return _db_conn
    except Exception:
        try:
            _db_conn.close()
        except Exception:
            pass
        _db_conn = None

    if not DATABASE_URL:
        return None
    try:
        _db_conn = psycopg2.connect(DATABASE_URL)
        _db_conn.autocommit = False
        return _db_conn
    except Exception as e:
        print(f"  [webcast] DB connection failed: {e}")
        _db_conn = None
        return None


def _get_voyage():
    """Get or create a Voyage AI client."""
    global _vo_client
    if _vo_client is None:
        if not VOYAGE_API_KEY:
            return None
        try:
            import voyageai
            _vo_client = voyageai.Client(api_key=VOYAGE_API_KEY)
        except ImportError:
            return None
    return _vo_client


def _get_whisper():
    """Load Whisper model (lazy, ~1-2 GB for base)."""
    global _whisper_model
    if _whisper_model is None and _whisper_available:
        print(f"  [webcast] Loading Whisper model '{WHISPER_MODEL}'...")
        _whisper_model = _whisper_module.load_model(WHISPER_MODEL)
        print(f"  [webcast] Whisper model loaded.")
    return _whisper_model


def _get_openai():
    """Get or create an OpenAI client for Whisper API."""
    global _openai_client
    if _openai_client is None and _openai_whisper_available:
        _openai_client = _openai_module.OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# ===========================================================================
# 1. AUDIO CAPTURE
# ===========================================================================

def capture_audio_yt_dlp(url: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Try to download audio from a webcast URL using yt-dlp.
    Works when the player exposes an HLS/DASH manifest.
    Returns the path to the downloaded audio file, or None on failure.
    """
    os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
    if not output_path:
        slug = hashlib.md5(url.encode()).hexdigest()[:12]
        output_path = os.path.join(AUDIO_TEMP_DIR, f"webcast_{slug}.mp3")

    try:
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--no-playlist",
            "--output", output_path.replace(".mp3", ".%(ext)s"),
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0 and os.path.exists(output_path):
            print(f"  [webcast] yt-dlp captured audio: {output_path}")
            return output_path
        else:
            # yt-dlp might save with different extension
            base = output_path.rsplit(".", 1)[0]
            for ext in ["mp3", "m4a", "wav", "opus", "webm"]:
                candidate = f"{base}.{ext}"
                if os.path.exists(candidate):
                    return candidate
            print(f"  [webcast] yt-dlp failed: {result.stderr[:500]}")
            return None
    except FileNotFoundError:
        print("  [webcast] yt-dlp not installed")
        return None
    except subprocess.TimeoutExpired:
        print("  [webcast] yt-dlp timed out")
        return None
    except Exception as e:
        print(f"  [webcast] yt-dlp error: {e}")
        return None


def convert_to_wav(input_path: str) -> Optional[str]:
    """Convert any audio/video file to 16kHz mono WAV for Whisper."""
    output_path = input_path.rsplit(".", 1)[0] + "_16k.wav"
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        print(f"  [webcast] ffmpeg conversion failed: {result.stderr[:500]}")
        return None
    except FileNotFoundError:
        print("  [webcast] ffmpeg not installed")
        return None
    except Exception as e:
        print(f"  [webcast] ffmpeg error: {e}")
        return None


# JavaScript to inject into the browser for MediaRecorder capture.
# This is returned to the frontend/Chrome extension to execute.
MEDIA_RECORDER_JS = """
(async () => {
    const BACKEND_URL = '__BACKEND_URL__';

    // Find the video/audio element
    const media = document.querySelector('video[src^="blob:"]')
        || document.querySelector('video')
        || document.querySelector('audio[src^="blob:"]')
        || document.querySelector('audio');
    if (!media) return { error: 'No media element found on this page' };

    // Capture the audio stream
    const stream = media.captureStream ? media.captureStream()
        : media.mozCaptureStream ? media.mozCaptureStream()
        : null;
    if (!stream) return { error: 'captureStream not supported in this browser' };

    const audioTracks = stream.getAudioTracks();
    if (audioTracks.length === 0) return { error: 'No audio tracks found' };

    const audioStream = new MediaStream(audioTracks);
    const recorder = new MediaRecorder(audioStream, {
        mimeType: 'audio/webm;codecs=opus'
    });
    const chunks = [];

    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

    // Create a small floating status badge
    const badge = document.createElement('div');
    badge.id = '__helix_badge';
    badge.innerHTML = '🔴 Recording... <button id="__helix_stop" style="margin-left:8px;cursor:pointer;background:#dc2626;color:white;border:none;padding:4px 12px;border-radius:4px;font-size:13px;">Stop & Upload</button>';
    badge.style.cssText = 'position:fixed;top:10px;right:10px;z-index:999999;background:#1e1e2e;color:#e0e0e0;padding:8px 16px;border-radius:8px;font-family:system-ui;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.3);display:flex;align-items:center;';
    document.body.appendChild(badge);

    const startTime = Date.now();

    // Update badge with elapsed time
    const timer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        badge.querySelector('#__helix_stop').previousSibling.textContent =
            `🔴 Recording ${mins}:${secs.toString().padStart(2, '0')}... `;
    }, 1000);

    recorder.onstop = async () => {
        clearInterval(timer);
        badge.innerHTML = '⏳ Uploading to SatyaBio...';

        const blob = new Blob(chunks, { type: 'audio/webm' });
        const duration = (Date.now() - startTime) / 1000;

        // Also save locally as backup
        const backupUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = backupUrl; a.download = 'webcast_backup.webm'; a.click();

        // Upload to backend
        if (BACKEND_URL) {
            try {
                const formData = new FormData();
                formData.append('audio_file', blob, 'webcast_recording.webm');
                formData.append('title', document.title || 'Webcast Recording');
                formData.append('source_url', window.location.href);
                formData.append('duration_seconds', String(duration));

                const resp = await fetch(BACKEND_URL + '/extract/api/webcasts/upload-audio', {
                    method: 'POST',
                    body: formData,
                });
                const data = await resp.json();
                badge.innerHTML = data.status === 'ok'
                    ? `✅ Uploaded! ${data.word_count?.toLocaleString() || '?'} words transcribed.`
                    : `⚠️ ${data.error || 'Upload failed'}. Backup saved locally.`;
            } catch (err) {
                badge.innerHTML = `⚠️ Upload failed: ${err.message}. Backup saved locally.`;
            }
        } else {
            badge.innerHTML = '✅ Recording saved (no backend URL configured).';
        }

        setTimeout(() => badge.remove(), 15000);
    };

    recorder.start(1000);
    window.__helixRecorder = recorder;

    document.getElementById('__helix_stop').onclick = () => recorder.stop();

    return { recording: true, message: 'Recording started. Click the Stop button or call window.__helixRecorder.stop()' };
})();
"""


def get_media_recorder_js(backend_url: str = "") -> str:
    """Return the JS snippet for MediaRecorder-based audio capture."""
    return MEDIA_RECORDER_JS.replace("__BACKEND_URL__", backend_url)


# ===========================================================================
# 2. TRANSCRIPTION — OpenAI Whisper API (primary) or local Whisper (fallback)
# ===========================================================================

def transcribe_audio(audio_path: str) -> Optional[dict]:
    """
    Transcribe an audio file. Tries OpenAI Whisper API first (fast, reliable),
    falls back to local Whisper if API unavailable.

    Returns: {
        "text": str,           # full transcript
        "segments": [...],     # timestamped segments
        "language": str,
        "duration": float,     # seconds
        "method": str,         # "openai_api" or "local_whisper"
    }
    """
    # Try OpenAI Whisper API first (fast, no local deps)
    if _openai_whisper_available:
        result = _transcribe_openai_api(audio_path)
        if result and "error" not in result:
            return result
        print(f"  [webcast] OpenAI API transcription failed, trying local...")

    # Fallback: local Whisper
    if _whisper_available:
        return _transcribe_local_whisper(audio_path)

    return {"error": "No transcription engine available. Set OPENAI_API_KEY or install openai-whisper."}


def _transcribe_openai_api(audio_path: str) -> Optional[dict]:
    """Transcribe using OpenAI Whisper API ($0.006/min)."""
    client = _get_openai()
    if client is None:
        return {"error": "OpenAI client not available"}

    file_size = os.path.getsize(audio_path)
    print(f"  [webcast] Transcribing via OpenAI Whisper API ({file_size / 1024 / 1024:.1f} MB)...")

    try:
        # OpenAI API limit is 25 MB. If larger, compress with ffmpeg first.
        upload_path = audio_path
        if file_size > 24 * 1024 * 1024:
            print(f"  [webcast] File too large for API ({file_size / 1024 / 1024:.1f} MB), compressing...")
            compressed = _compress_for_api(audio_path)
            if compressed:
                upload_path = compressed
            else:
                return {"error": "Could not compress audio to under 25 MB"}

        with open(upload_path, "rb") as f:
            # Use verbose_json to get timestamps
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        # Parse response
        segments = []
        duration = 0
        if hasattr(response, "segments") and response.segments:
            for seg in response.segments:
                segments.append({
                    "start": seg.get("start", seg.start) if hasattr(seg, "start") else seg.get("start", 0),
                    "end": seg.get("end", seg.end) if hasattr(seg, "end") else seg.get("end", 0),
                    "text": (seg.get("text", seg.text) if hasattr(seg, "text") else seg.get("text", "")).strip(),
                })
            if segments:
                duration = segments[-1]["end"]

        text = response.text if hasattr(response, "text") else str(response)

        print(f"  [webcast] OpenAI API transcription complete: {len(text)} chars, {duration:.0f}s")

        # Clean up compressed file
        if upload_path != audio_path and os.path.exists(upload_path):
            os.remove(upload_path)

        return {
            "text": text.strip(),
            "segments": segments,
            "language": "en",
            "duration": duration,
            "method": "openai_api",
        }

    except Exception as e:
        print(f"  [webcast] OpenAI Whisper API error: {e}")
        return {"error": str(e)}


def _compress_for_api(audio_path: str) -> Optional[str]:
    """Compress audio to fit within OpenAI's 25 MB limit."""
    output = audio_path.rsplit(".", 1)[0] + "_compressed.mp3"
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ar", "16000",     # 16kHz
            "-ac", "1",         # mono
            "-b:a", "48k",      # low bitrate for speech (very efficient)
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output):
            compressed_size = os.path.getsize(output)
            if compressed_size < 24 * 1024 * 1024:
                print(f"  [webcast] Compressed to {compressed_size / 1024 / 1024:.1f} MB")
                return output
            else:
                os.remove(output)
                return None
        return None
    except Exception as e:
        print(f"  [webcast] Compression failed: {e}")
        return None


def _transcribe_local_whisper(audio_path: str) -> Optional[dict]:
    """Transcribe using local openai-whisper model."""
    model = _get_whisper()
    if model is None:
        return {"error": "Whisper not available. Install: pip install openai-whisper"}

    # Convert to 16kHz WAV if needed
    ext = audio_path.rsplit(".", 1)[-1].lower()
    if ext not in ("wav",):
        wav_path = convert_to_wav(audio_path)
        if wav_path is None:
            return {"error": f"Could not convert {ext} to WAV. Is ffmpeg installed?"}
    else:
        wav_path = audio_path

    print(f"  [webcast] Transcribing {wav_path} with local Whisper ({WHISPER_MODEL})...")
    try:
        result = model.transcribe(
            wav_path,
            language=WHISPER_LANGUAGE,
            verbose=False,
        )

        transcript = {
            "text": result.get("text", "").strip(),
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }
                for seg in result.get("segments", [])
            ],
            "language": result.get("language", WHISPER_LANGUAGE),
            "duration": result["segments"][-1]["end"] if result.get("segments") else 0,
            "method": "local_whisper",
        }

        print(f"  [webcast] Transcription complete: {len(transcript['text'])} chars, "
              f"{transcript['duration']:.0f}s duration")
        return transcript

    except Exception as e:
        print(f"  [webcast] Whisper error: {e}")
        return {"error": str(e)}


# ===========================================================================
# 3. CHUNKING — for spoken content
# ===========================================================================

def chunk_transcript(transcript_text: str, segments: list = None) -> list[dict]:
    """
    Chunk a transcript into ~CHUNK_WORDS-word pieces with overlap.
    Uses segment timestamps when available for better boundaries.

    Returns list of:
        {"content": str, "start_time": float, "end_time": float,
         "chunk_index": int, "word_count": int}
    """
    if not transcript_text or not transcript_text.strip():
        return []

    chunks = []

    if segments and len(segments) > 5:
        # Use segment boundaries for natural chunking
        current_text = ""
        current_start = segments[0]["start"] if segments else 0
        current_words = 0

        for seg in segments:
            seg_text = seg["text"].strip()
            seg_words = len(seg_text.split())

            if current_words + seg_words > CHUNK_WORDS and current_words > 0:
                # Save current chunk
                chunks.append({
                    "content": current_text.strip(),
                    "start_time": current_start,
                    "end_time": seg["start"],
                    "chunk_index": len(chunks),
                    "word_count": current_words,
                })
                # Start new chunk with overlap: keep last few segments
                overlap_text = " ".join(current_text.strip().split()[-CHUNK_OVERLAP:])
                current_text = overlap_text + " " + seg_text
                current_start = seg["start"]
                current_words = len(current_text.split())
            else:
                current_text += " " + seg_text
                current_words += seg_words

        # Final chunk
        if current_text.strip():
            chunks.append({
                "content": current_text.strip(),
                "start_time": current_start,
                "end_time": segments[-1]["end"] if segments else 0,
                "chunk_index": len(chunks),
                "word_count": len(current_text.split()),
            })
    else:
        # Fall back to word-count chunking
        words = transcript_text.split()
        start = 0
        while start < len(words):
            end = min(start + CHUNK_WORDS, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append({
                "content": chunk_text,
                "start_time": 0,
                "end_time": 0,
                "chunk_index": len(chunks),
                "word_count": end - start,
            })
            start += CHUNK_WORDS - CHUNK_OVERLAP

    return chunks


# ===========================================================================
# 4. RAG INGESTION — store in existing documents + chunks tables
# ===========================================================================

def ingest_webcast(
    transcript_text: str,
    segments: list = None,
    title: str = "",
    ticker: str = "",
    company_name: str = "",
    event_date: str = "",
    event_type: str = "webcast",
    source_url: str = "",
    duration_seconds: float = 0,
) -> dict:
    """
    Store a webcast transcript in the RAG database.
    Uses the existing documents + chunks tables with doc_type='webcast'.

    Returns: {"document_id": int, "chunks_stored": int, "status": str}
    """
    conn = _get_db()
    if conn is None:
        return {"error": "Database not available", "status": "error"}

    vo = _get_voyage()
    if vo is None:
        return {"error": "Voyage AI client not available", "status": "error"}

    # Build a filename for dedup
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower())[:80] if title else "untitled"
    filename = f"webcast_{ticker}_{slug}_{event_date}.txt"

    try:
        cur = conn.cursor()

        # Check if already ingested
        cur.execute(
            "SELECT id FROM documents WHERE ticker = %s AND filename = %s",
            (ticker.upper(), filename)
        )
        existing = cur.fetchone()
        if existing:
            return {
                "document_id": existing[0],
                "chunks_stored": 0,
                "status": "already_exists",
                "message": f"Webcast already ingested as document {existing[0]}"
            }

        word_count = len(transcript_text.split())

        # Insert document record
        cur.execute("""
            INSERT INTO documents (ticker, company_name, filename, file_path,
                                   doc_type, title, date, word_count, page_count,
                                   file_size_bytes, embedded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            ticker.upper(),
            company_name,
            filename,
            source_url or "",
            "webcast",
            title,
            event_date,
            word_count,
            0,  # page_count not applicable
            len(transcript_text.encode("utf-8")),
        ))
        doc_id = cur.fetchone()[0]

        # Chunk the transcript
        chunks = chunk_transcript(transcript_text, segments)
        if not chunks:
            conn.commit()
            return {"document_id": doc_id, "chunks_stored": 0, "status": "ok_no_chunks"}

        # Embed chunks in batches
        all_embeddings = []
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i:i + EMBED_BATCH_SIZE]
            texts = [c["content"] for c in batch]
            try:
                resp = vo.embed(texts, model=EMBED_MODEL, input_type="document")
                all_embeddings.extend(resp.embeddings)
            except Exception as e:
                print(f"  [webcast] Embedding batch {i} failed: {e}")
                # Fill with None so we can still store text
                all_embeddings.extend([None] * len(batch))

        # Insert chunks
        chunks_stored = 0
        for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
            section_title = _infer_section(chunk["content"], chunk.get("start_time", 0))

            emb_str = str(embedding) if embedding else None

            cur.execute("""
                INSERT INTO chunks (document_id, chunk_index, page_number,
                                    section_title, content, token_count,
                                    embedding, content_tsv, created_at)
                VALUES (%s, %s, %s, %s, %s, %s,
                        %s::vector, to_tsvector('english', %s), NOW())
            """, (
                doc_id,
                idx,
                0,  # page_number — not applicable for webcasts
                section_title,
                chunk["content"],
                chunk["word_count"],
                emb_str,
                chunk["content"],
            ))
            chunks_stored += 1

        conn.commit()

        # Also store metadata as JSON in a webcast_metadata record if table exists
        _store_webcast_metadata(cur, conn, doc_id, {
            "source_url": source_url,
            "event_type": event_type,
            "duration_seconds": duration_seconds,
            "segment_count": len(segments) if segments else 0,
            "chunk_count": chunks_stored,
        })

        print(f"  [webcast] Ingested: doc_id={doc_id}, {chunks_stored} chunks, "
              f"{word_count} words")
        return {
            "document_id": doc_id,
            "chunks_stored": chunks_stored,
            "word_count": word_count,
            "status": "ok",
        }

    except Exception as e:
        conn.rollback()
        print(f"  [webcast] Ingest error: {e}")
        return {"error": str(e), "status": "error"}


def _infer_section(text: str, start_time: float = 0) -> str:
    """Infer a section label from spoken content."""
    text_lower = text[:500].lower()

    section_keywords = [
        ("pipeline", "Pipeline Overview"),
        ("enrollment", "Enrollment Update"),
        ("efficacy", "Efficacy Data"),
        ("safety", "Safety & Tolerability"),
        ("dose", "Dosing"),
        ("pharmacokinetic", "PK/PD"),
        ("revenue", "Financial Results"),
        ("guidance", "Guidance"),
        ("fda", "Regulatory"),
        ("approval", "Regulatory"),
        ("phase 3", "Phase 3 Update"),
        ("phase 2", "Phase 2 Update"),
        ("phase 1", "Phase 1 Update"),
        ("investor", "Investor Update"),
        ("question", "Q&A"),
        ("forward-looking", "Forward-Looking Statements"),
    ]

    for keyword, label in section_keywords:
        if keyword in text_lower:
            return label

    # Time-based fallback
    if start_time < 120:
        return "Introduction"
    return "Presentation"


def _store_webcast_metadata(cur, conn, doc_id: int, metadata: dict):
    """Store extra webcast metadata. Creates table if needed."""
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webcast_metadata (
                id SERIAL PRIMARY KEY,
                document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                source_url TEXT,
                event_type VARCHAR(100),
                duration_seconds FLOAT,
                segment_count INTEGER,
                chunk_count INTEGER,
                metadata_json JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(document_id)
            )
        """)
        cur.execute("""
            INSERT INTO webcast_metadata (document_id, source_url, event_type,
                                          duration_seconds, segment_count, chunk_count,
                                          metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id) DO NOTHING
        """, (
            doc_id,
            metadata.get("source_url", ""),
            metadata.get("event_type", "webcast"),
            metadata.get("duration_seconds", 0),
            metadata.get("segment_count", 0),
            metadata.get("chunk_count", 0),
            json.dumps(metadata),
        ))
        conn.commit()
    except Exception as e:
        print(f"  [webcast] Metadata storage failed (non-fatal): {e}")
        try:
            conn.rollback()
        except Exception:
            pass


# ===========================================================================
# 5. SEARCH — across all webcast transcripts
# ===========================================================================

def search_webcasts(
    query: str,
    ticker: str = None,
    top_k: int = 10,
) -> list[dict]:
    """
    Hybrid search (vector + keyword) over webcast transcripts.
    Returns ranked chunks with document metadata.
    """
    if not query or not query.strip():
        return []

    conn = _get_db()
    vo = _get_voyage()
    if conn is None or vo is None:
        return []

    try:
        # Embed the query
        resp = vo.embed([query], model=EMBED_MODEL, input_type="query")
        query_embedding = resp.embeddings[0]

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Vector search — webcasts only
        # Param order must match SQL placeholder order:
        #   SELECT: %s::vector (similarity), WHERE: ticker %s, ORDER BY: %s::vector, LIMIT: %s
        ticker_clause = "AND d.ticker = %s" if ticker else ""
        emb_str = str(query_embedding)
        params_vec = [emb_str]
        if ticker:
            params_vec.append(ticker.upper())
        params_vec.append(emb_str)
        params_vec.append(top_k * 3)

        cur.execute(f"""
            SELECT c.id, c.content, c.chunk_index, c.section_title, c.token_count,
                   d.id AS document_id, d.ticker, d.company_name, d.title,
                   d.date, d.doc_type,
                   1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.doc_type = 'webcast' {ticker_clause}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, params_vec)
        vector_results = cur.fetchall()

        # Keyword search
        # Param order: WHERE tsv match %s, WHERE tsv @@ %s, ticker %s, LIMIT %s
        params_kw = [query]
        if ticker:
            params_kw.append(ticker.upper())
        params_kw.append(query)
        params_kw.append(top_k * 2)

        cur.execute(f"""
            SELECT c.id, c.content, c.chunk_index, c.section_title, c.token_count,
                   d.id AS document_id, d.ticker, d.company_name, d.title,
                   d.date, d.doc_type,
                   ts_rank_cd(c.content_tsv, websearch_to_tsquery('english', %s)) AS rank
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.doc_type = 'webcast'
              {ticker_clause}
              AND c.content_tsv @@ websearch_to_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """, params_kw)
        keyword_results = cur.fetchall()

        # Merge results by chunk ID
        merged = {}
        for r in vector_results:
            merged[r["id"]] = {
                **dict(r),
                "vector_score": float(r["similarity"]),
                "keyword_score": 0,
            }
        for r in keyword_results:
            cid = r["id"]
            if cid in merged:
                merged[cid]["keyword_score"] = float(r["rank"])
            else:
                merged[cid] = {
                    **dict(r),
                    "vector_score": 0,
                    "keyword_score": float(r["rank"]),
                }

        # Score and rank
        VECTOR_W = 0.6
        KEYWORD_W = 0.4
        scored = []
        for item in merged.values():
            item["hybrid_score"] = (
                VECTOR_W * item["vector_score"] +
                KEYWORD_W * min(item["keyword_score"] / 10, 1.0)
            )
            scored.append(item)

        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Rerank with Voyage if enough candidates
        if len(scored) > 3:
            try:
                rerank_resp = vo.rerank(
                    query=query,
                    documents=[s["content"] for s in scored[:30]],
                    model="rerank-2",
                    top_k=min(top_k, len(scored)),
                )
                reranked = []
                for rr in rerank_resp.results:
                    item = scored[rr.index]
                    item["rerank_score"] = rr.relevance_score
                    reranked.append(item)
                return reranked
            except Exception as e:
                print(f"  [webcast] Rerank failed, using hybrid scores: {e}")

        return scored[:top_k]

    except Exception as e:
        print(f"  [webcast] Search error: {e}")
        return []


# ===========================================================================
# 6. LIBRARY — list and browse all webcasts
# ===========================================================================

def list_webcasts(
    ticker: str = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    List all ingested webcasts with metadata.
    Returns: {"webcasts": [...], "total": int}
    """
    conn = _get_db()
    if conn is None:
        return {"webcasts": [], "total": 0, "error": "Database not available"}

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        where = "WHERE d.doc_type = 'webcast'"
        params = []
        if ticker:
            where += " AND d.ticker = %s"
            params.append(ticker.upper())

        # Count
        cur.execute(f"SELECT COUNT(*) FROM documents d {where}", params)
        total = cur.fetchone()["count"]

        # Fetch with metadata
        params_fetch = params + [limit, offset]
        cur.execute(f"""
            SELECT d.id, d.ticker, d.company_name, d.title, d.date,
                   d.word_count, d.embedded_at,
                   wm.source_url, wm.event_type, wm.duration_seconds
            FROM documents d
            LEFT JOIN webcast_metadata wm ON wm.document_id = d.id
            {where}
            ORDER BY d.embedded_at DESC
            LIMIT %s OFFSET %s
        """, params_fetch)
        webcasts = [dict(row) for row in cur.fetchall()]

        # Format duration nicely
        for w in webcasts:
            dur = w.get("duration_seconds") or 0
            if dur > 0:
                mins = int(dur // 60)
                secs = int(dur % 60)
                w["duration_display"] = f"{mins}m {secs}s"
            else:
                w["duration_display"] = ""

        return {"webcasts": webcasts, "total": total}

    except Exception as e:
        print(f"  [webcast] List error: {e}")
        return {"webcasts": [], "total": 0, "error": str(e)}


def get_webcast_transcript(document_id: int) -> dict:
    """
    Retrieve the full transcript for a webcast, reconstructed from chunks.
    """
    conn = _get_db()
    if conn is None:
        return {"error": "Database not available"}

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get document info
        cur.execute("""
            SELECT d.*, wm.source_url, wm.event_type, wm.duration_seconds
            FROM documents d
            LEFT JOIN webcast_metadata wm ON wm.document_id = d.id
            WHERE d.id = %s AND d.doc_type = 'webcast'
        """, (document_id,))
        doc = cur.fetchone()
        if not doc:
            return {"error": "Webcast not found"}

        # Get chunks in order
        cur.execute("""
            SELECT chunk_index, section_title, content, token_count
            FROM chunks
            WHERE document_id = %s
            ORDER BY chunk_index
        """, (document_id,))
        chunks = [dict(row) for row in cur.fetchall()]

        # Reconstruct full text (skip overlap by using unique content)
        full_text = " ".join(c["content"] for c in chunks)

        return {
            "document": dict(doc),
            "chunks": chunks,
            "full_transcript": full_text,
        }

    except Exception as e:
        return {"error": str(e)}


# ===========================================================================
# 7. END-TO-END PIPELINE
# ===========================================================================

async def process_webcast(
    audio_path: str = None,
    url: str = None,
    title: str = "",
    ticker: str = "",
    company_name: str = "",
    event_date: str = "",
    event_type: str = "webcast",
) -> dict:
    """
    Full pipeline: capture audio → transcribe → chunk → embed → store.

    Provide either:
      - audio_path: path to a local audio/video file
      - url: webcast URL to try downloading via yt-dlp

    Returns status dict with document_id and chunk count.
    """
    steps = []

    # Step 1: Get audio file
    if audio_path and os.path.exists(audio_path):
        steps.append({"step": "audio_source", "method": "file_upload", "path": audio_path})
    elif url:
        steps.append({"step": "audio_capture", "method": "yt-dlp", "url": url})
        audio_path = capture_audio_yt_dlp(url)
        if audio_path is None:
            return {
                "status": "error",
                "error": "Could not capture audio. Try uploading the file directly.",
                "steps": steps,
                "capture_js": get_media_recorder_js(),
                "message": "yt-dlp failed. Use the MediaRecorder JS snippet to capture "
                           "audio from the browser, then upload the recording.",
            }
        steps.append({"step": "audio_captured", "path": audio_path})
    else:
        return {"status": "error", "error": "Provide audio_path or url"}

    # Step 2: Transcribe
    steps.append({"step": "transcribing", "model": WHISPER_MODEL})
    transcript = transcribe_audio(audio_path)
    if not transcript or "error" in transcript:
        return {
            "status": "error",
            "error": transcript.get("error", "Transcription failed"),
            "steps": steps,
        }
    steps.append({
        "step": "transcribed",
        "chars": len(transcript["text"]),
        "duration": transcript.get("duration", 0),
    })

    # Step 3: Ingest into RAG
    steps.append({"step": "ingesting"})
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    result = ingest_webcast(
        transcript_text=transcript["text"],
        segments=transcript.get("segments"),
        title=title,
        ticker=ticker,
        company_name=company_name,
        event_date=event_date,
        event_type=event_type,
        source_url=url or "",
        duration_seconds=transcript.get("duration", 0),
    )

    steps.append({"step": "ingested", **result})

    return {
        "status": result.get("status", "error"),
        "document_id": result.get("document_id"),
        "chunks_stored": result.get("chunks_stored", 0),
        "word_count": result.get("word_count", 0),
        "duration": transcript.get("duration", 0),
        "transcript_preview": transcript["text"][:500],
        "steps": steps,
    }


# ===========================================================================
# 8. WEBCAST NAVIGATOR — auto-fill registration gates
# ===========================================================================

# Registration details for auto-filling gated webcasts
DEFAULT_REGISTRATION = {
    "first_name": "Daisy",
    "last_name": "Kotecha",
    "email": "deeya.j.kotecha@gmail.com",
    "company": "SatyaBio",
}

REGISTRATION_FORM_JS = """
(function(info) {
    // Common field selectors for Notified / edge.media-server.com registration
    const fieldMaps = [
        // [fieldName, possibleSelectors]
        ['first_name', ['#firstName', '#first_name', 'input[name="firstName"]',
                        'input[name="first_name"]', 'input[placeholder*="First"]']],
        ['last_name',  ['#lastName', '#last_name', 'input[name="lastName"]',
                        'input[name="last_name"]', 'input[placeholder*="Last"]']],
        ['email',      ['#email', '#emailAddress', 'input[name="email"]',
                        'input[name="emailAddress"]', 'input[type="email"]',
                        'input[placeholder*="Email"]']],
        ['company',    ['#company', '#companyName', 'input[name="company"]',
                        'input[name="companyName"]', 'input[name="organization"]',
                        'input[placeholder*="Company"]', 'input[placeholder*="Organization"]']],
    ];

    const filled = {};
    for (const [field, selectors] of fieldMaps) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                el.value = info[field];
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                filled[field] = sel;
                break;
            }
        }
    }

    // Try to find and click submit
    const submitBtn = document.querySelector(
        'button[type="submit"], input[type="submit"], ' +
        'button.submit, button.btn-primary, ' +
        '#submitButton, .registration-submit'
    );

    return {
        filled: filled,
        submit_found: !!submitBtn,
        submit_text: submitBtn ? submitBtn.textContent.trim() : null,
    };
})(REGISTRATION_INFO);
"""


def get_registration_js(
    first_name: str = None,
    last_name: str = None,
    email: str = None,
    company: str = None,
) -> str:
    """
    Return JS to auto-fill a webcast registration form.
    Replaces REGISTRATION_INFO placeholder with actual values.
    """
    info = {
        "first_name": first_name or DEFAULT_REGISTRATION["first_name"],
        "last_name": last_name or DEFAULT_REGISTRATION["last_name"],
        "email": email or DEFAULT_REGISTRATION["email"],
        "company": company or DEFAULT_REGISTRATION["company"],
    }
    return REGISTRATION_FORM_JS.replace("REGISTRATION_INFO", json.dumps(info))


# ===========================================================================
# 9. STATUS & UTILITIES
# ===========================================================================

def get_webcast_status() -> dict:
    """Check readiness of all pipeline components."""
    status = {
        "openai_whisper_api": _openai_whisper_available,
        "local_whisper_available": _whisper_available,
        "whisper_model": WHISPER_MODEL,
        "database_available": False,
        "voyage_available": False,
        "ffmpeg_available": False,
        "yt_dlp_available": False,
        "transcription_ready": _openai_whisper_available or _whisper_available,
        "upload_enabled": True,
        "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
    }

    # Check DB
    conn = _get_db()
    if conn:
        status["database_available"] = True

    # Check Voyage
    if _get_voyage():
        status["voyage_available"] = True

    # Check ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        status["ffmpeg_available"] = True
    except Exception:
        pass

    # Check yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, timeout=5)
        status["yt_dlp_available"] = True
    except Exception:
        pass

    # Pipeline is ready if we can transcribe AND embed
    status["ready"] = (
        status["transcription_ready"] and
        status["database_available"] and
        status["voyage_available"]
    )

    # Human-readable method description
    if _openai_whisper_available:
        status["transcription_method"] = "OpenAI Whisper API (fast, cloud)"
    elif _whisper_available:
        status["transcription_method"] = f"Local Whisper ({WHISPER_MODEL} model)"
    else:
        status["transcription_method"] = "None available"

    return status


def format_webcast_results_for_claude(results: list[dict], query: str = "") -> str:
    """Format webcast search results for Claude context window."""
    if not results:
        return "No webcast transcripts found."

    lines = [f"=== WEBCAST TRANSCRIPT SEARCH: '{query}' ===\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"--- Result {i} ---")
        lines.append(f"Company: {r.get('ticker', '?')} — {r.get('company_name', '')}")
        lines.append(f"Event: {r.get('title', 'Untitled')}")
        lines.append(f"Date: {r.get('date', 'N/A')}")
        lines.append(f"Section: {r.get('section_title', 'N/A')}")
        lines.append(f"Score: {r.get('hybrid_score', 0):.3f}")
        lines.append(f"Excerpt:\n{r.get('content', '')[:800]}\n")

    return "\n".join(lines)
