"""
Presentation Scraper

Scrapes investor relations pages to find and catalog PDF presentations.
Works with various IR site structures (Notified, Q4, custom).
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import re


# Keywords to identify presentation types
PRESENTATION_KEYWORDS = {
    "corporate_presentation": ["corporate presentation", "company overview", "investor presentation"],
    "conference_presentation": ["conference", "jpm", "cowen", "goldman", "asco", "aacr", "esc", "aha", "ada", "easl", "aasld"],
    "clinical_data": ["clinical data", "phase 1", "phase 2", "phase 3", "topline", "results", "trial"],
    "earnings": ["earnings", "quarterly", "q1", "q2", "q3", "q4", "financial results"],
    "r&d_day": ["r&d day", "pipeline day", "science day", "research day"],
}

# Date patterns to extract from titles
DATE_PATTERNS = [
    r"(\w+)\s+(\d{1,2}),?\s+(\d{4})",  # January 15, 2025
    r"(\d{1,2})/(\d{1,2})/(\d{4})",     # 01/15/2025
    r"(\d{4})-(\d{2})-(\d{2})",          # 2025-01-15
    r"(\w+)\s+(\d{4})",                   # January 2025
    r"Q([1-4])\s+(\d{4})",               # Q1 2025
]


class PresentationScraper:
    """Scrape presentations from IR pages."""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def scrape(self, ir_url: str, months_back: int = 12) -> List[dict]:
        """
        Scrape presentations from an IR page.

        Args:
            ir_url: IR page URL (download library or presentations page)
            months_back: How many months back to look

        Returns:
            List of presentation metadata dicts
        """
        presentations = []
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)

        try:
            # Fetch the page
            async with self.session.get(ir_url, allow_redirects=True) as response:
                if response.status != 200:
                    return []
                html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            # Strategy 1: Find all PDF links
            pdf_links = self._find_pdf_links(soup, ir_url)
            presentations.extend(pdf_links)

            # Strategy 2: Find event/presentation containers
            event_items = self._find_event_items(soup, ir_url)
            presentations.extend(event_items)

            # Strategy 3: Look for common IR platform structures
            platform_items = self._find_platform_items(soup, ir_url)
            presentations.extend(platform_items)

            # Deduplicate by URL
            seen_urls = set()
            unique = []
            for p in presentations:
                if p["url"] and p["url"] not in seen_urls:
                    seen_urls.add(p["url"])
                    # Filter by date if we have one
                    if p.get("date"):
                        try:
                            p_date = datetime.fromisoformat(p["date"])
                            if p_date >= cutoff_date:
                                unique.append(p)
                        except:
                            unique.append(p)
                    else:
                        unique.append(p)

            # Sort by date (most recent first)
            unique.sort(key=lambda x: x.get("date") or "0000-00-00", reverse=True)

            return unique

        except Exception as e:
            print(f"Scrape error: {e}")
            return []

    def _find_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[dict]:
        """Find all PDF links on the page."""
        presentations = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href.lower():
                url = urljoin(base_url, href)
                title = link.get_text(strip=True) or self._extract_filename(href)

                presentations.append({
                    "title": title,
                    "url": url,
                    "date": self._extract_date(title) or self._extract_date(href),
                    "type": self._classify_presentation(title),
                    "source": "pdf_link"
                })

        return presentations

    def _find_event_items(self, soup: BeautifulSoup, base_url: str) -> List[dict]:
        """Find event/presentation items in common structures."""
        presentations = []

        # Look for common event container classes
        selectors = [
            "div.event-item", "div.presentation-item", "article.event",
            "div[class*='event']", "div[class*='presentation']",
            "li[class*='event']", "li[class*='presentation']",
            "tr[class*='event']", "tr[class*='presentation']"
        ]

        for selector in selectors:
            for item in soup.select(selector):
                # Find title
                title_elem = item.find(["h2", "h3", "h4", "a", "span"], class_=lambda x: x and ("title" in x.lower() if x else False))
                if not title_elem:
                    title_elem = item.find(["h2", "h3", "h4"])
                if not title_elem:
                    title_elem = item.find("a")

                title = title_elem.get_text(strip=True) if title_elem else None

                # Find PDF link
                pdf_link = item.find("a", href=lambda x: x and ".pdf" in x.lower())
                url = urljoin(base_url, pdf_link["href"]) if pdf_link else None

                # Find date
                date_elem = item.find(["time", "span", "div"], class_=lambda x: x and ("date" in x.lower() if x else False))
                if date_elem:
                    date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
                    date = self._parse_date(date_str)
                else:
                    date = self._extract_date(title) if title else None

                if title and url:
                    presentations.append({
                        "title": title,
                        "url": url,
                        "date": date,
                        "type": self._classify_presentation(title),
                        "source": "event_item"
                    })

        return presentations

    def _find_platform_items(self, soup: BeautifulSoup, base_url: str) -> List[dict]:
        """Find items from common IR platforms (Notified, Q4, etc.)."""
        presentations = []

        # Notified platform
        for item in soup.select("div.nir-widget--list-item"):
            title_elem = item.select_one("span.nir-widget--field--title")
            date_elem = item.select_one("span.nir-widget--field--date")
            link_elem = item.select_one("a.nir-widget--link")

            if title_elem and link_elem:
                presentations.append({
                    "title": title_elem.get_text(strip=True),
                    "url": urljoin(base_url, link_elem["href"]) if link_elem.get("href") else None,
                    "date": self._parse_date(date_elem.get_text(strip=True)) if date_elem else None,
                    "type": self._classify_presentation(title_elem.get_text(strip=True)),
                    "source": "notified"
                })

        # Q4 platform
        for item in soup.select("div.module-item"):
            title_elem = item.select_one("h3, .module-title")
            date_elem = item.select_one(".module-date, time")
            link_elem = item.select_one("a[href*='.pdf']")

            if title_elem:
                presentations.append({
                    "title": title_elem.get_text(strip=True),
                    "url": urljoin(base_url, link_elem["href"]) if link_elem and link_elem.get("href") else None,
                    "date": self._parse_date(date_elem.get_text(strip=True)) if date_elem else None,
                    "type": self._classify_presentation(title_elem.get_text(strip=True)),
                    "source": "q4"
                })

        # Generic table rows
        for row in soup.select("table tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                # Look for PDF link in row
                pdf_link = row.find("a", href=lambda x: x and ".pdf" in x.lower())
                if pdf_link:
                    title = pdf_link.get_text(strip=True) or cells[0].get_text(strip=True)
                    date_cell = cells[0] if len(cells) > 1 else None
                    date = self._parse_date(date_cell.get_text(strip=True)) if date_cell else None

                    presentations.append({
                        "title": title,
                        "url": urljoin(base_url, pdf_link["href"]),
                        "date": date or self._extract_date(title),
                        "type": self._classify_presentation(title),
                        "source": "table"
                    })

        return presentations

    def _extract_filename(self, url: str) -> str:
        """Extract filename from URL."""
        path = urlparse(url).path
        return path.split("/")[-1].replace(".pdf", "").replace("-", " ").replace("_", " ")

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text using patterns."""
        if not text:
            return None

        for pattern in DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_date(match.group(0))

        return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats to ISO format."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Common formats
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
            "%d %B %Y",
            "%B %Y",
            "%Y-%m-%dT%H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Handle Q1 2025 format
        q_match = re.match(r"Q([1-4])\s+(\d{4})", date_str, re.IGNORECASE)
        if q_match:
            quarter = int(q_match.group(1))
            year = int(q_match.group(2))
            month = (quarter - 1) * 3 + 1
            return f"{year}-{month:02d}-01"

        return None

    def _classify_presentation(self, title: str) -> str:
        """Classify presentation type based on title."""
        if not title:
            return "other"

        title_lower = title.lower()

        for ptype, keywords in PRESENTATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return ptype

        return "other"


async def scrape_presentations(ir_url: str, months_back: int = 12) -> List[dict]:
    """Convenience function to scrape presentations."""
    async with PresentationScraper() as scraper:
        return await scraper.scrape(ir_url, months_back)


async def main():
    """Test presentation scraper."""
    test_urls = [
        "https://ir.arrowheadpharma.com/download-library",
        "https://investors.alnylam.com/events-and-presentations",
    ]

    print("=" * 70)
    print("Presentation Scraper Test")
    print("=" * 70)

    async with PresentationScraper() as scraper:
        for url in test_urls:
            print(f"\n{url}:")
            presentations = await scraper.scrape(url, months_back=6)
            print(f"  Found {len(presentations)} presentations")

            for p in presentations[:5]:
                print(f"\n  [{p.get('date', 'No date')}] {p.get('type')}")
                print(f"    {p.get('title', 'No title')[:60]}...")
                print(f"    {p.get('url', 'No URL')[:70]}...")


if __name__ == "__main__":
    asyncio.run(main())
