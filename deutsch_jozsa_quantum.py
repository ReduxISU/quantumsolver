"""
Deutsch-Jozsa problem quantum solver.

In this problem the input is a function f:{0,1}^n -> {0,1} which is either
constant (all outputs are the same) or balanced (half the outputs are 0, half
are 1).

The input to this solver is either a list:
    [0, 1, 0, 1, ...]
  list[i] represents f(i) and must be a power of 2 in size

OR, the input can be a dictionary:
    {'nbits': N,
     'values': [a list of integers of length 2^N, values[i] represents f(i)]}

The result is a dictionary:
    {'answer': 'constant' or 'balanced', or an error message}
"""

import argparse
import requests
from qiskit import QuantumCircuit, qasm2
from qiskit_aer import AerSimulator
from bits import power_of_two_info


def dj_algorithm(function: QuantumCircuit):
    """Determine if a function is constant or balanced."""

    qc = compile_circuit(function)
    result = AerSimulator().run(qc, shots=1, memory=True).result()
    measurements = result.get_memory()
    return ("balanced", qc) if "1" in measurements[0] else ("constant", qc)


def compile_circuit(function: QuantumCircuit):
    """Compiles a circuit for use in the Deutsch-Jozsa algorithm."""

    n = function.num_qubits - 1
    qc = QuantumCircuit(n + 1, n)
    qc.x(n)
    qc.h(range(n + 1))
    qc.compose(function, inplace=True)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def dj_constant(num_qubits, output=True):
    """Return a constant DJ function circuit."""

    qc = QuantumCircuit(num_qubits + 1)
    if output:
        qc.x(num_qubits)
    return qc


def dj_balanced(num_qubits, fbits):
    """Return a balanced DJ function circuit."""

    qc = QuantumCircuit(num_qubits + 1)

    def add_cx(qc, bit_string):
        for qubit, bit in enumerate(reversed(bit_string)):
            if bit == "1":
                qc.x(qubit)
        return qc

    for state, fbit in enumerate(fbits):
        if fbit:
            qc.barrier()
            qc = add_cx(qc, f"{state:0b}")
            qc.mcx(list(range(num_qubits)), num_qubits)
            qc = add_cx(qc, f"{state:0b}")

    qc.barrier()
    return qc


def solve(data) -> dict:
    """Solves the Deutsch-Jozsa problem for the given function data.
    The input data is a json schema like this (old style):
    {'nbits': N,
     'f': [list of integers of length 2^nbits: f[x] = f(x) = {0, 1}}
    or (new style): just a list [0, 1, ...] where the position i is f(i)
    """

    if isinstance(data, list):
        # If we're given just a list, assume it is f's values
        fbits = [bool(x) for x in data]
        ispower2, nbits = power_of_two_info(len(fbits))
        if not ispower2:
            return {"answer": "invalid function length, need power of 2"}
    else:
        nbits = data["nbits"]
        fbits = [bool(x) for x in data["f"]]
        if 2**nbits != len(fbits):
            return {
                "answer": f"invalid function length {len(fbits)} != 2^nbits {2**nbits}"
            }

    if sum(fbits) == 0:
        func = dj_constant(nbits, output=False)
    elif len(fbits) == sum(fbits):
        func = dj_constant(nbits, output=True)
    else:
        func = dj_balanced(nbits, fbits)

    answer, qc = dj_algorithm(func)
    return {"answer": answer, "qasm": qasm2.dumps(qc)}


def testit(url, data, expected, show_circuits=False):
    """Test the deutsch-jozsa solver with given data and expected result."""

    if url is None:
        result = solve(data)
    else:
        req = requests.post(url, json=data, timeout=5)
        assert req.status_code == 200, f"HTTP error {req.status_code} for data={data}"
        result = req.json()

    assert (
        result["answer"] == expected
    ), f"expected {expected}, got {result['answer']} for {data}"
    if show_circuits and "qasm" in result:
        print(f"// Deutsch-Jozsa circuit for input {data}:")
        print(result["qasm"])


def main():
    """Internal/server testing of solver"""
    parser = argparse.ArgumentParser(description="Deutsch-Jozsa Quantum Solver")
    parser.add_argument(
        "--baseurl",
        type=str,
        default=None,
        help="Base URL for the quantum solver to test against.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="deutsch-jozsa-quantum",
        help="Endpoint for the classical solver.",
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

    # new style tests
    testit(url, [0, 0, 0, 0, 0, 0, 0, 0], "constant", args.show_circuits)
    testit(url, [1, 1, 1, 1, 1, 1, 1, 1], "constant", args.show_circuits)
    testit(url, [0, 1, 0, 1, 1, 0, 1, 0], "balanced", args.show_circuits)
    testit(url, [0, 1, 1, 0, 1, 0, 0, 1], "balanced", args.show_circuits)

    # old style tests
    testit(
        url, {"nbits": 3, "f": [0, 0, 0, 0, 0, 0, 0, 0]}, "constant", args.show_circuits
    )
    testit(
        url, {"nbits": 3, "f": [1, 1, 1, 1, 1, 1, 1, 1]}, "constant", args.show_circuits
    )
    testit(
        url,
        {"nbits": 3, "f": [0, 1, 0, 1, 1, 0, 1, 0]},
        "balanced",
        args.show_circuits,
    )
    testit(
        url,
        {"nbits": 3, "f": [0, 1, 1, 0, 1, 0, 0, 1]},
        "balanced",
        args.show_circuits,
    )
    if url is None:
        url = "local"
    print(f"All tests passed ({url})")


if __name__ == "__main__":
    main()
