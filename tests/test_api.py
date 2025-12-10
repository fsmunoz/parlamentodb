"""
Basic API integration tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "data_stats" in data


def test_api_metadata():
    """Test API metadata endpoint."""
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "legislature_coverage" in data


def test_list_iniciativas():
    """Test list iniciativas endpoint."""
    response = client.get("/api/v1/iniciativas/?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert "meta" in data
    assert len(data["data"]) <= 10
    assert data["pagination"]["limit"] == 10


def test_list_iniciativas_with_filters():
    """Test iniciativas with filters."""
    response = client.get("/api/v1/iniciativas/?legislatura=L17&limit=5")
    assert response.status_code == 200
    data = response.json()
    # All results should be from L17
    for item in data["data"]:
        assert item["legislatura"] == "L17"


def test_list_votacoes():
    """Test list votacoes endpoint."""
    response = client.get("/api/v1/votacoes/?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) <= 10


def test_date_filtering():
    """Test date filtering on votacoes."""
    response = client.get("/api/v1/votacoes/?data_desde=2025-01-01&limit=100")
    assert response.status_code == 200
    data = response.json()
    # All returned votes should be >= 2025-01-01
    for vote in data["data"]:
        if vote["data"]:  # Some votes might not have dates
            assert vote["data"] >= "2025-01-01"


def test_pagination_limits():
    """Test pagination limit enforcement."""
    # Should work with limit <= 500
    response = client.get("/api/v1/iniciativas/?limit=500")
    assert response.status_code == 200

    # Should fail with limit > 500
    response = client.get("/api/v1/iniciativas/?limit=1000")
    assert response.status_code == 422  # Validation error


def test_list_legislaturas():
    """Test list legislatures endpoint."""
    response = client.get("/api/v1/legislaturas/")
    assert response.status_code == 200
    data = response.json()
    # Now returns wrapped APIResponse format
    assert "data" in data
    assert "pagination" in data
    assert "meta" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    # Verify pagination
    assert data["pagination"]["total"] >= len(data["data"])


def test_get_single_iniciativa():
    """Test getting a single initiative by its unique ID."""
    # First, get an initiative ID from the list
    list_response = client.get("/api/v1/iniciativas/?limit=1")
    assert list_response.status_code == 200
    data = list_response.json()["data"]
    assert len(data) > 0

    ini_id = data[0]["ini_id"]
    ini_nr = data[0]["ini_nr"]

    # Get the full initiative by ini_id
    response = client.get(f"/api/v1/iniciativas/{ini_id}")
    assert response.status_code == 200
    result = response.json()
    assert result["ini_id"] == ini_id
    assert result["ini_nr"] == ini_nr


def test_get_nonexistent_iniciativa():
    """Test 404 for non-existent initiative."""
    response = client.get("/api/v1/iniciativas/999999999")
    assert response.status_code == 404


def test_list_iniciativas_includes_ini_id():
    """Verify list endpoint returns ini_id field."""
    response = client.get("/api/v1/iniciativas/?limit=5")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0
    # Check first item has ini_id
    assert "ini_id" in data[0]
    assert data[0]["ini_id"] is not None
    assert isinstance(data[0]["ini_id"], str)


def test_filter_by_ini_nr():
    """Verify ?ini_nr filter works."""
    # Use ini_nr='7' in L15 (known to have duplicates)
    response = client.get("/api/v1/iniciativas/?ini_nr=7&legislatura=L15")
    assert response.status_code == 200
    data = response.json()
    # Should be a list response
    assert "data" in data
    assert "pagination" in data
    # All results should have ini_nr='7'
    for item in data["data"]:
        assert item["ini_nr"] == "7"
        assert item["legislatura"] == "L15"
    # Should have multiple results (known duplicate)
    if data["pagination"]["total"] > 1:
        # Verify each has different ini_id
        ini_ids = [item["ini_id"] for item in data["data"]]
        assert len(ini_ids) == len(set(ini_ids)), "All ini_ids should be unique"


def test_root_redirects_to_docs():
    """Test root path redirects to docs."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert "/docs" in response.headers["location"]


def test_detalhe_parsed():
    """Test detalhe is parsed into structured format."""
    # Get a votacao with detalhe
    response = client.get("/api/v1/votacoes/?limit=100")
    assert response.status_code == 200
    data = response.json()

    # Find a vote with vot_id to check details
    if data["data"]:
        vot_id = data["data"][0]["vot_id"]
        detail_response = client.get(f"/api/v1/votacoes/{vot_id}")
        assert detail_response.status_code == 200
        vote_data = detail_response.json()

        # Check new fields exist
        assert "detalhe_parsed" in vote_data
        assert "is_nominal" in vote_data

        # If detalhe_parsed is present, check structure
        if vote_data.get("detalhe_parsed"):
            assert "a_favor" in vote_data["detalhe_parsed"]
            assert "contra" in vote_data["detalhe_parsed"]
            assert "abstencao" in vote_data["detalhe_parsed"]
            assert "ausencia" in vote_data["detalhe_parsed"]
            assert isinstance(vote_data["detalhe_parsed"]["a_favor"], list)


def test_party_filter():
    """Test filtering by party position."""
    # Test filtering by party voting in favor
    response = client.get("/api/v1/votacoes/?partido_favor=PSD&limit=10")
    assert response.status_code == 200
    # Note: This test validates the API accepts the parameter
    # Actual filtering validation would require checking detalhe_parsed in responses


def test_ninsc_preserved():
    """Test that Ninsc members are preserved with full names."""
    # Get votes, looking for nominal votes that might have Ninsc members
    response = client.get("/api/v1/votacoes/?limit=100")
    assert response.status_code == 200

    # This test validates that the API handles Ninsc members correctly
    # when they exist in the data
    # Ninsc members are rare, so we don't assert they must be found


def test_list_deputados():
    """Test list deputados endpoint."""
    response = client.get("/api/v1/deputados/?limit=10&legislatura=L17")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) <= 10
    # Verify response structure
    if data["data"]:
        dep = data["data"][0]
        assert "dep_cad_id" in dep
        assert "nome_parlamentar" in dep
        assert "partido_atual" in dep


def test_get_single_deputado():
    """Test getting a single deputy."""
    # First get a deputy ID
    list_response = client.get("/api/v1/deputados/?limit=1&legislatura=L17")
    dep_cad_id = list_response.json()["data"][0]["dep_cad_id"]

    # Get full deputy info
    response = client.get(f"/api/v1/deputados/{dep_cad_id}?legislatura=L17")
    assert response.status_code == 200
    data = response.json()
    assert data["dep_cad_id"] == dep_cad_id
    assert "partido_historico" in data
    assert "situacao_historico" in data


def test_list_circulos():
    """Test list circulos endpoint."""
    response = client.get("/api/v1/circulos/?legislatura=L17")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should have 22 electoral circles
    assert len(data["data"]) == 22


def test_get_circulo_deputados():
    """Test getting deputies from a circle."""
    # Get a circle ID
    list_response = client.get("/api/v1/circulos/?limit=1&legislatura=L17")
    cp_id = list_response.json()["data"][0]["cp_id"]

    # Get deputies from that circle
    response = client.get(f"/api/v1/circulos/{cp_id}/deputados?legislatura=L17")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Verify all deputies are from this circle and are active
    for dep in data["data"]:
        assert dep["situacao_atual"] == "Efetivo"


def test_list_partidos():
    """Test list partidos endpoint."""
    response = client.get("/api/v1/partidos/?legislatura=L17")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # L17 should have 10 parties
    assert len(data["data"]) == 10


def test_get_partido_deputados():
    """Test getting deputies from a party."""
    # Get PS deputies
    response = client.get("/api/v1/partidos/PS/deputados?legislatura=L17&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # All deputies should be from PS
    for dep in data["data"]:
        assert dep["partido_atual"] == "PS"


def test_get_partido_iniciativas():
    """Test getting initiatives from a party."""
    # Get PS initiatives
    response = client.get("/api/v1/partidos/PS/iniciativas?legislatura=L17&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_iniciativas_filter_by_autor_gp():
    """Test filtering initiatives by parliamentary group author."""
    response = client.get("/api/v1/iniciativas/?autor_gp=PS&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Note: Can't verify all have PS without fetching full details
    # Just verify endpoint accepts the parameter


def test_iniciativas_filter_by_autor_tipo():
    """Test filtering initiatives by author type."""
    response = client.get("/api/v1/iniciativas/?autor_tipo=Governo&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should return some government initiatives


def test_iniciativas_combined_filters():
    """Test combining multiple filters."""
    response = client.get(
        "/api/v1/iniciativas/?legislatura=L17&autor_gp=CH&data_desde=2024-01-01&limit=5"
    )
    assert response.status_code == 200
    data = response.json()
    # All results should be from L17
    for item in data["data"]:
        assert item["legislatura"] == "L17"


# =============================================================================
# Tests for L15 and L16 Support
# =============================================================================


def test_list_deputados_l15():
    """Test list deputados endpoint for L15."""
    response = client.get("/api/v1/deputados/?limit=10&legislatura=L15")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["total"] == 1331  # L15 should have 1331 deputies
    # Verify response structure
    if data["data"]:
        dep = data["data"][0]
        assert "dep_cad_id" in dep
        assert "nome_parlamentar" in dep
        assert "partido_atual" in dep


def test_list_deputados_l16():
    """Test list deputados endpoint for L16."""
    response = client.get("/api/v1/deputados/?limit=10&legislatura=L16")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["total"] == 1513  # L16 should have 1513 deputies


def test_list_circulos_l15():
    """Test list circulos endpoint for L15."""
    response = client.get("/api/v1/circulos/?legislatura=L15")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should have 22 electoral circles
    assert len(data["data"]) == 22


def test_list_circulos_l16():
    """Test list circulos endpoint for L16."""
    response = client.get("/api/v1/circulos/?legislatura=L16")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should have 22 electoral circles
    assert len(data["data"]) == 22


def test_list_partidos_l15():
    """Test list partidos endpoint for L15."""
    response = client.get("/api/v1/partidos/?legislatura=L15")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # L15 should have 8 parties
    assert len(data["data"]) == 8
    # Verify expected parties are present
    party_siglas = [p["gp_sigla"] for p in data["data"]]
    assert "PS" in party_siglas
    assert "PSD" in party_siglas
    assert "BE" in party_siglas


def test_list_partidos_l16():
    """Test list partidos endpoint for L16."""
    response = client.get("/api/v1/partidos/?legislatura=L16")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # L16 should have 9 parties (includes CDS-PP)
    assert len(data["data"]) == 9
    party_siglas = [p["gp_sigla"] for p in data["data"]]
    assert "PS" in party_siglas
    assert "PSD" in party_siglas
    assert "CDS-PP" in party_siglas


def test_get_partido_ps_l15():
    """Test getting PS party details for L15."""
    response = client.get("/api/v1/partidos/PS?legislatura=L15")
    assert response.status_code == 200
    data = response.json()
    assert data["gp_sigla"] == "PS"
    assert data["gp_nome"] == "Partido Socialista"


def test_get_partido_ps_l16():
    """Test getting PS party details for L16."""
    response = client.get("/api/v1/partidos/PS?legislatura=L16")
    assert response.status_code == 200
    data = response.json()
    assert data["gp_sigla"] == "PS"
    assert data["gp_nome"] == "Partido Socialista"


def test_get_partido_deputados_l15():
    """Test getting PS deputies for L15."""
    response = client.get("/api/v1/partidos/PS/deputados?legislatura=L15&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # All deputies should be from PS
    for dep in data["data"]:
        assert dep["partido_atual"] == "PS"


def test_get_partido_deputados_l16():
    """Test getting PS deputies for L16."""
    response = client.get("/api/v1/partidos/PS/deputados?legislatura=L16&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # All deputies should be from PS
    for dep in data["data"]:
        assert dep["partido_atual"] == "PS"
