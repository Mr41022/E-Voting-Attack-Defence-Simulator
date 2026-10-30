"""
visualisation/style.py

One visual system for every figure in the thesis: palette, typography,
mark specification, and the threshold-annotation helpers.

COLOUR PALETTE -- VALIDATED, NOT EYEBALLED
------------------------------------------
The categorical palette below was checked programmatically for
colour-vision-deficiency separation rather than chosen by eye. Running

    node validate_palette.js "#D55E00,#009E73,#882E72,#0072B2,#B07A00"

reports PASS on all six checks: lightness band, chroma floor, adjacent
CVD separation (worst adjacent pair dE 10.5 under deuteranopia, 19.9
under tritanopia), normal-vision separation (worst adjacent dE 21.8),
and contrast against the page (all five at or above 3:1). Four of the
five hues are Okabe-Ito; ballot stuffing uses Paul Tol's muted purple
(#882E72) in place of Okabe-Ito's reddish purple (#CC79A7), which sat
in the marginal 6-8 dE band against the Sybil green under deuteranopia.

Colour is never the only channel. Every attack type also carries its
own marker shape, and every multi-series figure is either directly
labelled or has a legend, so the figures survive greyscale printing --
the normal fate of a submitted thesis.

TYPOGRAPHY
----------
Serif text with STIX mathematics, so figure labels sit visually with
the Times-set body text of the report rather than looking like output
pasted in from a different document.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# --- categorical palette (validated; see module docstring) ------------
COLOR_BASELINE = "#D55E00"      # vermillion  -- unprotected configuration
COLOR_PROTECTED = "#0072B2"     # blue        -- protected configuration
COLOR_BRIBERY = "#D55E00"       # vermillion
COLOR_SYBIL = "#009E73"         # bluish green
COLOR_BALLOT = "#882E72"        # muted purple
COLOR_COALITION = "#333333"     # near-black  -- combined multi-vector attack
COLOR_EXACT = "#1A1A1A"         # exact analytic curve
COLOR_MC = "#B07A00"            # Monte Carlo markers
COLOR_CHERNOFF = "#0072B2"      # Chernoff bound (always dashed)

# --- neutral ink (text never wears a series colour) -------------------
INK = "#1A1A1A"
INK_SECONDARY = "#4D4D4D"
INK_MUTED = "#767676"
GRID = "#D9D9D9"
SURFACE = "#FFFFFF"

# --- threshold semantics ----------------------------------------------
# Thresholds are a distinct visual class: charcoal, dashed, thin, always
# labelled with their numeric value. They are annotations on the data,
# never a data series, so they never take a categorical hue.
COLOR_THRESHOLD = "#1A1A1A"
COLOR_THRESHOLD_ALT = "#767676"

ATTACK_COLORS = {
    "bribery": COLOR_BRIBERY,
    "sybil": COLOR_SYBIL,
    "ballot_stuffing": COLOR_BALLOT,
    "coalition": COLOR_COALITION,
}

# Secondary encoding: shape carries identity when colour cannot.
ATTACK_MARKERS = {
    "bribery": "o",
    "sybil": "s",
    "ballot_stuffing": "^",
    "coalition": "D",
}

ATTACK_LABELS = {
    "bribery": "Bribery",
    "sybil": "Sybil",
    "ballot_stuffing": "Ballot stuffing",
    "coalition": "Coalition",
}

SYSTEM_COLORS = {"baseline": COLOR_BASELINE, "protected": COLOR_PROTECTED}
SYSTEM_MARKERS = {"baseline": "o", "protected": "s"}
SYSTEM_LABELS = {"baseline": "Baseline", "protected": "Protected"}

# Sequential ramp: one hue, light to dark (never a rainbow).
SEQUENTIAL_CMAP = LinearSegmentedColormap.from_list(
    "thesis_sequential", ["#EAF2F8", "#9CC6E0", "#4B93C4", "#0072B2", "#00436A"])

# Diverging ramp: two hues with a NEUTRAL GREY midpoint, so the zero
# contour stays visible against a white page (a white midpoint would
# disappear into the paper exactly where the decision boundary is).
DIVERGING_CMAP = LinearSegmentedColormap.from_list(
    "thesis_diverging",
    ["#7A3200", "#D55E00", "#F0B183", "#DDDDDD", "#7FB8DB", "#0072B2", "#003F63"])


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
        "grid.alpha": 0.9,
        "xtick.color": INK_SECONDARY,
        "ytick.color": INK_SECONDARY,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.fontsize": 9.5,
        "legend.frameon": False,
        "legend.labelcolor": INK,
        "legend.handlelength": 2.2,
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
        "lines.solid_capstyle": "round",
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 320,
        "savefig.bbox": "tight",
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "pdf.fonttype": 42,     # embed TrueType, so the PDF stays editable/searchable
        "ps.fonttype": 42,
    })


# ---------------------------------------------------------------------
# Threshold annotation helpers
# ---------------------------------------------------------------------

_THRESHOLD_BOX = dict(boxstyle="round,pad=0.28", facecolor="white",
                      edgecolor="#BFBFBF", linewidth=0.6, alpha=0.94)


def mark_vline(ax, x: float, label: str, *, y: float = 0.94, color: str = COLOR_THRESHOLD,
               linestyle: str = "--", rotation: int = 0, ha: str = "left",
               dx: int = 6, fontsize: float = 8.6, linewidth: float = 1.1,
               box: bool = True):
    """Draw a labelled vertical threshold line at x.

    The label carries the threshold's numeric value, because a line
    without its value tells the reader that something changes there but
    not what to compare against.
    """
    if x is None or not _finite(x):
        return None
    ax.axvline(x, color=color, linestyle=linestyle, linewidth=linewidth, zorder=2.5)
    ax.annotate(label, xy=(x, y), xycoords=("data", "axes fraction"),
                xytext=(dx, 0), textcoords="offset points",
                ha=ha, va="center", fontsize=fontsize, color=INK,
                rotation=rotation, zorder=6,
                bbox=_THRESHOLD_BOX if box else None)
    return x


def mark_hline(ax, y: float, label: str, *, x: float = 0.02, color: str = COLOR_THRESHOLD,
               linestyle: str = "--", ha: str = "left", dy: int = 6,
               fontsize: float = 8.6, linewidth: float = 1.1, box: bool = True):
    """Draw a labelled horizontal threshold line at y."""
    if y is None or not _finite(y):
        return None
    ax.axhline(y, color=color, linestyle=linestyle, linewidth=linewidth, zorder=2.5)
    ax.annotate(label, xy=(x, y), xycoords=("axes fraction", "data"),
                xytext=(0, dy), textcoords="offset points",
                ha=ha, va="bottom", fontsize=fontsize, color=INK, zorder=6,
                bbox=_THRESHOLD_BOX if box else None)
    return y


def mark_point(ax, x: float, y: float, label: str, *, color: str = COLOR_THRESHOLD,
               dx: int = 10, dy: int = 10, fontsize: float = 8.6, size: float = 46):
    """Mark and label a single distinguished point (an optimum, a crossing)."""
    if not (_finite(x) and _finite(y)):
        return
    ax.scatter([x], [y], s=size, color=color, zorder=7, edgecolor="white", linewidth=1.1)
    ax.annotate(label, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                fontsize=fontsize, color=INK, zorder=7, bbox=_THRESHOLD_BOX)


def shade_region(ax, x0: float, x1: float, label: str | None = None,
                 color: str = "#D55E00", alpha: float = 0.07):
    """Shade a parameter region (e.g. 'attack is profitable here')."""
    ax.axvspan(x0, x1, color=color, alpha=alpha, zorder=0, linewidth=0)
    if label:
        ax.annotate(label, xy=((x0 + x1) / 2, 0.045), xycoords=("data", "axes fraction"),
                    ha="center", va="bottom", fontsize=8.4, color=INK_SECONDARY, zorder=6)


def ci_band(ax, x, lo, hi, color: str, alpha: float = 0.16):
    """95% confidence ribbon behind a mean curve."""
    ax.fill_between(x, lo, hi, color=color, alpha=alpha, linewidth=0, zorder=1.5)


def caption_note(fig, text: str, y: float = -0.02, fontsize: float = 8.4):
    """A small note under the axes, for a caveat that belongs on the
    figure itself rather than in the surrounding prose."""
    fig.text(0.5, y, text, ha="center", va="top", fontsize=fontsize,
             color=INK_MUTED, wrap=True)


def _finite(v) -> bool:
    try:
        return v is not None and float(v) == float(v) and abs(float(v)) != float("inf")
    except (TypeError, ValueError):
        return False


def fmt_int(v) -> str:
    """Thousands-separated integer for annotation text."""
    try:
        return f"{int(round(float(v))):,}"
    except (TypeError, ValueError):
        return "n/a"


def fmt_money(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "n/a"
    for cut, suffix in ((1e9, "bn"), (1e6, "m"), (1e3, "k")):
        if abs(v) >= cut:
            return f"{v / cut:,.2f}{suffix}".replace(".00", "")
    return f"{v:,.0f}"
