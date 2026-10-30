"""
mathematics/binomial.py

Exact analytical binomial probability calculations.

Implements:
    M4 / M9 / M12:  X ~ Binomial(n, p)
    M5 / M10 / M13:  P(X >= m)  (survival function, exact)
    E[X] = n * p

All functions are numerically stable (they rely on scipy.stats.binom,
which uses log-space computation internally to avoid overflow for
large n).

Edge cases handled explicitly:
    n <= 0            -> degenerate distribution, X is always 0
    p == 0             -> X is always 0
    p == 1             -> X is always n
    m <= 0              -> P(X >= m) = 1 (any outcome satisfies threshold)
    m > n               -> P(X >= m) = 0 (impossible, more successes than trials)
"""

from __future__ import annotations
import numpy as np
from scipy.stats import binom


def validate_binomial_params(n: int, p: float) -> tuple[int, float]:
    """Clamp/validate n and p into numerically sane ranges.

    n is coerced to a non-negative integer.
    p is clamped into [0, 1] (floating point drift can push p slightly
    outside this range, e.g. 1 - 1e-17 - 1 giving a negative number).
    """
    n = int(max(0, round(n)))
    p = float(min(1.0, max(0.0, p)))
    return n, p


def expected_value(n: int, p: float) -> float:
    """M6: mu = n * p"""
    n, p = validate_binomial_params(n, p)
    return n * p


def variance(n: int, p: float) -> float:
    n, p = validate_binomial_params(n, p)
    return n * p * (1 - p)


def p_at_least(n: int, p: float, m: int) -> float:
    """Exact P(X >= m) for X ~ Binomial(n, p).

    Implements M5 / M10 / M13 depending on calling context (bribery,
    Sybil, ballot stuffing respectively share this identical binomial
    machinery -- only the semantic meaning of n, p, m differs).
    """
    n, p = validate_binomial_params(n, p)

    # Edge case: non-positive threshold -> always satisfied
    if m <= 0:
        return 1.0
    # Edge case: threshold exceeds number of trials -> impossible
    if m > n:
        return 0.0
    if n == 0:
        return 0.0 if m > 0 else 1.0

    # P(X >= m) = 1 - P(X <= m-1) = survival function evaluated at m-1
    prob = binom.sf(m - 1, n, p)
    # Guard against tiny negative floating point noise
    return float(min(1.0, max(0.0, prob)))


def pmf(n: int, p: float, k: int) -> float:
    """P(X = k)"""
    n, p = validate_binomial_params(n, p)
    if k < 0 or k > n:
        return 0.0
    return float(binom.pmf(k, n, p))


def sample(n: int, p: float, size: int, rng: np.random.Generator) -> np.ndarray:
    """Draw `size` i.i.d. samples of X ~ Binomial(n, p) using the supplied
    reproducible NumPy Generator. Used by the Monte Carlo engine.
    """
    n, p = validate_binomial_params(n, p)
    if n == 0:
        return np.zeros(size, dtype=int)
    return rng.binomial(n, p, size=size)
