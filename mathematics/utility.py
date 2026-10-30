"""
mathematics/utility.py

M1: Uv = (1-q) R - q P            (rational voter utility from accepting a bribe)
M2: R > qP / (1-q)                (incentive-compatibility condition, where valid)

Decision rule:
    Uv > 0  -> rational voter accepts
    Uv <= 0 -> rational voter rejects

Edge cases:
    q == 1 -> voter is certainly detected; Uv = -P (accepting is never
              rational unless P <= 0, handled naturally by the formula).
              The M2 inequality R > qP/(1-q) is undefined (division by
              zero) at q==1; we do not evaluate it there and instead
              rely directly on the Uv formula, which remains well
              defined and is the ground truth decision rule.
    P == 0  -> no penalty; Uv = (1-q)R >= 0 for R>=0, so any positive
               reward whenever q<1 is accepted.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class VoterDecision:
    Uv: float
    accepts: bool
    incentive_threshold: Optional[float]  # qP/(1-q), None if undefined (q==1)


def voter_utility(q: float, R: float, P: float) -> float:
    """M1: Uv = (1-q)R - qP"""
    q = min(1.0, max(0.0, q))
    return (1 - q) * R - q * P


def incentive_threshold(q: float, P: float) -> Optional[float]:
    """M2 RHS: qP / (1-q). Returns None if q == 1 (division by zero)."""
    q = min(1.0, max(0.0, q))
    if math.isclose(q, 1.0):
        return None
    return (q * P) / (1 - q)


def rational_voter_decision(q: float, R: float, P: float) -> VoterDecision:
    """Full decision object: utility value, accept/reject, and the
    incentive-compatibility threshold for reference/reporting.
    """
    Uv = voter_utility(q, R, P)
    thresh = incentive_threshold(q, P)
    accepts = Uv > 0
    return VoterDecision(Uv=Uv, accepts=accepts, incentive_threshold=thresh)
