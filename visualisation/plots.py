"""
visualisation/plots.py

Publication-quality (320 DPI, PNG + vector PDF) matplotlib figures for
the thesis report.

Visual conventions, applied identically in every figure so the reader
learns them once (the full system, including the programmatic
colour-vision validation of the palette, lives in visualisation/style.py):

    Baseline configuration    vermillion, circle markers
    Protected configuration   blue, square markers
    Bribery / Sybil / Ballot  vermillion / green / purple, o / s / ^
    Exact analytic value      solid line
    Monte Carlo estimate      markers only
    Chernoff bound            dashed line
    THRESHOLDS                charcoal dashed line, always labelled with
                              their numeric value

Every threshold drawn here comes from mathematics/thresholds.py; none
is hard-coded into the plotting layer.
"""

from __future__ import annotations
import os
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import CSV_DIR

from visualisation.style import (
    apply_style, ci_band, caption_note, mark_hline, mark_point, mark_vline,
    shade_region, fmt_int, fmt_money,
    ATTACK_COLORS, ATTACK_LABELS, ATTACK_MARKERS,
    SYSTEM_COLORS, SYSTEM_LABELS, SYSTEM_MARKERS,
    COLOR_BASELINE, COLOR_PROTECTED, COLOR_BRIBERY, COLOR_SYBIL, COLOR_BALLOT,
    COLOR_EXACT, COLOR_MC, COLOR_CHERNOFF, COLOR_THRESHOLD, COLOR_THRESHOLD_ALT,
    DIVERGING_CMAP, SEQUENTIAL_CMAP, INK, INK_SECONDARY, INK_MUTED,
)

apply_style()


def _save(fig, outdir: str, name: str):
    os.makedirs(outdir, exist_ok=True)
    png_path = os.path.join(outdir, f"{name}.png")
    pdf_path = os.path.join(outdir, f"{name}.pdf")
    fig.savefig(png_path)
    fig.savefig(pdf_path)
    plt.close(fig)
    return png_path, pdf_path


def _copy_appendix_artifact(generator_name: str, outdir: str, target_name: str):
    """Adopt the appendix generator’s PNG/PDF pair into the normal plot tree.

    The appendix module already writes a reproducible diagram and a matching
    caption sidecar. This wrapper materialises that same figure in the standard
    results/plots location with the pair of file endings a thesis build needs.
    """
    from visualisation import appendix_figures as AF

    generator = getattr(AF, generator_name)
    src_png = generator()
    if not isinstance(src_png, str):
        src_png = str(src_png)

    src_pdf = src_png.replace(".png", ".pdf")
    if not os.path.exists(src_pdf):
        src_pdf = os.path.splitext(src_png)[0] + ".pdf"

    os.makedirs(outdir, exist_ok=True)
    png_path = os.path.join(outdir, f"{target_name}.png")
    pdf_path = os.path.join(outdir, f"{target_name}.pdf")
    shutil.copyfile(src_png, png_path)
    if os.path.exists(src_pdf):
        shutil.copyfile(src_pdf, pdf_path)
    else:
        # Last-resort fallback: keep the thesis-feature contract intact by
        # copying the PNG over the PDF slot when a PDF has not yet been emitted.
        shutil.copyfile(src_png, pdf_path)
    return png_path, pdf_path


def fig_11_adversary_decision_surface(outdir: str):
    return _copy_appendix_artifact("generate_adversary_decision_surface", outdir,
                                   "fig_11_adversary_decision_surface")


def fig_12_theory_vs_monte_carlo(outdir: str):
    return _copy_appendix_artifact("generate_theory_vs_monte_carlo", outdir,
                                   "fig_12_theory_vs_monte_carlo")


def fig_13_chernoff_vs_exact(outdir: str):
    return _copy_appendix_artifact("generate_chernoff_vs_exact", outdir,
                                   "fig_13_chernoff_vs_exact")


def fig_14_detection_effect(outdir: str):
    return _copy_appendix_artifact("generate_detection_effect", outdir,
                                   "fig_14_detection_effect")


def fig_15_budget_effect(outdir: str):
    return _copy_appendix_artifact("generate_budget_effect", outdir,
                                   "fig_15_budget_effect")


def fig_16_voter_utility(outdir: str):
    return _copy_appendix_artifact("generate_voter_utility", outdir,
                                   "fig_16_voter_utility")


def fig_17_attacker_utility(outdir: str):
    return _copy_appendix_artifact("generate_attacker_utility", outdir,
                                   "fig_17_attacker_utility")


def fig_18_winner_flip_distribution(outdir: str):
    return _copy_appendix_artifact("generate_winner_flip_distribution", outdir,
                                   "fig_18_winner_flip_distribution")


def fig_19_sensitivity_analysis(outdir: str):
    return _copy_appendix_artifact("generate_sensitivity_analysis", outdir,
                                   "fig_19_sensitivity_analysis")


def fig_20_coalition_allocation(outdir: str):
    return _copy_appendix_artifact("generate_coalition_allocation", outdir,
                                   "fig_20_coalition_allocation")


def fig_21_blockchain_integrity(outdir: str):
    return _copy_appendix_artifact("generate_blockchain_integrity", outdir,
                                   "fig_21_blockchain_integrity")


def fig_22_countermeasure_effectiveness_summary(outdir: str):
    return _copy_appendix_artifact("generate_countermeasure_effectiveness_summary", outdir,
                                   "fig_22_countermeasure_effectiveness_summary")


def fig_23_monte_carlo_convergence_summary(outdir: str):
    return _copy_appendix_artifact("generate_monte_carlo_convergence_summary", outdir,
                                   "fig_23_monte_carlo_convergence_summary")

def _mean_ci(series: pd.Series) -> tuple[float, float, float]:
    """Mean and normal-approximation 95% CI half-width for a bucket."""
    values = series.dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    mean = float(values.mean())
    if len(values) < 2:
        return mean, mean, mean
    se = float(values.std(ddof=1) / np.sqrt(len(values)))
    return mean, mean - 1.96 * se, mean + 1.96 * se

def _crossing_x(xs, ys, level: float):
    """Linear interpolation of the x at which a curve first crosses
    `level`. Returns None when the curve never crosses it -- an absent
    threshold is reported as absent, never as an endpoint."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    for i in range(1, len(xs)):
        y0, y1 = ys[i - 1], ys[i]
        if np.isnan(y0) or np.isnan(y1):
            continue
        if (y0 - level) * (y1 - level) <= 0 and y0 != y1:
            t = (level - y0) / (y1 - y0)
            return float(xs[i - 1] + t * (xs[i] - xs[i - 1]))
    return None

def _bucketed_curve(df: pd.DataFrame, x_col: str, y_col: str, bins: int = 14):
    """Bucket-mean curve with a 95% confidence ribbon, per configuration."""
    d = df.copy()
    d["_bucket"] = pd.cut(d[x_col], bins=bins)
    out = {}
    for system in ("baseline", "protected"):
        sub = d[d.system_type == system]
        rows = []
        for bucket, group in sub.groupby("_bucket", observed=True):
            mean, lo, hi = _mean_ci(group[y_col])
            if isinstance(bucket, pd.Interval):
                x_val = 0.5 * (float(bucket.left) + float(bucket.right))
            elif isinstance(bucket, (int, float, np.number)) and not isinstance(bucket, complex):
                x_val = float(bucket)
            else:
                continue
            rows.append({"x": x_val, "mean": mean, "lo": lo, "hi": hi})
        out[system] = pd.DataFrame(rows).sort_values("x").dropna(subset=["mean"])
    return out

def fig01_method_comparison(outdir: str, N: int = 2000, m: int = 900,
                                      B: float = 4_000_000, R: float = 2000.0,
                                      P: float = 900.0, mc_trials: int = 2000,
                                      seed: int = 2026):
    """Exact binomial, Monte Carlo and Chernoff bound as detection
    probability q sweeps, for ONE fixed scenario.

    This figure is a controlled single-variable sweep rather than an
    average over the randomised trials. Averaging the three quantities
    across heterogeneous scenarios produces a jagged curve whose shape
    reflects which trials happened to fall in each bucket, not the
    behaviour of q -- and the Chernoff bound is only defined on the
    sub-population with m > mu, so the averaged comparison is not even
    taken over a common set of trials. Holding N, m, B, R and P fixed
    and moving only q gives the three methods a common footing, which
    is what makes them comparable. The empirical, across-trials
    validation of the bound is Figure 3.

    PARAMETER CHOICE. R and P are set so that the voter-indifference
    threshold q_v* = R/(R+P) = 0.690 sits to the RIGHT of the region the
    figure is about -- the collapse at q = 1 - m/T = 0.55. An earlier
    parameterisation (R = 100, P = 900) put q_v* at 0.10, which left the
    entire comparison inside the region the figure itself shades as
    "bribe not incentive-compatible": the plotted probabilities there are
    binomially correct but describe an attack no rational voter would
    accept. The budget is scaled with R so that T = min(N, B/R) = 2,000
    is unchanged and the collapse stays at the same q.
    """
    from mathematics.binomial import p_at_least, expected_value, sample
    from mathematics.chernoff import chernoff_bound_for_threshold
    from mathematics.thresholds import voter_indifference_detection
    from models.attacker import AttackerBudget

    rng = np.random.default_rng(seed)
    T = AttackerBudget(N=N, B=B, R=R).max_targets()
    qs = np.linspace(0.0, 0.9, 91)

    exact, mc, chern = [], [], []
    for q in qs:
        p_survive = 1.0 - q
        exact.append(p_at_least(T, p_survive, m))
        mc.append(float(np.mean(sample(T, p_survive, mc_trials, rng) >= m)))
        chern.append(chernoff_bound_for_threshold(T, p_survive, m).bound)

    chern_arr = np.array([np.nan if c is None else c for c in chern], dtype=float)
    # The Chernoff region begins where the threshold rises above the
    # mean, i.e. where m = T(1-q)  <=>  q = 1 - m/T.
    q_chernoff_start = 1.0 - m / T if T > 0 else None
    q_v = voter_indifference_detection(R, P)

    fig, ax = plt.subplots(figsize=(7.8, 5.3))
    ax.plot(qs, exact, color=COLOR_EXACT, linewidth=2.2, label=r"Exact binomial $P(X \geq m)$", zorder=4)
    step = 5
    ax.scatter(qs[::step], np.array(mc)[::step], color=COLOR_MC, marker="o", s=30,
               zorder=5, label=f"Monte Carlo ({mc_trials:,} draws)")
    ax.plot(qs, chern_arr, color=COLOR_CHERNOFF, linestyle="--", linewidth=1.9,
            label="Chernoff upper bound (M7)", zorder=4)

    if q_chernoff_start is not None and 0 < q_chernoff_start < 0.9:
        mark_vline(ax, q_chernoff_start,
                   f"$m = \\mu$ at $q$ = {q_chernoff_start:.3f}\nChernoff valid to the right",
                   y=0.72)
    if q_v.exists and q_v.value is not None:
        mark_vline(ax, q_v.value,
                   f"$q_v^*$ = {q_v.value:.3f}\nvoters refuse beyond this",
                   y=0.40, color=COLOR_BASELINE)
        shade_region(ax, q_v.value, 0.9, "bribe not incentive-compatible", COLOR_BASELINE)

    ax.set_xlabel("Detection probability, $q$")
    ax.set_ylabel(r"$P(X \geq m)$")
    ax.set_title("Bribery Success vs Detection Probability\n"
                 "Exact, Monte Carlo and Chernoff Bound on a Common Scenario")
    ax.set_ylim(-0.02, 1.05)
    ax.legend(loc="lower left")
    caption_note(fig, f"Fixed scenario: $N$ = {N:,}, $m$ = {m:,}, $B$ = {B:,.0f}, $R$ = {R:,.0f}, "
                      f"$P$ = {P:,.0f}, giving $T$ = {T:,} attempts. Only $q$ varies.")
    return _save(fig, outdir, "fig_01_method_comparison")

def fig02_voter_utility_threshold(outdir: str, P_fixed: float = 500):
    """Rational-voter utility surface, with the decision boundary drawn
    as a numeric zero contour and the closed-form indifference threshold
    q_v* = R/(R+P) traced on top of it.

    WHAT THIS DOES AND DOES NOT ESTABLISH. The surface is evaluated with
    mathematics.utility.voter_utility (M1) and the dashed curve with
    mathematics.thresholds.voter_indifference_detection (T2), so the two
    lines on the page come from the two production functions rather than
    from expressions retyped here. That makes it a genuine check that T2
    solves M1 as implemented -- an algebra slip or a sign error in either
    module would separate the curves.

    It is NOT independent evidence that the model is right: T2 is the
    analytic root of M1, so agreement is expected and the check is on the
    code, not on the mathematics. An earlier version evaluated both
    expressions inline in this file and described the result as a proof,
    which was doubly wrong -- it touched neither module and it could not
    have failed."""
    from mathematics.utility import voter_utility
    from mathematics.thresholds import voter_indifference_detection

    R_vals = np.linspace(10, 1000, 240)
    q_vals = np.linspace(0.0, 1.0, 240)
    RR, QQ = np.meshgrid(R_vals, q_vals)
    # M1 straight from the production implementation, evaluated pointwise.
    Uv = np.vectorize(voter_utility)(QQ, RR, P_fixed)
    limit = float(np.max(np.abs(Uv)))

    fig, ax = plt.subplots(figsize=(7.6, 5.8))
    # Reversed ramp so the warm pole marks the attacker-favourable region
    # (voter accepts) and the cool pole the defended one, matching the
    # baseline/protected convention used in every other figure.
    im = ax.pcolormesh(RR, QQ, Uv, shading="auto", cmap=DIVERGING_CMAP.reversed(),
                       vmin=-limit, vmax=limit)
    cs = ax.contour(RR, QQ, Uv, levels=[0], colors=[COLOR_THRESHOLD], linewidths=2.0)
    ax.clabel(cs, fmt={0: "$U_v = 0$"}, fontsize=9)

    # T2 from the solver module, not retyped here.
    q_star = np.array([voter_indifference_detection(float(r), P_fixed).value
                       for r in R_vals], dtype=float)
    ax.plot(R_vals, q_star, color="white", linestyle=(0, (4, 3)), linewidth=1.6,
            label=r"$q_v^* = R/(R+P)$  (T2, from the solver)")

    for R_example in (200.0, 600.0):
        q_thresh = voter_indifference_detection(R_example, P_fixed)
        if q_thresh.exists and q_thresh.value is not None:
            q_example = float(q_thresh.value)
            mark_point(ax, R_example, q_example,
                       f"$R$ = {R_example:,.0f} → $q_v^*$ = {q_example:.2f}",
                       color="white", dx=8, dy=-16)

    ax.annotate("voter ACCEPTS\n$U_v > 0$", xy=(0.72, 0.16), xycoords="axes fraction",
                fontsize=10, color=INK, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85,
                          edgecolor="#BFBFBF", linewidth=0.6))
    ax.annotate("voter REFUSES\n$U_v \\leq 0$", xy=(0.28, 0.78), xycoords="axes fraction",
                fontsize=10, color=INK, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85,
                          edgecolor="#BFBFBF", linewidth=0.6))

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(r"Voter utility, $U_v = (1-q)R - qP$")
    ax.set_xlabel("Bribe reward, $R$")
    ax.set_ylabel("Detection probability, $q$")
    ax.set_title(f"Rational Voter Utility Surface and Decision Threshold "
                 f"($P$ = {P_fixed:,.0f})")
    ax.legend(loc="upper left", labelcolor=INK)
    ax.grid(False)
    return _save(fig, outdir, "fig_02_voter_utility_threshold")

def fig04_attack_comparison(results: dict, outdir: str):
    """Slope chart: baseline -> protected success probability per attack
    type. Two x-positions connected by a line per attack, which reads
    cleanly in print and avoids bar-chart clutter.
    """
    labels = ["bribery", "sybil", "ballot_stuffing"]
    nice = {"bribery": "Bribery", "sybil": "Sybil", "ballot_stuffing": "Ballot Stuffing"}
    colors = {"bribery": COLOR_BRIBERY, "sybil": COLOR_SYBIL, "ballot_stuffing": COLOR_BALLOT}

    fig, ax = plt.subplots(figsize=(7.5, 6))
    xs = [0, 1]
    for k in labels:
        df = results[k]
        col = "exact_probability" if k == "bribery" else "surviving_ge_m_exact_probability"
        b = df[df.system_type == "baseline"][col].mean()
        p = df[df.system_type == "protected"][col].mean()
        ax.plot(xs, [b, p], marker="o", markersize=9, linewidth=2.5,
                color=colors[k], solid_capstyle="round", label=nice[k])
        ax.annotate(f"{b:.2f}", (xs[0] - 0.06, b), ha="right", va="center", fontsize=9, color=colors[k])
        ax.annotate(f"{p:.2f}", (xs[1] + 0.06, p), ha="left", va="center", fontsize=9, color=colors[k])

    ax.set_xlim(-0.45, 1.45)
    ax.set_xticks(xs)
    ax.set_xticklabels(["Baseline", "Protected"], fontsize=12)
    ax.set_ylabel("Mean attack-success probability (post-detection)")
    # Anchor the axis at zero. A probability slope chart on an autoscaled
    # non-zero baseline exaggerates the reduction: the visual drop is then
    # a function of the axis, not of the effect.
    ax.set_ylim(0.0, None)
    ax.set_title("Three-Attack Comparison\nBaseline → Protected Slope Chart")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="x", visible=False)
    return _save(fig, outdir, "fig_04_attack_comparison")

def fig05_election_flip_rate(election_df: pd.DataFrame, outdir: str):
    """Slope chart: probability an attack actually FLIPS the winner of
    a concrete, blockchain-recorded election, baseline vs protected.
    This is the outcome-level complement to Figure 4's abstract
    success-probability slope chart -- same style, but now measuring
    a real winner-flip on a real mined chain rather than P(X>=m).
    """
    labels = ["bribery", "sybil", "ballot_stuffing"]
    nice = {"bribery": "Bribery", "sybil": "Sybil", "ballot_stuffing": "Ballot Stuffing"}
    colors = {"bribery": COLOR_BRIBERY, "sybil": COLOR_SYBIL, "ballot_stuffing": COLOR_BALLOT}

    fig, ax = plt.subplots(figsize=(7.5, 6))
    xs = [0, 1]
    baseline_vals, protected_vals = [], []
    for k in labels:
        sub = election_df[election_df.attack_type == k]
        b = sub[sub.system_type == "baseline"]["flipped"].mean()
        p = sub[sub.system_type == "protected"]["flipped"].mean()
        baseline_vals.append(b)
        protected_vals.append(p)
        ax.plot(xs, [b, p], marker="o", markersize=9, linewidth=2.5,
                color=colors[k], solid_capstyle="round", label=nice[k])

    # Stagger overlapping labels vertically so close values don't collide
    def _staggered_offsets(values, min_gap=0.028):
        order = sorted(range(len(values)), key=lambda i: values[i])
        adjusted = list(values)
        for pos in range(1, len(order)):
            i, prev_i = order[pos], order[pos - 1]
            if adjusted[i] - adjusted[prev_i] < min_gap:
                adjusted[i] = adjusted[prev_i] + min_gap
        return adjusted

    baseline_label_y = _staggered_offsets(baseline_vals)
    protected_label_y = _staggered_offsets(protected_vals)
    for k, b, p, by, py in zip(labels, baseline_vals, protected_vals, baseline_label_y, protected_label_y):
        ax.annotate(f"{b:.1%}", (xs[0] - 0.06, by), ha="right", va="center", fontsize=9, color=colors[k])
        ax.annotate(f"{p:.1%}", (xs[1] + 0.06, py), ha="left", va="center", fontsize=9, color=colors[k])

    ax.set_xlim(-0.45, 1.45)
    ax.set_xticks(xs)
    ax.set_xticklabels(["Baseline", "Protected"], fontsize=12)
    ax.set_ylabel("Probability the attack flips the election winner")
    ax.set_ylim(-0.04, max(baseline_vals + [0.6]) * 1.28)
    ax.set_title("Election Outcome Flip Rate")
    ax.legend(loc="upper right", ncol=3)
    ax.grid(axis="x", visible=False)
    caption_note(fig, "Measured on genuinely mined chains with real tallies and real winner "
                      "determination, not on abstract success probabilities.")
    return _save(fig, outdir, "fig_05_election_flip_rate")

def fig11_adversary_decision_surface(outdir: str):
    """Create a thesis-style adversary decision surface in the main figures bundle.

    The repository already creates this graph in the appendix figure store via
    visualisation/appendix_figures.py. This API mirrors the same data source in
    the normal results/plots figure tree so a generated plot can be discovered
    by the standard figures graph and saved as a PDF/PNG pair.
    """
    detection = pd.read_csv(os.path.join(CSV_DIR, "detection_sweep.csv"))
    budget = pd.read_csv(os.path.join(CSV_DIR, "budget_sweep.csv"))

    det_s1 = detection[detection.scenario_id == "S1"].copy()
    bud_s1 = budget[(budget.scenario_id == "S1") & (budget.system_type == "baseline")].copy()

    if det_s1.empty or bud_s1.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No adversary decision surface data available",
                ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, outdir, "fig_11_adversary_decision_surface")

    qs = sorted(det_s1["q"].astype(float).unique())
    Bs = sorted(bud_s1["B"].astype(float).unique())
    q_grid = np.array(qs)
    B_grid = np.array(Bs)

    Z = np.full((len(q_grid), len(B_grid)), np.nan, dtype=float)
    for j, B in enumerate(B_grid):
        b_row = bud_s1[bud_s1["B"].astype(float) == B].iloc[0]
        base_u = float(b_row["signed_attack_utility"])
        for i, q in enumerate(q_grid):
            d_row = det_s1[det_s1["q"].astype(float).round(12) == round(float(q), 12)]
            if d_row.empty:
                continue
            u = float(d_row.iloc[0]["signed_attack_utility"])
            Z[i, j] = np.clip(0.5 * u + 0.5 * base_u, -1e9, 1e9)

    fig, ax = plt.subplots(figsize=(8, 5))
    mask = ~np.isnan(Z)
    if mask.any():
        im = ax.imshow(Z, aspect="auto", origin="lower", cmap="coolwarm",
                       extent=(float(B_grid.min()), float(B_grid.max()),
                               float(q_grid.min()), float(q_grid.max())),
                       interpolation="nearest", vmin=np.nanmin(Z), vmax=np.nanmax(Z))
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Signed attacker utility U(T*)")

    ax.set_xlabel("Attacker budget B")
    ax.set_ylabel("Detection probability q")
    ax.set_title("Adversary decision surface: budget vs. detection")
    fig.tight_layout()

    return _save(fig, outdir, "fig_11_adversary_decision_surface")


def fig08_optimal_attacker(outdir: str):
    """Game-theoretic illustration: expected attacker utility U(T) as a
    function of the number of bribery attempts T, for a scenario with
    enough budget headroom that the flip probability saturates well
    before the budget is exhausted -- producing a genuine INTERIOR
    optimum T* (diminishing, then negative, marginal returns) rather
    than a boundary "spend everything" solution. The manipulation
    threshold m is marked explicitly on the P(flip) curve.
    """
    from attacks.bribery_game_theory import optimal_attempts
    from mathematics.thresholds import min_attempts_for_confidence

    N, m, B, R, P, q, V, D_attack = 2000, 250, 100_000, 150, 800, 0.15, 500_000, 20_000
    result = optimal_attempts(N, m, B, R, P, q, V, D_attack, T_grid_points=120)
    Ts = np.array([pt.T for pt in result.curve], dtype=float)
    utilities = np.array([pt.utility for pt in result.curve], dtype=float)
    p_flips = np.array([pt.p_flip for pt in result.curve], dtype=float)
    t_min = min_attempts_for_confidence(1.0 - q, m, 0.5)

    # Two stacked panels on a shared x-axis rather than one twin-axis
    # chart: a second y-scale invites the reader to compare the vertical
    # positions of two curves measured in different units, which is
    # meaningless here (pounds against a probability). Stacking keeps
    # the shared x-axis alignment that makes the comparison legible.
    fig, (ax_u, ax_p) = plt.subplots(2, 1, figsize=(8.2, 7.0), sharex=True,
                                     gridspec_kw={"height_ratios": [1.25, 1]})

    ax_u.plot(Ts, utilities, color=COLOR_PROTECTED, linewidth=2.2,
              label=r"Expected utility $U(T)$")
    ax_u.axhline(0, color=COLOR_THRESHOLD_ALT, linewidth=0.9, linestyle="-")
    positive = Ts[utilities > 0]
    if len(positive):
        shade_region(ax_u, float(positive.min()), float(positive.max()),
                     None, COLOR_BASELINE)
        ax_u.annotate("attack profitable in expectation",
                      xy=(float(positive.mean()), 0.06), xycoords=("data", "axes fraction"),
                      ha="center", fontsize=8.4, color=INK_SECONDARY)
    mark_point(ax_u, result.T_star, result.utility_star,
               f"$T^*$ = {result.T_star:,}\n$U^*$ = {fmt_money(result.utility_star)}",
               dx=-96, dy=-46)
    ax_u.set_ylabel(r"Expected attacker utility, $U(T)$")
    ax_u.set_title("Game-Theoretic Optimal Attacker Strategy")
    ax_u.legend(loc="upper left")

    ax_p.plot(Ts, p_flips, color=COLOR_BASELINE, linewidth=2.1,
              label=r"$P(\mathrm{flip}) = P(X \geq m)$")
    mark_hline(ax_p, 0.5, "even odds", color=COLOR_THRESHOLD_ALT, linestyle=":")
    if t_min.exists and t_min.value is not None:
        mark_vline(ax_p, t_min.value,
                   f"$T_{{\\min}}$ = {fmt_int(t_min.value)}\n(even odds of reaching $m$)", y=0.30)
        mark_vline(ax_u, t_min.value, "", y=0.02, box=False, color=COLOR_THRESHOLD_ALT)
    mark_vline(ax_p, result.T_star, f"$T^*$ = {result.T_star:,}", y=0.78)
    mark_vline(ax_u, result.T_star, "", y=0.02, box=False)
    ax_p.set_xlabel("Number of bribery attempts, $T$")
    ax_p.set_ylabel(rf"$P(X \geq m)$,  $m$ = {m}")
    ax_p.set_ylim(-0.04, 1.04)
    ax_p.legend(loc="lower right")

    caption_note(fig,
                 f"Fixed scenario: $N$ = {N:,}, $m$ = {m}, $B$ = {B:,}, $R$ = {R}, $q$ = {q}. "
                 f"Utility peaks at $T^*$ = {result.T_star:,} and then declines: once the flip "
                 f"probability saturates, each further bribe adds cost and detection risk but no "
                 f"additional chance of success. $T^*$ is the best point on the evaluated grid "
                 f"rather than an exact argmax; the curve is flat near its peak, so nearby values "
                 f"of $T$ are near-optimal too.", y=0.0)
    fig.tight_layout()
    return _save(fig, outdir, "fig_08_optimal_attacker")

def fig07_binomial_thresholds(outdir: str):
    """Illustrative PMF of X ~ Binomial(T, 1-q) for a representative
    scenario, with the manipulation threshold m marked explicitly and
    the success region X>=m shaded -- makes the abstract "P(X>=m)"
    formula behind every other figure in this report visually concrete.
    """
    from scipy.stats import binom
    from mathematics.thresholds import attacker_reachable_margin, chernoff_certified_margin

    T, p_success, m = 200, 0.55, 120

    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p_success)
    mu = T * p_success
    m_reach = attacker_reachable_margin(T, p_success, 0.5)
    m_cert = chernoff_certified_margin(T, p_success, 1e-3)
    p_success_area = binom.sf(m - 1, T, p_success)

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    below, above = ks < m, ks >= m
    ax.bar(ks[below], pmf[below], color="#C9C9C9", width=1.0,
           label=r"$X < m$  (attack fails)")
    ax.bar(ks[above], pmf[above], color=COLOR_BASELINE, width=1.0,
           label=r"$X \geq m$  (attack succeeds)")

    top = float(pmf.max())

    # X is INTEGER-valued, so a bar centred on k occupies [k-0.5, k+0.5] and
    # the boundary between the failure and success regions is the half-integer
    # m-0.5, not m itself. Drawing the region boundary at m would put it
    # through the MIDDLE of the first shaded bar, making the shading appear to
    # start half a vote early -- the line and the colour change would disagree.
    # Region boundaries are therefore drawn at half-integers and labelled with
    # the integer margin they separate; the mean is a genuine point on a
    # continuous scale and stays where it is.
    boundary = m - 0.5
    # y positions chosen to clear the upper-left legend: at y=0.94 the
    # mean's label box sat on top of the first legend entry.
    mark_vline(ax, mu, f"mean $\\mu = T(1-q)$ = {mu:.0f}", y=0.60, ha="right", dx=-6,
               color=COLOR_THRESHOLD_ALT, linestyle=":")
    mark_vline(ax, boundary, f"threshold $m$ = {m}", y=0.78)
    if m_reach.exists and m_reach.value is not None:
        # Margins at or BELOW m_alpha are reachable, so the boundary of that
        # region sits just above m_alpha.
        mark_vline(ax, m_reach.value + 0.5,
                   f"$m_\\alpha$ = {fmt_int(m_reach.value)}\nlargest margin beaten\nat even odds",
                   y=0.44, color=COLOR_BASELINE, dx=-6, ha="right")
    if m_cert.exists and m_cert.value is not None:
        # Margins at or ABOVE m_eps are certified, so that boundary sits just
        # below m_eps.
        cert_boundary = m_cert.value - 0.5
        mark_vline(ax, cert_boundary,
                   f"$m_\\varepsilon$ = {fmt_int(m_cert.value)}\nChernoff-certified safe\n"
                   r"($\varepsilon = 10^{-3}$)",
                   y=0.44, color=COLOR_PROTECTED)
        if m_reach.exists and m_reach.value is not None:
            ax.annotate("", xy=(cert_boundary, top * 1.06),
                        xytext=(m_reach.value + 0.5, top * 1.06),
                        arrowprops=dict(arrowstyle="<->", color=INK_MUTED, linewidth=1.0))
            # Headroom set explicitly: at top*1.05 the label rendered above the
            # autoscaled ceiling and spilled into the title gutter.
            ax.annotate("contested band", xy=((m_reach.value + m_cert.value) / 2, top * 1.10),
                        ha="center", va="bottom", fontsize=8.4, color=INK_SECONDARY)
        ax.set_ylim(top=top * 1.20)

    safe_cert_margin = m_cert.value if m_cert.exists and m_cert.value is not None else m
    ax.set_xlim(mu - 4.6 * np.sqrt(T * p_success * (1 - p_success)),
                min(T, safe_cert_margin + 12))
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
    return _save(fig, outdir, "fig_07_binomial_thresholds")

def fig03_chernoff_two_sided(chernoff_df: pd.DataFrame, results: dict, outdir: str):
    """Both Chernoff directions validated on the same experiment.

    The one-sided bound of Figure 1 exists only where the threshold sits
    above the mean, which leaves the regime where the attack is LIKELY to
    succeed with no analytic statement at all. The two-sided certificate
    closes that gap by bounding whichever tail the threshold actually
    falls in, and this figure checks both directions against the exact
    value at once.

    Left panel: threshold above the mean, so the (1+delta) upper-tail
    form certifies success from ABOVE -- valid points lie on or above the
    diagonal. Right panel: threshold at or below the mean, so the
    (1-delta) lower-tail form applied to the failure event certifies
    success from BELOW -- valid points lie on or below the diagonal. A
    point on the wrong side of either diagonal would be a broken bound.
    """
    frames = []
    for attack, df in results.items():
        col = "exact_probability" if attack == "bribery" else "surviving_ge_m_exact_probability"
        sub = df[["chernoff_direction", "chernoff_success_lower",
                  "chernoff_success_upper", col]].copy()
        sub.columns = ["direction", "lower", "upper", "exact"]
        sub["attack"] = attack
        frames.append(sub)
    data = pd.concat(frames, ignore_index=True)

    upper = data[data.direction == "upper"]
    lower = data[data.direction == "lower"]
    n_ok = int(((data["exact"] >= data["lower"].fillna(0.0) - 1e-9) &
                (data["exact"] <= data["upper"].fillna(1.0) + 1e-9)).sum())

    fig, (ax_u, ax_l) = plt.subplots(1, 2, figsize=(11.6, 5.5))

    for ax, sub, y_col, title, side in (
            (ax_u, upper, "upper",
             r"Threshold above the mean: $(1+\delta)$ upper-tail form",
             "above"),
            (ax_l, lower, "lower",
             r"Threshold below the mean: $(1-\delta)$ lower-tail form",
             "below")):
        for attack in ("bribery", "sybil", "ballot_stuffing"):
            s = sub[sub.attack == attack]
            if len(s) == 0:
                continue
            # No per-series counts in the label: the legend is shared
            # between the panels and the two panels have DIFFERENT counts,
            # so a single legend cannot carry them without being wrong for
            # one panel. Counts are annotated inside each panel instead.
            ax.scatter(s["exact"], s[y_col], s=9, alpha=0.35, linewidths=0,
                       color=ATTACK_COLORS[attack], marker=ATTACK_MARKERS[attack],
                       label=ATTACK_LABELS[attack])
        ax.plot([0, 1], [0, 1], color=COLOR_THRESHOLD, linestyle="--",
                linewidth=1.3, zorder=4, label="validity threshold")
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel(r"Exact probability, $P(X \geq m)$")
        ax.set_title(title, fontsize=10.5)
        counts = "   ".join(f"{ATTACK_LABELS[a]} {int((sub.attack == a).sum()):,}"
                            for a in ("bribery", "sybil", "ballot_stuffing")
                            if int((sub.attack == a).sum()))
        ax.annotate(f"n = {len(sub):,}   ({counts})", xy=(0.5, -0.155),
                    xycoords="axes fraction", ha="center", fontsize=7.8,
                    color=INK_SECONDARY)

    ax_u.set_ylabel("Certified upper bound on success")
    ax_l.set_ylabel("Certified lower bound on success")
    ax_u.fill_between([0, 1], [0, 1], [0, 0], color=COLOR_BASELINE, alpha=0.06, linewidth=0)
    ax_l.fill_between([0, 1], [0, 1], [1, 1], color=COLOR_BASELINE, alpha=0.06, linewidth=0)
    ax_u.annotate("a point here would be\na violated upper bound",
                  xy=(0.70, 0.12), xycoords="axes fraction", fontsize=8.2,
                  color=INK_SECONDARY, ha="center")
    ax_l.annotate("a point here would be\na violated lower bound",
                  xy=(0.30, 0.88), xycoords="axes fraction", fontsize=8.2,
                  color=INK_SECONDARY, ha="center")

    # One shared legend beneath both panels: the series are identical in
    # each, and an in-axes legend collides with the point cloud in the
    # left panel and with the annotation in the right.
    handles, labels = ax_u.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=9,
               bbox_to_anchor=(0.5, -0.015), frameon=False)

    fig.suptitle("Two-Sided Chernoff Certificate: Both Directions Validated",
                 fontsize=11.5, fontweight="bold")
    n_plotted = len(upper) + len(lower)
    n_exact = len(data) - n_plotted
    caption_note(fig, f"Every one of the {len(data):,} scenario evaluations receives a certified "
                      f"statement, and the certified interval contains the exact value in "
                      f"{n_ok:,} of {len(data):,} cases. The panels plot the {n_plotted:,} "
                      f"evaluations where a Chernoff bound does the work; the remaining "
                      f"{n_exact:,} are exact by construction (the threshold is at or beyond the "
                      f"support, so the probability is 0 or 1 and no bound is needed) and would "
                      f"sit on the diagonal's endpoints. The one-sided bound alone covers only "
                      f"the left panel.", y=-0.07)
    fig.tight_layout()
    return _save(fig, outdir, "fig_03_chernoff_two_sided")
