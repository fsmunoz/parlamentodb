"""
Pydantic models for Evento (legislative event) responses.

Frederico Muñoz <fsmunoz@gmail.com>

Each Iniciativa has many Eventos, and almost everything occurs in them - namely, voting.

It's also important to be able to determine when an iniciative "arrived", since that is
obtained from an event of type Entrada

"""

from datetime import date
from typing import Any
from pydantic import BaseModel, Field


class EventoListItem(BaseModel):
    """Legislative event record for list responses."""

    # Initiative context
    ini_id: str = Field(..., description="Initiative ID")
    ini_nr: str = Field(..., description="Initiative number")
    legislatura: str = Field(..., description="Legislature")
    ini_titulo: str | None = Field(None, description="Initiative title")
    ini_tipo: str | None = Field(None, description="Initiative type")

    # Event fields
    evt_id: str | None = Field(None, description="Event ID")
    oev_id: str | None = Field(None, description="Original event ID")
    fase: str | None = Field(None, description="Event phase/type (e.g., 'Entrada', 'Votação na generalidade')")
    codigo_fase: str | None = Field(None, description="Phase code")
    data_fase: date | None = Field(None, description="Event date")
    obs_fase: str | None = Field(None, description="Event observations")

    # Nested structures preserved as-is
    votacao: list[Any] | None = Field(None, description="Voting data (array)")
    comissao: Any | None = Field(None, description="Committee information")
    anexos_fase: list[Any] | None = Field(None, description="Phase attachments")
    links: Any | None = Field(None, description="Related links")

    # Related records
    act_id: str | None = Field(None, description="Activity ID (links to atividades dataset)")
    atividades_conjuntas: list[Any] | None = Field(None, description="Joint activities")
    iniciativas_conjuntas: list[Any] | None = Field(None, description="Joint initiatives")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "ini_id": "315199",
                "ini_nr": "99",
                "legislatura": "L17",
                "ini_titulo": "Recomenda o reforço da Língua Gestual Portuguesa (LGP) nas escolas",
                "ini_tipo": "R",
                "evt_id": "1",
                "oev_id": "1234567",
                "fase": "Entrada",
                "codigo_fase": "10",
                "data_fase": "2025-06-27",
                "obs_fase": None,
                "votacao": [],
                "comissao": None,
                "anexos_fase": None,
                "links": None,
                "act_id": None,
                "atividades_conjuntas": None,
                "iniciativas_conjuntas": None
            }]
        }
    }
