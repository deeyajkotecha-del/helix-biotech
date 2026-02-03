"""
IR Scraper Service
Scrapes investor relations pages to discover presentations,
SEC filings, and other investor documents.
Ported from cli/src/services/ir-scraper.ts
"""

import re
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal


@dataclass
class IRDocument:
    """An investor relations document."""
    id: str
    title: str
    url: str
    date: str
    date_obj: datetime
    doc_type: Literal['presentation', 'poster', 'sec-filing', 'webcast', 'other']
    event: str = ""
    file_size: str = ""
    file_size_bytes: int = 0
    category: str = ""
    downloaded: bool = False
    extracted_text: bool = False


@dataclass
class IRScraperResult:
    """Result from scraping IR documents."""
    ticker: str
    company_name: str
    ir_base_url: str
    documents: list[IRDocument]
    scraped_at: str
    total_documents: int
    documents_by_year: dict[str, int] = field(default_factory=dict)


@dataclass
class IRSiteConfig:
    """Configuration for an IR site."""
    base_url: str
    events_path: str
    download_library_path: str = ""
    sec_filings_path: str = ""
    news_path: str = ""


# Known IR site configurations
IR_CONFIGS: dict[str, IRSiteConfig] = {
    'ARWR': IRSiteConfig(
        base_url='https://ir.arrowheadpharma.com',
        events_path='/events-and-presentations',
        download_library_path='/download-library',
        sec_filings_path='/financials-filings',
        news_path='https://arrowheadpharma.com/newsroom/',
    ),
}

# Company names
COMPANY_NAMES: dict[str, str] = {
    'ARWR': 'Arrowhead Pharmaceuticals',
}

# Month name to number mapping
MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

# HTTP headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def parse_file_size(size_str: str) -> int:
    """Parse file size string to bytes."""
    if not size_str:
        return 0
    match = re.match(r'([\d.]+)\s*(KB|MB|GB)', size_str, re.IGNORECASE)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {'KB': 1024, 'MB': 1024 * 1024, 'GB': 1024 * 1024 * 1024}
    return int(value * multipliers.get(unit, 0))


def parse_date(date_str: str) -> datetime:
    """Parse various date formats into datetime."""
    if not date_str:
        return datetime.now()

    cleaned = date_str.strip().replace(',', '')

    # Try standard parsing first
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        pass

    # Try common formats
    for fmt in ['%B %d %Y', '%b %d %Y', '%m/%d/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    # Try parsing "Apr 15 2025" style
    match = re.match(r'(\w+)\s+(\d+)\s+(\d{4})', cleaned, re.IGNORECASE)
    if match:
        month_str = match.group(1).lower()[:3]
        month = MONTHS.get(month_str)
        if month:
            return datetime(int(match.group(3)), month, int(match.group(2)))

    return datetime.now()


def infer_document_type(title: str, url: str) -> Literal['presentation', 'poster', 'sec-filing', 'webcast', 'other']:
    """Infer document type from title and URL."""
    title_lower = title.lower()
    url_lower = url.lower()

    if 'poster' in title_lower or 'poster' in url_lower:
        return 'poster'
    if 'webcast' in title_lower or 'webcast' in url_lower:
        return 'webcast'
    if any(x in title_lower for x in ['10-k', '10-q', '8-k']):
        return 'sec-filing'
    if any(x in title_lower for x in ['presentation', 'corporate', 'conference', 'congress', 'study', 'data']):
        return 'presentation'

    return 'other'


def generate_document_id(url: str, title: str) -> str:
    """Generate unique document ID from URL or title."""
    # Extract UUID from static-files URL
    uuid_match = re.search(r'static-files/([a-f0-9-]+)', url, re.IGNORECASE)
    if uuid_match:
        return uuid_match.group(1)

    # Generate from title
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
    slug = slug.strip('-')[:50]
    return slug or hashlib.md5(url.encode()).hexdigest()[:12]


def scrape_download_library(config: IRSiteConfig) -> list[IRDocument]:
    """Scrape the download library page for documents."""
    documents: list[IRDocument] = []
    seen_ids: set[str] = set()

    if not config.download_library_path:
        return documents

    page = 0
    has_more = True

    while has_more and page <= 10:
        try:
            url = f"{config.base_url}{config.download_library_path}"
            if page > 0:
                url += f"?page={page}"

            print(f"[IR Scraper] Fetching download library page {page}: {url}")

            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            found_docs = 0

            # ARWR uses table rows with specific NIR widget classes
            for row in soup.find_all('tr'):
                # Get date from NIR asset date field
                date_field = row.select_one('.field-nir-asset-date .field__item')
                date_str = date_field.get_text(strip=True) if date_field else ''

                # Get title link from NIR asset title field
                title_link = row.select_one('.field-nir-asset-title a[href*="/static-files/"]')
                href = ''
                title = ''

                if title_link:
                    href = title_link.get('href', '')
                    title = title_link.get_text(strip=True)

                # Fallback: look for any static-files link in the row
                if not href:
                    any_link = row.select_one('a[href*="/static-files/"]')
                    if any_link:
                        href = any_link.get('href', '')
                        if not title or len(title) < 3:
                            title = any_link.get_text(strip=True)

                # Skip generic titles
                if title and title.lower() in ['view presentation', 'pdf']:
                    static_link = row.select_one('a[href*="/static-files/"]')
                    if static_link:
                        better_title = static_link.get('title', '')
                        if better_title:
                            title = re.sub(r'\.pdf$', '', better_title, flags=re.IGNORECASE)

                # Get file size
                filesize_elem = row.select_one('.filesize')
                file_size = filesize_elem.get_text(strip=True) if filesize_elem else ''

                if href and title and len(title) > 3:
                    full_url = href if href.startswith('http') else f"{config.base_url}{href}"
                    doc_id = generate_document_id(full_url, title)

                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        found_docs += 1
                        documents.append(IRDocument(
                            id=doc_id,
                            title=' '.join(title.split()),
                            url=full_url,
                            date=date_str or 'Unknown',
                            date_obj=parse_date(date_str),
                            doc_type=infer_document_type(title, full_url),
                            file_size=file_size,
                            file_size_bytes=parse_file_size(file_size),
                            category='download-library',
                        ))

            print(f"[IR Scraper] Found {found_docs} documents on page {page}")

            # Check for next page
            next_page_links = soup.select(f'a[href*="page="]')
            has_next = any(
                re.search(r'page=(\d+)', link.get('href', ''))
                and int(re.search(r'page=(\d+)', link.get('href', '')).group(1)) > page
                for link in next_page_links
                if re.search(r'page=(\d+)', link.get('href', ''))
            )

            has_more = found_docs > 0 and has_next
            page += 1

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"[IR Scraper] Error scraping page {page}: {e}")
            has_more = False

    return documents


def scrape_events_page_for_year(config: IRSiteConfig, year: int) -> list[IRDocument]:
    """Scrape a single year's events page."""
    documents: list[IRDocument] = []

    try:
        url = f"{config.base_url}{config.events_path}?year={year}"
        print(f"[IR Scraper] Fetching events for {year}: {url}")

        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all event items
        event_selectors = '.nir-widget--event, .module_item, .event-item, article'
        for event_el in soup.select(event_selectors):
            # Get event title/name
            title_el = event_el.select_one('.nir-widget--field--title, .module_headline, .event-title, h3, h4')
            event_name = title_el.get_text(strip=True) if title_el else ''

            # Get date
            date_el = event_el.select_one('.nir-widget--field--date, .module_date, .date, time')
            date_str = date_el.get_text(strip=True) if date_el else ''

            if not date_str:
                event_text = event_el.get_text()
                date_match = re.search(
                    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}',
                    event_text, re.IGNORECASE
                )
                if date_match:
                    date_str = date_match.group(0)

            # Find all PDF/document links within this event
            for link in event_el.select('a[href*="/static-files/"], a[href*=".pdf"]'):
                href = link.get('href', '')
                if not href:
                    continue

                full_url = href if href.startswith('http') else f"{config.base_url}{href}"

                # Get link text as title, or use event name
                title = link.get_text(strip=True)
                if not title or len(title) < 3 or title.lower() in ['pdf', 'download']:
                    title = link.get('title') or link.get('aria-label') or event_name or 'Untitled'

                title = ' '.join(title.split())

                # Skip if we already have this URL
                if any(d.url == full_url for d in documents):
                    continue

                documents.append(IRDocument(
                    id=generate_document_id(full_url, title),
                    title=title,
                    url=full_url,
                    date=date_str or str(year),
                    date_obj=parse_date(date_str or f'Jan 1, {year}'),
                    doc_type=infer_document_type(title, full_url),
                    event=event_name if event_name != title else '',
                    category='events',
                ))

        # Also look for standalone PDF links not in event containers
        for link in soup.select('a[href*="/static-files/"], a[href*=".pdf"]'):
            href = link.get('href', '')
            if not href:
                continue

            full_url = href if href.startswith('http') else f"{config.base_url}{href}"

            # Skip if already found
            if any(d.url == full_url for d in documents):
                continue

            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                title = link.get('title') or link.get('aria-label') or 'Untitled'

            # Try to find date from nearby elements
            date_str = ''
            parent = link.find_parent(['tr', 'li', 'div'])
            if parent:
                for date_el in parent.select('.date, time, td'):
                    text = date_el.get_text(strip=True)
                    if re.search(r'\d{4}', text) and len(text) < 30:
                        date_str = text
                        break

            documents.append(IRDocument(
                id=generate_document_id(full_url, title),
                title=' '.join(title.split()),
                url=full_url,
                date=date_str or str(year),
                date_obj=parse_date(date_str or f'Jan 1, {year}'),
                doc_type=infer_document_type(title, full_url),
                category='events',
            ))

        print(f"[IR Scraper] Found {len(documents)} documents for {year}")

    except Exception as e:
        print(f"[IR Scraper] Error scraping {year}: {e}")

    return documents


def scrape_events_page(config: IRSiteConfig) -> list[IRDocument]:
    """Scrape ALL years from events and presentations page."""
    all_documents: list[IRDocument] = []
    current_year = datetime.now().year
    start_year = 2015  # Go back to 2015 to capture historical presentations

    print(f"[IR Scraper] Scraping events from {start_year} to {current_year}...")

    # Scrape each year sequentially to avoid rate limiting
    for year in range(current_year, start_year - 1, -1):
        year_docs = scrape_events_page_for_year(config, year)
        all_documents.extend(year_docs)

        # Rate limiting between years
        if year > start_year:
            time.sleep(0.8)

    print(f"[IR Scraper] Total events documents found: {len(all_documents)}")
    return all_documents


def scrape_ir_documents(ticker: str) -> IRScraperResult:
    """
    Scrape all IR documents for a company.

    Args:
        ticker: Stock ticker symbol (e.g., "ARWR")

    Returns:
        IRScraperResult with all discovered documents
    """
    ticker_upper = ticker.upper()
    config = IR_CONFIGS.get(ticker_upper)

    if not config:
        raise ValueError(f"No IR configuration found for ticker: {ticker}")

    print(f"[IR Scraper] Starting scrape for {ticker_upper}...")

    # Scrape all sources
    download_docs = scrape_download_library(config)
    event_docs = scrape_events_page(config)

    # Merge and dedupe
    all_docs = download_docs + event_docs
    unique_docs: dict[str, IRDocument] = {}

    for doc in all_docs:
        existing = unique_docs.get(doc.id)
        if not existing or doc.file_size:
            unique_docs[doc.id] = doc

    # Sort by date descending
    documents = sorted(
        unique_docs.values(),
        key=lambda x: x.date_obj,
        reverse=True
    )

    # Calculate stats
    documents_by_year: dict[str, int] = {}
    for doc in documents:
        year = str(doc.date_obj.year)
        documents_by_year[year] = documents_by_year.get(year, 0) + 1

    print(f"[IR Scraper] Completed scrape for {ticker_upper}: {len(documents)} unique documents")

    return IRScraperResult(
        ticker=ticker_upper,
        company_name=COMPANY_NAMES.get(ticker_upper, ticker_upper),
        ir_base_url=config.base_url,
        documents=list(documents),
        scraped_at=datetime.now().isoformat(),
        total_documents=len(documents),
        documents_by_year=documents_by_year,
    )


def get_supported_tickers() -> list[str]:
    """Get list of supported tickers."""
    return list(IR_CONFIGS.keys())


def is_ticker_supported(ticker: str) -> bool:
    """Check if a ticker is supported."""
    return ticker.upper() in IR_CONFIGS


def scrape_all_presentations(ticker: str) -> dict:
    """
    Scrape ALL presentations for a company (convenience function).

    Returns:
        Dict with ticker, totalPresentations, presentations, byYear, byType
    """
    result = scrape_ir_documents(ticker)

    # Filter to just presentations (exclude webcasts, SEC filings)
    presentations = [
        d for d in result.documents
        if d.doc_type in ('presentation', 'poster') or '/static-files/' in d.url
    ]

    # Count by year
    by_year: dict[str, int] = {}
    for doc in presentations:
        year = str(doc.date_obj.year)
        by_year[year] = by_year.get(year, 0) + 1

    # Count by type
    by_type: dict[str, int] = {}
    for doc in presentations:
        by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1

    return {
        'ticker': ticker.upper(),
        'total_presentations': len(presentations),
        'presentations': presentations,
        'by_year': by_year,
        'by_type': by_type,
    }
