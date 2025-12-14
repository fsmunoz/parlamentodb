"""Party-related aggregation queries.

Frederico Muñoz <fsmunoz@gmail.com>

Query functions for party-specific statistics and aggregations.
"""

import duckdb


def get_party_vote_support(conn: duckdb.DuckDBPyConnection, gp_sigla: str, legislatura: str) -> list[tuple]:
    """
    Get aggregated vote counts by parties on initiatives authored by a specific party.

    Shows how other parties voted on initiatives from the focus party,
    aggregated by fase (legislative phase).

    Args:
        conn: DuckDB connection
        gp_sigla: Parliamentary group abbreviation (focus party whose initiatives are analyzed)
        legislatura: Legislature identifier (L15, L16, L17)

    Returns:
        List of tuples: (fase, party, a_favor_count, contra_count, abstencao_count)
    """
    query = """
    WITH party_initiatives AS (
        -- Step 1: Get all initiatives authored by the focus party
        SELECT DISTINCT ini_id
        FROM iniciativas
        WHERE legislatura = $legislatura
          AND list_contains(
              list_transform(ini_autor_grupos_parlamentares, x -> x.GP),
              $gp_sigla
          )
    ),
    vote_details AS (
        -- Step 2: Get voting details for those initiatives
        SELECT
            v.fase,
            v.detalhe_parsed
        FROM votacoes v
        JOIN party_initiatives pi ON v.ini_id = pi.ini_id
        WHERE v.legislatura = $legislatura
          AND v.fase IS NOT NULL
          AND v.detalhe_parsed IS NOT NULL
    ),
    flattened_votes AS (
        -- Step 3: Flatten vote types
        SELECT
            fase,
            UNNEST(detalhe_parsed.a_favor) as party,
            'a_favor' as vote_type
        FROM vote_details
        WHERE detalhe_parsed.a_favor IS NOT NULL
          AND length(detalhe_parsed.a_favor) > 0
        UNION ALL
        SELECT
            fase,
            UNNEST(detalhe_parsed.contra) as party,
            'contra' as vote_type
        FROM vote_details
        WHERE detalhe_parsed.contra IS NOT NULL
          AND length(detalhe_parsed.contra) > 0
        UNION ALL
        SELECT
            fase,
            UNNEST(detalhe_parsed.abstencao) as party,
            'abstencao' as vote_type
        FROM vote_details
        WHERE detalhe_parsed.abstencao IS NOT NULL
          AND length(detalhe_parsed.abstencao) > 0
    )
    -- Step 4: Aggregate by fase and party, pivot vote types into columns
    SELECT
        fase,
        party,
        SUM(CASE WHEN vote_type = 'a_favor' THEN 1 ELSE 0 END) as a_favor_count,
        SUM(CASE WHEN vote_type = 'contra' THEN 1 ELSE 0 END) as contra_count,
        SUM(CASE WHEN vote_type = 'abstencao' THEN 1 ELSE 0 END) as abstencao_count
    FROM flattened_votes
    WHERE party IS NOT NULL
    GROUP BY fase, party
    ORDER BY fase, party
    """
    return conn.execute(query, {"gp_sigla": gp_sigla.upper(), "legislatura": legislatura}).fetchall()
