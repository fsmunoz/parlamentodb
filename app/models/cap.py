"""
Pydantic models for CAP (Comparative Agendas Project) classification endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

CAP topic codes classify legislative iniciativas into 22 major policy areas
(e.g., Saúde, Habitação, Imigração) using the poltextlab/xlm-roberta-large-pooled-cap-v3
multilingual model.  Classification is produced by the votoaberto-cap project and
committed as a CSV into data/cap_source/; the ETL pipeline converts it to Parquet.

Only proposals for which a document text could be extracted are classified; the rest
simply have no entry in the cap view (the endpoint LEFT-joins against iniciativas).
"""

from pydantic import BaseModel, Field


# Valid CAP major-topic codes (Comparative Agendas Project codebook)
VALID_CAP_CODES = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 999}


class CapListItem(BaseModel):
    """A single CAP-classified initiative, returned in list responses."""

    # CAP classification fields (from cap view)
    ini_id: str = Field(..., description="Unique initiative ID (join key with iniciativas)")
    legislatura: str = Field(..., description="Legislature (e.g., L17)")
    cap: int = Field(..., description="CAP major-topic code (e.g., 3 = Saúde, 9 = Imigração)")
    cap_label: str = Field(..., description="Portuguese label for the CAP code")
    model_version: str = Field(..., description="Model used for classification")

    # Joined iniciativa context (denormalised for convenience)
    ini_nr: str | None = Field(None, description="Initiative number within its type/legislature (not unique)")
    ini_tipo: str | None = Field(None, description="Initiative type code (e.g., J, R, PPL)")
    ini_desc_tipo: str | None = Field(None, description="Initiative type description")
    ini_titulo: str | None = Field(None, description="Initiative title")


class CapDetail(BaseModel):
    """Full CAP classification record for a single initiative."""

    # CAP classification fields
    ini_id: str = Field(..., description="Unique initiative ID")
    legislatura: str = Field(..., description="Legislature (e.g., L17)")
    cap: int = Field(..., description="CAP major-topic code")
    cap_label: str = Field(..., description="Portuguese label for the CAP code")
    model_version: str = Field(..., description="Model used for classification")

    # Joined iniciativa context
    ini_nr: str | None = Field(None, description="Initiative number")
    ini_tipo: str | None = Field(None, description="Initiative type code")
    ini_desc_tipo: str | None = Field(None, description="Initiative type description")
    ini_titulo: str | None = Field(None, description="Initiative title")
