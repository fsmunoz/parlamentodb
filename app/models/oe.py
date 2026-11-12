"""
Pydantic models for Orçamento do Estado (OE) responses.

Frederico Muñoz <fsmunoz@gmail.com>

The propostas de alteração (amendments) to each State Budget and their votes. Votes use the same
detalhe_parsed / detalhe_deputados structures as /iniciativas/votacoes.
"""

from datetime import date
from pydantic import BaseModel, Field

from app.models.votacao import DetalheVotos, DeputadoVoto, VOTE_DETAIL_DOCS


class Orcamento(BaseModel):
    """One State Budget, with the totals of its propostas de alteração."""

    ano: int = Field(..., description="Budget year (OE2027 -> 2027)")
    legislatura: str = Field(..., description="Legislature where it was debated")
    propostas: int = Field(..., description="Number of propostas de alteração")
    votacoes: int = Field(..., description="Number of votes on them")
    aprovadas: int = Field(..., description="Propostas with an approved estado (including partially approved)")
    data_ultima_votacao: date | None = Field(None, description="Date of the latest vote (none while still in debate)")


class Proponente(BaseModel):
    nome: str | None = Field(None, description="Deputy name")
    partido: str | None = Field(None, description="Party code at the time (Ninsc for non-attached deputies)")


class Artigo(BaseModel):
    artigo: str | None = Field(None, description="Budget bill article (e.g. 'Artigo 100.º')")
    titulo: str | None = None
    texto: str | None = Field(None, description="Article text (truncated in the source)")
    estado: str | None = None


class PropostaListItem(BaseModel):
    """Proposta de alteração for list responses."""

    prop_id: str = Field(..., description="Proposta ID (unique across all budgets)")
    numero: str = Field(..., description="Proposta number within the budget (e.g. '2076C')")
    ano: int = Field(..., description="Budget year")
    legislatura: str
    data: date | None = Field(None, description="Submission date")
    titulo: str | None = None
    temas: list[str] | None = Field(None, description="Subject areas")
    tipo: str | None = Field(None, description="Type (Aditamento, Substituição, Emenda, Eliminação, ...)")
    estado: str | None = Field(None, description="Status (e.g. 'Aprovado(a) em Comissão', 'Aguarda Voto em Comissão')")
    autores_gp: list[str] | None = Field(None, description="Author parties (empty when authored only by non-attached deputies)")
    n_votacoes: int = Field(0, description="Number of votes")


class Proposta(PropostaListItem):
    """Full proposta de alteração."""

    incide: str | None = Field(None, description="Articulado (bill articles) or Mapas (budget tables)")
    proponentes: list[Proponente] | None = None
    numero_artigo_novo: str | None = Field(None, description="Number of the article it adds, if any")
    artigos: list[Artigo] | None = Field(None, description="Bill articles it changes")
    ficheiro: str | None = Field(None, description="Link to the proposta PDF")


class OEVotacaoListItem(BaseModel):
    """OE vote for list responses."""

    vot_id: str = Field(..., description="Vote ID: {prop_id}_{n} (the source has no vote IDs)")
    prop_id: str
    numero: str
    ano: int
    legislatura: str
    titulo: str | None = Field(None, description="Proposta title")
    autores_gp: list[str] | None = None
    data: date | None = None
    resultado: str | None = Field(None, description="Result (Aprovado(a), Rejeitado(a), ...)")
    tipo_reuniao: str | None = Field(None, description="COM (committee) or RP (plenary)")
    detalhe_parsed: DetalheVotos | None = Field(None, description="Party positions (same structure as /iniciativas/votacoes)")


class OEVotacao(OEVotacaoListItem):
    """Full OE vote."""

    tipo: str | None = Field(None, description="Proposta type")
    resultado_completo: str | None = Field(None, description="Result with place (e.g. 'Rejeitado(a) em Comissão')")
    descricao: str | None = None
    subdescricao: str | None = None
    unanime: str | None = Field(None, description="'unanime' for unanimous votes")
    detalhe_deputados: list[DeputadoVoto] | None = Field(None, description=VOTE_DETAIL_DOCS["detalhe_deputados"])
    source: str = Field("oe", description="Vote source discriminator")
