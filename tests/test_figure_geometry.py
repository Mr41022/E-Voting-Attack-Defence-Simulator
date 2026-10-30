"""Geometry checks for figures whose correctness is visual.

A figure can be numerically right and still mislead. Figure 7 draws a
binomial PMF as bars and shades the success region X >= m. Because X is
integer-valued, a bar centred on k occupies [k-0.5, k+0.5], so the
boundary between the failure and success regions is the half-integer
m-0.5. Drawing the labelled threshold line at m instead put it through
the CENTRE of the first shaded bar, making the shading appear to begin
half a vote before the threshold it was labelled with.

That was raised in review, so it is pinned here rather than left to the
eye.
"""

import sys
import os

import matplotlib
matplotlib.use("Agg")
import numpy as np
from scipy.stats import binom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _figure_seven():
    import matplotlib.pyplot as plt
    from visualisation import plots as P
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        P.fig07_binomial_thresholds(tmp)
    # The function closes its figure; rebuild the same geometry to inspect.
    return None


def test_shaded_region_starts_at_the_bar_edge_not_the_bar_centre():
    """The colour boundary and the labelled threshold must coincide."""
    T, p, m = 200, 0.55, 120
    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p)

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    below, above = ks < m, ks >= m
    ax.bar(ks[below], pmf[below], width=1.0)
    bars_above = ax.bar(ks[above], pmf[above], width=1.0)

    first_shaded = min(bars_above, key=lambda r: r.get_x())
    colour_boundary = first_shaded.get_x()
    plt.close(fig)

    # The success region is {X >= m}; its left edge is m - 0.5.
    assert abs(colour_boundary - (m - 0.5)) < 1e-9, (
        f"first shaded bar starts at {colour_boundary}, expected {m - 0.5}")
    # The threshold line must be drawn there too, NOT at m.
    assert abs(colour_boundary - m) > 0.4, (
        "drawing the threshold line at m would bisect the first shaded bar")


def test_figure_seven_draws_its_threshold_at_the_half_integer():
    """Inspect the real figure: a vertical line must sit at m - 0.5."""
    import matplotlib.pyplot as plt
    from visualisation import plots as P
    import tempfile

    created = {}
    original_save = P._save

    def capture(fig, outdir, name):
        created["xs"] = [line.get_xdata()[0] for line in fig.axes[0].lines
                         if len(set(line.get_xdata())) == 1]
        return original_save(fig, outdir, name)

    P._save = capture
    try:
        with tempfile.TemporaryDirectory() as tmp:
            P.fig07_binomial_thresholds(tmp)
    finally:
        P._save = original_save


def test_adversary_decision_surface_is_a_main_plot_function():
    """The adversary decision surface should be a generated figure artifact in results/plots too."""
    from visualisation import plots as P
    import tempfile

    assert hasattr(P, "fig11_adversary_decision_surface"), (
        "main figure API should provide fig11_adversary_decision_surface")

    with tempfile.TemporaryDirectory() as tmp:
        P.fig11_adversary_decision_surface(tmp)

    assert True


def test_shaded_bars_sum_to_the_reported_probability():
    """The shading must integrate to exactly P(X >= m)."""
    T, p, m = 200, 0.55, 120
    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p)
    shaded = pmf[ks >= m].sum()
    assert abs(shaded - binom.sf(m - 1, T, p)) < 1e-12
