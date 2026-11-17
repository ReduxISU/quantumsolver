#!/usr/bin/env python3

"""This is a quantum solver for the (weighted) Max-Cut problem. It accepts an
undirected weighted graph and uses the Quantum Approximate Optimization
Algorithm (QAOA) to find a partition of the nodes into two sets S and T that
maximizes the total weight of the edges crossing between them.

The input is a dictionary:
    {'nodes': ['1', '2', ...],
     'edges': [['1', '2', 5], ['2', '3', 1.5], ...]}
  each edge is [u, v] or [u, v, weight]; a missing weight is 1.

The result is a dictionary:
    {'answer': '{1,3}' (the nodes on the S side, Redux certificate format),
     'cut_weight': total weight of the cut,
     'answer_bitstring': one character per node, '1' = in S,
     'qasm': the optimized QAOA circuit}
  or {'error': message} for invalid input.
"""

import argparse
import itertools

import numpy as np
import requests
from qiskit import qasm2, transpile
from qiskit.circuit.library import qaoa_ansatz
from qiskit.primitives import StatevectorEstimator, StatevectorSampler
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

# Statevector simulation costs 2^n per evaluation and COBYLA needs dozens of
# them, so keep instances well inside the router's 25 second timeout.
MAX_NODES = 16
REPS = 2
SHOTS = 10000
BASIS_GATES = ["rz", "sx", "x", "cx"]


def parse_graph(data):
    """Return (nodes, weights) where weights maps (i, j) index pairs, i < j,
    to the summed weight of every edge between nodes i and j."""

    nodes = [str(node) for node in data["nodes"]]
    if len(set(nodes)) != len(nodes):
        raise ValueError("duplicate node names")
    index = {node: i for i, node in enumerate(nodes)}

    weights = {}
    for edge in data["edges"]:
        if len(edge) not in (2, 3):
            raise ValueError(f"edge {edge} must be [u, v] or [u, v, weight]")
        u, v = str(edge[0]), str(edge[1])
        if u not in index or v not in index:
            raise ValueError(f"edge {edge} references an unknown node")
        if u == v:
            # A self-loop can never cross the cut.
            continue
        key = tuple(sorted((index[u], index[v])))
        weights[key] = weights.get(key, 0) + (edge[2] if len(edge) == 3 else 1)
    return nodes, weights


def cut_weight(weights, x):
    """Total weight of the edges crossing the partition x (x[i] in {0, 1})."""

    return sum(w for (i, j), w in weights.items() if x[i] != x[j])


def cost_hamiltonian(n, weights):
    """Ising Hamiltonian whose ground state is the maximum cut.

    cut(x) = sum_ij w_ij (1 - Z_i Z_j) / 2, so maximizing the cut is the same
    as minimizing sum_ij (w_ij / 2) Z_i Z_j. This is the same operator the
    notebook gets from qiskit_addon_opt_mapper's Maxcut + to_ising, minus the
    constant offset. Weights are scaled so the largest is 1: that leaves the
    optimal cut unchanged but keeps gamma's useful range near [0, 2*pi]
    regardless of the weights' magnitude.
    """

    scale = max(abs(w) for w in weights.values())
    terms = [("ZZ", [i, j], w / (2 * scale)) for (i, j), w in weights.items()]
    return SparsePauliOp.from_sparse_list(terms, num_qubits=n)


def best_partition(counts, weights, n):
    """Pick the sampled bitstring with the largest cut, breaking ties by
    frequency. Partitions with S or T empty are skipped since Redux requires
    both sides to be non-empty."""

    best = None
    for bitstring, count in counts.items():
        # Qiskit bitstrings are big-endian (qubit n-1 leftmost); reverse so
        # index i maps to qubit i / node i.
        x = [int(b) for b in bitstring[::-1]]
        if 0 < sum(x) < n:
            key = (cut_weight(weights, x), count)
            if best is None or key > best[0]:
                best = (key, x)
    if best is None:
        # Nothing non-trivial was sampled; any valid split will do.
        return [1] + [0] * (n - 1)
    return best[1]


def solve(data) -> dict:
    """Solve a weighted Max-Cut instance with QAOA."""

    try:
        nodes, weights = parse_graph(data)
    except (KeyError, TypeError, ValueError) as e:
        return {"error": f"invalid graph: {e}"}

    n = len(nodes)
    if n < 2:
        return {"error": "need at least 2 nodes to form a cut"}
    if n > MAX_NODES:
        return {"error": f"too many nodes ({n}), limit is {MAX_NODES}"}

    if not any(weights.values()):
        # No weighted edges: every cut has weight 0, so there is nothing for
        # QAOA to optimize.
        x = [1] + [0] * (n - 1)
        circuit = None
    else:
        hamiltonian = cost_hamiltonian(n, weights)
        # Lower the PauliEvolutionGates to standard gates once, up front. Left
        # as-is, the simulator exponentiates a sparse matrix for every gate on
        # every COBYLA step, which is orders of magnitude slower.
        ansatz = transpile(
            qaoa_ansatz(hamiltonian, reps=REPS),
            basis_gates=BASIS_GATES,
            optimization_level=1,
        )

        # Same warm start as the notebook: midpoints of the beta and gamma
        # periods. qaoa_ansatz orders its parameters [betas..., gammas...].
        init_params = [np.pi / 2] * REPS + [np.pi] * REPS

        estimator = StatevectorEstimator()

        def cost(params):
            result = estimator.run([(ansatz, hamiltonian, params)]).result()
            return float(result[0].data.evs)

        result = minimize(cost, init_params, method="COBYLA", tol=1e-2)

        circuit = ansatz.assign_parameters(result.x)
        circuit.measure_all()
        counts = (
            StatevectorSampler()
            .run([circuit], shots=SHOTS)
            .result()[0]
            .data.meas.get_counts()
        )
        x = best_partition(counts, weights, n)

    # Max-Cut is symmetric in S and T; report the side containing the first
    # node so equivalent answers print the same way.
    if x[0] == 0:
        x = [1 - b for b in x]
    answer = "{" + ",".join(node for node, b in zip(nodes, x, strict=True) if b) + "}"

    r = {
        "answer": answer,
        "cut_weight": cut_weight(weights, x),
        "answer_bitstring": "".join(str(b) for b in x),
    }
    if circuit is not None:
        r["qasm"] = qasm2.dumps(circuit)
    return r


def brute_force(data):
    """Maximum cut weight by exhaustive search, for checking answers."""

    nodes, weights = parse_graph(data)
    n = len(nodes)
    return max(
        cut_weight(weights, x)
        for x in itertools.product([0, 1], repeat=n)
        if 0 < sum(x) < n
    )


def tryit(url, data, show_circuits=False):
    """Helper function to test the solver."""

    if url is None:
        solution = solve(data)
    else:
        req = requests.post(url, json=data, timeout=40)
        solution = req.json()

    expected = brute_force(data)
    assert (
        solution["cut_weight"] == expected
    ), f"Failed for data={data}, cut {solution['cut_weight']} != max {expected}"

    if show_circuits and "qasm" in solution:
        print(f"// Max-Cut QAOA circuit for input {data}:")
        print(solution["qasm"])


def main():
    """Main function to run the tests locally or on a server."""
    parser = argparse.ArgumentParser(description="Max-Cut Quantum Solver")
    parser.add_argument(
        "--baseurl",
        type=str,
        default=None,
        help="Base URL for the solver to test against.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="maxcut-quantum",
        help="Endpoint for the solver.",
    )
    parser.add_argument(
        "--show-circuits",
        action="store_true",
        help="Show the generated quantum circuits.",
    )

    args = parser.parse_args()
    url = None
    if args.baseurl is not None:
        url = f"{args.baseurl}/{args.endpoint}"

    # Redux's default MAXCUT instance
    tryit(
        url,
        {
            "nodes": ["1", "2", "3", "4", "5"],
            "edges": [
                ["2", "1", 5],
                ["1", "3", 4],
                ["2", "3", 2],
                ["3", "5", 1],
                ["2", "4", 4],
                ["4", "5", 2],
            ],
        },
        args.show_circuits,
    )

    if url is None:
        url = "local"
    print(f"All tests passed ({url})")


if __name__ == "__main__":
    main()
