"""
IR Page Discoverer

Automatically discovers investor relations pages for any biotech company.
Uses multiple strategies: common URL patterns, SEC EDGAR lookup, web search.
"""

import asyncio
import aiohttp
from typing import Optional
from urllib.parse import urlparse
import re


# Common IR URL patterns for biotech companies
IR_URL_PATTERNS = [
    "https://ir.{domain}",
    "https://investor.{domain}",
    "https://investors.{domain}",
    "https://{domain}/investors",
    "https://{domain}/investor-relations",
    "https://{domain}/ir",
    "https://www.{domain}/investors",
    "https://www.{domain}/investor-relations",
    "https://{domain}/en/investors",
    "https://www.{domain}/en/investors",
]

# Known IR page URLs (direct mappings for common biotech companies)
KNOWN_IR_URLS = {
    "ARWR": "https://ir.arrowheadpharma.com",
    "ALNY": "https://investors.alnylam.com",
    "IONS": "https://ir.ionispharma.com",
    "VKTX": "https://ir.vikingtherapeutics.com",
    "REGN": "https://investor.regeneron.com",
    "VRTX": "https://investors.vrtx.com",
    "BIIB": "https://investors.biogen.com",
    "MRNA": "https://investors.modernatx.com",
    "INSM": "https://investor.insmed.com",
    "SRPT": "https://investorrelations.sarepta.com",
}

# Known company domain mappings (fallback)
KNOWN_DOMAINS = {
    "ARWR": "arrowheadpharma.com",
    "ALNY": "alnylam.com",
    "IONS": "ionispharma.com",
    "VKTX": "vikingtherapeutics.com",
    "REGN": "regeneron.com",
    "VRTX": "vrtx.com",
    "BIIB": "biogen.com",
    "BMRN": "biomarin.com",
    "INSM": "insmed.com",
    "SRPT": "sarepta.com",
    "NBIX": "neurocrine.com",
    "EXEL": "exelixis.com",
    "INCY": "incyte.com",
    "SGEN": "seagen.com",
    "UTHR": "unither.com",
    "TECH": "bio-techne.com",
    "BGNE": "beigene.com",
    "MRNA": "modernatx.com",
    "BNTX": "biontech.de",
}

# Common download library paths
DOWNLOAD_PATHS = [
    "/download-library",
    "/events-presentations",
    "/events-and-presentations",
    "/presentations",
    "/financial-information/presentations",
    "/sec-filings",
    "/financials/sec-filings",
]


class IRDiscoverer:
    """Discover IR pages for biotech companies."""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Helix-Biotech-Research/1.0"},
            timeout=aiohttp.ClientTimeout(total=5, connect=3)  # Shorter timeouts
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def discover(self, ticker: str) -> dict:
        """
        Discover IR page for a ticker.

        Args:
            ticker: Stock ticker (e.g., ARWR)

        Returns:
            dict with IR URLs and company info
        """
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "company_name": None,
            "domain": None,
            "ir_base_url": None,
            "download_library_url": None,
            "presentations_url": None,
            "sec_filings_url": None,
            "discovery_method": None,
            "verified": False
        }

        # Strategy 0: Check known IR URLs (fastest, most reliable)
        if ticker in KNOWN_IR_URLS:
            ir_url = KNOWN_IR_URLS[ticker]
            if ticker in KNOWN_DOMAINS:
                result["domain"] = KNOWN_DOMAINS[ticker]

            # Try to verify URL exists
            try:
                is_reachable = await self._url_exists(ir_url)
            except Exception:
                is_reachable = False

            if is_reachable:
                result["ir_base_url"] = ir_url
                result["discovery_method"] = "known_ir_url"
                result["verified"] = True
                await self._find_subpages(result)
                return result
            else:
                # URL known but not reachable - still use it (network may be blocked)
                result["ir_base_url"] = ir_url
                result["discovery_method"] = "known_ir_url_unverified"
                result["download_library_url"] = f"{ir_url}/download-library"
                result["presentations_url"] = f"{ir_url}/events-presentations"
                result["verified"] = False
                return result

        # Strategy 1: Check known domains
        if ticker in KNOWN_DOMAINS:
            domain = KNOWN_DOMAINS[ticker]
            result["domain"] = domain
            result["discovery_method"] = "known_domain"
            await self._try_ir_patterns(result, domain)

        # Strategy 2: Try SEC EDGAR lookup
        if not result["ir_base_url"]:
            sec_info = await self._lookup_sec_edgar(ticker)
            if sec_info:
                result["company_name"] = sec_info.get("name")
                if sec_info.get("website"):
                    domain = urlparse(sec_info["website"]).netloc.replace("www.", "")
                    result["domain"] = domain
                    result["discovery_method"] = "sec_edgar"
                    await self._try_ir_patterns(result, domain)

        # Strategy 3: Try common domain patterns
        if not result["ir_base_url"]:
            domain_guesses = self._guess_domains(ticker)
            for domain in domain_guesses:
                result["domain"] = domain
                result["discovery_method"] = "domain_guess"
                await self._try_ir_patterns(result, domain)
                if result["ir_base_url"]:
                    break

        # Find download library and presentations pages
        if result["ir_base_url"]:
            await self._find_subpages(result)
            result["verified"] = True

        return result

    async def _try_ir_patterns(self, result: dict, domain: str):
        """Try common IR URL patterns for a domain."""
        for pattern in IR_URL_PATTERNS:
            url = pattern.format(domain=domain)
            if await self._url_exists(url):
                result["ir_base_url"] = url
                return

    async def _url_exists(self, url: str) -> bool:
        """Check if a URL exists and returns 200."""
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                return response.status == 200
        except Exception:
            try:
                async with self.session.get(url, allow_redirects=True) as response:
                    return response.status == 200
            except Exception:
                return False

    async def _lookup_sec_edgar(self, ticker: str) -> Optional[dict]:
        """Look up company info from SEC EDGAR."""
        try:
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=1&output=atom"
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                text = await response.text()

                # Extract company name from atom feed
                name_match = re.search(r'<title>([^<]+)</title>', text)
                if name_match:
                    title = name_match.group(1)
                    # Clean up title (remove "EDGAR" prefix, etc.)
                    if " - " in title:
                        company_name = title.split(" - ")[0].strip()
                    else:
                        company_name = title.strip()

                    return {"name": company_name, "website": None}

        except Exception:
            pass

        # Try company tickers JSON
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for entry in data.values():
                        if entry.get("ticker") == ticker:
                            return {"name": entry.get("title"), "cik": entry.get("cik_str")}
        except Exception:
            pass

        return None

    def _guess_domains(self, ticker: str) -> list:
        """Generate domain guesses from ticker."""
        ticker_lower = ticker.lower()
        return [
            f"{ticker_lower}.com",
            f"{ticker_lower}pharma.com",
            f"{ticker_lower}therapeutics.com",
            f"{ticker_lower}bio.com",
            f"{ticker_lower}sciences.com",
            f"{ticker_lower}oncology.com",
        ]

    async def _find_subpages(self, result: dict):
        """Find download library and other subpages."""
        base_url = result["ir_base_url"].rstrip("/")

        for path in DOWNLOAD_PATHS:
            url = f"{base_url}{path}"
            if await self._url_exists(url):
                if "download" in path or "presentation" in path:
                    result["download_library_url"] = url
                    result["presentations_url"] = url
                elif "sec" in path or "filing" in path:
                    result["sec_filings_url"] = url

        # If no download library found, use base URL
        if not result["download_library_url"]:
            result["download_library_url"] = base_url
            result["presentations_url"] = base_url


async def discover_ir_page(ticker: str) -> dict:
    """Convenience function to discover IR page."""
    async with IRDiscoverer() as discoverer:
        return await discoverer.discover(ticker)


async def main():
    """Test IR discoverer on multiple tickers."""
    tickers = ["ARWR", "ALNY", "IONS", "VKTX", "MRNA"]

    print("=" * 70)
    print("IR Page Discovery Test")
    print("=" * 70)

    async with IRDiscoverer() as discoverer:
        for ticker in tickers:
            print(f"\n{ticker}:")
            result = await discoverer.discover(ticker)
            print(f"  Company: {result.get('company_name', 'Unknown')}")
            print(f"  Domain: {result.get('domain')}")
            print(f"  IR URL: {result.get('ir_base_url')}")
            print(f"  Downloads: {result.get('download_library_url')}")
            print(f"  Method: {result.get('discovery_method')}")
            print(f"  Verified: {result.get('verified')}")


if __name__ == "__main__":
    asyncio.run(main())
