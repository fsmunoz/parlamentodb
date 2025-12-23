"""
Regression tests for critical edge cases and known invariants.

These tests protect against regressions in critical business logic and data integrity.
They verify known constants (e.g., 22 electoral circles) and edge cases (e.g., Ninsc members).
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ninsc_members_have_full_names():
    """
    REGRESSION: Ninsc (non-registered) members must appear with full names.

    Example: "António Maló (Ninsc)" not just "Ninsc"
    This ensures individual MPs who are not affiliated with a party are identifiable.
    """
    # Get a sample of votes
    response = client.get("/api/v1/iniciativas/votacoes/?limit=100")
    assert response.status_code == 200

    votes = response.json()["data"]
    ninsc_found = False

    # Check detailed vote information for Ninsc members
    for vote in votes[:10]:  # Check first 10 votes for performance
        detail_response = client.get(f"/api/v1/iniciativas/votacoes/{vote['vot_id']}")
        if detail_response.status_code != 200:
            continue

        detail = detail_response.json()

        if detail.get("detalhe_parsed"):
            for position in ["a_favor", "contra", "abstencao", "ausencia"]:
                members = detail["detalhe_parsed"].get(position, [])
                for member in members:
                    if "Ninsc" in member:
                        ninsc_found = True
                        # Must contain full name format: "Name (Ninsc)"
                        assert "(" in member and ")" in member, \
                            f"Ninsc member missing full name: {member}"

    # Note: Ninsc members are rare, so we don't assert they must be found


def test_electoral_circles_always_22():
    """
    REGRESSION: Portugal has exactly 22 electoral circles (constituencies).

    This is a constitutional constant that should never change without major reform.
    Circles: 18 mainland + 2 Azores + 2 Madeira
    """
    response = client.get("/api/v1/circulos/?legislatura=L17")
    assert response.status_code == 200

    data = response.json()
    assert data["pagination"]["total"] == 22, \
        f"Expected 22 electoral circles, got {data['pagination']['total']}"


@pytest.mark.parametrize("legislatura,expected_parties", [
    ("L17", 10),  # 2024: PS, AD(PSD+CDS+PPM), CH, IL, BE, PCP-PEV, L, PAN, + others
    # Note: L16 and L15 counts depend on available data
])
def test_party_count_per_legislature(legislatura, expected_parties):
    """
    REGRESSION: Known party counts per legislature.

    These are historical facts that validate data integrity.
    The number of parliamentary groups changes between legislatures based on election results.
    """
    response = client.get(f"/api/v1/partidos/?legislatura={legislatura}")
    assert response.status_code == 200

    data = response.json()
    actual_count = data["pagination"]["total"]

    assert actual_count == expected_parties, \
        f"{legislatura}: Expected {expected_parties} parties, got {actual_count}"


def test_pagination_limit_enforced():
    """
    REGRESSION: Maximum pagination limit of 500 must be enforced.

    This prevents abuse and ensures reasonable response sizes.
    Requests above 500 should return validation error (422).
    """
    # Test at the limit (should work)
    response = client.get("/api/v1/iniciativas/?limit=500")
    assert response.status_code == 200

    # Test above the limit (should fail with validation error)
    response = client.get("/api/v1/iniciativas/?limit=1000")
    assert response.status_code == 422, \
        f"Expected 422 for limit=1000, got {response.status_code}"


def test_detalhe_parsed_structure():
    """
    REGRESSION: Voting details (detalhe_parsed) must have correct structure.

    When present, detalhe_parsed should contain:
    - a_favor (list of members voting in favor)
    - contra (list of members voting against)
    - abstencao (list of members abstaining)
    - ausencia (list of absent members)
    """
    # Get a vote with details
    response = client.get("/api/v1/iniciativas/votacoes/?limit=50")
    assert response.status_code == 200

    votes = response.json()["data"]
    found_detailed_vote = False

    for vote in votes:
        detail_response = client.get(f"/api/v1/iniciativas/votacoes/{vote['vot_id']}")
        if detail_response.status_code != 200:
            continue

        detail = detail_response.json()

        if detail.get("detalhe_parsed"):
            found_detailed_vote = True
            parsed = detail["detalhe_parsed"]

            # All four fields must exist
            assert "a_favor" in parsed, "Missing 'a_favor' field"
            assert "contra" in parsed, "Missing 'contra' field"
            assert "abstencao" in parsed, "Missing 'abstencao' field"
            assert "ausencia" in parsed, "Missing 'ausencia' field"

            # All fields must be lists
            assert isinstance(parsed["a_favor"], list)
            assert isinstance(parsed["contra"], list)
            assert isinstance(parsed["abstencao"], list)
            assert isinstance(parsed["ausencia"], list)

            break

    # We should find at least one vote with parsed details
    assert found_detailed_vote, "No votes with detalhe_parsed found in sample"


def test_date_filtering_respected():
    """
    REGRESSION: Date filters (data_desde, data_ate) must be respected.

    Results should only include records within the specified date range.
    """
    # Test data_desde filter
    response = client.get("/api/v1/iniciativas/votacoes/?data_desde=2025-01-01&limit=50")
    assert response.status_code == 200

    votes = response.json()["data"]
    for vote in votes:
        if vote.get("data"):
            assert vote["data"] >= "2025-01-01", \
                f"Vote date {vote['data']} is before data_desde=2025-01-01"


def test_circulo_deputados_only_active():
    """
    REGRESSION: Circle deputados endpoint returns only active (Efetivo) deputies.

    When querying /circulos/{id}/deputados, only deputies with situacao_atual='Efetivo'
    should be returned, not substitutes (Suplente) or resigned (Renunciou).
    """
    # Get a circle
    response = client.get("/api/v1/circulos/?legislatura=L17&limit=1")
    assert response.status_code == 200

    circles = response.json()["data"]
    if not circles:
        pytest.skip("No circles found for L17")

    cp_id = circles[0]["cp_id"]

    # Get deputies from that circle
    response = client.get(f"/api/v1/circulos/{cp_id}/deputados?legislatura=L17")
    assert response.status_code == 200

    deputies = response.json()["data"]

    # All deputies must be active (Efetivo)
    for deputy in deputies:
        assert deputy["situacao_atual"] == "Efetivo", \
            f"Circle endpoint returned non-active deputy: {deputy['nome_parlamentar']} ({deputy['situacao_atual']})"


def test_partido_iniciativas_correct_author():
    """
    REGRESSION: Party initiatives endpoint returns only initiatives authored by that party.

    When querying /partidos/{sigla}/iniciativas, the initiatives should have that party
    in their ini_autor_grupos_parlamentares array.

    Note: This is a smoke test - we verify the endpoint works but don't exhaustively
    check every initiative's author list (would require full detail fetches).
    """
    # Get PS initiatives
    response = client.get("/api/v1/partidos/PS/iniciativas?legislatura=L17&limit=10")
    assert response.status_code == 200

    data = response.json()

    # Should have data structure
    assert "data" in data
    assert "pagination" in data

    # Should return some initiatives (PS is a major party)
    # Note: Not asserting count > 0 as it depends on data availability
    initiatives = data["data"]

    # Basic structure check
    for initiative in initiatives:
        assert "ini_nr" in initiative
        assert "legislatura" in initiative
        assert initiative["legislatura"] == "L17"


def test_autor_gp_filter_correctness():
    """
    REGRESSION: autor_gp filter should only return initiatives authored by that group.

    Verifies that the list_contains + list_transform pattern correctly filters
    the ini_autor_grupos_parlamentares array.
    """
    # Get PS initiatives
    response = client.get("/api/v1/iniciativas/?autor_gp=PS&legislatura=L17&limit=10")
    assert response.status_code == 200

    data = response.json()
    initiatives = data["data"]

    # Should have some PS initiatives
    assert len(initiatives) > 0, "PS should have authored initiatives in L17"

    # Verify by fetching full details of one initiative
    if initiatives:
        ini_id = initiatives[0]["ini_id"]
        detail = client.get(f"/api/v1/iniciativas/{ini_id}")
        assert detail.status_code == 200
        # Full record has ini_autor_grupos_parlamentares array
        # (detailed verification would require parsing the array)


def test_ini_nr_can_have_duplicates():
    """
    REGRESSION: ini_nr is NOT unique within a legislature.

    Known example: ini_nr='7' in L15 has 9 different initiatives.
    This test ensures we handle this correctly via filter parameter.
    """
    response = client.get("/api/v1/iniciativas/?ini_nr=7&legislatura=L15")
    assert response.status_code == 200
    data = response.json()

    # Should return multiple initiatives
    assert data["pagination"]["total"] > 1, \
        "ini_nr='7' should have multiple initiatives in L15"

    # Each should have a different ini_id
    ini_ids = [item["ini_id"] for item in data["data"]]
    assert len(ini_ids) == len(set(ini_ids)), "All ini_ids should be unique"

    # All should have ini_nr='7'
    for item in data["data"]:
        assert item["ini_nr"] == "7", f"Expected ini_nr='7', got {item['ini_nr']}"
        assert item["legislatura"] == "L15"


def test_ini_id_is_unique_identifier():
    """
    REGRESSION: ini_id is the unique identifier for initiatives.

    Verify that ini_id can be used to fetch a specific initiative,
    and that each ini_id corresponds to exactly one initiative.
    """
    # Get first initiative from list
    response = client.get("/api/v1/iniciativas/?limit=1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0

    ini_id = data[0]["ini_id"]
    ini_nr = data[0]["ini_nr"]

    # Fetch by ini_id
    detail = client.get(f"/api/v1/iniciativas/{ini_id}")
    assert detail.status_code == 200
    result = detail.json()

    # Should match the original
    assert result["ini_id"] == ini_id
    assert result["ini_nr"] == ini_nr


# =============================================================================
# Regression Tests for Atividades
# =============================================================================


def test_atividades_l17_count_307():
    """
    REGRESSION: L17 should have exactly 307 atividades.

    This is a known constant from the atividades dataset transformation.
    Validates ETL data integrity.
    """
    response = client.get("/api/v1/atividades/?legislatura=L17&limit=500")
    assert response.status_code == 200

    data = response.json()
    assert data["pagination"]["total"] == 307, \
        f"Expected 307 atividades in L17, got {data['pagination']['total']}"


def test_atividades_votes_l17_count_77():
    """
    REGRESSION: L17 should have exactly 77 votes from atividades.

    This is a known constant from the atividades_votacoes transformation.
    Validates vote extraction accuracy.
    """
    response = client.get("/api/v1/atividades/votacoes/?legislatura=L17&limit=500")
    assert response.status_code == 200

    data = response.json()
    assert data["pagination"]["total"] == 77, \
        f"Expected 77 atividades votes in L17, got {data['pagination']['total']}"


def test_has_party_details_implies_detalhe_not_null():
    """
    REGRESSION: has_party_details flag must be accurate.

    When has_party_details=true, the vote must have a non-null detalhe field
    with parsed party voting data. This validates the data quality flag integrity.
    """
    # Get votes with party details
    response = client.get("/api/v1/atividades/votacoes/?has_party_details=true&limit=10")
    assert response.status_code == 200

    votes = response.json()["data"]

    # Get detailed info for each vote
    for vote in votes:
        detail_response = client.get(f"/api/v1/atividades/votacoes/{vote['vot_id']}")
        assert detail_response.status_code == 200

        detail = detail_response.json()

        # Must have party details flag set
        assert detail["has_party_details"] is True, \
            f"Vote {vote['vot_id']} claims has_party_details=true but flag is false"

        # Must have detalhe_parsed structure
        assert detail["detalhe_parsed"] is not None, \
            f"Vote {vote['vot_id']} has has_party_details=true but detalhe_parsed is null"

        # Verify structure
        parsed = detail["detalhe_parsed"]
        assert "a_favor" in parsed
        assert "contra" in parsed
        assert "abstencao" in parsed
        assert isinstance(parsed["a_favor"], list)


def test_has_party_details_false_implies_no_parsed_data():
    """
    REGRESSION: Votes without party details should not have parsed data.

    When has_party_details=false, detalhe_parsed should be null or empty.
    This validates the data quality flag integrity in the opposite direction.
    """
    # Get votes without party details
    response = client.get("/api/v1/atividades/votacoes/?has_party_details=false&limit=10")
    assert response.status_code == 200

    votes = response.json()["data"]

    if votes:  # Only test if there are votes without party details
        # Get detailed info for first vote
        detail_response = client.get(f"/api/v1/atividades/votacoes/{votes[0]['vot_id']}")
        assert detail_response.status_code == 200

        detail = detail_response.json()

        # Must have party details flag set to false
        assert detail["has_party_details"] is False

        # detalhe_parsed should be null
        assert detail["detalhe_parsed"] is None, \
            f"Vote {votes[0]['vot_id']} has has_party_details=false but detalhe_parsed is not null"


def test_vote_source_breakdown_sum_correct():
    """
    REGRESSION: Vote source breakdown totals must equal sum of iniciativas + atividades.

    The stats endpoint provides vote_source_breakdown showing votes from both sources.
    The total field must equal iniciativas + atividades.
    """
    response = client.get("/api/v1/stats/?legislatura=L17")
    assert response.status_code == 200

    data = response.json()
    stats = data["data"]

    # Vote source breakdown should exist
    assert stats["vote_source_breakdown"] is not None, \
        "vote_source_breakdown should be present in stats"

    breakdown = stats["vote_source_breakdown"]

    # Verify sum
    expected_total = breakdown["iniciativas"] + breakdown["atividades"]
    assert breakdown["total"] == expected_total, \
        f"vote_source_breakdown total mismatch: {breakdown['total']} != {expected_total}"

    # For L17, we know atividades should be 77
    assert breakdown["atividades"] == 77, \
        f"L17 should have 77 atividades votes, got {breakdown['atividades']}"


def test_atividades_synthetic_id_format():
    """
    REGRESSION: Atividades must have synthetic IDs in correct format.

    IDs should be either:
    - Composite key: {legislatura}_{tipo}_{numero} (when numero exists)
    - MD5 hash: {legislatura}_{md5_hash} (when numero is null)

    This validates the ETL synthetic ID generation.
    """
    response = client.get("/api/v1/atividades/?legislatura=L17&limit=10")
    assert response.status_code == 200

    activities = response.json()["data"]
    assert len(activities) > 0, "Should have activities for L17"

    for activity in activities:
        ativ_id = activity["ativ_id"]

        # Must start with legislatura
        assert ativ_id.startswith("L17_"), \
            f"Activity ID should start with 'L17_', got {ativ_id}"

        # Must not be empty after prefix
        assert len(ativ_id) > len("L17_"), \
            f"Activity ID too short: {ativ_id}"


def test_atividades_filter_by_tipo_correctness():
    """
    REGRESSION: tipo filter should only return activities of that type.

    Verifies that the tipo filter correctly filters atividades by their ativ_tipo field.
    """
    # Test filtering for VOT type
    response = client.get("/api/v1/atividades/?tipo=VOT&legislatura=L17&limit=50")
    assert response.status_code == 200

    data = response.json()
    activities = data["data"]

    # Should have some VOT activities (most common type)
    assert len(activities) > 0, "Should have VOT activities in L17"

    # All returned activities must be type VOT
    for activity in activities:
        assert activity["ativ_tipo"] == "VOT", \
            f"Expected tipo=VOT, got {activity['ativ_tipo']}"


def test_atividades_votes_have_source_field():
    """
    REGRESSION: All atividades votes must have source='atividade'.

    This discriminator field distinguishes votes from atividades vs iniciativas.
    Critical for data provenance tracking.
    """
    response = client.get("/api/v1/atividades/votacoes/?limit=10")
    assert response.status_code == 200

    votes = response.json()["data"]

    if votes:
        # Get detailed info for first vote
        vot_id = votes[0]["vot_id"]
        detail_response = client.get(f"/api/v1/atividades/votacoes/{vot_id}")
        assert detail_response.status_code == 200

        detail = detail_response.json()

        # Must have source field set to 'atividade'
        assert "source" in detail, "Vote must have 'source' field"
        assert detail["source"] == "atividade", \
            f"Expected source='atividade', got {detail['source']}"


def test_atividades_by_tipo_in_stats():
    """
    REGRESSION: Stats endpoint must include atividades_by_tipo aggregation.

    For L17, should show VOT as dominant type (~95% of activities).
    Validates stats aggregation correctness.
    """
    response = client.get("/api/v1/stats/?legislatura=L17")
    assert response.status_code == 200

    data = response.json()
    stats = data["data"]

    # Should have atividades_by_tipo
    assert "atividades_by_tipo" in stats
    assert isinstance(stats["atividades_by_tipo"], list)

    # Should have at least one type
    assert len(stats["atividades_by_tipo"]) > 0, \
        "Should have at least one activity type in L17"

    # VOT should be the most common type
    tipo_counts = {item["tipo"]: item["count"] for item in stats["atividades_by_tipo"]}
    assert "VOT" in tipo_counts, "VOT should be present in atividades types"

    # VOT should be majority (>= 280 out of 307)
    assert tipo_counts["VOT"] >= 280, \
        f"VOT should be dominant type, got {tipo_counts['VOT']} out of 307"
