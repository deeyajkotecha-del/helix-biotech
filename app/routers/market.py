"""
Market Data Router

Live market cap lookups and bulk refresh via Yahoo Finance.
"""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import yfinance as yf

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "companies" / "index.json"
COMPANIES_DIR = PROJECT_ROOT / "data" / "companies"


class MarketDataResponse(BaseModel):
    ticker: str
    name: Optional[str] = None
    market_cap_raw: Optional[int] = None
    market_cap_formatted: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    source: str = "yahoo_finance"


class RefreshResult(BaseModel):
    updated: int
    unchanged: int
    failed: int
    total: int
    timestamp: str


class LastUpdatedResponse(BaseModel):
    last_updated: str
    total_companies: int
    version: str


def format_market_cap(value: int | float | None) -> str | None:
    """Convert numeric market cap (in USD) to string format like '$3.7B', '$350M'."""
    if value is None or value <= 0:
        return None
    if value >= 1_000_000_000:
        billions = value / 1_000_000_000
        if billions >= 100:
            return f"${billions:.0f}B"
        elif billions >= 10:
            return f"${billions:.0f}B"
        else:
            return f"${billions:.1f}B"
    elif value >= 1_000_000:
        millions = value / 1_000_000
        if millions >= 100:
            return f"${millions:.0f}M"
        else:
            return f"${millions:.0f}M"
    else:
        return f"${value / 1_000_000:.1f}M"


# --- Fixed routes MUST come before the /{ticker} catch-all ---


@router.get("/status/last-updated", response_model=LastUpdatedResponse)
async def get_last_updated():
    """Read last-updated metadata from index.json."""
    if not INDEX_PATH.exists():
        raise HTTPException(status_code=404, detail="index.json not found")

    with open(INDEX_PATH) as f:
        index = json.load(f)

    return LastUpdatedResponse(
        last_updated=index.get("updated", "unknown"),
        total_companies=len(index.get("companies", [])),
        version=index.get("version", "unknown"),
    )


@router.post("/refresh", response_model=RefreshResult)
async def refresh_market_data():
    """Bulk refresh all market caps in index.json from Yahoo Finance."""
    if not INDEX_PATH.exists():
        raise HTTPException(status_code=404, detail="index.json not found")

    with open(INDEX_PATH) as f:
        index = json.load(f)

    companies = index.get("companies", [])
    updated = 0
    failed = 0
    unchanged = 0

    for company in companies:
        ticker = company["ticker"]
        old_cap = company.get("market_cap_mm", "")

        try:
            t = yf.Ticker(ticker)
            market_cap_raw = t.info.get("marketCap")
        except Exception:
            failed += 1
            continue

        new_cap = format_market_cap(market_cap_raw)
        if new_cap is None:
            failed += 1
            continue

        if new_cap == old_cap:
            unchanged += 1
            continue

        company["market_cap_mm"] = new_cap
        updated += 1

        # Also update individual company.json if it exists
        company_json = COMPANIES_DIR / ticker / "company.json"
        if company_json.exists():
            try:
                with open(company_json) as f:
                    cdata = json.load(f)
                cdata["market_cap"] = new_cap
                with open(company_json, "w") as f:
                    json.dump(cdata, f, indent=2)
            except Exception:
                pass

        # Rate limit
        await asyncio.sleep(0.3)

    # Write index
    if updated > 0:
        index["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(INDEX_PATH, "w") as f:
            json.dump(index, f, indent=2)

    return RefreshResult(
        updated=updated,
        unchanged=unchanged,
        failed=failed,
        total=len(companies),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# --- Dynamic route (catch-all) MUST come last ---


@router.get("/{ticker}", response_model=MarketDataResponse)
async def get_market_data(ticker: str):
    """Live Yahoo Finance lookup for a single ticker."""
    ticker = ticker.upper()
    try:
        t = yf.Ticker(ticker)
        info = t.info
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Yahoo Finance error: {e}")

    market_cap = info.get("marketCap")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    name = info.get("shortName") or info.get("longName")

    return MarketDataResponse(
        ticker=ticker,
        name=name,
        market_cap_raw=market_cap,
        market_cap_formatted=format_market_cap(market_cap),
        price=price,
    )
