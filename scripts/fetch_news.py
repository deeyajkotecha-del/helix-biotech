#!/usr/bin/env python3
"""
Automated biotech news ticker fetcher.

Fetches RSS feeds from biotech news sources, uses Claude API to classify
and extract structured data, writes to data/homepage/news_ticker.json.

Usage:
    python scripts/fetch_news.py              # Fetch and classify
    python scripts/fetch_news.py --dry-run    # Fetch only, no Claude API call

Requires:
    pip install feedparser anthropic
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser

DATA_DIR = Path(__file__).parent.parent / "data" / "homepage"
OUTPUT_PATH = DATA_DIR / "news_ticker.json"
MANUAL_PATH = DATA_DIR / "news_ticker_manual.json"

# RSS feeds — biotech-focused sources
RSS_FEEDS = [
    {
        "name": "FierceBiotech",
        "url": "https://www.fiercebiotech.com/rss/xml",
        "category": "industry",
    },
    {
        "name": "BioSpace",
        "url": "https://www.biospace.com/rss",
        "category": "industry",
    },
    {
        "name": "Endpoints News",
        "url": "https://endpts.com/feed/",
        "category": "industry",
    },
    {
        "name": "STAT News",
        "url": "https://www.statnews.com/feed/",
        "category": "industry",
    },
]

# Maximum items to keep per source
MAX_PER_SOURCE = 8
# Maximum total items in output (excluding manual pins)
MAX_TOTAL = 20

CLASSIFY_PROMPT = """You are a biotech investment analyst. Given the following news headlines and summaries from biotech RSS feeds, classify each one and extract structured data.

For each item, return a JSON object with:
- "headline": cleaned headline (max 120 chars, remove source prefix if present)
- "source": source name
- "url": article URL
- "published": ISO date string
- "category": one of ["clinical_data", "regulatory", "deal", "ipo_financing", "earnings", "personnel", "policy", "other"]
- "tickers": array of stock tickers mentioned (uppercase, empty array if none)
- "importance": 1-5 (5 = most important for biotech investors)
- "one_liner": a single sentence summary (max 80 chars) suitable for a scrolling ticker

Only include items scoring importance >= 3. Return a JSON array of objects.

Here are the items:
{items}

Return ONLY the JSON array, no other text."""


def fetch_feeds() -> list[dict]:
    """Fetch and parse all RSS feeds, return raw items."""
    all_items = []

    for feed_config in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            entries = feed.entries[:MAX_PER_SOURCE]

            for entry in entries:
                published = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                    except (ValueError, TypeError):
                        published = ""

                all_items.append({
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:300].strip(),
                    "published": published,
                    "source": feed_config["name"],
                })

            print(f"  Fetched {len(entries)} items from {feed_config['name']}")

        except Exception as e:
            print(f"  Warning: Failed to fetch {feed_config['name']}: {e}")

    return all_items


def classify_with_claude(items: list[dict]) -> list[dict]:
    """Use Claude API to classify and structure news items."""
    try:
        import anthropic
    except ImportError:
        print("  Error: anthropic package not installed. Run: pip install anthropic")
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  Error: ANTHROPIC_API_KEY not set. Skipping classification.")
        return []

    # Format items for the prompt
    items_text = ""
    for i, item in enumerate(items, 1):
        items_text += f"\n{i}. [{item['source']}] {item['title']}\n"
        items_text += f"   URL: {item['link']}\n"
        items_text += f"   Published: {item['published']}\n"
        if item['summary']:
            items_text += f"   Summary: {item['summary']}\n"

    prompt = CLASSIFY_PROMPT.format(items=items_text)

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        classified = json.loads(text)
        print(f"  Claude classified {len(classified)} items (importance >= 3)")
        return classified

    except json.JSONDecodeError as e:
        print(f"  Error parsing Claude response: {e}")
        return []
    except Exception as e:
        print(f"  Error calling Claude API: {e}")
        return []


def load_manual_items() -> list[dict]:
    """Load manually pinned news items."""
    if MANUAL_PATH.exists():
        with open(MANUAL_PATH) as f:
            data = json.load(f)
            return data.get("pinned", [])
    return []


def build_ticker_output(classified: list[dict], manual: list[dict]) -> dict:
    """Merge classified + manual items into final ticker output."""
    # Sort classified by importance (desc), then recency
    classified.sort(key=lambda x: (-x.get("importance", 0), x.get("published", "")), reverse=False)

    # Trim to max
    classified = classified[:MAX_TOTAL]

    now = datetime.now(timezone.utc).isoformat()

    return {
        "_metadata": {
            "last_fetched": now,
            "sources": [f["name"] for f in RSS_FEEDS],
            "total_items": len(classified),
            "pinned_items": len(manual),
        },
        "pinned": manual,
        "items": classified,
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch biotech news for ticker")
    parser.add_argument("--dry-run", action="store_true", help="Fetch RSS only, skip Claude classification")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Biotech News Ticker Fetcher")
    print("=" * 50)

    # Step 1: Fetch RSS feeds
    print("\n1. Fetching RSS feeds...")
    raw_items = fetch_feeds()
    print(f"   Total raw items: {len(raw_items)}")

    if not raw_items:
        print("   No items fetched. Exiting.")
        return

    # Step 2: Classify with Claude (unless dry-run)
    if args.dry_run:
        print("\n2. Dry run — skipping Claude classification")
        # Create basic items without classification
        classified = []
        for item in raw_items[:MAX_TOTAL]:
            classified.append({
                "headline": item["title"][:120],
                "source": item["source"],
                "url": item["link"],
                "published": item["published"],
                "category": "other",
                "tickers": [],
                "importance": 3,
                "one_liner": item["title"][:80],
            })
    else:
        print("\n2. Classifying with Claude API...")
        classified = classify_with_claude(raw_items)

    if not classified:
        print("   No classified items. Using raw headlines as fallback.")
        classified = []
        for item in raw_items[:MAX_TOTAL]:
            classified.append({
                "headline": item["title"][:120],
                "source": item["source"],
                "url": item["link"],
                "published": item["published"],
                "category": "other",
                "tickers": [],
                "importance": 3,
                "one_liner": item["title"][:80],
            })

    # Step 3: Load manual items
    print("\n3. Loading manual overrides...")
    manual = load_manual_items()
    print(f"   Pinned items: {len(manual)}")

    # Step 4: Build and write output
    print("\n4. Writing output...")
    output = build_ticker_output(classified, manual)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"   Written to {OUTPUT_PATH}")
    print(f"   Total: {len(output['items'])} items + {len(output['pinned'])} pinned")
    print("\nDone.")


if __name__ == "__main__":
    main()
