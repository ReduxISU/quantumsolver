# pylint: disable=redefined-outer-name  # pytest fixture pattern
"""Tests for the Flask API routes."""

import pytest
from app import app as flask_app


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_index(client):
    """GET / returns 200."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_index_alias(client):
    """GET /index returns 200."""
    resp = client.get("/index")
    assert resp.status_code == 200


def test_health(client):
    """GET /health returns ok status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"
