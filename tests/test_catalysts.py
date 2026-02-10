"""
Tests for the shared catalyst system (render_catalyst_section).
"""
import json
import os
import re
import pytest
from pathlib import Path
from datetime import date, timedelta

from app.pages import render_catalyst_section, _parse_catalyst_date


MOCK_DIR = Path(__file__).parent.parent / "data" / "targets" / "_test_mock"


@pytest.fixture(autouse=True)
def mock_catalysts_dir():
    """Create and clean up a mock catalysts.json for testing."""
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    yield
    cat_file = MOCK_DIR / "catalysts.json"
    if cat_file.exists():
        os.remove(cat_file)
    if MOCK_DIR.exists():
        MOCK_DIR.rmdir()


def _write_mock(data):
    with open(MOCK_DIR / "catalysts.json", "w") as f:
        json.dump(data, f)


# ── _parse_catalyst_date ────────────────────────────────────────

def test_parse_full_date():
    assert _parse_catalyst_date("2026-03-15") == date(2026, 3, 15)


def test_parse_year_month():
    assert _parse_catalyst_date("2026-03") == date(2026, 3, 1)


def test_parse_invalid():
    result = _parse_catalyst_date("bad")
    assert result == date(9999, 1, 1)


# ── Completed vs upcoming split ─────────────────────────────────

def test_past_catalysts_go_to_completed():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _write_mock({
        "last_reviewed": date.today().isoformat(),
        "catalysts": [
            {"date": yesterday, "date_display": "Yesterday", "company": "TestCo", "asset": "Drug-A", "description": "Phase 1 done", "outcome": "Positive"}
        ]
    })
    html = render_catalyst_section("_test_mock")
    assert "Completed Catalysts" in html
    assert "Upcoming Catalysts" not in html
    assert "TestCo (Drug-A)" in html
    assert "Positive" in html


def test_future_catalysts_go_to_upcoming():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    _write_mock({
        "last_reviewed": date.today().isoformat(),
        "catalysts": [
            {"date": tomorrow, "date_display": "Tomorrow", "company": "FutureCo", "asset": "Drug-B", "description": "Phase 3 readout"}
        ]
    })
    html = render_catalyst_section("_test_mock")
    assert "Upcoming Catalysts" in html
    assert "Completed Catalysts" not in html
    assert "FutureCo (Drug-B)" in html


def test_today_is_upcoming():
    """A catalyst dated today should be upcoming (date >= today)."""
    today_str = date.today().isoformat()
    _write_mock({
        "last_reviewed": date.today().isoformat(),
        "catalysts": [
            {"date": today_str, "date_display": "Today", "company": "TodayCo", "asset": "X", "description": "Happening now"}
        ]
    })
    html = render_catalyst_section("_test_mock")
    assert "Upcoming Catalysts" in html
    assert "Completed Catalysts" not in html


# ── Sorting ──────────────────────────────────────────────────────

def test_completed_sorted_descending():
    _write_mock({
        "last_reviewed": date.today().isoformat(),
        "catalysts": [
            {"date": "2024-01", "date_display": "Jan 2024", "company": "A", "description": "First"},
            {"date": "2025-06", "date_display": "Jun 2025", "company": "B", "description": "Second"},
            {"date": "2024-09", "date_display": "Sep 2024", "company": "C", "description": "Third"},
        ]
    })
    html = render_catalyst_section("_test_mock")
    pos_b = html.index("Jun 2025")
    pos_c = html.index("Sep 2024")
    pos_a = html.index("Jan 2024")
    assert pos_b < pos_c < pos_a, "Completed should be most recent first"


def test_upcoming_sorted_ascending():
    far_future1 = "2027-01"
    far_future2 = "2028-06"
    far_future3 = "2027-09"
    _write_mock({
        "last_reviewed": date.today().isoformat(),
        "catalysts": [
            {"date": far_future2, "date_display": "Jun 2028", "company": "A", "description": "Latest"},
            {"date": far_future1, "date_display": "Jan 2027", "company": "B", "description": "Earliest"},
            {"date": far_future3, "date_display": "Sep 2027", "company": "C", "description": "Middle"},
        ]
    })
    html = render_catalyst_section("_test_mock")
    pos_b = html.index("Jan 2027")
    pos_c = html.index("Sep 2027")
    pos_a = html.index("Jun 2028")
    assert pos_b < pos_c < pos_a, "Upcoming should be soonest first"


# ── Staleness banner ─────────────────────────────────────────────

def test_no_banner_without_admin():
    _write_mock({
        "last_reviewed": "2025-01-01",
        "catalysts": [{"date": "2027-01", "date_display": "2027", "company": "X", "description": "Test"}]
    })
    html = render_catalyst_section("_test_mock", admin=False)
    assert "Catalysts last verified" not in html


def test_banner_with_admin_when_stale():
    _write_mock({
        "last_reviewed": "2025-01-01",
        "catalysts": [{"date": "2027-01", "date_display": "2027", "company": "X", "description": "Test"}]
    })
    html = render_catalyst_section("_test_mock", admin=True)
    assert "Catalysts last verified 2025-01-01" in html


def test_no_banner_with_admin_when_fresh():
    _write_mock({
        "last_reviewed": date.today().isoformat(),
        "catalysts": [{"date": "2027-01", "date_display": "2027", "company": "X", "description": "Test"}]
    })
    html = render_catalyst_section("_test_mock", admin=True)
    assert "Catalysts last verified" not in html


# ── Missing file ─────────────────────────────────────────────────

def test_missing_file_returns_empty():
    html = render_catalyst_section("nonexistent-target-slug")
    assert html == ""


# ── TL1A integration ─────────────────────────────────────────────

def test_tl1a_page_uses_shared_system():
    from main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    r = client.get("/targets/tl1a-ibd")
    assert r.status_code == 200
    html = r.text

    # Has both sections
    assert "Completed Catalysts" in html
    assert "Upcoming Catalysts" in html

    # No stale 2025 in upcoming
    upcoming = re.search(r"Upcoming Catalysts</h2>(.*?)Back to Target", html, re.DOTALL).group(1)
    assert "2025" not in upcoming

    # Key content present
    assert "ATLAS-UC" in upcoming
    assert "ECCO 2025" in html
