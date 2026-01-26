"""
SEC EDGAR 13F Scraper

Pulls 13F filings from biotech specialist hedge funds.
The SEC requires all institutional investment managers with >$100M AUM to file quarterly.

Data source: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=13F
"""

import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
import time
import re
import json
from pathlib import Path

# SEC requires a User-Agent header with contact info
HEADERS = {
    "User-Agent": "BiotechIntel Research contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}

# Rate limit: SEC asks for max 10 requests per second
RATE_LIMIT_DELAY = 0.1


@dataclass
class Fund:
    """Investment fund that files 13F"""
    name: str
    cik: str
    is_biotech_specialist: bool = False


@dataclass 
class Holding:
    """Single holding from a 13F filing"""
    company_name: str
    cusip: str
    value: int  # in thousands (as reported)
    shares: int
    share_type: str  # "SH" for shares, "PRN" for principal
    investment_discretion: str
    voting_authority_sole: int
    voting_authority_shared: int
    voting_authority_none: int


@dataclass
class Filing13F:
    """Complete 13F filing"""
    fund_cik: str
    fund_name: str
    filing_date: date
    report_date: date  # Quarter end
    accession_number: str
    holdings: list[Holding]
    total_value: int  # in thousands


# Biotech specialist funds to track
# These are the funds whose moves actually matter
BIOTECH_SPECIALIST_FUNDS = [
    Fund("Baker Bros. Advisors LP", "0001263508", True),
    Fund("RA Capital Management, L.P.", "0001555283", True),
    Fund("Perceptive Advisors LLC", "0001291922", True),
    Fund("OrbiMed Advisors LLC", "0001055504", True),
    Fund("Avoro Capital Advisors LLC", "0001730627", True),  # Formerly Vivo Capital
    Fund("RTW Investments, LP", "0001599738", True),
    Fund("EcoR1 Capital, LLC", "0001633589", True),
    Fund("Redmile Group, LLC", "0001520115", True),
    Fund("Boxer Capital, LLC", "0001423053", True),
    Fund("Adage Capital Partners, L.P.", "0001299352", True),
    Fund("Rock Springs Capital Management LP", "0001581811", True),
    Fund("Farallon Capital Management, L.L.C.", "0001020851", True),
    Fund("Deerfield Management Company, L.P.", "0001509391", True),
    Fund("Casdin Capital, LLC", "0001599445", True),
    Fund("Cormorant Asset Management, LP", "0001630085", True),
    Fund("Citadel Advisors LLC", "0001423053", False),  # Generalist but important
    Fund("Point72 Asset Management, L.P.", "0001603466", False),  # Generalist
]


class SECEdgarScraper:
    """Scraper for SEC EDGAR 13F filings"""
    
    BASE_URL = "https://www.sec.gov"
    EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
    
    def __init__(self, data_dir: str = "data/13f"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def _rate_limit(self):
        """Respect SEC rate limits"""
        time.sleep(RATE_LIMIT_DELAY)
    
    def get_recent_filings(self, cik: str, count: int = 4) -> list[dict]:
        """
        Get recent 13F-HR filings for a fund.
        
        Args:
            cik: SEC Central Index Key (with or without leading zeros)
            count: Number of recent filings to retrieve
            
        Returns:
            List of filing metadata dicts
        """
        # Normalize CIK to 10 digits with leading zeros
        cik_normalized = cik.lstrip("0").zfill(10)
        
        # Use SEC's EDGAR API
        url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "CIK": cik_normalized,
            "type": "13F-HR",
            "dateb": "",
            "owner": "include",
            "count": count,
            "output": "atom"
        }
        
        self._rate_limit()
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        # Parse Atom feed
        filings = []
        root = ET.fromstring(response.content)
        
        # Define namespace
        ns = {
            "atom": "http://www.w3.org/2005/Atom"
        }
        
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            link = entry.find("atom:link", ns)
            updated = entry.find("atom:updated", ns)
            
            if title is not None and link is not None:
                # Extract accession number from link
                href = link.get("href", "")
                accession_match = re.search(r"(\d{10}-\d{2}-\d{6})", href)
                
                filings.append({
                    "title": title.text,
                    "link": href,
                    "accession_number": accession_match.group(1) if accession_match else None,
                    "updated": updated.text if updated is not None else None,
                    "cik": cik_normalized
                })
        
        return filings
    
    def get_filing_index(self, cik: str, accession_number: str) -> dict:
        """
        Get the index of documents in a filing.
        
        Returns dict with paths to primary documents and info table.
        """
        # Format accession number for URL (remove dashes)
        acc_formatted = accession_number.replace("-", "")
        cik_normalized = cik.lstrip("0").zfill(10)
        
        index_url = f"{self.BASE_URL}/Archives/edgar/data/{cik_normalized}/{acc_formatted}/index.json"
        
        self._rate_limit()
        response = self.session.get(index_url)
        response.raise_for_status()
        
        return response.json()
    
    def get_13f_info_table(self, cik: str, accession_number: str) -> list[Holding]:
        """
        Parse the 13F information table (holdings data).
        
        The info table is an XML file containing all holdings.
        """
        acc_formatted = accession_number.replace("-", "")
        cik_normalized = cik.lstrip("0").zfill(10)
        
        # First get the filing index to find the info table file
        try:
            index = self.get_filing_index(cik, accession_number)
        except Exception as e:
            print(f"Error getting index for {accession_number}: {e}")
            return []
        
        # Find the info table XML file
        info_table_file = None
        directory = index.get("directory", {})
        items = directory.get("item", [])
        
        for item in items:
            name = item.get("name", "").lower()
            if "infotable" in name and name.endswith(".xml"):
                info_table_file = item.get("name")
                break
            # Sometimes it's named differently
            if "information" in name and "table" in name and name.endswith(".xml"):
                info_table_file = item.get("name")
                break
        
        if not info_table_file:
            # Try common naming patterns
            for item in items:
                name = item.get("name", "")
                if name.endswith(".xml") and "primary" not in name.lower():
                    info_table_file = name
                    break
        
        if not info_table_file:
            print(f"Could not find info table for {accession_number}")
            return []
        
        # Download and parse the info table
        info_url = f"{self.BASE_URL}/Archives/edgar/data/{cik_normalized}/{acc_formatted}/{info_table_file}"
        
        self._rate_limit()
        response = self.session.get(info_url)
        response.raise_for_status()
        
        return self._parse_info_table_xml(response.content)
    
    def _parse_info_table_xml(self, xml_content: bytes) -> list[Holding]:
        """Parse 13F info table XML into Holding objects"""
        holdings = []
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
            return []
        
        # Handle different namespace variations
        # The SEC uses different namespaces across filings
        namespaces = {
            "ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable",
            "ns2": "http://www.sec.gov/edgar/thirteenf"
        }
        
        # Try to find infoTable entries
        info_tables = root.findall(".//ns:infoTable", namespaces)
        if not info_tables:
            info_tables = root.findall(".//{http://www.sec.gov/edgar/document/thirteenf/informationtable}infoTable")
        if not info_tables:
            # Try without namespace
            info_tables = root.findall(".//infoTable")
        if not info_tables:
            # Try iterating all elements
            for elem in root.iter():
                if "infoTable" in elem.tag:
                    info_tables = root.findall(f".//{elem.tag}")
                    break
        
        for entry in info_tables:
            try:
                holding = self._parse_holding_entry(entry)
                if holding:
                    holdings.append(holding)
            except Exception as e:
                print(f"Error parsing holding entry: {e}")
                continue
        
        return holdings
    
    def _parse_holding_entry(self, entry: ET.Element) -> Optional[Holding]:
        """Parse a single holding entry from the info table"""
        
        def get_text(parent, tag_name):
            """Helper to get text from element, handling namespaces"""
            # Try various namespace patterns
            for elem in parent.iter():
                if tag_name.lower() in elem.tag.lower():
                    return elem.text
            return None
        
        name = get_text(entry, "nameOfIssuer")
        cusip = get_text(entry, "cusip")
        value = get_text(entry, "value")
        shares_or_principal = get_text(entry, "sshPrnamt")
        share_type = get_text(entry, "sshPrnamtType")
        investment_discretion = get_text(entry, "investmentDiscretion")
        
        # Voting authority
        voting_sole = get_text(entry, "Sole") or get_text(entry, "votingAuthoritySole")
        voting_shared = get_text(entry, "Shared") or get_text(entry, "votingAuthorityShared")
        voting_none = get_text(entry, "None") or get_text(entry, "votingAuthorityNone")
        
        if not name or not cusip:
            return None
        
        return Holding(
            company_name=name.strip() if name else "",
            cusip=cusip.strip() if cusip else "",
            value=int(value) if value else 0,
            shares=int(shares_or_principal) if shares_or_principal else 0,
            share_type=share_type.strip() if share_type else "SH",
            investment_discretion=investment_discretion.strip() if investment_discretion else "",
            voting_authority_sole=int(voting_sole) if voting_sole else 0,
            voting_authority_shared=int(voting_shared) if voting_shared else 0,
            voting_authority_none=int(voting_none) if voting_none else 0,
        )
    
    def get_primary_document(self, cik: str, accession_number: str) -> dict:
        """
        Get the primary document (13F-HR) to extract filing metadata.
        
        This contains the report date, filing date, and fund info.
        """
        acc_formatted = accession_number.replace("-", "")
        cik_normalized = cik.lstrip("0").zfill(10)
        
        # Get filing index
        index = self.get_filing_index(cik, accession_number)
        
        # Find primary doc
        primary_doc = None
        items = index.get("directory", {}).get("item", [])
        
        for item in items:
            name = item.get("name", "").lower()
            if "primary_doc" in name or (name.endswith(".xml") and "infotable" not in name):
                primary_doc = item.get("name")
                break
        
        if not primary_doc:
            return {}
        
        doc_url = f"{self.BASE_URL}/Archives/edgar/data/{cik_normalized}/{acc_formatted}/{primary_doc}"
        
        self._rate_limit()
        response = self.session.get(doc_url)
        response.raise_for_status()
        
        # Parse metadata
        return self._parse_primary_document(response.content)
    
    def _parse_primary_document(self, xml_content: bytes) -> dict:
        """Extract metadata from primary document"""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return {}
        
        metadata = {}
        
        # Look for common fields
        for elem in root.iter():
            tag_lower = elem.tag.lower()
            if "reportcalendarorquarter" in tag_lower:
                metadata["report_date"] = elem.text
            elif "filingmanager" in tag_lower:
                for child in elem:
                    if "name" in child.tag.lower():
                        metadata["fund_name"] = child.text
        
        return metadata
    
    def scrape_fund(self, fund: Fund, num_quarters: int = 4) -> list[Filing13F]:
        """
        Scrape recent 13F filings for a fund.
        
        Args:
            fund: Fund to scrape
            num_quarters: Number of quarterly filings to retrieve
            
        Returns:
            List of Filing13F objects with all holdings
        """
        print(f"Scraping {fund.name} (CIK: {fund.cik})...")
        
        filings_metadata = self.get_recent_filings(fund.cik, num_quarters)
        filings = []
        
        for meta in filings_metadata:
            if not meta.get("accession_number"):
                continue
                
            print(f"  Processing filing {meta['accession_number']}...")
            
            # Get holdings
            holdings = self.get_13f_info_table(fund.cik, meta["accession_number"])
            
            # Get primary document for dates
            primary_doc = self.get_primary_document(fund.cik, meta["accession_number"])
            
            # Parse dates
            report_date = None
            if primary_doc.get("report_date"):
                try:
                    report_date = datetime.strptime(
                        primary_doc["report_date"], "%m-%d-%Y"
                    ).date()
                except ValueError:
                    try:
                        report_date = datetime.strptime(
                            primary_doc["report_date"], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        pass
            
            filing_date = None
            if meta.get("updated"):
                try:
                    filing_date = datetime.fromisoformat(
                        meta["updated"].replace("Z", "+00:00")
                    ).date()
                except ValueError:
                    pass
            
            total_value = sum(h.value for h in holdings)
            
            filing = Filing13F(
                fund_cik=fund.cik,
                fund_name=primary_doc.get("fund_name", fund.name),
                filing_date=filing_date or date.today(),
                report_date=report_date or date.today(),
                accession_number=meta["accession_number"],
                holdings=holdings,
                total_value=total_value
            )
            
            filings.append(filing)
            print(f"    Found {len(holdings)} holdings, total value: ${total_value:,}K")
        
        return filings
    
    def save_filing_to_json(self, filing: Filing13F):
        """Save a filing to JSON for later processing"""
        filename = f"{filing.fund_cik}_{filing.accession_number}.json"
        filepath = self.data_dir / filename
        
        data = {
            "fund_cik": filing.fund_cik,
            "fund_name": filing.fund_name,
            "filing_date": filing.filing_date.isoformat() if filing.filing_date else None,
            "report_date": filing.report_date.isoformat() if filing.report_date else None,
            "accession_number": filing.accession_number,
            "total_value": filing.total_value,
            "holdings": [
                {
                    "company_name": h.company_name,
                    "cusip": h.cusip,
                    "value": h.value,
                    "shares": h.shares,
                    "share_type": h.share_type,
                    "investment_discretion": h.investment_discretion,
                }
                for h in filing.holdings
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved to {filepath}")


def scrape_all_specialist_funds(num_quarters: int = 2):
    """Scrape all biotech specialist funds"""
    scraper = SECEdgarScraper()
    all_filings = []
    
    for fund in BIOTECH_SPECIALIST_FUNDS:
        if not fund.is_biotech_specialist:
            continue
        
        try:
            filings = scraper.scrape_fund(fund, num_quarters)
            for filing in filings:
                scraper.save_filing_to_json(filing)
            all_filings.extend(filings)
        except Exception as e:
            print(f"Error scraping {fund.name}: {e}")
            continue
        
        # Be nice to SEC servers
        time.sleep(1)
    
    return all_filings


if __name__ == "__main__":
    # Example: Scrape most recent quarter for all specialist funds
    print("Starting 13F scraper for biotech specialist funds...")
    print("=" * 60)
    
    filings = scrape_all_specialist_funds(num_quarters=1)
    
    print("=" * 60)
    print(f"Scraped {len(filings)} filings total")
