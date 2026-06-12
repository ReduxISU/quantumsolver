# pylint: disable=redefined-outer-name  # pytest fixture pattern
"""Tests for the Bernstein-Vazirani quantum solver."""

import pytest
import bernstein_vazirani_quantum as bv
from app import app as flask_app

# (f_bits, expected hidden string s)
CASES = [
    ([0, 1, 0, 1, 1, 0, 1, 0], "101"),
    ([0, 1, 1, 0, 1, 0, 0, 1], "111"),
    ([1, 0, 0, 1, 0, 1, 1, 0], "000"),
    ([0, 1, 0, 1, 0, 1, 0, 1], "001"),
]


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.mark.parametrize("f,expected_s", CASES)
def test_list_input(f, expected_s):
    """Solve directly with list input and check recovered hidden string."""
    assert bv.solve(f)["answer"] == expected_s


@pytest.mark.parametrize("f,expected_s", CASES)
def test_dict_input(f, expected_s):
    """Solve directly with dict input and check recovered hidden string."""
    assert bv.solve({"nbits": 3, "f": f})["answer"] == expected_s


@pytest.mark.parametrize("f,expected_s", CASES)
def test_api_list_input(client, f, expected_s):
    """POST list input to /bernstein-vazirani-quantum and check hidden string."""
    resp = client.post("/bernstein-vazirani-quantum", json=f)
    assert resp.status_code == 200
    assert resp.json["answer"] == expected_s


@pytest.mark.parametrize("f,expected_s", CASES)
def test_api_dict_input(client, f, expected_s):
    """POST dict input to /bernstein-vazirani-quantum and check hidden string."""
    resp = client.post("/bernstein-vazirani-quantum", json={"nbits": 3, "f": f})
    assert resp.status_code == 200
    assert resp.json["answer"] == expected_s
