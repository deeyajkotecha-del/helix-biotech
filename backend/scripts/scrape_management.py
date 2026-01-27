"""
Scrape Management/Leadership Information from SEC 10-K Filings

Primary source: 10-K "Information about our Executive Officers" section in Part I
Fallback: DEF 14A proxy statement (if 10-K incorporates by reference)

10-K Item 1 often includes a standardized table with:
- Executive names (with credentials like M.D., Ph.D., J.D.)
- Ages
- Titles/Positions
"""

import os
import sys
import json
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
import sqlite3
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Executive:
    name: str
    title: str
    age: Optional[int] = None
    bio: Optional[str] = None
    compensation: Optional[float] = None
    is_ceo: bool = False
    is_cfo: bool = False
    is_cmo: bool = False
    is_cso: bool = False
    is_coo: bool = False
    is_director: bool = False


@dataclass
class CompanyData:
    ticker: str
    company_name: str
    cik: Optional[str] = None
    filing_date: Optional[str] = None
    filing_url: Optional[str] = None
    filing_type: Optional[str] = None  # "10-K" or "DEF 14A"
    executives: List[Executive] = field(default_factory=list)


class SECManagementScraper:
    """Scraper for SEC filings to extract executive information"""

    SEC_BASE = "https://www.sec.gov"
    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

    def __init__(self, db_path: Optional[str] = None):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.db_path = db_path or str(self.data_dir / "helix.db")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helix Intelligence Platform research@helix-intel.com",
            "Accept": "application/json, text/html",
        })
        self._ticker_to_cik = None

    def init_database(self):
        """Initialize management table in database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS management (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_ticker TEXT NOT NULL,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                age INTEGER,
                bio TEXT,
                compensation REAL,
                is_ceo BOOLEAN DEFAULT FALSE,
                is_cfo BOOLEAN DEFAULT FALSE,
                is_cmo BOOLEAN DEFAULT FALSE,
                is_cso BOOLEAN DEFAULT FALSE,
                is_coo BOOLEAN DEFAULT FALSE,
                is_director BOOLEAN DEFAULT FALSE,
                source_filing TEXT,
                filing_date TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_ticker, name)
            )
        """)

        conn.commit()
        conn.close()
        print(f"[DB] Database ready: {self.db_path}")

    def _load_ticker_mapping(self):
        """Load ticker to CIK mapping from SEC"""
        if self._ticker_to_cik is not None:
            return

        print("[INFO] Loading SEC ticker to CIK mapping...")
        try:
            resp = self.session.get(self.COMPANY_TICKERS_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            self._ticker_to_cik = {}
            for item in data.values():
                ticker = item.get("ticker", "").upper()
                cik = str(item.get("cik_str", "")).zfill(10)
                self._ticker_to_cik[ticker] = {
                    "cik": cik,
                    "name": item.get("title", "")
                }
            print(f"[INFO] Loaded {len(self._ticker_to_cik)} ticker mappings")
        except Exception as e:
            print(f"[ERROR] Loading ticker mapping: {e}")
            self._ticker_to_cik = {}

    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker"""
        self._load_ticker_mapping()
        info = self._ticker_to_cik.get(ticker.upper())
        return info["cik"] if info else None

    def get_filing_url(self, cik: str, form_type: str = "10-K") -> Optional[Dict]:
        """Get most recent filing URL of specified type"""
        url = self.SUBMISSIONS_URL.format(cik=cik)

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])

            # For DEF 14A, prefer the actual proxy statement over amendments
            if form_type == "DEF 14A":
                # First look for DEF 14A exactly
                for i, form in enumerate(forms):
                    if form == "DEF 14A":
                        accession = accessions[i].replace("-", "")
                        return {
                            "form": form,
                            "date": dates[i],
                            "url": f"{self.SEC_BASE}/Archives/edgar/data/{cik}/{accession}/{primary_docs[i]}"
                        }
                # Fallback to DEFA14A if no DEF 14A found
                for i, form in enumerate(forms):
                    if form == "DEFA14A":
                        accession = accessions[i].replace("-", "")
                        return {
                            "form": form,
                            "date": dates[i],
                            "url": f"{self.SEC_BASE}/Archives/edgar/data/{cik}/{accession}/{primary_docs[i]}"
                        }
            else:
                for i, form in enumerate(forms):
                    if form == form_type:
                        accession = accessions[i].replace("-", "")
                        return {
                            "form": form,
                            "date": dates[i],
                            "url": f"{self.SEC_BASE}/Archives/edgar/data/{cik}/{accession}/{primary_docs[i]}"
                        }
            return None
        except Exception as e:
            print(f"  [ERROR] Fetching filings: {e}")
            return None

    def parse_10k_executives(self, url: str) -> List[Executive]:
        """Parse executive officers from 10-K filing"""
        executives = []

        try:
            print(f"  [FETCH] 10-K: {url[:70]}...")
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(separator='\n')

            # Find the executive officers section (not TOC)
            # Look for "The names" which indicates actual content
            all_matches = list(re.finditer(
                r'(?:INFORMATION\s+ABOUT\s+)?(?:OUR\s+)?EXECUTIVE\s+OFFICERS',
                text, re.IGNORECASE
            ))

            section_start = None
            for m in all_matches:
                following = text[m.start():m.start() + 300]
                if 'The names' in following or 'Name\n' in following or 'NAME\n' in following:
                    section_start = m.start()
                    break

            if not section_start:
                print(f"  [INFO] No executive officers section in 10-K")
                return []

            print(f"  [FOUND] Executive officers section")
            section = text[section_start:section_start + 10000]

            # Find table header: Name Age Position
            header_match = re.search(
                r'(?:Name|NAME)\s*\n\s*(?:Age|AGE)\s*\n\s*(?:Position|Title|POSITION|TITLE)',
                section
            )

            if header_match:
                print(f"  [PARSE] Multi-line table format")
                table_text = section[header_match.end():]
                lines = [l.strip() for l in table_text.split('\n') if l.strip()]

                i = 0
                while i < len(lines) - 2:
                    name = lines[i]

                    if not self._is_valid_name(name):
                        if name.startswith(('Dr.', 'Mr.', 'Ms.', 'The ')) or 'has been' in name:
                            break
                        i += 1
                        continue

                    age_str = lines[i + 1]
                    if not age_str.isdigit():
                        i += 1
                        continue
                    age = int(age_str)
                    if age < 30 or age > 85:
                        i += 1
                        continue

                    title = lines[i + 2]
                    if not self._is_executive_title(title):
                        i += 1
                        continue

                    exec = Executive(name=name, title=title, age=age)
                    self._classify_executive(exec)
                    executives.append(exec)
                    i += 3
            else:
                # Try prose format
                print(f"  [PARSE] Prose format")
                pattern = r'([A-Z][a-zA-Z\s\.\,\-\"\']+?(?:,\s*(?:M\.D\.|Ph\.D\.|J\.D\.|CPA))?)\s*,\s*(?:age\s*)?(\d{2})\s*,\s*(.+?)(?:\.|,\s*(?:has|is|was|who|since))'
                seen = set()
                for match in re.finditer(pattern, section, re.IGNORECASE):
                    name = match.group(1).strip()
                    age = int(match.group(2))
                    title = match.group(3).strip()

                    if name.lower() in seen:
                        continue
                    seen.add(name.lower())

                    if self._is_valid_name(name) and 30 <= age <= 85:
                        exec = Executive(name=name, title=title, age=age)
                        self._classify_executive(exec)
                        executives.append(exec)

            return executives

        except Exception as e:
            print(f"  [ERROR] Parsing 10-K: {e}")
            return []

    def parse_def14a_executives(self, url: str) -> List[Executive]:
        """Parse executive officers from DEF 14A proxy statement"""
        executives = []

        try:
            print(f"  [FETCH] DEF 14A: {url[:70]}...")
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(separator='\n')

            # Find Summary Compensation Table (most reliable source)
            comp_match = re.search(r'Summary\s+Compensation\s+Table', text, re.IGNORECASE)
            if comp_match:
                print(f"  [FOUND] Summary Compensation Table")
                section = text[comp_match.start():comp_match.start() + 8000]

                # Parse multi-line format: Name on one line, Title on next
                # Example: "Yvonne L. Greenstreet, M.D. \nChief Executive Officer..."
                lines = section.split('\n')
                seen = set()

                i = 0
                while i < len(lines) - 1:
                    line = lines[i].strip()

                    # Check if this looks like a name (with possible credentials)
                    # Pattern: First Last or First M. Last, with optional M.D., Ph.D., etc.
                    name_match = re.match(
                        r'^([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+(?:,\s*(?:M\.D\.|Ph\.D\.|J\.D\.|CPA|MBA|III|Jr\.))?)\s*$',
                        line
                    )

                    if name_match:
                        name = name_match.group(1).strip()

                        # Next line should be title
                        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

                        if self._is_executive_title(next_line) and name.lower() not in seen:
                            title = next_line
                            # Clean up title - remove parenthetical notes
                            title = re.sub(r'\s*\([^)]+\)\s*$', '', title).strip()

                            seen.add(name.lower())
                            exec = Executive(name=name, title=title)
                            self._classify_executive(exec)
                            executives.append(exec)
                            i += 2  # Skip both name and title lines
                            continue

                    i += 1

                if executives:
                    return executives

            # Fallback: Look for "age XX" patterns
            section_patterns = [
                r'NAMED\s+EXECUTIVE\s+OFFICERS',
                r'EXECUTIVE\s+OFFICERS\s+OF\s+THE',
            ]

            section_start = None
            for pattern in section_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    section_start = match.start()
                    break

            if not section_start:
                print(f"  [INFO] No executive section found in DEF 14A")
                return []

            print(f"  [FOUND] Executive officers section")
            section = text[section_start:section_start + 15000]

            # Parse executives with age pattern
            patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,\s*age\s*(\d{2})\s*[,\.]\s*([A-Za-z][^\.]{10,80}?)(?:\.|,)',
                r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,\s*(\d{2})\s*,\s*([A-Za-z][^\.]{10,80}?)(?:\.|,)',
            ]

            seen = set()
            for pattern in patterns:
                for match in re.finditer(pattern, section):
                    name = match.group(1).strip()
                    age = int(match.group(2))
                    title = match.group(3).strip()

                    if name.lower() in seen:
                        continue
                    seen.add(name.lower())

                    if self._is_valid_name(name) and 30 <= age <= 85 and self._is_executive_title(title):
                        exec = Executive(name=name, title=title, age=age)
                        self._classify_executive(exec)
                        executives.append(exec)

            return executives

        except Exception as e:
            print(f"  [ERROR] Parsing DEF 14A: {e}")
            return []

    def _is_valid_name(self, text: str) -> bool:
        """Check if text is a valid person name"""
        if not text or len(text) < 5 or len(text) > 60:
            return False
        if text[0].islower():
            return False
        words = text.replace(',', '').split()
        if len(words) < 2:
            return False
        if text.startswith(('Dr.', 'Mr.', 'Ms.', 'The ', 'Our ', 'Each ')):
            return False
        if any(c.isdigit() for c in text):
            return False
        return True

    def _is_executive_title(self, text: str) -> bool:
        """Check if text is an executive title"""
        if not text or len(text) < 2:
            return False
        text_lower = text.lower().strip()
        # Check for short acronym titles first
        short_titles = ['ceo', 'cfo', 'cmo', 'coo', 'cso', 'cto', 'cio', 'cro']
        if text_lower in short_titles:
            return True
        # Check for longer title keywords
        if len(text) < 5:
            return False
        keywords = ['chief', 'officer', 'president', 'chairman', 'vice president',
                   'evp', 'svp', 'counsel', 'head of', 'controller', 'treasurer',
                   'secretary', 'director', 'executive']
        return any(kw in text_lower for kw in keywords)

    def _classify_executive(self, exec: Executive):
        """Classify executive role based on title"""
        # Normalize whitespace (including non-breaking spaces \xa0)
        t = ' '.join(exec.title.lower().split())
        exec.is_ceo = 'chief executive' in t or t == 'ceo' or 'ceo' in t.split() or 'president and ceo' in t
        exec.is_cfo = 'chief financial' in t or t == 'cfo' or 'cfo' in t.split()
        exec.is_cmo = 'chief medical' in t or t == 'cmo' or 'cmo' in t.split()
        exec.is_cso = 'chief scientific' in t or t == 'cso' or 'cso' in t.split() or 'chief science' in t
        exec.is_coo = 'chief operating' in t or t == 'coo' or 'coo' in t.split()
        exec.is_director = 'director' in t and 'officer' not in t

    def scrape_company(self, ticker: str, company_name: str = None) -> CompanyData:
        """Scrape management info for a single company"""
        print(f"\n{'='*60}")
        print(f"Scraping {ticker}")
        print(f"{'='*60}")

        result = CompanyData(ticker=ticker, company_name=company_name or ticker)

        # Get CIK
        print(f"  [CIK] Looking up {ticker}...")
        cik = self.get_cik(ticker)
        if not cik:
            print(f"  [ERROR] CIK not found")
            return result

        result.cik = cik
        print(f"  [CIK] {cik}")

        time.sleep(0.2)

        # Try 10-K first (preferred source)
        print(f"  [FILING] Looking for 10-K...")
        filing_10k = self.get_filing_url(cik, "10-K")

        if filing_10k:
            print(f"  [FILING] Found 10-K from {filing_10k['date']}")
            time.sleep(0.3)

            executives = self.parse_10k_executives(filing_10k['url'])

            if executives:
                result.executives = executives
                result.filing_date = filing_10k['date']
                result.filing_url = filing_10k['url']
                result.filing_type = "10-K"
                print(f"  [RESULT] Found {len(executives)} executives from 10-K")
                return result

        # Fallback to DEF 14A
        print(f"  [FILING] Trying DEF 14A fallback...")
        filing_14a = self.get_filing_url(cik, "DEF 14A")

        if filing_14a:
            print(f"  [FILING] Found DEF 14A from {filing_14a['date']}")
            time.sleep(0.3)

            executives = self.parse_def14a_executives(filing_14a['url'])

            if executives:
                result.executives = executives
                result.filing_date = filing_14a['date']
                result.filing_url = filing_14a['url']
                result.filing_type = "DEF 14A"
                print(f"  [RESULT] Found {len(executives)} executives from DEF 14A")
                return result

        print(f"  [RESULT] No executives found")
        return result

    def save_to_database(self, data: CompanyData):
        """Save company data to database"""
        if not data.executives:
            print(f"  [DB] No executives to save")
            return

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Clear existing data for this company
        cur.execute("DELETE FROM management WHERE company_ticker = ?", (data.ticker,))

        # Insert executives
        for exec in data.executives:
            cur.execute("""
                INSERT OR REPLACE INTO management
                (company_ticker, name, title, age, bio, compensation,
                 is_ceo, is_cfo, is_cmo, is_cso, is_coo, is_director,
                 source_filing, filing_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.ticker,
                exec.name,
                exec.title,
                exec.age,
                exec.bio,
                exec.compensation,
                exec.is_ceo,
                exec.is_cfo,
                exec.is_cmo,
                exec.is_cso,
                exec.is_coo,
                exec.is_director,
                data.filing_url,
                data.filing_date,
                datetime.utcnow().isoformat()
            ))

        conn.commit()
        conn.close()
        print(f"  [DB] Saved {len(data.executives)} executives")

    def run(self, tickers: Optional[List[str]] = None, limit: int = 20):
        """Run scraper for specified tickers"""
        self.init_database()

        if not tickers:
            # Load from XBI holdings
            holdings_path = self.data_dir / "xbi_holdings.json"
            if holdings_path.exists():
                with open(holdings_path) as f:
                    xbi = json.load(f)
                    tickers = [h['ticker'] for h in xbi.get('holdings', [])[:limit]]
            else:
                print("[ERROR] No tickers specified and XBI holdings not found")
                return []

        results = []
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[PROGRESS] {i}/{len(tickers)}")
            try:
                data = self.scrape_company(ticker)
                if data.executives:
                    self.save_to_database(data)
                    results.append(data)
            except Exception as e:
                print(f"  [ERROR] {e}")
            time.sleep(0.5)

        # Summary
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Companies with executives: {len(results)}/{len(tickers)}")
        print(f"Total executives found: {sum(len(r.executives) for r in results)}")

        for r in results:
            ceo = next((e for e in r.executives if e.is_ceo), None)
            source = f"[{r.filing_type}]" if r.filing_type else ""
            ceo_str = f" (CEO: {ceo.name})" if ceo else ""
            print(f"  {r.ticker}: {len(r.executives)} executives{ceo_str} {source}")

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape management info from SEC filings")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to scrape")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of companies")
    parser.add_argument("--all", action="store_true", help="Scrape all XBI companies")

    args = parser.parse_args()

    scraper = SECManagementScraper()

    if args.tickers:
        scraper.run(tickers=args.tickers)
    elif args.all:
        scraper.run(limit=args.limit)
    else:
        # Default: test with a few companies
        scraper.run(tickers=["VRTX", "REGN", "MRNA", "GILD", "BIIB"])


if __name__ == "__main__":
    main()
