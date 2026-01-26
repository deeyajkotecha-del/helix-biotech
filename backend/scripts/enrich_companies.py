"""
Enrich XBI Companies with SEC EDGAR, ClinicalTrials.gov, and SEC Filings data

This script fetches comprehensive data for each company:
1. SEC EDGAR - Company info, CIK lookup
2. ClinicalTrials.gov - Active and completed trials
3. SEC Filings - Recent 10-K, 10-Q, 8-K filings
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class CompanyInfo:
    ticker: str
    name: str
    cik: Optional[str] = None
    sic: Optional[str] = None
    sic_description: Optional[str] = None
    state: Optional[str] = None
    fiscal_year_end: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None


@dataclass
class ClinicalTrial:
    nct_id: str
    title: str
    status: str
    phase: Optional[str]
    conditions: List[str]
    interventions: List[str]
    sponsor: Optional[str]
    start_date: Optional[str]
    completion_date: Optional[str]
    enrollment: Optional[int]
    study_type: Optional[str]


@dataclass
class SECFiling:
    accession_number: str
    form_type: str
    filing_date: str
    description: Optional[str]
    primary_document: Optional[str]
    filing_url: Optional[str]


class SECEdgarClient:
    """Client for SEC EDGAR API"""

    BASE_URL = "https://data.sec.gov"
    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helix Intelligence research@helix.com",
            "Accept": "application/json"
        })
        self._ticker_to_cik = None

    def _load_ticker_mapping(self):
        """Load ticker to CIK mapping from SEC"""
        if self._ticker_to_cik is not None:
            return

        print("Loading SEC ticker to CIK mapping...")
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
            print(f"Loaded {len(self._ticker_to_cik)} ticker mappings")
        except Exception as e:
            print(f"Error loading ticker mapping: {e}")
            self._ticker_to_cik = {}

    def get_cik(self, ticker: str) -> Optional[str]:
        """Get CIK for a ticker"""
        self._load_ticker_mapping()
        info = self._ticker_to_cik.get(ticker.upper())
        return info["cik"] if info else None

    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        """Get company info from SEC EDGAR"""
        cik = self.get_cik(ticker)
        if not cik:
            return None

        try:
            url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            return CompanyInfo(
                ticker=ticker.upper(),
                name=data.get("name", ""),
                cik=cik,
                sic=data.get("sic"),
                sic_description=data.get("sicDescription"),
                state=data.get("stateOfIncorporation"),
                fiscal_year_end=data.get("fiscalYearEnd"),
                website=data.get("website"),
            )
        except Exception as e:
            print(f"Error fetching company info for {ticker}: {e}")
            return None

    def get_recent_filings(self, ticker: str, limit: int = 10) -> List[SECFiling]:
        """Get recent SEC filings for a company"""
        cik = self.get_cik(ticker)
        if not cik:
            return []

        try:
            url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            filings = []
            recent = data.get("filings", {}).get("recent", {})

            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            dates = recent.get("filingDate", [])
            descriptions = recent.get("primaryDocDescription", [])
            documents = recent.get("primaryDocument", [])

            for i in range(min(limit, len(forms))):
                accession = accessions[i].replace("-", "")
                filings.append(SECFiling(
                    accession_number=accessions[i],
                    form_type=forms[i],
                    filing_date=dates[i],
                    description=descriptions[i] if i < len(descriptions) else None,
                    primary_document=documents[i] if i < len(documents) else None,
                    filing_url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{documents[i]}" if i < len(documents) else None
                ))

            return filings
        except Exception as e:
            print(f"Error fetching filings for {ticker}: {e}")
            return []


class ClinicalTrialsClient:
    """Client for ClinicalTrials.gov API v2"""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Helix Intelligence research@helix.com"
        })

    def search_trials(self, company_name: str, drug_name: Optional[str] = None, limit: int = 20) -> List[ClinicalTrial]:
        """Search for clinical trials by company name or drug"""
        trials = []

        # Search by sponsor (company name)
        query = f"AREA[LeadSponsorName]{company_name}"
        if drug_name:
            query = f"{query} OR AREA[InterventionName]{drug_name}"

        try:
            params = {
                "query.term": company_name,
                "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED",
                "pageSize": limit,
                "format": "json"
            }

            resp = self.session.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                design_module = protocol.get("designModule", {})
                sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
                conditions_module = protocol.get("conditionsModule", {})
                interventions_module = protocol.get("armsInterventionsModule", {})

                # Extract phases
                phases = design_module.get("phases", [])
                phase = phases[0] if phases else None

                # Extract conditions
                conditions = conditions_module.get("conditions", [])

                # Extract interventions
                interventions = []
                for intervention in interventions_module.get("interventions", []):
                    interventions.append(intervention.get("name", ""))

                # Extract sponsor
                lead_sponsor = sponsor_module.get("leadSponsor", {})
                sponsor_name = lead_sponsor.get("name")

                trials.append(ClinicalTrial(
                    nct_id=id_module.get("nctId", ""),
                    title=id_module.get("briefTitle", ""),
                    status=status_module.get("overallStatus", ""),
                    phase=phase,
                    conditions=conditions,
                    interventions=interventions,
                    sponsor=sponsor_name,
                    start_date=status_module.get("startDateStruct", {}).get("date"),
                    completion_date=status_module.get("completionDateStruct", {}).get("date"),
                    enrollment=design_module.get("enrollmentInfo", {}).get("count"),
                    study_type=design_module.get("studyType")
                ))

            return trials

        except Exception as e:
            print(f"Error searching trials for {company_name}: {e}")
            return []


class CompanyEnricher:
    """Main class to enrich company data from multiple sources"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).parent.parent / "data" / "helix.db")
        self.sec_client = SECEdgarClient()
        self.trials_client = ClinicalTrialsClient()
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Companies table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cik TEXT,
                sic TEXT,
                sic_description TEXT,
                state TEXT,
                fiscal_year_end TEXT,
                description TEXT,
                website TEXT,
                employees INTEGER,
                xbi_weight REAL,
                updated_at TEXT
            )
        """)

        # Clinical trials table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clinical_trials (
                nct_id TEXT PRIMARY KEY,
                company_ticker TEXT,
                title TEXT,
                status TEXT,
                phase TEXT,
                conditions TEXT,
                interventions TEXT,
                sponsor TEXT,
                start_date TEXT,
                completion_date TEXT,
                enrollment INTEGER,
                study_type TEXT,
                updated_at TEXT,
                FOREIGN KEY (company_ticker) REFERENCES companies(ticker)
            )
        """)

        # SEC filings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sec_filings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_ticker TEXT,
                accession_number TEXT,
                form_type TEXT,
                filing_date TEXT,
                description TEXT,
                primary_document TEXT,
                filing_url TEXT,
                updated_at TEXT,
                FOREIGN KEY (company_ticker) REFERENCES companies(ticker),
                UNIQUE(company_ticker, accession_number)
            )
        """)

        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trials_ticker ON clinical_trials(company_ticker)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trials_status ON clinical_trials(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_filings_ticker ON sec_filings(company_ticker)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_filings_form ON sec_filings(form_type)")

        conn.commit()
        conn.close()
        print(f"Database initialized at {self.db_path}")

    def load_xbi_holdings(self) -> List[Dict]:
        """Load XBI holdings from JSON file"""
        holdings_path = self.data_dir / "xbi_holdings.json"
        if not holdings_path.exists():
            print("XBI holdings file not found. Run fetch_xbi_holdings.py first.")
            return []

        with open(holdings_path) as f:
            data = json.load(f)
            return data.get("holdings", [])

    def enrich_company(self, ticker: str, name: str, weight: float = None) -> Dict:
        """Enrich a single company with all data sources"""
        print(f"\n{'='*60}")
        print(f"Enriching {ticker}: {name}")
        print(f"{'='*60}")

        result = {
            "ticker": ticker,
            "name": name,
            "xbi_weight": weight,
            "company_info": None,
            "clinical_trials": [],
            "sec_filings": []
        }

        # 1. Get SEC EDGAR company info
        print(f"  Fetching SEC EDGAR info...")
        company_info = self.sec_client.get_company_info(ticker)
        if company_info:
            result["company_info"] = asdict(company_info)
            print(f"    CIK: {company_info.cik}")
            print(f"    SIC: {company_info.sic_description}")
        else:
            print(f"    No SEC data found")

        time.sleep(0.2)  # Rate limiting

        # 2. Get SEC filings
        print(f"  Fetching SEC filings...")
        filings = self.sec_client.get_recent_filings(ticker, limit=10)
        result["sec_filings"] = [asdict(f) for f in filings]
        print(f"    Found {len(filings)} recent filings")
        if filings:
            form_types = set(f.form_type for f in filings)
            print(f"    Types: {', '.join(form_types)}")

        time.sleep(0.2)  # Rate limiting

        # 3. Get clinical trials
        print(f"  Fetching ClinicalTrials.gov data...")
        # Try multiple search strategies
        trials = []
        # First try full company name
        trials = self.trials_client.search_trials(name, limit=20)
        # If no results, try first word
        if not trials:
            search_name = name.split(" ")[0]
            trials = self.trials_client.search_trials(search_name, limit=20)
        # Also try ticker as a last resort
        if not trials:
            trials = self.trials_client.search_trials(ticker, limit=20)
        result["clinical_trials"] = [asdict(t) for t in trials]
        print(f"    Found {len(trials)} clinical trials")
        if trials:
            phases = set(t.phase for t in trials if t.phase)
            statuses = set(t.status for t in trials)
            print(f"    Phases: {', '.join(phases)}")
            print(f"    Statuses: {', '.join(statuses)}")

        time.sleep(0.3)  # Rate limiting for ClinicalTrials.gov

        return result

    def save_to_database(self, enriched_data: Dict):
        """Save enriched data to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        ticker = enriched_data["ticker"]
        now = datetime.utcnow().isoformat()

        # Save company info
        company = enriched_data.get("company_info") or {}
        cur.execute("""
            INSERT OR REPLACE INTO companies
            (ticker, name, cik, sic, sic_description, state, fiscal_year_end,
             description, website, employees, xbi_weight, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            enriched_data["name"],
            company.get("cik"),
            company.get("sic"),
            company.get("sic_description"),
            company.get("state"),
            company.get("fiscal_year_end"),
            company.get("description"),
            company.get("website"),
            company.get("employees"),
            enriched_data.get("xbi_weight"),
            now
        ))

        # Save clinical trials
        for trial in enriched_data.get("clinical_trials", []):
            cur.execute("""
                INSERT OR REPLACE INTO clinical_trials
                (nct_id, company_ticker, title, status, phase, conditions, interventions,
                 sponsor, start_date, completion_date, enrollment, study_type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trial["nct_id"],
                ticker,
                trial["title"],
                trial["status"],
                trial["phase"],
                json.dumps(trial["conditions"]),
                json.dumps(trial["interventions"]),
                trial["sponsor"],
                trial["start_date"],
                trial["completion_date"],
                trial["enrollment"],
                trial["study_type"],
                now
            ))

        # Save SEC filings
        for filing in enriched_data.get("sec_filings", []):
            cur.execute("""
                INSERT OR REPLACE INTO sec_filings
                (company_ticker, accession_number, form_type, filing_date,
                 description, primary_document, filing_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                filing["accession_number"],
                filing["form_type"],
                filing["filing_date"],
                filing["description"],
                filing["primary_document"],
                filing["filing_url"],
                now
            ))

        conn.commit()
        conn.close()

    def run(self, limit: Optional[int] = None, tickers: Optional[List[str]] = None):
        """Run enrichment for all XBI holdings or specific tickers"""
        self.init_database()

        if tickers:
            holdings = [{"ticker": t, "name": t, "weight": None} for t in tickers]
        else:
            holdings = self.load_xbi_holdings()

        if limit:
            holdings = holdings[:limit]

        print(f"\nEnriching {len(holdings)} companies...")

        results = []
        for i, holding in enumerate(holdings):
            ticker = holding["ticker"]
            name = holding["name"]
            weight = holding.get("weight")

            print(f"\n[{i+1}/{len(holdings)}]", end="")

            try:
                enriched = self.enrich_company(ticker, name, weight)
                self.save_to_database(enriched)
                results.append(enriched)
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

        # Save summary
        summary_path = self.data_dir / "enrichment_summary.json"
        with open(summary_path, "w") as f:
            json.dump({
                "enriched_at": datetime.utcnow().isoformat(),
                "companies_count": len(results),
                "total_trials": sum(len(r["clinical_trials"]) for r in results),
                "total_filings": sum(len(r["sec_filings"]) for r in results),
            }, f, indent=2)

        print(f"\n{'='*60}")
        print("ENRICHMENT COMPLETE")
        print(f"{'='*60}")
        print(f"Companies enriched: {len(results)}")
        print(f"Total clinical trials: {sum(len(r['clinical_trials']) for r in results)}")
        print(f"Total SEC filings: {sum(len(r['sec_filings']) for r in results)}")
        print(f"Database: {self.db_path}")

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enrich XBI companies with SEC and clinical trial data")
    parser.add_argument("--limit", type=int, help="Limit number of companies to enrich")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to enrich")
    parser.add_argument("--db", type=str, help="Path to SQLite database")

    args = parser.parse_args()

    enricher = CompanyEnricher(db_path=args.db)
    enricher.run(limit=args.limit, tickers=args.tickers)


if __name__ == "__main__":
    main()
