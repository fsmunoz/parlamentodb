"""
Orçamento do Estado (State Budget) endpoints: propostas de alteração and their votes.

Frederico Muñoz <fsmunoz@gmail.com>

The budget bill itself (and its generalidade / votação final global votes) is an iniciativa; these
are the amendments proposed during the especialidade phase and their (mostly committee) votes.
"""

from datetime import date
from fastapi import APIRouter, Depends, Query
import duckdb

from app.config import settings
from app.dependencies import get_db
from app.models.common import APIResponse
from app.models.oe import Orcamento, Proposta, PropostaListItem, OEVotacao, OEVotacaoListItem
from app.models.validators import validate_legislatura, validate_partido, validate_pagination, validate_tipos_reuniao
from app.queries.utils import QueryBuilder, paginated_list, get_one

router = APIRouter(prefix="/api/v1/oe", tags=["oe"])

ORCAMENTOS = """(
    SELECT p.*, v.data_ultima_votacao
    FROM (
        SELECT ano, legislatura, count(*)::INTEGER AS propostas,
               sum(n_votacoes)::INTEGER AS votacoes,
               (count(*) FILTER (WHERE estado ILIKE 'Aprovad%'))::INTEGER AS aprovadas
        FROM oe_propostas GROUP BY ano, legislatura
    ) p
    LEFT JOIN (SELECT ano, max(data) AS data_ultima_votacao FROM oe_votacoes GROUP BY ano) v USING (ano)
) AS orcamentos"""

ANO = Query(None, ge=2000, description="Budget year (e.g. 2027 for OE2027)")


@router.get("/", response_model=APIResponse[Orcamento])
def list_orcamentos(
    legislatura: str | None = Query(None, description="Filter by legislature (L14 ... L17)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """List the State Budgets available, with totals of propostas, votes and approved propostas."""
    limit, offset = validate_pagination(limit, offset)
    qb = QueryBuilder().add_equals("legislatura", validate_legislatura(legislatura))
    return paginated_list(db, ORCAMENTOS, qb, Orcamento, "ano DESC", limit, offset)


@router.get("/propostas/", response_model=APIResponse[PropostaListItem])
def list_propostas(
    ano: int | None = ANO,
    legislatura: str | None = Query(None, description="Filter by legislature (L14 ... L17)"),
    autor_gp: str | None = Query(None, description="Filter by author party (e.g. PS, L, CDS-PP). Case-insensitive."),
    estado: str | None = Query(None, description="Status, substring match (e.g. 'aprovado', 'em plenário', 'aguarda')"),
    tipo: str | None = Query(None, description="Type, substring match (e.g. 'aditamento', 'substituição')"),
    tema: str | None = Query(None, description="Subject area, substring match (e.g. 'saúde')"),
    q: str | None = Query(None, description="Search in title. Case-insensitive substring match."),
    data_desde: date | None = Query(None, description="Minimum submission date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum submission date (YYYY-MM-DD)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """List propostas de alteração to the State Budget. Default limit is 50, maximum is 500."""
    limit, offset = validate_pagination(limit, offset)
    qb = QueryBuilder()
    qb.add_equals("ano", ano)
    qb.add_equals("legislatura", validate_legislatura(legislatura))
    qb.add_list_contains("autores_gp", validate_partido(autor_gp), "autor_gp")
    qb.add_text_search("estado", estado)
    qb.add_text_search("tipo", tipo)
    qb.add_text_search("array_to_string(temas, '; ')", tema, "tema")
    qb.add_text_search("titulo", q)
    qb.add_gte("data", data_desde, "data_desde")
    qb.add_lte("data", data_ate, "data_ate")
    return paginated_list(db, "oe_propostas", qb, PropostaListItem, "data DESC NULLS LAST, prop_id", limit, offset)


@router.get("/propostas/{prop_id}", response_model=Proposta)
def get_proposta(prop_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Get a single proposta de alteração, with proponents, articles and PDF link."""
    return get_one(db, "oe_propostas", "prop_id", prop_id, Proposta)


@router.get("/votacoes/", response_model=APIResponse[OEVotacaoListItem])
def list_oe_votacoes(
    ano: int | None = ANO,
    legislatura: str | None = Query(None, description="Filter by legislature (L14 ... L17)"),
    prop_id: str | None = Query(None, description="Filter by proposta ID"),
    autor_gp: str | None = Query(None, description="Filter by author party of the proposta. Case-insensitive."),
    resultado: str | None = Query(None, description="Result, substring match (e.g. 'aprovado', 'rejeitado')"),
    tipo_reuniao: str | None = Query(None, description="Comma-separated: COM (committee), RP (plenary). Default: all."),
    partido_favor: str | None = Query(None, description="Filter by party voting in favor. Case-insensitive."),
    partido_contra: str | None = Query(None, description="Filter by party voting against. Case-insensitive."),
    partido_abstencao: str | None = Query(None, description="Filter by party abstaining. Case-insensitive."),
    q: str | None = Query(None, description="Search in proposta title. Case-insensitive substring match."),
    data_desde: date | None = Query(None, description="Minimum vote date (YYYY-MM-DD)"),
    data_ate: date | None = Query(None, description="Maximum vote date (YYYY-MM-DD)"),
    limit: int = Query(settings.DEFAULT_LIMIT, le=settings.MAX_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """List votes on propostas de alteração. Default limit is 50, maximum is 500."""
    limit, offset = validate_pagination(limit, offset)
    qb = QueryBuilder()
    qb.add_equals("ano", ano)
    qb.add_equals("legislatura", validate_legislatura(legislatura))
    qb.add_equals("prop_id", prop_id)
    qb.add_list_contains("autores_gp", validate_partido(autor_gp), "autor_gp")
    qb.add_text_search("resultado", resultado)
    qb.add_in("tipo_reuniao", validate_tipos_reuniao(tipo_reuniao))
    qb.add_list_contains("detalhe_parsed.a_favor", validate_partido(partido_favor), "partido_favor")
    qb.add_list_contains("detalhe_parsed.contra", validate_partido(partido_contra), "partido_contra")
    qb.add_list_contains("detalhe_parsed.abstencao", validate_partido(partido_abstencao), "partido_abstencao")
    qb.add_text_search("titulo", q)
    qb.add_gte("data", data_desde, "data_desde")
    qb.add_lte("data", data_ate, "data_ate")
    return paginated_list(db, "oe_votacoes", qb, OEVotacaoListItem, "data DESC NULLS LAST, vot_id", limit, offset)


@router.get("/votacoes/{vot_id}", response_model=OEVotacao)
def get_oe_votacao(vot_id: str, db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Get a single OE vote, with deputies voting individually."""
    return get_one(db, "oe_votacoes", "vot_id", vot_id, OEVotacao)
