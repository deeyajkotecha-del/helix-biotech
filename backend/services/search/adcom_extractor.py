"""
SatyaBio — AdCom Structured Extraction Pipeline

Extracts structured product-level data from FDA advisory committee transcripts
and briefing documents stored in the Neon database. For each AdCom document,
pulls out:

  1. Product name (brand + generic)
  2. Sponsor company
  3. Mechanism of action + mechanism class (for fast-follower linkage)
  4. Indication(s) discussed
  5. Committee vote (if transcript)
  6. Key concerns raised by committee members
  7. Regulatory pathway (standard, accelerated, breakthrough, etc.)

The mechanism_class field is the key to fast-follower intelligence: if the
committee raised durability-of-effect concerns about one AAV gene therapy,
that same concern applies to ALL AAV gene therapies regardless of company.

Usage:
    # Extract from all AdCom docs (uses Claude for extraction)
    python3 adcom_extractor.py --all

    # Extract for a specific committee
    python3 adcom_extractor.py --committee ODAC

    # Extract for a single document by ID
    python3 adcom_extractor.py --doc-id 423

    # Dry run — show what would be extracted without writing to DB
    python3 adcom_extractor.py --all --dry-run
"""

import os
import sys
import json
import argparse
import time
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
import anthropic

DATABASE_URL = os.environ.get("NEON_DATABASE_URL", "")

# ── Mechanism class taxonomy ──
# These are the groupings that enable fast-follower linkage.
# If the FDA raises a concern about "AAV gene therapy", it applies to
# ALL drugs in the "aav_gene_therapy" class.
MECHANISM_CLASSES = {
    # Immuno-oncology
    "anti_pd1": ["PD-1", "pembrolizumab", "nivolumab", "cemiplimab", "dostarlimab",
                 "retifanlimab", "toripalimab", "sintilimab", "tislelizumab",
                 "zimberelimab", "prolgolimab"],
    "anti_pdl1": ["PD-L1", "atezolizumab", "durvalumab", "avelumab",
                  "sugemalimab", "envafolimab", "cosibelimab"],
    "anti_ctla4": ["CTLA-4", "ipilimumab", "tremelimumab"],
    "bispecific_tcell": ["bispecific T-cell", "BiTE", "blinatumomab",
                         "teclistamab", "mosunetuzumab", "epcoritamab",
                         "glofitamab", "talquetamab", "elranatamab"],
    "car_t": ["CAR-T", "CAR T", "axicabtagene", "tisagenlecleucel",
              "lisocabtagene", "idecabtagene", "brexucabtagene",
              "ciltacabtagene"],
    "adc": ["antibody-drug conjugate", "ADC", "trastuzumab deruxtecan",
            "sacituzumab", "enfortumab vedotin", "tisotumab vedotin",
            "mirvetuximab", "datopotamab", "patritumab", "telisotuzumab",
            "ifinatamab", "tusamitamab"],

    # Targeted oncology
    "kras_inhibitor": ["KRAS", "sotorasib", "adagrasib", "divarasib",
                       "garsorasib", "olomorasib", "RMC-6236",
                       "daraxonrasib", "MRTX1133", "G12C", "G12D"],
    "egfr_inhibitor": ["EGFR", "osimertinib", "amivantamab", "lazertinib",
                       "furmonertinib", "sunvozertinib", "exon 20"],
    "braf_inhibitor": ["BRAF", "dabrafenib", "encorafenib", "vemurafenib",
                       "V600E", "V600K"],
    "bcl2_inhibitor": ["BCL-2", "venetoclax", "sonrotoclax", "lisaftoclax"],
    "parp_inhibitor": ["PARP", "olaparib", "niraparib", "rucaparib",
                       "talazoparib", "veliparib"],

    # Gene/cell therapy
    "aav_gene_therapy": ["AAV", "adeno-associated", "gene therapy", "gene replacement",
                         "voretigene", "onasemnogene", "valoctocogene",
                         "delandistrogene", "fidanacogene", "etranacogene",
                         "giroctocogene", "lovotibeglogene"],
    "lentiviral_gene_therapy": ["lentiviral", "lenti-D", "betibeglogene",
                                 "elivaldogene", "atidarsagene"],
    "gene_editing": ["CRISPR", "base editing", "gene editing", "exagamglogene",
                     "exa-cel", "CTX001"],
    "cell_therapy_non_cart": ["cell therapy", "TIL", "lifileucel", "NK cell",
                              "iPSC-derived"],

    # Metabolic / endocrine
    "glp1_agonist": ["GLP-1", "semaglutide", "tirzepatide", "liraglutide",
                     "dulaglutide", "orforglipron", "survodutide",
                     "retatrutide", "CagriSema", "pemvidutide"],
    "sglt2_inhibitor": ["SGLT2", "empagliflozin", "dapagliflozin",
                        "canagliflozin", "ertugliflozin", "sotagliflozin"],

    # Neuroscience
    "anti_amyloid": ["amyloid", "lecanemab", "donanemab", "aducanumab",
                     "gantenerumab", "solanezumab", "anti-amyloid"],
    "anti_tau": ["tau", "semorinemab", "zagotenemab", "bepranemab",
                 "E2814", "JNJ-63733657"],
    "antisense_oligo": ["antisense", "ASO", "nusinersen", "tofersen",
                        "tominersen", "jacifusen", "ION", "ISIS"],

    # Rare disease
    "enzyme_replacement": ["enzyme replacement", "ERT", "agalsidase",
                           "imiglucerase", "laronidase", "idursulfase",
                           "elosulfase", "vestronidase", "avalglucosidase"],
    "rna_interference": ["RNAi", "siRNA", "patisiran", "givosiran",
                         "lumasiran", "inclisiran", "vutrisiran", "fitusiran"],

    # Biosimilars
    "biosimilar": ["biosimilar", "biosimilarity", "interchangeable",
                   "interchangeability"],
}


def _get_connection():
    """Get a fresh Neon connection."""
    return psycopg2.connect(DATABASE_URL)


def setup_tables():
    """Create the adcom_products table if it doesn't exist."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS adcom_products (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            committee_code VARCHAR(30),    -- e.g., 'ODAC', 'CTGTAC'
            meeting_date VARCHAR(20),      -- YYYY-MM-DD
            product_name VARCHAR(300),     -- Brand name or code
            generic_name VARCHAR(300),     -- INN / generic
            sponsor VARCHAR(300),          -- Company name
            sponsor_ticker VARCHAR(20),    -- Mapped company ticker if known
            indication TEXT,               -- What indication was discussed
            mechanism_of_action TEXT,      -- Free-text MoA description
            mechanism_class VARCHAR(100),  -- Taxonomy key for fast-follower linkage
            modality VARCHAR(100),         -- small_molecule, antibody, adc, gene_therapy, etc.
            regulatory_pathway VARCHAR(100), -- standard, accelerated, breakthrough, priority, etc.
            vote_yes INTEGER,             -- Committee yes votes (NULL if not a voting meeting)
            vote_no INTEGER,              -- Committee no votes
            vote_abstain INTEGER,         -- Abstentions
            vote_outcome VARCHAR(50),     -- 'favorable', 'unfavorable', 'mixed', 'no_vote'
            key_concerns TEXT[],          -- Array of key concerns raised
            key_positives TEXT[],         -- Array of positive points noted
            extracted_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(document_id, product_name)
        );

        CREATE INDEX IF NOT EXISTS idx_adcom_products_committee
            ON adcom_products(committee_code);
        CREATE INDEX IF NOT EXISTS idx_adcom_products_mechanism_class
            ON adcom_products(mechanism_class);
        CREATE INDEX IF NOT EXISTS idx_adcom_products_sponsor
            ON adcom_products(sponsor);
        CREATE INDEX IF NOT EXISTS idx_adcom_products_date
            ON adcom_products(meeting_date);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✓ adcom_products table ready")


# ── Claude extraction ──

EXTRACTION_PROMPT = """You are an expert FDA regulatory analyst. Extract structured product information from this FDA advisory committee document.

For EACH product/drug discussed in the document, return a JSON array with one object per product. Each object must have:

{
  "product_name": "Brand name or company code (e.g., Leqembi, BLA 761269)",
  "generic_name": "INN or generic name (e.g., lecanemab-irmb)",
  "sponsor": "Sponsoring company name",
  "indication": "What indication/population was being discussed",
  "mechanism_of_action": "Brief MoA (e.g., anti-amyloid beta antibody, GLP-1 receptor agonist)",
  "modality": "One of: small_molecule, antibody, adc, bispecific, car_t, gene_therapy, cell_therapy, enzyme_replacement, antisense, sirna, peptide, vaccine, biosimilar, other",
  "regulatory_pathway": "One of: standard, accelerated, breakthrough, priority_review, fast_track, rems, orphan, or comma-separated if multiple",
  "vote_yes": null or integer,
  "vote_no": null or integer,
  "vote_abstain": null or integer,
  "vote_outcome": "favorable, unfavorable, mixed, or no_vote",
  "key_concerns": ["Array of 2-5 specific concerns raised by committee members. Be specific — 'durability of effect beyond 18 months not demonstrated' not just 'durability'. Include the actual issue, not generic categories."],
  "key_positives": ["Array of 2-5 positive points. Same specificity requirement."]
}

IMPORTANT RULES:
- If the document discusses multiple products (e.g., comparison, or multiple agenda items), return one object per product.
- For briefing documents that don't include votes, set vote fields to null and vote_outcome to "no_vote".
- Be SPECIFIC in concerns and positives — quote or closely paraphrase committee language. An investor reading these should understand the exact issue.
- If you can't determine a field, use null rather than guessing.
- Return ONLY the JSON array, no other text.
- If no product information can be extracted (e.g., procedural document), return an empty array [].
"""


def _classify_mechanism_class(moa_text: str, product_name: str, generic_name: str) -> Optional[str]:
    """
    Map a mechanism of action description to our taxonomy.
    Returns the mechanism_class key or None if no match.
    """
    if not moa_text and not product_name and not generic_name:
        return None

    text = f"{moa_text or ''} {product_name or ''} {generic_name or ''}".lower()

    for mclass, keywords in MECHANISM_CLASSES.items():
        for kw in keywords:
            if kw.lower() in text:
                return mclass

    return None


def extract_from_document(doc_id: int, dry_run: bool = False) -> list[dict]:
    """
    Extract product information from a single AdCom document.
    Uses Claude to read the document chunks and extract structured data.
    """
    conn = _get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get document metadata
    cur.execute("""
        SELECT id, ticker, company_name, title, date, doc_type
        FROM documents WHERE id = %s
    """, (doc_id,))
    doc = cur.fetchone()
    if not doc:
        print(f"  ✗ Document {doc_id} not found")
        cur.close()
        conn.close()
        return []

    # Get document chunks (first ~50 for extraction — enough context)
    cur.execute("""
        SELECT content, section_title, chunk_index
        FROM chunks
        WHERE document_id = %s
        ORDER BY chunk_index
        LIMIT 50
    """, (doc_id,))
    chunks = cur.fetchall()

    if not chunks:
        print(f"  ✗ No chunks for document {doc_id}")
        cur.close()
        conn.close()
        return []

    # Build document text for Claude (truncate to ~80K chars to stay within limits)
    doc_text = f"DOCUMENT: {doc['title']}\nDATE: {doc['date']}\nCOMMITTEE: {doc['company_name']}\nTYPE: {doc['doc_type']}\n\n"
    for chunk in chunks:
        section = f"\n[Section: {chunk['section_title']}]\n" if chunk['section_title'] else ""
        doc_text += f"{section}{chunk['content']}\n\n"
        if len(doc_text) > 80000:
            break

    # Extract committee code from ticker (e.g., "FDA_ODAC" -> "ODAC")
    committee_code = doc['ticker'].replace("FDA_", "") if doc['ticker'] else ""

    # Call Claude for extraction
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": doc_text}],
        )
        result_text = response.content[0].text.strip()

        # Parse JSON
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        products = json.loads(result_text)
        if not isinstance(products, list):
            products = [products]

    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse error for doc {doc_id}: {e}")
        cur.close()
        conn.close()
        return []
    except Exception as e:
        print(f"  ✗ Claude extraction error for doc {doc_id}: {e}")
        cur.close()
        conn.close()
        return []

    # Post-process: add mechanism_class and store
    extracted = []
    for prod in products:
        if not prod.get("product_name"):
            continue

        # Classify mechanism
        mclass = _classify_mechanism_class(
            prod.get("mechanism_of_action"),
            prod.get("product_name"),
            prod.get("generic_name"),
        )

        record = {
            "document_id": doc_id,
            "committee_code": committee_code,
            "meeting_date": doc['date'],
            "product_name": prod.get("product_name", ""),
            "generic_name": prod.get("generic_name"),
            "sponsor": prod.get("sponsor"),
            "sponsor_ticker": None,  # TODO: map to company ticker
            "indication": prod.get("indication"),
            "mechanism_of_action": prod.get("mechanism_of_action"),
            "mechanism_class": mclass,
            "modality": prod.get("modality"),
            "regulatory_pathway": prod.get("regulatory_pathway"),
            "vote_yes": prod.get("vote_yes"),
            "vote_no": prod.get("vote_no"),
            "vote_abstain": prod.get("vote_abstain"),
            "vote_outcome": prod.get("vote_outcome", "no_vote"),
            "key_concerns": prod.get("key_concerns", []),
            "key_positives": prod.get("key_positives", []),
        }
        extracted.append(record)

        if not dry_run:
            try:
                cur.execute("""
                    INSERT INTO adcom_products (
                        document_id, committee_code, meeting_date,
                        product_name, generic_name, sponsor, sponsor_ticker,
                        indication, mechanism_of_action, mechanism_class, modality,
                        regulatory_pathway, vote_yes, vote_no, vote_abstain,
                        vote_outcome, key_concerns, key_positives
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    ON CONFLICT (document_id, product_name) DO UPDATE SET
                        generic_name = EXCLUDED.generic_name,
                        sponsor = EXCLUDED.sponsor,
                        indication = EXCLUDED.indication,
                        mechanism_of_action = EXCLUDED.mechanism_of_action,
                        mechanism_class = EXCLUDED.mechanism_class,
                        modality = EXCLUDED.modality,
                        regulatory_pathway = EXCLUDED.regulatory_pathway,
                        vote_yes = EXCLUDED.vote_yes,
                        vote_no = EXCLUDED.vote_no,
                        vote_abstain = EXCLUDED.vote_abstain,
                        vote_outcome = EXCLUDED.vote_outcome,
                        key_concerns = EXCLUDED.key_concerns,
                        key_positives = EXCLUDED.key_positives,
                        extracted_at = NOW()
                """, (
                    record["document_id"], record["committee_code"], record["meeting_date"],
                    record["product_name"], record["generic_name"], record["sponsor"],
                    record["sponsor_ticker"],
                    record["indication"], record["mechanism_of_action"],
                    record["mechanism_class"], record["modality"],
                    record["regulatory_pathway"], record["vote_yes"], record["vote_no"],
                    record["vote_abstain"], record["vote_outcome"],
                    record["key_concerns"], record["key_positives"],
                ))
            except Exception as e:
                print(f"  ✗ DB insert error for {record['product_name']}: {e}")
                conn.rollback()

    if not dry_run:
        conn.commit()

    cur.close()
    conn.close()
    return extracted


def extract_all(committee: Optional[str] = None, dry_run: bool = False,
                limit: Optional[int] = None):
    """
    Extract product data from all AdCom documents (or filtered by committee).
    """
    conn = _get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get AdCom documents that haven't been extracted yet
    query = """
        SELECT d.id, d.ticker, d.title, d.date, d.doc_type, d.word_count
        FROM documents d
        WHERE d.ticker LIKE 'FDA_%%'
        AND NOT EXISTS (
            SELECT 1 FROM adcom_products ap WHERE ap.document_id = d.id
        )
    """
    params = []

    if committee:
        query += " AND d.ticker = %s"
        params.append(f"FDA_{committee}")

    # Prioritize transcripts (most info) then briefing docs
    query += " ORDER BY CASE WHEN d.doc_type = 'transcript' THEN 1 WHEN d.doc_type = 'briefing_document' THEN 2 ELSE 3 END, d.date DESC"

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query, params)
    docs = cur.fetchall()
    cur.close()
    conn.close()

    print(f"\n{'DRY RUN — ' if dry_run else ''}Extracting from {len(docs)} AdCom documents")
    if committee:
        print(f"  Committee filter: {committee}")
    print()

    total_products = 0
    for i, doc in enumerate(docs):
        print(f"  [{i+1}/{len(docs)}] {doc['title'][:80]}...")
        products = extract_from_document(doc['id'], dry_run=dry_run)
        total_products += len(products)

        for p in products:
            flag = "🟢" if p["vote_outcome"] == "favorable" else "🔴" if p["vote_outcome"] == "unfavorable" else "⚪"
            mclass_tag = f" [{p['mechanism_class']}]" if p['mechanism_class'] else ""
            print(f"    {flag} {p['product_name']} — {p['sponsor'] or '?'}{mclass_tag}")
            if p['key_concerns']:
                for c in p['key_concerns'][:2]:
                    print(f"       ⚠ {c[:80]}")

        # Rate limit — Claude API
        if i < len(docs) - 1:
            time.sleep(1)

    print(f"\n✓ Extracted {total_products} products from {len(docs)} documents")


# ── Query functions (used by the routing agent) ──

def get_adcom_for_mechanism_class(mechanism_class: str, limit: int = 20) -> list[dict]:
    """
    Get all AdCom products sharing a mechanism class.
    This is the fast-follower query: "what did the FDA say about ALL anti-PD1 drugs?"
    """
    conn = _get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT ap.*, d.title as doc_title
        FROM adcom_products ap
        JOIN documents d ON d.id = ap.document_id
        WHERE ap.mechanism_class = %s
        ORDER BY ap.meeting_date DESC
        LIMIT %s
    """, (mechanism_class, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Convert psycopg2 types
    results = []
    for r in rows:
        row = dict(r)
        row['key_concerns'] = list(row.get('key_concerns') or [])
        row['key_positives'] = list(row.get('key_positives') or [])
        results.append(row)
    return results


def get_adcom_for_product(product_name: str) -> list[dict]:
    """Get all AdCom entries for a specific product (any name match)."""
    conn = _get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT ap.*, d.title as doc_title
        FROM adcom_products ap
        JOIN documents d ON d.id = ap.document_id
        WHERE LOWER(ap.product_name) LIKE LOWER(%s)
           OR LOWER(ap.generic_name) LIKE LOWER(%s)
        ORDER BY ap.meeting_date DESC
    """, (f"%{product_name}%", f"%{product_name}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_adcom_for_committee(committee_code: str, limit: int = 50) -> list[dict]:
    """Get recent AdCom products for a committee."""
    conn = _get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT ap.*, d.title as doc_title
        FROM adcom_products ap
        JOIN documents d ON d.id = ap.document_id
        WHERE ap.committee_code = %s
        ORDER BY ap.meeting_date DESC
        LIMIT %s
    """, (committee_code, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_concerns_by_mechanism_class(mechanism_class: str) -> dict:
    """
    Aggregate all concerns raised for a mechanism class.
    Returns a dict with concern frequency — the "regulatory risk profile" for a drug class.
    """
    products = get_adcom_for_mechanism_class(mechanism_class, limit=100)
    all_concerns = []
    for p in products:
        all_concerns.extend(p.get("key_concerns", []))

    # Simple frequency count
    concern_counts = {}
    for c in all_concerns:
        # Normalize
        key = c.lower().strip()
        concern_counts[key] = concern_counts.get(key, 0) + 1

    return {
        "mechanism_class": mechanism_class,
        "total_products_reviewed": len(products),
        "total_concerns": len(all_concerns),
        "concerns": sorted(concern_counts.items(), key=lambda x: -x[1]),
        "products": [
            {
                "product_name": p["product_name"],
                "sponsor": p["sponsor"],
                "meeting_date": p["meeting_date"],
                "vote_outcome": p["vote_outcome"],
            }
            for p in products
        ],
    }


def format_adcom_for_claude(products: list[dict], context_label: str = "AdCom Intelligence") -> str:
    """Format extracted AdCom data for injection into Claude synthesis prompt."""
    if not products:
        return ""

    lines = [f"\n── {context_label} ──\n"]
    for p in products:
        vote_str = ""
        if p.get("vote_yes") is not None:
            vote_str = f" | Vote: {p['vote_yes']}Y-{p['vote_no']}N"
            if p.get("vote_abstain"):
                vote_str += f"-{p['vote_abstain']}A"
            vote_str += f" ({p['vote_outcome']})"

        lines.append(f"• {p['product_name']} ({p.get('generic_name', '?')}) — {p.get('sponsor', '?')}")
        lines.append(f"  Committee: {p.get('committee_code', '?')} | Date: {p.get('meeting_date', '?')}{vote_str}")
        lines.append(f"  Indication: {p.get('indication', '?')}")
        lines.append(f"  MoA: {p.get('mechanism_of_action', '?')} [{p.get('mechanism_class', 'unclassified')}]")

        if p.get("key_concerns"):
            lines.append("  Concerns:")
            for c in p["key_concerns"]:
                lines.append(f"    ⚠ {c}")

        if p.get("key_positives"):
            lines.append("  Positives:")
            for pos in p["key_positives"]:
                lines.append(f"    ✓ {pos}")

        lines.append("")

    return "\n".join(lines)


# ── CLI ──

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract structured data from AdCom documents")
    parser.add_argument("--setup", action="store_true", help="Create adcom_products table")
    parser.add_argument("--all", action="store_true", help="Extract from all unprocessed AdCom docs")
    parser.add_argument("--committee", type=str, help="Filter by committee code (e.g., ODAC)")
    parser.add_argument("--doc-id", type=int, help="Extract from a single document ID")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--limit", type=int, help="Max documents to process")
    parser.add_argument("--query-class", type=str, help="Query products by mechanism class")
    parser.add_argument("--query-product", type=str, help="Query by product name")
    args = parser.parse_args()

    if args.setup:
        setup_tables()
    elif args.query_class:
        results = get_adcom_for_mechanism_class(args.query_class)
        print(format_adcom_for_claude(results, f"Mechanism class: {args.query_class}"))
    elif args.query_product:
        results = get_adcom_for_product(args.query_product)
        print(format_adcom_for_claude(results, f"Product: {args.query_product}"))
    elif args.doc_id:
        products = extract_from_document(args.doc_id, dry_run=args.dry_run)
        print(f"\nExtracted {len(products)} products")
        for p in products:
            print(f"  {p['product_name']} — {p.get('sponsor')} [{p.get('mechanism_class', '?')}]")
    elif args.all or args.committee:
        setup_tables()
        extract_all(committee=args.committee, dry_run=args.dry_run, limit=args.limit)
    else:
        parser.print_help()
