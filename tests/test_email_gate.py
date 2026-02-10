"""
Smoke tests for the email gate on /companies and the /api/subscribe endpoint.
"""
import json
import os
import re
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from main import app, _subscribe_rate

SUBS_PATH = Path(__file__).parent.parent / "data" / "subscribers.json"

FEATURED_TICKERS = ["ARGX", "ARWR", "ASND", "EWTX", "KYMR", "NUVL"]


@pytest.fixture(autouse=True)
def clean_subscribers():
    """Remove subscribers.json before and after each test."""
    if SUBS_PATH.exists():
        os.remove(SUBS_PATH)
    _subscribe_rate.clear()
    yield
    if SUBS_PATH.exists():
        os.remove(SUBS_PATH)


@pytest.fixture
def client():
    return TestClient(app)


# ── GET /companies ──────────────────────────────────────────────


def test_companies_page_returns_200(client):
    r = client.get("/companies")
    assert r.status_code == 200


def test_companies_page_has_locked_overlay(client):
    r = client.get("/companies")
    assert "locked-overlay" in r.text


def test_featured_companies_not_locked(client):
    r = client.get("/companies")
    html = r.text

    # Extract the featured section
    m = re.search(r'id="has-detailed-data">(.*?)</section>', html, re.DOTALL)
    assert m, "Featured section not found"
    featured_html = m.group(1)

    assert "locked-blur" not in featured_html
    assert "locked-overlay" not in featured_html
    assert "locked-card" not in featured_html

    # Each featured ticker should be a normal <a> link
    for ticker in FEATURED_TICKERS:
        link = f'<a href="/api/clinical/companies/{ticker}/html"'
        assert link in featured_html, f"{ticker} is not an unlocked link"


# ── POST /api/subscribe ────────────────────────────────────────


def test_subscribe_valid_email(client):
    r = client.post("/api/subscribe", json={"email": "user@example.com"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # Verify file was written
    assert SUBS_PATH.exists()
    with open(SUBS_PATH) as f:
        subs = json.load(f)
    assert len(subs) == 1
    assert subs[0]["email"] == "user@example.com"


def test_subscribe_invalid_email(client):
    r = client.post("/api/subscribe", json={"email": "not-an-email"})
    assert r.status_code == 400


def test_subscribe_rejects_spaces(client):
    r = client.post("/api/subscribe", json={"email": "has space@x.com"})
    assert r.status_code == 400


def test_subscribe_rejects_no_dot(client):
    r = client.post("/api/subscribe", json={"email": "user@localhost"})
    assert r.status_code == 400


def test_subscribe_rejects_too_long(client):
    r = client.post("/api/subscribe", json={"email": "x" * 250 + "@example.com"})
    assert r.status_code == 400


def test_subscribe_deduplicates(client):
    client.post("/api/subscribe", json={"email": "dupe@example.com"})
    client.post("/api/subscribe", json={"email": "dupe@example.com"})

    with open(SUBS_PATH) as f:
        subs = json.load(f)
    assert len(subs) == 1


def test_subscribe_rate_limit(client):
    for i in range(5):
        r = client.post("/api/subscribe", json={"email": f"rate{i}@example.com"})
        assert r.status_code == 200

    r = client.post("/api/subscribe", json={"email": "rate5@example.com"})
    assert r.status_code == 429
