"""
Partidos (parliamentary groups/parties) endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.partido import Partido, PartidoListItem
from app.models.deputado import DeputadoListItem
from app.models.iniciativa import IniciativaListItem
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/partidos", tags=["partidos"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[PartidoListItem])
def list_partidos(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17)"),
    limit: int = Query(settings.MAX_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List parliamentary groups (parties) with optional filters.

    Returns a paginated list of political parties/groups in parliament.
    Filter by legislature to see parties for specific periods.

    Default limit is 500 records, maximum is 500.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        limit, offset = validate_pagination(limit, offset)

        # Build WHERE clause using QueryBuilder
        qb = QueryBuilder()
        qb.add_equals("legislatura", legislatura)

        where_sql = qb.build_where()
        params = qb.get_params()

        # Get total count
        count_query = f"SELECT COUNT(*) FROM partidos {where_sql}"
        total = db.execute(count_query, params).fetchone()[0]

        # Get data
        data_query = f"""
            SELECT
                legislatura,
                gp_sigla,
                gp_nome
            FROM partidos
            {where_sql}
            ORDER BY gp_sigla
            LIMIT $limit OFFSET $offset
        """
        params.update({"limit": limit, "offset": offset})

        rows = db.execute(data_query, params).fetchall()

        # Convert to models
        data = [
            PartidoListItem(
                legislatura=row[0],
                gp_sigla=row[1],
                gp_nome=row[2]
            )
            for row in rows
        ]

        return APIResponse(
            data=data,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("partidos_list_error", legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while listing parties"
        )


@router.get("/{gp_sigla}", response_model=Partido)
def get_partido(
    gp_sigla: str,
    legislatura: str = Query(..., description="Legislature (required)"),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single party by abbreviation (e.g., PS, PSD, CH).
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)

        query = """
            SELECT * FROM partidos
            WHERE gp_sigla = $gp_sigla
              AND legislatura = $legislatura
        """
        # Execute once and save cursor
        cursor = db.execute(query, {"gp_sigla": gp_sigla.upper(), "legislatura": legislatura})
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Party {gp_sigla} not found in legislatura {legislatura}"
            )

        # Convert to dict
        row_dict = dict(zip(column_names, result))

        return Partido(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("partido_fetch_error", gp_sigla=gp_sigla, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching party"
        )


@router.get("/{gp_sigla}/deputados", response_model=APIResponse[DeputadoListItem])
def get_partido_deputados(
    gp_sigla: str,
    legislatura: str = Query(..., description="Legislature (required)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get all deputies affiliated with this party.

    Returns all deputies with this party as their current affiliation,
    regardless of status (includes Efetivo, Suplente, Renunciou).
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        limit, offset = validate_pagination(limit, offset)

        # Verify party exists
        party_query = """
            SELECT gp_nome FROM partidos
            WHERE gp_sigla = $gp_sigla AND legislatura = $legislatura
        """
        party_result = db.execute(party_query, {"gp_sigla": gp_sigla.upper(), "legislatura": legislatura}).fetchone()

        if not party_result:
            raise HTTPException(
                status_code=404,
                detail=f"Party {gp_sigla} not found in legislatura {legislatura}"
            )

        # Get deputies
        count_query = """
            SELECT COUNT(*) FROM deputados
            WHERE partido_atual = $gp_sigla
              AND legislatura = $legislatura
        """
        total = db.execute(count_query, {"gp_sigla": gp_sigla.upper(), "legislatura": legislatura}).fetchone()[0]

        data_query = """
            SELECT
                legislatura,
                dep_cad_id,
                nome_parlamentar,
                circulo_atual,
                partido_atual,
                situacao_atual
            FROM deputados
            WHERE partido_atual = $gp_sigla
              AND legislatura = $legislatura
            ORDER BY nome_parlamentar
            LIMIT $limit OFFSET $offset
        """

        rows = db.execute(data_query, {
            "gp_sigla": gp_sigla.upper(),
            "legislatura": legislatura,
            "limit": limit,
            "offset": offset
        }).fetchall()

        # Convert to models
        data = [
            DeputadoListItem(
                legislatura=row[0],
                dep_cad_id=row[1],
                nome_parlamentar=row[2],
                circulo_atual=row[3],
                partido_atual=row[4],
                situacao_atual=row[5]
            )
            for row in rows
        ]

        return APIResponse(
            data=data,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("partido_deputados_error", gp_sigla=gp_sigla, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching party deputies"
        )


@router.get("/{gp_sigla}/iniciativas", response_model=APIResponse[IniciativaListItem])
def get_partido_iniciativas(
    gp_sigla: str,
    legislatura: str = Query(..., description="Legislature (required)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get all initiatives authored by this party.

    Returns initiatives where this party is listed as the author
    (ini_autor_partido matches the party abbreviation).
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        limit, offset = validate_pagination(limit, offset)

        # Verify party exists
        party_query = """
            SELECT gp_nome FROM partidos
            WHERE gp_sigla = $gp_sigla AND legislatura = $legislatura
        """
        party_result = db.execute(party_query, {"gp_sigla": gp_sigla.upper(), "legislatura": legislatura}).fetchone()

        if not party_result:
            raise HTTPException(
                status_code=404,
                detail=f"Party {gp_sigla} not found in legislatura {legislatura}"
            )

        # Get initiatives
        # Check if party is in ini_autor_grupos_parlamentares array
        count_query = """
            SELECT COUNT(*) FROM iniciativas
            WHERE list_contains(
                list_transform(ini_autor_grupos_parlamentares, x -> x.GP),
                $gp_sigla
            )
              AND legislatura = $legislatura
        """
        total = db.execute(count_query, {"gp_sigla": gp_sigla.upper(), "legislatura": legislatura}).fetchone()[0]

        data_query = """
            SELECT
                ini_id,
                ini_nr,
                legislatura,
                ini_tipo,
                ini_desc_tipo,
                ini_titulo
            FROM iniciativas
            WHERE list_contains(
                list_transform(ini_autor_grupos_parlamentares, x -> x.GP),
                $gp_sigla
            )
              AND legislatura = $legislatura
            ORDER BY ini_nr DESC
            LIMIT $limit OFFSET $offset
        """

        rows = db.execute(data_query, {
            "gp_sigla": gp_sigla.upper(),
            "legislatura": legislatura,
            "limit": limit,
            "offset": offset
        }).fetchall()

        # Convert to models
        data = [
            IniciativaListItem(
                ini_id=row[0],
                ini_nr=row[1],
                legislatura=row[2],
                ini_tipo=row[3],
                ini_desc_tipo=row[4],
                ini_titulo=row[5]
            )
            for row in rows
        ]

        return APIResponse(
            data=data,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("partido_iniciativas_error", gp_sigla=gp_sigla, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching party initiatives"
        )
