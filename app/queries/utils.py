"""
Utilities for building DuckDB queries.

Frederico Muñoz <fsmunoz@gmail.com>

This makes the router code simpler and reduces duplication.
"""

from typing import Any, TypeVar

import duckdb
from fastapi import HTTPException
from pydantic import BaseModel

from app.config import settings
from app.models.common import APIResponse, APIMeta, PaginationMeta

M = TypeVar("M", bound=BaseModel)


class QueryBuilder:
    """Helper for building DuckDB WHERE clauses with parameterized queries."""

    def __init__(self):
        self.clauses: list[str] = []
        self.params: dict[str, Any] = {}

    def add_equals(self, field: str, value: Any, param_name: str | None = None):
        """Add equality condition (field = value)."""
        if value is not None:
            param_name = param_name or field
            self.clauses.append(f"{field} = ${param_name}")
            self.params[param_name] = value
        return self

    def add_gte(self, field: str, value: Any, param_name: str | None = None):
        """Add greater-than-or-equal condition."""
        if value is not None:
            param_name = param_name or field
            self.clauses.append(f"{field} >= ${param_name}")
            self.params[param_name] = value
        return self

    def add_lte(self, field: str, value: Any, param_name: str | None = None):
        """Add less-than-or-equal condition."""
        if value is not None:
            param_name = param_name or field
            self.clauses.append(f"{field} <= ${param_name}")
            self.params[param_name] = value
        return self

    def add_in(self, field: str, values: list | None, param_name: str | None = None):
        """Add membership condition (field is one of values)."""
        if values:
            param_name = param_name or field
            self.clauses.append(f"{field} = ANY(${param_name})")
            self.params[param_name] = values
        return self

    def add_list_contains(self, field: str, value: Any, param_name: str | None = None):
        """Add list_contains condition for DuckDB arrays."""
        if value is not None:
            param_name = param_name or field
            self.clauses.append(f"list_contains({field}, ${param_name})")
            self.params[param_name] = value
        return self

    def add_text_search(self, field: str, search_text: str, param_name: str | None = None):
        """Add case-insensitive text search (ILIKE) for substring matching.

        Args:
            field: Field name to search in
            search_text: Search term (will be wrapped with % wildcards)
            param_name: Optional parameter name (defaults to field_search)

        Returns:
            self for method chaining
        """
        if search_text is not None and search_text.strip():
            param_name = param_name or f"{field}_search"
            # Wrap with wildcards for substring matching
            search_pattern = f"%{search_text.strip()}%"
            self.clauses.append(f"{field} ILIKE ${param_name}")
            self.params[param_name] = search_pattern
        return self

    def add_custom(self, clause: str, params: dict[str, Any] | None = None):
        """Add custom SQL clause with optional parameters."""
        self.clauses.append(clause)
        if params:
            self.params.update(params)
        return self

    def build_where(self) -> str:
        """Build the WHERE clause string."""
        return "WHERE " + " AND ".join(self.clauses) if self.clauses else ""

    def get_params(self) -> dict[str, Any]:
        """Get the parameters dict."""
        return self.params


def fetch_models(db: duckdb.DuckDBPyConnection, sql: str, params: dict[str, Any], model: type[M]) -> list[M]:
    """Run a query and build one model per row, matching columns to fields by name."""
    cursor = db.execute(sql, params)
    columns = [d[0] for d in cursor.description]
    return [model(**dict(zip(columns, row))) for row in cursor.fetchall()]


def paginated_list(
    db: duckdb.DuckDBPyConnection, table: str, qb: QueryBuilder, model: type[M],
    order_by: str, limit: int, offset: int
) -> APIResponse[M]:
    """SELECT the model's fields from a flat table, filtered by qb, as a paginated APIResponse."""
    where_sql, params = qb.build_where(), qb.get_params()
    total = db.execute(f"SELECT COUNT(*) FROM {table} {where_sql}", params).fetchone()[0]
    data = fetch_models(
        db,
        f"SELECT {', '.join(model.model_fields)} FROM {table} {where_sql} "
        f"ORDER BY {order_by} LIMIT $limit OFFSET $offset",
        {**params, "limit": limit, "offset": offset},
        model,
    )
    return APIResponse(
        data=data,
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
        meta=APIMeta(version=settings.API_VERSION),
    )


def get_one(db: duckdb.DuckDBPyConnection, table: str, key: str, value: str, model: type[M]) -> M:
    """Fetch a single row by key from a flat table, or 404."""
    rows = fetch_models(
        db, f"SELECT {', '.join(model.model_fields)} FROM {table} WHERE {key} = $value", {"value": value}, model
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"{table} {value} not found")
    return rows[0]
