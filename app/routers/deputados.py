"""
Deputados (deputies/MPs) endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.deputado import Deputado, DeputadoListItem
from app.models.iniciativa import IniciativaListItem
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_partido, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/deputados", tags=["deputados"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[DeputadoListItem])
def list_deputados(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17)"),
    partido: str | None = Query(None, description="Filter by party (PS, PSD, etc.)"),
    circulo: str | None = Query(None, description="Filter by electoral circle name"),
    situacao: str | None = Query(None, description="Filter by status (Efetivo, Suplente, Renunciou)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List deputies (MPs) with optional filters.

    Returns a paginated list of deputies. Filter by:
    - Legislature (L15, L16, L17)
    - Party affiliation
    - Electoral circle
    - Status (Efetivo=active, Suplente=substitute, Renunciou=resigned)

    Default limit is 50 records, maximum is 500.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        partido = validate_partido(partido)
        limit, offset = validate_pagination(limit, offset)

        # Build WHERE clause using QueryBuilder
        qb = QueryBuilder()
        qb.add_equals("legislatura", legislatura)
        qb.add_equals("partido_atual", partido, "partido")
        qb.add_equals("circulo_atual", circulo, "circulo")
        qb.add_equals("situacao_atual", situacao, "situacao")

        where_sql = qb.build_where()
        params = qb.get_params()

        # Get total count
        count_query = f"SELECT COUNT(*) FROM deputados {where_sql}"
        total = db.execute(count_query, params).fetchone()[0]

        # Get data
        data_query = f"""
            SELECT
                legislatura,
                dep_cad_id,
                nome_parlamentar,
                circulo_atual,
                partido_atual,
                situacao_atual
            FROM deputados
            {where_sql}
            ORDER BY nome_parlamentar
            LIMIT $limit OFFSET $offset
        """
        params.update({"limit": limit, "offset": offset})

        rows = db.execute(data_query, params).fetchall()

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

    except Exception as e:
        logger.error("deputies_list_error", filters=params, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error listing deputies"
        )


@router.get("/{dep_cad_id}", response_model=Deputado)
def get_deputado(
    dep_cad_id: float,
    legislatura: str = Query(..., description="Legislature (required)"),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single deputy by cadastro ID.

    The dep_cad_id is a persistent identifier that links deputies across legislatures.
    """
    try:
        # Validate legislature
        legislatura = validate_legislatura(legislatura)

        query = """
            SELECT * FROM deputados
            WHERE dep_cad_id = $dep_cad_id
              AND legislatura = $legislatura
        """
        # Execute once and save cursor
        cursor = db.execute(query, {"dep_cad_id": dep_cad_id, "legislatura": legislatura})
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Deputy {dep_cad_id} not found in legislatura {legislatura}"
            )

        # Convert to dict
        row_dict = dict(zip(column_names, result))

        return Deputado(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("deputy_fetch_error", dep_cad_id=dep_cad_id, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving deputy data"
        )


@router.get("/{dep_cad_id}/iniciativas", response_model=APIResponse[IniciativaListItem])
def get_deputado_iniciativas(
    dep_cad_id: str,
    legislatura: str = Query(..., description="Legislature (required)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List all initiatives authored by a specific deputy.

    Returns initiatives where the deputy is listed as an individual author
    (ini_autor_deputados field). Initiatives authored only by parliamentary
    groups or government are excluded.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        limit, offset = validate_pagination(limit, offset)

        # Verify deputy exists
        check_query = """
            SELECT nome_parlamentar FROM deputados
            WHERE dep_cad_id = $dep_cad_id AND legislatura = $legislatura
        """
        check_result = db.execute(check_query, {
            "dep_cad_id": dep_cad_id,
            "legislatura": legislatura
        }).fetchone()

        if not check_result:
            raise HTTPException(
                status_code=404,
                detail=f"Deputy {dep_cad_id} not found in legislatura {legislatura}"
            )

        # Build query using QueryBuilder
        qb = QueryBuilder()
        qb.add_equals("legislatura", legislatura)
        qb.add_custom("""
            list_contains(
                list_transform(ini_autor_deputados, x -> x.idCadastro),
                $dep_cad_id
            )
        """, {"dep_cad_id": dep_cad_id})

        where_sql = qb.build_where()
        params = qb.get_params()

        # Count query
        count_query = f"SELECT COUNT(*) FROM iniciativas {where_sql}"
        total = db.execute(count_query, params).fetchone()[0]

        # Data query
        data_query = f"""
            SELECT
                ini_id,
                ini_nr,
                legislatura,
                ini_tipo,
                ini_desc_tipo,
                ini_titulo
            FROM iniciativas
            {where_sql}
            ORDER BY ini_nr DESC
            LIMIT $limit OFFSET $offset
        """
        params.update({"limit": limit, "offset": offset})

        rows = db.execute(data_query, params).fetchall()

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
        logger.error("deputado_iniciativas_error", dep_cad_id=dep_cad_id, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving deputy initiatives"
        )
