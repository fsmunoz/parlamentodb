"""
FastAPI dependencies for database connections and shared resources.

Frederico Muñoz <fsmunoz@gmail.com>
"""

import duckdb
from pathlib import Path
from typing import Generator

from app.config import settings

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

        # info_base might not exist for all legislatures (WIP)
        info_base_files = list(data_dir.glob("info_base_*.parquet"))
        if info_base_files:
            conn.execute(f"""
                CREATE VIEW info_base AS
                SELECT * FROM read_parquet('{data_dir}/info_base_*.parquet')
            """)

        # deputados, circulos, partidos
        deputados_files = list(data_dir.glob("deputados_*.parquet"))
        if deputados_files:
            conn.execute(f"""
                CREATE VIEW deputados AS
                SELECT * FROM read_parquet('{data_dir}/deputados_*.parquet')
            """)

        circulos_files = list(data_dir.glob("circulos_*.parquet"))
        if circulos_files:
            conn.execute(f"""
                CREATE VIEW circulos AS
                SELECT * FROM read_parquet('{data_dir}/circulos_*.parquet')
            """)

        partidos_files = list(data_dir.glob("partidos_*.parquet"))
        if partidos_files:
            conn.execute(f"""
                CREATE VIEW partidos AS
                SELECT * FROM read_parquet('{data_dir}/partidos_*.parquet')
            """)

        # atividades and atividades_votacoes
        # Note: Use specific patterns to avoid schema mismatch between atividades and atividades_votacoes
        atividades_files = list(data_dir.glob("atividades_l*.parquet"))
        if atividades_files:
            conn.execute(f"""
                CREATE VIEW atividades AS
                SELECT * FROM read_parquet('{data_dir}/atividades_l*.parquet')
            """)

        atividades_votacoes_files = list(data_dir.glob("atividades_votacoes_*.parquet"))
        if atividades_votacoes_files:
            conn.execute(f"""
                CREATE VIEW atividades_votacoes AS
                SELECT * FROM read_parquet('{data_dir}/atividades_votacoes_*.parquet')
            """)

        yield conn

    finally:
        conn.close()
