"""
simulation/monte_carlo.py

Monte Carlo convergence utility: repeatedly estimate P(X>=m) for
X~Binomial(n,p) using increasing sample sizes, to demonstrate
empirical convergence toward the exact analytical probability
(thesis Experiment 12 / Figure 13).
"""

from __future__ import annotations
import numpy as np
from mathematics.binomial import sample, p_at_least


def convergence_curve(n: int, p: float, m: int, sample_sizes: list[int],
                       rng: np.random.Generator) -> list[dict]:
    exact = p_at_least(n, p, m)
    out = []
    for size in sample_sizes:
        if n > 0 and size > 0:
            draws = sample(n, p, size, rng)
            mc_est = float(np.mean(draws >= m))
        else:
            mc_est = 0.0 if m > 0 else 1.0
        out.append({
            "sample_size": size,
            "monte_carlo_estimate": mc_est,
            "exact_probability": exact,
            "absolute_error": abs(mc_est - exact),
        })
    return out
