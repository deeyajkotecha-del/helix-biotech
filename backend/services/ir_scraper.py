"""
Company IR News Scraper

Scrapes investor relations pages for recent press releases
to identify catalyst updates and data readouts.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import re
from urllib.parse import urljoin, urlparse


class IRScraper:
    """Scrape investor relations pages for press releases."""

    # Known IR page patterns for biotech companies
    IR_PATTERNS = {
        "arrowheadpharma.com": {
            "news_path": "/news-releases",
            "selectors": {
                "article": "div.wd_news_item, article.news-item, div.news-release",
                "title": "h3 a, h2 a, .news-title a, a.wd_news_title",
                "date": ".wd_news_date, .news-date, time, .date",
                "link": "h3 a, h2 a, .news-title a, a.wd_news_title"
            }
        },
        "default": {
            "selectors": {
                "article": "article, .news-item, .press-release, div[class*='news'], div[class*='release']",
                "title": "h2 a, h3 a, .title a, a[class*='title']",
                "date": "time, .date, span[class*='date'], div[class*='date']",
                "link": "h2 a, h3 a, .title a, a[class*='title']"
            }
        }
    }

    # Keywords for categorizing press releases
    CATEGORY_KEYWORDS = {
        "approval": ["fda approval", "approved", "clearance", "marketing authorization", "nda", "bla", "approval"],
        "data": ["data", "results", "efficacy", "safety", "primary endpoint", "phase 1", "phase 2", "phase 3", "trial results", "topline"],
        "partnership": ["partnership", "collaboration", "agreement", "license", "acquisition", "milestone"],
        "financial": ["earnings", "quarterly", "revenue", "guidance", "financial", "fiscal"],
        "regulatory": ["regulatory", "fda", "ema", "pdufa", "filing", "submission", "breakthrough", "fast track", "priority review"],
        "conference": ["conference", "presentation", "investor", "webcast", "call"],
        "pipeline": ["pipeline", "clinical trial", "initiated", "enrolled", "dosing", "patient"]
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def scrape_news(self, ir_url: str, days_back: int = 90) -> dict:
        """
        Scrape press releases from an IR page.

        Args:
            ir_url: Company IR news URL
            days_back: How many days back to look

        Returns:
            dict with news items and metadata
        """
        result = {
            "url": ir_url,
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "days_back": days_back,
            "news_items": [],
            "errors": []
        }

        try:
            response = self.session.get(ir_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Get domain-specific selectors
            domain = urlparse(ir_url).netloc.replace("www.", "").replace("ir.", "")
            config = self.IR_PATTERNS.get(domain, self.IR_PATTERNS["default"])
            selectors = config.get("selectors", self.IR_PATTERNS["default"]["selectors"])

            # Find news articles
            articles = soup.select(selectors["article"])

            if not articles:
                # Try alternative selectors
                articles = soup.find_all(["article", "div"], class_=lambda x: x and ("news" in x.lower() or "release" in x.lower()))

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

            for article in articles[:50]:  # Limit to 50 most recent
                news_item = self._parse_article(article, selectors, ir_url)
                if news_item:
                    # Check if within date range
                    if news_item.get("date"):
                        try:
                            item_date = datetime.fromisoformat(news_item["date"].replace("Z", "+00:00"))
                            if item_date < cutoff_date:
                                continue
                        except:
                            pass  # Include if date parsing fails

                    result["news_items"].append(news_item)

        except requests.RequestException as e:
            result["errors"].append(f"Request error: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Parsing error: {str(e)}")

        return result

    def _parse_article(self, article, selectors: dict, base_url: str) -> Optional[dict]:
        """Parse a single news article element."""
        try:
            # Find title
            title_elem = article.select_one(selectors["title"])
            if not title_elem:
                title_elem = article.find(["h2", "h3", "a"])

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                return None

            # Find link
            link_elem = article.select_one(selectors["link"])
            if not link_elem:
                link_elem = title_elem if title_elem.name == "a" else title_elem.find("a")

            link = None
            if link_elem and link_elem.get("href"):
                link = urljoin(base_url, link_elem["href"])

            # Find date
            date_elem = article.select_one(selectors["date"])
            if not date_elem:
                date_elem = article.find(["time", "span"], class_=lambda x: x and "date" in x.lower())

            date_str = None
            if date_elem:
                # Try datetime attribute first
                date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
                date_str = self._parse_date(date_str)

            # Categorize the news
            categories = self._categorize_news(title)

            return {
                "title": title,
                "date": date_str,
                "url": link,
                "categories": categories,
                "is_catalyst": self._is_catalyst(title, categories)
            }

        except Exception as e:
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats to ISO format."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Try to extract date with regex
        date_pattern = r"(\w+)\s+(\d{1,2}),?\s+(\d{4})"
        match = re.search(date_pattern, date_str)
        if match:
            try:
                dt = datetime.strptime(f"{match.group(1)} {match.group(2)}, {match.group(3)}", "%B %d, %Y")
                return dt.strftime("%Y-%m-%d")
            except:
                try:
                    dt = datetime.strptime(f"{match.group(1)} {match.group(2)}, {match.group(3)}", "%b %d, %Y")
                    return dt.strftime("%Y-%m-%d")
                except:
                    pass

        return None

    def _categorize_news(self, title: str) -> List[str]:
        """Categorize news based on title keywords."""
        title_lower = title.lower()
        categories = []

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title_lower:
                    categories.append(category)
                    break

        return list(set(categories)) if categories else ["general"]

    def _is_catalyst(self, title: str, categories: List[str]) -> bool:
        """Determine if this news item is a potential catalyst."""
        catalyst_categories = {"approval", "data", "regulatory", "partnership"}
        if any(cat in catalyst_categories for cat in categories):
            return True

        # Additional catalyst keywords
        catalyst_keywords = [
            "fda", "approval", "approved", "data", "results",
            "phase 3", "phase 2", "pivotal", "breakthrough",
            "pdufa", "filing", "submission", "milestone"
        ]
        title_lower = title.lower()
        return any(kw in title_lower for kw in catalyst_keywords)

    def extract_drug_mentions(self, news_items: List[dict], drug_names: List[str]) -> dict:
        """
        Extract which drugs are mentioned in news items.

        Args:
            news_items: List of news items
            drug_names: List of drug names to look for

        Returns:
            dict mapping drug names to relevant news items
        """
        drug_news = {drug: [] for drug in drug_names}

        for item in news_items:
            title_lower = item.get("title", "").lower()
            for drug in drug_names:
                drug_lower = drug.lower()
                # Check for drug name or common variations
                if drug_lower in title_lower or drug_lower.replace("-", "") in title_lower:
                    drug_news[drug].append(item)

        return drug_news


def scrape_arwr_news():
    """Test IR scraper on ARWR."""
    scraper = IRScraper()

    ir_url = "https://ir.arrowheadpharma.com/news-releases"

    print("=" * 70)
    print("IR News Scraper - Arrowhead Pharmaceuticals")
    print("=" * 70)
    print(f"\nScraping: {ir_url}")

    result = scraper.scrape_news(ir_url, days_back=90)

    print(f"\nFound {len(result['news_items'])} news items")

    if result.get("errors"):
        print(f"\nErrors: {result['errors']}")

    # Show recent catalyst news
    catalysts = [item for item in result["news_items"] if item.get("is_catalyst")]
    print(f"\nCatalyst News ({len(catalysts)} items):")

    for item in catalysts[:10]:
        print(f"\n  {item.get('date', 'No date')}:")
        print(f"    {item['title'][:70]}...")
        print(f"    Categories: {', '.join(item.get('categories', []))}")

    # Check drug mentions
    drugs = ["plozasiran", "REDEMPLO", "zodasiran", "fazirsiran", "ARO-INHBE", "ARO-ALK7"]
    drug_mentions = scraper.extract_drug_mentions(result["news_items"], drugs)

    print("\n\nDrug Mentions:")
    for drug, items in drug_mentions.items():
        if items:
            print(f"  {drug}: {len(items)} mentions")


if __name__ == "__main__":
    scrape_arwr_news()
