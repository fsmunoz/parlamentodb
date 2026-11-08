"""
Committee Audições (hearings) and Audiências (audiences) endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Both share filters and shape (see app/models/audicao.py).
"""

from datetime import date
from fastapi import APIRouter, Depends, Query
import duckdb

from app.config import settings
from app.dependencies import get_db
from app.models.audicao import Audicao, Audiencia
from app.models.common import APIResponse
from app.models.validators import validate_legislatura, validate_pagination
from app.queries.utils import QueryBuilder, paginated_list, get_one

router = APIRouter(prefix="/api/v1", tags=["audicoes"])

ORDER_BY = "data DESC NULLS LAST, aud_id"


def audicao_filters(
    legislatura: str | None = Query(None, description="Filter by legislature (L13 ... L17)"),
    comissao: str | None = Query(None, description="Filter by committee acronym (e.g. COFAP). Case-insensitive."),
    entidade: str | None = Query(None, description="Search in entities heard. Case-insensitive substring match."),
    q: str | None = Query(None, description="Search in subject (assunto). Case-insensitive substring match."),
    data_desde: date | None = Query(None, description="Minimum date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum date (YYYY-MM-DD)"),
) -> QueryBuilder:
    """Filters shared by /audicoes and /audiencias."""
    qb = QueryBuilder()
    qb.add_equals("legislatura", validate_legislatura(legislatura))
    if comissao:
        qb.add_custom("lower(comissao_sigla) = lower($comissao)", {"comissao": comissao})
    qb.add_text_search("entidades", entidade)
    qb.add_text_search("assunto", q)
    qb.add_gte("data", data_desde, "data_desde")
    qb.add_lte("data", data_ate, "data_ate")
    return qb


@router.get("/audicoes/", response_model=APIResponse[Audicao])
def list_audicoes(
    qb: QueryBuilder = Depends(audicao_filters),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """List committee hearings (entities called by a committee). Default limit is 50, maximum is 500."""
    return paginated_list(db, "audicoes", qb, Audicao, ORDER_BY, *validate_pagination(limit, offset))


@router.get("/audicoes/{aud_id}", response_model=Audicao)
def get_audicao(aud_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Get a single committee hearing."""
    return get_one(db, "audicoes", "aud_id", aud_id, Audicao)


@router.get("/audiencias/", response_model=APIResponse[Audiencia])
def list_audiencias(
    qb: QueryBuilder = Depends(audicao_filters),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """List committee audiences (requested by the entity). Default limit is 50, maximum is 500."""
    return paginated_list(db, "audiencias", qb, Audiencia, ORDER_BY, *validate_pagination(limit, offset))


@router.get("/audiencias/{aud_id}", response_model=Audiencia)
def get_audiencia(aud_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Get a single committee audience."""
    return get_one(db, "audiencias", "aud_id", aud_id, Audiencia)
