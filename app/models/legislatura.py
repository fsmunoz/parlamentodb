"""
Pydantic models for Legislatura (legislature metadata) responses.

Frederico Muñoz <fsmunoz@gmail.com>

This includes the 'base information' about the legislature, which is obtained
from a specific file (different from Iniciativas)
"""

from datetime import date
from typing import Any
from pydantic import BaseModel, Field


class LegislaturaListItem(BaseModel):
    """Simplified legislature record for list responses."""

    legislatura: str = Field(..., description="Legislature ID (L15, L16, L17)")
    sigla: str | None = Field(None, description="Legislature roman numeral (XV, XVI, XVII)")
    dtini: date | None = Field(None, description="Legislature start date")
    dtfim: date | None = Field(None, description="Legislature end date (null if ongoing)")
    num_deputados: int | None = Field(None, description="Number of deputies")
    num_grupos: int | None = Field(None, description="Number of parliamentary groups")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "sigla": "XVII",
                "dtini": "2025-06-03",
                "dtfim": None,
                "num_deputados": 1446,
                "num_grupos": 10
            }]
        }
    }


class Legislatura(BaseModel):
    """
    Complete legislature metadata.

    Includes detailed information about the legislature, deputies,
    parliamentary groups, electoral districts, and legislative sessions.
    """

    legislatura: str = Field(..., description="Legislature ID (L15, L16, L17)")

    # Legislature details
    DetalheLegislatura: dict[str, Any] | None = Field(
        None,
        description="Legislature basic information (dates, ID, etc.)"
    )

    # Deputies
    Deputados: list[dict[str, Any]] | None = Field(
        None,
        description="List of all deputies with their details"
    )

    # Parliamentary groups
    GruposParlamentares: list[dict[str, Any]] | None = Field(
        None,
        description="Parliamentary groups/parties"
    )

    # Electoral districts
    CirculosEleitorais: list[dict[str, Any]] | None = Field(
        None,
        description="Electoral districts"
    )

    # Legislative sessions
    SessoesLegislativas: list[dict[str, Any]] | None = Field(
        None,
        description="Legislative sessions within this legislature"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "DetalheLegislatura": {
                    "dtfim": None,
                    "dtini": "2025-06-03",
                    "id": 108,
                    "sigla": "XVII",
                    "siglaAntiga": "XVII"
                },
                "Deputados": [
                    {
                        "DepCadId": 9008.0,
                        "DepNomeCompleto": "Francisco Gabriel Meneses de Lima",
                        "DepNomeParlamentar": "Francisco Lima",
                        "DepCPDes": "Açores"
                    }
                ],
                "GruposParlamentares": [
                    {"Sigla": "PS", "DesignacaoFormal": "Partido Socialista"}
                ]
            }]
        }
    }
