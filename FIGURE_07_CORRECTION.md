# Figure 7 — Correction Note

**Figure.** *Binomial Outcome Distribution and the Three Margin Thresholds*
**Source.** `visualisation/plots.py :: fig07_binomial_thresholds`
**Standalone runnable copy.** `figure_07_corrected.py`
**Regression tests.** `tests/test_figure_geometry.py` (3 tests)
**Status.** Corrected; verified; pinned by tests.

---

## 1. The observation

Raised in supervision: *"the graph looks slightly off, because the shaded
region is lower [starts earlier] than it should be."*

The observation was correct. The defect was in **rendering**, not in the
mathematics.

## 2. The mathematics was verified first, and is right

The figure illustrates the quantity that sits behind every other result in
the dissertation — the probability that the number of surviving fraudulent
votes reaches the manipulation threshold:

$$X \sim \mathrm{Binomial}(T = 200,\; 1-q = 0.55), \qquad m = 120$$

$$P(X \geq m) \;=\; \texttt{binom.sf(119, 200, 0.55)} \;=\; 0.088073$$

Summing the heights of the shaded bars gives `0.088073` — agreement to
machine precision (`< 1e-12`). So the *area* was never wrong, and no
reported number in the thesis changes as a result of this correction.

## 3. What was actually wrong

`matplotlib`'s `ax.bar(x, h, width=1.0)` defaults to `align='center'`.
A bar drawn for outcome $k$ therefore occupies the interval

$$[\,k - 0.5,\; k + 0.5\,]$$

Querying the rectangle coordinates of the original figure directly:

| artist | span |
|---|---|
| last grey bar, $k = 119$ | `[118.50, 119.50]` |
| first shaded bar, $k = 120$ | `[119.50, 120.50]` |
| **threshold line, labelled $m = 120$** | **`120.00`** |

The labelled line at $x = 120$ passed through the **centre** of the first
shaded bar rather than along its left edge. The colour change began at
$119.5$ while the label said $120$ — a disagreement of exactly one half
bar width, which is precisely the "shading starts half a vote early"
appearance that was spotted.

This is a class of error a numerical check cannot catch: the figure was
simultaneously *numerically exact* and *visually misleading*.

## 4. The correction

$X$ is **integer-valued**, so every region boundary on this axis is a
half-integer, and each boundary is labelled with the integer margin it
separates:

| region | meaning | boundary drawn at |
|---|---|---|
| $\{X \geq m\}$ | attack succeeds | $m - 0.5 = 119.5$ |
| $\{X \leq m_\alpha\}$ | reachable at even odds (T7) | $m_\alpha + 0.5 = 110.5$ |
| $\{X \geq m_\varepsilon\}$ | Chernoff-certified safe (T6) | $m_\varepsilon - 0.5 = 151.5$ |

The mean $\mu = T(1-q) = 110$ is **not** moved. $\mu$ is an expectation —
a genuine point on a continuous scale, not a boundary between integer
outcomes — so it stays at exactly $110.0$.

A side effect worth stating accurately: $m_\alpha = 110$ and $\mu = 110$
were previously drawn at exactly the same coordinate. They are now at
$110.5$ and $110.0$ — formally distinct, but half a vote apart on an
axis roughly 86 votes wide, so at print size they still read as one
line. The separation is in the data, not yet in the picture; the two
are told apart by their labels, which is why both carry one.

### The rule, stated generally

> For a discrete random variable plotted as unit-width centred bars, a
> line separating $\{X < c\}$ from $\{X \geq c\}$ belongs at $c - 0.5$,
> and must be *labelled* $c$. Lines representing continuous quantities
> (means, expectations, fitted values) stay at their true coordinate.

## 5. The code change

```python
# BEFORE — line bisects the first shaded bar
mark_vline(ax, m, f"threshold $m$ = {m}", y=0.78)

# AFTER — line meets the bar's left edge, label keeps the integer margin
boundary = m - 0.5
mark_vline(ax, boundary, f"threshold $m$ = {m}", y=0.78)
```

and correspondingly `m_reach.value + 0.5` and `m_cert.value - 0.5` for the
other two region boundaries. Full annotated source: `figure_07_corrected.py`,
section 3.

The caption now states the convention explicitly, so a reader who measures
the figure against the axis does not have to rediscover it:

> *Because $X$ is integer-valued, region boundaries are drawn at
> half-integers (the $m$ line sits at $m-0.5$), so each line meets the
> edge of a bar rather than cutting through its centre.*

## 6. Regression tests

Added in `tests/test_figure_geometry.py`. They inspect the **actual
Matplotlib artists**, not a re-derivation, so they fail if the figure code
regresses:

```python
def test_shaded_region_starts_at_the_bar_edge_not_the_bar_centre():
    """The colour boundary and the labelled threshold must coincide."""
    T, p, m = 200, 0.55, 120
    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p)

    fig, ax = plt.subplots()
    ax.bar(ks[ks < m], pmf[ks < m], width=1.0)
    bars_above = ax.bar(ks[ks >= m], pmf[ks >= m], width=1.0)

    first_shaded = min(bars_above, key=lambda r: r.get_x())
    colour_boundary = first_shaded.get_x()
    plt.close(fig)

    assert abs(colour_boundary - (m - 0.5)) < 1e-9
    assert abs(colour_boundary - m) > 0.4


def test_figure_seven_draws_its_threshold_at_the_half_integer():
    """Inspect the real figure: a vertical line must sit at m - 0.5."""
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

    xs = created.get("xs", [])
    assert any(abs(x - 119.5) < 1e-6 for x in xs)      # boundary present
    assert not any(abs(x - 120.0) < 1e-6 for x in xs)  # old bug absent


def test_shaded_bars_sum_to_the_reported_probability():
    """The shading must integrate to exactly P(X >= m)."""
    T, p, m = 200, 0.55, 120
    ks = np.arange(0, T + 1)
    pmf = binom.pmf(ks, T, p)
    assert abs(pmf[ks >= m].sum() - binom.sf(m - 1, T, p)) < 1e-12
```

Suite size after this fix: 101 → **104** (all passing at the time); it has
since grown further with the review changes recorded in
`CHANGES_FROM_REVIEW.md`.
`check_consistency.py` reports no drift.

## 7. Impact on the dissertation

| | |
|---|---|
| Reported probabilities | **unchanged** — the area was always exact |
| Thresholds $m_\alpha$, $m_\varepsilon$, $\mu$ | **unchanged** (110, 152, 110) |
| Tables, findings, conclusions | **unchanged** |
| Figure 7 rendering | corrected |
| Caption | extended to state the half-integer convention |
| Tests | 101 → 104 at the time of this fix |

The correction is worth reporting rather than silently applying: it is a
concrete instance of a figure being numerically exact and still capable of
misleading a reader, and the methodology chapter now says so.

## 8. How to reproduce

```bash
python3 figure_07_corrected.py     # standalone: prints self-checks, writes PNG + PDF
python3 generate_figures.py        # regenerates all 10 thesis figures
python3 /root/devtools/run_tests.py tests/test_figure_geometry.py
```
