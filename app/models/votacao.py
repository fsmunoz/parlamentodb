"""
Pydantic models for Votacao (vote) responses.

Frederico Muñoz <fsmunoz@gmail.com>

We elevate votacoes to an endpoint since they are so important to determine lots of things,
 namely all the analysis in the www.votoaberto.org portal: in a way, they are more important
than the initiative when the goal is to determine any kind of political sentiment.
"""

from datetime import date
from pydantic import BaseModel, Field


class DetalheVotos(BaseModel):
    """
    Structured vote breakdown by party position.

    Parsed from HTML-formatted detalhe field (through an UDF). Party codes (PCP, PS, etc.)
    represent party positions. Ninsc members are preserved with full names
    (e.g. "John Doe (Ninsc)") since they represent independent positions (only member elected
    by a party, or someone that broke of a party).
    """

    a_favor: list[str] = Field(
        default_factory=list,
        description="Parties/members voting in favor"
    )
    contra: list[str] = Field(
        default_factory=list,
        description="Parties/members voting against"
    )
    abstencao: list[str] = Field(
        default_factory=list,
        description="Parties/members abstaining"
    )
    ausencia: list[str] = Field(
        default_factory=list,
        description="Parties/members absent"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "a_favor": ["PSD", "CDS-PP"],
                "contra": ["CH", "IL", "L", "PCP", "BE", "PAN", "JPP"],
                "abstencao": ["PS"],
                "ausencia": []
            }]
        }
    }


class Votacao(BaseModel):
    """Vote record from a parliamentary session."""

    vot_id: str = Field(..., description="Unique vote ID")
    ini_nr: str = Field(..., description="Initiative number")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    ini_titulo: str = Field(..., description="Initiative title")
    ini_tipo: str | None = Field(None, description="Initiative type")
    fase: str | None = Field(None, description="Legislative phase")
    data_fase: date | None = Field(None, description="Phase date")
    data: date | None = Field(None, description="Vote date")
    resultado: str | None = Field(None, description="Vote result (Aprovado, Rejeitado, etc.)")
    descricao: str | None = Field(None, description="Vote description")
    reuniao: str | None = Field(None, description="Meeting number")
    tipo_reuniao: str | None = Field(None, description="Meeting type")
    unanime: str | None = Field(None, description="Unanimous vote flag")
    ausencias: list[str] | None = Field(None, description="Absent parties/members")
    detalhe: str | None = Field(None, description="HTML-formatted voting details (original)")
    detalhe_parsed: DetalheVotos | None = Field(None, description="Structured voting details by party/member")
    is_nominal: bool | None = Field(None, description="True if vote includes individual MP names (nominal vote)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "vot_id": "140068",
                "ini_nr": "37",
                "legislatura": "L17",
                "ini_titulo": "Orçamento do Estado para 2026",
                "ini_tipo": "Proposta de Lei",
                "fase": "Votação final global",
                "data_fase": "2025-11-27",
                "data": "2025-11-27",
                "resultado": "Aprovado",
                "descricao": None,
                "reuniao": "1",
                "tipo_reuniao": "Plenária",
                "unanime": "Não",
                "ausencias": [],
                "detalhe": None
            }]
        }
    }


class VotacaoListItem(BaseModel):
    """Simplified vote record for list responses."""

    vot_id: str
    ini_nr: str
    legislatura: str
    ini_titulo: str
    fase: str | None
    data: date | None
    resultado: str | None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "vot_id": "140068",
                "ini_nr": "37",
                "legislatura": "L17",
                "ini_titulo": "Orçamento do Estado para 2026",
                "fase": "Votação final global",
                "data": "2025-11-27",
                "resultado": "Aprovado"
            }]
        }
    }
