"""
Pydantic models for Partido (parliamentary group/party) responses.
"""

from pydantic import BaseModel, Field


class Partido(BaseModel):
    """Parliamentary group/party record."""

    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    gp_sigla: str = Field(..., description="Party abbreviation (e.g., PS, PSD)")
    gp_nome: str = Field(..., description="Full party name")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "gp_sigla": "PS",
                "gp_nome": "Partido Socialista"
            }]
        }
    }


class PartidoListItem(BaseModel):
    """Simplified party record for list responses."""

    legislatura: str
    gp_sigla: str
    gp_nome: str

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "gp_sigla": "PS",
                "gp_nome": "Partido Socialista"
            }]
        }
    }
