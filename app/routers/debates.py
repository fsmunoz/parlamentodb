"""
Debates (plenary debates) endpoints.

Frederico Muñoz <fsmunoz@gmail.com>
"""

from datetime import date
from fastapi import APIRouter, Depends, Query
import duckdb

from app.config import settings
from app.dependencies import get_db
from app.models.debate import Debate, DebateListItem
from app.models.common import APIResponse
from app.models.validators import validate_legislatura, validate_partido, validate_pagination
from app.queries.utils import QueryBuilder, paginated_list, get_one

router = APIRouter(prefix="/api/v1/debates", tags=["debates"])


@router.get("/", response_model=APIResponse[DebateListItem])
def list_debates(
    legislatura: str | None = Query(None, description="Filter by legislature (L13 ... L17)"),
    tipo: str | None = Query(None, description="Filter by debate type code (tipo_debate, e.g. 10 = Declarações Políticas)"),
    autor_gp: str | None = Query(None, description="Filter by author parliamentary group. Case-insensitive."),
    data_desde: date | None = Query(None, description="Minimum debate date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum debate date (YYYY-MM-DD)"),
    q: str | None = Query(None, description="Search in subject (assunto). Case-insensitive substring match."),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    List plenary debates (political statements, debates with the Prime Minister,
    urgency debates, State of the Nation, ...). Default limit is 50, maximum is 500.
    """
    limit, offset = validate_pagination(limit, offset)
    qb = QueryBuilder()
    qb.add_equals("legislatura", validate_legislatura(legislatura))
    qb.add_equals("tipo_debate", tipo)
    qb.add_equals("autor_gp", validate_partido(autor_gp))
    qb.add_gte("data_debate", data_desde, "data_desde")
    qb.add_lte("data_debate", data_ate, "data_ate")
    qb.add_text_search("assunto", q)
    return paginated_list(db, "debates", qb, DebateListItem, "data_debate DESC NULLS LAST, debate_id", limit, offset)


@router.get("/{debate_id}", response_model=Debate)
def get_debate(debate_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Get a single debate, including speech IDs and DAR publication links."""
    return get_one(db, "debates", "debate_id", debate_id, Debate)
