"""
Statistics endpoints.

Frederico Muñoz <fsmunoz@gmail.com>

Provides aggregated statistics for each legislature,
computed on-demand from silver layer Parquet files using DuckDB.

This helps in getting the 'big numbers' for things that aren't easily done without
many calls, like getting the sum of votes from parties in relation to others.

"""

from fastapi import APIRouter, Depends, Query, HTTPException
import duckdb
import structlog

from app.config import settings
from app.dependencies import get_db
from app.models.stats import (
    StatsResponse,
    LegislaturaStats,
    FaseOutcome,
    PartyInitiativeStats,
    PartyFaseOutcome,
    VotesByEventType,
    PartyVoteTypeStats,
    AtividadesByTipo,
    AtividadesVotesByTipo,
    VoteSourceBreakdown,
)
from app.models.common import APIMeta
from app.models.validators import validate_legislatura
from app.queries.stats import (
    get_initiatives_by_fase,
    get_initiatives_by_party,
    get_votes_by_event_type,
    get_votes_by_party_and_type,
)

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])
logger = structlog.get_logger()


@router.get("/", response_model=StatsResponse)
def get_legislature_stats(
    legislatura: str = Query(..., description="Legislature identifier (L15, L16, L17)"),
    db: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Get important statistics for a legislature.

    Returns 7 fundamental aggregations computed on-demand:

    1. **Initiatives by fase**: Total initiatives grouped by phase and outcome
       - Shows vote outcomes (Aprovado/Rejeitado) per legislative phase
       - Includes both vote count and distinct initiative count

    2. **Initiatives by party**: Party-level initiative authorship with outcomes
       - Total initiatives authored by each parliamentary group
       - Breakdown of outcomes by phase for each party's initiatives
       - Reuses the same logic as `/partidos/{gp_sigla}/iniciativas` endpoint

    3. **Votes by event type**: Vote counts grouped by event phase
       - Simple aggregation of voting sessions by their type/phase

    4. **Votes by party and type**: Detailed voting behavior by party
       - Grouped first by party, then by vote type
       - Vote types: A Favor (For), Contra (Against), Abstenção (Abstention)

    5. **Atividades by type**: Activity counts grouped by type (NEW)
       - Count of atividades (VOT, MOC, PRG, etc.)

    6. **Atividades votes by type**: Vote counts from atividades (NEW)
       - How many votes each activity type generated

    7. **Vote source breakdown**: Total votes by source (NEW)
       - Breakdown of all votes: iniciativas vs atividades
       - Enables clients to see complete parliamentary voting coverage

    These have been chosen while developing clients, since getting this information
    would require many API calls.

    Uses on-demand SQL aggregation using DuckDB on Parquet files (performance is great).

    """
    try:
        # Validate input
        legislatura = validate_legislatura(legislatura)

        logger.info("stats_query_started", legislatura=legislatura)

        # Execute all 4 aggregations
        # Aggregation #1: Initiatives by fase outcome
        agg1_results = get_initiatives_by_fase(db, legislatura)
        initiatives_by_fase = [
            FaseOutcome(
                fase=row[0],
                resultado=row[1],
                vote_count=row[2],
                initiative_count=row[3]
            )
            for row in agg1_results
        ]

        # Aggregation #2: Initiatives by party with fase outcomes
        agg2_results = get_initiatives_by_party(db, legislatura)
        initiatives_by_party = [
            PartyInitiativeStats(
                party=party_data["party"],
                total_initiatives=party_data["total_initiatives"],
                fase_outcomes=[
                    PartyFaseOutcome(
                        fase=outcome["fase"],
                        resultado=outcome["resultado"],
                        count=outcome["count"]
                    )
                    for outcome in party_data["fase_outcomes"]
                ]
            )
            for party_data in agg2_results
        ]

        # Aggregation #3: Votes by event type
        agg3_results = get_votes_by_event_type(db, legislatura)
        votes_by_event_type = [
            VotesByEventType(
                fase=row[0],
                vote_count=row[1]
            )
            for row in agg3_results
        ]

        # Aggregation #4: Votes by party and type
        agg4_results = get_votes_by_party_and_type(db, legislatura)
        votes_by_party_and_type = [
            PartyVoteTypeStats(
                party=row[0],
                vote_type=row[1],
                vote_count=row[2]
            )
            for row in agg4_results
        ]

        # Aggregation #5: Atividades by tipo (if atividades exist)
        atividades_by_tipo = []
        try:
            agg5_query = """
                SELECT ativ_tipo, COUNT(*) as count
                FROM atividades
                WHERE legislatura = $legislatura
                  AND ativ_tipo IS NOT NULL
                GROUP BY ativ_tipo
                ORDER BY count DESC
            """
            agg5_results = db.execute(agg5_query, {"legislatura": legislatura}).fetchall()
            atividades_by_tipo = [
                AtividadesByTipo(tipo=row[0], count=row[1])
                for row in agg5_results
            ]
        except Exception as e:
            logger.warning("atividades_by_tipo_failed", error=str(e))

        # Aggregation #6: Atividades votes by tipo (if atividades_votacoes exist)
        atividades_votes_by_tipo = []
        try:
            agg6_query = """
                SELECT tipo, COUNT(*) as vote_count
                FROM atividades_votacoes
                WHERE legislatura = $legislatura
                  AND tipo IS NOT NULL
                GROUP BY tipo
                ORDER BY vote_count DESC
            """
            agg6_results = db.execute(agg6_query, {"legislatura": legislatura}).fetchall()
            atividades_votes_by_tipo = [
                AtividadesVotesByTipo(tipo=row[0], vote_count=row[1])
                for row in agg6_results
            ]
        except Exception as e:
            logger.warning("atividades_votes_by_tipo_failed", error=str(e))

        # Aggregation #7: Vote source breakdown
        vote_source_breakdown = None
        try:
            agg7_query = """
                SELECT
                    (SELECT COUNT(*) FROM votacoes WHERE legislatura = $legislatura) as iniciativas,
                    (SELECT COALESCE(COUNT(*), 0) FROM atividades_votacoes WHERE legislatura = $legislatura) as atividades
            """
            agg7_result = db.execute(agg7_query, {"legislatura": legislatura}).fetchone()
            if agg7_result:
                iniciativas_count = agg7_result[0]
                atividades_count = agg7_result[1]
                vote_source_breakdown = VoteSourceBreakdown(
                    iniciativas=iniciativas_count,
                    atividades=atividades_count,
                    total=iniciativas_count + atividades_count
                )
        except Exception as e:
            logger.warning("vote_source_breakdown_failed", error=str(e))

        # Construct response
        stats = LegislaturaStats(
            legislatura=legislatura,
            initiatives_by_fase=initiatives_by_fase,
            initiatives_by_party=initiatives_by_party,
            votes_by_event_type=votes_by_event_type,
            votes_by_party_and_type=votes_by_party_and_type,
            atividades_by_tipo=atividades_by_tipo,
            atividades_votes_by_tipo=atividades_votes_by_tipo,
            vote_source_breakdown=vote_source_breakdown
        )

        logger.info(
            "stats_query_completed",
            legislatura=legislatura,
            initiatives_by_fase_count=len(initiatives_by_fase),
            parties_count=len(initiatives_by_party),
            event_types_count=len(votes_by_event_type),
            party_vote_records_count=len(votes_by_party_and_type),
            atividades_types_count=len(atividades_by_tipo),
            atividades_votes_types_count=len(atividades_votes_by_tipo),
            vote_source_breakdown=vote_source_breakdown is not None
        )

        return StatsResponse(
            data=stats,
            meta=APIMeta(version=settings.API_VERSION)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("stats_query_error", legislatura=legislatura, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving statistics"
        )
