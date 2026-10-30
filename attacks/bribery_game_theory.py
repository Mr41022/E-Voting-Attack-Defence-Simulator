"""
attacks/bribery_game_theory.py

Game-theoretic layer on top of attacks/bribery.py: instead of
evaluating a single fixed number of bribery attempts T, this module
finds the UTILITY-MAXIMIZING T for a rational attacker, given:

    - a payoff V if the election outcome is successfully flipped
      (m or more bribed votes survive detection),
    - a per-voter bribe cost R (same R as mathematics/utility.py --
      the reward paid to a bribed voter is simultaneously the
      attacker's cost per accepted bribe),
    - a penalty D_attack incurred (in expectation) if the attack is
      detected at all -- i.e. if at least one bribed vote is caught.

Expected utility for attempting T bribes:

    U(T) = P(X >= m) * V  -  T * R * P(voter accepts)  -  P(at least one
           of the T accepted bribes is detected) * D_attack

Under this project's rational-voter gate (mathematics/utility.py),
P(voter accepts) is 0 or 1 for a GIVEN (q,R,P) -- voters facing
identical incentives reach identical decisions (see
attacks/bribery.py's docstring) -- so the term simplifies to T*R when
the bribe is incentive-compatible, and to 0 (no attempts materialise)
when it is not. This module therefore only searches T when bribery is
incentive-compatible in the first place; if it is not, the optimal
strategy is trivially T=0 (do not attempt).

NOTE ON NOTATION: this module keeps the SAME q=P(detection) convention
used throughout the rest of the project (mathematics/*, attacks/*),
NOT q=P(acceptance) as used in some alternative textbook presentations
of this model. Under that alternative convention, substitute
q_theirs = 1 - q_here. See MATHEMATICAL_MODEL.md's "Notation
reconciliation" section for the full explanation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from mathematics.binomial import p_at_least
from mathematics.probability import prob_at_least_one_detected
from mathematics.utility import rational_voter_decision
from models.attacker import AttackerBudget


@dataclass
class UtilityCurvePoint:
    T: int
    p_flip: float
    expected_cost: float
    expected_detection_penalty: float
    utility: float


@dataclass
class GameTheoreticResult:
    T_max_feasible: int  # budget/electorate ceiling, min(N, floor(B/R))
    voter_accepts: bool
    T_star: int           # utility-maximizing number of bribery attempts
    utility_star: float
    p_flip_at_T_star: float
    curve: List[UtilityCurvePoint]


def attacker_utility(T: int, m: int, q: float, R: float, V: float,
                      D_attack: float, voter_accepts: bool) -> UtilityCurvePoint:
    """U(T) = P(X>=m)*V - T*R*1[accepts] - P(at least one detected)*D_attack

    X ~ Binomial(T, 1-q) as throughout attacks/bribery.py (p_success=1-q
    is the probability a given bribed vote survives detection).
    """
    if not voter_accepts or T <= 0:
        return UtilityCurvePoint(T=T, p_flip=0.0, expected_cost=0.0,
                                  expected_detection_penalty=0.0, utility=0.0)

    p_success = 1 - min(1.0, max(0.0, q))
    p_flip = p_at_least(T, p_success, m)
    expected_cost = T * R
    p_detected_attack = prob_at_least_one_detected(T, q)
    expected_penalty = p_detected_attack * D_attack
    utility = p_flip * V - expected_cost - expected_penalty
    return UtilityCurvePoint(T=T, p_flip=p_flip, expected_cost=expected_cost,
                              expected_detection_penalty=expected_penalty, utility=utility)


def optimal_attempts(N: int, m: int, B: float, R: float, P: float, q: float,
                      V: float, D_attack: float, T_grid_points: int = 60) -> GameTheoreticResult:
    """Searches T in [0, T_max_feasible] for the utility-maximizing
    number of bribery attempts, where T_max_feasible = min(N,
    floor(B/R)) (the attacker cannot exceed budget or electorate size
    -- M3). Voter rationality (Uv=(1-q)R-qP) is evaluated once (it does
    not depend on T), matching attacks/bribery.py's model: if bribery
    is not incentive-compatible at all, T*=0 regardless of budget.
    """
    attacker = AttackerBudget(N=N, B=B, R=R)
    T_max = attacker.max_targets()
    decision = rational_voter_decision(q, R, P)

    if T_max <= 0 or not decision.accepts:
        zero_point = attacker_utility(0, m, q, R, V, D_attack, decision.accepts)
        return GameTheoreticResult(T_max_feasible=T_max, voter_accepts=decision.accepts,
                                    T_star=0, utility_star=zero_point.utility,
                                    p_flip_at_T_star=0.0, curve=[zero_point])

    # Evaluate a grid of T values up to T_max (coarser grid for large T_max,
    # always including T_max itself and T=0) -- a full O(T_max) sweep is
    # unnecessary for a smooth, unimodal-ish utility curve and keeps this
    # fast even for T_max in the thousands.
    if T_max <= T_grid_points:
        T_values = list(range(0, T_max + 1))
    else:
        T_values = sorted(set(
            [0] + list(np.linspace(1, T_max, T_grid_points, dtype=int)) + [T_max]
        ))

    curve = [attacker_utility(T, m, q, R, V, D_attack, decision.accepts) for T in T_values]
    best = max(curve, key=lambda pt: pt.utility)

    return GameTheoreticResult(T_max_feasible=T_max, voter_accepts=decision.accepts,
                                T_star=best.T, utility_star=best.utility,
                                p_flip_at_T_star=best.p_flip, curve=curve)
