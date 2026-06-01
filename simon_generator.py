"""Generates and solves instances of Simon's problem.

The function f: {0,1}^n -> {0,1}^m satisfies f(x) = f(y) iff x = y or x = y XOR s,
where s is a secret string of length n. The output is a json schema:
{'nbits': nbits,
 'mbits': mbits,
 'f': [list of integers representing f(0), f(1), ..., f(2^n - 1)],
 's': the secret string s}
"""

import argparse
import json
import random
from bits import power_of_two_info



def brute_force_simon(farray):
    """Brute-force search to find the secret string s given f."""

    def f(x):
        return farray[x]

    ispower2, nbits = power_of_two_info(len(farray))
    if not ispower2:
        return f"length of function is not power of 2 {len(farray)}"

    fmap = {}
    for s in range(2**nbits):
        y = f(s)
        if y not in fmap:
            fmap[y] = []
        fmap[y].append(s)

    # one to one mapping, secret string is all zeros
    if len(fmap) == 2**nbits:
        return "".zfill(nbits)

    candidates = set()
    for ys in fmap.values():
        if len(ys) != 2:
            return "invalid f: more than two inputs map to the same output"
        candidates.add(ys[0] ^ ys[1])

    if len(candidates) != 1:
        return "invalid f: inconsistent secret strings found"
    s = candidates.pop()
    return f"{s:b}".zfill(nbits)


def generate(nbits: int, mbits: int, s: str):
    """Generates a Simon's problem instance with the given secret string s.
    The function f: {0,1}^n -> {0,1}^m satisfies f(x) = f(y) iff x = y or x = y XOR s.
    The output is a json schema:
    {'nbits': nbits,
     'mbits': mbits,
     'f': [list of integers representing f(0), f(1), ..., f(2^n - 1)]}
    """
    mfield = list(range(2**mbits))
    random.shuffle(mfield)

    sint = int(s, 2)
    f = [None] * (2**nbits)
    for i in range(2**nbits):
        f[i] = mfield.pop()
        f[i ^ sint] = f[i]
    data = {
        "nbits": nbits,
        "mbits": mbits,
        "f": f,
        "s": s,
    }
    return data


def main():
    """Main function to parse arguments and generate Simon's problem instance."""

    parser = argparse.ArgumentParser(
        description="Generate a function for Simon's problem."
    )
    parser.add_argument(
        "--nbits",
        type=int,
        default=3,
        help="Number of bits for function input x.",
    )
    parser.add_argument(
        "--s",
        type=str,
        default=None,
        help="The secret string s (length nbits).",
    )
    parser.add_argument(
        "--mbits",
        type=int,
        default=5,
        help="Output bit size (must be >= nbits).",
    )
    args = parser.parse_args()

    if args.s is None:
        args.s = f"{random.randint(0, 2**args.nbits - 1):b}".zfill(args.nbits)

    if args.mbits < args.nbits:
        raise ValueError("Output bit size must be >= input bit size.")
    if len(args.s) > args.nbits:
        raise ValueError("Secret string s must have length nbits.")

    args.s = args.s.zfill(args.nbits)
    data = generate(args.nbits, args.mbits, args.s)
    print(json.dumps(data, indent=2))
    print(brute_force_simon(data["f"]), data["s"])


if __name__ == "__main__":
    main()
