"""
Legislaturas (legislature metadata) endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Fundamental information about the legislature.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.legislatura import Legislatura, LegislaturaListItem
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_pagination

router = APIRouter(prefix="/api/v1/legislaturas", tags=["legislaturas"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[LegislaturaListItem])
def list_legislaturas(
    limit: int = Query(settings.MAX_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List all available legislatures.

    Returns basic information about each legislature including dates and counts.
    """
    # Validate inputs
    limit, offset = validate_pagination(limit, offset)

    # Check if info_base table has data
    try:
        has_info_base = db.execute("SELECT COUNT(*) FROM info_base").fetchone()[0] > 0
    except:
        has_info_base = False

    # Build query based on data availability
    if has_info_base:
        base_query = """
            SELECT
                legislatura,
                DetalheLegislatura.sigla as sigla,
                DetalheLegislatura.dtini as dtini,
                DetalheLegislatura.dtfim as dtfim,
                length(Deputados) as num_deputados,
                length(GruposParlamentares) as num_grupos
            FROM info_base
        """
    else:
        base_query = """
            SELECT DISTINCT
                legislatura,
                legislatura as sigla,
                min(data_inicio_leg) as dtini,
                CAST(NULL AS DATE) as dtfim,
                CAST(NULL AS INTEGER) as num_deputados,
                CAST(NULL AS INTEGER) as num_grupos
            FROM iniciativas
            GROUP BY legislatura
        """

    # Get total count
    count_query = f"SELECT COUNT(*) FROM ({base_query})"
    total = db.execute(count_query).fetchone()[0]

    # Get paginated data
    data_query = f"{base_query} ORDER BY legislatura LIMIT $limit OFFSET $offset"
    rows = db.execute(data_query, {"limit": limit, "offset": offset}).fetchall()

    # Convert to models
    data = [
        LegislaturaListItem(
            legislatura=row[0],
            sigla=row[1],
            dtini=row[2],
            dtfim=row[3],
            num_deputados=row[4],
            num_grupos=row[5]
        )
        for row in rows
    ]

    return APIResponse(
        data=data,
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
        meta=APIMeta(version=settings.API_VERSION)
    )


@router.get("/{legislatura}", response_model=Legislatura)
def get_legislatura(
    legislatura: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get detailed information about a specific legislature.

    Includes:
    - Legislature details (dates, ID)
    - List of all deputies
    - Parliamentary groups
    - Electoral districts (círculos)
    - Legislative sessions

    Note: Detailed metadata is only available for legislatures with InformacaoBase data in the config file.
    """
    try:
        query = "SELECT * FROM info_base WHERE legislatura = $legislatura"
        # Execute once and save cursor
        cursor = db.execute(query, {"legislatura": legislatura})
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            # Check if legislature exists in iniciativas
            check_query = "SELECT COUNT(*) FROM iniciativas WHERE legislatura = $legislatura"
            count = db.execute(check_query, {"legislatura": legislatura}).fetchone()[0]

            if count == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"Legislatura {legislatura} not found"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Detailed metadata not available for {legislatura}. Try L17 or use /api/v1/legislaturas for basic info."
                )

        # Convert to dict
        row_dict = dict(zip(column_names, result))

        return Legislatura(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("legislature_fetch_error", legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving legislature data"
        )
