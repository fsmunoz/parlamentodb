"""Integration tests for error handling.

Simple tests focused on correctness - verifying API handles errors properly.
"""
import pytest


def test_nonexistent_endpoint(client):
    """Non-existent endpoints return 404."""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404


def test_invalid_limit_param(client):
    """Invalid limit parameter is handled appropriately."""
    response = client.get("/api/v1/iniciativas?limit=invalid")
    # Should return 422 (validation error) or gracefully handle it
    assert response.status_code in [422, 200]


def test_negative_limit(client):
    """Negative limit is handled appropriately."""
    response = client.get("/api/v1/iniciativas?limit=-1")
    # Should either reject it or treat it as invalid
    assert response.status_code in [422, 400, 200]


def test_very_large_limit(client):
    """Extremely large limit is capped or rejected."""
    response = client.get("/api/v1/iniciativas?limit=999999")
    # API should reject with 422 (validation error) or accept with 200
    assert response.status_code in [200, 422]

    # If accepted, should be capped to a reasonable number
    if response.status_code == 200:
        data = response.json()
        assert len(data["data"]) < 999999


def test_negative_offset(client):
    """Negative offset is handled appropriately."""
    response = client.get("/api/v1/iniciativas?offset=-1")
    # Should either reject it or treat it as zero
    assert response.status_code in [422, 400, 200]


def test_nonexistent_resource_by_id(client):
    """Requesting non-existent resource by ID returns appropriate error."""
    # Try to get a non-existent partido
    response = client.get("/api/v1/partidos/NONEXISTENT?legislatura=L17")
    assert response.status_code in [404, 200]

    # If 200, data should be empty or null
    if response.status_code == 200:
        data = response.json()
        assert data is None or data.get("gp_sigla") is None


def test_missing_required_parameter(client):
    """Missing required parameters are handled properly."""
    # Some endpoints require legislatura parameter
    response = client.get("/api/v1/partidos/PS")
    # Should work with default or return error
    assert response.status_code in [200, 400, 422]


def test_invalid_json_response_structure(client):
    """All successful responses have consistent structure."""
    response = client.get("/api/v1/iniciativas?limit=1")
    assert response.status_code == 200

    data = response.json()
    # Verify JSON structure
    assert isinstance(data, dict)
    assert "data" in data
    assert "pagination" in data
    assert isinstance(data["data"], list)
    assert isinstance(data["pagination"], dict)
