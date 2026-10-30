"""
simulation/threshold_analysis.py

Computes the critical thresholds (T1-T7, mathematics/thresholds.py) and
the coalition attack (G2, attacks/game_theory.py) for each of the five
named benchmark scenarios, under both the baseline and the protected
configuration.

This is the module that turns the abstract threshold solvers into the
concrete numbers annotated on the figures and quoted in the report. It
adds no new mathematics of its own: every value it returns comes from
mathematics/thresholds.py or attacks/game_theory.py, evaluated at the
fixed parameters declared in simulation/named_scenarios.py.

Coalition cost parameters. The named scenarios specify a bribe reward R
but not the cost of forging an identity or of injecting a ballot, since
the base model treats those vectors as effort-limited rather than
budget-limited. To place all three vectors on one budget line the
analysis assumes a forged identity costs 40% of a bribe and an injected
ballot 15% of a bribe -- registration fraud requires document forgery
and so is expensive but far cheaper than buying a voter, while ballot
injection is close to free once access exists. Both ratios are declared
here as named constants rather than buried as literals, are listed in
ASSUMPTIONS.md, and are swept in the sensitivity analysis so that no
conclusion in the report rests on their exact value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

from attacks.bribery_game_theory import optimal_attempts
from attacks.game_theory import (
    ballot_stuffing_spec,
    bribery_spec,
    coalition_attack,
    optimal_coalition,
    optimal_effort,
    sybil_spec,
)
from mathematics.binomial import expected_value
from mathematics.thresholds import (
    attacker_break_even_budget,
    attacker_reachable_margin,
    chernoff_certified_margin,
    defender_critical_detection,
    incentive_reward_threshold,
    min_attempts_for_confidence,
    voter_indifference_detection,
)
from simulation.named_scenarios import SCENARIOS, NamedScenario

# --- coalition cost model (see module docstring, ASSUMPTIONS.md) ---
IDENTITY_COST_RATIO = 0.40   # cost of forging one identity, as a multiple of R
BALLOT_COST_RATIO = 0.15     # cost of injecting one ballot, as a multiple of R

# --- structural capacity ceilings -------------------------------------
# Bribery is capped at the electorate size N by M3: there is no one else
# to bribe. The other two vectors are capped well below N, because they
# are limited by what the surrounding process will absorb rather than by
# the attacker's budget. Forged registrations must clear a registration
# window that is open to a bounded number of late applicants, and
# injected ballots must hide inside a plausible turnout figure -- an
# attacker who submits a fraudulent ballot for every elector produces a
# turnout anomaly that needs no probabilistic detection at all. Without
# such ceilings the cheapest vector always saturates and the coalition
# question becomes trivial; the sensitivity analysis sweeps both.
SYBIL_CEILING_FRACTION = 0.20    # forged registrations, as a fraction of N
BALLOT_CEILING_FRACTION = 0.30   # injected ballots, as a fraction of N

# Acceptance / detection probabilities for the non-bribery vectors in the
# named scenarios. Baseline mirrors a system with only cursory identity
# and ballot checks; protected mirrors the countermeasure configuration
# used throughout the paired experiments (config.py).
VECTOR_PROBS = {
    "baseline": {"qs": 0.80, "pd": 0.10, "qb": 0.70, "pb": 0.10},
    "protected": {"qs": 0.25, "pd": 0.55, "qb": 0.20, "pb": 0.55},
}

CERTIFICATION_EPSILON = 1e-3   # epsilon for the Chernoff-certified margin
REACHABLE_ALPHA = 0.5          # alpha for the attacker-reachable margin


@dataclass
class ScenarioThresholds:
    scenario_id: str
    name: str
    system_type: str
    N: int
    m: int
    B: float
    R: float
    P: float
    q: float
    # --- voter-side thresholds
    R_star: float | None                 # T1
    q_voter_indifference: float | None   # T2
    voter_accepts: bool
    # --- effort / budget thresholds
    T_feasible: int                      # M3
    T_star: int                          # game-theoretic optimum
    T_min_for_even_odds: float | None    # T3
    B_star: float | None                 # T4
    q_defender_critical: float | None    # T5
    # --- margin thresholds
    mu: float                            # M6
    m_reachable: float | None            # T7
    m_certified: float | None            # T6
    # --- outcome
    exact_p_flip: float
    utility_star: float


def _scenario_rows(scenario: NamedScenario, system_type: str) -> ScenarioThresholds:
    q = scenario.q_baseline if system_type == "baseline" else scenario.q_protected
    p_survive = 1.0 - q

    game = optimal_attempts(scenario.N, scenario.m, scenario.B, scenario.R,
                            scenario.P, q, scenario.V, scenario.D_attack)
    r_star = incentive_reward_threshold(q, scenario.P)
    q_v = voter_indifference_detection(scenario.R, scenario.P)
    t_min = min_attempts_for_confidence(p_survive, scenario.m, REACHABLE_ALPHA)
    b_star = attacker_break_even_budget(scenario.N, scenario.m, scenario.R,
                                        scenario.P, q, scenario.V, scenario.D_attack)
    q_d = defender_critical_detection(scenario.N, scenario.m, scenario.B, scenario.R,
                                      scenario.P, scenario.V, scenario.D_attack)

    T_feasible = game.T_max_feasible
    mu = expected_value(T_feasible, p_survive)
    m_reach = attacker_reachable_margin(T_feasible, p_survive, REACHABLE_ALPHA)
    m_cert = chernoff_certified_margin(T_feasible, p_survive, CERTIFICATION_EPSILON)

    from mathematics.binomial import p_at_least
    exact = p_at_least(T_feasible, p_survive, scenario.m) if game.voter_accepts else 0.0

    return ScenarioThresholds(
        scenario_id=scenario.scenario_id, name=scenario.name, system_type=system_type,
        N=scenario.N, m=scenario.m, B=scenario.B, R=scenario.R, P=scenario.P, q=q,
        R_star=r_star.value, q_voter_indifference=q_v.value,
        voter_accepts=game.voter_accepts,
        T_feasible=T_feasible, T_star=game.T_star,
        T_min_for_even_odds=t_min.value, B_star=b_star.value,
        q_defender_critical=q_d.value,
        mu=mu, m_reachable=m_reach.value, m_certified=m_cert.value,
        exact_p_flip=exact, utility_star=game.utility_star,
    )


def compute_scenario_thresholds() -> pd.DataFrame:
    """Threshold table for all five named scenarios, both configurations."""
    rows: List[Dict] = []
    for scenario in SCENARIOS:
        for system_type in ("baseline", "protected"):
            rows.append(asdict(_scenario_rows(scenario, system_type)))
    return pd.DataFrame(rows)


def build_specs(scenario: NamedScenario, system_type: str):
    """The three vectors of a named scenario, on a common budget line."""
    q = scenario.q_baseline if system_type == "baseline" else scenario.q_protected
    probs = VECTOR_PROBS[system_type]
    b_spec, gate = bribery_spec(scenario.R, scenario.P, q, scenario.N)
    s_spec = sybil_spec(scenario.R * IDENTITY_COST_RATIO, probs["qs"], probs["pd"],
                        int(scenario.N * SYBIL_CEILING_FRACTION))
    z_spec = ballot_stuffing_spec(scenario.R * BALLOT_COST_RATIO, probs["qb"],
                                  probs["pb"],
                                  int(scenario.N * BALLOT_CEILING_FRACTION))
    return [b_spec, s_spec, z_spec], {"bribery": gate}


def compute_single_vector_optima() -> pd.DataFrame:
    """Optimal effort per vector, per scenario, per configuration (G1)."""
    rows: List[Dict] = []
    for scenario in SCENARIOS:
        for system_type in ("baseline", "protected"):
            specs, gates = build_specs(scenario, system_type)
            for spec in specs:
                res = optimal_effort(spec, scenario.m, scenario.B, scenario.V,
                                     scenario.D_attack,
                                     gate_open=gates.get(spec.name, True))
                rows.append({
                    "scenario_id": scenario.scenario_id, "name": scenario.name,
                    "system_type": system_type, "vector": spec.name,
                    "unit_cost": spec.unit_cost, "p_survive": spec.p_survive,
                    "p_detect": spec.p_detect, "m": scenario.m,
                    "n_feasible": res.n_feasible, "n_star": res.n_star,
                    "p_success_at_star": res.p_success_at_star,
                    "cost_at_star": res.cost_at_star,
                    "utility_star": res.utility_star, "viable": res.viable,
                    "gate_open": res.gate_open,
                })
    return pd.DataFrame(rows)


def compute_coalition_results(grid_step: float = 0.05) -> pd.DataFrame:
    """Optimal multi-vector budget allocation per scenario (G2)."""
    rows: List[Dict] = []
    for scenario in SCENARIOS:
        for system_type in ("baseline", "protected"):
            specs, gates = build_specs(scenario, system_type)
            best, grid = optimal_coalition(specs, scenario.m, scenario.B, scenario.V,
                                           scenario.D_attack, gates, grid_step=grid_step)
            pure = {}
            for i, spec in enumerate(specs):
                shares = [0.0, 0.0, 0.0]
                shares[i] = 1.0
                pure[spec.name] = coalition_attack(specs, scenario.m, scenario.B, shares,
                                                   scenario.V, scenario.D_attack, gates)
            best_pure_name = max(pure, key=lambda k: pure[k].utility)
            rows.append({
                "scenario_id": scenario.scenario_id, "name": scenario.name,
                "system_type": system_type, "m": scenario.m, "B": scenario.B,
                "share_bribery": best.allocation["bribery"],
                "share_sybil": best.allocation["sybil"],
                "share_ballot_stuffing": best.allocation["ballot_stuffing"],
                "n_bribery": best.attempts["bribery"],
                "n_sybil": best.attempts["sybil"],
                "n_ballot_stuffing": best.attempts["ballot_stuffing"],
                "mu_total": best.mu_total,
                "coalition_exact_p": best.exact_p_success,
                "coalition_chernoff": best.chernoff_bound,
                "coalition_p_noticed": best.p_noticed,
                "coalition_utility": best.utility,
                "best_pure_vector": best_pure_name,
                "best_pure_exact_p": pure[best_pure_name].exact_p_success,
                "best_pure_utility": pure[best_pure_name].utility,
                "coalition_gain_p": best.exact_p_success - pure[best_pure_name].exact_p_success,
                "coalition_gain_utility": best.utility - pure[best_pure_name].utility,
            })
    return pd.DataFrame(rows)


def detection_sweep(scenario: NamedScenario, n_points: int = 400) -> pd.DataFrame:
    """Attacker utility and flip probability as detection probability q
    sweeps from 0 to 1 for one scenario -- the data behind the critical
    detection threshold figure.

    RESOLUTION. 400 points gives dq = 0.0025. At the previous 60 points
    (dq = 0.017) the plotted polyline crossed zero roughly 0.012 to the
    right of the q_d* line the solver computes, because the last sampled
    point before the crossing still sat far above zero. The threshold and
    the curve then disagreed visibly, and a reader measuring the figure
    got the wrong number. The solver is exact -- it bisects rather than
    sampling -- so this is purely about the curve being drawn finely
    enough to meet it.
    """
    from mathematics.thresholds import best_attacking_utility
    from mathematics.binomial import p_at_least

    qs = np.linspace(0.0, 0.999, n_points)
    rows = []
    for q in qs:
        game = optimal_attempts(scenario.N, scenario.m, scenario.B, scenario.R,
                                scenario.P, float(q), scenario.V, scenario.D_attack)
        signed = best_attacking_utility(scenario.N, scenario.m, scenario.B, scenario.R,
                                        scenario.P, float(q), scenario.V, scenario.D_attack)
        # best_attacking_utility returns a large negative SENTINEL when no
        # attempt is affordable or accepted -- a marker meaning "no attack
        # exists here", not an expected utility. It is flagged so the
        # figure can mask it rather than plotting and axis-scaling it as
        # though it were a value.
        sentinel = -(abs(scenario.V) + abs(scenario.D_attack) + abs(scenario.R))
        rows.append({
            "scenario_id": scenario.scenario_id, "q": float(q),
            "T_star": game.T_star, "utility_star": game.utility_star,
            "signed_attack_utility": signed,
            "attack_exists": bool(abs(signed - sentinel) > 1e-9),
            "p_flip": p_at_least(game.T_max_feasible, 1.0 - float(q), scenario.m),
            "voter_accepts": game.voter_accepts,
        })
    return pd.DataFrame(rows)


def budget_sweep(scenario: NamedScenario, n_points: int = 60,
                 max_multiple: float = 3.0) -> pd.DataFrame:
    """Attacker utility as the budget sweeps up to `max_multiple` times
    the scenario budget -- the data behind the break-even budget figure.
    """
    from mathematics.thresholds import best_attacking_utility

    budgets = np.linspace(0.0, scenario.B * max_multiple, n_points)
    rows = []
    for B in budgets:
        for system_type in ("baseline", "protected"):
            q = scenario.q_baseline if system_type == "baseline" else scenario.q_protected
            game = optimal_attempts(scenario.N, scenario.m, float(B), scenario.R,
                                    scenario.P, q, scenario.V, scenario.D_attack)
            rows.append({
                "scenario_id": scenario.scenario_id, "system_type": system_type,
                "B": float(B), "T_star": game.T_star,
                "utility_star": game.utility_star,
                "signed_attack_utility": best_attacking_utility(
                    scenario.N, scenario.m, float(B), scenario.R, scenario.P, q,
                    scenario.V, scenario.D_attack),
                "p_flip_at_T_star": game.p_flip_at_T_star,
            })
    return pd.DataFrame(rows)
