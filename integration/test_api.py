"""Integration tests: the built image answering over HTTP.

Nothing here imports quantumsolver. Unlike tests/, which drives the app in-process via Flask's
test client, this suite only knows a URL — so it exercises the wheel, gunicorn, and the container
the way Redux does.
"""

import pytest
import requests

# Generous: each solve spawns a process that re-imports qiskit, and the app self-limits at 25s.
TIMEOUT = 40

# ([f0, f1], expected classification)
DEUTSCH_CASES = [
    ([0, 0], "constant"),
    ([0, 1], "balanced"),
]

# (f_bits, expected hidden string)
BERNSTEIN_VAZIRANI_CASES = [
    ([0, 1, 0, 1, 1, 0, 1, 0], "101"),
]


def test_health(base_url):
    """GET /health reports ok — the same route rbs polls for readiness."""
    resp = requests.get(f"{base_url}/health", timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/", "/index"])
def test_landing_routes(base_url, path):
    """The landing routes answer."""
    resp = requests.get(f"{base_url}{path}", timeout=TIMEOUT)
    assert resp.status_code == 200


@pytest.mark.parametrize("f,expected", DEUTSCH_CASES)
def test_deutsch(base_url, f, expected):
    """POST /deutsch-quantum classifies the oracle as constant or balanced."""
    resp = requests.post(f"{base_url}/deutsch-quantum", json=f, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert resp.json()["answer"] == expected


@pytest.mark.parametrize("f,expected", BERNSTEIN_VAZIRANI_CASES)
def test_bernstein_vazirani(base_url, f, expected):
    """POST /bernstein-vazirani-quantum recovers the hidden string."""
    resp = requests.post(
        f"{base_url}/bernstein-vazirani-quantum", json=f, timeout=TIMEOUT
    )
    assert resp.status_code == 200
    assert resp.json()["answer"] == expected
