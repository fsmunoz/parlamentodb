"""
Data fetching module for Portuguese Parliament ETL Pipeline.

Frederico Muñoz <fsmunoz@gmail.com>

Downloads JSON data from the parlamento.pt site with some retry logic and validation.
"""

import httpx
import structlog
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

import config

logger = structlog.get_logger()

class FetchError(Exception):
    """Raised when fetch operation fails."""
    pass

# When to retry...
# 
# CHeck https://tenacity.readthedocs.io/en/latest for the tenacity API,
# it uses a @retry decorator
@retry(
    stop=stop_after_attempt(config.FETCH_RETRIES),
    wait=wait_exponential(multiplier=config.FETCH_RETRY_DELAY)
)
def fetch_legislature(legislature: str, force: bool = False) -> Path:
    """
    Fetch JSON data for a legislature.

    Downloads the JSON file from the parlamento.pt site and saves to "bronze" directory.
    Uses atomic writes (temp file + rename), for safety.

    Args:
        legislature: Legislature ID (e.g. "L17")
        force: Re-download _even_ if file exists

    Returns:
        Path to downloaded JSON file

    Raises:
        FetchError: If download fails after retries
        ValueError: If legislature is not configured
    """
    # Check if we support the legislature
    if legislature not in config.LEGISLATURES:
        raise ValueError(f"Unknown legislature: {legislature}")

    leg_config = config.LEGISLATURES[legislature]
    output_path = config.BRONZE_DIR / f"iniciativas_{legislature.lower()}.json"

    # Skip if exists and not we are not forcing
    if output_path.exists() and not force:
        logger.info("file_exists", path=str(output_path), legislature=legislature)
        return output_path

    logger.info("fetching", legislature=legislature, url=leg_config["url"])

    # Download to tmp file first (atomic write, safer)
    temp_path = output_path.with_suffix(".json.tmp")

    try:
        with httpx.Client(timeout=config.FETCH_TIMEOUT) as client:
            response = client.get(
                leg_config["url"],
                headers={"User-Agent": config.USER_AGENT},
                follow_redirects=True
            )
            response.raise_for_status()

            # Verify if the JSON is actually valid
            data = response.json()
            if not isinstance(data, list):
                raise FetchError(f"Expected list, got {type(data)}")

            # ... and write to a tmp file...
            temp_path.write_text(response.text, encoding="utf-8")

            # ...and rename.
            temp_path.rename(output_path)

            logger.info(
                "fetch_complete",
                legislature=legislature,
                records=len(data),
                size_mb=round(output_path.stat().st_size / 1_000_000, 2)
            )

            return output_path
        
    # Something happened...
    except httpx.HTTPError as e:
        logger.error("http_error", legislature=legislature, error=str(e))
        raise FetchError(f"HTTP error: {e}")
    except Exception as e:
        logger.error("fetch_error", legislature=legislature, error=str(e))
        raise FetchError(f"Error fetching {legislature}: {e}")
    finally:
        # Clean up tmp file if it exists
        if temp_path.exists():
            temp_path.unlink()


@retry(
    stop=stop_after_attempt(config.FETCH_RETRIES),
    wait=wait_exponential(multiplier=config.FETCH_RETRY_DELAY)
)
def fetch_info_base(legislature: str, force: bool = False) -> Path | None:
    """
    Fetch InformacaoBase JSON data for a legislature.

    Downloads the legislature metadata JSON (deputies, parliamentary groups, etc.)
    and saves to "bronze" directory.

    Args:
        legislature: Legislature ID (e.g., "L17")
        force: Re-download even if file exists

    Returns:
        Path to downloaded JSON file, or None if URL not configured

    Raises:
        FetchError: If download fails after retries
        ValueError: If legislature is not configured
    """
    
    if legislature not in config.LEGISLATURES:
        raise ValueError(f"Unknown legislature: {legislature}")

    leg_config = config.LEGISLATURES[legislature]
    info_base_url = leg_config.get("info_base_url", "")

    # Skip if URL not configured in the config file (we are adding legislatures as we go)
    if not info_base_url:
        logger.warning("info_base_url_not_configured", legislature=legislature)
        return None

    output_path = config.BRONZE_DIR / f"info_base_{legislature.lower()}.json"

    # Skip if exists and we are not forcing
    if output_path.exists() and not force:
        logger.info("file_exists", path=str(output_path), legislature=legislature)
        return output_path

    logger.info("fetching_info_base", legislature=legislature, url=info_base_url)

    # Download to temp file first (atomic write)
    temp_path = output_path.with_suffix(".json.tmp")

    try:
        with httpx.Client(timeout=config.FETCH_TIMEOUT) as client:
            response = client.get(
                info_base_url,
                headers={"User-Agent": config.USER_AGENT},
                follow_redirects=True
            )
            response.raise_for_status()

            # Verify JSON is valid, etc - same as above
            data = response.json()
            if not isinstance(data, dict):
                raise FetchError(f"Expected dict, got {type(data)}")

            # ... but here we check for the expected keys
            expected_keys = ["DetalheLegislatura", "Deputados", "GruposParlamentares"]
            missing_keys = [k for k in expected_keys if k not in data]
            if missing_keys:
                logger.warning("missing_keys", keys=missing_keys)

            # Write to tmp file
            temp_path.write_text(response.text, encoding="utf-8")

            # Atomic rename
            temp_path.rename(output_path)

            logger.info(
                "fetch_info_base_complete",
                legislature=legislature,
                deputados=len(data.get("Deputados", [])),
                size_mb=round(output_path.stat().st_size / 1_000_000, 2)
            )

            return output_path
    # Exceptions
    except httpx.HTTPError as e:
        logger.error("http_error", legislature=legislature, error=str(e))
        raise FetchError(f"HTTP error: {e}")
    except Exception as e:
        logger.error("fetch_error", legislature=legislature, error=str(e))
        raise FetchError(f"Error fetching info_base for {legislature}: {e}")
    finally:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()


def fetch_all(
    legislatures: list[str] | None = None,
    include_info_base: bool = True,
    force: bool = False
) -> dict[str, dict[str, Path]]:
    """
    Fetch multiple legislatures and their metadata.

    Args:
        legislatures: List of legislature IDs, or None for all configured
        include_info_base: Also fetch InformacaoBase metadata
        force: Re-download files even if they exist

    Returns:
        Dict mapping legislature ID to {
            "iniciativas": Path,
            "info_base": Path | None
        }
    """
    if legislatures is None:
        legislatures = list(config.LEGISLATURES.keys())

    results = {}
    for leg in legislatures:
        leg_results = {}

        # Fetch iniciativas
        try:
            leg_results["iniciativas"] = fetch_legislature(leg, force=force)
        except FetchError as e:
            logger.error("fetch_iniciativas_failed", legislature=leg, error=str(e))

        # Fetch info_base
        if include_info_base:
            try:
                leg_results["info_base"] = fetch_info_base(leg, force=force)
            except FetchError as e:
                logger.error("fetch_info_base_failed", legislature=leg, error=str(e))

        if leg_results:
            results[leg] = leg_results

    return results
