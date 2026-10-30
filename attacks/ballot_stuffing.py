"""
attacks/ballot_stuffing.py

M12: Z ~ Binomial(A, qb)     Z = accepted fraudulent ballots
M13: P(Z >= m)
M14: 1 - (1-pb)^A            P(at least one fraudulent ballot detected)
     (1-pb)^A                P(all A ballots escape detection)

Distinguishes explicitly:
    A (attempted) -> accepted (Z, Binomial draw) -> detected/rejected -> surviving
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import numpy as np

from mathematics.binomial import expected_value, p_at_least, sample
from mathematics.chernoff import chernoff_bound_for_threshold, chernoff_certificate
from mathematics.probability import prob_at_least_one_detected, prob_all_escape_detection


@dataclass
class BallotStuffingResult:
    N: int
    m: int
    A: int
    qb: float
    pb: float
    expected_accepted: float
    exact_probability_accepted_ge_m: float
    monte_carlo_probability: float
    monte_carlo_std_error: float
    chernoff_bound: float | None
    chernoff_tail: str
    prob_at_least_one_detected: float
    prob_all_escape_detection: float
    expected_surviving: float
    surviving_ge_m_exact_probability: float
    surviving_monte_carlo_probability: float
    surviving_chernoff_bound: float | None
    # Two-sided certificate on the SURVIVING count, which is the quantity
    # compared against the threshold. Upper bound on success when m > mu,
    # lower bound when m <= mu. See mathematics/chernoff.py.
    chernoff_direction: str
    chernoff_success_lower: float | None
    chernoff_success_upper: float | None
    attack_success_exact: bool

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_ballot_stuffing_scenario(N: int, m: int, A: int, qb: float, pb: float,
                                  mc_trials: int, rng: np.random.Generator) -> BallotStuffingResult:
    expected_accepted = expected_value(A, qb)
    exact_prob_accepted = p_at_least(A, qb, m)

    if A > 0 and mc_trials > 0:
        z_samples = sample(A, qb, mc_trials, rng)
        mc_prob = float(np.mean(z_samples >= m))
        mc_std_error = float(np.sqrt(mc_prob * (1 - mc_prob) / mc_trials))
    else:
        mc_prob = 0.0 if m > 0 else 1.0
        mc_std_error = 0.0

    cher = chernoff_bound_for_threshold(A, qb, m)

    p_detect_at_least_one = prob_at_least_one_detected(A, pb)
    p_all_escape = prob_all_escape_detection(A, pb)

    p_survive_single = qb * (1 - min(1.0, max(0.0, pb)))
    expected_surviving = expected_value(A, p_survive_single)
    surviving_ge_m_prob = p_at_least(A, p_survive_single, m)

    if A > 0 and mc_trials > 0:
        surv_samples = sample(A, p_survive_single, mc_trials, rng)
        mc_prob_surviving = float(np.mean(surv_samples >= m))
    else:
        mc_prob_surviving = 0.0 if m > 0 else 1.0
    cher_surviving = chernoff_bound_for_threshold(A, p_survive_single, m)
    cert = chernoff_certificate(A, p_survive_single, m)

    return BallotStuffingResult(
        N=N, m=m, A=A, qb=qb, pb=pb,
        expected_accepted=expected_accepted,
        exact_probability_accepted_ge_m=exact_prob_accepted,
        monte_carlo_probability=mc_prob,
        monte_carlo_std_error=mc_std_error,
        chernoff_bound=cher.bound,
        chernoff_tail=cher.tail,
        prob_at_least_one_detected=p_detect_at_least_one,
        prob_all_escape_detection=p_all_escape,
        expected_surviving=expected_surviving,
        surviving_ge_m_exact_probability=surviving_ge_m_prob,
        surviving_monte_carlo_probability=mc_prob_surviving,
        surviving_chernoff_bound=cher_surviving.bound,
        chernoff_direction=cert.direction,
        chernoff_success_lower=cert.p_success_lower,
        chernoff_success_upper=cert.p_success_upper,
        attack_success_exact=surviving_ge_m_prob >= 0.5,
    )
