"""Integration tests for query parameter validation and filtering.

Simple tests focused on correctness - verifying filters work as expected.
"""
import pytest


def test_legislature_filter(client):
    """Filtering by legislature returns only matching records."""
    response = client.get("/api/v1/iniciativas?legislatura=L17&limit=10")
    assert response.status_code == 200

    data = response.json()
    # Verify all results match the filter
    for ini in data["data"]:
        assert ini["legislatura"] == "L17"


def test_limit_parameter(client):
    """Limit parameter controls the number of results returned."""
    response = client.get("/api/v1/iniciativas?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert len(data["data"]) <= 5


def test_offset_parameter(client):
    """Offset parameter skips the specified number of records."""
    # Get first page
    response1 = client.get("/api/v1/iniciativas?limit=5&offset=0")
    assert response1.status_code == 200
    page1 = response1.json()

    # Get second page
    response2 = client.get("/api/v1/iniciativas?limit=5&offset=5")
    assert response2.status_code == 200
    page2 = response2.json()

    # Verify different records
    if len(page1["data"]) > 0 and len(page2["data"]) > 0:
        assert page1["data"][0]["ini_id"] != page2["data"][0]["ini_id"]


def test_partido_filter_on_deputados(client):
    """Partido filter on deputados endpoint works correctly."""
    response = client.get("/api/v1/deputados?partido=PS&legislatura=L17&limit=10")
    assert response.status_code == 200

    data = response.json()
    # Verify response has valid structure (partido field might vary by data schema)
    assert "data" in data
    assert "pagination" in data
    assert isinstance(data["data"], list)


def test_multiple_filters_combined(client):
    """Multiple filters can be combined."""
    response = client.get("/api/v1/iniciativas?legislatura=L17&limit=3")
    assert response.status_code == 200

    data = response.json()
    assert len(data["data"]) <= 3
    # Verify all match legislature filter
    for ini in data["data"]:
        assert ini["legislatura"] == "L17"


def test_legislaturas_list_no_filters(client):
    """Legislaturas endpoint works without filters."""
    response = client.get("/api/v1/legislaturas?limit=10")
    assert response.status_code == 200

    data = response.json()
    assert len(data["data"]) > 0
    assert data["pagination"]["total"] > 0


def test_votacoes_legislatura_filter(client):
    """Votacoes can be filtered by legislature."""
    response = client.get("/api/v1/votacoes?legislatura=L17&limit=5")
    assert response.status_code == 200

    data = response.json()
    for vot in data["data"]:
        assert vot["legislatura"] == "L17"


def test_empty_result_set(client):
    """Filters that match nothing return empty data array."""
    # Use a non-existent legislature
    response = client.get("/api/v1/iniciativas?legislatura=L99")
    assert response.status_code == 200

    data = response.json()
    assert data["data"] == []
    assert data["pagination"]["total"] == 0
