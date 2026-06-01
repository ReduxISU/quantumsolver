# pylint: disable=redefined-outer-name  # pytest fixture pattern
"""Tests for the Deutsch quantum solver."""
import pytest
import deutsch_quantum as deutsch
from app import app as flask_app

# ([f0, f1], expected answer)
CASES = [
    ([0, 0], "constant"),
    ([0, 1], "balanced"),
    ([1, 0], "balanced"),
    ([1, 1], "constant"),
]


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.mark.parametrize("f,expected", CASES)
def test_direct(f, expected):
    """Solve directly and check constant/balanced classification."""
    assert deutsch.solve(f)["answer"] == expected


@pytest.mark.parametrize("f,expected", CASES)
def test_api(client, f, expected):
    """POST to /deutsch-quantum and check constant/balanced classification."""
    resp = client.post("/deutsch-quantum", json=f)
    assert resp.status_code == 200
    assert resp.json["answer"] == expected
