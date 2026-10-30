"""
simulation/experiment_runner.py

Runs N paired randomised trials (baseline vs protected) across the
three attack types, collecting results into pandas DataFrames ready
for CSV/JSON export and downstream analysis/visualisation.
"""

from __future__ import annotations
from typing import Dict, List
import numpy as np
import pandas as pd

from config import MC_TRIALS_PER_SCENARIO
from simulation.scenario_generator import generate_trial_scenario, TrialScenario
from attacks.bribery import run_bribery_scenario
from attacks.sybil import run_sybil_scenario
from attacks.ballot_stuffing import run_ballot_stuffing_scenario


def run_all_trials(n_trials: int, seed: int, mc_trials: int = MC_TRIALS_PER_SCENARIO,
                    attacks: List[str] | None = None) -> Dict[str, pd.DataFrame]:
    """Run n_trials paired scenarios. Returns a dict of DataFrames keyed
    by 'bribery', 'sybil', 'ballot_stuffing', 'combined'.
    attacks: subset of {'bribery','sybil','ballot_stuffing'} to run;
    defaults to all three.
    """
    if attacks is None:
        attacks = ["bribery", "sybil", "ballot_stuffing"]

    master_rng = np.random.default_rng(seed)
    # Derive independent-but-reproducible sub-seeds per trial for the
    # Monte Carlo draws, so re-running with the same top-level seed is
    # bit-for-bit reproducible regardless of call order.
    trial_seeds = master_rng.integers(0, 2**32 - 1, size=n_trials)

    bribery_rows = []
    sybil_rows = []
    ballot_rows = []
    combined_rows = []

    for i in range(n_trials):
        trial_id = i + 1
        scenario_rng = np.random.default_rng(int(trial_seeds[i]))
        scen: TrialScenario = generate_trial_scenario(trial_id, scenario_rng)
        mc_rng = np.random.default_rng(int(trial_seeds[i]) ^ 0xA5A5A5A5)

        if "bribery" in attacks:
            base = run_bribery_scenario(scen.N, scen.m, scen.B, scen.R, scen.P,
                                         scen.q_baseline, mc_trials, mc_rng)
            prot = run_bribery_scenario(scen.N, scen.m, scen.B, scen.R, scen.P,
                                         scen.q_protected, mc_trials, mc_rng)
            for label, res in (("baseline", base), ("protected", prot)):
                row = {"trial_id": trial_id, "seed": seed, "system_type": label,
                       "attack_type": "bribery"}
                row.update(res.as_dict())
                bribery_rows.append(row)
            combined_rows.append({
                "trial_id": trial_id, "attack_type": "bribery",
                "baseline_success_prob": base.exact_probability,
                "protected_success_prob": prot.exact_probability,
                "baseline_expected": base.expected_successful_votes,
                "protected_expected": prot.expected_successful_votes,
            })

        if "sybil" in attacks:
            base = run_sybil_scenario(scen.N, scen.m, scen.S, scen.qs_baseline,
                                       scen.pd_baseline, mc_trials, mc_rng)
            prot = run_sybil_scenario(scen.N, scen.m, scen.S, scen.qs_protected,
                                       scen.pd_protected, mc_trials, mc_rng)
            for label, res in (("baseline", base), ("protected", prot)):
                row = {"trial_id": trial_id, "seed": seed, "system_type": label,
                       "attack_type": "sybil"}
                row.update(res.as_dict())
                sybil_rows.append(row)
            combined_rows.append({
                "trial_id": trial_id, "attack_type": "sybil",
                "baseline_success_prob": base.surviving_ge_m_exact_probability,
                "protected_success_prob": prot.surviving_ge_m_exact_probability,
                "baseline_expected": base.expected_surviving,
                "protected_expected": prot.expected_surviving,
            })

        if "ballot_stuffing" in attacks:
            base = run_ballot_stuffing_scenario(scen.N, scen.m, scen.A, scen.qb_baseline,
                                                 scen.pb_baseline, mc_trials, mc_rng)
            prot = run_ballot_stuffing_scenario(scen.N, scen.m, scen.A, scen.qb_protected,
                                                 scen.pb_protected, mc_trials, mc_rng)
            for label, res in (("baseline", base), ("protected", prot)):
                row = {"trial_id": trial_id, "seed": seed, "system_type": label,
                       "attack_type": "ballot_stuffing"}
                row.update(res.as_dict())
                ballot_rows.append(row)
            combined_rows.append({
                "trial_id": trial_id, "attack_type": "ballot_stuffing",
                "baseline_success_prob": base.surviving_ge_m_exact_probability,
                "protected_success_prob": prot.surviving_ge_m_exact_probability,
                "baseline_expected": base.expected_surviving,
                "protected_expected": prot.expected_surviving,
            })

    out = {}
    if bribery_rows:
        out["bribery"] = pd.DataFrame(bribery_rows)
    if sybil_rows:
        out["sybil"] = pd.DataFrame(sybil_rows)
    if ballot_rows:
        out["ballot_stuffing"] = pd.DataFrame(ballot_rows)
    out["combined"] = pd.DataFrame(combined_rows)
    return out
