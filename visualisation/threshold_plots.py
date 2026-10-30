"""
visualisation/threshold_plots.py

Figures 6, 9 and 10: the threshold and coalition extension (T1-T7, G1-G2).

Where the other figures answer "how likely is this attack to succeed?",
these answer "where does the answer change?" -- each is built around a
threshold value that is drawn on the axes and labelled with its number,
because that number is what a defender can design against.

    Fig 6   Attacker utility vs detection probability, with q_d* and q_v*
    Fig 9   Expected vector capacity against the manipulation threshold
    Fig 10  Coalition vs best single vector, per scenario

(This module previously held eight figures of a thirty-figure set. That
set was cut to ten: five of the eight were removed and the remaining
three renumbered. Nothing here should refer to the old numbering.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binom

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from visualisation.plots import _save
from visualisation.style import (
    apply_style, caption_note, mark_hline, mark_point, mark_vline, shade_region,
    fmt_int, fmt_money,
    ATTACK_COLORS, ATTACK_LABELS, ATTACK_MARKERS,
    SYSTEM_COLORS, SYSTEM_LABELS,
    COLOR_BASELINE, COLOR_PROTECTED, COLOR_COALITION, COLOR_THRESHOLD,
    COLOR_THRESHOLD_ALT, COLOR_SYBIL, COLOR_BALLOT, COLOR_BRIBERY,
    SEQUENTIAL_CMAP, INK, INK_SECONDARY, INK_MUTED,
)

# Fixed hue order for per-scenario series. Scenario
# identity is not attack identity, so the series are assigned from this
# explicit list rather than by reusing the attack palette positionally.
SCENARIO_COLORS = [COLOR_BRIBERY, COLOR_SYBIL, COLOR_BALLOT, COLOR_PROTECTED,
                   COLOR_COALITION]

apply_style()


def fig06_critical_detection(detection_df: pd.DataFrame, thresholds_df: pd.DataFrame,
                                outdir: str, scenario_id: str = "S2"):
    """T5 made visible: the attacker's expected utility from mounting the
    attack, as detection probability rises, for one scenario.

    Two thresholds sit on this axis and they mean different things.
    q_d* is where attacking stops paying -- the attacker is still able
    to bribe, but no longer wants to. q_v* is where the targeted voters
    themselves refuse, so the attack cannot proceed at any budget. The
    first is the defender's efficient target; the second is the harder
    guarantee. The gap between them is the region in which deterrence
    depends on the attacker being rational.
    """
    d = detection_df[detection_df.scenario_id == scenario_id].sort_values("q")
    t = thresholds_df[(thresholds_df.scenario_id == scenario_id) &
                      (thresholds_df.system_type == "baseline")].iloc[0]

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    # Mask the sentinel. Beyond q_v* no attempt is affordable or accepted,
    # and best_attacking_utility returns a large negative marker meaning
    # "no attack exists here". Plotting it as a utility put a flat
    # -2.15e6 floor on the axis that was not an expected value and that
    # set the entire lower half of the y-range.
    u = d["signed_attack_utility"].astype(float).copy()
    if "attack_exists" in d.columns:
        u = u.where(d["attack_exists"].astype(bool))
    ax.plot(d["q"], u, color=COLOR_BASELINE, linewidth=2.2,
            label="Expected utility of attacking, $\\max_{T \\geq 1} U(T)$")
    ax.axhline(0, color=COLOR_THRESHOLD_ALT, linewidth=0.9)
    if "attack_exists" in d.columns and (~d["attack_exists"].astype(bool)).any():
        q_none = float(d.loc[~d["attack_exists"].astype(bool), "q"].min())
        ax.axvspan(q_none, float(d["q"].max()), color=INK_MUTED, alpha=0.07,
                   linewidth=0, zorder=0)
        ax.annotate("no attack exists:\nno attempt is\naffordable or accepted",
                    xy=(q_none, 0.06), xycoords=("data", "axes fraction"),
                    xytext=(8, 0), textcoords="offset points", ha="left",
                    va="bottom", fontsize=8.2, color=INK_SECONDARY)

    q_d = t["q_defender_critical"]
    q_v = t["q_voter_indifference"]
    if pd.notna(q_d):
        shade_region(ax, 0.0, float(q_d), "attack pays", COLOR_BASELINE)
        mark_vline(ax, float(q_d),
                   f"$q_d^*$ = {float(q_d):.3f}\nattack stops paying", y=0.80)
    if pd.notna(q_v):
        mark_vline(ax, float(q_v),
                   f"$q_v^*$ = {float(q_v):.3f}\nvoters refuse outright", y=0.52,
                   color=COLOR_PROTECTED)
    protected_q = float(thresholds_df[(thresholds_df.scenario_id == scenario_id) &
                                      (thresholds_df.system_type == "protected")]["q"].iloc[0])
    mark_vline(ax, protected_q,
               f"protected system\noperates at $q$ = {protected_q:.2f}", y=0.24,
               color=COLOR_THRESHOLD_ALT, linestyle="-.")

    ax.set_xlim(-0.01, min(1.0, protected_q + 0.12))
    ax.set_xlabel("Detection probability, $q$")
    ax.set_ylabel("Expected attacker utility")
    ax.set_title(f"Critical Detection Threshold ({scenario_id}, "
                 f"{t['name'].split(' (')[0]})")
    ax.legend(loc="center right")
    if pd.isna(q_d) or pd.isna(q_v):
        caption_note(fig, f"The protected configuration operates at $q$ = {protected_q:.0%}. "
                          f"Not every threshold exists for this scenario; those that do not are "
                          f"omitted rather than defaulted.")
        ax.legend(loc="center right")
        fig.tight_layout()
        return _save(fig, outdir, "fig_06_critical_detection")
    caption_note(fig, f"Only about {float(q_d):.1%} detection is needed to make this attack "
                      f"unprofitable, well below the {float(q_v):.1%} at which voters would refuse "
                      f"outright, and far below the {protected_q:.0%} the protected configuration "
                      f"actually achieves.")
    return _save(fig, outdir, "fig_06_critical_detection")

def fig10_coalition_vs_pure(coalition_df: pd.DataFrame, outdir: str):
    """G2 headline: for each scenario, the best single-vector attack
    against the best mixed-vector attack, baseline and protected."""
    base = coalition_df[coalition_df.system_type == "baseline"].reset_index(drop=True)
    # Align the protected rows to the baseline rows BY SCENARIO, not by
    # row order. Two separate reset_index calls joined positionally, which
    # is silently wrong the moment the CSV is reordered or filtered.
    prot = (coalition_df[coalition_df.system_type == "protected"]
            .set_index("scenario_id")
            .reindex(base["scenario_id"])
            .reset_index())
    y = np.arange(len(base))
    height = 0.34

    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    ax.barh(y + height / 2, base["best_pure_exact_p"], height=height, color="#C9C9C9",
            edgecolor="white", linewidth=1.4, label="Best single vector (baseline)")
    ax.barh(y - height / 2, base["coalition_exact_p"], height=height, color=COLOR_COALITION,
            edgecolor="white", linewidth=1.4, label="Best coalition (baseline)")
    ax.scatter(prot["coalition_exact_p"], y, color=COLOR_PROTECTED, s=90, zorder=5,
               marker="s", edgecolor="white", linewidth=1.1,
               label="Best coalition (protected)")

    for yi, r in zip(y, base.itertuples()):
        ax.annotate(f"{r.best_pure_exact_p:.3f}", (r.best_pure_exact_p, yi + height / 2),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=8.4, color=INK)
        ax.annotate(f"{r.coalition_exact_p:.3f}", (r.coalition_exact_p, yi - height / 2),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=8.4, color=INK)

    # Even-odds marker labelled high on the axis: the S1 row sits at the
    # bottom and its bar labels would otherwise collide with the legend.
    mark_vline(ax, 0.5, "even odds", y=0.94, color=COLOR_THRESHOLD_ALT, linestyle=":")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.scenario_id}: {r.name.split(' (')[0]}" for r in base.itertuples()],
                       fontsize=9.5)
    ax.set_xlabel(r"Exact success probability, $P(\mathrm{surviving\ fraudulent\ votes} \geq m)$")
    ax.set_xlim(0, 1.12)
    ax.set_title("Multi-Vector Coalition vs Best Single-Vector Attack")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    caption_note(fig, "Protected coalition markers sit at zero in every one of these "
                      "benchmark scenarios, under these parameter settings: the countermeasure "
                      "configuration reduces the mixed attack to the same degree as it reduces "
                      "each single vector. The wider randomised trials retain a non-zero "
                      "residual, so this is a statement about these scenarios, not a general "
                      "impossibility result.")
    fig.tight_layout()
    return _save(fig, outdir, "fig_10_coalition_vs_pure")

def fig09_vector_capacity(vector_df: pd.DataFrame, outdir: str,
                          coalition_df: pd.DataFrame | None = None):
    """Why a rational attacker declines a vector: EXPECTED capacity
    against the threshold, and what that does to success probability.

    IMPORTANT -- what the bars are, and what they are not.
    ------------------------------------------------------
    Each bar is  E[X] / m = n_max * p_survive / m: the *expected* number
    of surviving fraudulent votes at full structural capacity, as a
    multiple of the manipulation threshold. It is a MEAN, not a ceiling.

    A bar below 1.0 therefore means the expected count falls short of the
    threshold -- NOT that the threshold is unreachable. Success is still
    possible on an upward fluctuation, and the annotation on each bar
    gives the exact P(X >= m) at full effort so the reader can see how
    fast that possibility collapses: about 0.42 at a ratio of 0.97, 0.023
    at 0.97 for a larger n, and numerically zero by a ratio of 0.74.
    An earlier version of this figure claimed a sub-1.0 bar "cannot reach
    the threshold at any budget", which is false and is contradicted by
    those very numbers.

    The diamond is the OPTIMAL COALITION's expected capacity, taken from
    the coalition search (mu_total / m). That is a budget-FEASIBLE
    allocation of one budget across the three vectors. It replaces an
    earlier marker that summed each vector's independent full capacity --
    a quantity no attacker can buy, since funding all three at once
    exceeds the budget in four of the five scenarios.
    """
    base = vector_df[vector_df.system_type == "baseline"].copy()
    base["capacity_ratio"] = (base["n_feasible"] * base["p_survive"]) / base["m"]
    # Exact success probability at full structural effort. This is the
    # honest companion to the ratio: it is what "below the line" actually
    # costs the attacker.
    base["p_full"] = [
        float(binom.sf(int(m) - 1, int(n), float(pp))) if n > 0 else 0.0
        for n, pp, m in zip(base["n_feasible"], base["p_survive"], base["m"])
    ]
    scenarios = list(dict.fromkeys(base["scenario_id"]))
    vectors = ["bribery", "sybil", "ballot_stuffing"]
    x = np.arange(len(scenarios))
    width = 0.26

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    for i, vec in enumerate(vectors):
        sub = base[base.vector == vec].set_index("scenario_id").loc[scenarios]
        offset = (i - 1) * width
        ax.bar(x + offset, sub["capacity_ratio"], width=width * 0.9,
               color=ATTACK_COLORS[vec], edgecolor="white", linewidth=1.4,
               label=ATTACK_LABELS[vec])
        for xi, ratio, p_full in zip(x + offset, sub["capacity_ratio"], sub["p_full"]):
            # Label carries BOTH numbers: the mean ratio and what the
            # attacker's actual chance is at that ratio.
            #
            # Three decimals once the ratio is within 0.01 of 1.0: at two
            # decimals 0.997 prints as "1.00", which contradicts the line
            # it is sitting below and was flagged in review.
            txt = f"{ratio:.3f}" if ratio > 0.99 else f"{ratio:.2f}"
            if p_full >= 5e-4:
                txt += f"\n$P$={p_full:.2f}"
            ax.annotate(txt, (xi, ratio), xytext=(0, 4),
                        textcoords="offset points", ha="center", fontsize=7.0,
                        color=INK, linespacing=1.15)

    if coalition_df is not None:
        coal = (coalition_df[coalition_df.system_type == "baseline"]
                .set_index("scenario_id").loc[scenarios])
        totals = coal["mu_total"] / coal["m"]
        marker_label = "Optimal coalition (one budget, split)"
    else:
        totals = base.groupby("scenario_id")["capacity_ratio"].sum().loc[scenarios]
        marker_label = "All three at full capacity (not budget-feasible)"
    ax.scatter(x, totals, marker="D", s=76, color=COLOR_COALITION, zorder=6,
               edgecolor="white", linewidth=1.1, label=marker_label)
    group_max = base.groupby("scenario_id")["capacity_ratio"].max().loc[scenarios]
    for xi, total, gmax in zip(x, totals, group_max):
        # Diamond labels go ABOVE the marker, not beside it: to the right
        # they collided with the neighbouring group's bar labels.
        #
        # Where the optimal coalition degenerates to a single vector (S5,
        # whose optimum is the pure bribery corner) the diamond lands on
        # that bar's own label, so it is nudged sideways instead.
        coincides = abs(float(total) - float(gmax)) < 0.02 * max(float(gmax), 1e-9)
        dx, dy, ha_ = (14, 0, "left") if coincides else (0, 9, "center")
        ax.annotate(f"{float(total):.2f}", (xi, total), xytext=(dx, dy),
                    textcoords="offset points", ha=ha_,
                    va="center" if coincides else "bottom",
                    fontsize=8.2, color=INK, fontweight="bold")

    # Label parked at the far right, clear of every bar and diamond label.
    mark_hline(ax, 1.0, "expected capacity = $m$", x=0.985, ha="right", dy=4)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{sid}" for sid in scenarios])
    ax.set_xlabel("Benchmark scenario")
    ax.set_ylabel(r"Expected capacity at full effort, $n_{\max}\,p_{\mathrm{survive}} / m$")
    ax.set_title("Expected Vector Capacity Against the Manipulation Threshold (Baseline)")
    ax.set_ylim(top=float(np.max(totals)) * 9.0)
    ax.legend(ncol=4, loc="upper left", fontsize=8.4,
              columnspacing=1.1, handletextpad=0.5)
    caption_note(fig, "Bars are EXPECTED surviving votes over the threshold, so a bar below the "
                      "line means the mean falls short -- not that the threshold is out of reach. "
                      "$P$ is the exact success probability at full effort, and it shows how "
                      "quickly that distinction stops mattering: 0.42 where the ratio is 0.97, "
                      "and numerically zero once the ratio drops below about 0.7. The diamond is "
                      "the optimal split of a single budget across all three vectors, which is "
                      "budget-feasible and clears the line in four of the five scenarios.")
    fig.tight_layout()
    return _save(fig, outdir, "fig_09_vector_capacity")
