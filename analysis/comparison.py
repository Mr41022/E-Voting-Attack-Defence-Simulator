"""
analysis/comparison.py

Cross-attack and baseline-vs-protected comparison helpers built on top
of analysis/statistics.py.
"""

from __future__ import annotations
from typing import Dict
import pandas as pd

from analysis.statistics import countermeasure_effectiveness, paired_bootstrap_ci


def attack_success_column(attack_type: str) -> str:
    """The comparable "post-detection" attack-success probability
    column for each attack type. For bribery, detection is already
    baked into p_success=1-q, so exact_probability IS post-detection.
    For Sybil/ballot-stuffing, the analogous post-detection quantity
    is the "surviving" probability (accepted AND undetected >= m).
    """
    return {
        "bribery": "exact_probability",
        "sybil": "surviving_ge_m_exact_probability",
        "ballot_stuffing": "surviving_ge_m_exact_probability",
    }[attack_type]


def mc_column(attack_type: str) -> str:
    return {
        "bribery": "monte_carlo_probability",
        "sybil": "surviving_monte_carlo_probability",
        "ballot_stuffing": "surviving_monte_carlo_probability",
    }[attack_type]


def chernoff_column(attack_type: str) -> str:
    return {
        "bribery": "chernoff_bound",
        "sybil": "surviving_chernoff_bound",
        "ballot_stuffing": "surviving_chernoff_bound",
    }[attack_type]


def compare_baseline_protected(df: pd.DataFrame, attack_type: str) -> Dict[str, float]:
    col = attack_success_column(attack_type)
    baseline = df[df.system_type == "baseline"].sort_values("trial_id")[col].reset_index(drop=True)
    protected = df[df.system_type == "protected"].sort_values("trial_id")[col].reset_index(drop=True)
    eff = countermeasure_effectiveness(baseline, protected)
    boot = paired_bootstrap_ci(baseline, protected)
    eff.update({f"bootstrap_{k}": v for k, v in boot.items()})
    return eff


def cross_attack_comparison(results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for attack_type in ("bribery", "sybil", "ballot_stuffing"):
        if attack_type not in results:
            continue
        eff = compare_baseline_protected(results[attack_type], attack_type)
        eff["attack_type"] = attack_type
        rows.append(eff)
    return pd.DataFrame(rows)
