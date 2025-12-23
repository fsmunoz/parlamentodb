"""
Pydantic models for statistics endpoint responses.

Frederico Muñoz <fsmunoz@gmail.com>

These models structure the aggregated statistics computed on-demand from
the silver layer Parquet files via DuckDB queries.
"""

from pydantic import BaseModel, Field
from app.models.common import APIMeta


class FaseOutcome(BaseModel):
    """Initiative outcome statistics grouped by fase."""

    fase: str = Field(..., description="Legislative phase (e.g., 'Votação na generalidade')")
    resultado: str = Field(..., description="Vote outcome (e.g., 'Aprovado', 'Rejeitado')")
    vote_count: int = Field(..., description="Number of voting sessions with this outcome")
    initiative_count: int = Field(..., description="Number of distinct initiatives with this outcome")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "fase": "Votação na generalidade",
                "resultado": "Aprovado",
                "vote_count": 123,
                "initiative_count": 45
            }]
        }
    }


class PartyFaseOutcome(BaseModel):
    """Phase outcome breakdown for a single party."""

    fase: str = Field(..., description="Legislative phase")
    resultado: str = Field(..., description="Vote outcome")
    count: int = Field(..., description="Number of votes with this outcome for this party")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "fase": "Votação na generalidade",
                "resultado": "Aprovado",
                "count": 25
            }]
        }
    }


class PartyInitiativeStats(BaseModel):
    """Initiative statistics for a single party."""

    party: str = Field(..., description="Parliamentary group abbreviation (e.g., 'PS', 'PSD')")
    total_initiatives: int = Field(..., description="Total number of initiatives authored by this party")
    fase_outcomes: list[PartyFaseOutcome] = Field(
        ...,
        description="Breakdown of outcomes by legislative phase for this party's initiatives"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "party": "PS",
                "total_initiatives": 234,
                "fase_outcomes": [
                    {"fase": "Votação na generalidade", "resultado": "Aprovado", "count": 45},
                    {"fase": "Votação na especialidade", "resultado": "Aprovado", "count": 32}
                ]
            }]
        }
    }


class VotesByEventType(BaseModel):
    """Vote count statistics grouped by event type."""

    fase: str = Field(..., description="Event type/phase (e.g., 'Votação na generalidade')")
    vote_count: int = Field(..., description="Number of voting sessions for this event type")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "fase": "Votação na generalidade",
                "vote_count": 456
            }]
        }
    }


class PartyVoteTypeStats(BaseModel):
    """Vote statistics grouped by party and vote type."""

    party: str = Field(..., description="Parliamentary group abbreviation")
    vote_type: str = Field(..., description="Vote type: 'A Favor', 'Contra', or 'Abstenção'")
    vote_count: int = Field(..., description="Number of votes of this type by this party")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "party": "PS",
                "vote_type": "A Favor",
                "vote_count": 789
            }]
        }
    }


class AtividadesByTipo(BaseModel):
    """Activity count statistics grouped by activity type."""

    tipo: str = Field(..., description="Activity type (VOT, MOC, PRG, OEX, SES, ITG)")
    count: int = Field(..., description="Number of activities of this type")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "tipo": "VOT",
                "count": 286
            }]
        }
    }


class AtividadesVotesByTipo(BaseModel):
    """Vote count statistics from atividades grouped by activity type."""

    tipo: str = Field(..., description="Activity type")
    vote_count: int = Field(..., description="Number of votes from this activity type")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "tipo": "VOT",
                "vote_count": 65
            }]
        }
    }


class VoteSourceBreakdown(BaseModel):
    """Vote source breakdown (iniciativas vs atividades)."""

    iniciativas: int = Field(..., description="Number of votes from iniciativas")
    atividades: int = Field(..., description="Number of votes from atividades")
    total: int = Field(..., description="Total votes across both sources")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "iniciativas": 3792,
                "atividades": 327,
                "total": 4119
            }]
        }
    }


class LegislaturaStats(BaseModel):
    """
    Comprehensive statistics for a single legislature.

    Contains 7 fundamental aggregations:
    1. Initiatives by fase outcome
    2. Initiatives by party with fase breakdowns
    3. Votes by event type
    4. Votes by party and vote type
    5. Atividades by type (NEW)
    6. Atividades votes by type (NEW)
    7. Vote source breakdown (NEW)
    """

    legislatura: str = Field(..., description="Legislature identifier (L15, L16, L17)")

    initiatives_by_fase: list[FaseOutcome] = Field(
        ...,
        description="Total initiatives and outcomes grouped by legislative phase"
    )

    initiatives_by_party: list[PartyInitiativeStats] = Field(
        ...,
        description="Initiative counts per party with phase outcome breakdowns"
    )

    votes_by_event_type: list[VotesByEventType] = Field(
        ...,
        description="Vote counts grouped by event type/phase"
    )

    votes_by_party_and_type: list[PartyVoteTypeStats] = Field(
        ...,
        description="Vote counts grouped first by party, then by vote type"
    )

    atividades_by_tipo: list[AtividadesByTipo] = Field(
        default_factory=list,
        description="Activity counts grouped by type (VOT, MOC, PRG, etc.)"
    )

    atividades_votes_by_tipo: list[AtividadesVotesByTipo] = Field(
        default_factory=list,
        description="Vote counts from atividades grouped by activity type"
    )

    vote_source_breakdown: VoteSourceBreakdown | None = Field(
        None,
        description="Breakdown of votes by source (iniciativas vs atividades)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "initiatives_by_fase": [
                    {
                        "fase": "Votação na generalidade",
                        "resultado": "Aprovado",
                        "vote_count": 123,
                        "initiative_count": 45
                    }
                ],
                "initiatives_by_party": [
                    {
                        "party": "PS",
                        "total_initiatives": 234,
                        "fase_outcomes": [
                            {"fase": "Votação na generalidade", "resultado": "Aprovado", "count": 45}
                        ]
                    }
                ],
                "votes_by_event_type": [
                    {"fase": "Votação na generalidade", "vote_count": 456}
                ],
                "votes_by_party_and_type": [
                    {"party": "PS", "vote_type": "A Favor", "vote_count": 789}
                ]
            }]
        }
    }


class StatsResponse(BaseModel):
    """
    Statistics endpoint response wrapper.

    Unlike list endpoints that use APIResponse[T], the stats endpoint
    returns a single LegislaturaStats object for the requested legislature.
    """

    data: LegislaturaStats = Field(..., description="Legislature statistics")
    meta: APIMeta = Field(..., description="API metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "data": {
                    "legislatura": "L17",
                    "initiatives_by_fase": [],
                    "initiatives_by_party": [],
                    "votes_by_event_type": [],
                    "votes_by_party_and_type": []
                },
                "meta": {
                    "version": "1.0",
                    "timestamp": "2025-12-10T12:00:00",
                    "legislature_coverage": ["L15", "L16", "L17"]
                }
            }]
        }
    }
