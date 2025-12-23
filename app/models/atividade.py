"""
Pydantic models for Atividade (parliamentary activity) responses.

Frederico Muñoz <fsmunoz@gmail.com>

Atividades are parliamentary activities like condemnation votes, motions, elections, etc.
They differ from Iniciativas in that they don't follow the legislative process and contain
votes directly in the data rather than nested in events.
"""

from datetime import date
from typing import Any
from pydantic import BaseModel, Field

# Reuse DetalheVotos from votacao
from app.models.votacao import DetalheVotos


class AtividadeListItem(BaseModel):
    """
    Simplified activity for list endpoint.

    Used in paginated list responses to minimize payload size.
    """

    ativ_id: str = Field(..., description="Synthetic activity ID (legislature_tipo_numero or hash)")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    ativ_tipo: str | None = Field(None, description="Activity type (VOT, MOC, PRG, OEX, SES, ITG)")
    ativ_desc_tipo: str | None = Field(None, description="Activity type description")
    ativ_numero: str | None = Field(None, description="Activity number (can be null)")
    ativ_assunto: str | None = Field(None, description="Activity subject/title")
    data_entrada: date | None = Field(None, description="Entry/submission date")
    ativ_autores_gp: list[str] | None = Field(None, description="Array of party authors")
    has_votes: bool = Field(False, description="True if votacao_debate array is non-empty")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "ativ_id": "L17_VOT_1",
                "legislatura": "L17",
                "ativ_tipo": "VOT",
                "ativ_desc_tipo": "Voto",
                "ativ_numero": "1",
                "ativ_assunto": "Voto de pesar pelo falecimento de José Saraiva",
                "data_entrada": "2025-03-10",
                "ativ_autores_gp": ["PS", "PSD"],
                "has_votes": True
            }]
        }
    }


class Atividade(BaseModel):
    """
    Full activity detail.

    Includes all fields and nested structures (votes, publications, etc.).
    """

    ativ_id: str = Field(..., description="Synthetic activity ID")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    ativ_tipo: str | None = Field(None, description="Activity type (VOT, MOC, PRG, OEX, SES, ITG)")
    ativ_desc_tipo: str | None = Field(None, description="Activity type description")
    ativ_numero: str | None = Field(None, description="Activity number")
    ativ_assunto: str | None = Field(None, description="Activity subject/title")
    data_entrada: date | None = Field(None, description="Entry/submission date")
    data_agendamento_debate: date | None = Field(None, description="Scheduled debate date")
    data_anuncio: date | None = Field(None, description="Announcement date")
    ativ_autores_gp: list[str] | None = Field(None, description="Array of party authors")
    ativ_tipo_autor: str | None = Field(None, description="Author type (e.g., 'Grupos Parlamentares')")
    sessao: str | None = Field(None, description="Session")
    observacoes: str | None = Field(None, description="Observations/notes")
    votacao_debate: list[Any] | None = Field(None, description="Full vote array (nested structure)")
    publicacao: list[Any] | None = Field(None, description="Publication references")
    publicacao_debate: list[Any] | None = Field(None, description="Debate publication references")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "ativ_id": "L17_VOT_1",
                "legislatura": "L17",
                "ativ_tipo": "VOT",
                "ativ_desc_tipo": "Voto",
                "ativ_numero": "1",
                "ativ_assunto": "Voto de pesar pelo falecimento de José Saraiva",
                "data_entrada": "2025-03-10",
                "data_agendamento_debate": None,
                "data_anuncio": None,
                "ativ_autores_gp": ["PS", "PSD"],
                "ativ_tipo_autor": "Grupos Parlamentares",
                "sessao": "1",
                "observacoes": None,
                "votacao_debate": [],
                "publicacao": [],
                "publicacao_debate": []
            }]
        }
    }


class AtividadeVotacaoListItem(BaseModel):
    """
    Simplified vote for list endpoint.

    Used in paginated vote list responses.
    """

    vot_id: str = Field(..., description="Vote ID")
    ativ_id: str = Field(..., description="Activity ID (links to atividade)")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    assunto: str | None = Field(None, description="Activity subject (from ativ_assunto)")
    tipo: str | None = Field(None, description="Activity type")
    data: date | None = Field(None, description="Vote date")
    resultado: str | None = Field(None, description="Vote result (Aprovado, Rejeitado)")
    has_party_details: bool = Field(..., description="True if detalhe field has party voting data")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "vot_id": "139134",
                "ativ_id": "L17_VOT_1",
                "legislatura": "L17",
                "assunto": "Voto de saudação pelo 50.º aniversário da CAP",
                "tipo": "VOT",
                "data": "2025-07-11",
                "resultado": "Aprovado",
                "has_party_details": True
            }]
        }
    }


class AtividadeVotacao(BaseModel):
    """
    Full vote detail from an atividade.

    Includes all fields and parsed party voting data.
    """

    vot_id: str = Field(..., description="Vote ID")
    ativ_id: str = Field(..., description="Activity ID")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    assunto: str | None = Field(None, description="Activity subject")
    tipo: str | None = Field(None, description="Activity type")
    numero: str | None = Field(None, description="Activity number")
    data_entrada: date | None = Field(None, description="Activity entry date")
    autores_gp: list[str] | None = Field(None, description="Party authors")

    # Vote fields
    data: date | None = Field(None, description="Vote date")
    resultado: str | None = Field(None, description="Vote result (Aprovado, Rejeitado)")
    descricao: str | None = Field(None, description="Vote description")
    reuniao: str | None = Field(None, description="Meeting number")
    unanime: str | None = Field(None, description="Unanimous vote flag ('unanime' or null)")
    ausencias: list[str] | None = Field(None, description="Absent parties/members")
    detalhe: str | None = Field(None, description="Original HTML voting details")
    detalhe_parsed: DetalheVotos | None = Field(None, description="Structured party voting breakdown")
    has_party_details: bool = Field(..., description="True if detalhe field is populated")
    source: str = Field(..., description="Always 'atividade' to distinguish from initiative votes")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "vot_id": "139134",
                "ativ_id": "L17_VOT_1",
                "legislatura": "L17",
                "assunto": "Voto de saudação pelo 50.º aniversário da CAP",
                "tipo": "VOT",
                "numero": "1",
                "data_entrada": "2025-07-08",
                "autores_gp": ["Comissão de Agricultura e Pescas (CAPes)"],
                "data": "2025-07-11",
                "resultado": "Aprovado",
                "descricao": None,
                "reuniao": "12",
                "unanime": None,
                "ausencias": None,
                "detalhe": "A Favor: <I>PSD</I>, <I> CH</I>, <I> PS</I>, <I> IL</I>...",
                "detalhe_parsed": {
                    "a_favor": ["PSD", "CH", "PS", "IL", "L", "CDS-PP", "JPP"],
                    "contra": ["PAN"],
                    "abstencao": ["PCP", "BE"],
                    "ausencia": []
                },
                "has_party_details": True,
                "source": "atividade"
            }]
        }
    }
