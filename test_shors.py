import pytest
import shors_quantum
from app import app as flask_app

# (N, expected prime factors)
CASES = [
    (15,  [3, 5]),
    (21,  [3, 7]),
    (77,  [7, 11]),
    (85,  [5, 17]),
    (105, [3, 5, 7]),
    (81,  [3, 3, 3, 3]),
    (29,  [29]),
    (89,  [89]),
]


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.mark.parametrize("n,expected", CASES)
def test_direct_int(n, expected):
    assert shors_quantum.solve(n)["answer"] == expected


@pytest.mark.parametrize("n,expected", CASES)
def test_direct_dict(n, expected):
    assert shors_quantum.solve({"N": n})["answer"] == expected


@pytest.mark.parametrize("n,expected", CASES)
def test_api(client, n, expected):
    resp = client.post("/prime-factorization-quantum", json={"N": n})
    assert resp.status_code == 200
    assert resp.json["answer"] == expected
