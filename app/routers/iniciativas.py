"""
Iniciativas (legislative initiatives) endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Iniciativa related information
"""

from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.iniciativa import Iniciativa, IniciativaListItem
from app.models.evento import EventoListItem
from app.models.common import APIResponse, PaginationMeta, APIMeta
from app.models.validators import validate_legislatura, validate_partido, validate_pagination
from app.queries.utils import QueryBuilder

router = APIRouter(prefix="/api/v1/iniciativas", tags=["iniciativas"])
logger = structlog.get_logger()


@router.get("/", response_model=APIResponse[IniciativaListItem])
def list_iniciativas(
    legislatura: str | None = Query(None, description="Filter by legislature (L15, L16, L17)"),
    ini_nr: str | None = Query(None, description="Filter by initiative number (not unique - may return multiple)"),
    tipo: str | None = Query(None, description="Filter by initiative type code"),
    q: str | None = Query(None, description="Search in initiative title (ini_titulo). Case-insensitive substring match."),
    data_desde: date | None = Query(None, description="Filter by event date from (YYYY-MM-DD) - queries actual event dates"),
    data_ate: date | None = Query(None, description="Filter by event date until (YYYY-MM-DD) - queries actual event dates"),
    evento_fase: str | None = Query(None, description="Filter by event type(s). Comma-separated for multiple: 'Entrada,Admissão'"),
    autor_gp: str | None = Query(None, description="Filter by parliamentary group author (e.g., PS, PSD, CH)"),
    autor_tipo: str | None = Query(None, description="Filter by author type (e.g., Governo, Comissões)"),
    dep_cad_id: str | None = Query(None, description="Filter by deputy author (deputy ID)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List legislative initiatives with optional filters.

    Returns a paginated list of initiatives. Use query parameters to filter by:
    - Legislature (L15, L16, L17)
    - Initiative type (tipo: PPL, PJL, PJR, etc.)
    - Parliamentary group author (autor_gp: PS, PSD, CH, etc.)
    - Author type (autor_tipo: Governo, Comissões, Grupos Parlamentares, etc.)
    - Deputy author (dep_cad_id: deputy ID) - filters initiatives by individual deputy authorship
    - Event date range (data_desde, data_ate) - filters by actual event dates in ini_eventos
    - Event type (evento_fase) - e.g., "Entrada", "Votação na generalidade"

    Default limit is 50 records, maximum is 500.
    """
    try:
        # Validate inputs
        legislatura = validate_legislatura(legislatura)
        autor_gp = validate_partido(autor_gp)
        limit, offset = validate_pagination(limit, offset)

        # Parse event types if provided
        event_types = None
        if evento_fase:
            event_types = [e.strip() for e in evento_fase.split(',') if e.strip()]

        # Determine if we need event filtering (CTE query)
        needs_event_filtering = data_desde or data_ate or event_types

        # Build base WHERE clause using QueryBuilder (non-event filters)
        qb = QueryBuilder()
        qb.add_equals("legislatura", legislatura)
        qb.add_equals("ini_nr", ini_nr)
        qb.add_equals("ini_tipo", tipo, "tipo")

        if autor_gp:
            qb.add_custom("""
            list_contains(
                list_transform(ini_autor_grupos_parlamentares, x -> x.GP),
                $autor_gp
            )
        """, {"autor_gp": autor_gp})

        if autor_tipo:
            qb.add_custom("ini_autor_outros.nome = $autor_tipo", {"autor_tipo": autor_tipo})

        if dep_cad_id:
            qb.add_custom("""
            list_contains(
                list_transform(ini_autor_deputados, x -> x.idCadastro),
                $dep_cad_id
            )
        """, {"dep_cad_id": dep_cad_id})

        qb.add_text_search("ini_titulo", q)

        base_where_clauses = qb.clauses
        params = qb.get_params()

        if needs_event_filtering:
            # Use CTE to filter by event dates
            # Build WHERE clause for base filters
            if base_where_clauses:
                base_where = "WHERE " + " AND ".join(base_where_clauses) + " AND ini_eventos IS NOT NULL"
            else:
                base_where = "WHERE ini_eventos IS NOT NULL"

            # Build event filter clauses
            event_where_clauses = []
            if data_desde:
                event_where_clauses.append("evento.DataFase >= $data_desde")
                params["data_desde"] = data_desde
            if data_ate:
                event_where_clauses.append("evento.DataFase <= $data_ate")
                params["data_ate"] = data_ate
            if event_types:
                event_where_clauses.append("evento.Fase = ANY($event_types)")
                params["event_types"] = event_types

            event_where = " AND ".join(event_where_clauses)

            # Count query with CTE
            count_query = f"""
                WITH event_filtered AS (
                    SELECT
                        ini_id,
                        UNNEST(ini_eventos) as evento
                    FROM iniciativas
                    {base_where}
                ),
                matching_initiatives AS (
                    SELECT DISTINCT ini_id
                    FROM event_filtered
                    WHERE {event_where}
                )
                SELECT COUNT(*) FROM matching_initiatives
            """
            total = db.execute(count_query, params).fetchone()[0]

            # Data query with CTE
            data_query = f"""
                WITH event_filtered AS (
                    SELECT
                        ini_id, ini_nr, legislatura, ini_tipo,
                        ini_desc_tipo, ini_titulo,
                        list_transform(ini_autor_grupos_parlamentares, x -> x.GP) as autor_gp,
                        ini_data,
                        UNNEST(ini_eventos) as evento
                    FROM iniciativas
                    {base_where}
                ),
                matching_initiatives AS (
                    SELECT DISTINCT
                        ini_id, ini_nr, legislatura, ini_tipo,
                        ini_desc_tipo, ini_titulo, autor_gp, ini_data
                    FROM event_filtered
                    WHERE {event_where}
                )
                SELECT
                    ini_id, ini_nr, legislatura, ini_tipo,
                    ini_desc_tipo, ini_titulo, autor_gp
                FROM matching_initiatives
                ORDER BY ini_data DESC NULLS LAST, ini_id DESC
                LIMIT $limit OFFSET $offset
            """
        else:
            # Simple query (no event filtering)
            where_sql = "WHERE " + " AND ".join(base_where_clauses) if base_where_clauses else ""

            count_query = f"SELECT COUNT(*) FROM iniciativas {where_sql}"
            total = db.execute(count_query, params).fetchone()[0]

            data_query = f"""
                SELECT
                    ini_id,
                    ini_nr,
                    legislatura,
                    ini_tipo,
                    ini_desc_tipo,
                    ini_titulo,
                    list_transform(ini_autor_grupos_parlamentares, x -> x.GP) as autor_gp
                FROM iniciativas
                {where_sql}
                ORDER BY ini_data DESC NULLS LAST, ini_id DESC
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
                ini_titulo=row[5],
                autor_gp=row[6]
            )
            for row in rows
        ]

        return APIResponse(
            data=data,
            pagination=PaginationMeta(limit=limit, offset=offset, total=total),
            meta=APIMeta(version=settings.API_VERSION)
        )

    except Exception as e:
        logger.error("initiatives_list_error", filters=params, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error listing initiatives"
        )


@router.get("/{ini_id}", response_model=Iniciativa)
def get_iniciativa(
    ini_id: str,
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get a single initiative by its unique ID.

    The ini_id is the unique identifier for each initiative.
    Use the list endpoint to find the ini_id for a specific initiative.
    If you need to search by initiative number (ini_nr), use the filter:
    GET /iniciativas/?ini_nr=7&legislatura=L17
    """
    try:
        query = "SELECT * FROM iniciativas WHERE ini_id = $ini_id"
        params = {"ini_id": ini_id}

        # Execute once and save cursor
        cursor = db.execute(query, params)
        column_names = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Initiative with ini_id={ini_id} not found"
            )

        # Convert to dict
        row_dict = dict(zip(column_names, result))

        return Iniciativa(**row_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("initiative_fetch_error", ini_id=ini_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving initiative data"
        )


@router.get("/{ini_id}/eventos", response_model=APIResponse[EventoListItem])
def list_eventos(
    ini_id: str,
    evento_fase: str | None = Query(None, description="Filter by event type(s). Comma-separated: 'Entrada,Admissão'"),
    data_desde: date | None = Query(None, description="Minimum event date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum event date (YYYY-MM-DD)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List all events for a specific initiative.

    Returns a flattened list of legislative events for the given initiative,
    with optional filtering by event type and date range.

    Common event types:
    - "Entrada" - Initiative submission
    - "Admissão" - Admission
    - "Anúncio" - Announcement
    - "Votação na generalidade" - General vote
    - "Discussão generalidade" - General discussion
    - "Baixa comissão especialidade" - Committee referral
    - "Publicação" - Publication
    """
    try:
        # Verify initiative exists
        check_query = "SELECT ini_nr, legislatura, ini_titulo, ini_tipo FROM iniciativas WHERE ini_id = $ini_id"
        check_result = db.execute(check_query, {"ini_id": ini_id}).fetchone()

        if not check_result:
            raise HTTPException(
                status_code=404,
                detail=f"Initiative with ini_id={ini_id} not found"
            )

        ini_nr, legislatura, ini_titulo, ini_tipo = check_result

        # Parse event types if provided
        event_types = None
        if evento_fase:
            event_types = [e.strip() for e in evento_fase.split(',') if e.strip()]

        # Build event filter clauses
        event_where_clauses = []
        params = {"ini_id": ini_id}

        if data_desde:
            event_where_clauses.append("evento.DataFase >= $data_desde")
            params["data_desde"] = data_desde
        if data_ate:
            event_where_clauses.append("evento.DataFase <= $data_ate")
            params["data_ate"] = data_ate
        if event_types:
            event_where_clauses.append("evento.Fase = ANY($event_types)")
            params["event_types"] = event_types

        event_where = "WHERE " + " AND ".join(event_where_clauses) if event_where_clauses else ""

        # Count query
        count_query = f"""
            WITH flattened AS (
                SELECT UNNEST(ini_eventos) as evento
                FROM iniciativas
                WHERE ini_id = $ini_id AND ini_eventos IS NOT NULL
            )
            SELECT COUNT(*) FROM flattened
            {event_where}
        """
        total = db.execute(count_query, params).fetchone()[0]

        # Data query
        data_query = f"""
            WITH flattened AS (
                SELECT UNNEST(ini_eventos) as evento
                FROM iniciativas
                WHERE ini_id = $ini_id AND ini_eventos IS NOT NULL
            )
            SELECT
                evento.EvtId,
                evento.OevId,
                evento.Fase,
                evento.CodigoFase,
                evento.DataFase,
                evento.ObsFase,
                evento.Votacao,
                evento.Comissao,
                evento.AnexosFase,
                evento.Links,
                evento.ActId,
                evento.ActividadesConjuntas,
                evento.IniciativasConjuntas
            FROM flattened
            {event_where}
            ORDER BY evento.DataFase ASC NULLS LAST
            LIMIT $limit OFFSET $offset
        """
        params.update({"limit": limit, "offset": offset})

        rows = db.execute(data_query, params).fetchall()

        # Convert to models
        data = [
            EventoListItem(
                ini_id=ini_id,
                ini_nr=ini_nr,
                legislatura=legislatura,
                ini_titulo=ini_titulo,
                ini_tipo=ini_tipo,
                evt_id=row[0],
                oev_id=row[1],
                fase=row[2],
                codigo_fase=row[3],
                data_fase=row[4],
                obs_fase=row[5],
                votacao=row[6],
                comissao=row[7],
                anexos_fase=row[8],
                links=row[9],
                act_id=row[10],
                atividades_conjuntas=row[11],
                iniciativas_conjuntas=row[12]
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
        logger.error("eventos_fetch_error", ini_id=ini_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving initiative events"
        )
