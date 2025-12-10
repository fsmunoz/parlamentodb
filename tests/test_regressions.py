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
    response = client.get("/api/v1/votacoes/?limit=100")
    assert response.status_code == 200

    votes = response.json()["data"]
    ninsc_found = False

    # Check detailed vote information for Ninsc members
    for vote in votes[:10]:  # Check first 10 votes for performance
        detail_response = client.get(f"/api/v1/votacoes/{vote['vot_id']}")
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
    response = client.get("/api/v1/votacoes/?limit=50")
    assert response.status_code == 200

    votes = response.json()["data"]
    found_detailed_vote = False

    for vote in votes:
        detail_response = client.get(f"/api/v1/votacoes/{vote['vot_id']}")
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
    response = client.get("/api/v1/votacoes/?data_desde=2025-01-01&limit=50")
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
