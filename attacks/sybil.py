"""
attacks/sybil.py

M9:  Y ~ Binomial(S, qs)                    Y = successful fake identities
M10: P(Y >= m)
M11: 1 - (1-pd)^S                            P(at least one identity detected)
     (1-pd)^S                                P(all S identities escape detection)

Distinguishes explicitly:
    S               = attempted fake identities
    accepted (Y)    = identities that passed registration (Binomial draw)
    detected        = identities flagged by detection mechanism
    surviving       = accepted AND not detected
    attack success  = surviving >= m
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import numpy as np

from mathematics.binomial import expected_value, p_at_least, sample
from mathematics.chernoff import chernoff_bound_for_threshold, chernoff_certificate
from mathematics.probability import prob_at_least_one_detected, prob_all_escape_detection


@dataclass
class SybilResult:
    N: int
    m: int
    S: int
    qs: float
    pd: float
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


def run_sybil_scenario(N: int, m: int, S: int, qs: float, pd: float,
                        mc_trials: int, rng: np.random.Generator) -> SybilResult:
    # Accepted fake identities: Y ~ Binomial(S, qs)
    expected_accepted = expected_value(S, qs)
    exact_prob_accepted = p_at_least(S, qs, m)

    if S > 0 and mc_trials > 0:
        y_samples = sample(S, qs, mc_trials, rng)
        mc_prob = float(np.mean(y_samples >= m))
        mc_std_error = float(np.sqrt(mc_prob * (1 - mc_prob) / mc_trials))
    else:
        y_samples = np.zeros(max(mc_trials, 1), dtype=int)
        mc_prob = 0.0 if m > 0 else 1.0
        mc_std_error = 0.0

    cher = chernoff_bound_for_threshold(S, qs, m)

    p_detect_at_least_one = prob_at_least_one_detected(S, pd)
    p_all_escape = prob_all_escape_detection(S, pd)

    # Surviving identities: those accepted AND not detected.
    # Under independence, an accepted identity survives with prob (1-pd),
    # so surviving count W ~ Binomial(S, qs*(1-pd)) approximately, since
    # acceptance and detection-escape are modelled as independent
    # Bernoulli gates per attempted identity.
    p_survive_single = qs * (1 - min(1.0, max(0.0, pd)))
    expected_surviving = expected_value(S, p_survive_single)
    surviving_ge_m_prob = p_at_least(S, p_survive_single, m)

    # Monte Carlo + Chernoff for the SURVIVING distribution (post-detection),
    # which is the quantity comparable across attack types (bribery's
    # exact_probability already bakes detection into p_success=1-q).
    if S > 0 and mc_trials > 0:
        surv_samples = sample(S, p_survive_single, mc_trials, rng)
        mc_prob_surviving = float(np.mean(surv_samples >= m))
    else:
        mc_prob_surviving = 0.0 if m > 0 else 1.0
    cher_surviving = chernoff_bound_for_threshold(S, p_survive_single, m)
    cert = chernoff_certificate(S, p_survive_single, m)

    return SybilResult(
        N=N, m=m, S=S, qs=qs, pd=pd,
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
