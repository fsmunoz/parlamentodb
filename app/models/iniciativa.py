"""
Pydantic models for Iniciativa (legislative initiative) responses.

Frederico Muñoz <fsmunoz@gmail.com>

In this API version the iniciative gets a more prominent position: previously we derived
most things and flattened it into votacoes.
"""

from datetime import date
from typing import Any
from pydantic import BaseModel, Field


class IniciativaListItem(BaseModel):
    """Simplified initiative record for list responses."""

    ini_id: str = Field(..., description="Unique initiative ID (use this to fetch details)")
    ini_nr: str = Field(..., description="Initiative number (not unique - can have duplicates)")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    ini_tipo: str | None = Field(None, description="Initiative type")
    ini_desc_tipo: str | None = Field(None, description="Initiative type description")
    ini_titulo: str | None = Field(None, description="Initiative title")
    autor_gp: list[str] | None = Field(
        None,
        description="Parliamentary group authors (e.g., ['PS'], ['PCP', 'BE'])"
    )
    # REMOVED: data_inicio_leg - misleading field (was legislature start, not event date)
    # Use data_desde/data_ate filters to query actual event dates
    # Full date available in detail view: GET /iniciativas/{ini_id}

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "ini_id": "315199",
                "ini_nr": "99",
                "legislatura": "L17",
                "ini_tipo": "R",
                "ini_desc_tipo": "Projeto de Resolução",
                "ini_titulo": "Recomenda o reforço da Língua Gestual Portuguesa (LGP) nas escolas"
            }]
        }
    }


class Iniciativa(BaseModel):
    """
    Complete initiative record with all fields.

    Note: Some nested structures (ini_eventos, ini_anexos, etc.) are
    preserved as generic dicts to maintain flexibility.
    """

    ini_nr: str = Field(..., description="Initiative number")
    legislatura: str = Field(..., description="Legislature (L15, L16, L17)")
    ini_id: str | None = Field(None, description="Unique initiative ID")
    ini_leg: str | None = Field(None, description="Legislature session")
    ini_sel: str | None = Field(None, description="Legislative session")
    ini_tipo: str | None = Field(None, description="Initiative type code")
    ini_desc_tipo: str | None = Field(None, description="Initiative type description")
    ini_titulo: str | None = Field(None, description="Initiative title")
    ini_texto_subst: str | None = Field(None, description="Substitute text")
    ini_link_texto: str | None = Field(None, description="Link to full text")
    ini_epigrafe: Any | None = Field(None, description="Epigraph/summary")
    ini_obs: str | None = Field(None, description="Observations")

    data_inicio_leg: date | None = Field(None, description="Initiative start date")
    data_fim_leg: Any | None = Field(None, description="Initiative end date")

    # Author information
    ini_autor_outros: Any | None = Field(None, description="Other authors")
    ini_autor_deputados: list[Any] | None = Field(None, description="Deputy authors")
    ini_autor_grupos_parlamentares: list[Any] | None = Field(None, description="Parliamentary group authors")

    # Nested structures (preserved as-is from Parquet)
    ini_anexos: list[Any] | None = Field(None, description="Attachments")
    ini_eventos: list[Any] | None = Field(None, description="Legislative events and phases")

    # Related initiatives and petitions
    iniciativas_origem: list[Any] | None = Field(None, description="Origin initiatives")
    iniciativas_originadas: list[Any] | None = Field(None, description="Derived initiatives")
    iniciativas_europeias: Any | None = Field(None, description="European initiatives")
    peticoes: list[Any] | None = Field(None, description="Related petitions")
    propostas_alteracao: Any | None = Field(None, description="Amendment proposals")

    links: Any | None = Field(None, description="Related links")
    etl_timestamp: Any | None = Field(None, description="ETL processing timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "ini_nr": "99",
                "legislatura": "L17",
                "ini_id": "315199",
                "ini_leg": "XVII",
                "ini_sel": "I",
                "ini_tipo": "R",
                "ini_desc_tipo": "Projeto de Resolução",
                "ini_titulo": "Recomenda o reforço da Língua Gestual Portuguesa (LGP) nas escolas",
                "ini_texto_subst": None,
                "ini_link_texto": "https://...",
                "data_inicio_leg": "2025-06-03",
                "data_fim_leg": None
            }]
        }
    }
