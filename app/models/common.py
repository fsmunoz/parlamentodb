"""Common Pydantic models for API responses.

Frederico Muñoz <fsmunoz@gmail.com>

Major aspects of the API are defined here: pagination, base model for API responses.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

## We use offset pagination instead of cursor. No strong reason why, except that I can make parallel
## request more easily with offset pagination.

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    limit: int = Field(..., description="Records per page")
    offset: int = Field(..., description="Number of records skipped")
    total: int = Field(..., description="Total number of records")


class APIMeta(BaseModel):
    """API response metadata."""
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    legislature_coverage: list[str] = Field(
        default=["L15", "L16", "L17"],
        description="Available legislatures"
    )


# Generic type for data payload
T = TypeVar('T')


# Used for endpoints that return more than one element
class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.

    All list endpoints return responses in this format.
    """
    data: list[T] = Field(..., description="Response data")
    pagination: PaginationMeta = Field(..., description="Pagination information")
    meta: APIMeta = Field(..., description="API metadata")


class ErrorResponse(BaseModel):
    """Error response format."""
    detail: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Error code for client handling")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.now)
    data_stats: dict[str, Any] | None = Field(None, description="Data availability stats")
