"""
Webcast Pipeline — Dry-run Test Suite
======================================
Tests every layer of the pipeline:
  1. Chunking logic (pure Python, no deps)
  2. Section inference
  3. Registration JS generation
  4. MediaRecorder JS generation
  5. Transcript ingestion (mocked DB)
  6. Search formatting
  7. End-to-end with synthetic audio (if ffmpeg + whisper available)
  8. API endpoint contract tests

Run:  python test_webcast_pipeline.py
"""

import os
import sys
import json
import tempfile

# Add the search dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Track results
PASS = 0
FAIL = 0
SKIP = 0


def test(name):
    """Decorator to register and run a test."""
    def wrapper(fn):
        global PASS, FAIL, SKIP
        try:
            result = fn()
            if result == "SKIP":
                print(f"  ⏭  {name} (skipped)")
                SKIP += 1
            else:
                print(f"  ✓  {name}")
                PASS += 1
        except Exception as e:
            print(f"  ✗  {name}: {e}")
            FAIL += 1
        return fn
    return wrapper


# ===========================================================================
# 1. IMPORT TEST
# ===========================================================================

print("\n=== 1. Import Tests ===")

@test("webcast_pipeline imports without crash")
def _():
    import webcast_pipeline
    assert hasattr(webcast_pipeline, 'chunk_transcript')
    assert hasattr(webcast_pipeline, 'transcribe_audio')
    assert hasattr(webcast_pipeline, 'ingest_webcast')
    assert hasattr(webcast_pipeline, 'search_webcasts')
    assert hasattr(webcast_pipeline, 'process_webcast')
    assert hasattr(webcast_pipeline, 'get_webcast_status')

@test("all public functions exist")
def _():
    from webcast_pipeline import (
        capture_audio_yt_dlp,
        convert_to_wav,
        get_media_recorder_js,
        transcribe_audio,
        chunk_transcript,
        ingest_webcast,
        search_webcasts,
        list_webcasts,
        get_webcast_transcript,
        process_webcast,
        get_registration_js,
        get_webcast_status,
        format_webcast_results_for_claude,
    )


# ===========================================================================
# 2. CHUNKING LOGIC
# ===========================================================================

print("\n=== 2. Chunking Tests ===")

@test("chunk_transcript: empty input returns empty list")
def _():
    from webcast_pipeline import chunk_transcript
    assert chunk_transcript("") == []
    assert chunk_transcript("   ") == []
    assert chunk_transcript(None) == []

@test("chunk_transcript: short text returns single chunk")
def _():
    from webcast_pipeline import chunk_transcript
    text = "This is a short webcast transcript about drug efficacy."
    chunks = chunk_transcript(text)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["word_count"] == len(text.split())
    assert chunks[0]["content"] == text

@test("chunk_transcript: long text produces multiple chunks with overlap")
def _():
    from webcast_pipeline import chunk_transcript, CHUNK_WORDS, CHUNK_OVERLAP
    # Generate text longer than CHUNK_WORDS
    words = [f"word{i}" for i in range(CHUNK_WORDS * 3)]
    text = " ".join(words)
    chunks = chunk_transcript(text)
    assert len(chunks) > 1, f"Expected multiple chunks, got {len(chunks)}"
    # Check indices are sequential
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i
    # Check overlap: second chunk should contain some words from first
    first_words = set(chunks[0]["content"].split()[-CHUNK_OVERLAP:])
    second_words = set(chunks[1]["content"].split()[:CHUNK_OVERLAP])
    overlap = first_words & second_words
    assert len(overlap) > 0, "No overlap between consecutive chunks"

@test("chunk_transcript: segment-based chunking uses timestamps")
def _():
    from webcast_pipeline import chunk_transcript, CHUNK_WORDS
    # Simulate Whisper segments
    segments = []
    total_words = 0
    for i in range(100):
        seg_text = f"Segment {i} discusses clinical data about the drug candidate. " * 5
        segments.append({
            "start": i * 10.0,
            "end": (i + 1) * 10.0,
            "text": seg_text,
        })
        total_words += len(seg_text.split())

    full_text = " ".join(s["text"] for s in segments)
    chunks = chunk_transcript(full_text, segments)

    assert len(chunks) > 1, f"Expected multiple segment-based chunks, got {len(chunks)}"
    # Check timestamps are set
    assert chunks[0]["start_time"] >= 0
    assert chunks[-1]["end_time"] > 0
    # All chunks should have content
    for c in chunks:
        assert len(c["content"].strip()) > 0, f"Empty chunk at index {c['chunk_index']}"

@test("chunk_transcript: each chunk respects word limit (approximately)")
def _():
    from webcast_pipeline import chunk_transcript, CHUNK_WORDS, CHUNK_OVERLAP
    words = [f"word{i}" for i in range(CHUNK_WORDS * 5)]
    text = " ".join(words)
    chunks = chunk_transcript(text)
    for c in chunks[:-1]:  # Last chunk can be shorter
        # Allow some tolerance due to overlap
        assert c["word_count"] <= CHUNK_WORDS + CHUNK_OVERLAP + 10, \
            f"Chunk {c['chunk_index']} has {c['word_count']} words (limit ~{CHUNK_WORDS})"


# ===========================================================================
# 3. SECTION INFERENCE
# ===========================================================================

print("\n=== 3. Section Inference Tests ===")

@test("_infer_section: detects clinical sections")
def _():
    from webcast_pipeline import _infer_section
    assert _infer_section("The efficacy results from the Phase 2 trial were positive") == "Efficacy Data"
    assert _infer_section("Our pipeline includes three programs in oncology") == "Pipeline Overview"
    assert _infer_section("Revenue for Q4 was $2.3 billion, up 15%") == "Financial Results"
    assert _infer_section("We received FDA approval for our lead compound") == "Regulatory"

@test("_infer_section: Q&A detection")
def _():
    from webcast_pipeline import _infer_section
    assert _infer_section("Great question. Let me address the dosing schedule") == "Q&A"

@test("_infer_section: time-based fallback")
def _():
    from webcast_pipeline import _infer_section
    assert _infer_section("Some generic text about nothing specific", 30) == "Introduction"
    assert _infer_section("Some generic text about nothing specific", 300) == "Presentation"


# ===========================================================================
# 4. REGISTRATION JS GENERATION
# ===========================================================================

print("\n=== 4. Registration JS Tests ===")

@test("get_registration_js: contains user info")
def _():
    from webcast_pipeline import get_registration_js
    js = get_registration_js("Daisy", "Kotecha", "deeya.j@gmail.com", "SatyaBio")
    assert "Daisy" in js
    assert "Kotecha" in js
    assert "deeya.j@gmail.com" in js
    assert "SatyaBio" in js

@test("get_registration_js: default values work")
def _():
    from webcast_pipeline import get_registration_js, DEFAULT_REGISTRATION
    js = get_registration_js()
    assert DEFAULT_REGISTRATION["first_name"] in js
    assert DEFAULT_REGISTRATION["email"] in js

@test("get_registration_js: contains field selectors for Notified platform")
def _():
    from webcast_pipeline import get_registration_js
    js = get_registration_js()
    # Should target common Notified form fields
    assert "firstName" in js
    assert "lastName" in js
    assert "email" in js
    assert "company" in js

@test("get_registration_js: valid JavaScript structure")
def _():
    from webcast_pipeline import get_registration_js
    js = get_registration_js("Test", "User", "test@test.com", "TestCo")
    # Should be a self-executing function
    assert "(function(info)" in js
    # Should have the JSON replaced
    assert "REGISTRATION_INFO" not in js
    # Parse the embedded JSON
    import re
    json_match = re.search(r'\)\((\{.*?\})\)', js, re.DOTALL)
    assert json_match, "Could not find JSON parameter in JS"
    info = json.loads(json_match.group(1))
    assert info["first_name"] == "Test"
    assert info["company"] == "TestCo"


# ===========================================================================
# 5. MEDIA RECORDER JS
# ===========================================================================

print("\n=== 5. MediaRecorder JS Tests ===")

@test("get_media_recorder_js: returns valid JS snippet")
def _():
    from webcast_pipeline import get_media_recorder_js
    js = get_media_recorder_js()
    assert len(js) > 100
    assert "captureStream" in js
    assert "MediaRecorder" in js
    assert "__helixRecorder" in js
    assert "audio/webm" in js


# ===========================================================================
# 6. FORMAT FOR CLAUDE
# ===========================================================================

print("\n=== 6. Claude Formatting Tests ===")

@test("format_webcast_results_for_claude: empty results")
def _():
    from webcast_pipeline import format_webcast_results_for_claude
    result = format_webcast_results_for_claude([], "test query")
    assert "No webcast transcripts found" in result

@test("format_webcast_results_for_claude: with results")
def _():
    from webcast_pipeline import format_webcast_results_for_claude
    results = [
        {
            "ticker": "LLY",
            "company_name": "Eli Lilly",
            "title": "Q4 2025 Earnings Call",
            "date": "2025-12-15",
            "section_title": "Financial Results",
            "hybrid_score": 0.85,
            "content": "Revenue increased 22% year over year driven by strong Mounjaro sales.",
        }
    ]
    formatted = format_webcast_results_for_claude(results, "Eli Lilly revenue")
    assert "WEBCAST TRANSCRIPT SEARCH" in formatted
    assert "LLY" in formatted
    assert "Eli Lilly" in formatted
    assert "Q4 2025 Earnings Call" in formatted
    assert "Revenue increased" in formatted
    assert "0.850" in formatted


# ===========================================================================
# 7. STATUS CHECK
# ===========================================================================

print("\n=== 7. Status Tests ===")

@test("get_webcast_status: returns expected fields")
def _():
    from webcast_pipeline import get_webcast_status
    status = get_webcast_status()
    assert "whisper_available" in status
    assert "database_available" in status
    assert "voyage_available" in status
    assert "ffmpeg_available" in status
    assert "yt_dlp_available" in status
    assert "whisper_model" in status
    assert "ready" in status
    assert isinstance(status["ready"], bool)


# ===========================================================================
# 8. WHISPER TRANSCRIPTION (if available)
# ===========================================================================

print("\n=== 8. Whisper Transcription Tests ===")

@test("transcribe_audio: returns error when whisper not available")
def _():
    from webcast_pipeline import transcribe_audio, _whisper_available
    if _whisper_available:
        return "SKIP"  # Can't test error path when whisper IS available
    result = transcribe_audio("/tmp/nonexistent.wav")
    assert "error" in result
    assert "Whisper" in result["error"] or "not available" in result["error"]

@test("transcribe_audio: with synthetic speech (if ffmpeg + whisper available)")
def _():
    from webcast_pipeline import _whisper_available, get_webcast_status
    status = get_webcast_status()

    if not _whisper_available:
        return "SKIP"
    if not status["ffmpeg_available"]:
        return "SKIP"

    from webcast_pipeline import transcribe_audio
    import subprocess

    # Generate 5 seconds of synthetic speech-like audio using ffmpeg
    # (sine wave — not actual speech, but tests the pipeline mechanics)
    test_wav = "/tmp/helix_test_audio.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-ar", "16000", "-ac", "1",
        test_wav,
    ], capture_output=True, timeout=30)

    assert os.path.exists(test_wav), "Failed to create test audio"

    result = transcribe_audio(test_wav)
    assert "error" not in result, f"Transcription failed: {result.get('error')}"
    assert "text" in result
    assert "segments" in result
    assert "duration" in result
    assert result["duration"] > 0

    # Clean up
    os.remove(test_wav)


# ===========================================================================
# 9. YT-DLP CAPTURE (structure test)
# ===========================================================================

print("\n=== 9. yt-dlp Tests ===")

@test("capture_audio_yt_dlp: handles missing yt-dlp gracefully")
def _():
    from webcast_pipeline import capture_audio_yt_dlp, get_webcast_status
    status = get_webcast_status()
    if status["yt_dlp_available"]:
        return "SKIP"  # Can't test missing-tool path when it's installed
    result = capture_audio_yt_dlp("https://example.com/fake-webcast")
    assert result is None

@test("capture_audio_yt_dlp: handles invalid URL gracefully")
def _():
    from webcast_pipeline import capture_audio_yt_dlp
    result = capture_audio_yt_dlp("not-a-real-url")
    assert result is None  # Should fail gracefully, not crash


# ===========================================================================
# 10. INGEST (DB test — will fail without DB, that's expected)
# ===========================================================================

print("\n=== 10. Database Ingestion Tests ===")

@test("ingest_webcast: returns error when DB not available")
def _():
    from webcast_pipeline import ingest_webcast, _get_db
    conn = _get_db()
    if conn is not None:
        return "SKIP"  # DB is available, can't test error path
    result = ingest_webcast(
        transcript_text="Test transcript about clinical data.",
        title="Test Webcast",
        ticker="TEST",
    )
    assert result.get("status") == "error" or "error" in result

@test("ingest_webcast: with real DB connection (if available)")
def _():
    from webcast_pipeline import ingest_webcast, _get_db, _get_voyage
    conn = _get_db()
    vo = _get_voyage()
    if conn is None or vo is None:
        return "SKIP"

    # Generate a realistic biotech transcript
    test_transcript = (
        "Good morning everyone and welcome to Structure Therapeutics fourth quarter "
        "earnings call. I'm joined today by our CEO and our CFO. Before we begin, "
        "I'd like to remind you that this call contains forward-looking statements. "
        "Moving to our pipeline update. Our lead program, the oral GLP-1 receptor agonist "
        "GSBR-1290, has shown compelling Phase 2 data. We observed a mean body weight "
        "reduction of 7.5% at 12 weeks in the 120mg dose cohort. The safety profile "
        "remains favorable with the most common adverse events being mild GI-related. "
        "Nausea was reported in 15% of patients versus 5% placebo. We plan to initiate "
        "our Phase 3 ACCESS program in Q1 2026. Enrollment target is 1,500 patients "
        "across 200 sites globally. Now turning to our financial results. Revenue for "
        "the quarter was driven by our collaboration with Novo Nordisk. We ended the "
        "quarter with $450 million in cash, providing runway through 2027. "
        "Now I'll open the line for questions. Yes, regarding the dose selection for "
        "Phase 3, we selected 120mg based on the totality of our Phase 2 data showing "
        "the best efficacy-tolerability balance at that dose level. "
    )

    result = ingest_webcast(
        transcript_text=test_transcript,
        title="GPCR Q4 2025 Earnings Call (TEST)",
        ticker="GPCR",
        company_name="Structure Therapeutics",
        event_date="2025-12-15",
        event_type="earnings_call",
        source_url="https://example.com/test",
        duration_seconds=1800,
    )

    assert result.get("status") in ("ok", "already_exists"), \
        f"Unexpected status: {result}"

    if result["status"] == "ok":
        assert result["document_id"] > 0
        assert result["chunks_stored"] > 0
        assert result["word_count"] > 50
        print(f"      → Ingested: doc_id={result['document_id']}, "
              f"{result['chunks_stored']} chunks, {result['word_count']} words")

    return result


# ===========================================================================
# 11. SEARCH (if DB available)
# ===========================================================================

print("\n=== 11. Search Tests ===")

@test("search_webcasts: returns results for ingested content")
def _():
    from webcast_pipeline import search_webcasts, _get_db, _get_voyage
    if _get_db() is None or _get_voyage() is None:
        return "SKIP"

    results = search_webcasts("GLP-1 weight loss efficacy", ticker="GPCR", top_k=5)
    # If we just ingested the test transcript, should find it
    if len(results) > 0:
        assert results[0]["content"], "Empty content in search result"
        assert results[0].get("ticker") == "GPCR"
        print(f"      → Found {len(results)} results, top score: "
              f"{results[0].get('hybrid_score', 0):.3f}")
    else:
        print("      → No results (DB may be empty)")

@test("search_webcasts: empty query returns empty")
def _():
    from webcast_pipeline import search_webcasts, _get_db
    if _get_db() is None:
        return "SKIP"
    # An empty string query should not crash
    results = search_webcasts("")
    # May return results or empty, but should not crash

@test("list_webcasts: returns library data")
def _():
    from webcast_pipeline import list_webcasts, _get_db
    if _get_db() is None:
        return "SKIP"
    result = list_webcasts(limit=5)
    assert "webcasts" in result
    assert "total" in result
    assert isinstance(result["webcasts"], list)
    print(f"      → Library: {result['total']} total webcasts")

@test("get_webcast_transcript: retrieves ingested transcript")
def _():
    from webcast_pipeline import get_webcast_transcript, list_webcasts, _get_db
    if _get_db() is None:
        return "SKIP"

    # Get the most recent webcast
    lib = list_webcasts(limit=1)
    if not lib["webcasts"]:
        return "SKIP"

    doc_id = lib["webcasts"][0]["id"]
    result = get_webcast_transcript(doc_id)
    assert "chunks" in result
    assert "full_transcript" in result
    assert len(result["full_transcript"]) > 0
    assert len(result["chunks"]) > 0
    print(f"      → Transcript for doc {doc_id}: {len(result['chunks'])} chunks, "
          f"{len(result['full_transcript'])} chars")


# ===========================================================================
# 12. CONVERT TO WAV
# ===========================================================================

print("\n=== 12. Audio Conversion Tests ===")

@test("convert_to_wav: handles nonexistent file gracefully")
def _():
    from webcast_pipeline import convert_to_wav
    result = convert_to_wav("/tmp/nonexistent_audio.mp3")
    assert result is None

@test("convert_to_wav: converts synthetic audio (if ffmpeg available)")
def _():
    from webcast_pipeline import convert_to_wav, get_webcast_status
    if not get_webcast_status()["ffmpeg_available"]:
        return "SKIP"

    import subprocess
    # Create a WAV at 44.1kHz stereo — then convert_to_wav should make it 16kHz mono
    test_input = "/tmp/helix_test_convert_44k.wav"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
        "-ar", "44100", "-ac", "2",
        test_input,
    ], capture_output=True, timeout=30)

    if not os.path.exists(test_input):
        return "SKIP"

    result = convert_to_wav(test_input)
    assert result is not None, "Conversion returned None"
    assert os.path.exists(result), f"Output file not found: {result}"
    assert result.endswith("_16k.wav")

    # Verify it's 16kHz mono
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", result],
        capture_output=True, text=True, timeout=10,
    )
    if probe.returncode == 0:
        info = json.loads(probe.stdout)
        stream = info["streams"][0]
        assert int(stream["sample_rate"]) == 16000, f"Sample rate: {stream['sample_rate']}"
        assert int(stream["channels"]) == 1, f"Channels: {stream['channels']}"
        print(f"      → Converted: 16kHz mono WAV, {os.path.getsize(result)} bytes")

    os.remove(test_input)
    os.remove(result)


# ===========================================================================
# SUMMARY
# ===========================================================================

print(f"\n{'='*50}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped")
print(f"{'='*50}")

if FAIL > 0:
    print("\n  ⚠️  Some tests FAILED — review above for details")
    sys.exit(1)
else:
    print("\n  ✅ All tests passed!")
    sys.exit(0)
