"""
SatyaBio Entity Resolution

Maps drug names, company codes, informal references, and ambiguous mentions
to canonical entity IDs in the knowledge graph.

This replaces the simple alias mapping table from the old SatyaBio system
with a multi-strategy resolver that handles:
- Direct alias lookup (fastest path)
- Fuzzy matching for typos and abbreviations
- Context-aware resolution (target + modality + company narrows to one drug)
- IST detection (academic papers that reference a drug without naming the company)

Usage:
    from extraction.entity_resolver import EntityResolver

    resolver = EntityResolver(db_url="postgresql://...")

    # Direct lookup
    drug_id = resolver.resolve_drug("gilteritinib")
    drug_id = resolver.resolve_drug("ASP2215")  # same drug, company code
    drug_id = resolver.resolve_drug("Xospata")  # same drug, brand name

    # Context-aware (for IST detection)
    drug_id = resolver.resolve_drug_by_context(
        target="FLT3",
        modality="small_molecule",
        company="Astellas"
    )

    # Bulk resolve from a document
    entities = resolver.resolve_document_entities(text="...press release text...")
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""
    entity_type: str       # 'drug', 'target', 'company', 'indication'
    entity_id: str         # UUID from knowledge graph
    canonical_name: str    # The canonical name we resolved to
    match_method: str      # 'exact_alias', 'fuzzy', 'context', 'provisional'
    confidence: float      # 0-1
    input_text: str        # What was passed in


@dataclass
class UnresolvedEntity:
    """An entity mention we couldn't resolve — flagged for human review."""
    entity_type: str
    input_text: str
    context: str           # Surrounding text for review
    candidates: list       # Top fuzzy match candidates
    source_document: str


class EntityResolver:
    """
    Multi-strategy entity resolver for biotech knowledge graph.

    Resolution priority:
    1. Exact alias match (case-insensitive) — instant
    2. Fuzzy string match against all aliases — catches typos
    3. Context-based resolution — target + modality + company
    4. Provisional entity creation — new drug not yet in graph
    """

    def __init__(self, db_url: str, fuzzy_threshold: float = 0.85):
        self.db_url = db_url
        self.fuzzy_threshold = fuzzy_threshold
        self._conn = None
        # Cache alias table in memory for fast lookups
        self._alias_cache: dict[str, tuple[str, str]] = {}  # lowercase alias -> (drug_id, canonical_name)
        self._target_cache: dict[str, str] = {}  # lowercase symbol -> target_id
        self._company_cache: dict[str, str] = {}  # lowercase name/ticker -> company_id

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self):
        """Connect to Postgres and load caches."""
        self._conn = psycopg2.connect(self.db_url)
        self._load_caches()

    def _load_caches(self):
        """Load alias tables into memory for fast resolution."""
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Drug aliases
            cur.execute("""
                SELECT da.alias, da.drug_id, d.canonical_name
                FROM drug_aliases da
                JOIN drugs d ON da.drug_id = d.drug_id
            """)
            for row in cur.fetchall():
                self._alias_cache[row["alias"].lower()] = (
                    str(row["drug_id"]),
                    row["canonical_name"],
                )
            # Also add canonical names as aliases
            cur.execute("SELECT drug_id, canonical_name FROM drugs")
            for row in cur.fetchall():
                self._alias_cache[row["canonical_name"].lower()] = (
                    str(row["drug_id"]),
                    row["canonical_name"],
                )

            # Targets — use 'name' column (gene symbol) from existing schema
            cur.execute("SELECT target_id, name, display_name FROM targets")
            for row in cur.fetchall():
                self._target_cache[row["name"].lower()] = str(row["target_id"])
                if row["display_name"]:
                    self._target_cache[row["display_name"].lower()] = str(row["target_id"])

            # Target aliases
            cur.execute("SELECT target_id, alias FROM target_aliases")
            for row in cur.fetchall():
                self._target_cache[row["alias"].lower()] = str(row["target_id"])

    # ------------------------------------------------------------------
    # Drug resolution
    # ------------------------------------------------------------------

    def resolve_drug(self, name: str) -> Optional[ResolvedEntity]:
        """
        Resolve a drug name to a canonical entity.
        Tries exact match first, then fuzzy.
        """
        normalized = name.strip().lower()

        # Strategy 1: Exact alias match
        if normalized in self._alias_cache:
            drug_id, canonical = self._alias_cache[normalized]
            return ResolvedEntity(
                entity_type="drug",
                entity_id=drug_id,
                canonical_name=canonical,
                match_method="exact_alias",
                confidence=1.0,
                input_text=name,
            )

        # Strategy 2: Fuzzy match
        best_match = None
        best_score = 0.0
        for alias, (drug_id, canonical) in self._alias_cache.items():
            score = SequenceMatcher(None, normalized, alias).ratio()
            if score > best_score:
                best_score = score
                best_match = (drug_id, canonical, alias)

        if best_match and best_score >= self.fuzzy_threshold:
            drug_id, canonical, matched_alias = best_match
            return ResolvedEntity(
                entity_type="drug",
                entity_id=drug_id,
                canonical_name=canonical,
                match_method="fuzzy",
                confidence=best_score,
                input_text=name,
            )

        return None

    def resolve_drug_by_context(
        self,
        target: Optional[str] = None,
        modality: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Optional[ResolvedEntity]:
        """
        Resolve a drug by clinical context rather than name.
        Useful for ISTs that describe "a selective FLT3 inhibitor"
        without naming the drug directly.
        """
        if not self._conn:
            return None

        conditions = []
        params = []

        if target:
            conditions.append("""
                d.drug_id IN (
                    SELECT dt.drug_id FROM drug_targets dt
                    JOIN targets t ON dt.target_id = t.target_id
                    WHERE LOWER(t.name) = LOWER(%s)
                )
            """)
            params.append(target)

        if modality:
            conditions.append("LOWER(d.modality) = LOWER(%s)")
            params.append(modality)

        if company:
            conditions.append("""
                (LOWER(d.company_ticker) = LOWER(%s) OR LOWER(d.company_name) ILIKE %s)
            """)
            params.extend([company, f"%{company}%"])

        if not conditions:
            return None

        query = f"""
            SELECT d.drug_id, d.canonical_name
            FROM drugs d
            WHERE {' AND '.join(conditions)}
        """

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()

        if len(results) == 1:
            return ResolvedEntity(
                entity_type="drug",
                entity_id=str(results[0]["drug_id"]),
                canonical_name=results[0]["canonical_name"],
                match_method="context",
                confidence=0.85,
                input_text=f"target={target}, modality={modality}, company={company}",
            )
        elif len(results) > 1:
            # Multiple candidates — return None, needs human review
            return None

        return None

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    def resolve_target(self, name: str) -> Optional[ResolvedEntity]:
        """Resolve a target name (gene symbol or full name)."""
        normalized = name.strip().lower()

        if normalized in self._target_cache:
            return ResolvedEntity(
                entity_type="target",
                entity_id=self._target_cache[normalized],
                canonical_name=name.upper() if len(name) <= 10 else name,
                match_method="exact_alias",
                confidence=1.0,
                input_text=name,
            )

        # Try common variations
        variations = [
            normalized.replace("-", ""),    # "PD-L1" -> "PDL1"
            normalized.replace(" ", ""),     # "PD L1" -> "PDL1"
            normalized.upper(),
        ]
        for var in variations:
            if var.lower() in self._target_cache:
                return ResolvedEntity(
                    entity_type="target",
                    entity_id=self._target_cache[var.lower()],
                    canonical_name=var.upper(),
                    match_method="fuzzy",
                    confidence=0.9,
                    input_text=name,
                )

        return None

    # ------------------------------------------------------------------
    # Bulk document entity extraction
    # ------------------------------------------------------------------

    def resolve_document_entities(
        self,
        text: str,
        source_document: str = "unknown",
    ) -> dict:
        """
        Scan a document text and resolve all recognizable drug, target,
        and company mentions.

        Returns:
            {
                "resolved_drugs": [ResolvedEntity, ...],
                "resolved_targets": [ResolvedEntity, ...],
                "unresolved": [UnresolvedEntity, ...],
            }
        """
        resolved_drugs = []
        resolved_targets = []
        unresolved = []

        # Scan for known aliases (case-insensitive word boundary match)
        text_lower = text.lower()

        # Check drug aliases
        seen_drug_ids = set()
        for alias, (drug_id, canonical) in self._alias_cache.items():
            if len(alias) < 3:  # Skip very short aliases to avoid false positives
                continue
            # Use word boundary matching
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, text_lower):
                if drug_id not in seen_drug_ids:
                    seen_drug_ids.add(drug_id)
                    resolved_drugs.append(ResolvedEntity(
                        entity_type="drug",
                        entity_id=drug_id,
                        canonical_name=canonical,
                        match_method="text_scan",
                        confidence=0.95,
                        input_text=alias,
                    ))

        # Check target symbols
        seen_target_ids = set()
        for symbol, target_id in self._target_cache.items():
            if len(symbol) < 3:
                continue
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, text_lower):
                if target_id not in seen_target_ids:
                    seen_target_ids.add(target_id)
                    resolved_targets.append(ResolvedEntity(
                        entity_type="target",
                        entity_id=target_id,
                        canonical_name=symbol.upper(),
                        match_method="text_scan",
                        confidence=0.9,
                        input_text=symbol,
                    ))

        return {
            "resolved_drugs": resolved_drugs,
            "resolved_targets": resolved_targets,
            "unresolved": unresolved,
        }

    # ------------------------------------------------------------------
    # Alias management
    # ------------------------------------------------------------------

    def add_alias(self, drug_id: str, alias: str, alias_type: str = "informal"):
        """Add a new alias for a drug and update the cache."""
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO drug_aliases (drug_id, alias, alias_type)
                   VALUES (%s, %s, %s) ON CONFLICT (alias) DO NOTHING""",
                (drug_id, alias, alias_type),
            )
        self._conn.commit()

        # Update cache
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT canonical_name FROM drugs WHERE drug_id = %s", (drug_id,)
            )
            row = cur.fetchone()
            if row:
                self._alias_cache[alias.lower()] = (drug_id, row["canonical_name"])

    def create_provisional_drug(
        self,
        name: str,
        company_ticker: Optional[str] = None,
        modality: Optional[str] = None,
    ) -> str:
        """
        Create a provisional drug entry for an unresolved entity.
        Returns the new drug_id.
        Provisional entries are flagged for human review.
        """
        with self._conn.cursor() as cur:
            cur.execute(
                """INSERT INTO drugs (canonical_name, company_ticker, modality, phase_highest, status)
                   VALUES (%s, %s, %s, 'Preclinical', 'Provisional')
                   ON CONFLICT (canonical_name, company_ticker) DO UPDATE
                   SET updated_at = NOW()
                   RETURNING drug_id""",
                (name, company_ticker, modality),
            )
            drug_id = str(cur.fetchone()[0])

            # Add the name as an alias
            cur.execute(
                """INSERT INTO drug_aliases (drug_id, alias, alias_type)
                   VALUES (%s, %s, 'provisional')
                   ON CONFLICT (alias) DO NOTHING""",
                (drug_id, name),
            )

        self._conn.commit()

        # Update cache
        self._alias_cache[name.lower()] = (drug_id, name)
        return drug_id
