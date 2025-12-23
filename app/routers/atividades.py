"""
Atividades (parliamentary activities) endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Parliamentary activities like condemnation votes, motions, elections, etc.
These differ from Iniciativas in that they don't follow the legislative process.
"""

from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.atividade import (
    Atividade,
    AtividadeListItem,
    AtividadeVotacao,
    AtividadeVotacaoListItem
)
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_partido, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/atividades", tags=["atividades"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[AtividadeListItem])
def list_atividades(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17, LX)"),
    tipo: str | None = Query(None, description="Filter by activity type (VOT, MOC, PRG, OEX, SES, ITG)"),
    autor_gp: str | None = Query(None, description="Filter by party author (e.g., PS, PSD). Case-insensitive."),
    data_desde: date | None = Query(None, description="Minimum entry date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum entry date (YYYY-MM-DD)"),
    q: str | None = Query(None, description="Search in activity subject (ativ_assunto). Case-insensitive substring match."),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List parliamentary activities with optional filters.

    Returns a paginated list of activities (condemnation votes, motions, elections, etc.).
    Filter by:
    - Legislature (L15, L16, L17, LX)
    - Activity type (VOT, MOC, PRG, etc.)
    - Party author
    - Date range
    - Text search in subject

    **Case-Insensitive Parameters:**
    - Legislature codes are case-insensitive (e.g., 'l17', 'L17' both accepted, normalized to 'L17')
    - Party codes are case-insensitive (e.g., 'ps', 'PS' both accepted, normalized to 'PS')
    - Text search is also case-insensitive (uses ILIKE)

    Default limit is 50 records, maximum is 500.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        autor_gp = validate_partido(autor_gp)
        limit, offset = validate_pagination(limit, offset)

        # Build WHERE clause using QueryBuilder
        qb = QueryBuilder()
        qb.add_equals("legislatura", legislatura)
        qb.add_equals("ativ_tipo", tipo)
        qb.add_gte("data_entrada", data_desde, "data_desde")
        qb.add_lte("data_entrada", data_ate, "data_ate")
        qb.add_list_contains("ativ_autores_gp", autor_gp, "autor_gp")
        qb.add_text_search("ativ_assunto", q)

        where_clause = qb.build_where()
        params = qb.get_params()

        # Get total count
        count_query = f"SELECT count(*) FROM atividades {where_clause}"
        total = db.execute(count_query, params).fetchone()[0]

        # Get paginated results
        data_query = f"""
            SELECT
                ativ_id,
                legislatura,
                ativ_tipo,
                ativ_desc_tipo,
                ativ_numero,
                ativ_assunto,
                data_entrada,
                ativ_autores_gp,
                CASE
                    WHEN votacao_debate IS NOT NULL AND length(votacao_debate) > 0
                    THEN true
                    ELSE false
                END as has_votes
            FROM atividades
            {where_clause}
            ORDER BY data_entrada DESC NULLS LAST, ativ_id
            LIMIT $limit OFFSET $offset
        """
        params["limit"] = limit
        params["offset"] = offset

        results = db.execute(data_query, params).fetchall()

        # Convert to models
        items = [
            AtividadeListItem(
                ativ_id=row[0],
                legislatura=row[1],
                ativ_tipo=row[2],
                ativ_desc_tipo=row[3],
                ativ_numero=row[4],
                ativ_assunto=row[5],
                data_entrada=row[6],
                ativ_autores_gp=row[7],
                has_votes=row[8]
            )
            for row in results
        ]

        return APIResponse(
            data=items,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION)
        )

    except Exception as e:
        logger.error("list_atividades_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing atividades: {str(e)}")


@router.get("/{ativ_id}", response_model=Atividade)
def get_atividade(
    ativ_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single activity by ID.

    Returns complete activity details including nested structures
    (votes, publications, etc.).
    """
    try:
        query = """
            SELECT
                ativ_id,
                legislatura,
                ativ_tipo,
                ativ_desc_tipo,
                ativ_numero,
                ativ_assunto,
                data_entrada,
                data_agendamento_debate,
                data_anuncio,
                ativ_autores_gp,
                ativ_tipo_autor,
                sessao,
                observacoes,
                votacao_debate,
                publicacao,
                publicacao_debate
            FROM atividades
            WHERE ativ_id = $ativ_id
        """

        result = db.execute(query, {"ativ_id": ativ_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"Activity {ativ_id} not found")

        return Atividade(
            ativ_id=result[0],
            legislatura=result[1],
            ativ_tipo=result[2],
            ativ_desc_tipo=result[3],
            ativ_numero=result[4],
            ativ_assunto=result[5],
            data_entrada=result[6],
            data_agendamento_debate=result[7],
            data_anuncio=result[8],
            ativ_autores_gp=result[9],
            ativ_tipo_autor=result[10],
            sessao=result[11],
            observacoes=result[12],
            votacao_debate=result[13],
            publicacao=result[14],
            publicacao_debate=result[15]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_atividade_error", error=str(e), ativ_id=ativ_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving activity: {str(e)}")


@router.get("/votacoes/", response_model=APIResponse[AtividadeVotacaoListItem])
def list_atividades_votacoes(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17, LX)"),
    ativ_id: str | None = Query(None, description="Filter by specific activity ID"),
    tipo: str | None = Query(None, description="Filter by activity type (VOT, MOC, etc.)"),
    resultado: str | None = Query(None, description="Filter by result (Aprovado, Rejeitado)"),
    q: str | None = Query(None, description="Search in activity subject. Case-insensitive substring match."),
    data_desde: date | None = Query(None, description="Minimum vote date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum vote date (YYYY-MM-DD)"),
    partido_favor: str | None = Query(None, description="Filter by party voting in favor (e.g., PS, PSD). Case-insensitive."),
    partido_contra: str | None = Query(None, description="Filter by party voting against. Case-insensitive."),
    partido_abstencao: str | None = Query(None, description="Filter by party abstaining. Case-insensitive."),
    has_party_details: bool | None = Query(None, description="Filter by data quality: true = only votes with party voting details, false = only votes without details"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List votes from parliamentary activities with optional filters.

    Returns a paginated list of votes from atividades. Filter by:
    - Legislature (L15, L16, L17, LX)
    - Activity ID
    - Activity type
    - Vote result
    - Date range
    - Party positions (in favor, against, abstaining)
    - **Data quality** (has_party_details flag)

    **Important**: Only 8-20% of atividades votes have complete party voting details.
    Use `has_party_details=true` to filter for votes with complete data.

    **Case-Insensitive Parameters:**
    - Legislature codes are case-insensitive
    - Party codes are case-insensitive
    - Text search is case-insensitive (uses ILIKE)

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
        qb.add_equals("ativ_id", ativ_id)
        qb.add_equals("tipo", tipo)
        qb.add_equals("resultado", resultado)
        qb.add_equals("has_party_details", has_party_details)
        qb.add_gte("data", data_desde, "data_desde")
        qb.add_lte("data", data_ate, "data_ate")
        qb.add_list_contains("detalhe_parsed.a_favor", partido_favor, "partido_favor")
        qb.add_list_contains("detalhe_parsed.contra", partido_contra, "partido_contra")
        qb.add_list_contains("detalhe_parsed.abstencao", partido_abstencao, "partido_abstencao")
        qb.add_text_search("assunto", q)

        where_clause = qb.build_where()
        params = qb.get_params()

        # Get total count
        count_query = f"SELECT count(*) FROM atividades_votacoes {where_clause}"
        total = db.execute(count_query, params).fetchone()[0]

        # Get paginated results
        data_query = f"""
            SELECT
                vot_id,
                ativ_id,
                legislatura,
                assunto,
                tipo,
                data,
                resultado,
                has_party_details
            FROM atividades_votacoes
            {where_clause}
            ORDER BY data DESC NULLS LAST, vot_id
            LIMIT $limit OFFSET $offset
        """
        params["limit"] = limit
        params["offset"] = offset

        results = db.execute(data_query, params).fetchall()

        # Convert to models
        items = [
            AtividadeVotacaoListItem(
                vot_id=row[0],
                ativ_id=row[1],
                legislatura=row[2],
                assunto=row[3],
                tipo=row[4],
                data=row[5],
                resultado=row[6],
                has_party_details=row[7]
            )
            for row in results
        ]

        return APIResponse(
            data=items,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION)
        )

    except Exception as e:
        logger.error("list_atividades_votacoes_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error listing atividades votes: {str(e)}")


@router.get("/votacoes/{vot_id}", response_model=AtividadeVotacao)
def get_atividade_votacao(
    vot_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single vote from an activity by vote ID.

    Returns complete vote details including parsed party voting data.
    """
    try:
        query = """
            SELECT
                vot_id,
                ativ_id,
                legislatura,
                assunto,
                tipo,
                numero,
                data_entrada,
                autores_gp,
                data,
                resultado,
                descricao,
                reuniao,
                unanime,
                ausencias,
                detalhe,
                detalhe_parsed,
                has_party_details,
                source
            FROM atividades_votacoes
            WHERE vot_id = $vot_id
        """

        result = db.execute(query, {"vot_id": vot_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"Vote {vot_id} not found")

        return AtividadeVotacao(
            vot_id=result[0],
            ativ_id=result[1],
            legislatura=result[2],
            assunto=result[3],
            tipo=result[4],
            numero=result[5],
            data_entrada=result[6],
            autores_gp=result[7],
            data=result[8],
            resultado=result[9],
            descricao=result[10],
            reuniao=result[11],
            unanime=result[12],
            ausencias=result[13],
            detalhe=result[14],
            detalhe_parsed=result[15],
            has_party_details=result[16],
            source=result[17]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_atividade_votacao_error", error=str(e), vot_id=vot_id)
        raise HTTPException(status_code=500, detail=f"Error retrieving vote: {str(e)}")
