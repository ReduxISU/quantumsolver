# pylint: disable=redefined-outer-name  # pytest fixture pattern
"""Tests for the SAT quantum solver."""

import pytest
import sat_quantum
from app import app as flask_app

LONG_EXPR = " & ".join(
    [
        "(x1 | !x2 | x3)",
        "(!x1 | x3 | x1)",
        "(x2 | !x3 | x1)",
        "(!x3 | x4 | !x2 | x1)",
        "(!x4 | !x1)",
        "(x4 | x3 | !x1)",
    ]
)

# Bit strings that are NOT valid solutions to LONG_EXPR.
INVALID = {"0000", "0101", "0111", "1000", "1110"}


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_direct():
    """Solve directly and check that the answer is a valid satisfying assignment."""
    result = sat_quantum.solve({"boolexpr": LONG_EXPR})
    assert result["answer"] not in INVALID


def test_api(client):
    """POST to /sat-quantum and check that the answer is a valid satisfying assignment."""
    resp = client.post("/sat-quantum", json={"boolexpr": LONG_EXPR})
    assert resp.status_code == 200
    assert resp.json["answer"] not in INVALID
