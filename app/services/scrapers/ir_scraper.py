"""
IR Website Scraper - Fetches presentation PDFs from investor relations pages.

Supports multiple IR website platforms:
- Standard corporate IR pages
- Q4 Inc hosted pages
- Notified IR pages
- Custom implementations
"""

import re
import httpx
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

from .ir_website_mapping import IR_WEBSITE_MAP, get_ir_config

logger = logging.getLogger(__name__)

# Default headers to mimic browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# PDF download directory
DOWNLOADS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "downloads"


class IRScraper:
    """Scraper for investor relations websites."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def scrape_presentation_links(
        self,
        ticker: str,
        max_results: int = 3,
        keywords: list[str] = None
    ) -> list[dict]:
        """
        Find PDF presentation links on a company's IR page.

        Args:
            ticker: Company ticker symbol
            max_results: Maximum number of links to return
            keywords: Filter PDFs containing these keywords (e.g., ["corporate", "presentation"])

        Returns:
            List of dicts with keys: url, title, date (if available)
        """
        ticker = ticker.upper()
        config = get_ir_config(ticker)

        if not config:
            logger.warning(f"No IR config found for {ticker}")
            return []

        ir_url = config.get("presentations_url") or config.get("ir_url")
        if not ir_url:
            logger.warning(f"No IR URL configured for {ticker}")
            return []

        platform = config.get("platform", "standard")

        try:
            if platform == "q4":
                return self._scrape_q4_platform(ir_url, max_results, keywords)
            elif platform == "notified":
                return self._scrape_notified_platform(ir_url, max_results, keywords)
            else:
                return self._scrape_standard_page(ir_url, max_results, keywords)
        except Exception as e:
            logger.error(f"Error scraping {ticker} IR page: {e}")
            return []

    def _scrape_standard_page(
        self,
        url: str,
        max_results: int,
        keywords: list[str] = None
    ) -> list[dict]:
        """Scrape a standard IR webpage for PDF links."""
        response = self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Find all links
        for link in soup.find_all("a", href=True):
            href = link["href"]

            # Check if it's a PDF link
            if not self._is_pdf_link(href):
                continue

            # Get absolute URL
            full_url = urljoin(url, href)

            # Get title from link text or nearby elements
            title = self._extract_link_title(link)

            # Apply keyword filter if specified
            if keywords:
                title_lower = title.lower()
                href_lower = href.lower()
                if not any(kw.lower() in title_lower or kw.lower() in href_lower for kw in keywords):
                    continue

            # Try to extract date
            date = self._extract_date_near_link(link)

            results.append({
                "url": full_url,
                "title": title,
                "date": date,
                "source_page": url
            })

            if len(results) >= max_results:
                break

        return results

    def _scrape_q4_platform(
        self,
        url: str,
        max_results: int,
        keywords: list[str] = None
    ) -> list[dict]:
        """Scrape Q4 Inc hosted IR pages with multiple strategies."""
        response = self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # Strategy 1: Find /static-files/{UUID} links (Q4 standard PDF hosting)
        static_links = soup.find_all("a", href=re.compile(r"/static-files/", re.I))
        for link in static_links:
            href = link["href"]
            full_url = urljoin(url, href)
            title = self._extract_link_title(link)
            date = self._extract_date_near_link(link)

            if keywords:
                title_lower = title.lower()
                href_lower = href.lower()
                if not any(kw.lower() in title_lower or kw.lower() in href_lower for kw in keywords):
                    continue

            results.append({
                "url": full_url,
                "title": title,
                "date": date,
                "source_page": url
            })
            if len(results) >= max_results:
                return results

        # Strategy 2: Find Q4 widget containers
        if not results:
            widget_classes = re.compile(
                r"(nir-widget|module-presentations|ir-widget|presentation|event|document)",
                re.I
            )
            items = soup.find_all(class_=widget_classes)

            for item in items:
                pdf_link = item.find("a", href=lambda h: h and self._is_pdf_link(h))
                if not pdf_link:
                    continue

                full_url = urljoin(url, pdf_link["href"])
                title = self._extract_link_title(pdf_link) or item.get_text(strip=True)[:100]
                date = self._extract_date_near_link(item)

                if keywords:
                    if not any(kw.lower() in title.lower() for kw in keywords):
                        continue

                results.append({
                    "url": full_url,
                    "title": title,
                    "date": date,
                    "source_page": url
                })
                if len(results) >= max_results:
                    return results

        # Strategy 3: Fall back to standard scraping
        if not results:
            return self._scrape_standard_page(url, max_results, keywords)

        return results

    def _scrape_notified_platform(
        self,
        url: str,
        max_results: int,
        keywords: list[str] = None
    ) -> list[dict]:
        """Scrape Notified IR pages."""
        # Notified pages may require API calls or have specific structure
        # For now, fall back to standard scraping
        return self._scrape_standard_page(url, max_results, keywords)

    def _is_pdf_link(self, href: str) -> bool:
        """Check if a URL points to a PDF."""
        href_lower = href.lower()
        return (
            href_lower.endswith(".pdf")
            or ("pdf" in href_lower and "download" in href_lower)
            or "/pdf/" in href_lower
            or "/static-files/" in href_lower
        )

    def _extract_link_title(self, link) -> str:
        """Extract title from a link element."""
        # Try link text first
        text = link.get_text(strip=True)
        if text and len(text) > 3:
            return text

        # Try title attribute
        if link.get("title"):
            return link["title"]

        # Try aria-label
        if link.get("aria-label"):
            return link["aria-label"]

        # Try parent element text
        parent = link.parent
        if parent:
            parent_text = parent.get_text(strip=True)
            if parent_text and len(parent_text) < 200:
                return parent_text

        # Fallback to filename from URL
        href = link.get("href", "")
        filename = Path(urlparse(href).path).stem
        return filename.replace("-", " ").replace("_", " ").title()

    def _extract_date_near_link(self, element) -> Optional[str]:
        """Try to find a date near a link element."""
        # Common date patterns
        date_patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}",
            r"Q[1-4]\s+\d{4}",
            r"\d{4}[/-]\d{2}[/-]\d{2}",
        ]

        # Search in element and nearby elements
        search_text = ""
        if element.parent:
            search_text = element.parent.get_text()

        for pattern in date_patterns:
            match = re.search(pattern, search_text, re.I)
            if match:
                return match.group(0)

        return None

    def download_pdf(
        self,
        url: str,
        save_path: Optional[Path] = None,
        ticker: str = None
    ) -> Path:
        """
        Download a PDF from a URL.

        Args:
            url: URL of the PDF
            save_path: Where to save (optional, auto-generates if not provided)
            ticker: Company ticker for organizing downloads

        Returns:
            Path to the downloaded file
        """
        # Create downloads directory
        if ticker:
            download_dir = DOWNLOADS_DIR / ticker.upper()
        else:
            download_dir = DOWNLOADS_DIR / "misc"
        download_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename if not provided
        if not save_path:
            # Extract filename from URL
            parsed = urlparse(url)
            filename = Path(parsed.path).name
            if not filename or not filename.endswith(".pdf"):
                filename = f"presentation_{hash(url) % 10000}.pdf"
            save_path = download_dir / filename

        # Download the PDF
        logger.info(f"Downloading PDF from {url}")
        response = self.client.get(url)
        response.raise_for_status()

        # Verify it's actually a PDF
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not response.content[:4] == b"%PDF":
            raise ValueError(f"URL did not return a PDF: {content_type}")

        # Save to file
        save_path.write_bytes(response.content)
        logger.info(f"Saved PDF to {save_path}")

        return save_path


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def scrape_presentation_links(
    ticker: str,
    max_results: int = 3,
    keywords: list[str] = None
) -> list[dict]:
    """
    Find PDF presentation links for a company.

    Args:
        ticker: Company ticker symbol
        max_results: Maximum number of links to return
        keywords: Filter PDFs containing these keywords

    Returns:
        List of dicts with keys: url, title, date
    """
    with IRScraper() as scraper:
        return scraper.scrape_presentation_links(ticker, max_results, keywords)


def download_pdf(url: str, save_path: Path = None, ticker: str = None) -> Path:
    """
    Download a PDF from a URL.

    Args:
        url: URL of the PDF
        save_path: Where to save (optional)
        ticker: Company ticker for organizing downloads

    Returns:
        Path to the downloaded file
    """
    with IRScraper() as scraper:
        return scraper.download_pdf(url, save_path, ticker)


def scrape_and_download(
    ticker: str,
    max_results: int = 1,
    keywords: list[str] = None
) -> list[Path]:
    """
    Scrape IR page and download found PDFs.

    Args:
        ticker: Company ticker
        max_results: Maximum PDFs to download
        keywords: Filter by keywords

    Returns:
        List of paths to downloaded PDFs
    """
    with IRScraper() as scraper:
        links = scraper.scrape_presentation_links(ticker, max_results, keywords)
        downloaded = []

        for link in links:
            try:
                path = scraper.download_pdf(link["url"], ticker=ticker)
                downloaded.append(path)
            except Exception as e:
                logger.error(f"Failed to download {link['url']}: {e}")

        return downloaded
