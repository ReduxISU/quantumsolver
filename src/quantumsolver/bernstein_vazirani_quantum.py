"""The input to this solver is a json schema:
{'nbits': N,
 'f': [a list of bits (0's and 1's) where f[x] is f(x)]}

 This uses a quantum algorithm to find a binary string S of length N such that
  f(x) = S XOR x for all x in 0..2^N

 There is a promise that there is such an S.

 This code can also generate all possible problem instances for a given N
 (in other words, it generates a description of the function f for all possible S).
"""

import argparse
import json

import requests
from qiskit import QuantumCircuit, qasm2
from qiskit_aer import AerSimulator

from quantumsolver.bits import power_of_two_info


def bv_query(s):
    """Create a quantum circuit implementing a query gate for the
    Bernstein-Vazirani problem."""

    qc = QuantumCircuit(len(s) + 1)
    for index, bit in enumerate(reversed(s)):
        if bit == "1":
            qc.cx(index, len(s))
    return qc


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


def bv_algorithm(function: QuantumCircuit):
    """Runs the Bernstein-Vazirani algorithm using the given function"""
    qc = compile_circuit(function)
    result = AerSimulator().run(qc, shots=1, memory=True).result()
    return (result.get_memory()[0], qc)


def solve(data) -> dict:
    """returns the answer as a binary string"""

    if isinstance(data, list):
        fbits = [bool(x) for x in data]
        ispower2, nbits = power_of_two_info(len(fbits))
        if not ispower2:
            return {"answer": "function length is not power of 2"}
    else:
        nbits = data["nbits"]
        fbits = [bool(x) for x in data["f"]]
        if 2**nbits != len(fbits):
            return {
                "answer": f"invalid function length {len(fbits)} != 2^nbits {2**nbits}"
            }

    def f(x: int) -> bool:
        if x < 0 or x >= len(fbits):
            return False
        return fbits[x]

    bit_string = ["1" if f(1 << i) else "0" for i in range(nbits)]
    bit_string = "".join(reversed(bit_string))

    answer, circuit = bv_algorithm(bv_query(bit_string))
    return {"answer": answer, "qasm": qasm2.dumps(circuit)}


def generate(nbits, s):
    """Generates a Bernstein-Vazirani problem instance with hidden string 's'."""
    assert len(s) == nbits
    ftrue = set()

    si = int(s, 2)
    for i in range(2**nbits):
        if ((si & i).bit_count() % 2) == 1:
            ftrue.add(i)

    return (nbits, s, ftrue)


def generate_all(nbits):
    """Yields all possible problem instances for nbits."""
    for i in range(2**nbits):
        s = f"{i:b}".zfill(nbits)
        yield generate(nbits, s)


def tryit(url, nbits, ftrue, expected_s, show_circuits=False):
    """Helper function to test the solver."""

    tryit_oldstyle(url, nbits, ftrue, expected_s, show_circuits)

    data = ftrue
    if url is None:
        solution = solve(data)
    else:

        req = requests.post(url, json=data, timeout=5)
        solution = req.json()

    answer = solution["answer"]
    assert (
        answer == expected_s
    ), f"Failed for nbits={nbits}, ftrue={ftrue}, expected_s={expected_s}, got {answer}"
    if show_circuits:
        print(f"// Bernstein-Vazirani circuit for nbits={nbits}, s={expected_s}:")
        print(solution["qasm"])


def tryit_oldstyle(url, nbits, ftrue, expected_s, show_circuits=False):
    """Helper function to test the solver."""

    data = {"nbits": nbits, "f": list(ftrue)}
    if url is None:
        solution = solve(data)
    else:

        req = requests.post(url, json=data, timeout=5)
        solution = req.json()

    answer = solution["answer"]
    assert (
        answer == expected_s
    ), f"Failed for nbits={nbits}, ftrue={ftrue}, expected_s={expected_s}, got {answer}"
    if show_circuits:
        print(f"// Bernstein-Vazirani circuit for nbits={nbits}, s={expected_s}:")
        print(solution["qasm"])


def main():
    """Main function to either run tests or generate problem instances."""

    parser = argparse.ArgumentParser(
        description="Run the Bernstein-Vazirani quantum algorithm."
    )
    parser.add_argument(
        "--generate",
        type=int,
        required=False,
        default=None,
        help="The size of the problem to generate.",
    )
    parser.add_argument(
        "--show-circuits",
        action="store_true",
        help="Show the generated quantum circuits during tests.",
    )
    parser.add_argument(
        "--baseurl",
        type=str,
        default=None,
        help="Base URL for the quantum solver server.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="bernstein-vazirani-quantum",
        help="Endpoint for the quantum solver.",
    )
    args = parser.parse_args()

    # if we're not generating a problem, run tests
    fullurl = None
    if args.baseurl is not None:
        fullurl = f"{args.baseurl}/{args.endpoint}"

    if args.generate is None:
        tryit(fullurl, 3, [0, 1, 0, 1, 1, 0, 1, 0], "101", args.show_circuits)
        tryit(fullurl, 3, [0, 1, 1, 0, 1, 0, 0, 1], "111", args.show_circuits)
        tryit(fullurl, 3, [1, 0, 0, 1, 0, 1, 1, 0], "000", args.show_circuits)
        tryit(fullurl, 3, [0, 1, 0, 1, 0, 1, 0, 1], "001", args.show_circuits)
        if fullurl is None:
            fullurl = "local"
        print(f"All tests passed ({fullurl})")
        return

    for nbits, s, ftrue in generate_all(args.generate):
        a = {"nbits": nbits, "f": list(ftrue), "s": s}
        print(json.dumps(a))


if __name__ == "__main__":
    main()
