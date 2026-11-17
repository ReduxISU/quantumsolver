#!/usr/bin/env python3

"""This is a quantum solver for the (weighted) Max-Cut problem. It accepts an
undirected weighted graph and uses the Quantum Approximate Optimization
Algorithm (QAOA) to find a partition of the nodes into two sets S and T that
maximizes the total weight of the edges crossing between them.

The input is a dictionary:
    {'nodes': ['1', '2', ...],
     'edges': [['1', '2', 5], ['2', '3', 1.5], ...],
     'seed': 6680}
  each edge is [u, v] or [u, v, weight]; a missing weight is 1. 'seed' is
  optional (default SEED) and seeds the sampler, the only random step, so the
  same input and seed always give the same result.

The result is a dictionary:
    {'answer': '{1,3}' (the nodes on the S side, Redux certificate format),
     'cut_weight': total weight of the cut,
     'answer_bitstring': one character per node, '1' = in S,
     'seed': the seed used,
     'gammas': the optimized cost-layer angles, one per layer,
     'betas': the optimized mixer-layer angles, one per layer,
     'qasm': the optimized QAOA circuit, in h/cx/rz/rx gates}
  or {'error': message} for invalid input.
"""

import argparse
import itertools

import numpy as np
import requests
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit import ParameterVector
from qiskit.primitives import StatevectorEstimator, StatevectorSampler
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

# Statevector simulation costs 2^n per evaluation and COBYLA needs dozens of
# them, so keep instances well inside the router's 25 second timeout.
MAX_NODES = 16
REPS = 2
SHOTS = 10000
# The estimator is exact and COBYLA is deterministic, so sampling is the only
# random step; a fixed default seed makes every response reproducible.
SEED = 6680


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


def edge_rounds(weights):
    """Split the edges into rounds in which no two edges share a node (a greedy
    edge colouring), as [[(i, j, w), ...], ...]. Gates on one round's edges
    touch disjoint qubits, so they can run, and be drawn, side by side."""

    rounds = []
    for (i, j), w in sorted(weights.items()):
        for r in rounds:
            if not r["used"] & {i, j}:
                r["edges"].append((i, j, w))
                r["used"] |= {i, j}
                break
        else:
            rounds.append({"edges": [(i, j, w)], "used": {i, j}})
    return [r["edges"] for r in rounds]


def qaoa_circuit(n, weights, reps):
    """The QAOA ansatz for cost_hamiltonian(n, weights), built from h, cx, rz
    and rx so its QASM reads as the textbook circuit.

    Each layer k applies the cost unitary exp(-i gamma_k H), whose term
    (w / 2s) Z_i Z_j is RZZ(gamma_k w / s) = cx(i, j) rz(gamma_k w / s, j)
    cx(i, j), then the mixer exp(-i beta_k sum X) = rx(2 beta_k) on every
    qubit. This is the same state qaoa_ansatz builds, up to a global phase,
    and the parameters keep its names so they sort the same way:
    [beta[0..reps-1], gamma[0..reps-1]].
    """

    scale = max(abs(w) for w in weights.values())
    beta = ParameterVector("β", reps)
    gamma = ParameterVector("γ", reps)
    circuit = QuantumCircuit(n)
    circuit.h(range(n))
    for k in range(reps):
        for edges in edge_rounds(weights):
            for i, j, _ in edges:
                circuit.cx(i, j)
            for _, j, w in edges:
                circuit.rz(gamma[k] * w / scale, j)
            for i, j, _ in edges:
                circuit.cx(i, j)
        circuit.rx(2 * beta[k], range(n))
    return circuit


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

    seed = data.get("seed", SEED)
    # bool is an int subclass; numpy rejects negative seeds.
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        return {"error": f"invalid seed {seed!r}, need a non-negative integer"}

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
        # Built from standard gates, so the simulator runs it directly (no
        # PauliEvolutionGates to exponentiate on every COBYLA step).
        ansatz = qaoa_circuit(n, weights, REPS)

        # Same warm start as the notebook: midpoints of the beta and gamma
        # periods. The parameters sort as [betas..., gammas...].
        init_params = [np.pi / 2] * REPS + [np.pi] * REPS

        estimator = StatevectorEstimator()

        def cost(params):
            result = estimator.run([(ansatz, hamiltonian, params)]).result()
            return float(result[0].data.evs)

        result = minimize(cost, init_params, method="COBYLA", tol=1e-2)

        circuit = ansatz.assign_parameters(result.x)
        circuit.measure_all()
        counts = (
            StatevectorSampler(seed=seed)
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
        "seed": seed,
    }
    if circuit is not None:
        r["betas"] = [float(b) for b in result.x[:REPS]]
        r["gammas"] = [float(g) for g in result.x[REPS:]]
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
