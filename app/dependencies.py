"""
FastAPI dependencies for database connections and shared resources.

Frederico Muñoz <fsmunoz@gmail.com>
"""

import duckdb
from pathlib import Path
from typing import Generator

from app.config import settings

# view name -> Parquet glob (relative to DATA_DIR)
OPTIONAL_VIEWS = {
    "info_base": "info_base_*.parquet",
    "deputados": "deputados_*.parquet",
    "circulos": "circulos_*.parquet",
    "partidos": "partidos_*.parquet",
    "atividades": "atividades_l*.parquet",
    "atividades_votacoes": "atividades_votacoes_*.parquet",
    "debates": "debates_*.parquet",
    "audicoes": "audicoes_*.parquet",
    "audiencias": "audiencias_*.parquet",
    "cap": "cap_l*.parquet",
}


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Create DuckDB connection with Parquet files registered as views.
   
    This dependency provides a fresh DuckDB connection per request; the connection reads directly
    from Parquet files in the data directory.

    Provides:
        DuckDB connection with iniciativas, votacoes, and info_base views
    """
    # Create in-memory connection
    conn = duckdb.connect(database=':memory:', read_only=False)

    try:
        # Configure DuckDB
        conn.execute(f"SET memory_limit='{settings.DUCKDB_MEMORY_LIMIT}'")
        conn.execute(f"SET threads={settings.DUCKDB_THREADS}")

        # Set query timeout (may not be supported in all DuckDB versions)
        try:
            conn.execute(f"SET query_timeout='{settings.DUCKDB_QUERY_TIMEOUT}'")
        except Exception:
            # Query timeout not supported in this DuckDB version, continue without it
            pass

        data_dir = Path(settings.DATA_DIR)

        # Register Parquet files as views
        # DuckDB can read multiple files with glob patterns, so we load them all
        conn.execute(f"""
            CREATE VIEW iniciativas AS
            SELECT * FROM read_parquet('{data_dir}/iniciativas_*.parquet')
        """)

        conn.execute(f"""
            CREATE VIEW votacoes AS
            SELECT * FROM read_parquet('{data_dir}/votacoes_*.parquet')
        """)

        # Optional views, created only when their files exist.
        # Note: atividades_l* (not atividades_*) avoids matching atividades_votacoes files.
        # cap is present only if classify.py has been run and imported via ETL.
        for view, pattern in OPTIONAL_VIEWS.items():
            if any(data_dir.glob(pattern)):
                conn.execute(f"""
                    CREATE VIEW {view} AS
                    SELECT * FROM read_parquet('{data_dir}/{pattern}')
                """)

        yield conn

    finally:
        conn.close()
