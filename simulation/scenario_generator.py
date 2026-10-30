"""
simulation/scenario_generator.py

Generates the underlying randomised election scenario ONCE per trial,
then derives BOTH a baseline and a protected security configuration
from that same scenario. This guarantees paired trials (thesis
section 10): baseline and protected always share identical N, m, B,
R, P, S, A -- only detection/acceptance probabilities differ between
the two security configurations.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from config import PARAM_RANGES


@dataclass
class TrialScenario:
    trial_id: int
    N: int
    m: int
    # bribery
    B: float
    R: float
    P: float
    q_baseline: float
    q_protected: float
    # sybil
    S: int
    qs_baseline: float
    qs_protected: float
    pd_baseline: float
    pd_protected: float
    # ballot stuffing
    A: int
    qb_baseline: float
    qb_protected: float
    pb_baseline: float
    pb_protected: float


def _uniform(rng: np.random.Generator, key: str) -> float:
    lo, hi = PARAM_RANGES[key]
    return float(rng.uniform(lo, hi))


def generate_trial_scenario(trial_id: int, rng: np.random.Generator) -> TrialScenario:
    N = int(round(_uniform(rng, "N")))
    m_fraction = _uniform(rng, "m_fraction")
    m = max(1, int(round(m_fraction * N)))

    B = _uniform(rng, "B")
    R = _uniform(rng, "R")
    P = _uniform(rng, "P")
    q_baseline = _uniform(rng, "q_baseline")
    q_boost = _uniform(rng, "q_protected_boost")
    q_protected = min(1.0, q_baseline + (1 - q_baseline) * q_boost)

    S = int(round(_uniform(rng, "S")))
    qs_baseline = _uniform(rng, "qs_baseline")
    qs_reduction = _uniform(rng, "qs_protected_reduction")
    qs_protected = max(0.0, qs_baseline * (1 - qs_reduction))
    pd_baseline = _uniform(rng, "pd_baseline")
    pd_boost = _uniform(rng, "pd_protected_boost")
    pd_protected = min(1.0, pd_baseline + (1 - pd_baseline) * pd_boost)

    A = int(round(_uniform(rng, "A")))
    qb_baseline = _uniform(rng, "qb_baseline")
    qb_reduction = _uniform(rng, "qb_protected_reduction")
    qb_protected = max(0.0, qb_baseline * (1 - qb_reduction))
    pb_baseline = _uniform(rng, "pb_baseline")
    pb_boost = _uniform(rng, "pb_protected_boost")
    pb_protected = min(1.0, pb_baseline + (1 - pb_baseline) * pb_boost)

    return TrialScenario(
        trial_id=trial_id, N=N, m=m,
        B=B, R=R, P=P, q_baseline=q_baseline, q_protected=q_protected,
        S=S, qs_baseline=qs_baseline, qs_protected=qs_protected,
        pd_baseline=pd_baseline, pd_protected=pd_protected,
        A=A, qb_baseline=qb_baseline, qb_protected=qb_protected,
        pb_baseline=pb_baseline, pb_protected=pb_protected,
    )
