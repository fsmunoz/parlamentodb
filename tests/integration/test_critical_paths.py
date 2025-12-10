"""Integration tests for critical API paths.

Simple tests focused on correctness - verifying core endpoints work as expected.
"""
import pytest


def test_health_endpoint(client):
    """Health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_legislaturas_list(client):
    """Legislaturas endpoint returns valid data."""
    response = client.get("/api/v1/legislaturas?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0
    assert data["pagination"]["total"] > 0


def test_iniciativas_list(client):
    """Iniciativas endpoint returns valid data."""
    response = client.get("/api/v1/iniciativas?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0

    # Verify basic fields are present
    first_ini = data["data"][0]
    assert "ini_id" in first_ini
    assert "ini_nr" in first_ini


def test_votacoes_list(client):
    """Votacoes endpoint returns valid data."""
    response = client.get("/api/v1/votacoes?limit=5")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0

    # Verify basic fields are present
    first_vot = data["data"][0]
    assert "vot_id" in first_vot


def test_deputados_list(client):
    """Deputados endpoint returns valid data."""
    response = client.get("/api/v1/deputados?limit=5&legislatura=L17")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0

    # Verify all deputies are from L17
    for dep in data["data"]:
        assert dep["legislatura"] == "L17"


def test_partidos_list(client):
    """Partidos endpoint returns valid data."""
    response = client.get("/api/v1/partidos?legislatura=L17")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) > 0

    # Verify basic fields are present
    first_party = data["data"][0]
    assert "gp_sigla" in first_party
    assert first_party["legislatura"] == "L17"


def test_pagination_metadata(client):
    """Pagination metadata is consistent and correct."""
    response = client.get("/api/v1/iniciativas?limit=10&offset=0")
    assert response.status_code == 200

    data = response.json()
    pagination = data["pagination"]

    assert "limit" in pagination
    assert "offset" in pagination
    assert "total" in pagination
    assert pagination["limit"] == 10
    assert pagination["offset"] == 0
    assert pagination["total"] > 0
