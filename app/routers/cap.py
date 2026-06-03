"""
CAP (Comparative Agendas Project) classification endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Exposes the CAP topic-code classifications produced by the votoaberto-cap project.
Proposals are classified with poltextlab/xlm-roberta-large-pooled-cap-v3 (multilingual)
into 22 major policy areas (Macroeconomia, Saúde, Imigração, …).

Endpoints are optional: if data/silver/cap_l*.parquet files are absent (e.g., before
the classify.py pipeline has been run and the mapping CSV imported), the responses
will have zero results rather than raising an error.  Full CAP coverage requires
running the votoaberto-cap classify.py and committing the resulting
data/cap_source/cap_l17.csv, then re-running the ETL.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.cap import CapListItem, CapDetail
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_partido, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/cap", tags=["cap"])
logger = structlog.get_logger()

# ── helpers ─────────────────────────────────────────────────────────────────

# DuckDB expression that reads all author GP abbreviations from the nested
# ini_autor_grupos_parlamentares STRUCT array (same pattern as iniciativas.py).
_AUTOR_GP_EXPR = "list_transform(i.ini_autor_grupos_parlamentares, x -> x.GP)"

# SELECT columns shared by list and detail queries (c = cap view, i = iniciativas view)
_SELECT_COLS = """
    c.ini_id,
    c.legislatura,
    c.cap,
    c.cap_label,
    c.model_version,
    i.ini_nr,
    i.ini_tipo,
    i.ini_desc_tipo,
    i.ini_titulo
"""


def _cap_available(db: duckdb.DuckDBPyConnection) -> bool:
    """Return True if the cap view is registered on this connection."""
    try:
        db.execute("SELECT 1 FROM cap LIMIT 0")
        return True
    except Exception:
        return False


# ── list endpoint ────────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse[CapListItem])
def list_cap(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17)"),
    cap: int | None = Query(None, description="Filter by CAP major-topic code (e.g., 3=Saúde, 9=Imigração)"),
    autor_gp: str | None = Query(None, description="Filter by parliamentary group author (e.g., PS, PSD, CH)"),
    tipo: str | None = Query(None, description="Filter by initiative type code (e.g., J, R, PPL)"),
    q: str | None = Query(None, description="Search in initiative title (case-insensitive substring)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    List CAP-classified legislative initiatives with optional filters.

    Returns a paginated list of initiatives that have been classified with a
    CAP (Comparative Agendas Project) topic code.  Each result includes the
    numeric CAP code, its Portuguese label, and basic initiative metadata.

    **CAP major-topic codes** (22 categories, from comparativeagendas.net):
    1=Macroeconomia, 2=Direitos Civis, 3=Saúde, 4=Agricultura, 5=Trabalho,
    6=Educação, 7=Ambiente, 8=Energia, 9=Imigração, 10=Transportes,
    12=Direito e Crime, 13=Protecção Social, 14=Habitação, 15=Banca e Comércio,
    16=Defesa, 17=Tecnologia, 18=Comércio Externo, 19=Assuntos Internacionais,
    20=Administração Pública, 21=Terras Públicas, 23=Cultura, 999=Sem conteúdo político

    Not all initiatives are classified (only those for which a full-text document
    could be downloaded).  Coverage grows as the pipeline is run with --frac 1.0.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        autor_gp = validate_partido(autor_gp)
        limit, offset = validate_pagination(limit, offset)

        # Gracefully return empty result if the view is not yet built
        if not _cap_available(db):
            logger.info("cap_view_not_available")
            return APIResponse(
                data=[],
                pagination=PaginationMeta(limit=limit, offset=offset, total=0),
                meta=APIMeta(version=settings.API_VERSION),
            )

        # Build WHERE clause (all predicates are on the JOIN result)
        qb = QueryBuilder()
        qb.add_equals("c.legislatura", legislatura, "legislatura")
        qb.add_equals("c.cap", cap, "cap")
        qb.add_equals("i.ini_tipo", tipo, "tipo")

        if autor_gp:
            qb.add_custom(
                f"list_contains({_AUTOR_GP_EXPR}, $autor_gp)",
                {"autor_gp": autor_gp},
            )

        qb.add_text_search("i.ini_titulo", q, "ini_titulo_search")

        where_sql = qb.build_where()
        params = qb.get_params()

        base_from = "FROM cap c JOIN iniciativas i ON c.ini_id = i.ini_id"

        # Count
        total = db.execute(
            f"SELECT COUNT(*) {base_from} {where_sql}", params
        ).fetchone()[0]

        # Data
        params.update({"limit": limit, "offset": offset})
        rows = db.execute(
            f"""
            SELECT {_SELECT_COLS}
            {base_from}
            {where_sql}
            ORDER BY c.legislatura DESC, i.ini_data DESC NULLS LAST, c.ini_id DESC
            LIMIT $limit OFFSET $offset
            """,
            params,
        ).fetchall()

        data = [
            CapListItem(
                ini_id=row[0],
                legislatura=row[1],
                cap=row[2],
                cap_label=row[3],
                model_version=row[4],
                ini_nr=row[5],
                ini_tipo=row[6],
                ini_desc_tipo=row[7],
                ini_titulo=row[8],
            )
            for row in rows
        ]

        return APIResponse(
            data=data,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cap_list_error", legislatura=legislatura, cap=cap, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error while listing CAP classifications")


# ── detail endpoint ──────────────────────────────────────────────────────────

@router.get("/{ini_id}", response_model=CapDetail)
def get_cap(
    ini_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Get the CAP classification for a single initiative by its unique ID.

    Returns 404 if the initiative exists but has not yet been classified,
    or if the initiative ID is not found at all.
    """
    try:
        if not _cap_available(db):
            raise HTTPException(status_code=404, detail=f"CAP classification not available: no data loaded")

        cursor = db.execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM cap c JOIN iniciativas i ON c.ini_id = i.ini_id
            WHERE c.ini_id = $ini_id
            """,
            {"ini_id": ini_id},
        )
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"CAP classification for initiative '{ini_id}' not found",
            )

        row_dict = dict(zip(column_names, result))
        return CapDetail(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cap_detail_error", ini_id=ini_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error while fetching CAP classification")
