"""
analysis/validation.py

Monte Carlo error and Chernoff-bound conservativeness computations
used for RQ5/RQ6 and Experiment 11/12.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def monte_carlo_error_stats(df: pd.DataFrame,
                             exact_col: str = "exact_probability",
                             mc_col: str = "monte_carlo_probability") -> dict:
    if exact_col not in df.columns or mc_col not in df.columns:
        return {}
    abs_err = (df[mc_col] - df[exact_col]).abs()
    rel_err = abs_err / df[exact_col].replace(0, np.nan)
    return {
        "mean_absolute_error": float(abs_err.mean()),
        "max_absolute_error": float(abs_err.max()),
        "mean_relative_error": float(rel_err.dropna().mean()) if rel_err.notna().any() else float("nan"),
    }


def chernoff_conservativeness_stats(df: pd.DataFrame,
                                     exact_col: str = "exact_probability",
                                     chernoff_col: str = "chernoff_bound") -> dict:
    sub = df[df[chernoff_col].notna()]
    if len(sub) == 0:
        return {"n_valid": 0, "mean_conservativeness": float("nan"),
                "pct_bound_holds": float("nan")}
    conservativeness = sub[chernoff_col] - sub[exact_col]
    holds = (sub[chernoff_col] >= sub[exact_col] - 1e-9)
    return {
        "n_valid": int(len(sub)),
        "mean_conservativeness": float(conservativeness.mean()),
        "min_conservativeness": float(conservativeness.min()),
        "max_conservativeness": float(conservativeness.max()),
        "pct_bound_holds": float(holds.mean() * 100),
    }
