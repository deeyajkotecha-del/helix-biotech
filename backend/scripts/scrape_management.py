"""
Scrape Management/Leadership Information from Company Investor Relations Pages

This script:
1. Finds investor relations URLs for biotech companies
2. Scrapes leadership/management pages
3. Extracts CEO, CFO, CMO, CSO and other key executives
4. Stores in the database for use in reports
"""

import os
import sys
import json
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Executive:
    name: str
    title: str
    bio: Optional[str] = None
    image_url: Optional[str] = None


@dataclass
class ManagementInfo:
    ticker: str
    company_name: str
    ir_url: Optional[str] = None
    leadership_url: Optional[str] = None
    executives: List[Executive] = None
    last_updated: Optional[str] = None

    def __post_init__(self):
        if self.executives is None:
            self.executives = []


# Known IR URLs for biotech companies
KNOWN_IR_URLS = {
    "ABVX": "https://www.abivax.com/investors/",
    "INSM": "https://investor.insmed.com/",
    "ALNY": "https://www.alnylam.com/investors",
    "MRNA": "https://investors.modernatx.com/",
    "CGON": "https://ir.cgoncology.com/",
    "GPCR": "https://ir.structuretx.com/",
    "VRNA": "https://www.vfrona.com/investors/",
    "REGN": "https://investor.regeneron.com/",
    "VRTX": "https://investors.vrtx.com/",
    "BIIB": "https://investors.biogen.com/",
    "GILD": "https://investors.gilead.com/",
    "BMRN": "https://investors.biomarin.com/",
    "SRPT": "https://investorrelations.sarepta.com/",
    "NBIX": "https://neurocrine.com/investors/",
    "EXEL": "https://ir.exelixis.com/",
    "IONS": "https://ir.ionispharma.com/",
    "PCVX": "https://investors.vaxcyte.com/",
    "ARGX": "https://www.argenx.com/investors",
    "CRSP": "https://crisprtx.com/investors",
    "BEAM": "https://investors.beamtx.com/",
    "NTLA": "https://ir.intelliatx.com/",
}

# Common leadership page patterns
LEADERSHIP_PATTERNS = [
    "/leadership",
    "/management",
    "/team",
    "/about/leadership",
    "/about/management",
    "/about-us/leadership",
    "/about-us/management",
    "/company/leadership",
    "/company/management",
    "/corporate/leadership",
    "/our-team",
    "/executive-team",
    "/board-of-directors",
]


class ManagementScraper:
    def __init__(self, db_path: Optional[str] = None):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.db_path = db_path or str(self.data_dir / "helix.db")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.init_database()

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
                bio TEXT,
                image_url TEXT,
                is_ceo BOOLEAN DEFAULT FALSE,
                is_cfo BOOLEAN DEFAULT FALSE,
                is_cmo BOOLEAN DEFAULT FALSE,
                is_cso BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_ticker, name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS company_ir_info (
                ticker TEXT PRIMARY KEY,
                ir_url TEXT,
                leadership_url TEXT,
                last_scraped TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        print(f"Database initialized: {self.db_path}")

    def find_ir_url(self, ticker: str, company_name: str) -> Optional[str]:
        """Find investor relations URL for a company"""
        # Check known URLs first
        if ticker in KNOWN_IR_URLS:
            return KNOWN_IR_URLS[ticker]

        # Try common patterns
        company_slug = company_name.lower().split()[0]
        common_patterns = [
            f"https://investors.{company_slug}.com/",
            f"https://ir.{company_slug}.com/",
            f"https://investor.{company_slug}.com/",
            f"https://www.{company_slug}.com/investors",
        ]

        for url in common_patterns:
            try:
                resp = self.session.head(url, timeout=5, allow_redirects=True)
                if resp.status_code == 200:
                    return url
            except:
                continue

        return None

    def find_leadership_page(self, base_url: str) -> Optional[str]:
        """Find the leadership/management page from a base URL"""
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Try common leadership page patterns
        for pattern in LEADERSHIP_PATTERNS:
            url = urljoin(base, pattern)
            try:
                resp = self.session.head(url, timeout=5, allow_redirects=True)
                if resp.status_code == 200:
                    return resp.url
            except:
                continue

        # Try to find link on main page
        try:
            resp = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Look for leadership/team links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.get_text().lower()
                if any(word in href or word in text for word in ['leadership', 'management', 'team', 'executive']):
                    full_url = urljoin(base_url, link['href'])
                    return full_url
        except:
            pass

        return None

    def extract_executives_from_page(self, url: str, ticker: str) -> List[Executive]:
        """Extract executive information from a leadership page"""
        executives = []

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Common patterns for executive cards/sections
            # Pattern 1: Look for executive cards with name and title
            exec_sections = soup.find_all(['div', 'article', 'section'],
                class_=lambda x: x and any(word in str(x).lower() for word in ['executive', 'leader', 'team-member', 'bio', 'person']))

            for section in exec_sections:
                exec_info = self._extract_exec_from_section(section)
                if exec_info:
                    executives.append(exec_info)

            # Pattern 2: Look for structured data (often in schema.org format)
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Organization':
                        members = data.get('member', []) or data.get('employee', [])
                        for member in members:
                            if isinstance(member, dict):
                                name = member.get('name')
                                title = member.get('jobTitle')
                                if name and title:
                                    executives.append(Executive(name=name, title=title))
                except:
                    continue

            # Pattern 3: Look for h2/h3/h4 with names followed by titles
            if not executives:
                executives = self._extract_from_headings(soup)

            # Deduplicate
            seen = set()
            unique_execs = []
            for exec in executives:
                key = (exec.name.lower(), exec.title.lower())
                if key not in seen:
                    seen.add(key)
                    unique_execs.append(exec)

            return unique_execs[:15]  # Limit to top 15

        except Exception as e:
            print(f"    Error scraping {url}: {e}")
            return []

    def _extract_exec_from_section(self, section) -> Optional[Executive]:
        """Extract executive info from a section/card"""
        name = None
        title = None
        bio = None
        image_url = None

        # Try to find name (usually in h2, h3, h4, or strong tag)
        for tag in ['h2', 'h3', 'h4', 'h5', 'strong', 'b']:
            elem = section.find(tag)
            if elem:
                text = elem.get_text(strip=True)
                # Check if it looks like a name (2-4 words, capitalized)
                if self._looks_like_name(text):
                    name = text
                    break

        if not name:
            # Try class-based detection
            name_elem = section.find(class_=lambda x: x and 'name' in str(x).lower())
            if name_elem:
                name = name_elem.get_text(strip=True)

        # Try to find title
        title_elem = section.find(class_=lambda x: x and any(word in str(x).lower() for word in ['title', 'position', 'role']))
        if title_elem:
            title = title_elem.get_text(strip=True)
        else:
            # Look for common title patterns in text
            text = section.get_text()
            title_match = re.search(r'(Chief\s+\w+\s*Officer|CEO|CFO|CMO|CSO|COO|CTO|President|Vice\s+President|SVP|EVP|Director)', text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)

        # Try to find bio
        bio_elem = section.find(class_=lambda x: x and 'bio' in str(x).lower())
        if bio_elem:
            bio = bio_elem.get_text(strip=True)[:500]

        # Try to find image
        img = section.find('img')
        if img and img.get('src'):
            image_url = img['src']

        if name and title:
            return Executive(name=name, title=title, bio=bio, image_url=image_url)

        return None

    def _extract_from_headings(self, soup) -> List[Executive]:
        """Extract executives from heading patterns"""
        executives = []

        for heading in soup.find_all(['h2', 'h3', 'h4']):
            text = heading.get_text(strip=True)
            if self._looks_like_name(text):
                # Look for title in next sibling or parent
                next_elem = heading.find_next_sibling()
                if next_elem:
                    next_text = next_elem.get_text(strip=True)
                    if self._looks_like_title(next_text):
                        executives.append(Executive(name=text, title=next_text))

        return executives

    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name"""
        if not text or len(text) < 3 or len(text) > 50:
            return False
        words = text.split()
        if len(words) < 2 or len(words) > 5:
            return False
        # Should be mostly capitalized words
        cap_words = sum(1 for w in words if w[0].isupper())
        if cap_words < len(words) * 0.5:
            return False
        # Should not contain common non-name words
        non_name_words = ['about', 'contact', 'news', 'press', 'investor', 'leadership', 'team', 'our']
        if any(word.lower() in non_name_words for word in words):
            return False
        return True

    def _looks_like_title(self, text: str) -> bool:
        """Check if text looks like a job title"""
        title_keywords = ['chief', 'officer', 'president', 'director', 'vp', 'svp', 'evp',
                         'head', 'founder', 'ceo', 'cfo', 'cmo', 'cso', 'coo', 'cto']
        return any(keyword in text.lower() for keyword in title_keywords)

    def classify_executive(self, title: str) -> Dict[str, bool]:
        """Classify executive by their title"""
        title_lower = title.lower()
        return {
            'is_ceo': 'chief executive' in title_lower or title_lower == 'ceo' or 'ceo' in title_lower.split(),
            'is_cfo': 'chief financial' in title_lower or 'cfo' in title_lower,
            'is_cmo': 'chief medical' in title_lower or 'cmo' in title_lower,
            'is_cso': 'chief scientific' in title_lower or 'cso' in title_lower or 'chief science' in title_lower,
        }

    def scrape_company(self, ticker: str, company_name: str) -> ManagementInfo:
        """Scrape management info for a single company"""
        print(f"\n{'='*60}")
        print(f"Scraping management for {ticker}: {company_name}")
        print(f"{'='*60}")

        info = ManagementInfo(ticker=ticker, company_name=company_name)

        # Step 1: Find IR URL
        print("  Finding investor relations URL...")
        ir_url = self.find_ir_url(ticker, company_name)
        if ir_url:
            info.ir_url = ir_url
            print(f"    Found: {ir_url}")
        else:
            print(f"    Not found, trying company website...")
            # Try to find from SEC data or construct from company name
            info.ir_url = f"https://www.{company_name.lower().split()[0]}.com/investors"

        time.sleep(0.5)

        # Step 2: Find leadership page
        if info.ir_url:
            print("  Finding leadership page...")
            leadership_url = self.find_leadership_page(info.ir_url)
            if leadership_url:
                info.leadership_url = leadership_url
                print(f"    Found: {leadership_url}")
            else:
                # Try common patterns from company domain
                parsed = urlparse(info.ir_url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                for pattern in ['/about/leadership', '/leadership', '/about-us/leadership', '/company/leadership']:
                    test_url = urljoin(base.replace('investors.', 'www.').replace('investor.', 'www.').replace('ir.', 'www.'), pattern)
                    try:
                        resp = self.session.head(test_url, timeout=5, allow_redirects=True)
                        if resp.status_code == 200:
                            info.leadership_url = resp.url
                            print(f"    Found: {info.leadership_url}")
                            break
                    except:
                        continue

        time.sleep(0.5)

        # Step 3: Extract executives
        if info.leadership_url:
            print("  Extracting executives...")
            executives = self.extract_executives_from_page(info.leadership_url, ticker)
            info.executives = executives
            print(f"    Found {len(executives)} executives")
            for exec in executives[:5]:
                print(f"      - {exec.name}: {exec.title}")

        info.last_updated = datetime.utcnow().isoformat()

        return info

    def save_to_database(self, info: ManagementInfo):
        """Save management info to database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Save IR info
        cur.execute("""
            INSERT OR REPLACE INTO company_ir_info (ticker, ir_url, leadership_url, last_scraped, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (info.ticker, info.ir_url, info.leadership_url, info.last_updated, info.last_updated))

        # Save executives
        for exec in info.executives:
            classification = self.classify_executive(exec.title)
            cur.execute("""
                INSERT OR REPLACE INTO management
                (company_ticker, name, title, bio, image_url, is_ceo, is_cfo, is_cmo, is_cso, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                info.ticker,
                exec.name,
                exec.title,
                exec.bio,
                exec.image_url,
                classification['is_ceo'],
                classification['is_cfo'],
                classification['is_cmo'],
                classification['is_cso'],
                info.last_updated
            ))

        conn.commit()
        conn.close()
        print(f"  Saved {len(info.executives)} executives to database")

    def run(self, tickers: Optional[List[str]] = None):
        """Run scraper for specified tickers or all XBI companies"""
        if not tickers:
            # Load from XBI holdings
            holdings_path = self.data_dir / "xbi_holdings.json"
            if holdings_path.exists():
                with open(holdings_path) as f:
                    data = json.load(f)
                    tickers = [(h['ticker'], h['name']) for h in data.get('holdings', [])[:20]]
            else:
                print("No tickers specified and XBI holdings not found")
                return
        else:
            # Get company names from database
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            ticker_names = []
            for t in tickers:
                cur.execute("SELECT name FROM companies WHERE ticker = ?", (t,))
                row = cur.fetchone()
                name = row[0] if row else t
                ticker_names.append((t, name))
            conn.close()
            tickers = ticker_names

        results = []
        for ticker, name in tickers:
            try:
                info = self.scrape_company(ticker, name)
                if info.executives:
                    self.save_to_database(info)
                    results.append(info)
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(1)  # Rate limiting

        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Companies processed: {len(results)}")
        print(f"Total executives found: {sum(len(r.executives) for r in results)}")

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape management info for biotech companies")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all XBI companies")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of companies")

    args = parser.parse_args()

    scraper = ManagementScraper()

    if args.tickers:
        scraper.run(tickers=args.tickers)
    elif args.all:
        scraper.run()
    else:
        # Default: test with a few companies
        scraper.run(tickers=["ABVX", "INSM", "ALNY"])


if __name__ == "__main__":
    main()
