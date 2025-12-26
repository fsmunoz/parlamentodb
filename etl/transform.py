"""Data transformation module for Portuguese Parliament ETL Pipeline.

Frederico Muñoz <fsmunoz@gmail.com>

Transforms JSON to Parquet using DuckDB with complete data preservation. All nested structures are
preserved as STRUCT/LIST types, so they can be used and filtered upon.

"""

import duckdb
import structlog
from pathlib import Path

import config
from etl.schema import get_select_clause, get_atividades_select_clause

logger = structlog.get_logger()

# Add a custom exception class for transformation errors.
class TransformError(Exception):
    """Raised when transformation fails."""
    pass


def parse_detalhe(detalhe: str) -> dict:
    """Parse HTML voting details into structured dict.

    Converts free-form HTML text like:
        "A Favor: <I>PSD</I>, <I>CDS-PP</I><BR>Contra:<I>CH</I>"

    Into structured dict:
        {
            "a_favor": ["PSD", "CDS-PP"],
            "contra": ["CH"],
            "abstencao": [],
            "ausencia": []
        }

    IMPORTANT: Ninsc members are preserved with full names (e.g., "John Doe (Ninsc)") because they
    represent different political positions and must not be aggregated: a Ninsc MP can be a person
    that was elected by a party alone (only >1 MPs constitute a parliamentary group) or an MP that
    left the party that elected them. Either way, they should be treated as "parties" in themselves.

    Args:
        detalhe: HTML-formatted voting details string

    Returns:
        Dict with vote positions, or None if detalhe is empty

    """
    if not detalhe or len(detalhe.strip()) == 0:
        return None

    import re

    # Split by <BR> and process each section. This is based on the proc-parl-pt code, with some
    # simplifications
    
    sections = detalhe.split('<BR>')
    result = {
        'a_favor': [],
        'contra': [],
        'abstencao': [],
        'ausencia': []
    }

    for section in sections:
        if ':' not in section:
            continue

        # Extract vote type (A Favor, Contra, etc.)
        vote_type, parties_html = section.split(':', 1)
        vote_type_key = vote_type.strip().lower().replace(' ', '_')
        vote_type_key = vote_type_key.replace('ção', 'cao')  # normalize accents

        # Remove HTML tags
        parties_str = re.sub(r'</?I>', '', parties_html)

        # Split by comma
        party_list = [p.strip() for p in parties_str.split(',')]

        # Filter logic:
        # - Keep: Party codes (PS, PSD, etc.) and Ninsc members with full names
        # - Skip: Aggregates (6-PSD), individual party-affiliated MPs, empty strings
        clean_parties = []
        for p in party_list:
            if not p:
                continue
            # Skip aggregates like "6-PSD"
            if re.match(r'^\d+-', p):
                continue
            # CRITICAL: Keep Ninsc members with full names (e.g., "António Maló (Ninsc)")
            # They represent different political positions and must not be aggregated
            if '(Ninsc)' in p:
                clean_parties.append(p)
                continue
            # Skip individual party-affiliated MPs like "João Silva (PSD)"
            # (aggregate them to party level)
            if re.match(r'.+\(.+\)$', p):
                continue
            # Skip numeric-only
            if re.match(r'^\d+$', p):
                continue
            clean_parties.append(p)

        # Map to result dict
        if vote_type_key in result:
            result[vote_type_key] = clean_parties

    return result


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

    Extracts all votes from iniciativas.ini_eventos.Votacao and creates
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

        # Register parse_detalhe UDF for parsing voting details Using native Python UDF, DuckDB will
        # convert dict to STRUCT. This is likely possible in SQL, but doing it with a UDF allows me
        # to reuse the existing code from proc_parl_pt, and it's more natural (check the SQL that
        # flattens things just after this one...)
        conn.create_function(
            "parse_detalhe",
            parse_detalhe,
            parameters=[duckdb.string_type()],
            return_type=duckdb.struct_type({
                'a_favor': duckdb.list_type(duckdb.string_type()),
                'contra': duckdb.list_type(duckdb.string_type()),
                'abstencao': duckdb.list_type(duckdb.string_type()),
                'ausencia': duckdb.list_type(duckdb.string_type())
            })
        )

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
                        UNNEST(evento.Votacao) as vot
                    FROM all_events
                    WHERE evento.Votacao IS NOT NULL
                      AND length(evento.Votacao) > 0
                )
                SELECT
                    vot.id as vot_id,
                    ini_id,
                    ini_nr,
                    legislatura,
                    ini_titulo,
                    ini_tipo,
                    fase,
                    data_fase,
                    vot.data as data,
                    vot.resultado,
                    vot.descricao,
                    vot.reuniao,
                    vot.tipoReuniao as tipo_reuniao,
                    vot.unanime,
                    vot.ausencias,
                    vot.detalhe,
                    parse_detalhe(vot.detalhe) as detalhe_parsed,
                    length(COALESCE(vot.detalhe, '')) >= 1000 as is_nominal
                FROM flattened_votes
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

        # Register parse_detalhe UDF (reuse from votacoes)
        conn.create_function(
            "parse_detalhe",
            parse_detalhe,
            parameters=[duckdb.string_type()],
            return_type=duckdb.struct_type({
                'a_favor': duckdb.list_type(duckdb.string_type()),
                'contra': duckdb.list_type(duckdb.string_type()),
                'abstencao': duckdb.list_type(duckdb.string_type()),
                'ausencia': duckdb.list_type(duckdb.string_type())
            })
        )

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
                    parse_detalhe(vot.detalhe) as detalhe_parsed,
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


def transform_all(
    legislatures: list[str] | None = None,
    include_info_base: bool = True,
    include_votacoes: bool = True,
    include_deputados: bool = False,
    include_circulos: bool = False,
    include_partidos: bool = False,
    include_atividades: bool = True,
    include_atividades_votacoes: bool = True
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

    Returns:
        Dict mapping legislature ID to {
            "iniciativas": Path,
            "info_base": Path | None,
            "votacoes": Path | None,
            "deputados": Path | None,
            "circulos": Path | None,
            "partidos": Path | None,
            "atividades": Path | None,
            "atividades_votacoes": Path | None
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

        # Transform atividades
        if include_atividades:
            try:
                atividades_path = transform_atividades(leg)
                if atividades_path:
                    leg_results["atividades"] = atividades_path
            except TransformError as e:
                logger.error("transform_atividades_failed", legislature=leg, error=str(e))

        # Transform atividades_votacoes (requires atividades to exist)
        if include_atividades_votacoes and "atividades" in leg_results:
            try:
                atividades_votacoes_path = transform_atividades_votacoes(leg)
                if atividades_votacoes_path:
                    leg_results["atividades_votacoes"] = atividades_votacoes_path
            except TransformError as e:
                logger.error("transform_atividades_votacoes_failed", legislature=leg, error=str(e))

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
        include_atividades_votacoes=not args.skip_atividades_votacoes
    )

    print(f"==> Transform completed. Results: {len(results)} legislatures processed")
    for leg, paths in results.items():
        print(f"  - {leg}: {list(paths.keys())}")
