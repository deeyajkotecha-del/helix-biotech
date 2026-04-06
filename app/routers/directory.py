"""
Private Company Directory — CRUD + search for private biotech startups
======================================================================
"""

import os
import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/directory", tags=["directory"])

# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

_db_conn = None

def _get_db():
    global _db_conn
    try:
        if _db_conn and not _db_conn.closed:
            _db_conn.cursor().execute("SELECT 1")
            return _db_conn
    except Exception:
        _db_conn = None

    import psycopg2
    db_url = os.environ.get("NEON_DATABASE_URL", "")
    if not db_url:
        raise ValueError("NEON_DATABASE_URL not set")
    _db_conn = psycopg2.connect(db_url)
    _db_conn.autocommit = True
    return _db_conn


def _slugify(name: str) -> str:
    """Create a URL-safe slug from company name."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PrivateCompanyCreate(BaseModel):
    name: str
    hq_location: str = ""
    founded_year: Optional[int] = None
    employee_count: str = ""
    therapeutic_areas: list[str] = []
    modality: str = ""
    lead_programs: str = ""
    stage: str = ""  # preclinical, phase1, phase2, phase3
    description: str = ""
    website: str = ""
    source_url: str = ""
    source_type: str = ""  # biopharma_dive, clinicaltrials, crunchbase, manual

class PrivateCompanyUpdate(BaseModel):
    name: Optional[str] = None
    hq_location: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[str] = None
    therapeutic_areas: Optional[list[str]] = None
    modality: Optional[str] = None
    lead_programs: Optional[str] = None
    stage: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/companies")
async def list_private_companies(
    q: str = "",
    stage: str = "",
    modality: str = "",
    therapeutic_area: str = "",
    limit: int = 200,
    offset: int = 0,
):
    """List/search private companies."""
    try:
        conn = _get_db()
        cur = conn.cursor()

        conditions = []
        params = []

        if q.strip():
            conditions.append("(name ILIKE %s OR description ILIKE %s OR lead_programs ILIKE %s)")
            like = f"%{q.strip()}%"
            params.extend([like, like, like])

        if stage.strip():
            conditions.append("stage = %s")
            params.append(stage.strip())

        if modality.strip():
            conditions.append("modality ILIKE %s")
            params.append(f"%{modality.strip()}%")

        if therapeutic_area.strip():
            conditions.append("%s = ANY(therapeutic_areas)")
            params.append(therapeutic_area.strip())

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        # Get total count
        cur.execute(f"SELECT COUNT(*) FROM private_companies {where}", params)
        total = cur.fetchone()[0]

        # Get results
        cur.execute(f"""
            SELECT id, name, slug, hq_location, founded_year, employee_count,
                   therapeutic_areas, modality, lead_programs, stage, description,
                   website, source_url, source_type, last_updated
            FROM private_companies {where}
            ORDER BY name ASC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        companies = []
        for row in cur.fetchall():
            companies.append({
                "id": row[0],
                "name": row[1],
                "slug": row[2],
                "hq_location": row[3],
                "founded_year": row[4],
                "employee_count": row[5],
                "therapeutic_areas": row[6] or [],
                "modality": row[7],
                "lead_programs": row[8],
                "stage": row[9],
                "description": row[10],
                "website": row[11],
                "source_url": row[12],
                "source_type": row[13],
                "last_updated": row[14].isoformat() if row[14] else None,
            })
        cur.close()

        # Get filter options
        cur2 = conn.cursor()
        cur2.execute("SELECT DISTINCT stage FROM private_companies WHERE stage != '' ORDER BY stage")
        stages = [r[0] for r in cur2.fetchall()]
        cur2.execute("SELECT DISTINCT modality FROM private_companies WHERE modality != '' ORDER BY modality")
        modalities = [r[0] for r in cur2.fetchall()]
        cur2.execute("SELECT DISTINCT unnest(therapeutic_areas) AS ta FROM private_companies ORDER BY ta")
        areas = [r[0] for r in cur2.fetchall()]
        cur2.close()

        return JSONResponse({
            "companies": companies,
            "total": total,
            "filters": {
                "stages": stages,
                "modalities": modalities,
                "therapeutic_areas": areas,
            },
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/companies/{company_id}")
async def get_private_company(company_id: int):
    """Get a single private company by ID."""
    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, slug, hq_location, founded_year, employee_count,
                   therapeutic_areas, modality, lead_programs, stage, description,
                   website, source_url, source_type, last_updated, created_at
            FROM private_companies WHERE id = %s
        """, (company_id,))
        row = cur.fetchone()
        cur.close()

        if not row:
            return JSONResponse({"error": "Company not found"}, status_code=404)

        return JSONResponse({
            "id": row[0], "name": row[1], "slug": row[2],
            "hq_location": row[3], "founded_year": row[4],
            "employee_count": row[5], "therapeutic_areas": row[6] or [],
            "modality": row[7], "lead_programs": row[8],
            "stage": row[9], "description": row[10],
            "website": row[11], "source_url": row[12],
            "source_type": row[13],
            "last_updated": row[14].isoformat() if row[14] else None,
            "created_at": row[15].isoformat() if row[15] else None,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/companies")
async def create_private_company(company: PrivateCompanyCreate):
    """Add a new private company."""
    try:
        conn = _get_db()
        cur = conn.cursor()
        slug = _slugify(company.name)

        cur.execute("""
            INSERT INTO private_companies
                (name, slug, hq_location, founded_year, employee_count,
                 therapeutic_areas, modality, lead_programs, stage,
                 description, website, source_url, source_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                hq_location = COALESCE(NULLIF(EXCLUDED.hq_location, ''), private_companies.hq_location),
                founded_year = COALESCE(EXCLUDED.founded_year, private_companies.founded_year),
                employee_count = COALESCE(NULLIF(EXCLUDED.employee_count, ''), private_companies.employee_count),
                therapeutic_areas = CASE
                    WHEN array_length(EXCLUDED.therapeutic_areas, 1) > 0 THEN EXCLUDED.therapeutic_areas
                    ELSE private_companies.therapeutic_areas
                END,
                modality = COALESCE(NULLIF(EXCLUDED.modality, ''), private_companies.modality),
                lead_programs = COALESCE(NULLIF(EXCLUDED.lead_programs, ''), private_companies.lead_programs),
                stage = COALESCE(NULLIF(EXCLUDED.stage, ''), private_companies.stage),
                description = COALESCE(NULLIF(EXCLUDED.description, ''), private_companies.description),
                website = COALESCE(NULLIF(EXCLUDED.website, ''), private_companies.website),
                source_url = COALESCE(NULLIF(EXCLUDED.source_url, ''), private_companies.source_url),
                last_updated = NOW()
            RETURNING id
        """, (
            company.name, slug, company.hq_location, company.founded_year,
            company.employee_count, company.therapeutic_areas, company.modality,
            company.lead_programs, company.stage, company.description,
            company.website, company.source_url, company.source_type,
        ))
        row = cur.fetchone()
        cur.close()

        return JSONResponse({"id": row[0], "slug": slug, "status": "created"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/companies/{company_id}")
async def update_private_company(company_id: int, update: PrivateCompanyUpdate):
    """Update a private company."""
    try:
        conn = _get_db()
        cur = conn.cursor()

        sets = []
        params = []
        for field, value in update.dict(exclude_none=True).items():
            if field == "name":
                sets.append("name = %s")
                params.append(value)
                sets.append("slug = %s")
                params.append(_slugify(value))
            elif field == "therapeutic_areas":
                sets.append("therapeutic_areas = %s")
                params.append(value)
            else:
                sets.append(f"{field} = %s")
                params.append(value)

        if not sets:
            return JSONResponse({"error": "No fields to update"}, status_code=400)

        sets.append("last_updated = NOW()")
        params.append(company_id)

        cur.execute(
            f"UPDATE private_companies SET {', '.join(sets)} WHERE id = %s RETURNING id",
            params
        )
        row = cur.fetchone()
        cur.close()

        if not row:
            return JSONResponse({"error": "Company not found"}, status_code=404)

        return JSONResponse({"id": row[0], "status": "updated"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/companies/{company_id}")
async def delete_private_company(company_id: int):
    """Delete a private company."""
    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM private_companies WHERE id = %s RETURNING id", (company_id,))
        row = cur.fetchone()
        cur.close()

        if not row:
            return JSONResponse({"error": "Company not found"}, status_code=404)

        return JSONResponse({"status": "deleted"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/stats")
async def directory_stats():
    """Get directory summary stats."""
    try:
        conn = _get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM private_companies")
        total = cur.fetchone()[0]
        cur.execute("""
            SELECT stage, COUNT(*) FROM private_companies
            WHERE stage != '' GROUP BY stage ORDER BY COUNT(*) DESC
        """)
        by_stage = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("""
            SELECT unnest(therapeutic_areas) AS ta, COUNT(*) FROM private_companies
            GROUP BY ta ORDER BY COUNT(*) DESC LIMIT 10
        """)
        by_area = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()

        return JSONResponse({
            "total": total,
            "by_stage": by_stage,
            "by_therapeutic_area": by_area,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
