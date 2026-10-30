"""
simulation/named_scenarios.py

Five named, fixed (non-randomised) benchmark scenarios, matching the
scope described in the project's scenario list:

    1. Small university election      (100 voters, close race)
    2. Medium organisation election   (10,000 voters)
    3. Large national-scale election  (100,000 voters) -- Monte Carlo
       vs Chernoff bound comparison at scale
    4. High-budget attack             -- maximum attacker capability
    5. Low-budget attack              -- expected to fail (~0% flip probability)

Unlike simulation/scenario_generator.py (which randomises parameters
across 2,500 paired trials for statistical power), these are FIXED,
hand-chosen, individually-interpretable scenarios meant to be quoted
directly in the thesis text and shown as worked examples alongside the
aggregate statistics.

Each scenario is evaluated for bribery (exact probability, Monte
Carlo, Chernoff bound, and the game-theoretic optimal attacker
strategy), under both baseline and protected detection probability.

CALIBRATION NOTE ON m: for scenarios S1-S4, the manipulation threshold
m is deliberately chosen close to (roughly 0.3-0.5 standard deviations
above) the baseline mean mu=T(1-q), rather than at an extreme. This is
what makes the exact-vs-Monte-Carlo-vs-Chernoff comparison genuinely
informative (Scenario 3 in particular is built specifically to show
this three-way comparison at national scale): choosing m far below mu
would make baseline success probability trivially ~1, and choosing it
far above mu would make it trivially ~0, in both cases giving no
Chernoff bound (see mathematics/chernoff.py's tail dispatcher, which
only returns a bound for m>mu) and nothing interesting to compare.
Scenario 5 (low-budget) is the deliberate exception: its m is chosen
to be far beyond what the attacker's budget can reach at all,
specifically to validate the "expected to fail" claim.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import numpy as np
import pandas as pd

from attacks.bribery import run_bribery_scenario
from attacks.bribery_game_theory import optimal_attempts


@dataclass
class NamedScenario:
    scenario_id: str
    name: str
    N: int
    m: int
    B: float
    R: float
    P: float
    q_baseline: float
    q_protected: float
    V: float           # attacker's payoff if the flip succeeds (game theory)
    D_attack: float     # expected penalty if the attack is detected (game theory)


SCENARIOS: List[NamedScenario] = [
    NamedScenario(
        scenario_id="S1", name="Small university election (100 voters)",
        N=100, m=35, B=3000, R=80, P=600,
        q_baseline=0.08, q_protected=0.55,
        V=60000, D_attack=1000,
    ),
    NamedScenario(
        scenario_id="S2", name="Medium organisation election (10,000 voters)",
        N=10_000, m=1943, B=250_000, R=120, P=900,
        q_baseline=0.07, q_protected=0.55,
        V=2_000_000, D_attack=150_000,
    ),
    NamedScenario(
        scenario_id="S3", name="Large national-scale election (100,000 voters)",
        N=100_000, m=19015, B=3_000_000, R=150, P=1200,
        q_baseline=0.05, q_protected=0.55,
        V=20_000_000, D_attack=1_500_000,
    ),
    NamedScenario(
        scenario_id="S4", name="High-budget attack (maximum attacker capability)",
        N=5000, m=4758, B=5_000_000, R=100, P=500,
        q_baseline=0.05, q_protected=0.55,
        V=5_000_000, D_attack=400_000,
    ),
    NamedScenario(
        scenario_id="S5", name="Low-budget attack (expected to fail)",
        N=5000, m=550, B=8000, R=100, P=500,
        q_baseline=0.05, q_protected=0.55,
        V=2_000_000, D_attack=100_000,
    ),
]


def evaluate_scenario(scenario: NamedScenario, mc_trials: int, rng: np.random.Generator) -> Dict:
    rows = {}
    for label, q in (("baseline", scenario.q_baseline), ("protected", scenario.q_protected)):
        res = run_bribery_scenario(scenario.N, scenario.m, scenario.B, scenario.R,
                                    scenario.P, q, mc_trials, rng)
        game = optimal_attempts(scenario.N, scenario.m, scenario.B, scenario.R,
                                 scenario.P, q, scenario.V, scenario.D_attack)
        rows[label] = {
            "T": res.T,
            "voter_decision": res.voter_decision,
            "exact_probability": res.exact_probability,
            "monte_carlo_probability": res.monte_carlo_probability,
            "monte_carlo_std_error": res.monte_carlo_std_error,
            "chernoff_bound": res.chernoff_bound,
            "chernoff_tail": res.chernoff_tail,
            "expected_successful_votes": res.expected_successful_votes,
            "T_star": game.T_star,
            "utility_star": game.utility_star,
            "p_flip_at_T_star": game.p_flip_at_T_star,
            "game_result": game,
            "bribery_result": res,
        }
    return rows


def run_named_scenarios(mc_trials: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    for scenario in SCENARIOS:
        evaluated = evaluate_scenario(scenario, mc_trials, rng)
        for system_type in ("baseline", "protected"):
            r = evaluated[system_type]
            records.append({
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "system_type": system_type,
                "N": scenario.N, "m": scenario.m, "B": scenario.B, "R": scenario.R, "P": scenario.P,
                "q": scenario.q_baseline if system_type == "baseline" else scenario.q_protected,
                "T": r["T"],
                "voter_decision": r["voter_decision"],
                "exact_probability": r["exact_probability"],
                "monte_carlo_probability": r["monte_carlo_probability"],
                "chernoff_bound": r["chernoff_bound"],
                "chernoff_tail": r["chernoff_tail"],
                "expected_successful_votes": r["expected_successful_votes"],
                "T_star": r["T_star"],
                "utility_star": r["utility_star"],
                "p_flip_at_T_star": r["p_flip_at_T_star"],
            })
    return pd.DataFrame(records)
