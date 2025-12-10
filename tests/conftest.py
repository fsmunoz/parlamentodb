"""Pytest configuration and shared fixtures."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


def pytest_configure(config):
    """Print ASCII banner at test session start."""
    banner = """
========================================================================
 PORTUGUESE PARLIAMENT API - TEST SUITE
========================================================================
 Testing endpoints: iniciativas, votacoes, deputados, partidos, circulos
 Data coverage: Legislatures L15, L16, L17 (2019-present)
========================================================================
"""
    terminal_writer = config.pluginmanager.get_plugin("terminalreporter")
    if terminal_writer:
        terminal_writer.write_line(banner)


def pytest_collection_finish(session):
    """Print collection summary in ASCII."""
    terminal_writer = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminal_writer:
        terminal_writer.write_line(f"\n    [COLLECTED] {len(session.items)} tests\n")


# Removed pytest_runtest_logreport - pytest handles output formatting


@pytest.fixture(scope="module")
def client():
    """FastAPI test client (shared across test module)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def app_instance():
    """FastAPI application instance for contract testing."""
    return app
