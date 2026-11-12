"""Data transformation module for Portuguese Parliament ETL Pipeline.

Frederico Muñoz <fsmunoz@gmail.com>

Transforms JSON to Parquet using DuckDB with complete data preservation. All nested structures are
preserved as STRUCT/LIST types, so they can be used and filtered upon.

"""

import duckdb
import json
import re
import structlog
import unicodedata
from datetime import date, datetime
from pathlib import Path

import config
from etl.schema import get_select_clause, get_atividades_select_clause

logger = structlog.get_logger()

# Add a custom exception class for transformation errors.
class TransformError(Exception):
    """Raised when transformation fails."""
    pass


# Vote positions ("sentidos") as they appear in detalhe, normalized to keys
SENTIDOS = ('a_favor', 'contra', 'abstencao', 'ausencia')

# "6-PSD": 6 deputies of PSD voted this way
COUNT_RE = re.compile(r'^(\d+)-(.+)$')

# "João Silva (PSD)": a deputy named individually (typically voting differently from the group)
NAMED_RE = re.compile(r'^(.+?)\s*\(([^()]+)\)$')


def _detalhe_tokens(detalhe: str):
    """
    Yield (sentido, token) for every entry in an HTML voting details string.

    "A Favor: <I>PSD</I>, <I> 1-PS</I><BR>Contra:<I>CH</I>"
    -> ('a_favor', 'PSD'), ('a_favor', '1-PS'), ('contra', 'CH')

    This is based on the proc-parl-pt code, with some simplifications.
    """
    for section in detalhe.split('<BR>'):
        if ':' not in section:
            continue
        vote_type, parties_html = section.split(':', 1)
        # "Abstenção" -> abstencao, "Ausência" -> ausencia
        sentido = unicodedata.normalize('NFKD', vote_type.strip().lower().replace(' ', '_'))
        sentido = sentido.encode('ascii', 'ignore').decode()
        if sentido not in SENTIDOS:
            continue
        for token in re.sub(r'</?I>', '', parties_html).split(','):
            if token.strip():
                yield sentido, token.strip()


def parse_detalhe(detalhe: str) -> dict | None:
    """Parse HTML voting details into party positions.

    "A Favor: <I>PSD</I>, <I>CDS-PP</I><BR>Contra:<I>CH</I>"
    -> {"a_favor": ["PSD", "CDS-PP"], "contra": ["CH"], "abstencao": [], "ausencia": []}

    Only plain party codes are listed. Counts ("6-PSD") and individually named deputies
    ("João Silva (PSD)") are left out here; see parse_detalhe_contagens and
    parse_detalhe_deputados.

    IMPORTANT: Ninsc members are preserved with full names (e.g., "John Doe (Ninsc)") because they
    represent different political positions and must not be aggregated: a Ninsc MP can be a person
    that was elected by a party alone (only >1 MPs constitute a parliamentary group) or an MP that
    left the party that elected them. Either way, they should be treated as "parties" in themselves.

    Returns:
        Dict with vote positions, or None if detalhe is empty
    """
    if not detalhe or not detalhe.strip():
        return None

    result = {sentido: [] for sentido in SENTIDOS}
    for sentido, token in _detalhe_tokens(detalhe):
        if COUNT_RE.match(token) or token.isdigit():
            continue
        if '(Ninsc)' in token or not NAMED_RE.match(token):
            result[sentido].append(token)
    return result


def parse_detalhe_contagens(detalhe: str) -> list[dict] | None:
    """
    Per-party vote counts given in the source as "N-PARTY".

    "A Favor: <I>82-PSD</I>, <I> 53-PS</I><BR>Abstenção:<I>3-PCP</I>"
    -> [{"partido": "PSD", "sentido": "a_favor", "votos": 82}, ..., {"partido": "PCP", "sentido": "abstencao", "votos": 3}]

    When a party is also listed by plain code, the count is the part of the group that voted
    differently ("Contra: PSD, 1-PS" with PS under A Favor). When a vote lists every party only
    as counts, these are the full per-party results.
    """
    if not detalhe or not detalhe.strip():
        return None
    return [
        {'partido': m[2], 'sentido': sentido, 'votos': int(m[1])}
        for sentido, token in _detalhe_tokens(detalhe)
        if (m := COUNT_RE.match(token))
    ]


def parse_detalhe_deputados(detalhe: str) -> list[dict] | None:
    """
    Deputies named individually in the source, with their vote; Ninsc members are excluded
    (they are already in parse_detalhe, as "parties").

    "A Favor: <I>PS</I><BR>Contra:<I>21-PSD</I>, <I> João Silva (PSD)</I>"
    -> [{"nome": "João Silva", "partido": "PSD", "sentido": "contra"}]
    """
    if not detalhe or not detalhe.strip():
        return None
    return [
        {'nome': m[1], 'partido': m[2], 'sentido': sentido}
        for sentido, token in _detalhe_tokens(detalhe)
        if (m := NAMED_RE.match(token)) and m[2] != 'Ninsc'
    ]


_VARCHAR = duckdb.string_type()

# UDF name -> (function, DuckDB return type)
DETALHE_UDFS = {
    "parse_detalhe": (
        parse_detalhe,
        duckdb.struct_type({sentido: duckdb.list_type(_VARCHAR) for sentido in SENTIDOS}),
    ),
    "parse_detalhe_contagens": (
        parse_detalhe_contagens,
        duckdb.list_type(duckdb.struct_type({'partido': _VARCHAR, 'sentido': _VARCHAR, 'votos': duckdb.sqltype('INTEGER')})),
    ),
    "parse_detalhe_deputados": (
        parse_detalhe_deputados,
        duckdb.list_type(duckdb.struct_type({'nome': _VARCHAR, 'partido': _VARCHAR, 'sentido': _VARCHAR})),
    ),
}


def register_detalhe_udfs(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Register the detalhe parsers as DuckDB UDFs (Python dicts become STRUCTs). Doing this in
    Python rather than SQL reuses the proc_parl_pt logic and keeps it readable.
    """
    for name, (function, return_type) in DETALHE_UDFS.items():
        conn.create_function(name, function, parameters=[_VARCHAR], return_type=return_type)


def transform_legislature(
    legislature: str,
    bronze_path: Path | None = None,
    silver_path: Path | None = None
) -> Path:
    """
    Transform JSON to Parquet with complete data preservation.

    All nested structures (IniEventos, IniAnexos, etc.) are preserved
    as DuckDB STRUCT and LIST types in Parquet. No data is lost or flattened.

    Args:
        legislature: Legislature ID (e.g., "L17")
        bronze_path: Input JSON path (default: auto-detect)
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created Parquet file

    Raises:
        TransformError: If the transformation fails.
    """
    if bronze_path is None:
        bronze_path = config.BRONZE_DIR / f"iniciativas_{legislature.lower()}.json"

    if silver_path is None:
        silver_path = config.SILVER_DIR / f"iniciativas_{legislature.lower()}.parquet"

    if not bronze_path.exists():
        raise TransformError(f"Bronze file not found: {bronze_path}")

    logger.info("transforming", legislature=legislature, input=str(bronze_path))

    try:
        conn = duckdb.connect()

        # Configure DuckDB with the limits from .env
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        # Get SELECT clause with field mappings (using the helper)
        select_clause = get_select_clause(legislature)

        # Transform: JSON -> Parquet
        # DuckDB automatically preserves nested structures as STRUCT/LIST types, which is quite nice.
        
        query = f"""
            COPY (
                SELECT
                    {select_clause}
                FROM read_json_auto(
                    '{bronze_path}',
                    union_by_name=true,
                    maximum_object_size=16777216
                )
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get stats
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_complete",
            legislature=legislature,
            records=record_count,
            size_mb=size_mb,
            compression_ratio=round(
                bronze_path.stat().st_size / silver_path.stat().st_size, 2
            )
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming {legislature}: {e}")


def transform_info_base(
    legislature: str,
    bronze_path: Path | None = None,
    silver_path: Path | None = None
) -> Path | None:
    """
    Transform InformacaoBase JSON to Parquet.

    Converts legislature metadata (deputies, groups, etc.) to Parquet format.

    Args:
        legislature: Legislature ID (e.g., "L17")
        bronze_path: Input JSON path (default: auto-detect)
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created Parquet file, or None if bronze file doesn't exist

    Raises:
        TransformError: If transformation fails.
    """
    if bronze_path is None:
        bronze_path = config.BRONZE_DIR / f"info_base_{legislature.lower()}.json"

    if silver_path is None:
        silver_path = config.SILVER_DIR / f"info_base_{legislature.lower()}.parquet"

    if not bronze_path.exists():
        logger.warning("bronze_file_not_found", path=str(bronze_path))
        return None

    logger.info("transforming_info_base", legislature=legislature, input=str(bronze_path))

    try:
        conn = duckdb.connect()

        # Configure DuckDB with options from .env
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        # Transform: JSON -> Parquet
        # The InformacaoBase structure is preserved as-is
        query = f"""
            COPY (
                SELECT
                    '{legislature}' as legislatura,
                    *
                FROM read_json_auto(
                    '{bronze_path}',
                    maximum_object_size=16777216
                )
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_info_base_complete",
            legislature=legislature,
            size_mb=size_mb
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming info_base for {legislature}: {e}")


def transform_votacoes(legislature: str, silver_path: Path | None = None) -> Path:
    """
    Transform votacoes by flattening nested structure from iniciativas.

    Extracts all votes from iniciativas.ini_eventos.Votacao (plenary) and
    ini_eventos.Comissao.Votacao (committee, tipo_reuniao='COM') and creates
    a separate votacoes.parquet file with one record per vote.

    Args:
        legislature: Legislature ID (e.g., "L17")
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created votacoes Parquet file

    Raises:
        TransformError: If transformation fails
    """
    if silver_path is None:
        silver_path = config.SILVER_DIR / f"votacoes_{legislature.lower()}.parquet"

    # Source: already-transformed iniciativas parquet
    iniciativas_path = config.SILVER_DIR / f"iniciativas_{legislature.lower()}.parquet"

    if not iniciativas_path.exists():
        raise TransformError(
            f"Iniciativas file not found: {iniciativas_path}. "
            "Run transform_legislature first."
        )

    logger.info("transforming_votacoes", legislature=legislature)

    try:
        conn = duckdb.connect()

        # Configure DuckDB, with options from .env
        # TODO: this can perhaps be added to a helper?
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        register_detalhe_udfs(conn)

        # Flatten votacoes from nested structure
        query = f"""
            COPY (
                WITH all_events AS (
                    SELECT
                        ini_id,
                        ini_nr,
                        legislatura,
                        ini_titulo,
                        ini_tipo,
                        UNNEST(ini_eventos) as evento
                    FROM '{iniciativas_path}'
                    WHERE ini_eventos IS NOT NULL
                      AND length(ini_eventos) > 0
                ),
                flattened_votes AS (
                    SELECT
                        ini_id,
                        ini_nr,
                        legislatura,
                        ini_titulo,
                        ini_tipo,
                        evento.Fase as fase,
                        evento.DataFase as data_fase,
                        UNNEST(evento.Votacao) as vot,
                        NULL::VARCHAR as comissao,
                        NULL::VARCHAR as tipo_reuniao_override
                    FROM all_events
                    WHERE evento.Votacao IS NOT NULL
                      AND length(evento.Votacao) > 0
                ),
                -- Committee votes live one level deeper (IniEventos[].Comissao[].Votacao)
                -- and have no tipoReuniao in the source, so tag them 'COM'.
                event_comissoes AS (
                    SELECT
                        ini_id, ini_nr, legislatura, ini_titulo, ini_tipo,
                        evento.Fase as fase,
                        evento.DataFase as data_fase,
                        UNNEST(evento.Comissao) as com
                    FROM all_events
                    WHERE evento.Comissao IS NOT NULL
                      AND length(evento.Comissao) > 0
                ),
                committee_votes AS (
                    SELECT
                        ini_id, ini_nr, legislatura, ini_titulo, ini_tipo, fase, data_fase,
                        UNNEST(com.Votacao) as vot,
                        trim(com.Nome) as comissao,
                        'COM' as tipo_reuniao_override
                    FROM event_comissoes
                    WHERE com.Votacao IS NOT NULL
                      AND length(com.Votacao) > 0
                ),
                all_votes AS (
                    SELECT ini_id, ini_nr, legislatura, ini_titulo, ini_tipo, fase, data_fase,
                           vot.id, vot.data, vot.resultado, vot.descricao, vot.reuniao,
                           vot.tipoReuniao::VARCHAR as tipoReuniao, vot.unanime, vot.ausencias, vot.detalhe,
                           comissao, tipo_reuniao_override
                    FROM flattened_votes
                    UNION ALL
                    SELECT ini_id, ini_nr, legislatura, ini_titulo, ini_tipo, fase, data_fase,
                           vot.id, vot.data, vot.resultado, vot.descricao, vot.reuniao,
                           NULL::VARCHAR, vot.unanime, vot.ausencias, vot.detalhe,
                           comissao, tipo_reuniao_override
                    FROM committee_votes
                )
                SELECT
                    id as vot_id,
                    ini_id,
                    ini_nr,
                    legislatura,
                    ini_titulo,
                    ini_tipo,
                    fase,
                    data_fase,
                    data,
                    resultado,
                    descricao,
                    reuniao,
                    COALESCE(tipo_reuniao_override, tipoReuniao) as tipo_reuniao,
                    comissao,
                    unanime,
                    ausencias,
                    detalhe,
                    parse_detalhe(detalhe) as detalhe_parsed,
                    parse_detalhe_contagens(detalhe) as detalhe_contagens,
                    parse_detalhe_deputados(detalhe) as detalhe_deputados,
                    length(COALESCE(detalhe, '')) >= 1000 as is_nominal
                FROM all_votes
                ORDER BY data DESC NULLS LAST, vot_id
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get stats
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_votacoes_complete",
            legislature=legislature,
            votes=record_count,
            size_mb=size_mb
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming votacoes for {legislature}: {e}")


def transform_deputados(legislature: str, silver_path: Path | None = None) -> Path:
    """
    Transform deputados by flattening from info_base.

    Extracts all deputies from info_base.Deputados and creates
    a separate deputados.parquet file with one record per deputy.

    Args:
        legislature: Legislature ID (e.g., "L17")
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created deputados Parquet file

    Raises:
        TransformError: If transformation fails.
    """
    if silver_path is None:
        silver_path = config.SILVER_DIR / f"deputados_{legislature.lower()}.parquet"

    # Source: info_base parquet
    info_base_path = config.SILVER_DIR / f"info_base_{legislature.lower()}.parquet"

    if not info_base_path.exists():
        raise TransformError(
            f"Info base file not found: {info_base_path}. "
            "Run transform_info_base first."
        )

    logger.info("transforming_deputados", legislature=legislature)

    try:
        conn = duckdb.connect()

        # Configure DuckDB
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        # Flatten deputados from nested structure
        # Normalize nested historical records to snake_case
        query = f"""
            COPY (
                WITH unnested AS (
                    SELECT UNNEST(Deputados) as dep
                    FROM '{info_base_path}'
                )
                SELECT
                    '{legislature}' as legislatura,
                    dep.DepCadId as dep_cad_id,
                    dep.DepNomeParlamentar as nome_parlamentar,
                    dep.DepNomeCompleto as nome_completo,
                    dep.DepCPDes as circulo_atual,
                    dep.DepCPId as circulo_id,
                    dep.DepGP[-1].gpSigla as partido_atual,
                    dep.DepSituacao[-1].sioDes as situacao_atual,

                    -- Normalize partido_historico to snake_case
                    list_transform(dep.DepGP, x -> {{
                        'gp_sigla': x.gpSigla,
                        'gp_dt_inicio': x.gpDtInicio,
                        'gp_dt_fim': x.gpDtFim,
                        'gp_id': x.gpId
                    }}) as partido_historico,

                    -- Normalize situacao_historico to snake_case
                    list_transform(dep.DepSituacao, x -> {{
                        'sio_des': x.sioDes,
                        'sio_dt_inicio': x.sioDtInicio,
                        'sio_dt_fim': x.sioDtFim
                    }}) as situacao_historico
                FROM unnested
                ORDER BY dep.DepNomeParlamentar
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get statistics
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_deputados_complete",
            legislature=legislature,
            deputies=record_count,
            size_mb=size_mb
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming deputados for {legislature}: {e}")


def transform_circulos(legislature: str, silver_path: Path | None = None) -> Path:
    """
    Transform circulos by flattening from info_base.

    Extracts all electoral circles from info_base.CirculosEleitorais and creates
    a separate circulos.parquet file with one record per circle.

    Args:
        legislature: Legislature ID (e.g., "L17")
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created circulos Parquet file

    Raises:
        TransformError: If transformation fails.
    """
    if silver_path is None:
        silver_path = config.SILVER_DIR / f"circulos_{legislature.lower()}.parquet"

    # Source: info_base parquet
    info_base_path = config.SILVER_DIR / f"info_base_{legislature.lower()}.parquet"

    if not info_base_path.exists():
        raise TransformError(
            f"Info base file not found: {info_base_path}. "
            "Run transform_info_base first."
        )

    logger.info("transforming_circulos", legislature=legislature)

    try:
        conn = duckdb.connect()

        # Configure DuckDB
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        # Flatten circulos from nested structure
        query = f"""
            COPY (
                WITH unnested AS (
                    SELECT UNNEST(CirculosEleitorais) as circ
                    FROM '{info_base_path}'
                )
                SELECT
                    '{legislature}' as legislatura,
                    circ.cpId as cp_id,
                    circ.cpDes as cp_des
                FROM unnested
                ORDER BY circ.cpDes
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get statistics
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_circulos_complete",
            legislature=legislature,
            circles=record_count,
            size_mb=size_mb
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming circulos for {legislature}: {e}")


def transform_partidos(legislature: str, silver_path: Path | None = None) -> Path:
    """
    Transform partidos by flattening from info_base.

    Extracts all parliamentary groups from info_base.GruposParlamentares and creates
    a separate partidos.parquet file with one record per party.

    Args:
        legislature: Legislature ID (e.g., "L17")
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created partidos Parquet file

    Raises:
        TransformError: If transformation fails.
    """
    if silver_path is None:
        silver_path = config.SILVER_DIR / f"partidos_{legislature.lower()}.parquet"

    # Source: info_base parquet
    info_base_path = config.SILVER_DIR / f"info_base_{legislature.lower()}.parquet"

    if not info_base_path.exists():
        raise TransformError(
            f"Info base file not found: {info_base_path}. "
            "Run transform_info_base first."
        )

    logger.info("transforming_partidos", legislature=legislature)

    try:
        conn = duckdb.connect()

        # Configure DuckDB
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        # Flatten partidos from nested structure
        query = f"""
            COPY (
                WITH unnested AS (
                    SELECT UNNEST(GruposParlamentares) as gp
                    FROM '{info_base_path}'
                )
                SELECT
                    '{legislature}' as legislatura,
                    gp.sigla as gp_sigla,
                    gp.nome as gp_nome
                FROM unnested
                ORDER BY gp.sigla
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get statistics
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_partidos_complete",
            legislature=legislature,
            parties=record_count,
            size_mb=size_mb
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming partidos for {legislature}: {e}")


def transform_atividades(
    legislature: str,
    bronze_path: Path | None = None,
    silver_path: Path | None = None
) -> Path | None:
    """
    Transform Atividades JSON to Parquet.

    Extracts the Atividades array from nested {"AtividadesGerais": {"Atividades": [...]}}
    structure and applies field name normalization.

    Args:
        legislature: Legislature ID (e.g., "L17")
        bronze_path: Input JSON path (default: auto-detect)
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created Parquet file, or None if bronze file doesn't exist

    Raises:
        TransformError: If transformation fails
    """
    if bronze_path is None:
        bronze_path = config.BRONZE_DIR / f"atividades_{legislature.lower()}.json"

    if silver_path is None:
        silver_path = config.SILVER_DIR / f"atividades_{legislature.lower()}.parquet"

    if not bronze_path.exists():
        logger.warning("bronze_file_not_found", path=str(bronze_path))
        return None

    logger.info("transforming_atividades", legislature=legislature, input=str(bronze_path))

    try:
        conn = duckdb.connect()

        # Configure DuckDB
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        # Get SELECT clause with field mappings
        select_clause = get_atividades_select_clause(legislature)

        # Transform: JSON -> Parquet
        # Extract Atividades array from nested structure
        query = f"""
            COPY (
                WITH atividades_gerais AS (
                    SELECT AtividadesGerais FROM read_json_auto(
                        '{bronze_path}',
                        maximum_object_size=16777216
                    )
                ),
                atividades_array AS (
                    SELECT UNNEST(AtividadesGerais.Atividades) as ativ
                    FROM atividades_gerais
                    WHERE AtividadesGerais.Atividades IS NOT NULL
                )
                SELECT
                    -- Generate synthetic ID (composite key or hash)
                    CASE
                        WHEN ativ.Numero IS NOT NULL
                        THEN '{legislature}_' || ativ.Tipo || '_' || ativ.Numero
                        ELSE '{legislature}_' || MD5(COALESCE(ativ.Assunto, '') || COALESCE(CAST(ativ.DataEntrada AS VARCHAR), ''))
                    END as ativ_id,
                    ativ.Assunto as ativ_assunto,
                    ativ.Tipo as ativ_tipo,
                    ativ.DescTipo as ativ_desc_tipo,
                    ativ.Numero as ativ_numero,
                    ativ.Sessao as sessao,
                    ativ.DataEntrada as data_entrada,
                    ativ.DataAgendamentoDebate as data_agendamento_debate,
                    ativ.DataAnuncio as data_anuncio,
                    ativ.AutoresGP as ativ_autores_gp,
                    ativ.TipoAutor as ativ_tipo_autor,
                    ativ.Publicacao as publicacao,
                    ativ.PublicacaoDebate as publicacao_debate,
                    ativ.VotacaoDebate as votacao_debate,
                    ativ.TextosAprovados::VARCHAR[] as textos_aprovados,
                    ativ.Observacoes as observacoes,
                    '{legislature}' as legislatura,
                    CURRENT_TIMESTAMP as etl_timestamp
                FROM atividades_array
                ORDER BY data_entrada DESC NULLS LAST
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get stats
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_atividades_complete",
            legislature=legislature,
            atividades=record_count,
            size_mb=size_mb,
            compression_ratio=round(
                bronze_path.stat().st_size / silver_path.stat().st_size, 2
            )
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming atividades for {legislature}: {e}")


def transform_atividades_votacoes(
    legislature: str,
    silver_path: Path | None = None
) -> Path | None:
    """
    Extract votes from atividades.votacao_debate array.

    Flattens nested VotacaoDebate array and parses HTML voting details
    using the same parse_detalhe() UDF as iniciativas votes.

    Args:
        legislature: Legislature ID (e.g., "L17")
        silver_path: Output Parquet path (default: auto-detect)

    Returns:
        Path to created votacoes Parquet file, or None if atividades not found

    Raises:
        TransformError: If transformation fails
    """
    if silver_path is None:
        silver_path = config.SILVER_DIR / f"atividades_votacoes_{legislature.lower()}.parquet"

    # Source: already-transformed atividades parquet
    atividades_path = config.SILVER_DIR / f"atividades_{legislature.lower()}.parquet"

    if not atividades_path.exists():
        logger.warning("atividades_file_not_found", path=str(atividades_path))
        return None

    logger.info("transforming_atividades_votacoes", legislature=legislature)

    try:
        conn = duckdb.connect()

        # Configure DuckDB
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        register_detalhe_udfs(conn)

        # Flatten votes from atividades
        query = f"""
            COPY (
                WITH atividades_with_votes AS (
                    SELECT
                        ativ_id,
                        ativ_assunto,
                        ativ_tipo,
                        ativ_numero,
                        legislatura,
                        data_entrada,
                        ativ_autores_gp,
                        UNNEST(votacao_debate) as vot
                    FROM '{atividades_path}'
                    WHERE votacao_debate IS NOT NULL
                      AND length(votacao_debate) > 0
                )
                SELECT
                    vot.id as vot_id,
                    ativ_id,
                    legislatura,
                    ativ_assunto as assunto,
                    ativ_tipo as tipo,
                    ativ_numero as numero,
                    data_entrada,
                    ativ_autores_gp as autores_gp,
                    vot.data as data,
                    vot.resultado,
                    vot.descricao,
                    vot.reuniao,
                    vot.unanime,
                    vot.ausencias,
                    vot.detalhe,
                    vot.publicacao,
                    parse_detalhe(vot.detalhe) as detalhe_parsed,
                    parse_detalhe_contagens(vot.detalhe) as detalhe_contagens,
                    parse_detalhe_deputados(vot.detalhe) as detalhe_deputados,
                    CASE
                        WHEN vot.detalhe IS NOT NULL AND length(vot.detalhe) > 0
                        THEN true
                        ELSE false
                    END as has_party_details,
                    'atividade' as source
                FROM atividades_with_votes
                ORDER BY data DESC NULLS LAST, vot_id
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """

        conn.execute(query)

        # Get stats
        record_count = conn.execute(f"""
            SELECT count(*) FROM '{silver_path}'
        """).fetchone()[0]

        size_mb = round(silver_path.stat().st_size / 1024.0 / 1024.0, 2)

        logger.info(
            "transform_atividades_votacoes_complete",
            legislature=legislature,
            votes=record_count,
            size_mb=size_mb
        )

        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming atividades_votacoes for {legislature}: {e}")


def _audicao_select(id_field: str, numero_field: str, extra: str = "") -> str:
    """SELECT list shared by Audicoes and Audiencias (same shape, different key names)."""
    return f"""
        CAST(x.{id_field} AS VARCHAR) as aud_id,
        x.{numero_field}::VARCHAR as numero,
        -- numero is '<n>-<committee acronym>-<legislature>', e.g. '74-CECT-XVII'
        split_part(x.{numero_field}, '-', 2) as comissao_sigla,
        x.Assunto::VARCHAR as assunto,
        x.Entidades::VARCHAR as entidades,
        x.Data::DATE as data,
        x.SessaoLegislativa::VARCHAR as sessao{extra}
    """


# Top-level sections of the Atividades JSON persisted as their own tables:
# name (silver file prefix) -> (JSON section, SELECT list over `x`).
# Explicit casts keep schemas identical across legislatures (all-null fields infer as JSON).
ATIVIDADES_SECTIONS = {
    "debates": ("Debates", """
        x.DebateId::VARCHAR as debate_id,
        x.TipoDebate::VARCHAR as tipo_debate,
        x.TipoDebateDesig::VARCHAR as tipo_debate_desig,
        x.Assunto::VARCHAR as assunto,
        x.DataDebate::DATE as data_debate,
        x.DataEntrada::DATE as data_entrada,
        x.TipoAutor::VARCHAR as tipo_autor,
        x.AutoresGP::VARCHAR as autor_gp,
        x.AutoresDeputados::VARCHAR as autores_deputados,
        x.Artigo::VARCHAR as artigo,
        x.Intervencoes::VARCHAR[] as intervencoes,
        x.Publicacao as publicacao,
        x.Sessao::VARCHAR as sessao,
        x.Observacoes::VARCHAR as observacoes
    """),
    "audicoes": ("Audicoes", _audicao_select("IDAudicao", "NumeroAudicao")),
    "audiencias": ("Audiencias", _audicao_select("IDAudiencia", "NumeroAudiencia",
                                                 ",\n        x.Concedida::VARCHAR as concedida")),
}


def transform_atividades_section(legislature: str, name: str) -> Path | None:
    """
    Persist one top-level section of the Atividades JSON (see ATIVIDADES_SECTIONS).

    Returns:
        Path to created Parquet file, or None if bronze file doesn't exist
    """
    section, select_list = ATIVIDADES_SECTIONS[name]
    bronze_path = config.BRONZE_DIR / f"atividades_{legislature.lower()}.json"
    silver_path = config.SILVER_DIR / f"{name}_{legislature.lower()}.parquet"

    if not bronze_path.exists():
        logger.warning("bronze_file_not_found", path=str(bronze_path))
        return None

    try:
        conn = duckdb.connect()
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")
        conn.execute(f"""
            COPY (
                WITH items AS (
                    SELECT UNNEST({section}) as x
                    FROM read_json_auto('{bronze_path}', maximum_object_size=16777216)
                )
                SELECT {select_list}, '{legislature}' as legislatura
                FROM items
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """)
        count = conn.execute(f"SELECT count(*) FROM '{silver_path}'").fetchone()[0]
        logger.info("transform_atividades_section_complete", legislature=legislature, section=name, rows=count)
        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, section=name, error=str(e))
        raise TransformError(f"Error transforming {name} for {legislature}: {e}")


def transform_cap(
    legislature: str,
    cap_source_path: Path | None = None,
    silver_path: Path | None = None,
) -> Path | None:
    """
    Convert a CAP mapping CSV into a Parquet file in the silver layer.

    The source CSV is produced by the votoaberto-cap project's classify.py
    and committed into data/cap_source/cap_<leg>.csv. If the CSV does not
    exist this function logs a warning and returns None (graceful skip).

    Columns in source CSV: ini_id, legislatura, cap, cap_label, model_version
    These are written as-is to the Parquet file.

    Args:
        legislature: Legislature ID (e.g., "L17")
        cap_source_path: Input CSV path (default: config.CAP_SOURCE_DIR / cap_<leg>.csv)
        silver_path: Output Parquet path (default: config.SILVER_DIR / cap_<leg>.parquet)

    Returns:
        Path to created Parquet file, or None if CSV source is absent.

    Raises:
        TransformError: If the CSV exists but conversion fails.
    """
    if cap_source_path is None:
        cap_source_path = config.CAP_SOURCE_DIR / f"cap_{legislature.lower()}.csv"

    if silver_path is None:
        silver_path = config.SILVER_DIR / f"cap_{legislature.lower()}.parquet"

    if not cap_source_path.exists():
        logger.info(
            "transform_cap_skipped",
            legislature=legislature,
            reason="source CSV not found",
            path=str(cap_source_path),
        )
        return None

    logger.info("transform_cap_start", legislature=legislature, input=str(cap_source_path))

    try:
        conn = duckdb.connect()
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        query = f"""
            COPY (
                SELECT
                    ini_id::VARCHAR         AS ini_id,
                    legislatura::VARCHAR    AS legislatura,
                    cap::INTEGER            AS cap,
                    cap_label::VARCHAR      AS cap_label,
                    model_version::VARCHAR  AS model_version
                FROM read_csv_auto('{cap_source_path}', header=true)
                ORDER BY legislatura, ini_id
            ) TO '{silver_path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """
        conn.execute(query)
        conn.close()

        record_count = duckdb.execute(f"SELECT count(*) FROM '{silver_path}'").fetchone()[0]
        size_kb = round(silver_path.stat().st_size / 1024.0, 1)

        logger.info(
            "transform_cap_complete",
            legislature=legislature,
            records=record_count,
            size_kb=size_kb,
        )
        return silver_path

    except duckdb.Error as e:
        logger.error("duckdb_error", legislature=legislature, error=str(e))
        raise TransformError(f"DuckDB error in transform_cap: {e}")
    except Exception as e:
        logger.error("transform_error", legislature=legislature, error=str(e))
        raise TransformError(f"Error transforming CAP for {legislature}: {e}")


# Orçamento do Estado (propostas de alteração) ------------------------------------------------
#
# The OE JSON is converted from XML, so its shape differs from the other datasets: one-element
# lists collapse into the element (and empty ones into null), votes are two parallel arrays of
# party *full names* and votes, there are no vote IDs and dates are dd/mm/yyyy. It's normalized
# here in Python and written with explicit schemas (read_json_auto would infer each file
# differently, and a budget still in debate has no votes at all).
#
# Votes are written with the same detalhe_parsed / detalhe_deputados columns as votacoes, so that
# everything that analyses those also works for the OE.

OE_SENTIDOS = {'Favor': 'a_favor', 'Contra': 'contra', 'Abstenção': 'abstencao', 'Ausente': 'ausencia'}

# Proponentes.GP_Partido truncates CDS-PP
OE_GP_FIXES = {'CDS-P': 'CDS-PP'}

_OE_DETALHE = f"STRUCT({', '.join(f'{s} VARCHAR[]' for s in SENTIDOS)})"

OE_PROPOSTAS_COLUMNS = {
    'prop_id': 'VARCHAR', 'numero': 'VARCHAR', 'ano': 'INTEGER', 'legislatura': 'VARCHAR',
    'data': 'DATE', 'titulo': 'VARCHAR', 'temas': 'VARCHAR[]', 'tipo': 'VARCHAR', 'estado': 'VARCHAR',
    'incide': 'VARCHAR', 'autores_gp': 'VARCHAR[]',
    'proponentes': 'STRUCT(nome VARCHAR, partido VARCHAR)[]',
    'numero_artigo_novo': 'VARCHAR',
    'artigos': 'STRUCT(artigo VARCHAR, titulo VARCHAR, texto VARCHAR, estado VARCHAR)[]',
    'ficheiro': 'VARCHAR', 'n_votacoes': 'INTEGER',
}

OE_VOTACOES_COLUMNS = {
    'vot_id': 'VARCHAR', 'prop_id': 'VARCHAR', 'numero': 'VARCHAR', 'ano': 'INTEGER',
    'legislatura': 'VARCHAR', 'titulo': 'VARCHAR', 'tipo': 'VARCHAR', 'autores_gp': 'VARCHAR[]',
    'data': 'DATE', 'resultado': 'VARCHAR', 'resultado_completo': 'VARCHAR', 'descricao': 'VARCHAR',
    'subdescricao': 'VARCHAR', 'tipo_reuniao': 'VARCHAR', 'unanime': 'VARCHAR',
    'votos': 'STRUCT(nome VARCHAR, voto VARCHAR)[]',
    'detalhe_parsed': _OE_DETALHE,
    'detalhe_deputados': 'STRUCT(nome VARCHAR, partido VARCHAR, sentido VARCHAR)[]',
    'source': 'VARCHAR',
}


def _as_list(x) -> list:
    """XML-converted JSON: null -> [], a single element -> [element], a list stays a list."""
    return [] if x is None else x if isinstance(x, list) else [x]


def _oe_date(value: str | None) -> date | None:
    """'15/11/2024 21:42:00' -> 2024-11-15 (day first: the old p3 CSVs got this wrong)."""
    return datetime.strptime(value[:10], '%d/%m/%Y').date() if value else None


def _split(value: str | None, sep: str) -> list[str]:
    return [part.strip() for part in (value or '').split(sep) if part.strip()]


def _oe_deputado(nome: str, data: date | None, deputados: dict) -> tuple[str, str | None]:
    """Source deputy name ('SARA MADRUGA DA COSTA') -> (nome_parlamentar, gp_sigla on that date or None)."""
    nome_parl, historico = deputados.get(nome.strip().lower(), (nome.strip().title(), []))
    sigla = next((
        sigla for sigla, inicio, fim in historico
        if data is not None and inicio <= data and (fim is None or data <= fim)
    ), None)
    return nome_parl, sigla


def oe_autores(autores: list[str], proponentes: list[dict], data: date | None, siglas: dict, deputados: dict) -> list[str]:
    """
    GrupoParlamentar_Partido -> autores_gp, as in iniciativas: party siglas only. The source lists a
    deputy's name when they authored a proposal alone; that becomes their party at the time
    (Sara Madruga da Costa -> PSD), or nothing when they were non-attached (they are still in
    proponentes, as Ninsc).
    """
    known = set(siglas.values())
    result = []
    for autor in autores:
        sigla = OE_GP_FIXES.get(autor, autor)
        if sigla not in known:
            _, sigla = _oe_deputado(autor, data, deputados)
            sigla = sigla or next((pr['partido'] for pr in proponentes if pr['nome'].lower() == autor.lower()), None)
            if sigla is None:
                raise TransformError(f"Unknown OE author: '{autor}'")
        if sigla != 'Ninsc' and sigla not in result:
            result.append(sigla)
    return result


def oe_parse_votos(votos: list[dict], data: date | None, siglas: dict, deputados: dict) -> tuple[dict, list]:
    """
    Turn the source votes ({nome, voto} pairs) into detalhe_parsed / detalhe_deputados, using the
    same conventions as parse_detalhe:

    - parties as their sigla ("Partido Socialista" -> "PS", via partidos.gp_nome)
    - deputies named individually ("PEDRO COELHO(PSD)") go to detalhe_deputados, unless they were
      non-attached on the vote date (from deputados.partido_historico): those are kept with the
      parties as "Name (Ninsc)". The source lists them under their former party: Cristina
      Rodrigues is "(PAN)" in OE2021, but had been Ninsc since June 2020.

    siglas: lower(gp_nome) -> gp_sigla
    deputados: lower(nome_parlamentar) -> (nome_parlamentar, [(gp_sigla, inicio, fim), ...])

    Raises TransformError on an unknown party name or vote, so that a new party fails loudly.
    """
    parsed = {sentido: [] for sentido in SENTIDOS}
    named = []
    for v in votos:
        nome, voto = v['nome'], v['voto']
        if voto not in OE_SENTIDOS:
            raise TransformError(f"Unknown OE vote '{voto}' for {nome}")
        sentido = OE_SENTIDOS[voto]
        if nome.lower() in siglas:
            parsed[sentido].append(siglas[nome.lower()])
        elif nome == 'Não Inscrito':
            # Seen once (OE2025), with no name: keep it identifiable as non-attached
            parsed[sentido].append('Não Inscrito (Ninsc)')
        elif m := NAMED_RE.match(nome):
            nome_parl, sigla = _oe_deputado(m[1], data, deputados)
            if sigla == 'Ninsc':
                parsed[sentido].append(f"{nome_parl} (Ninsc)")
            else:
                named.append({'nome': nome_parl, 'partido': m[2], 'sentido': sentido})
        else:
            raise TransformError(f"Unknown party in OE vote: '{nome}'")
    return parsed, named


def oe_rows(propostas: list[dict], ano: int, legislatura: str, siglas: dict, deputados: dict) -> tuple[list, list]:
    """Flatten the source propostas into (propostas rows, votacoes rows)."""
    prop_rows, vot_rows = [], []
    for p in propostas:
        data_prop = _oe_date(p.get('Data'))
        proponentes = []
        for pr in _as_list((p.get('Proponentes') or {}).get('Proponente')):
            nome, sigla = _oe_deputado(pr.get('Deputado') or '', data_prop, deputados)
            partido = OE_GP_FIXES.get(pr.get('GP_Partido'), pr.get('GP_Partido'))
            proponentes.append({'nome': nome, 'partido': 'Ninsc' if sigla == 'Ninsc' else partido})
        autores = oe_autores(_split(p.get('GrupoParlamentar_Partido'), ','), proponentes, data_prop, siglas, deputados)
        votacoes = _as_list((p.get('Votacoes') or {}).get('Votacao'))
        prop_rows.append({
            'prop_id': p['ID'], 'numero': p['Numero'], 'ano': ano, 'legislatura': legislatura,
            'data': data_prop, 'titulo': p.get('Titulo'), 'temas': _split(p.get('Tema'), ';'),
            'tipo': p.get('Tipo'), 'estado': p.get('Estado'), 'incide': p.get('Incide'),
            'autores_gp': autores,
            'proponentes': proponentes,
            'numero_artigo_novo': p.get('NumeroArtigoNovo'),
            'artigos': [
                {'artigo': a.get('Artigo'), 'titulo': a.get('Titulo'), 'texto': a.get('Texto'), 'estado': a.get('Estado')}
                for a in _as_list((p.get('Iniciativas_Artigos') or {}).get('Iniciativa_Artigo'))
            ],
            'ficheiro': p.get('Ficheiro'), 'n_votacoes': len(votacoes),
        })
        # The source has no vote ID; votes keep their source order within a proposal
        for i, v in enumerate(votacoes, start=1):
            grupos = v.get('GruposParlamentares') or {}
            nomes, votos = _as_list(grupos.get('GrupoParlamentar')), _as_list(grupos.get('Voto'))
            if len(nomes) != len(votos):
                raise TransformError(f"OE {ano} proposta {p['ID']}: {len(nomes)} parties but {len(votos)} votes")
            votos = [{'nome': n, 'voto': vo} for n, vo in zip(nomes, votos)]
            data = _oe_date(v.get('Data'))
            parsed, named = oe_parse_votos(votos, data, siglas, deputados)
            completo = v.get('ResultadoCompleto') or ''
            vot_rows.append({
                'vot_id': f"{p['ID']}_{i}", 'prop_id': p['ID'], 'numero': p['Numero'], 'ano': ano,
                'legislatura': legislatura, 'titulo': p.get('Titulo'), 'tipo': p.get('Tipo'),
                'autores_gp': autores, 'data': data, 'resultado': v.get('Resultado'),
                'resultado_completo': v.get('ResultadoCompleto'),
                'descricao': '; '.join(_as_list((v.get('Descricoes') or {}).get('Descricao'))) or None,
                'subdescricao': v.get('SubDescricao'),
                # "Assunção pelo Plenário das votações em Comissão" is plenary, so check that first
                'tipo_reuniao': 'RP' if 'Plenário' in completo else 'COM' if 'Comissão' in completo else None,
                'unanime': 'unanime' if 'Unanimidade' in completo + (v.get('Resultado') or '') else None,
                'votos': votos, 'detalhe_parsed': parsed if votos else None,
                'detalhe_deputados': named, 'source': 'oe',
            })
    return prop_rows, vot_rows


def _write_parquet(conn: duckdb.DuckDBPyConnection, rows: list[dict], columns: dict, order_by: str, path: Path) -> None:
    """Write rows to Parquet with an explicit schema (via a temporary NDJSON file)."""
    ndjson = path.with_suffix('.ndjson.tmp')
    try:
        ndjson.write_text(''.join(json.dumps(r, default=str, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
        conn.execute(f"""
            COPY (
                SELECT * FROM read_json('{ndjson}', format='newline_delimited', columns={columns!r})
                ORDER BY {order_by}
            ) TO '{path}' (
                FORMAT PARQUET,
                COMPRESSION '{config.PARQUET_COMPRESSION}',
                ROW_GROUP_SIZE {config.PARQUET_ROW_GROUP_SIZE}
            )
        """)
    finally:
        ndjson.unlink(missing_ok=True)


def transform_oe(ano: int) -> tuple[Path, Path] | None:
    """
    Transform bronze/oe_{ano}.json into silver oe_propostas_{ano}.parquet and oe_votacoes_{ano}.parquet.
    Needs the partidos and deputados silver files of the budget's legislatura.

    Returns:
        (propostas path, votacoes path), or None if the bronze file is missing
    """
    bronze = config.BRONZE_DIR / f"oe_{ano}.json"
    if not bronze.exists():
        logger.warning("oe_file_not_found", path=str(bronze))
        return None

    legislatura = config.OE[ano]["legislatura"]
    leg = legislatura.lower()
    logger.info("transforming_oe", ano=ano, legislatura=legislatura)
    try:
        conn = duckdb.connect()
        conn.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={config.DUCKDB_THREADS}")

        siglas = {nome.lower(): sigla for sigla, nome in conn.execute(
            f"SELECT gp_sigla, gp_nome FROM '{config.SILVER_DIR}/partidos_{leg}.parquet'").fetchall()}
        deputados = {
            nome.lower(): (nome, [(h['gp_sigla'], h['gp_dt_inicio'], h['gp_dt_fim']) for h in historico or []])
            for nome, historico in conn.execute(
                f"SELECT nome_parlamentar, partido_historico FROM '{config.SILVER_DIR}/deputados_{leg}.parquet'"
            ).fetchall()
        }

        propostas = json.loads(bronze.read_text(encoding='utf-8-sig'))['PropostaDeAlteracao']
        prop_rows, vot_rows = oe_rows(propostas, ano, legislatura, siglas, deputados)

        propostas_path = config.SILVER_DIR / f"oe_propostas_{ano}.parquet"
        votacoes_path = config.SILVER_DIR / f"oe_votacoes_{ano}.parquet"
        _write_parquet(conn, prop_rows, OE_PROPOSTAS_COLUMNS, "data DESC NULLS LAST, prop_id", propostas_path)
        _write_parquet(conn, vot_rows, OE_VOTACOES_COLUMNS, "data DESC NULLS LAST, vot_id", votacoes_path)

        logger.info("transform_oe_complete", ano=ano, propostas=len(prop_rows), votacoes=len(vot_rows))
        return propostas_path, votacoes_path

    except TransformError:
        raise
    except Exception as e:
        logger.error("transform_oe_error", ano=ano, error=str(e))
        raise TransformError(f"Error transforming OE {ano}: {e}")


def transform_all(
    legislatures: list[str] | None = None,
    include_info_base: bool = True,
    include_votacoes: bool = True,
    include_deputados: bool = False,
    include_circulos: bool = False,
    include_partidos: bool = False,
    include_atividades: bool = True,
    include_atividades_votacoes: bool = True,
    include_cap: bool = True,
    include_oe: bool = True,
) -> dict[str, dict[str, Path]]:
    """
    Transform multiple legislatures and their metadata.

    Args:
        legislatures: List of legislature IDs, or None for all configured
        include_info_base: Also transform InformacaoBase metadata
        include_votacoes: Also create flattened votacoes file
        include_deputados: Also create flattened deputados file
        include_circulos: Also create flattened circulos file
        include_partidos: Also create flattened partidos file
        include_atividades: Also transform Atividades data
        include_atividades_votacoes: Also create flattened atividades_votacoes file
        include_cap: Convert CAP mapping CSV → Parquet if cap_source CSV is present
        include_oe: Transform the OE budgets of each legislatura (needs its partidos and deputados)

    Returns:
        Dict mapping legislature ID to {
            "iniciativas": Path,
            "info_base": Path | None,
            "votacoes": Path | None,
            "deputados": Path | None,
            "circulos": Path | None,
            "partidos": Path | None,
            "atividades": Path | None,
            "atividades_votacoes": Path | None,
            "cap": Path | None,
        }
    """
    if legislatures is None:
        legislatures = list(config.LEGISLATURES.keys())

    results = {}
    for leg in legislatures:
        leg_results = {}

        # Transform iniciativas
        try:
            leg_results["iniciativas"] = transform_legislature(leg)
        except TransformError as e:
            logger.error("transform_iniciativas_failed", legislature=leg, error=str(e))

        # Transform info_base
        if include_info_base:
            try:
                info_base_path = transform_info_base(leg)
                if info_base_path:
                    leg_results["info_base"] = info_base_path
            except TransformError as e:
                logger.error("transform_info_base_failed", legislature=leg, error=str(e))

        # Transform votacoes (requires iniciativas to exist)
        if include_votacoes and "iniciativas" in leg_results:
            try:
                leg_results["votacoes"] = transform_votacoes(leg)
            except TransformError as e:
                logger.error("transform_votacoes_failed", legislature=leg, error=str(e))

        # Transform deputados (requires info_base to exist)
        if include_deputados and "info_base" in leg_results:
            try:
                leg_results["deputados"] = transform_deputados(leg)
            except TransformError as e:
                logger.error("transform_deputados_failed", legislature=leg, error=str(e))

        # Transform circulos (requires info_base to exist)
        if include_circulos and "info_base" in leg_results:
            try:
                leg_results["circulos"] = transform_circulos(leg)
            except TransformError as e:
                logger.error("transform_circulos_failed", legislature=leg, error=str(e))

        # Transform partidos (requires info_base to exist)
        if include_partidos and "info_base" in leg_results:
            try:
                leg_results["partidos"] = transform_partidos(leg)
            except TransformError as e:
                logger.error("transform_partidos_failed", legislature=leg, error=str(e))

        # Transform the OE budgets debated in this legislature (needs partidos and deputados)
        if include_oe:
            for ano in [a for a, oe in config.OE.items() if oe["legislatura"] == leg]:
                try:
                    paths = transform_oe(ano)
                    if paths:
                        leg_results[f"oe_propostas_{ano}"], leg_results[f"oe_votacoes_{ano}"] = paths
                except TransformError as e:
                    logger.error("transform_oe_failed", ano=ano, error=str(e))

        # Transform atividades
        if include_atividades:
            try:
                atividades_path = transform_atividades(leg)
                if atividades_path:
                    leg_results["atividades"] = atividades_path
            except TransformError as e:
                logger.error("transform_atividades_failed", legislature=leg, error=str(e))

            for name in ATIVIDADES_SECTIONS:
                try:
                    path = transform_atividades_section(leg, name)
                    if path:
                        leg_results[name] = path
                except TransformError as e:
                    logger.error("transform_atividades_section_failed", legislature=leg, section=name, error=str(e))

        # Transform atividades_votacoes (requires atividades to exist)
        if include_atividades_votacoes and "atividades" in leg_results:
            try:
                atividades_votacoes_path = transform_atividades_votacoes(leg)
                if atividades_votacoes_path:
                    leg_results["atividades_votacoes"] = atividades_votacoes_path
            except TransformError as e:
                logger.error("transform_atividades_votacoes_failed", legislature=leg, error=str(e))

        # Transform CAP mapping (optional - skipped silently if source CSV absent)
        if include_cap:
            try:
                cap_path = transform_cap(leg)
                if cap_path:
                    leg_results["cap"] = cap_path
            except TransformError as e:
                logger.error("transform_cap_failed", legislature=leg, error=str(e))

        if leg_results:
            results[leg] = leg_results

    return results


if __name__ == "__main__":
    import argparse
    import sys

    def parse_args():
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="Transform Portuguese Parliament data (JSON → Parquet)"
        )
        parser.add_argument(
            "-l", "--legislature",
            type=str,
            help="Legislature(s) to transform (e.g., L17 or L17,L16). If not specified, transforms all."
        )
        parser.add_argument(
            "--skip-info-base",
            action="store_true",
            help="Skip transforming info_base (metadata) files"
        )
        parser.add_argument(
            "--skip-votacoes",
            action="store_true",
            help="Skip transforming votacoes (votes from iniciativas)"
        )
        parser.add_argument(
            "--skip-deputados",
            action="store_true",
            help="Skip transforming deputados (deputies)"
        )
        parser.add_argument(
            "--skip-circulos",
            action="store_true",
            help="Skip transforming circulos (electoral circles)"
        )
        parser.add_argument(
            "--skip-partidos",
            action="store_true",
            help="Skip transforming partidos (parties)"
        )
        parser.add_argument(
            "--skip-atividades",
            action="store_true",
            help="Skip transforming atividades (activities)"
        )
        parser.add_argument(
            "--skip-atividades-votacoes",
            action="store_true",
            help="Skip transforming atividades votacoes (activity votes)"
        )
        parser.add_argument(
            "--skip-oe",
            action="store_true",
            help="Skip transforming Orçamento do Estado (propostas de alteração)"
        )
        parser.add_argument(
            "--skip-cap",
            action="store_true",
            help="Skip converting CAP mapping CSV to Parquet"
        )
        return parser.parse_args()

    args = parse_args()

    # Parse legislature list
    legislatures = None
    if args.legislature:
        legislatures = [leg.strip() for leg in args.legislature.split(",")]

        # Validate legislature codes
        invalid = [leg for leg in legislatures if leg not in config.LEGISLATURES]
        if invalid:
            available = ", ".join(config.LEGISLATURES.keys())
            print(f"Error: Unknown legislature(s): {', '.join(invalid)}", file=sys.stderr)
            print(f"Available legislatures: {available}", file=sys.stderr)
            sys.exit(1)

    # Display what we're transforming
    if legislatures:
        print(f"==> Transforming legislatures: {', '.join(legislatures)}")
    else:
        print("==> Transforming all legislatures")

    # Call transform_all with parsed arguments
    results = transform_all(
        legislatures=legislatures,
        include_info_base=not args.skip_info_base,
        include_votacoes=not args.skip_votacoes,
        include_deputados=not args.skip_deputados,
        include_circulos=not args.skip_circulos,
        include_partidos=not args.skip_partidos,
        include_atividades=not args.skip_atividades,
        include_atividades_votacoes=not args.skip_atividades_votacoes,
        include_cap=not args.skip_cap,
        include_oe=not args.skip_oe,
    )

    print(f"==> Transform completed. Results: {len(results)} legislatures processed")
    for leg, paths in results.items():
        print(f"  - {leg}: {list(paths.keys())}")
