"""Pydantic models for party-related endpoint responses.

Frederico Muñoz <fsmunoz@gmail.com>

Response models for party-specific aggregations and statistics.
"""

from pydantic import BaseModel, Field
from app.models.common import APIMeta


class PartyVoteCount(BaseModel):
    """Aggregated vote counts for a single party in a specific fase."""

    party: str = Field(..., description="Parliamentary group abbreviation")
    a_favor: int = Field(..., description="Total votes in favor")
    contra: int = Field(..., description="Total votes against")
    abstencao: int = Field(..., description="Total abstentions")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "party": "CHEGA",
                "a_favor": 1323,
                "contra": 332,
                "abstencao": 355
            }]
        }
    }


class FaseVoteSupport(BaseModel):
    """Vote support breakdown for a single legislative phase."""

    fase: str = Field(..., description="Legislative phase (e.g., 'Votação Final Global')")
    vote_details: list[PartyVoteCount] = Field(
        ...,
        description="Aggregated vote counts by party within this fase"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "fase": "Votação Final Global",
                "vote_details": [
                    {"party": "CHEGA", "a_favor": 1323, "contra": 332, "abstencao": 355},
                    {"party": "PS", "a_favor": 33, "contra": 0, "abstencao": 12}
                ]
            }]
        }
    }


class PartyVoteSupportData(BaseModel):
    """Data structure for party vote support response."""

    party: str = Field(..., description="Focus party (whose initiatives are being analyzed)")
    legislatura: str = Field(..., description="Legislature identifier (L15, L16, L17)")
    vote_support_by_fase: list[FaseVoteSupport] = Field(
        ...,
        description="Vote support breakdown by legislative phase"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "party": "PCP",
                "legislatura": "L17",
                "vote_support_by_fase": [
                    {
                        "fase": "Votação Final Global",
                        "vote_details": [
                            {"party": "CHEGA", "a_favor": 1323, "contra": 332, "abstencao": 355},
                            {"party": "PS", "a_favor": 33, "contra": 0, "abstencao": 12}
                        ]
                    }
                ]
            }]
        }
    }


class PartyVoteSupportResponse(BaseModel):
    """Response showing aggregated vote counts on initiatives from a specific party."""

    data: PartyVoteSupportData = Field(..., description="Vote support data")
    meta: APIMeta = Field(..., description="API metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "data": {
                    "party": "PCP",
                    "legislatura": "L17",
                    "vote_support_by_fase": []
                },
                "meta": {
                    "version": "1.0",
                    "timestamp": "2025-12-10T12:00:00",
                    "legislature_coverage": ["L15", "L16", "L17"]
                }
            }]
        }
    }
