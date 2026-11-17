"""Tests for the Max-Cut quantum solver."""

import re

import numpy as np
import pytest
from qiskit.circuit.library import qaoa_ansatz
from qiskit.quantum_info import Statevector

from quantumsolver import maxcut_quantum
from quantumsolver.app import app as flask_app

# Redux's default MAXCUT instance; its maximum cut has weight 15.
REDUX_DEFAULT = {
    "nodes": ["1", "2", "3", "4", "5"],
    "edges": [
        ["2", "1", 5],
        ["1", "3", 4],
        ["2", "3", 2],
        ["3", "5", 1],
        ["2", "4", 4],
        ["4", "5", 2],
    ],
}

# Unweighted 6-node graph from the QAOA notebook; its maximum cut is 8.
NOTEBOOK_GRAPH = {
    "nodes": [0, 1, 2, 3, 4, 5],
    "edges": [[0, 3], [0, 2], [1, 2], [1, 3], [2, 4], [2, 5], [3, 4], [3, 5]],
}


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def check(data, result):
    """The answer is a valid, maximum cut that agrees with its bitstring."""
    nodes = [str(node) for node in data["nodes"]]
    side = set(result["answer"].strip("{}").split(","))
    assert side == {
        node
        for node, b in zip(nodes, result["answer_bitstring"], strict=True)
        if b == "1"
    }
    assert 0 < len(side) < len(nodes)
    assert result["cut_weight"] == maxcut_quantum.brute_force(data)


@pytest.mark.parametrize("data", [REDUX_DEFAULT, NOTEBOOK_GRAPH])
def test_direct(data):
    """Solve directly and check that the answer is a maximum cut."""
    result = maxcut_quantum.solve(data)
    check(data, result)
    assert "OPENQASM 2.0" in result["qasm"]


def test_api(client):
    """POST to /maxcut-quantum and check that the answer is a maximum cut."""
    resp = client.post("/maxcut-quantum", json=REDUX_DEFAULT)
    assert resp.status_code == 200
    check(REDUX_DEFAULT, resp.json)


# A 10-node graph where the sample, not just the angles, decides the answer.
TEN_NODES = {
    "nodes": [str(i) for i in range(10)],
    "edges": [[str(i), str((i * 3 + 1) % 10), i % 4 + 1] for i in range(10)]
    + [[str(i), str((i + 5) % 10), 2] for i in range(5)],
}


@pytest.mark.parametrize("data", [REDUX_DEFAULT, TEN_NODES])
def test_seeded_is_reproducible(data):
    """With the default seed, the same input gives the same response."""
    first = maxcut_quantum.solve(data)
    assert first["seed"] == maxcut_quantum.SEED
    assert maxcut_quantum.solve(data) == first


def test_custom_seed():
    """A request's seed is used and echoed back."""
    result = maxcut_quantum.solve({**REDUX_DEFAULT, "seed": 1})
    assert result["seed"] == 1
    check(REDUX_DEFAULT, result)
    assert maxcut_quantum.solve({**REDUX_DEFAULT, "seed": 1}) == result


@pytest.mark.parametrize("data", [REDUX_DEFAULT, NOTEBOOK_GRAPH, TEN_NODES])
def test_qaoa_circuit_matches_qaoa_ansatz(data):
    """The hand-built circuit prepares the same state as qiskit's qaoa_ansatz
    (up to global phase) and orders its parameters the same way."""
    nodes, weights = maxcut_quantum.parse_graph(data)
    n = len(nodes)
    ours = maxcut_quantum.qaoa_circuit(n, weights, maxcut_quantum.REPS)
    reference = qaoa_ansatz(
        maxcut_quantum.cost_hamiltonian(n, weights), reps=maxcut_quantum.REPS
    )
    assert [p.name for p in ours.parameters] == [p.name for p in reference.parameters]
    rng = np.random.default_rng(0)
    for _ in range(3):
        params = rng.uniform(-np.pi, np.pi, ours.num_parameters)
        a = Statevector(ours.assign_parameters(params)).data
        b = Statevector(reference.assign_parameters(params)).data
        assert abs(np.vdot(a, b)) == pytest.approx(1.0)


def test_edge_rounds_are_matchings_covering_every_edge():
    """Each round's edges share no node, and every edge is in exactly one round."""
    _, weights = maxcut_quantum.parse_graph(TEN_NODES)
    rounds = maxcut_quantum.edge_rounds(weights)
    for edges in rounds:
        touched = [q for i, j, _ in edges for q in (i, j)]
        assert len(touched) == len(set(touched))
    assert sorted((i, j) for edges in rounds for i, j, _ in edges) == sorted(weights)


def test_response_has_angles_and_textbook_gates():
    """The response carries one gamma and one beta per layer, and the qasm uses
    only h, cx, rz, rx and measurements."""
    result = maxcut_quantum.solve(REDUX_DEFAULT)
    assert len(result["gammas"]) == maxcut_quantum.REPS
    assert len(result["betas"]) == maxcut_quantum.REPS
    gates = set(re.findall(r"^([a-z]+)[ (]", result["qasm"], re.MULTILINE))
    gates -= {"include", "qreg", "creg"}
    assert gates <= {"h", "cx", "rz", "rx", "barrier", "measure"}
    assert {"h", "cx", "rz", "rx", "measure"} <= gates


def test_fractional_and_large_weights():
    """Weight scale doesn't matter: the same graph with weights scaled up or
    to fractions gives the same partition quality."""
    for scale in (0.01, 1000):
        data = {
            "nodes": REDUX_DEFAULT["nodes"],
            "edges": [[u, v, w * scale] for u, v, w in REDUX_DEFAULT["edges"]],
        }
        result = maxcut_quantum.solve(data)
        assert result["cut_weight"] == pytest.approx(15 * scale)


def test_parallel_edges_and_self_loops():
    """Parallel edges sum; self-loops never cross the cut."""
    data = {
        "nodes": ["a", "b", "c"],
        "edges": [["a", "b", 2], ["b", "a", 3], ["c", "c", 9]],
    }
    nodes, weights = maxcut_quantum.parse_graph(data)
    assert weights == {(0, 1): 5}
    assert maxcut_quantum.solve(data)["cut_weight"] == 5


def test_no_edges():
    """With nothing to cut, any non-trivial split is returned."""
    result = maxcut_quantum.solve({"nodes": ["a", "b"], "edges": []})
    assert result["answer"] == "{a}"
    assert result["cut_weight"] == 0
    assert "qasm" not in result


@pytest.mark.parametrize(
    "data",
    [
        {"nodes": ["a"], "edges": []},
        {"nodes": ["a", "a"], "edges": []},
        {"nodes": ["a", "b"], "edges": [["a", "z", 1]]},
        {"nodes": ["a", "b"], "edges": [["a"]]},
        {"edges": []},
        {"nodes": ["a", "b"], "edges": [], "seed": -1},
        {"nodes": ["a", "b"], "edges": [], "seed": "6680"},
        {"nodes": ["a", "b"], "edges": [], "seed": 1.5},
        {"nodes": ["a", "b"], "edges": [], "seed": True},
        {"nodes": [str(i) for i in range(maxcut_quantum.MAX_NODES + 1)], "edges": []},
    ],
)
def test_invalid(data):
    """Invalid instances return an error and no answer."""
    result = maxcut_quantum.solve(data)
    assert "error" in result
    assert "answer" not in result
