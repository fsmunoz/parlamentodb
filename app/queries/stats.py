"""Statistical aggregation queries for parliamentary data.

Frederico Muñoz <fsmunoz@gmail.com>

These functions compute statistics on-demand from silver layer Parquet
files. DuckDB's columnar query performance makes real-time aggregation
practical, and hopefully speedy enough.

Initial idea was to create this in a "gold" layer, with Parquet files
containing the computed results; the transformation code was however
much more complex (or at least longer) than using DuckDB queries, so
it's implemented at the "silver" lever, and made available in a new
/stats endpoint.

"""

import duckdb


def get_initiatives_by_fase(conn: duckdb.DuckDBPyConnection, legislatura: str) -> list[tuple]:
    """
    Aggregation #1: Total initiatives + vote outcomes by Fase.

    Returns initiatives grouped by fase and resultado (vote outcome).
    Each row contains: fase, resultado, vote_count, initiative_count.

    Args:
        conn: DuckDB connection
        legislatura: Legislature identifier (L15, L16, L17)

    Returns:
        List of tuples: (fase, resultado, vote_count, initiative_count)
    """
    query = """
    SELECT
        fase,
        resultado,
        COUNT(*) as vote_count,
        COUNT(DISTINCT ini_id) as initiative_count
    FROM votacoes
    WHERE legislatura = $legislatura
      AND fase IS NOT NULL
      AND resultado IS NOT NULL
    GROUP BY fase, resultado
    ORDER BY fase, resultado
    """
    return conn.execute(query, {"legislatura": legislatura}).fetchall()


def get_initiatives_by_party(conn: duckdb.DuckDBPyConnection, legislatura: str) -> list[dict]:
    """
    Aggregation #2: Total initiatives by party + outcomes by Fase for each.

    Reuses the same logic as /partidos/{gp_sigla}/iniciativas endpoint.
    Flattens ini_autor_grupos_parlamentares array and groups by party.
    Then joins with votacoes to get outcome breakdowns per party.

    Args:
        conn: DuckDB connection
        legislatura: Legislature identifier (L15, L16, L17)

    Returns:
        List of dicts with structure:
        {
            "party": "PS",
            "total_initiatives": 123,
            "fase_outcomes": [
                {"fase": "Votação na generalidade", "resultado": "Aprovado", "count": 45},
                ...
            ]
        }
    """
    # First get party initiative counts
    party_counts_query = """
    WITH flattened AS (
        SELECT
            ini_id,
            UNNEST(list_transform(ini_autor_grupos_parlamentares, x -> x.GP)) as party
        FROM iniciativas
        WHERE legislatura = $legislatura
          AND ini_autor_grupos_parlamentares IS NOT NULL
          AND length(ini_autor_grupos_parlamentares) > 0
    )
    SELECT
        party,
        COUNT(DISTINCT ini_id) as total_initiatives
    FROM flattened
    GROUP BY party
    ORDER BY total_initiatives DESC
    """

    parties_data = conn.execute(party_counts_query, {"legislatura": legislatura}).fetchall()

    # Then get fase breakdown per party
    fase_breakdown_query = """
    WITH flattened_initiatives AS (
        SELECT
            i.ini_id,
            UNNEST(list_transform(i.ini_autor_grupos_parlamentares, x -> x.GP)) as party
        FROM iniciativas i
        WHERE i.legislatura = $legislatura
          AND i.ini_autor_grupos_parlamentares IS NOT NULL
          AND length(i.ini_autor_grupos_parlamentares) > 0
    )
    SELECT
        f.party,
        v.fase,
        v.resultado,
        COUNT(*) as vote_count
    FROM flattened_initiatives f
    JOIN votacoes v ON f.ini_id = v.ini_id
    WHERE v.legislatura = $legislatura
      AND v.fase IS NOT NULL
      AND v.resultado IS NOT NULL
    GROUP BY f.party, v.fase, v.resultado
    ORDER BY f.party, v.fase, v.resultado
    """

    fase_data = conn.execute(fase_breakdown_query, {"legislatura": legislatura}).fetchall()

    # Organize data structure: party -> list of fase outcomes
    party_fase_map: dict[str, list[dict]] = {}
    for party, fase, resultado, count in fase_data:
        if party not in party_fase_map:
            party_fase_map[party] = []
        party_fase_map[party].append({
            "fase": fase,
            "resultado": resultado,
            "count": count
        })

    # Combine with party totals
    result = []
    for party, total in parties_data:
        result.append({
            "party": party,
            "total_initiatives": total,
            "fase_outcomes": party_fase_map.get(party, [])
        })

    return result


def get_votes_by_event_type(conn: duckdb.DuckDBPyConnection, legislatura: str) -> list[tuple]:
    """
    Aggregation #3: Total votes by Event type (fase).

    Simple GROUP BY to count voting sessions by their phase/event type.

    Args:
        conn: DuckDB connection
        legislatura: Legislature identifier (L15, L16, L17)

    Returns:
        List of tuples: (fase, vote_count)
    """
    query = """
    SELECT
        fase,
        COUNT(*) as vote_count
    FROM votacoes
    WHERE legislatura = $legislatura
      AND fase IS NOT NULL
    GROUP BY fase
    ORDER BY vote_count DESC
    """
    return conn.execute(query, {"legislatura": legislatura}).fetchall()


def get_votes_by_party_and_type(conn: duckdb.DuckDBPyConnection, legislatura: str) -> list[tuple]:
    """
    Aggregation #4: Total votes by party and vote type.

    Most complex aggregation - flattens detalhe_parsed struct which contains
    arrays of parties for each vote type (a_favor, contra, abstencao).
    Uses UNION ALL to combine all three vote types.

    Args:
        conn: DuckDB connection
        legislatura: Legislature identifier (L15, L16, L17)

    Returns:
        List of tuples: (party, vote_type, vote_count)
    """
    query = """
    WITH flattened AS (
        SELECT
            vot_id,
            UNNEST(detalhe_parsed.a_favor) as party,
            'A Favor' as vote_type
        FROM votacoes
        WHERE legislatura = $legislatura
          AND detalhe_parsed IS NOT NULL
          AND detalhe_parsed.a_favor IS NOT NULL
          AND length(detalhe_parsed.a_favor) > 0
        UNION ALL
        SELECT
            vot_id,
            UNNEST(detalhe_parsed.contra) as party,
            'Contra' as vote_type
        FROM votacoes
        WHERE legislatura = $legislatura
          AND detalhe_parsed IS NOT NULL
          AND detalhe_parsed.contra IS NOT NULL
          AND length(detalhe_parsed.contra) > 0
        UNION ALL
        SELECT
            vot_id,
            UNNEST(detalhe_parsed.abstencao) as party,
            'Abstenção' as vote_type
        FROM votacoes
        WHERE legislatura = $legislatura
          AND detalhe_parsed IS NOT NULL
          AND detalhe_parsed.abstencao IS NOT NULL
          AND length(detalhe_parsed.abstencao) > 0
    )
    SELECT
        party,
        vote_type,
        COUNT(*) as vote_count
    FROM flattened
    WHERE party IS NOT NULL
    GROUP BY party, vote_type
    ORDER BY party, vote_type
    """
    return conn.execute(query, {"legislatura": legislatura}).fetchall()
