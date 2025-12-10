"""
Circulos (electoral circles) endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.circulo import Circulo, CirculoListItem
from app.models.deputado import DeputadoListItem
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/circulos", tags=["circulos"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[CirculoListItem])
def list_circulos(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17)"),
    limit: int = Query(settings.MAX_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List electoral circles with optional filters.

    Returns a paginated list of Portugal's 22 electoral circles.
    Filter by legislature to see circles for specific periods.

    Default limit is 500 records (returns all circles), maximum is 500.
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
        count_query = f"SELECT COUNT(*) FROM circulos {where_sql}"
        total = db.execute(count_query, params).fetchone()[0]

        # Get data
        data_query = f"""
            SELECT
                legislatura,
                cp_id,
                cp_des
            FROM circulos
            {where_sql}
            ORDER BY cp_des
            LIMIT $limit OFFSET $offset
        """
        params.update({"limit": limit, "offset": offset})

        rows = db.execute(data_query, params).fetchall()

        # Convert to models
        data = [
            CirculoListItem(
                legislatura=row[0],
                cp_id=row[1],
                cp_des=row[2]
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
        logger.error("circulos_list_error", legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while listing electoral circles"
        )


@router.get("/{cp_id}", response_model=Circulo)
def get_circulo(
    cp_id: float,
    legislatura: str = Query(..., description="Legislature (required)"),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single electoral circle by ID.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)

        query = """
            SELECT * FROM circulos
            WHERE cp_id = $cp_id
              AND legislatura = $legislatura
        """
        # Execute once and save cursor
        cursor = db.execute(query, {"cp_id": cp_id, "legislatura": legislatura})
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Circle {cp_id} not found in legislatura {legislatura}"
            )

        # Convert to dict
        row_dict = dict(zip(column_names, result))

        return Circulo(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("circulo_fetch_error", cp_id=cp_id, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching electoral circle"
        )


@router.get("/{cp_id}/deputados", response_model=APIResponse[DeputadoListItem])
def get_circulo_deputados(
    cp_id: float,
    legislatura: str = Query(..., description="Legislature (required)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get all currently active deputies (Efetivo) elected in this circle.

    Only returns deputies with situacao_atual='Efetivo' (active deputies),
    excluding substitutes and resigned members.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        limit, offset = validate_pagination(limit, offset)

        # Verify circle exists
        circle_query = """
            SELECT cp_des FROM circulos
            WHERE cp_id = $cp_id AND legislatura = $legislatura
        """
        circle_result = db.execute(circle_query, {"cp_id": cp_id, "legislatura": legislatura}).fetchone()

        if not circle_result:
            raise HTTPException(
                status_code=404,
                detail=f"Circle {cp_id} not found in legislatura {legislatura}"
            )

        circle_name = circle_result[0]

        # Get deputies (only active ones)
        count_query = """
            SELECT COUNT(*) FROM deputados
            WHERE circulo_id = $cp_id
              AND legislatura = $legislatura
              AND situacao_atual = 'Efetivo'
        """
        total = db.execute(count_query, {"cp_id": cp_id, "legislatura": legislatura}).fetchone()[0]

        data_query = """
            SELECT
                legislatura,
                dep_cad_id,
                nome_parlamentar,
                circulo_atual,
                partido_atual,
                situacao_atual
            FROM deputados
            WHERE circulo_id = $cp_id
              AND legislatura = $legislatura
              AND situacao_atual = 'Efetivo'
            ORDER BY nome_parlamentar
            LIMIT $limit OFFSET $offset
        """

        rows = db.execute(data_query, {
            "cp_id": cp_id,
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
        logger.error("circulo_deputados_error", cp_id=cp_id, legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching deputies from electoral circle"
        )
