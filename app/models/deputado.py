"""
Pydantic models for Deputado (deputy/MP) responses.
"""

from datetime import date
from pydantic import BaseModel, Field


class PartidoHistorico(BaseModel):
    """Historical party affiliation record."""

    gp_sigla: str = Field(..., description="Party abbreviation (e.g., PS, PSD)")
    gp_dt_inicio: date | None = Field(None, description="Start date of party affiliation")
    gp_dt_fim: date | None = Field(None, description="End date of party affiliation")
    gp_id: float | None = Field(None, description="Party affiliation ID")


class SituacaoHistorico(BaseModel):
    """Historical status record."""

    sio_des: str = Field(..., description="Status description (Efetivo, Suplente, Renunciou)")
    sio_dt_inicio: date | None = Field(None, description="Start date of status")
    sio_dt_fim: date | None = Field(None, description="End date of status")


class Deputado(BaseModel):
    """Deputy (MP) record with full details."""

    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    dep_cad_id: float = Field(..., description="Unique cadastro ID (persistent across legislatures)")
    nome_parlamentar: str = Field(..., description="Parliamentary name")
    nome_completo: str = Field(..., description="Full legal name")
    circulo_atual: str = Field(..., description="Current electoral circle")
    circulo_id: float = Field(..., description="Electoral circle ID")
    partido_atual: str | None = Field(None, description="Current party abbreviation")
    situacao_atual: str | None = Field(None, description="Current status (Efetivo, Suplente, etc.)")
    partido_historico: list[PartidoHistorico] | None = Field(
        None,
        description="Full party affiliation history"
    )
    situacao_historico: list[SituacaoHistorico] | None = Field(
        None,
        description="Full status history"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "dep_cad_id": 9324,
                "nome_parlamentar": "Pedro Nuno Santos",
                "nome_completo": "Pedro Nuno Santos Silva",
                "circulo_atual": "Lisboa",
                "circulo_id": 11,
                "partido_atual": "PS",
                "situacao_atual": "Efetivo",
                "partido_historico": [
                    {
                        "gp_sigla": "PS",
                        "gp_dt_inicio": "2022-03-29",
                        "gp_dt_fim": None,
                        "gp_id": 6890
                    }
                ],
                "situacao_historico": [
                    {
                        "sio_des": "Efetivo",
                        "sio_dt_inicio": "2022-03-29",
                        "sio_dt_fim": None
                    }
                ]
            }]
        }
    }


class DeputadoListItem(BaseModel):
    """Simplified deputy record for list responses."""

    legislatura: str
    dep_cad_id: float
    nome_parlamentar: str
    circulo_atual: str
    partido_atual: str | None
    situacao_atual: str | None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "dep_cad_id": 9324,
                "nome_parlamentar": "Pedro Nuno Santos",
                "circulo_atual": "Lisboa",
                "partido_atual": "PS",
                "situacao_atual": "Efetivo"
            }]
        }
    }
