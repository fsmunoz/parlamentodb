"""
FastAPI application for Portuguese Parliament Data API.

Frederico Muñoz <fsmunoz@gmail.com>

Main FastAPI application entry point with router registration and middleware.
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import structlog

from app.config import settings
from app.routers import health, iniciativas, votacoes, legislaturas, deputados, circulos, partidos, stats, atividades

logger = structlog.get_logger()

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# NOTE: CORS and request logging are handled by infrastructure (Cloudflare/nginx) in production.
# For local development, you can add CORS middleware here if needed.
# See DEPLOYMENT.md for nginx/Cloudflare configuration.


# Register routers - updated as we add more endpoints
app.include_router(health.router)
app.include_router(iniciativas.router)
app.include_router(votacoes.router)
app.include_router(legislaturas.router)
app.include_router(deputados.router)
app.include_router(circulos.router)
app.include_router(partidos.router)
app.include_router(atividades.router)
app.include_router(stats.router)


@app.on_event("startup")
def validate_data_files():
    """
    Validate that required Parquet data files exist at startup.

    Provides helpful error messages if data files are missing, preventing
    cryptic errors later when endpoints try to query non-existent files.
    """
    data_dir = Path(settings.DATA_DIR)

    if not data_dir.exists():
        error_msg = f"Data directory not found: {data_dir.absolute()}"
        logger.error("startup_validation_error", error=error_msg)
        raise RuntimeError(
            f"{error_msg}\n"
            f"Please create the directory and run the ETL pipeline:\n"
            f"  make etl-fetch && make etl-transform"
        )

    # Required files (iniciativas and votacoes are mandatory)
    required_patterns = [
        "iniciativas_*.parquet",
        "votacoes_*.parquet"
    ]

    missing_files = []
    for pattern in required_patterns:
        files = list(data_dir.glob(pattern))
        if not files:
            missing_files.append(pattern)

    if missing_files:
        error_msg = f"Required Parquet files not found: {', '.join(missing_files)}"
        logger.error("startup_validation_error", missing=missing_files, data_dir=str(data_dir))
        raise RuntimeError(
            f"{error_msg}\n"
            f"Data directory: {data_dir.absolute()}\n"
            f"Please run the ETL pipeline to generate data files:\n"
            f"  make etl-fetch && make etl-transform"
        )

    # Log successful validation
    all_files = list(data_dir.glob("*.parquet"))
    logger.info(
        "startup_validation_success",
        data_dir=str(data_dir),
        parquet_files_count=len(all_files),
        files=[f.name for f in all_files]
    )


# Backward compatibility redirects for API restructuring
# Old /votacoes -> New /iniciativas/votacoes
# We might DROP this soon-ish...

@app.get("/api/v1/votacoes/", include_in_schema=False)
@app.get("/api/v1/votacoes/{vot_id}", include_in_schema=False)
async def redirect_old_votacoes(request: Request):
    """
    Redirect old /votacoes URLs to new /iniciativas/votacoes for backward compatibility.

    HTTP 301 Permanent Redirect signals to clients that the resource has moved permanently.
    Query parameters are preserved in the redirect.
    """
    # Replace the old path with the new path
    new_path = request.url.path.replace("/api/v1/votacoes", "/api/v1/iniciativas/votacoes")
    # Preserve query parameters
    new_url = str(request.url).replace(request.url.path, new_path)
    return RedirectResponse(url=new_url, status_code=301)


# Redirect to /docs ... could be /redocs as well, but /docs looks
# better for a dev
@app.get("/", include_in_schema=False)
def root():
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
