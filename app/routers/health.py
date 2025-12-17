"""
Health check and metadata endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Health check with minimal additional metadata
"""

from fastapi import APIRouter, Depends
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.common import HealthResponse, APIMeta

router = APIRouter(tags=["health"])
logger = structlog.get_logger()


@router.get("/health", response_model=HealthResponse)
def health_check(db: duckdb.DuckDBPyConnection = Depends(get_db)):
    """
    Enhanced health check endpoint with comprehensive diagnostics.

    Returns service status, data availability, and configuration information.

    **Status Levels:**
    - `healthy`: All systems operational
    - `degraded`: Some optional datasets unavailable but core functionality working
    - `unhealthy`: Critical failures preventing normal operation

    **Data Stats Include:**
    - Record counts for all available datasets (iniciativas, votacoes, deputados, etc.)
    - Available legislatures
    - Configuration details (memory limit, threads, query timeout)
    - Database connectivity status
    """
    stats = {}
    errors = []
    warnings = []

    try:
        # Test basic database connectivity
        db.execute("SELECT 1").fetchone()
        stats["database_connection"] = "ok"

        # Configuration information (useful for debugging)
        # FIXME: this could be too much actually.
        
        stats["config"] = {
            "memory_limit": settings.DUCKDB_MEMORY_LIMIT,
            "threads": settings.DUCKDB_THREADS,
            "query_timeout": settings.DUCKDB_QUERY_TIMEOUT,
            "data_dir": settings.DATA_DIR
        }

        # Check core datasets (required for API to function)
        try:
            result = db.execute("SELECT COUNT(*) FROM iniciativas").fetchone()
            stats["total_iniciativas"] = result[0] if result else 0
        except Exception as e:
            errors.append(f"iniciativas table unavailable: {type(e).__name__}")
            stats["total_iniciativas"] = None

        try:
            result = db.execute("SELECT COUNT(*) FROM votacoes").fetchone()
            stats["total_votacoes"] = result[0] if result else 0
        except Exception as e:
            errors.append(f"votacoes table unavailable: {type(e).__name__}")
            stats["total_votacoes"] = None

        # Check optional datasets (nice to have but not critical)
        try:
            result = db.execute("SELECT COUNT(*) FROM deputados").fetchone()
            stats["total_deputados"] = result[0] if result else 0
        except Exception:
            warnings.append("deputados table unavailable")
            stats["total_deputados"] = None

        try:
            result = db.execute("SELECT COUNT(*) FROM partidos").fetchone()
            stats["total_partidos"] = result[0] if result else 0
        except Exception:
            warnings.append("partidos table unavailable")
            stats["total_partidos"] = None

        try:
            result = db.execute("SELECT COUNT(*) FROM circulos").fetchone()
            stats["total_circulos"] = result[0] if result else 0
        except Exception:
            warnings.append("circulos table unavailable")
            stats["total_circulos"] = None

        try:
            result = db.execute("SELECT COUNT(*) FROM info_base").fetchone()
            stats["total_info_base"] = result[0] if result else 0
        except Exception:
            warnings.append("info_base table unavailable")
            stats["total_info_base"] = None

        # Get available legislatures from iniciativas
        try:
            result = db.execute(
                "SELECT DISTINCT legislatura FROM iniciativas ORDER BY legislatura"
            ).fetchall()
            stats["legislatures"] = [row[0] for row in result] if result else []
        except Exception as e:
            errors.append(f"Could not determine legislatures: {type(e).__name__}")
            stats["legislatures"] = []

        # Determine overall health status
        # FIXME: I need to revisit this since it might be the wrong approach and not really help
        
        if errors:
            # Critical errors - core functionality affected
            status = "unhealthy"
            stats["errors"] = errors
            logger.error("health_check_unhealthy", errors=errors, warnings=warnings)
        elif warnings:
            # Non-critical issues - optional features unavailable
            status = "degraded"
            stats["warnings"] = warnings
            logger.warning("health_check_degraded", warnings=warnings)
        else:
            # All systems operational
            status = "healthy"

        return HealthResponse(
            status=status,
            version=settings.API_VERSION,
            data_stats=stats
        )

    except Exception as e:
        # Catastrophic failure - database connection failed
        logger.error("health_check_critical_failure", error=str(e), error_type=type(e).__name__)
        return HealthResponse(
            status="unhealthy",
            version=settings.API_VERSION,
            data_stats={
                "database_connection": "failed",
                "error": f"Critical failure: {type(e).__name__}",
                "details": "Database connection failed or dependency injection error"
            }
        )


# TODO: remove hardcoded coverage    
@router.get("/api/v1/meta", response_model=APIMeta)
def api_metadata():
    """
    API metadata endpoint.

    Returns information about API version and available data coverage.
    """
    return APIMeta(
        version=settings.API_VERSION,
        legislature_coverage=["L13","L14","L15", "L16", "L17"]
    )
