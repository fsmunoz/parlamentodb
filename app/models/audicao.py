"""
Pydantic models for committee Audições (hearings) and Audiências (audiences).

Frederico Muñoz <fsmunoz@gmail.com>

Both come from the Atividades dataset and share the same shape: which external entities a
committee received, when and about what. Audiências are requested by the entity (and may or
may not be granted); Audições are called by the committee.
"""

from datetime import date
from pydantic import BaseModel, Field


class Audicao(BaseModel):
    """Committee hearing."""

    aud_id: str = Field(..., description="Hearing ID")
    legislatura: str = Field(..., description="Legislature (L13 ... L17)")
    numero: str | None = Field(None, description="Hearing number, '<n>-<committee>-<legislature>'")
    comissao_sigla: str | None = Field(None, description="Committee acronym (e.g. COFAP), from numero")
    assunto: str | None = Field(None, description="Subject")
    entidades: str | None = Field(None, description="Entities heard")
    data: date | None = Field(None, description="Date")
    sessao: str | None = Field(None, description="Legislative session")


class Audiencia(Audicao):
    """Committee audience (requested by the entity)."""

    concedida: str | None = Field(None, description="Status (Concedida, Em apreciação, Não realizada)")
