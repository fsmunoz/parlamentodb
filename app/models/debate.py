"""
Pydantic models for Debate (plenary debate) responses.

Frederico Muñoz <fsmunoz@gmail.com>

Plenary debates from the Atividades dataset: political statements, debates with the
Prime Minister, urgency debates, State of the Nation, etc.
"""

from datetime import date
from typing import Any
from pydantic import BaseModel, Field


class DebateListItem(BaseModel):
    """Debate record for list responses."""

    debate_id: str = Field(..., description="Debate ID")
    legislatura: str = Field(..., description="Legislature (L13 ... L17)")
    tipo_debate: str | None = Field(None, description="Debate type code (e.g. 10, 16)")
    tipo_debate_desig: str | None = Field(None, description="Debate type (e.g. 'Declarações Políticas')")
    assunto: str | None = Field(None, description="Subject")
    data_debate: date | None = Field(None, description="Debate date")
    autor_gp: str | None = Field(None, description="Author parliamentary group")
    autores_deputados: str | None = Field(None, description="Author deputy, e.g. 'Name (PARTY)'")


class Debate(DebateListItem):
    """Full debate detail."""

    data_entrada: date | None = Field(None, description="Entry date")
    tipo_autor: str | None = Field(None, description="Author type")
    artigo: str | None = Field(None, description="Rules of procedure article")
    sessao: str | None = Field(None, description="Legislative session")
    observacoes: str | None = Field(None, description="Observations")
    intervencoes: list[str] | None = Field(None, description="IDs of the speeches (intervenções) in this debate")
    publicacao: list[Any] | None = Field(None, description="DAR publication references (URLDiario links)")
