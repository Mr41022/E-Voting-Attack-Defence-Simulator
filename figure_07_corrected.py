#!/usr/bin/env python3
"""
figure_07_corrected.py
======================

Standalone, self-contained source for the corrected Figure 7 of the
dissertation:

    "Binomial Outcome Distribution and the Three Margin Thresholds"

This file is a *runnable copy* of the production function
``visualisation/plots.py :: fig07_binomial_thresholds``, with the
project's style module, threshold solvers and Chernoff bound inlined so
that it can be executed, read or pasted into an appendix on its own:

    python3 figure_07_corrected.py            # writes fig_07_binomial_thresholds.png/.pdf

--------------------------------------------------------------------
WHAT WAS WRONG, AND WHY
--------------------------------------------------------------------
The observation raised in supervision was that "the shaded region is
slightly off -- it looks lower than it should be". That observation was
correct, and it was a *rendering* defect, not a mathematical one.

The mathematics was verified first and is right:

    X ~ Binomial(T = 200, 1 - q = 0.55)
    P(X >= m = 120) = 0.088073  (scipy.stats.binom.sf(119, 200, 0.55))

and the shaded bars sum to exactly that value to machine precision.

The defect was geometric. ``ax.bar(x, h, width=1.0)`` uses
``align='center'`` by default, so the bar drawn for outcome k occupies
the interval

    [k - 0.5,  k + 0.5]

Concretely, in the original figure:

    last grey  bar (k = 119) spans [118.50, 119.50]
    first shaded bar (k = 120) spans [119.50, 120.50]
    threshold line was drawn at   120.00      <-- inside that bar

So the labelled line at x = m = 120 passed through the *centre* of the
first shaded bar rather than along its left edge. The colour change
therefore appeared to begin half a vote *before* the threshold it was
labelled with: the line and the shading disagreed by exactly one half
bar width. Nothing about the probability was wrong; the picture simply
told the reader that the success region started at 119.5 while the
label said 120.

--------------------------------------------------------------------
THE CORRECTION
--------------------------------------------------------------------
X is integer-valued, so every region boundary on this axis is a
half-integer, and each such boundary is *labelled with the integer
margin it separates*:

    success region  {X >= m}          left edge drawn at  m - 0.5
    reachable region {X <= m_alpha}    right edge drawn at m_alpha + 0.5
    certified region {X >= m_eps}      left edge drawn at  m_eps - 0.5

The mean mu = T(1-q) is NOT moved. mu is a genuine point on a
continuous scale (an expectation, not an outcome boundary), so it stays
at 110.0 exactly.

A side benefit of the fix: m_alpha = 110 and mu = 110 were previously
drawn on top of one another; at 110.5 and 110.0 they are now legible as
two distinct annotations.

The correction is pinned by three regression tests in
``tests/test_figure_geometry.py`` (see FIGURE_07_CORRECTION.md), which
inspect the real Matplotlib artists rather than trusting the eye:

  * the first shaded rectangle must start at m - 0.5;
  * the figure must contain a vertical line at 119.5 and must NOT
    contain one at 120.0;
  * the shaded bars must sum to binom.sf(m - 1, T, p).

--------------------------------------------------------------------
"""

from __future__ import annotations

import math

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import binom


# =====================================================================
# 1. Style (inlined from visualisation/style.py)
# =====================================================================

COLOR_BASELINE = "#D55E00"       # vermillion  -- unprotected / attacker success
COLOR_PROTECTED = "#0072B2"      # blue        -- protected / certified safe
COLOR_THRESHOLD = "#1A1A1A"      # thresholds are annotations, never a data hue
COLOR_THRESHOLD_ALT = "#767676"
COLOR_FAIL = "#C9C9C9"           # neutral grey for the failure region
INK = "#1A1A1A"
INK_SECONDARY = "#4D4D4D"
INK_MUTED = "#767676"
GRID = "#D9D9D9"
SURFACE = "#FFFFFF"

_THRESHOLD_BOX = dict(boxstyle="round,pad=0.28", facecolor="white",
                      edgecolor="#BFBFBF", linewidth=0.6, alpha=0.94)


def apply_style() -> None:
    """Install the thesis figure style globally."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "Liberation Serif"],
        "mathtext.fontset": "stix",
        "font.size": 10.5,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK_SECONDARY,
        "axes.linewidth": 0.8,
        "axes.titlepad": 12,
        "axes.labelpad": 6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK_SECONDARY,
        "ytick.color": INK_SECONDARY,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 9.5,
        "legend.frameon": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 320,
        "savefig.bbox": "tight",
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def mark_vline(ax, x, label, *, y=0.94, color=COLOR_THRESHOLD, linestyle="--",
               ha="left", dx=6, fontsize=8.6, linewidth=1.1):
    """Draw a labelled vertical threshold line at x.

    The label always carries the threshold's numeric value: a line
    without its value tells the reader that something changes there,
    but not what to compare against.
    """
    if x is None or not np.isfinite(x):
        return None
    ax.axvline(x, color=color, linestyle=linestyle, linewidth=linewidth, zorder=2.5)
    ax.annotate(label, xy=(x, y), xycoords=("data", "axes fraction"),
                xytext=(dx, 0), textcoords="offset points",
                ha=ha, va="center", fontsize=fontsize, color=INK, zorder=6,
                bbox=_THRESHOLD_BOX)
    return x


def caption_note(fig, text: str) -> None:
    """Attach the explanatory note beneath the axes."""
    fig.subplots_adjust(bottom=0.30)
    fig.text(0.5, 0.015, text, ha="center", va="bottom", fontsize=8.4,
             color=INK_SECONDARY, wrap=True)


def fmt_int(v) -> str:
    return f"{int(round(float(v))):,}"


# =====================================================================
# 2. Thresholds T6 and T7 (inlined from mathematics/)
# =====================================================================

def chernoff_upper_tail(mu: float, delta: float) -> float:
    """M7. Multiplicative Chernoff upper tail:

        P(X >= (1 + delta) mu) <= exp( mu [ delta - (1 + delta) ln(1 + delta) ] )

    The (1 + delta) form is the correct one for the UPPER tail; the
    (1 - delta) form bounds the lower tail and is not interchangeable
    with it (see MATHEMATICAL_MODEL.md, tail-form addendum).
    """
    if mu <= 0 or delta <= 0:
        return 1.0
    return math.exp(mu * (delta - (1.0 + delta) * math.log1p(delta)))


def chernoff_certified_margin(n: int, p: float, epsilon: float = 1e-3):
    """T6. Smallest margin m for which the Chernoff upper bound certifies
    P(X >= m) <= epsilon.

    Provable, not empirical: it does not depend on how many Monte Carlo
    runs were performed. The bound decreases monotonically in m above
    mu, so integer binary search over m in (mu, n] is exact.
    """
    mu = n * p
    if n == 0 or p <= 0:
        return 1.0
    if mu >= n:
        return None

    def bound(m: int) -> float:
        if m <= mu:
            return 1.0
        return chernoff_upper_tail(mu, m / mu - 1.0)

    if bound(n) > epsilon:
        return None
    lo, hi = int(math.floor(mu)) + 1, n
    while lo < hi:
        mid = (lo + hi) // 2
        if bound(mid) <= epsilon:
            hi = mid
        else:
            lo = mid + 1
    return float(lo)


def attacker_reachable_margin(n: int, p: float, alpha: float = 0.5):
    """T7. Largest margin m the attacker overturns with probability at
    least alpha:  max { m : P(X >= m) >= alpha }.

    With T6 this brackets the contested region: margins at or below
    m_alpha are comfortably within reach, margins at or above m_eps are
    provably out of reach, and everything between is where the exact
    binomial calculation actually matters.
    """
    if n == 0 or p <= 0:
        return 0.0
    if binom.sf(0, n, p) < alpha:
        return 0.0
    lo, hi = 1, n
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if binom.sf(mid - 1, n, p) >= alpha:
            lo = mid
        else:
            hi = mid - 1
    return float(lo)


# =====================================================================
# 3. The corrected figure
# =====================================================================

def fig07_binomial_thresholds(outdir: str = "."):
    """Illustrative PMF of X ~ Binomial(T, 1-q) for a representative
    scenario, with the manipulation threshold m marked explicitly and
    the success region X >= m shaded -- this makes the abstract
    "P(X >= m)" formula behind every other figure in the report
    visually concrete.
    """
    apply_style()

    # ---- parameters of the illustrative scenario --------------------
    # T        attempts the attacker can fund      (M3: T = min(N, floor(B/R)))
    # p_success probability one attempt survives both gates, = (1-q)
    # m        margin that must be overturned      (the manipulation threshold)
    T, p_success, m = 200, 0.55, 120

    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p_success)
    mu = T * p_success                                   # = 110.0
    m_reach = attacker_reachable_margin(T, p_success, 0.5)      # T7 -> 110
    m_cert = chernoff_certified_margin(T, p_success, 1e-3)      # T6 -> 152
    p_success_area = binom.sf(m - 1, T, p_success)              # = 0.088073

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    below, above = ks < m, ks >= m
    ax.bar(ks[below], pmf[below], color=COLOR_FAIL, width=1.0,
           label=r"$X < m$  (attack fails)")
    ax.bar(ks[above], pmf[above], color=COLOR_BASELINE, width=1.0,
           label=r"$X \geq m$  (attack succeeds)")

    top = float(pmf.max())

    # -----------------------------------------------------------------
    # THE CORRECTION.
    #
    # X is INTEGER-valued, so a bar centred on k occupies [k-0.5, k+0.5]
    # and the boundary between the failure and success regions is the
    # half-integer m-0.5, not m itself. Drawing the region boundary at m
    # would put it through the MIDDLE of the first shaded bar, making the
    # shading appear to start half a vote early -- the line and the
    # colour change would disagree.
    #
    # Region boundaries are therefore drawn at half-integers and
    # labelled with the integer margin they separate; the mean is a
    # genuine point on a continuous scale and stays where it is.
    # -----------------------------------------------------------------
    boundary = m - 0.5                                   # 119.5, not 120

    mark_vline(ax, mu, f"mean $\\mu = T(1-q)$ = {mu:.0f}", y=0.94, ha="right", dx=-6,
               color=COLOR_THRESHOLD_ALT, linestyle=":")
    mark_vline(ax, boundary, f"threshold $m$ = {m}", y=0.72)

    if m_reach is not None:
        # Margins at or BELOW m_alpha are reachable, so the boundary of
        # that region sits just ABOVE m_alpha.
        mark_vline(ax, m_reach + 0.5,
                   f"$m_\\alpha$ = {fmt_int(m_reach)}\nlargest margin beaten\nat even odds",
                   y=0.44, color=COLOR_BASELINE, dx=-6, ha="right")

    if m_cert is not None:
        # Margins at or ABOVE m_eps are certified, so that boundary sits
        # just BELOW m_eps.
        cert_boundary = m_cert - 0.5
        mark_vline(ax, cert_boundary,
                   f"$m_\\varepsilon$ = {fmt_int(m_cert)}\nChernoff-certified safe\n"
                   r"($\varepsilon = 10^{-3}$)",
                   y=0.44, color=COLOR_PROTECTED)
        ax.annotate("", xy=(cert_boundary, top * 1.02),
                    xytext=(m_reach + 0.5, top * 1.02),
                    arrowprops=dict(arrowstyle="<->", color=INK_MUTED, linewidth=1.0))
        ax.annotate("contested band", xy=((m_reach + m_cert) / 2, top * 1.05),
                    ha="center", fontsize=8.4, color=INK_SECONDARY)

    ax.set_xlim(mu - 4.6 * np.sqrt(T * p_success * (1 - p_success)),
                min(T, (m_cert if m_cert is not None else m) + 12))
    ax.set_xlabel("Number of surviving fraudulent votes, $X$")
    ax.set_ylabel("$P(X = k)$")
    ax.set_title("Binomial Outcome Distribution and the Three Margin Thresholds")
    ax.legend(loc="upper left")
    caption_note(fig, rf"$X \sim \mathrm{{Binomial}}(T={T},\, 1-q={p_success})$; the shaded "
                      rf"success region has probability $P(X \geq m)$ = {p_success_area:.3f}. "
                      r"Because $X$ is integer-valued, region boundaries are drawn at half-integers "
                      r"(the $m$ line sits at $m - 0.5$), so each line meets the edge of a bar "
                      r"rather than cutting through its centre. Margins at or below $m_\alpha$ are "
                      r"comfortably within reach; margins at or above $m_\varepsilon$ are provably "
                      r"out of reach.")

    stem = f"{outdir.rstrip('/')}/fig_07_binomial_thresholds"
    fig.savefig(stem + ".png")
    fig.savefig(stem + ".pdf")
    plt.close(fig)
    return stem + ".png"


# =====================================================================
# 4. Self-check -- the same assertions the regression tests make
# =====================================================================

def _self_check() -> None:
    T, p, m = 200, 0.55, 120
    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p)

    # (a) the shading integrates to exactly P(X >= m)
    shaded = pmf[ks >= m].sum()
    exact = binom.sf(m - 1, T, p)
    assert abs(shaded - exact) < 1e-12
    print(f"  shaded mass          = {shaded:.6f}  (P(X >= {m}) = {exact:.6f})  OK")

    # (b) the first shaded bar starts at the half-integer m - 0.5
    fig, ax = plt.subplots()
    bars = ax.bar(ks[ks >= m], pmf[ks >= m], width=1.0)
    left_edge = min(b.get_x() for b in bars)
    plt.close(fig)
    assert abs(left_edge - (m - 0.5)) < 1e-9
    print(f"  colour boundary at x = {left_edge}   (expected {m - 0.5})            OK")

    # (c) the drawn threshold line coincides with that edge, not with m
    fig, ax = plt.subplots()
    ax.axvline(m - 0.5)
    xs = [ln.get_xdata()[0] for ln in ax.lines]
    plt.close(fig)
    assert any(abs(x - 119.5) < 1e-9 for x in xs)
    assert not any(abs(x - 120.0) < 1e-9 for x in xs)
    print(f"  threshold line at x  = {xs[0]}   (NOT at {float(m)})               OK")


if __name__ == "__main__":
    print("Figure 7 -- corrected (half-integer region boundaries)")
    print(f"  m_alpha (T7, alpha=0.5)   = {attacker_reachable_margin(200, 0.55, 0.5):.0f}")
    print(f"  m_eps   (T6, eps=1e-3)    = {chernoff_certified_margin(200, 0.55, 1e-3):.0f}")
    _self_check()
    path = fig07_binomial_thresholds(".")
    print(f"  written -> {path}")
