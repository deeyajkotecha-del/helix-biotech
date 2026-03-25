"""
Oncology IR Page Scraper

Scrapes investor presentations and press releases from oncology company IR pages.
Uses curl-cffi with Chrome TLS impersonation to bypass Akamai/Q4 bot detection
that blocks standard Python HTTP libraries (httpx, requests, urllib3).

Features:
  - curl-cffi Chrome TLS fingerprint (bypasses JA3/JA4 detection)
  - Multi-page scraping (events, press releases, presentations)
  - PDF + PPTX document detection
  - Two-tier deduplication: URL lookup (fast) then SHA-256 hash (catches mirrors)
  - Download to memory first for hash check before writing to disk
  - Persistent metadata in data/downloads/oncology_metadata.json
  - Retry with exponential backoff on 403/429/timeout
  - Document type classification (investor_presentation, sec_filing, etc.)
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as cffi_requests
from curl_cffi.requests.errors import RequestsError
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from company_config import ONCOLOGY_COMPANIES, get_oncology_config, get_all_oncology_tickers

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
COMPANIES_DIR = DATA_DIR / "companies"
METADATA_FILE = DATA_DIR / "downloads" / "oncology_metadata.json"
PAGE_DELAY = 2  # seconds between page requests
MAX_RETRIES = 3
BACKOFF_DELAYS = [2, 4, 8]  # seconds
EVENT_YEARS = [2024, 2025, 2026]  # years to scrape for events pages

# --------------------------------------------------------------------------
# Document type classification
# --------------------------------------------------------------------------

_DOC_TYPE_RULES = [
    ("sec_filing", re.compile(
        r"10-[KQ]|8-K|sec\.gov|edgar", re.I)),
    ("poster", re.compile(
        r"poster|ASCO|ESMO|AACR|abstract", re.I)),
    ("investor_presentation", re.compile(
        r"investor|corporate.presentation|earnings|JPM|conference", re.I)),
    ("press_release", re.compile(
        r"press.release|announces|announce|data", re.I)),
]


# --------------------------------------------------------------------------
# Date extraction → ISO 8601 (YYYY-MM-DD)
# --------------------------------------------------------------------------

_MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

# Ordered by specificity — most precise first
_DATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # "January 15, 2025" / "Jan 15, 2025"
    (re.compile(
        r"(January|February|March|April|May|June|July|August|September|October|November|December"
        r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{1,2}),?\s+(\d{4})", re.I),
     "month_day_year"),
    # "2025-01-15" / "2025/01/15"
    (re.compile(r"(\d{4})[/-](\d{2})[/-](\d{2})"), "ymd"),
    # "01/15/2025" / "01-15-2025"
    (re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})"), "mdy"),
    # "Jan 2025" / "January 2025" (month only — day defaults to 1)
    (re.compile(
        r"(January|February|March|April|May|June|July|August|September|October|November|December"
        r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{4})", re.I),
     "month_year"),
]

# URL path date: /2025/01/ or /2025-01/
_URL_DATE_RE = re.compile(r"/(\d{4})[/-](\d{2})(?:/|$)")


def _parse_date_match(match: re.Match, fmt: str) -> str | None:
    """Convert a regex match into YYYY-MM-DD, or None if invalid."""
    try:
        if fmt == "month_day_year":
            month = _MONTH_NAMES[match.group(1).lower()]
            day = int(match.group(2))
            year = int(match.group(3))
        elif fmt == "ymd":
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        elif fmt == "mdy":
            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        elif fmt == "month_year":
            month = _MONTH_NAMES[match.group(1).lower()]
            year = int(match.group(2))
            day = 1
        else:
            return None

        # Validate by constructing a real date
        from datetime import date
        return date(year, month, day).isoformat()
    except (ValueError, KeyError):
        return None


def extract_date_iso(text: str, url: str = "") -> str | None:
    """Extract a date from text or URL and return as YYYY-MM-DD, or None.

    Checks page text first (most precise), then falls back to URL path.
    """
    # 1. Search page text
    for pattern, fmt in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            iso = _parse_date_match(match, fmt)
            if iso:
                return iso

    # 2. Fall back to URL (path segments and filename)
    if url:
        # Check /2025/01/ style path segments
        match = _URL_DATE_RE.search(url)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            if 2000 <= year <= 2099 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-01"

        # Check filename — first raw (for YYYY-MM-DD), then normalized (for text dates)
        # Raw catches "2024-09-14_ESMO.pdf", normalized catches "February_26_2026"
        filename = urlparse(url).path.rsplit("/", 1)[-1]
        for pattern, fmt in _DATE_PATTERNS:
            match = pattern.search(filename)
            if match:
                iso = _parse_date_match(match, fmt)
                if iso:
                    return iso
        filename_text = filename.replace("_", " ").replace("-", " ")
        for pattern, fmt in _DATE_PATTERNS:
            match = pattern.search(filename_text)
            if match:
                iso = _parse_date_match(match, fmt)
                if iso:
                    return iso

    return None


def _extract_link_title(link) -> str:
    """Extract a human-readable title from a BeautifulSoup <a> element."""
    text = link.get_text(strip=True)
    if text and len(text) > 3:
        return text
    if link.get("title"):
        return link["title"]
    if link.get("aria-label"):
        return link["aria-label"]
    parent = link.parent
    if parent:
        parent_text = parent.get_text(strip=True)
        if parent_text and len(parent_text) < 200:
            return parent_text
    href = link.get("href", "")
    filename = Path(urlparse(href).path).stem
    return filename.replace("-", " ").replace("_", " ").title()


def classify_doc_type(url: str, title: str) -> str:
    """Classify a document by URL and title text.

    Checked in priority order — first match wins.
    """
    text = f"{url} {title}"
    for doc_type, pattern in _DOC_TYPE_RULES:
        if pattern.search(text):
            return doc_type
    return "other"


_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class OncologyScraper:
    """Scraper for oncology company IR pages.

    Uses curl-cffi with Chrome TLS impersonation to bypass Q4/Akamai
    bot detection. Adds multi-page support, PPTX detection, and hash dedup.
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.session = cffi_requests.Session(impersonate="chrome124")
        self.session.headers.update(_DEFAULT_HEADERS)
        self.metadata = self._load_metadata()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._save_metadata()
        self.session.close()

    # ------------------------------------------------------------------
    # Metadata persistence
    # ------------------------------------------------------------------

    def _load_metadata(self) -> dict:
        """Load metadata from disk. Keyed by document URL for O(1) lookups."""
        if METADATA_FILE.exists():
            try:
                data = json.loads(METADATA_FILE.read_text())
                # Separate errors list from document metadata
                self.errors = data.pop("_errors", [])
                return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load metadata: %s", e)
        self.errors = []
        return {}

    def _save_metadata(self) -> None:
        """Persist metadata to disk (including errors list)."""
        METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = dict(self.metadata)
        if self.errors:
            data["_errors"] = self.errors
        METADATA_FILE.write_text(json.dumps(data, indent=2))

    def _save_document_index(self, ticker: str) -> None:
        """Write per-ticker document_index.json mapping filename → provenance.

        Output: data/companies/{TICKER}/metadata/document_index.json
        Keyed by PDF filename for O(1) lookup from downstream pipeline steps.
        """
        ticker = ticker.upper()
        index = {}
        for url, meta in self.metadata.items():
            if url.startswith("_"):
                continue
            if meta.get("ticker", "").upper() != ticker:
                continue
            file_path = meta.get("file_path", "")
            filename = Path(file_path).name if file_path else ""
            if not filename:
                continue
            index[filename] = {
                "source_url": url,
                "title": meta.get("title"),
                "date": meta.get("date"),
                "doc_type": meta.get("doc_type"),
                "sha256": meta.get("sha256"),
                "file_size_bytes": meta.get("file_size_bytes"),
                "scraped_at": meta.get("scraped_at"),
                "source_page": meta.get("source_page"),
                "page_type": meta.get("page_type"),
            }

        out_dir = COMPANIES_DIR / ticker / "metadata"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "document_index.json"
        out_path.write_text(json.dumps(index, indent=2))
        logger.debug("Wrote document index: %s (%d docs)", out_path, len(index))

    # ------------------------------------------------------------------
    # HTTP with retry
    # ------------------------------------------------------------------

    def _request_with_retry(self, url: str, timeout: float | None = None):
        """GET with 3 retries, exponential backoff, 403/429/timeout handling.

        Uses curl-cffi session with Chrome TLS impersonation.
        Raises the last exception if all retries fail.
        """
        timeout = timeout or self.timeout
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=timeout)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", BACKOFF_DELAYS[attempt]))
                    logger.warning("429 Too Many Requests for %s, waiting %ds", url, retry_after)
                    time.sleep(retry_after)
                    continue

                if response.status_code == 403:
                    logger.warning("403 Forbidden for %s (attempt %d/%d)", url, attempt + 1, MAX_RETRIES)
                    time.sleep(BACKOFF_DELAYS[attempt])
                    continue

                response.raise_for_status()
                return response

            except RequestsError as e:
                last_exc = e
                msg = str(e)
                if "timeout" in msg.lower() or "timed out" in msg.lower():
                    logger.warning("Timeout for %s (attempt %d/%d)", url, attempt + 1, MAX_RETRIES)
                else:
                    logger.warning("Request error for %s: %s (attempt %d/%d)", url, e, attempt + 1, MAX_RETRIES)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_DELAYS[attempt])
            except Exception as e:
                last_exc = e
                logger.warning("Unexpected error for %s: %s (attempt %d/%d)", url, e, attempt + 1, MAX_RETRIES)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_DELAYS[attempt])

        raise last_exc or RequestsError(f"Failed after {MAX_RETRIES} retries: {url}")

    def _log_error(self, url: str, ticker: str, error: str) -> None:
        """Append an error entry to the errors list in metadata."""
        self.errors.append({
            "url": url,
            "ticker": ticker,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ------------------------------------------------------------------
    # Document discovery
    # ------------------------------------------------------------------

    def _is_document_link(self, href: str) -> bool:
        """Check if a URL points to a PDF or PPTX.

        Strips URL fragments (#new_tab) and query strings before checking
        extensions, so links like 'file.pdf#new_tab' or 'file.pdf?dl=1'
        are correctly detected.
        """
        href_lower = href.lower()
        # Strip fragment and query string for extension checks
        clean = href_lower.split("#")[0].split("?")[0]
        return (
            clean.endswith(".pdf")
            or clean.endswith(".pptx")
            or clean.endswith(".ppt")
            or "/static-files/" in href_lower
            or "/pdf/" in href_lower
        )

    # Regex for PDF/PPTX URLs embedded in JSON, data attributes, or inline JS.
    # Excludes backslash so URLs stop before JSON escapes like \"
    _EMBEDDED_PDF_RE = re.compile(
        r'(https?://[^\s"\'<>\\]+\.(?:pdf|pptx|ppt))',
        re.IGNORECASE,
    )

    def _extract_docs_from_html(self, html: str, base_url: str) -> list[dict]:
        """Extract document links (PDF/PPTX) from HTML content.

        First scans <a href> tags (preferred — gives us title + date context).
        Falls back to regex extraction from raw HTML for sites that embed PDF
        URLs in JSON data, script tags, or data-* attributes (e.g. Sanity CMS).

        Returns:
            List of dicts with keys: url, title, date, source_page, file_type
        """
        soup = BeautifulSoup(html, "html.parser")
        results = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if not self._is_document_link(href):
                continue

            full_url = urljoin(base_url, href)
            # Strip URL fragments (#new_tab etc.) — they pollute filenames and dedup
            full_url = full_url.split("#")[0]

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title = _extract_link_title(link)
            context_text = link.parent.get_text() if link.parent else ""
            date = extract_date_iso(context_text, full_url)

            # Check cleaned href for file type
            clean_href = href.lower().split("#")[0].split("?")[0]
            if clean_href.endswith(".pptx") or clean_href.endswith(".ppt"):
                file_type = "pptx"
            else:
                file_type = "pdf"

            results.append({
                "url": full_url,
                "title": title,
                "date": date,
                "source_page": base_url,
                "file_type": file_type,
            })

        # Fallback: regex-extract PDF URLs from raw HTML (catches Sanity CDN,
        # Next.js __NEXT_DATA__, data-* attrs, inline JS, etc.)
        if not results:
            # Unescape double-encoded JSON (\\\" → \") so regex can parse it
            unescaped = html.replace('\\"', '"')

            # Pre-build a map of CDN URL → original filename from nearby JSON
            # e.g. "filename":"Something.pdf","mimeType":"...","url":"https://cdn..."
            _filename_re = re.compile(
                r'"filename"\s*:\s*"([^"]+\.(?:pdf|pptx|ppt))"'
                r'.{0,200}?'
                r'"url"\s*:\s*"(https?://[^"]+\.(?:pdf|pptx|ppt))"',
                re.IGNORECASE,
            )
            name_for_url = {}
            for m in _filename_re.finditer(unescaped):
                name_for_url[m.group(2)] = m.group(1)

            for match in self._EMBEDDED_PDF_RE.finditer(unescaped):
                url = match.group(1).split("#")[0]
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                clean = url.lower().split("?")[0]
                if clean.endswith(".pptx") or clean.endswith(".ppt"):
                    file_type = "pptx"
                else:
                    file_type = "pdf"

                # Use original filename from JSON if available, else URL path stem
                orig_name = name_for_url.get(url, "")
                if orig_name:
                    title = Path(orig_name).stem.replace("-", " ").replace("_", " ")
                    date = extract_date_iso(title, url)
                else:
                    filename = Path(urlparse(url).path).stem
                    title = filename.replace("-", " ").replace("_", " ").title()
                    date = extract_date_iso("", url)

                results.append({
                    "url": url,
                    "title": title,
                    "date": date,
                    "source_page": base_url,
                    "file_type": file_type,
                })

            if results:
                logger.info("    Fallback regex extracted %d doc(s) from embedded data", len(results))

        return results

    # ------------------------------------------------------------------
    # Playwright fallback for JS-rendered pages
    # ------------------------------------------------------------------

    def _fetch_rendered_html(self, url: str, wait_seconds: float = 5.0) -> str | None:
        """Launch headless Chromium, load a page, wait for JS to render, return HTML.

        Used as a fallback for pages where curl-cffi gets the shell HTML but
        document links are loaded dynamically (Notified, React/Next.js sites, etc.).

        Returns the fully rendered HTML string, or None on failure.
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not installed — cannot render JS pages. "
                           "Install with: pip install playwright && playwright install chromium")
            return None

        logger.info("    [playwright] Launching headless Chromium for %s", url)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/132.0.0.0 Safari/537.36"
                    ),
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                # Additional wait for late-loading content (AJAX, lazy widgets)
                page.wait_for_timeout(int(wait_seconds * 1000))
                html = page.content()
                browser.close()

            logger.info("    [playwright] Got %d bytes of rendered HTML", len(html))
            return html
        except Exception as e:
            logger.error("    [playwright] Failed to render %s: %s", url, e)
            return None

    def find_documents_browser(self, url: str) -> list[dict]:
        """Find PDF/PPTX links on a JS-rendered page using Playwright.

        Falls back to curl-cffi if Playwright is unavailable.
        Returns the same list[dict] format as find_documents().
        """
        html = self._fetch_rendered_html(url)
        if html is None:
            logger.warning("    Browser fallback failed, trying curl-cffi for %s", url)
            return self.find_documents(url)
        return self._extract_docs_from_html(html, url)

    def _find_documents_eprints(self, url: str) -> list[dict]:
        """Scrape an EPrints 3 repository (e.g. OAK Novartis).

        EPrints exposes several access patterns:
          - /cgi/latest_tool?n=100  — latest N items
          - /view/year/YYYY.type.html — browse by year (most comprehensive)
          - /NNNNN/ — individual item pages with PDF downloads

        Strategy:
          1. Fetch /cgi/latest_tool?n=100 for the most recent items
          2. Also crawl /view/year/ for 2024-2026 to get broader coverage
          3. For each listing, extract item page URLs (/NNNNN/)
          4. Crawl item pages for actual PDF download links

        Returns list of doc dicts with PDF URLs, titles, and dates.
        """
        base_url = url.rsplit("/cgi/", 1)[0] if "/cgi/" in url else url.rstrip("/")
        all_docs = []
        seen_urls = set()
        seen_items = set()

        # Build list of pages to scan: latest_tool + year browse views
        listing_urls = [
            f"{base_url}/cgi/latest_tool?n=100",
        ]
        for year in EVENT_YEARS:
            listing_urls.append(f"{base_url}/view/year/{year}.type.html")

        for listing_url in listing_urls:
            try:
                response = self._request_with_retry(listing_url)
            except Exception as e:
                logger.warning("EPrints fetch failed for %s: %s", listing_url, e)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # EPrints item pages are at /NNNNN/ — find all links to them
            item_urls = set()
            for link in soup.find_all("a", href=True):
                href = link["href"]
                full = urljoin(listing_url, href)
                # Match EPrints item pattern: /12345/ or /12345
                if re.match(rf'^{re.escape(base_url)}/\d+/?$', full):
                    normalized = full.rstrip("/") + "/"
                    if normalized not in seen_items:
                        item_urls.add(normalized)
                        seen_items.add(normalized)

            # Also grab any direct PDF links on the listing page
            page_docs = self._extract_docs_from_html(response.text, listing_url)
            for doc in page_docs:
                if doc["url"] not in seen_urls:
                    seen_urls.add(doc["url"])
                    all_docs.append(doc)

            logger.info("    EPrints %s: %d new items, %d direct PDFs",
                        listing_url.split(base_url)[-1][:40], len(item_urls), len(page_docs))

            # Crawl item detail pages for PDFs (cap at 50 per listing to be respectful)
            for item_url in list(item_urls)[:50]:
                time.sleep(1)
                try:
                    item_resp = self._request_with_retry(item_url)
                    item_docs = self._extract_docs_from_html(item_resp.text, item_url)
                    for doc in item_docs:
                        if doc["url"] not in seen_urls:
                            seen_urls.add(doc["url"])
                            # Try to get better title from item page
                            item_soup = BeautifulSoup(item_resp.text, "html.parser")
                            title_tag = item_soup.find("h1") or item_soup.find("title")
                            if title_tag and not doc.get("title"):
                                doc["title"] = title_tag.get_text(strip=True)
                            all_docs.append(doc)
                except Exception as e:
                    logger.warning("    EPrints item fetch failed %s: %s", item_url, e)

            time.sleep(PAGE_DELAY)

        logger.info("    EPrints total: %d document(s) from %d item pages",
                     len(all_docs), len(seen_items))
        return all_docs

    def find_documents(self, url: str, platform: str = "standard") -> list[dict]:
        """Fetch a page and find PDF/PPTX links on it.

        If platform is 'js_rendered', uses Playwright headless browser.
        If platform is 'eprints', uses EPrints repository crawler.
        Otherwise uses curl-cffi.
        """
        if platform == "js_rendered":
            return self.find_documents_browser(url)

        if platform == "eprints":
            return self._find_documents_eprints(url)

        try:
            response = self._request_with_retry(url)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return []

        docs = self._extract_docs_from_html(response.text, url)

        # Auto-fallback: if curl-cffi found 0 docs on a page that returned
        # HTML successfully, and the page config says use_browser, try Playwright
        if not docs and platform in ("notified",):
            logger.info("    curl-cffi found 0 docs on %s platform, trying Playwright", platform)
            docs = self.find_documents_browser(url)

        return docs

    # ------------------------------------------------------------------
    # Year-filtered events crawling
    # ------------------------------------------------------------------

    def _find_events_all_years(self, url: str, platform: str) -> list[dict]:
        """Find documents across EVENT_YEARS on events pages.

        Q4 platform: appends ?year=YYYY to the URL.
        Standard platform: detects webDriver AJAX widget and crawls per-year.
        Other platforms: falls back to single-page scan.

        Deduplicates results by URL across all years.
        """
        if platform == "q4":
            return self._find_events_q4_years(url)
        elif platform == "standard":
            return self._find_events_standard_years(url)
        else:
            # Notified or unknown — just scan the page as-is
            return self.find_documents(url, platform)

    def _find_events_q4_years(self, url: str) -> list[dict]:
        """Q4 platform: scan events page for each year via ?year=YYYY."""
        all_docs = []
        seen_urls = set()

        for i, year in enumerate(EVENT_YEARS):
            if i > 0:
                time.sleep(PAGE_DELAY)

            sep = "&" if "?" in url else "?"
            year_url = f"{url}{sep}year={year}"
            logger.info("    Year %d: %s", year, year_url)

            docs = self.find_documents(year_url, "q4")
            new_count = 0
            for doc in docs:
                if doc["url"] not in seen_urls:
                    seen_urls.add(doc["url"])
                    all_docs.append(doc)
                    new_count += 1
            logger.info("    Year %d: %d new document(s)", year, new_count)

        return all_docs

    def _find_events_standard_years(self, url: str) -> list[dict]:
        """Standard platform: use webDriver AJAX endpoint for year filtering.

        Detects the wd_events widget on the page, then calls the AJAX endpoint
        for each year to get event listing items. Parses event items for direct
        PDF links and event detail page URLs (?item=N), crawling those for PDFs.

        Falls back to single-page scan if no webDriver widget is detected.
        """
        # Fetch base page to detect widget and get current-year docs
        try:
            response = self._request_with_retry(url)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return []

        html = response.text
        all_docs = []
        seen_urls = set()

        # Get docs from the base page HTML
        base_docs = self._extract_docs_from_html(html, url)
        for doc in base_docs:
            seen_urls.add(doc["url"])
            all_docs.append(doc)

        # Detect webDriver widget
        if "wd_events" not in html and "widget_form_base" not in html:
            logger.debug("No webDriver widget on %s, using base page only", url)
            return all_docs

        # Extract widget s parameter from hidden form field or JS config
        # Patterns: <input name="s" value="19">, "s": "19", s: "19", s: 19
        s_match = re.search(r'name="s"\s+value="(\d+)"', html)
        if not s_match:
            s_match = re.search(r'(?:^|[,{}\s])s\s*:\s*"?(\d+)', html, re.MULTILINE)
        if not s_match:
            logger.warning("Could not find webDriver widget ID on %s", url)
            return all_docs

        s_param = s_match.group(1)
        logger.info("    Detected webDriver widget (s=%s), crawling years %s", s_param, EVENT_YEARS)

        ajax_base = url.rstrip("/") + "/index.php"

        for year in EVENT_YEARS:
            time.sleep(PAGE_DELAY)

            ajax_url = (
                f"{ajax_base}?s={s_param}&ajax=ajax&op=list"
                f"&direction=past&limit_date={year}-12-00"
            )
            logger.info("    AJAX year %d", year)

            try:
                resp = self._request_with_retry(ajax_url)
                data = resp.json()
            except Exception as e:
                logger.warning("    AJAX failed for year %d: %s", year, e)
                continue

            items = data.get("items", [])
            detail_urls = []

            for item in items:
                content_html = item.get("content", "")
                if not content_html:
                    continue

                item_soup = BeautifulSoup(content_html, "html.parser")

                # Direct document links in the event listing
                for link in item_soup.find_all("a", href=True):
                    href = link["href"]
                    if self._is_document_link(href):
                        full_url = urljoin(url, href)
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            title = _extract_link_title(link)
                            context = link.parent.get_text() if link.parent else ""
                            date = extract_date_iso(context, full_url)
                            href_lower = href.lower()
                            file_type = "pptx" if href_lower.endswith((".pptx", ".ppt")) else "pdf"
                            all_docs.append({
                                "url": full_url, "title": title, "date": date,
                                "source_page": url, "file_type": file_type,
                            })

                # Collect event detail page links (?item=N)
                for link in item_soup.find_all("a", href=True):
                    href = link["href"]
                    if "item=" in href and not self._is_document_link(href):
                        detail_url = urljoin(url, href)
                        if detail_url not in detail_urls:
                            detail_urls.append(detail_url)

            # Crawl event detail pages for PDFs
            for detail_url in detail_urls:
                time.sleep(1)
                detail_docs = self.find_documents(detail_url, "standard")
                for doc in detail_docs:
                    if doc["url"] not in seen_urls:
                        seen_urls.add(doc["url"])
                        doc["source_page"] = detail_url
                        all_docs.append(doc)
                        logger.info("    Detail page doc: %s", doc["title"][:60] if doc["title"] else doc["url"][:60])

        logger.info("    Year filter total: %d unique document(s)", len(all_docs))
        return all_docs

    # ------------------------------------------------------------------
    # Download with dedup
    # ------------------------------------------------------------------

    def _url_already_seen(self, url: str) -> bool:
        """Fast O(1) check: have we already downloaded this URL?"""
        return url in self.metadata

    def _hash_already_seen(self, sha256: str) -> str | None:
        """Check if we already have a file with this hash.

        Returns the original URL if found, None otherwise.
        """
        for existing_url, meta in self.metadata.items():
            if meta.get("sha256") == sha256:
                return existing_url
        return None

    def download_document(
        self,
        url: str,
        ticker: str,
        title: str = "",
        file_type: str = "pdf",
        date: str | None = None,
        dry_run: bool = False,
    ) -> dict | None:
        """Download a document with two-tier dedup.

        1. Check URL against metadata (fast dict lookup)
        2. Download to memory
        3. Check SHA-256 hash against all known hashes
        4. Save to disk only if both checks pass

        Returns:
            Metadata dict for the downloaded file, or None if skipped/failed.
        """
        # Tier 1: URL dedup
        if self._url_already_seen(url):
            logger.debug("Skipping (URL seen): %s", url)
            return None

        doc_type = classify_doc_type(url, title)

        # If no date from page context, try the URL itself
        if not date:
            date = extract_date_iso("", url)

        if dry_run:
            return {"url": url, "title": title, "file_type": file_type, "doc_type": doc_type, "date": date, "status": "dry_run"}

        # Download to memory
        try:
            response = self._request_with_retry(url)
        except Exception as e:
            logger.error("Download failed for %s: %s", url, e)
            self._log_error(url, ticker, str(e))
            return None

        content = response.content
        if not content:
            logger.warning("Empty response for %s", url)
            return None

        # Tier 2: SHA-256 hash dedup
        sha256 = hashlib.sha256(content).hexdigest()
        duplicate_url = self._hash_already_seen(sha256)
        if duplicate_url:
            logger.info("Skipping (hash match with %s): %s", duplicate_url, url)
            # Record in metadata so we don't re-download
            self.metadata[url] = {
                "ticker": ticker.upper(),
                "title": title,
                "sha256": sha256,
                "duplicate_of": duplicate_url,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            return None

        # Save to disk
        download_dir = COMPANIES_DIR / ticker.upper() / "sources"
        download_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        if not filename or filename == "":
            filename = f"document_{hash(url) % 10000}.{file_type}"

        # Ensure correct extension
        if not any(filename.lower().endswith(ext) for ext in (".pdf", ".pptx", ".ppt")):
            filename = f"{filename}.{file_type}"

        save_path = download_dir / filename

        # Avoid overwriting existing files
        if save_path.exists():
            stem = save_path.stem
            suffix = save_path.suffix
            n = 1
            while save_path.exists():
                save_path = download_dir / f"{stem}_{n}{suffix}"
                n += 1

        save_path.write_bytes(content)
        size_kb = len(content) // 1024
        logger.info("Downloaded: %s (%d KB) -> %s", url, size_kb, save_path.name)

        # Record metadata
        meta = {
            "ticker": ticker.upper(),
            "title": title,
            "date": date,
            "file_type": file_type,
            "doc_type": doc_type,
            "sha256": sha256,
            "file_path": str(save_path),
            "file_size_bytes": len(content),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata[url] = meta
        return meta

    # ------------------------------------------------------------------
    # Company-level scraping
    # ------------------------------------------------------------------

    def scrape_company(self, ticker: str, dry_run: bool = False) -> list[dict]:
        """Scrape all configured pages for one company.

        Args:
            ticker: Company ticker symbol
            dry_run: If True, find links but don't download

        Returns:
            List of metadata dicts for downloaded/found documents
        """
        ticker = ticker.upper()
        config = get_oncology_config(ticker)
        if not config:
            logger.error("No oncology config for %s", ticker)
            return []

        logger.info("Scraping %s (%s) — %d page(s)", ticker, config["name"], len(config["pages"]))
        all_results = []

        # Process direct_links first (for JS-rendered pages like Notified)
        for url in config.get("direct_links", []):
            href_lower = url.lower()
            if href_lower.endswith(".pptx") or href_lower.endswith(".ppt"):
                file_type = "pptx"
            else:
                file_type = "pdf"
            result = self.download_document(
                url=url,
                ticker=ticker,
                title="",
                file_type=file_type,
                dry_run=dry_run,
            )
            if result:
                result["source_page"] = "direct_link"
                result["page_type"] = "direct"
                all_results.append(result)

        for i, page in enumerate(config["pages"]):
            if i > 0:
                time.sleep(PAGE_DELAY)

            page_url = page["url"]
            platform = page.get("platform", "standard")
            page_type = page.get("type", "unknown")
            content_type = page.get("content_type", "documents")
            use_browser = page.get("use_browser", False)

            # Skip text-only pages (press releases) — no PDFs to download
            # TODO: text content scraper for press releases
            if content_type == "text":
                logger.debug("  [%s] %s — skipping (content_type=text)", page_type, page_url)
                continue

            # Override platform if page explicitly requests browser rendering
            if use_browser:
                platform = "js_rendered"

            logger.info("  [%s] %s (%s)", page_type, page_url, platform)

            # Events pages get year-filter crawling (2024-2026)
            if page_type == "events":
                documents = self._find_events_all_years(page_url, platform)
            else:
                documents = self.find_documents(page_url, platform)
            logger.info("  Found %d document(s)", len(documents))

            for doc in documents:
                result = self.download_document(
                    url=doc["url"],
                    ticker=ticker,
                    title=doc.get("title", ""),
                    file_type=doc.get("file_type", "pdf"),
                    date=doc.get("date"),
                    dry_run=dry_run,
                )
                if result:
                    result["source_page"] = page_url
                    result["page_type"] = page_type
                    all_results.append(result)

        # Write per-ticker document index for downstream provenance
        self._save_document_index(ticker)

        return all_results

    def scrape_all(self, dry_run: bool = False) -> dict[str, list[dict]]:
        """Scrape all 13 oncology companies.

        Returns:
            Dict mapping ticker -> list of metadata dicts
        """
        results = {}
        tickers = get_all_oncology_tickers()

        for i, ticker in enumerate(tickers):
            if i > 0:
                time.sleep(PAGE_DELAY)
            try:
                results[ticker] = self.scrape_company(ticker, dry_run=dry_run)
            except Exception as e:
                logger.error("Failed to scrape %s, continuing: %s", ticker, e)
                self._log_error("", ticker, f"scrape_company failed: {e}")
                results[ticker] = []

        return results

    def probe_pages(self, ticker: str | None = None) -> list[dict]:
        """Probe each configured page URL and report status + link counts.

        Uses a short 10s timeout with no retries — designed to finish fast
        so you can see which sites respond before committing to a full scrape.

        Returns a list of result dicts, one per page, with:
            ticker, page_type, url, status_code, doc_count, error
        """
        PROBE_TIMEOUT = 10  # seconds — fast fail for probing

        if ticker:
            tickers = [ticker.upper()]
        else:
            tickers = get_all_oncology_tickers()

        results = []
        for t in tickers:
            config = get_oncology_config(t)
            if not config:
                continue

            for i, page in enumerate(config["pages"]):
                if results:
                    time.sleep(1)  # lighter delay for probing

                page_url = page["url"]
                page_type = page.get("type", "unknown")
                entry = {
                    "ticker": t,
                    "page_type": page_type,
                    "url": page_url,
                    "status_code": None,
                    "doc_count": 0,
                    "error": None,
                }

                try:
                    # Single attempt, short timeout — no retries for probe
                    response = self.session.get(page_url, timeout=PROBE_TIMEOUT)
                    entry["status_code"] = response.status_code
                    if response.status_code < 400:
                        soup = BeautifulSoup(response.text, "html.parser")
                        count = sum(
                            1 for link in soup.find_all("a", href=True)
                            if self._is_document_link(link["href"])
                        )
                        entry["doc_count"] = count
                except Exception as e:
                    msg = str(e)
                    if "resolve" in msg.lower() or "nodename" in msg.lower():
                        entry["error"] = "DNS failure"
                    elif "timeout" in msg.lower() or "timed out" in msg.lower():
                        entry["error"] = "timeout"
                    else:
                        entry["error"] = msg[:40]

                results.append(entry)

        return results

    def get_stats(self) -> dict:
        """Get summary statistics from metadata."""
        if not self.metadata:
            return {"total_documents": 0, "companies": {}, "duplicates": 0}

        companies = {}
        duplicates = 0
        total_size = 0

        for url, meta in self.metadata.items():
            ticker = meta.get("ticker", "UNKNOWN")
            if ticker not in companies:
                companies[ticker] = {"documents": 0, "size_bytes": 0}
            companies[ticker]["documents"] += 1
            companies[ticker]["size_bytes"] += meta.get("file_size_bytes", 0)
            total_size += meta.get("file_size_bytes", 0)
            if meta.get("duplicate_of"):
                duplicates += 1

        return {
            "total_documents": len(self.metadata),
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "duplicates": duplicates,
            "companies": companies,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def scrape_oncology_company(ticker: str, dry_run: bool = False) -> list[dict]:
    """Scrape a single oncology company's IR pages."""
    with OncologyScraper() as scraper:
        return scraper.scrape_company(ticker, dry_run=dry_run)


def scrape_all_oncology(dry_run: bool = False) -> dict[str, list[dict]]:
    """Scrape all oncology companies' IR pages."""
    with OncologyScraper() as scraper:
        return scraper.scrape_all(dry_run=dry_run)
