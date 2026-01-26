"""
Shor's Algorithm Quantum Solver (Recursive Prime Factorization)
George Lake - December 2025

This program implements the full Shor's algorithm procedure:
1. Classical checks for primality, even numbers, and perfect powers.
2. Quantum Period Finding (Order Finding) to find a split for composite numbers
3. Recursive decomposition untill all factors are prime

Notes on Visualization:
1. N = 15, this program returns the actual quantum circuit built,
   showing the QPE made of controlled swap gates.
2. N != 15, this program returns a dummy quantum circuit,
   that is easier to visualize using QASM.
3. This program returns nothing (in terms of visualization) when the factorization was trivial.
   (even, prime, perfect powers)

Hard Limit = N < 10 bits (example N <= 511)
Note: As numbers get above 7 bits in size, this algorithm can take longer than 30 seconds to run.
"""

import argparse
import math
import random
from fractions import Fraction

import numpy as np
import qiskit.qasm2
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit import Gate
from qiskit.circuit.library import QFTGate, UnitaryGate
from qiskit_aer import AerSimulator

# --------------------------------------------------
#                 Circuits
# --------------------------------------------------


class ShorCircuit(QuantumCircuit):
    """
    Generic Quantum Circuit for Shor's Algorithm (The "Math" Circuit).
    Uses unitary matrices to implement modular exponentiation for any N.

    Args:
        a (int): The base integer for modular exponentiation.
        N (int): The integer to be factored.
    """

    def __init__(self, a, n):
        # Calculate required qubits
        self.n_target = n.bit_length()
        self.n_count = 2 * self.n_target
        total_qubits = self.n_count + self.n_target

        super().__init__(total_qubits, self.n_count)

        self.a = a
        self.n = n

        self._create_circuit()

    def _get_controlled_unitary_matrix(self, power_of_a):
        """
        Creates the controlled unitary matrix for f(y) = a^(2^i) * y mod N.
        This matrix represents the modular exponentiation operation.

        Args:
            power_of_a (int): The exponent 2^i corresponding to the control qubit index.

        Returns:
            UnitaryGate: A custom gate implementing the controlled modular exponentiation.
        """
        dim_target = 2**self.n_target
        u_matrix = np.zeros((dim_target, dim_target), dtype=complex)

        # 1. Calculate the effective multiplier: a^(2^i) mod N
        effective_multiplier = pow(self.a, power_of_a, self.n)

        # 2. Build the permutation matrix for the modular multiplication
        for y in range(dim_target):
            if y < self.n:
                target_y = (effective_multiplier * y) % self.n
            else:
                target_y = y
            u_matrix[target_y, y] = 1

        # 3. Create the Controlled-U matrix (block diagonal)
        cu_matrix = np.block(
            [
                [np.eye(dim_target), np.zeros((dim_target, dim_target))],
                [np.zeros((dim_target, dim_target)), u_matrix],
            ]
        )

        return UnitaryGate(cu_matrix, label=f"C-U{power_of_a}")

    def _create_circuit(self):
        """
        Constructs the full quantum circuit.
        """
        # 1. Initialize counting qubits to superposition state |+>
        self.h(range(self.n_count))

        # 2. Initialize target qubit to state |1> (eigenstate for modulo multiplication)
        self.x(self.num_qubits - 1)

        # 3. Apply sequence of Controlled-U operations
        for i in range(self.n_count):
            power_of_a = 2**i
            cu_gate = self._get_controlled_unitary_matrix(power_of_a)
            target_qubits = list(range(self.n_count, self.num_qubits))
            control_qubit = i
            self.append(cu_gate, target_qubits + [control_qubit])

        # 4. Apply Inverse Quantum Fourier Transform (IQFT) to counting register
        qft_gate = QFTGate(self.n_count).inverse()
        self.append(qft_gate, range(self.n_count))

        # 5. Measure the counting qubits
        self.measure(range(self.n_count), range(self.n_count))

    def run_simulation(self, simulator):
        """
        Simulates the circuit once to measure the phase.

        Args:
            simulator: The backend simulator to run the circuit on.

        Returns:
            Result: The simulation result object containing counts/memory.
        """
        transpiled_circuit = transpile(self, simulator)
        result = simulator.run(transpiled_circuit, shots=1, memory=True).result()
        return result


class ShorN15Circuit(QuantumCircuit):
    """
    Specific implementation for N=15, a=2 using C-SWAP gates.

    Args:
        a (int): Base integer (strictly 2 for this implementation).
        N (int): Number to factor (strictly 15).
    """

    def __init__(self, a, n):
        if n != 15 or a != 2:
            raise ValueError("ShorN15Circuit is strictly for N=15 and a=2.")

        self.n_target = 4
        self.n_count = 8
        total_qubits = self.n_count + self.n_target
        super().__init__(total_qubits, self.n_count)
        self.a = a
        self.n = n
        self._create_circuit()

    def _apply_manual_gates(self, ctrl_qubit, stage_index):
        """
        Applies manual Controlled-SWAP gates to implement modular exponentiation for a=2, N=15.

        Args:
            ctrl_qubit (int): Index of the control qubit.
            stage_index (int): The current stage of exponentiation.
        """
        t = list(range(self.n_count, self.num_qubits))

        # Logic derived from specific N=15, a=2 decomposition
        if stage_index == 0:
            self.cswap(ctrl_qubit, t[2], t[3])
            self.cswap(ctrl_qubit, t[1], t[2])
            self.cswap(ctrl_qubit, t[0], t[1])
        elif stage_index == 1:
            self.cswap(ctrl_qubit, t[0], t[2])
            self.cswap(ctrl_qubit, t[1], t[3])

    def _create_circuit(self):
        """
        Constructs the specialized circuit using C-SWAPs.
        """
        # 1. Initialize counting register to superposition |+>
        self.h(range(self.n_count))

        # 2. Initialize target register to |1>
        self.x(self.num_qubits - 1)

        # 3. Apply manual modular exponentiation gates
        # Manual gates for the first two control qubits for a=2, N=15
        # Higher powers result in Identity operations for this specific case.
        for i in range(self.n_count):
            self._apply_manual_gates(i, i)

        # 4. Inverse QFT
        qft_gate = QFTGate(self.n_count).inverse()
        self.append(qft_gate, range(self.n_count))

        # 5. Measurement
        self.measure(range(self.n_count), range(self.n_count))

    def run_simulation(self, simulator):
        """
        Simulates the circuit to get a measurement result.

        Args:
            simulator: The backend simulator.

        Returns:
            Result: Simulation result.
        """
        transpiled_circuit = transpile(self, simulator)
        result = simulator.run(transpiled_circuit, shots=1, memory=True).result()
        return result


class ShorDisplayCircuit(QuantumCircuit):
    """
    Dummy circuit strictly for visualization/QASM.
    Uses compact Opaque Gates to avoid visual clutter.

    Args:
        a (int): Base integer.
        N (int): Number to factor.
    """

    def __init__(self, a, n):
        self.n_target = n.bit_length()
        self.n_count = 2 * self.n_target
        qr_count = QuantumRegister(self.n_count, "cnt")
        qr_target = QuantumRegister(self.n_target, "tgt")
        cr = ClassicalRegister(self.n_count, "meas")

        super().__init__(qr_count, qr_target, cr)

        self.a = a
        self.n = n
        self._build_visual_only()

    def _build_visual_only(self):
        """
        Constructs the dummy circuit with opaque gates.
        This includes initialization, opaque modular exponentiation gates, and opaque inverse QFT.
        """
        # 1. Initialization
        self.h(self.qubits[: self.n_count])
        self.x(self.qubits[-1])

        # 2. Add Opaque Oracle Gates
        for i in range(self.n_count):
            power = 2**i

            qasm_name = f"U{power}"
            oracle_gate = Gate(name=qasm_name, num_qubits=self.n_target + 1, params=[])
            oracle_gate.label = f"U^{power}"
            control_qubit = [self.qubits[i]]
            target_qubits = self.qubits[self.n_count :]

            self.append(oracle_gate, control_qubit + target_qubits)

        # 3. Add Opaque Inverse QFT
        iqft_gate = Gate(name="iqft", num_qubits=self.n_count, params=[])
        iqft_gate.label = "IQFT"
        self.append(iqft_gate, self.qubits[: self.n_count])

        # 4. Measure
        self.measure(self.qubits[: self.n_count], self.clbits)


# --------------------------------------------------
#                 Algorithm
# --------------------------------------------------


class ShorAlgorithm:
    """
    Completes the full prime factorization using Shor's Algorithm.
    Recursively splits factors until only primes remain.

    Args:
        N (int): The number to be factored.
        circuit_class (class): The class to use for building quantum circuits. N=15 or N!=15
        max_attempts (int): Maximum attempts for the quantum step per recursive call.
        simulator: The backend simulator instance.
    """

    def __init__(self, n, circuit_class=ShorCircuit, max_attempts=-1, simulator=None):
        self.n = n
        self.circuit_class = circuit_class
        self.simulator = simulator if simulator else AerSimulator()
        self.max_attempts = max_attempts
        self.chosen_a = None
        self.r = None
        self.qpe_circuit = None

    def _is_prime(self, n):
        """
        Checks if a number is prime using simple trial division.
        """
        if n < 2:
            return False
        if n in (2, 3):
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(n**0.5) + 1, 2):
            if n % i == 0:
                return False
        return True

    def _check_perfect_power(self, n):
        """
        Checks if n is a perfect power (n = b^k).
        Returns the base 'b' if true, else None.
        """
        k_max = int(math.log2(n))
        for k in range(2, k_max + 1):
            root = round(n ** (1 / k))
            if root**k == n:
                return root
        return None

    def get_prime_factors(self):
        """
        Public method to start the recursive factoring process.
        Returns a list of sorted prime factors.
        """
        #print(f"--- Factoring N={self.n} ---")
        return sorted(self._recursive_factor(self.n))

    def _recursive_factor(self, current_n):
        """
        Recursively decomposes the number into prime factors.

        Args:
            current_n (int): The current number to split.

        Returns:
            list: A list of prime factors.
        """
        # Step 1: Base case for recursion
        if current_n == 1:
            return []
        if self._is_prime(current_n):
            #print(f"[Base Case] {current_n} is prime.")
            return [current_n]

        # Step 2: Classical Checks
        # Check if even
        if current_n % 2 == 0:
            #print(f"[Classical] {current_n} is even. Split into 2 and {current_n//2}.")
            return [2] + self._recursive_factor(current_n // 2)

        # Check perfect powers
        base = self._check_perfect_power(current_n)
        if base:
            exponent = int(round(math.log(current_n, base)))
            #print(f"[Classical] {current_n} is a perfect power ({base}^{exponent}).")
            factors = []
            for _ in range(exponent):
                factors.extend(self._recursive_factor(base))
            return factors

        # Step 3: Quantum Period Finding
        #print(
        #   f"[Quantum] Attempting to split {current_n} using Quantum Period Finding..."
        #)
        factor_a, factor_b = self._attempt_quantum_split(current_n)

        if factor_a and factor_b:
            #print(f"[Split Found] {current_n} -> {factor_a} * {factor_b}")
            return self._recursive_factor(factor_a) + self._recursive_factor(factor_b)
        #print(f"[Fail] Could not split {current_n} quantumly. Returning as is.")
        return [current_n]

    def _attempt_quantum_split(self, n_to_split):
        """
        Attempts to find a non-trivial factor of n_to_split using the quantum period algorithm.

        Args:
            n_to_split (int): The composite number to factor.

        Returns:
            tuple: (factor_1, factor_2) if successful, else (None, None).
        """
        # Step 1: Pick a random 'a' co-prime to N.
        candidates = [a for a in range(2, n_to_split) if math.gcd(a, n_to_split) == 1]

        # For specific demo N=15, limit candidates to ensure consistent results
        if n_to_split == 15 and self.circuit_class == ShorN15Circuit:
            candidates = [2]

        if not candidates:
            return None, None

        # Determine attempt limit
        if self.max_attempts > 0:
            limit = min(self.max_attempts, len(candidates))
        else:
            limit = len(candidates)

        attempts_count = 0

        # Step 2: Loop through attempts with different 'a' values
        while attempts_count < limit and candidates:
            attempts_count += 1
            self.chosen_a = random.choice(candidates)
            candidates.remove(self.chosen_a)

            #print(f"  Attempt {attempts_count} (a={self.chosen_a})")

            # Step 3: Run Quantum Circuit (Period Finding)
            circuit_cls = self.circuit_class
            # Fallback to generic circuit if specialized one doesn't apply
            if n_to_split != 15 and circuit_cls == ShorN15Circuit:
                circuit_cls = ShorCircuit

            self.qpe_circuit = circuit_cls(self.chosen_a, n_to_split)
            result = self.qpe_circuit.run_simulation(self.simulator)

            # Step 4: Process Measurement to find Order 'r'
            readout = result.get_memory()[0]
            phase = int(readout, 2) / (2**self.qpe_circuit.n_count)
            frac = Fraction(phase).limit_denominator(n_to_split)
            r_measured = frac.denominator
            #print(f"  -> Measured Phase: {phase:.4f} (~{frac}) -> Denom r={r_measured}")

            # Verify if r is actually the period.
            # The Quantum Phase Estimation might return a factor of the true period (e.g., r/2).
            r_true = None
            for k in range(1, 5):
                r_candidate = r_measured * k
                if r_candidate > 0 and pow(self.chosen_a, r_candidate, n_to_split) == 1:
                    r_true = r_candidate
                    if k > 1:
                        #print(
                        #   f"  [+] Found true period r={r_true} (using multiple {k} * {r_measured})"
                        #)
                        pass
                    break

            if r_true is None:
                #print(
                #    f"  [-] Measured r={r_measured} is invalid (a^r != 1 mod N). Retry."
                #)
                continue

            r = r_true

            # Step 5: Validate Order 'r' properties for factoring
            if r % 2 != 0:
                #print(f"  -> Period r={r} is odd. Cannot split N. Retry.")
                continue

            # Check if a^(r/2) == -1 (mod N). If so, the factors will be trivial.
            half_power = pow(self.chosen_a, r // 2, n_to_split)
            if half_power == n_to_split - 1:
                #print(
                #    f"  -> Period r={r} yields trivial factors (a^(r/2) = -1 mod N). Retry."
                #)
                continue

            # Step 6: Calculate Factors using gcd(a^(r/2) ± 1, N)
            guess_1 = math.gcd(half_power - 1, n_to_split)
            guess_2 = math.gcd(half_power + 1, n_to_split)

            # Check if we found non-trivial factors
            if guess_1 not in [1, n_to_split]:
                return guess_1, n_to_split // guess_1
            if guess_2 not in [1, n_to_split]:
                return guess_2, n_to_split // guess_2

            #print("  -> Trivial factors found. Retry.")

        # Return failure if loop finishes without success
        return None, None


# --------------------------------------------------
#                 MAIN Entry
# --------------------------------------------------


def solve(n: int | dict) -> dict:
    """
    Main entry point for the Shor's Algorithm solver.

    Args:
        n (int | dict): The integer to factor (or a dict containing "N").

    Returns:
        dict: A dictionary containing the list of prime factors and the QASM string.
              Format: {"answer": [p1, p2...], "qasm": "..."}
    """
    # Step 1: Parse Input
    n_val = n["N"] if isinstance(n, dict) else n

    if not isinstance(n_val, int):
        return {"answer": "Input must be an integer", "qasm": "NA"}

    # Hard Limit: N must be < 10 bits (example, N <= 511)
    if n_val.bit_length() >= 10:
        return {"answer": "Input too large (limit < 10 bits)", "qasm": "NA"}

    # Step 2: Select Circuit Strategy
    # Usage of specialized circuit for N=15 vs generic for others
    if n_val == 15:
        selected_circuit = ShorN15Circuit
    else:
        selected_circuit = ShorCircuit

    # Step 3: Run Shor's Algorithm
    simulator = AerSimulator()
    shor_calc = ShorAlgorithm(
        n_val, circuit_class=selected_circuit, max_attempts=-1, simulator=simulator
    )

    factors = shor_calc.get_prime_factors()

    # Step 4: Generate QASM for Visualization
    qasm_string = "No Quantum Circuit needed (Solved Classically)"

    try:
        # Case A: Special N=15 (Real circuit)
        if n_val == 15 and shor_calc.qpe_circuit:
            qasm_string = qiskit.qasm2.dumps(shor_calc.qpe_circuit)

        # Case B: All others (Dummy Display Circuit)
        elif n_val > 3:
            a_vis = shor_calc.chosen_a if shor_calc.chosen_a else 2
            dummy_circuit = ShorDisplayCircuit(a=a_vis, n=n_val)
            qasm_string = qiskit.qasm2.dumps(dummy_circuit)

    except (TypeError, ValueError, AttributeError) as e:
        qasm_string = f"Error generating QASM: {e}"

    return {"answer": factors, "qasm": qasm_string}

def testit(n, expected):
    """ test shor's algorithm """
    result = solve(n)
    answer = result["answer"]
    assert answer == expected, f"Failed for N={n}, got {answer}, expected {expected}"


def main():
    """ run tests and such """
    parser = argparse.ArgumentParser(description="Shor's Algorithm Quantum Solver")
    parser.add_argument(
        "N", type=int, nargs="*", help="The integer N to factor"
    )
    args = parser.parse_args()
    if len(args.N) == 0:
        # Run tests
        testit(15, [3, 5])
        testit(21, [3, 7])
        testit(77, [7, 11])
        testit(85, [5, 17])
        testit(105, [3, 5, 7])
        testit(81, [3,3,3,3])
        testit(29, [29])
        testit(89, [89])
    else:
        # Execute
        for n in args.N:
            result = solve(n)
            print(f"\nFinal Prime Factors: {result['answer']}")


if __name__ == "__main__":
    main()
