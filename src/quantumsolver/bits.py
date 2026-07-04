"""Bit-width utility functions shared across quantum solvers."""

import math


def power_of_two_info(n):
    """Return (True, exponent) if n is a power of 2, else (False, None)."""
    if n <= 0:
        return False, None
    if (n & (n - 1)) == 0:
        return True, int(math.log2(n))
    return False, None
