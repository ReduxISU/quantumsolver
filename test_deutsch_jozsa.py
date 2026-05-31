import pytest
import deutsch_jozsa_quantum as dj
from app import app as flask_app

# (f_bits, expected answer)
LIST_CASES = [
    ([0, 0, 0, 0, 0, 0, 0, 0], "constant"),
    ([1, 1, 1, 1, 1, 1, 1, 1], "constant"),
    ([0, 1, 0, 1, 1, 0, 1, 0], "balanced"),
    ([0, 1, 1, 0, 1, 0, 0, 1], "balanced"),
]

DICT_CASES = [
    ({"nbits": 3, "f": f}, expected) for f, expected in LIST_CASES
]


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.mark.parametrize("f,expected", LIST_CASES)
def test_direct_list(f, expected):
    assert dj.solve(f)["answer"] == expected


@pytest.mark.parametrize("data,expected", DICT_CASES)
def test_direct_dict(data, expected):
    assert dj.solve(data)["answer"] == expected


@pytest.mark.parametrize("f,expected", LIST_CASES)
def test_api_list(client, f, expected):
    resp = client.post("/deutsch-jozsa-quantum", json=f)
    assert resp.status_code == 200
    assert resp.json["answer"] == expected


@pytest.mark.parametrize("data,expected", DICT_CASES)
def test_api_dict(client, data, expected):
    resp = client.post("/deutsch-jozsa-quantum", json=data)
    assert resp.status_code == 200
    assert resp.json["answer"] == expected
