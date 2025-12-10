"""
Pydantic models for Circulo (electoral circle) responses.
"""

from pydantic import BaseModel, Field


class Circulo(BaseModel):
    """Electoral circle record."""

    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    cp_id: float = Field(..., description="Unique circle ID")
    cp_des: str = Field(..., description="Circle name/description")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "cp_id": 11,
                "cp_des": "Lisboa"
            }]
        }
    }


class CirculoListItem(BaseModel):
    """Simplified circle record for list responses."""

    legislatura: str
    cp_id: float
    cp_des: str

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "legislatura": "L17",
                "cp_id": 11,
                "cp_des": "Lisboa"
            }]
        }
    }
