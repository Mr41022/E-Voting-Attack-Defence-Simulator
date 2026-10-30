"""
attacks/bribery.py

Implements the full rational-voter bribery attack pipeline described
in thesis sections 2.2-2.5 and 5.

For a given scenario (N, m, B, R, P, q):
    1. T = min(N, floor(B/R))                     (models/attacker.py)
    2. Each of the T targeted voters makes an independent rational
       decision Uv = (1-q)R - qP  (mathematics/utility.py). Because all
       T targeted voters face IDENTICAL (q,R,P), they all reach the
       SAME accept/reject decision under this model (the utility
       function has no per-voter randomness). This is stated explicitly
       as a modelling assumption in ASSUMPTIONS.md: voter heterogeneity
       is out of scope for the base model; the "acceptance" step here
       determines whether bribery is *incentive-compatible at all*
       for this scenario. If accepted, each of the T bribed voters
       independently succeeds in casting a fraudulent vote with
       probability p_success = 1-q (i.e. escapes detection at the
       point of the fraudulent act), captured by X ~ Binomial(T, 1-q).
    3. If voters reject (Uv <= 0), the attack cannot proceed: bribes
       are never accepted, so zero fraudulent votes occur regardless
       of T.
    4. Exact P(X>=m), Monte Carlo P(X>=m), and Chernoff bound are all
       computed for downstream comparison.

This file DOES NOT assume all targeted voters accept bribes -- the
rational decision gate in step 2/3 is mandatory and explicit.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import numpy as np

from models.attacker import AttackerBudget
from mathematics.utility import rational_voter_decision
from mathematics.binomial import expected_value, p_at_least, sample
from mathematics.chernoff import chernoff_bound_for_threshold, chernoff_certificate


@dataclass
class BriberyResult:
    N: int
    m: int
    B: float
    R: float
    P: float
    q: float
    Uv: float
    voter_decision: str          # "accept" | "reject"
    T: int
    p_success: float
    expected_successful_votes: float
    exact_probability: float
    monte_carlo_probability: float
    monte_carlo_std_error: float
    chernoff_bound: float | None
    chernoff_tail: str
    chernoff_reason: str
    # Two-sided certificate: an upper bound on success when m > mu, and a
    # lower bound on success when m <= mu (the (1-delta) lower-tail form
    # applied to the failure event). See mathematics/chernoff.py.
    chernoff_direction: str
    chernoff_success_lower: float | None
    chernoff_success_upper: float | None
    attack_success_exact: bool          # P(X>=m) > 0.5 heuristic flag (see report)
    bribes_offered: int
    bribes_accepted: int
    bribes_rejected: int
    attacker_cost: float
    remaining_budget: float

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_bribery_scenario(N: int, m: int, B: float, R: float, P: float, q: float,
                          mc_trials: int, rng: np.random.Generator) -> BriberyResult:
    attacker = AttackerBudget(N=N, B=B, R=R)
    T = attacker.max_targets()

    decision = rational_voter_decision(q, R, P)
    p_success = 1 - min(1.0, max(0.0, q))

    if decision.accepts and T > 0:
        bribes_offered = T
        bribes_accepted = T
        bribes_rejected = 0
        effective_T = T
    else:
        # Voters rationally reject: no fraudulent votes materialise
        # even though the attacker theoretically could have approached
        # T voters.
        bribes_offered = T
        bribes_accepted = 0
        bribes_rejected = T
        effective_T = 0

    expected_votes = expected_value(effective_T, p_success)
    exact_prob = p_at_least(effective_T, p_success, m)

    # Monte Carlo empirical probability
    if effective_T > 0 and mc_trials > 0:
        samples = sample(effective_T, p_success, mc_trials, rng)
        mc_prob = float(np.mean(samples >= m))
        mc_std_error = float(np.sqrt(mc_prob * (1 - mc_prob) / mc_trials)) if mc_trials > 0 else 0.0
    else:
        mc_prob = 0.0 if m > 0 else 1.0
        mc_std_error = 0.0

    cher = chernoff_bound_for_threshold(effective_T, p_success, m)
    cert = chernoff_certificate(effective_T, p_success, m)

    attacker_cost = bribes_accepted * R
    remaining_budget = B - attacker_cost

    return BriberyResult(
        N=N, m=m, B=B, R=R, P=P, q=q,
        Uv=decision.Uv,
        voter_decision="accept" if decision.accepts else "reject",
        T=T,
        p_success=p_success,
        expected_successful_votes=expected_votes,
        exact_probability=exact_prob,
        monte_carlo_probability=mc_prob,
        monte_carlo_std_error=mc_std_error,
        chernoff_bound=cher.bound,
        chernoff_tail=cher.tail,
        chernoff_reason=cher.reason,
        chernoff_direction=cert.direction,
        chernoff_success_lower=cert.p_success_lower,
        chernoff_success_upper=cert.p_success_upper,
        attack_success_exact=exact_prob >= 0.5,
        bribes_offered=bribes_offered,
        bribes_accepted=bribes_accepted,
        bribes_rejected=bribes_rejected,
        attacker_cost=attacker_cost,
        remaining_budget=remaining_budget,
    )
