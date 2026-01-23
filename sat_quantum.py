#!/usr/bin/env python3

"""This is a quantum solver for the SAT problem. It accepts a boolean
expression and finds a set of subsitutions for the variables that
produces a true result of the expression using Grover's algorithm.

It is based on the tutorial on:
https://qiskit-community.github.io/qiskit-algorithms/tutorials/07_grover_examples.html
"""

import argparse
import re
import requests
from qiskit import qasm2
from qiskit.circuit.library.phase_oracle import PhaseOracleGate
from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import AmplificationProblem, Grover


def solve(data):
    """Solve a SAT expression using a quantum circuit"""

    # Redux's expressions are -almost- completely compatible,
    # just substitue '!' for '~'.
    expr = data["boolexpr"].replace("!", "~")

    # extract the variable names and sort them in lexicographic order.
    # this is so we can marry the results with the variable names
    # correctly at the end
    expr_vars = sorted(list(set(re.findall(r"[A-Za-z0-9_]+", expr))))

    # create a phase gate oracle from the boolean expression and
    # do that crazy Grover thing.
    oracle = PhaseOracleGate(expr, var_order=expr_vars)
    problem = AmplificationProblem(oracle)
    grover = Grover(sampler=StatevectorSampler())
    result = grover.amplify(problem)

    # reverse the string and pair it with the variable names
    best_guess = result.top_measurement[::-1]
    r = [f"{expr_vars[i]}:{best_guess[i] == '1'}" for i in range(len(expr_vars))]
    r = ",".join(r)
    r = f"({r})"
    return {
        "answer": r,
        "answer_bitstring": best_guess,
        "qasm": qasm2.dumps(grover.construct_circuit(problem, 4, True)),
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

    tryit(
        url,
        "(x1 | !x2 | x3) & (!x1 | x3 | x1) & (x2 | !x3 | x1) & (!x3 | x4 | !x2 | x1) & (!x4 | !x1) & (x4 | x3 | !x1)",
        set(("0000", "0101", "0111", "1000", "1110")),
        args.show_circuits,
    )

    if url is None:
        url = "local"
    print(f"All tests passed ({url})")


if __name__ == "__main__":
    main()
