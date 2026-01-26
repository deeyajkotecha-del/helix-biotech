"""
PubMed KOL (Key Opinion Leader) Extractor

Finds top researchers/physicians publishing on specific drugs or indications.
Extracts their contact information for expert network calls.

This is what funds pay $5-15K per call to GLG/Guidepoint for.
You're building the lead generation for free.
"""

import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import time
import re
from collections import defaultdict
import json
from pathlib import Path


# NCBI E-utilities base URL
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Rate limit: NCBI allows 3 requests/second without API key, 10/sec with key
RATE_LIMIT_DELAY = 0.35


@dataclass
class Author:
    """A publication author with extracted info"""
    full_name: str
    last_name: str
    first_name: str
    initials: str
    affiliation: str = ""
    email: str = ""
    orcid: str = ""
    
    # Computed fields
    institution: str = ""
    department: str = ""
    city: str = ""
    country: str = ""


@dataclass
class Publication:
    """A PubMed publication"""
    pmid: str
    title: str
    abstract: str
    journal: str
    publication_date: Optional[datetime]
    doi: str = ""
    authors: list[Author] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    publication_type: str = ""
    citation_count: int = 0


@dataclass
class KOL:
    """Key Opinion Leader profile"""
    name: str
    last_name: str
    first_name: str
    email: str
    institution: str
    department: str
    city: str
    country: str
    
    # Metrics
    publication_count: int = 0
    first_author_count: int = 0
    last_author_count: int = 0  # Senior/corresponding author
    recent_publication_count: int = 0  # Last 3 years
    
    # Publications
    pmids: list[str] = field(default_factory=list)
    
    # Relevance
    relevance_score: float = 0.0


class PubMedKOLExtractor:
    """
    Extracts KOLs from PubMed based on search queries.
    
    Usage:
        extractor = PubMedKOLExtractor()
        kols = extractor.find_kols("obefazimod ulcerative colitis")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize extractor.
        
        Args:
            api_key: NCBI API key (optional but recommended for higher rate limits)
                    Get one free at: https://www.ncbi.nlm.nih.gov/account/settings/
        """
        self.api_key = api_key
        self.session = requests.Session()
    
    def _make_request(self, url: str, params: dict) -> requests.Response:
        """Make a rate-limited request to NCBI"""
        if self.api_key:
            params["api_key"] = self.api_key
        
        time.sleep(RATE_LIMIT_DELAY)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response
    
    def search(self, query: str, max_results: int = 100) -> list[str]:
        """
        Search PubMed and return list of PMIDs.
        
        Args:
            query: PubMed search query (supports boolean operators)
            max_results: Maximum number of results to return
            
        Returns:
            List of PubMed IDs
        """
        url = f"{PUBMED_BASE}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        
        response = self._make_request(url, params)
        data = response.json()
        
        return data.get("esearchresult", {}).get("idlist", [])
    
    def fetch_articles(self, pmids: list[str]) -> list[Publication]:
        """
        Fetch full article details for a list of PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of Publication objects with author details
        """
        if not pmids:
            return []
        
        publications = []
        
        # Fetch in batches of 100
        batch_size = 100
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            url = f"{PUBMED_BASE}/efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
            }
            
            response = self._make_request(url, params)
            batch_pubs = self._parse_pubmed_xml(response.content)
            publications.extend(batch_pubs)
        
        return publications
    
    def _parse_pubmed_xml(self, xml_content: bytes) -> list[Publication]:
        """Parse PubMed XML response into Publication objects"""
        publications = []
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
            return []
        
        for article in root.findall(".//PubmedArticle"):
            pub = self._parse_article(article)
            if pub:
                publications.append(pub)
        
        return publications
    
    def _parse_article(self, article_elem: ET.Element) -> Optional[Publication]:
        """Parse a single PubMed article element"""
        
        # Get PMID
        pmid_elem = article_elem.find(".//PMID")
        if pmid_elem is None:
            return None
        pmid = pmid_elem.text
        
        # Get title
        title_elem = article_elem.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else ""
        
        # Get abstract
        abstract_parts = []
        for abstract_elem in article_elem.findall(".//AbstractText"):
            if abstract_elem.text:
                label = abstract_elem.get("Label", "")
                if label:
                    abstract_parts.append(f"{label}: {abstract_elem.text}")
                else:
                    abstract_parts.append(abstract_elem.text)
        abstract = " ".join(abstract_parts)
        
        # Get journal
        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""
        
        # Get DOI
        doi = ""
        for id_elem in article_elem.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break
        
        # Get publication date
        pub_date = None
        date_elem = article_elem.find(".//PubDate")
        if date_elem is not None:
            year = date_elem.find("Year")
            month = date_elem.find("Month")
            day = date_elem.find("Day")
            
            try:
                year_val = int(year.text) if year is not None else 2000
                month_val = self._parse_month(month.text) if month is not None else 1
                day_val = int(day.text) if day is not None else 1
                pub_date = datetime(year_val, month_val, day_val)
            except (ValueError, TypeError):
                pass
        
        # Get authors
        authors = []
        for author_elem in article_elem.findall(".//Author"):
            author = self._parse_author(author_elem)
            if author:
                authors.append(author)
        
        # Get MeSH terms
        mesh_terms = []
        for mesh_elem in article_elem.findall(".//MeshHeading/DescriptorName"):
            if mesh_elem.text:
                mesh_terms.append(mesh_elem.text)
        
        # Get keywords
        keywords = []
        for kw_elem in article_elem.findall(".//Keyword"):
            if kw_elem.text:
                keywords.append(kw_elem.text)
        
        return Publication(
            pmid=pmid,
            title=title,
            abstract=abstract,
            journal=journal,
            publication_date=pub_date,
            doi=doi,
            authors=authors,
            keywords=keywords,
            mesh_terms=mesh_terms,
        )
    
    def _parse_author(self, author_elem: ET.Element) -> Optional[Author]:
        """Parse an author element"""
        
        last_name_elem = author_elem.find("LastName")
        first_name_elem = author_elem.find("ForeName")
        initials_elem = author_elem.find("Initials")
        
        if last_name_elem is None:
            return None
        
        last_name = last_name_elem.text or ""
        first_name = first_name_elem.text if first_name_elem is not None else ""
        initials = initials_elem.text if initials_elem is not None else ""
        
        full_name = f"{first_name} {last_name}".strip()
        
        # Get affiliation
        affiliation = ""
        affil_elem = author_elem.find(".//Affiliation")
        if affil_elem is not None and affil_elem.text:
            affiliation = affil_elem.text
        
        # Try to extract email from affiliation
        email = self._extract_email(affiliation)
        
        # Parse institution from affiliation
        institution, department, city, country = self._parse_affiliation(affiliation)
        
        return Author(
            full_name=full_name,
            last_name=last_name,
            first_name=first_name,
            initials=initials,
            affiliation=affiliation,
            email=email,
            institution=institution,
            department=department,
            city=city,
            country=country,
        )
    
    def _extract_email(self, text: str) -> str:
        """Extract email address from text"""
        if not text:
            return ""
        
        # Common email patterns
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        
        return match.group(0) if match else ""
    
    def _parse_affiliation(self, affiliation: str) -> tuple[str, str, str, str]:
        """
        Parse affiliation string to extract institution details.
        
        Returns: (institution, department, city, country)
        """
        if not affiliation:
            return "", "", "", ""
        
        # Common institution patterns
        institution = ""
        department = ""
        city = ""
        country = ""
        
        # Split by common delimiters
        parts = re.split(r'[,;]', affiliation)
        parts = [p.strip() for p in parts if p.strip()]
        
        # Look for institution keywords
        institution_keywords = [
            "University", "Hospital", "Institute", "Medical Center",
            "School of Medicine", "College", "Centre", "Center",
            "Clinic", "Foundation", "Laboratory"
        ]
        
        for part in parts:
            for keyword in institution_keywords:
                if keyword.lower() in part.lower():
                    institution = part
                    break
            if institution:
                break
        
        # Look for department
        dept_keywords = ["Department", "Division", "Section", "Unit"]
        for part in parts:
            for keyword in dept_keywords:
                if keyword.lower() in part.lower():
                    department = part
                    break
        
        # Look for country (usually last part)
        common_countries = [
            "USA", "United States", "UK", "United Kingdom", "Germany",
            "France", "Japan", "China", "Canada", "Australia", "Italy",
            "Spain", "Switzerland", "Netherlands", "Sweden", "Israel"
        ]
        
        for part in reversed(parts):
            for country_name in common_countries:
                if country_name.lower() in part.lower():
                    country = country_name
                    break
            if country:
                break
        
        return institution, department, city, country
    
    def _parse_month(self, month_str: str) -> int:
        """Convert month string to integer"""
        if not month_str:
            return 1
        
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        
        month_lower = month_str.lower()[:3]
        return month_map.get(month_lower, 1)
    
    def find_kols(
        self,
        query: str,
        max_publications: int = 100,
        min_publications: int = 2
    ) -> list[KOL]:
        """
        Find Key Opinion Leaders for a given search query.
        
        Args:
            query: Search query (drug name, indication, etc.)
            max_publications: Maximum publications to analyze
            min_publications: Minimum publications required to be considered a KOL
            
        Returns:
            List of KOL objects sorted by relevance
        """
        print(f"Searching PubMed for: {query}")
        
        # Search PubMed
        pmids = self.search(query, max_publications)
        print(f"Found {len(pmids)} publications")
        
        if not pmids:
            return []
        
        # Fetch article details
        print("Fetching article details...")
        publications = self.fetch_articles(pmids)
        print(f"Parsed {len(publications)} publications")
        
        # Aggregate authors
        author_stats = defaultdict(lambda: {
            "name": "",
            "last_name": "",
            "first_name": "",
            "email": "",
            "institution": "",
            "department": "",
            "city": "",
            "country": "",
            "affiliations": [],
            "emails": [],
            "pmids": [],
            "first_author_count": 0,
            "last_author_count": 0,
            "recent_count": 0,
        })
        
        cutoff_year = datetime.now().year - 3
        
        for pub in publications:
            if not pub.authors:
                continue
            
            for i, author in enumerate(pub.authors):
                # Create a unique key for this author
                key = f"{author.last_name.lower()}_{author.first_name.lower()[:1]}"
                
                stats = author_stats[key]
                
                # Update basic info
                stats["name"] = author.full_name
                stats["last_name"] = author.last_name
                stats["first_name"] = author.first_name
                
                # Collect affiliations and emails
                if author.affiliation:
                    stats["affiliations"].append(author.affiliation)
                if author.email:
                    stats["emails"].append(author.email)
                if author.institution:
                    stats["institution"] = author.institution
                if author.department:
                    stats["department"] = author.department
                if author.country:
                    stats["country"] = author.country
                
                # Track PMIDs
                stats["pmids"].append(pub.pmid)
                
                # Count author positions
                if i == 0:  # First author
                    stats["first_author_count"] += 1
                if i == len(pub.authors) - 1:  # Last author
                    stats["last_author_count"] += 1
                
                # Count recent publications
                if pub.publication_date and pub.publication_date.year >= cutoff_year:
                    stats["recent_count"] += 1
        
        # Convert to KOL objects
        kols = []
        for key, stats in author_stats.items():
            pub_count = len(stats["pmids"])
            
            if pub_count < min_publications:
                continue
            
            # Pick best email (most common or most recent)
            email = ""
            if stats["emails"]:
                email = max(set(stats["emails"]), key=stats["emails"].count)
            
            # Calculate relevance score
            # Weight: publications + first author bonus + last author bonus + recency
            relevance = (
                pub_count * 1.0 +
                stats["first_author_count"] * 0.5 +
                stats["last_author_count"] * 0.5 +
                stats["recent_count"] * 0.3
            )
            
            kol = KOL(
                name=stats["name"],
                last_name=stats["last_name"],
                first_name=stats["first_name"],
                email=email,
                institution=stats["institution"],
                department=stats["department"],
                city=stats["city"],
                country=stats["country"],
                publication_count=pub_count,
                first_author_count=stats["first_author_count"],
                last_author_count=stats["last_author_count"],
                recent_publication_count=stats["recent_count"],
                pmids=list(set(stats["pmids"])),
                relevance_score=relevance,
            )
            
            kols.append(kol)
        
        # Sort by relevance
        kols.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return kols
    
    def export_kols_to_csv(
        self,
        kols: list[KOL],
        output_path: str,
        query: str = ""
    ):
        """Export KOL list to CSV"""
        import csv
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Name", "Email", "Institution", "Department", "Country",
                "Publications", "First Author", "Last Author", "Recent (3yr)",
                "Relevance Score", "PMIDs"
            ])
            
            for kol in kols:
                writer.writerow([
                    kol.name,
                    kol.email,
                    kol.institution,
                    kol.department,
                    kol.country,
                    kol.publication_count,
                    kol.first_author_count,
                    kol.last_author_count,
                    kol.recent_publication_count,
                    round(kol.relevance_score, 2),
                    ";".join(kol.pmids[:5]),  # First 5 PMIDs
                ])
        
        print(f"Exported {len(kols)} KOLs to {output_path}")
    
    def export_kols_to_json(
        self,
        kols: list[KOL],
        output_path: str,
        query: str = ""
    ):
        """Export KOL list to JSON"""
        data = {
            "query": query,
            "generated_at": datetime.now().isoformat(),
            "kol_count": len(kols),
            "kols": [
                {
                    "name": kol.name,
                    "email": kol.email,
                    "institution": kol.institution,
                    "department": kol.department,
                    "country": kol.country,
                    "publication_count": kol.publication_count,
                    "first_author_count": kol.first_author_count,
                    "last_author_count": kol.last_author_count,
                    "recent_publication_count": kol.recent_publication_count,
                    "relevance_score": round(kol.relevance_score, 2),
                    "pmids": kol.pmids,
                }
                for kol in kols
            ]
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(kols)} KOLs to {output_path}")


def find_kols_for_drug(drug_name: str, indication: str = "") -> list[KOL]:
    """
    Convenience function to find KOLs for a specific drug.
    
    Args:
        drug_name: Name of the drug (e.g., "obefazimod")
        indication: Optional indication to narrow search (e.g., "ulcerative colitis")
        
    Returns:
        List of KOLs sorted by relevance
    """
    query = drug_name
    if indication:
        query = f"{drug_name} {indication}"
    
    extractor = PubMedKOLExtractor()
    return extractor.find_kols(query)


if __name__ == "__main__":
    # Example: Find KOLs for obefazimod in ulcerative colitis
    print("=" * 60)
    print("PubMed KOL Extractor")
    print("=" * 60)
    
    # You can change this to any drug/indication
    drug = "obefazimod"
    indication = "ulcerative colitis"
    
    print(f"\nSearching for KOLs: {drug} + {indication}")
    print("-" * 60)
    
    extractor = PubMedKOLExtractor()
    kols = extractor.find_kols(f"{drug} {indication}", max_publications=50)
    
    print(f"\nFound {len(kols)} KOLs")
    print("=" * 60)
    print("TOP KOLs:")
    print("=" * 60)
    
    for i, kol in enumerate(kols[:15], 1):
        print(f"\n{i}. {kol.name}")
        print(f"   Institution: {kol.institution or 'Unknown'}")
        print(f"   Email: {kol.email or 'Not found'}")
        print(f"   Publications: {kol.publication_count} "
              f"(First author: {kol.first_author_count}, "
              f"Last author: {kol.last_author_count})")
        print(f"   Recent (3yr): {kol.recent_publication_count}")
    
    # Export to files
    output_dir = Path("data/kols")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = f"{drug}_{indication}".replace(" ", "_").lower()
    extractor.export_kols_to_csv(kols, output_dir / f"{safe_name}_kols.csv", f"{drug} {indication}")
    extractor.export_kols_to_json(kols, output_dir / f"{safe_name}_kols.json", f"{drug} {indication}")
