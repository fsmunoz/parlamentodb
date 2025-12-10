"""
Votacoes (votes) endpoints.
"""

from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.votacao import Votacao, VotacaoListItem
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_partido, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/votacoes", tags=["votacoes"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[VotacaoListItem])
def list_votacoes(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17)"),
    ini_id: str | None = Query(None, description="Filter by initiative ID"),
    resultado: str | None = Query(None, description="Filter by result (Aprovado, Rejeitado, etc.)"),
    data_desde: date | None = Query(None, description="Minimum vote date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum vote date (YYYY-MM-DD)"),
    partido_favor: str | None = Query(None, description="Filter by party voting in favor (e.g., PS, PSD). Case-insensitive."),
    partido_contra: str | None = Query(None, description="Filter by party voting against. Case-insensitive."),
    partido_abstencao: str | None = Query(None, description="Filter by party abstaining. Case-insensitive."),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List votes with optional filters.

    Returns a paginated list of parliamentary votes. Filter by:
    - Legislature (L15, L16, L17)
    - Initiative ID
    - Vote result
    - Date range
    - Party positions (in favor, against, abstaining)

    **Case-Insensitive Parameters:**
    - Legislature codes are case-insensitive (e.g., 'l17', 'L17' both accepted, normalized to 'L17')
    - Party codes are case-insensitive (e.g., 'ps', 'PS' both accepted, normalized to 'PS')

    Party filters match exact party codes (PS, PSD, etc.).
    Note: Individual Ninsc members are stored with full names (e.g., "António Maló (Ninsc)").

    Default limit is 50 records, maximum is 500.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        partido_favor = validate_partido(partido_favor)
        partido_contra = validate_partido(partido_contra)
        partido_abstencao = validate_partido(partido_abstencao)
        limit, offset = validate_pagination(limit, offset)

        # Build WHERE clause using QueryBuilder
        qb = QueryBuilder()
        qb.add_equals("legislatura", legislatura)
        qb.add_equals("ini_id", ini_id)
        qb.add_equals("resultado", resultado)
        qb.add_gte("data", data_desde, "data_desde")
        qb.add_lte("data", data_ate, "data_ate")
        qb.add_list_contains("detalhe_parsed.a_favor", partido_favor, "partido_favor")
        qb.add_list_contains("detalhe_parsed.contra", partido_contra, "partido_contra")
        qb.add_list_contains("detalhe_parsed.abstencao", partido_abstencao, "partido_abstencao")

        where_sql = qb.build_where()
        params = qb.get_params()

        # Get total count
        count_query = f"SELECT COUNT(*) FROM votacoes {where_sql}"
        total = db.execute(count_query, params).fetchone()[0]

        # Get data
        data_query = f"""
            SELECT
                vot_id,
                ini_nr,
                legislatura,
                ini_titulo,
                fase,
                data,
                resultado
            FROM votacoes
            {where_sql}
            ORDER BY data DESC NULLS LAST, vot_id DESC
            LIMIT $limit OFFSET $offset
        """
        params.update({"limit": limit, "offset": offset})

        rows = db.execute(data_query, params).fetchall()

        # Convert to models
        data = [
            VotacaoListItem(
                vot_id=row[0],
                ini_nr=row[1],
                legislatura=row[2],
                ini_titulo=row[3],
                fase=row[4],
                data=row[5],
                resultado=row[6]
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
        logger.error("votes_list_error",
                     legislatura=legislatura,
                     ini_id=ini_id,
                     resultado=resultado,
                     partido_favor=partido_favor,
                     partido_contra=partido_contra,
                     partido_abstencao=partido_abstencao,
                     error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while listing votes"
        )


@router.get("/{vot_id}", response_model=Votacao)
def get_votacao(
    vot_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single vote by ID.
    """
    try:
        query = "SELECT * FROM votacoes WHERE vot_id = $vot_id"
        # Execute once and save cursor
        cursor = db.execute(query, {"vot_id": vot_id})
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Vote {vot_id} not found"
            )

        # Convert to dict
        row_dict = dict(zip(column_names, result))

        return Votacao(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("vote_fetch_error", vot_id=vot_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching vote"
        )
