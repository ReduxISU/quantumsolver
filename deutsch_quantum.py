"""
Deutsch Quantum Solver

Input - list
Representing the states of 2 bits
[0,0], [0,1], [1,0], [1,1]


Output - dictionary
{'answer': 'constant' or 'balanced'}
"""

import argparse
from qiskit import QuantumCircuit, qasm2
from qiskit_aer import AerSimulator


def deutsch_function(case: int) -> QuantumCircuit:
    """
    Creates a quantum circuit just for the oracle
    Depending on the state given:
    f1 - Do nothing
    f2 - CNOT
    f3 - CNOT, Not
    f4 - Not
    """
    if case not in [1, 2, 3, 4]:
        raise ValueError("'case' must be 1, 2, 3, or 4")

    f = QuantumCircuit(2)
    if case in [2, 3]:
        f.cx(0, 1)
    if case in [3, 4]:
        f.x(1)
    return f


def compile_circuit(function: QuantumCircuit) -> QuantumCircuit:
    """
    Builds the circuit around the oracle
    """
    # create circuit with 2 qubits and 1 classial bit.
    n = function.num_qubits - 1
    qc = QuantumCircuit(n + 1, n)

    # prepare |1>, and put both qubits in superpostition
    qc.x(n)
    qc.h(range(n + 1))

    # apply the oracle
    qc.compose(function, inplace=True)

    # hadamard on the first qubit and measure
    qc.h(range(n))
    qc.measure(range(n), range(n))

    return qc


def deutsch_algorithm(function: QuantumCircuit) -> tuple[dict, QuantumCircuit]:
    """
    Runs the compiled circuit (with oracle) in the Qiskit simulator.

    Returns:
        (result_dict, qc)
        result_dict: {'answer': 'constant' or 'balanced'}
        qc: the QuantumCircuit that was executed
    """
    qc = compile_circuit(function)
    result = AerSimulator().run(qc, shots=1, memory=True).result()
    measurements = result.get_memory()
    answer = "constant" if measurements[0] == "0" else "balanced"
    return {"answer": answer}, qc


def export_qasm(qc: QuantumCircuit) -> str:
    """
    Export a Qiskit circuit to QASM
    """
    return qasm2.dumps(qc)


def solve(data: list) -> dict:
    """
    Main entry point
    Determine which case is given by the input

    Returns a JSON-ready dictionary with:
    {
        "answer": "...",
        "qasm" : "..."
    }
    """
    # Determine oracle
    if data[0]:
        if data[1]:
            f = deutsch_function(4)  # [1, 1] f4
        else:
            f = deutsch_function(3)  # [1, 0] f3
    else:
        if data[1]:
            f = deutsch_function(2)  # [0, 1] f2
        else:
            f = deutsch_function(1)  # [0, 0] f1

    # Run algorithm
    result, qc = deutsch_algorithm(f)

    # Attach QASM circuit
    result["qasm"] = export_qasm(qc)

    return result


def main():
    """
    Internal testing + optional ASCII and QASM visualization
    python deutsch_quantum.py --show-circuits
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-circuits", action="store_true")
    args = parser.parse_args()

    # Run tests via solve
    assert solve([0, 0])["answer"] == "constant"  # f1
    assert solve([0, 1])["answer"] == "balanced"  # f2
    assert solve([1, 0])["answer"] == "balanced"  # f3
    assert solve([1, 1])["answer"] == "constant"  # f4
    print("All tests passed")

    # Optional debugging display
    if args.show_circuits:
        print("\n--- Debug: Showing All 4 Oracle Circuits ---\n")

        for case in [1, 2, 3, 4]:
            f = deutsch_function(case)
            result, qc = deutsch_algorithm(f)

            print(f"Oracle f{case}:")
            print("Answer:", result["answer"])
            print("QASM snippet:")
            print(export_qasm(qc)[:200], "...\n")


if __name__ == "__main__":
    main()
