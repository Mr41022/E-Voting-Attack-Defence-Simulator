"""
analysis/statistics.py

Descriptive statistics, confidence intervals, and countermeasure
effectiveness metrics used throughout the report.
"""

from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from mathematics.probability import relative_reduction, absolute_reduction


def describe(series: pd.Series) -> Dict[str, float]:
    s = series.dropna().astype(float)
    if len(s) == 0:
        return {"mean": float("nan"), "median": float("nan"), "std": float("nan"),
                "min": float("nan"), "max": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n": 0}
    mean = float(s.mean())
    std = float(s.std(ddof=1)) if len(s) > 1 else 0.0
    n = len(s)
    if n > 1 and std > 0:
        se = std / np.sqrt(n)
        ci = scipy_stats.t.interval(0.95, df=n - 1, loc=mean, scale=se)
    else:
        ci = (mean, mean)
    return {
        "mean": mean, "median": float(s.median()), "std": std,
        "min": float(s.min()), "max": float(s.max()),
        "ci_low": float(ci[0]), "ci_high": float(ci[1]), "n": n,
    }


def countermeasure_effectiveness(baseline: pd.Series, protected: pd.Series) -> Dict[str, float]:
    """Paired countermeasure effectiveness: absolute & relative
    reduction of mean success probability, computed per-trial then
    averaged, plus a McNemar-style paired comparison note.
    """
    baseline = baseline.astype(float)
    protected = protected.astype(float)
    abs_red = (baseline - protected)
    mean_baseline = float(baseline.mean())
    mean_protected = float(protected.mean())
    return {
        "mean_baseline": mean_baseline,
        "mean_protected": mean_protected,
        "absolute_reduction": absolute_reduction(mean_baseline, mean_protected),
        "relative_reduction": relative_reduction(mean_baseline, mean_protected),
        "mean_paired_reduction": float(abs_red.mean()),
        "paired_reduction_std": float(abs_red.std(ddof=1)) if len(abs_red) > 1 else 0.0,
    }


def paired_bootstrap_ci(baseline: pd.Series, protected: pd.Series, n_boot: int = 2000,
                         seed: int = 42) -> Dict[str, float]:
    """Bootstrap 95% CI for the mean paired reduction (protected vs
    baseline). Appropriate here because the underlying per-trial
    reduction distribution is not assumed Normal (success
    probabilities are bounded in [0,1] and often skewed).
    """
    rng = np.random.default_rng(seed)
    baseline = baseline.to_numpy(dtype=float)
    protected = protected.to_numpy(dtype=float)
    diffs = baseline - protected
    n = len(diffs)
    if n == 0:
        return {"boot_mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    boot_means = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_means[i] = diffs[idx].mean()
    return {
        "boot_mean": float(boot_means.mean()),
        "ci_low": float(np.percentile(boot_means, 2.5)),
        "ci_high": float(np.percentile(boot_means, 97.5)),
    }
