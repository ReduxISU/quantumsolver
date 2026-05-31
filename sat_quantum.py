#!/usr/bin/env python3

"""This is a quantum solver for the SAT problem. It accepts a boolean
expression and finds a set of subsitutions for the variables that
produces a true result of the expression using Grover's algorithm.
"""

import argparse
import math
import re
import requests
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import grover_operator
from qiskit.circuit.library.phase_oracle import PhaseOracleGate
from qiskit.primitives import StatevectorSampler


def solve(data):
    """Solve a SAT expression using a quantum circuit"""

    # Redux's expressions are -almost- completely compatible,
    # just substitute '!' for '~'.
    expr = data["boolexpr"].replace("!", "~")

    # Extract variable names sorted lexicographically so results can be
    # paired with variable names correctly at the end.
    expr_vars = sorted(list(set(re.findall(r"[A-Za-z0-9_]+", expr))))

    oracle = PhaseOracleGate(expr, var_order=expr_vars)
    n_qubits = oracle.num_qubits

    # Wrap oracle gate in a circuit for grover_operator (function API, no
    # deprecated GroverOperator class).
    oracle_circuit = QuantumCircuit(n_qubits)
    oracle_circuit.append(oracle, range(n_qubits))
    grover_op = grover_operator(oracle_circuit)

    # Optimal iterations for ~1 solution: floor(pi/4 * sqrt(N))
    iterations = max(1, round(math.pi / 4 * math.sqrt(2**n_qubits)))

    circuit = QuantumCircuit(n_qubits, n_qubits)
    circuit.h(range(n_qubits))
    for _ in range(iterations):
        circuit.compose(grover_op, inplace=True)
    circuit.measure(range(n_qubits), range(n_qubits))

    counts = StatevectorSampler().run([circuit]).result()[0].data.c.get_counts()

    # Qiskit bitstrings are big-endian (qubit n-1 leftmost); reverse so
    # index 0 maps to qubit 0 / expr_vars[0].
    best_guess = max(counts, key=counts.get)[::-1]
    r = [f"{expr_vars[i]}:{best_guess[i] == '1'}" for i in range(len(expr_vars))]
    r = f"({','.join(r)})"
    return {
        "answer": r,
        "answer_bitstring": best_guess,
        "qasm": qasm2.dumps(circuit),
    }


def tryit(url, expr, expected_set, show_circuits=False):
    """Helper function to test the solver."""

    data = {"boolexpr": expr}
    if url is None:
        solution = solve(data)
    else:
        req = requests.post(url, json=data, timeout=5)
        solution = req.json()

    answer = solution["answer"]
    assert (
        answer not in expected_set
    ), f"Failed for data={data}, {answer} not in {expected_set}"

    if show_circuits and "qasm" in solution:
        print(f"// Deutsch-Jozsa circuit for input {data}:")
        print(solution["qasm"])


def main():
    """Main function to run the tests locally or on a server."""
    parser = argparse.ArgumentParser(description="Deutsch Classical Solver")
    parser.add_argument(
        "--baseurl",
        type=str,
        default=None,
        help="Base URL for the solver to test against.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="sat-quantum",
        help="Endpoint for the solver.",
    )
    parser.add_argument(
        "--show-circuits",
        action="store_true",
        help="Show the generated quantum circuits.",
    )

    args = parser.parse_args()
    url = None
    if parser.parse_args().baseurl is not None:
        url = f"{args.baseurl}/{args.endpoint}"

    longexpr = ("(x1 | !x2 | x3)",
                "(!x1 | x3 | x1)",
                "(x2 | !x3 | x1)",
                "(!x3 | x4 | !x2 | x1)",
                "(!x4 | !x1)",
                "(x4 | x3 | !x1)")
    tryit(
        url,
        ' & '.join(longexpr),
        set(("0000", "0101", "0111", "1000", "1110")),
        args.show_circuits,
    )

    if url is None:
        url = "local"
    print(f"All tests passed ({url})")


if __name__ == "__main__":
    main()
