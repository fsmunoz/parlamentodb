"""
Data fetching module for Portuguese Parliament ETL Pipeline.

Frederico Muñoz <fsmunoz@gmail.com>

Downloads JSON data from the parlamento.pt site with some retry logic and validation.
"""

import json

import httpx
import structlog
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

import config

logger = structlog.get_logger()

class FetchError(Exception):
    """Raised when fetch operation fails."""
    pass


def _vote_ids(ini: dict) -> set:
    """IDs of the plenary and committee votes in one iniciativa."""
    ids = set()
    for ev in ini.get("IniEventos") or []:
        ids |= {v.get("id") for v in ev.get("Votacao") or []}
        for com in ev.get("Comissao") or []:
            ids |= {v.get("id") for v in com.get("Votacao") or []}
    return ids


def merge_iniciativas(old: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """Merge a new upstream iniciativas file onto the previous bronze, by IniId.

    
    Upstream wins for every record it has: records missing upstream
    are carried forward. Since (at least) Nov 2026 the parlamento.pt
    export intermittently drops whole sessions (IniSel) while the
    records it does include stay complete, so a plain overwrite would
    delete history. If a record that is present lost votes, that is a
    new failure mode: refuse the file instead of trying to be smart
    about it.

    Returns (merged records, number carried forward).

    """
    new_ids = {x["IniId"] for x in new}
    carried = [x for x in old if x["IniId"] not in new_ids]
    old_votes = set().union(*map(_vote_ids, old))
    new_votes = set().union(*map(_vote_ids, new + carried))
    lost = old_votes - new_votes
    if lost:
        raise FetchError(f"Upstream file would lose {len(lost)} votes, e.g. {sorted(map(str, lost))[:5]}")
    return new + carried, len(carried)


def _section_sizes(data: dict) -> dict[str, int]:
    """Non-empty records per list in a dict-shaped file, one level deep
    (e.g. Debates, AtividadesGerais.Atividades). A record whose fields are
    all null counts as empty: the broken export leaves one such placeholder."""
    def count(xs: list) -> int:
        return sum(1 for x in xs if not isinstance(x, dict) or any(v is not None for v in x.values()))
    sizes = {}
    for k, v in data.items():
        if isinstance(v, list):
            sizes[k] = count(v)
        elif isinstance(v, dict):
            sizes |= {f"{k}.{k2}": count(v2) for k2, v2 in v.items() if isinstance(v2, list)}
    return sizes


def check_shrink(path: Path, new: dict) -> None:
    """
    Refuse an upstream file whose record lists shrank by more than 10% against
    the current bronze (Nov 2026: L14 Debates went 326 -> 1 empty record).
    Small drops pass, so a legitimately removed record doesn't block updates.
    """
    if not path.exists():
        return
    old = _section_sizes(json.loads(path.read_text(encoding="utf-8-sig")))
    now = _section_sizes(new)
    shrunk = {k: f"{n} -> {now.get(k, 0)}" for k, n in old.items() if now.get(k, 0) < 0.9 * n}
    if shrunk:
        raise FetchError(f"Upstream file shrank, keeping {path.name}: {shrunk}")

# When to retry...
# 
# CHeck https://tenacity.readthedocs.io/en/latest for the tenacity API,
# it uses a @retry decorator
@retry(
    stop=stop_after_attempt(config.FETCH_RETRIES),
    wait=wait_exponential(multiplier=config.FETCH_RETRY_DELAY),
    reraise=True,  # raise the FetchError itself, not tenacity's RetryError
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

            # Keep records the export dropped (see merge_iniciativas)
            if output_path.exists():
                old = json.loads(output_path.read_text(encoding="utf-8-sig"))
                upstream = len(data)
                data, carried = merge_iniciativas(old, data)
                logger.info("merged", legislature=legislature, upstream=upstream,
                            previous=len(old), carried_forward=carried)

            # ... and write to a tmp file...
            temp_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

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
    wait=wait_exponential(multiplier=config.FETCH_RETRY_DELAY),
    reraise=True,  # raise the FetchError itself, not tenacity's RetryError
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
            check_shrink(output_path, data)
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


@retry(
    stop=stop_after_attempt(config.FETCH_RETRIES),
    wait=wait_exponential(multiplier=config.FETCH_RETRY_DELAY),
    reraise=True,  # raise the FetchError itself, not tenacity's RetryError
)
def fetch_atividades(legislature: str, force: bool = False) -> Path | None:
    """
    Fetch Atividades JSON data for a legislature.

    Downloads parliamentary activities (condemnation votes, motions, etc.)
    and saves to "bronze" directory. Structure: {"AtividadesGerais": {"Atividades": [...]}}.

    The structure of these votes is different from the one in Iniciativas (and doesn't have a unique ID).
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
    atividades_url = leg_config.get("atividades_url", "")

    # Skip if URL not configured
    if not atividades_url:
        logger.warning("atividades_url_not_configured", legislature=legislature)
        return None

    output_path = config.BRONZE_DIR / f"atividades_{legislature.lower()}.json"

    # Skip if exists and not forcing
    if output_path.exists() and not force:
        logger.info("file_exists", path=str(output_path), legislature=legislature)
        return output_path

    logger.info("fetching_atividades", legislature=legislature, url=atividades_url)

    # Download to temp file first (atomic write)
    temp_path = output_path.with_suffix(".json.tmp")

    try:
        with httpx.Client(timeout=config.FETCH_TIMEOUT) as client:
            response = client.get(
                atividades_url,
                headers={"User-Agent": config.USER_AGENT},
                follow_redirects=True
            )
            response.raise_for_status()

            # Verify JSON structure
            data = response.json()
            if not isinstance(data, dict):
                raise FetchError(f"Expected dict, got {type(data)}")

            # Validate expected structure
            if "AtividadesGerais" not in data:
                logger.warning("missing_atividades_gerais", legislature=legislature)
            elif "Atividades" not in data.get("AtividadesGerais", {}):
                logger.warning("missing_atividades_array", legislature=legislature)

            # Write to temp file
            check_shrink(output_path, data)
            temp_path.write_text(response.text, encoding="utf-8")

            # Atomic rename
            temp_path.rename(output_path)

            atividades_count = len(data.get("AtividadesGerais", {}).get("Atividades", []))
            logger.info(
                "fetch_atividades_complete",
                legislature=legislature,
                atividades=atividades_count,
                size_mb=round(output_path.stat().st_size / 1_000_000, 2)
            )

            return output_path

    except httpx.HTTPError as e:
        logger.error("http_error", legislature=legislature, error=str(e))
        raise FetchError(f"HTTP error: {e}")
    except Exception as e:
        logger.error("fetch_error", legislature=legislature, error=str(e))
        raise FetchError(f"Error fetching atividades for {legislature}: {e}")
    finally:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()


@retry(
    stop=stop_after_attempt(config.FETCH_RETRIES),
    wait=wait_exponential(multiplier=config.FETCH_RETRY_DELAY),
    reraise=True,  # raise the FetchError itself, not tenacity's RetryError
)
def fetch_oe(ano: int, force: bool = False) -> Path:
    """
    Fetch the Orçamento do Estado propostas de alteração JSON for one budget year
    ({"PropostaDeAlteracao": [...]}) into bronze/oe_{ano}.json, with an atomic write.
    """
    output_path = config.BRONZE_DIR / f"oe_{ano}.json"
    if output_path.exists() and not force:
        logger.info("file_exists", path=str(output_path), ano=ano)
        return output_path

    temp_path = output_path.with_suffix(".json.tmp")
    try:
        with httpx.Client(timeout=config.FETCH_TIMEOUT) as client:
            response = client.get(
                config.OE[ano]["url"], headers={"User-Agent": config.USER_AGENT}, follow_redirects=True
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "PropostaDeAlteracao" not in data:
                raise FetchError(f"Expected {{'PropostaDeAlteracao': [...]}}, got {type(data)}")
            check_shrink(output_path, data)
            temp_path.write_text(response.text, encoding="utf-8")
            temp_path.rename(output_path)
            logger.info("fetch_oe_complete", ano=ano, propostas=len(data["PropostaDeAlteracao"]))
            return output_path
    except Exception as e:
        logger.error("fetch_oe_error", ano=ano, error=str(e))
        raise FetchError(f"Error fetching OE {ano}: {e}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


def fetch_all(
    legislatures: list[str] | None = None,
    include_info_base: bool = True,
    include_atividades: bool = True,
    include_oe: bool = True,
    force: bool = False
) -> dict[str, dict[str, Path]]:
    """
    Fetch multiple legislatures and their metadata.

    Args:
        legislatures: List of legislature IDs, or None for all configured
        include_info_base: Also fetch InformacaoBase metadata
        include_atividades: Also fetch Atividades data
        force: Re-download files even if they exist

    Returns:
        Dict mapping legislature ID to {
            "iniciativas": Path,
            "info_base": Path | None,
            "atividades": Path | None
        }
    """
    if legislatures is None:
        legislatures = list(config.LEGISLATURES.keys())

    results = {}
    failed = []

    def fail(event: str, **kw) -> None:
        failed.append(f"{event} {kw}")
        logger.error(event, **kw)

    for leg in legislatures:
        leg_results = {}

        # Fetch iniciativas
        try:
            leg_results["iniciativas"] = fetch_legislature(leg, force=force)
        except FetchError as e:
            fail("fetch_iniciativas_failed", legislature=leg, error=str(e))

        # Fetch info_base
        if include_info_base:
            try:
                leg_results["info_base"] = fetch_info_base(leg, force=force)
            except FetchError as e:
                fail("fetch_info_base_failed", legislature=leg, error=str(e))

        # Fetch atividades
        if include_atividades:
            try:
                leg_results["atividades"] = fetch_atividades(leg, force=force)
            except FetchError as e:
                fail("fetch_atividades_failed", legislature=leg, error=str(e))

        # Fetch the OE budgets debated in this legislature
        if include_oe:
            for ano in [a for a, oe in config.OE.items() if oe["legislatura"] == leg]:
                try:
                    leg_results[f"oe_{ano}"] = fetch_oe(ano, force=force)
                except FetchError as e:
                    fail("fetch_oe_failed", ano=ano, error=str(e))

        if leg_results:
            results[leg] = leg_results

    # Everything else was still fetched; fail now so the caller (make, the
    # systemd timer) stops before transform and leaves the running API alone.
    if failed:
        raise FetchError(f"{len(failed)} fetch(es) failed: {failed}")

    return results
