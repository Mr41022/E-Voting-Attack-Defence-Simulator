"""
mathematics/probability.py

General-purpose probability helpers shared across the three attack
models (bribery, Sybil, ballot stuffing).

Implements:
    M11 / M14 pattern:
        P(at least one of n independent items is detected)
            = 1 - (1 - p_detect)^n
        P(all n items escape detection) = (1 - p_detect)^n

These are numerically stable for large n via log-space computation
(np.expm1 / np.log1p) to avoid catastrophic cancellation when
p_detect is very small.
"""

from __future__ import annotations
import numpy as np


def prob_all_escape_detection(n: int, p_detect: float) -> float:
    """(1 - p_detect)^n -- probability every one of n independent
    fraudulent items escapes detection.
    """
    n = max(0, int(n))
    p_detect = float(min(1.0, max(0.0, p_detect)))
    if n == 0:
        return 1.0
    if p_detect <= 0:
        return 1.0
    if p_detect >= 1:
        return 0.0
    # log-space for numerical stability with large n
    log_survival = n * np.log1p(-p_detect)
    return float(np.exp(log_survival))


def prob_at_least_one_detected(n: int, p_detect: float) -> float:
    """1 - (1 - p_detect)^n, computed via expm1/log1p for numerical
    stability when p_detect is small and n is large.
    """
    n = max(0, int(n))
    p_detect = float(min(1.0, max(0.0, p_detect)))
    if n == 0:
        return 0.0
    if p_detect <= 0:
        return 0.0
    if p_detect >= 1:
        return 1.0
    log_survival = n * np.log1p(-p_detect)
    return float(-np.expm1(log_survival))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division guarding against zero/near-zero denominators."""
    if denominator == 0 or np.isclose(denominator, 0.0):
        return default
    return numerator / denominator


def relative_reduction(baseline: float, protected: float) -> float:
    """(baseline - protected) / baseline, with safe zero-denominator handling."""
    return safe_divide(baseline - protected, baseline, default=0.0)


def absolute_reduction(baseline: float, protected: float) -> float:
    return baseline - protected


def clamp01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))
