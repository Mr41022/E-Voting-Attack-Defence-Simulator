# Changes made in response to review

Two rounds. **Round 1** addressed the three issues raised directly. **Round 2**
was a full adversarial audit of every number, claim and figure in the project,
which found further defects of the same *class* as the one reported — correct
arithmetic described wrongly — and fixed those too.

**Status:** 119 tests passing (was 104) · `check_consistency.py` clean ·
thesis 56 pages · compendium 24 pages · both compile with zero LaTeX errors and
no undefined references.

---

# Round 1 — the three reported issues

## 🔴 1. The Sybil / ballot-stuffing mismatch — diagnosed, not a bug

Sybil and ballot stuffing pass each fraudulent vote through **two independent
gates**; bribery through one.

```
accepted   A ~ Binomial(n, q_accept)                  <- acceptance gate only
surviving  W ~ Binomial(n, q_accept * (1 - p_detect)) <- BOTH gates
```

so `P(W >= m) <= P(A >= m)` always. Tables 3/4 reported the first under a bare
heading `mean`; Tables 7–9 and Figure 4 reported the second. Bribery agreed
because detection is folded into its `1 − q`, which is exactly why only the
other two looked inconsistent.

| file | change |
|---|---|
| `generate_tables.py` | Tables 3/4 report **both** measures with explicit `measure` + `measure_definition` columns; Table 5 filters to the headline measure, so it now matches Tables 7–9 exactly |
| `generate_report.py` | Four injected macros for the acceptance-only figures |
| `report/sections/findings.tex` | New subsection *"Which probability is being reported"* |
| `build_compendium.py` | Titles name the statistic; boxed note opens Part II |
| `MATHEMATICAL_MODEL.md` | Addendum deriving both measures |
| `tests/test_reporting_consistency.py` *(new, 5 tests)* | Table 5 must agree with Tables 7/8/9 to 4 dp; `accepted >= surviving` always |

Both measures are kept, because the gap between them separates the share of the
countermeasure effect coming from tightened registration from the share coming
from detection — different mechanisms, different costs.

## 🟠 2. Overclaiming

F3 now names the residuals (0.1356 Sybil, 0.1162 ballot stuffing) and says
"substantially reduced… not eliminated". The abstract's "as completely as" and
Figure 10's caption are scoped to the benchmark scenarios.

## 🟡 3. Detection levels are assumptions

Figure 6's note now says the protected operating point is a deliberately
generous margin, not a level the analysis finds necessary. Figure 10's note
positions coalitions as an extension.

---

# Round 2 — what the full audit found

## 🔴 4. Capacity was a mean, described as a ceiling

**The most serious defect found, and the same class as the reported one.**

`capacity = n_feasible × p_survive / m` is **E[X]/m** — a mean. The figure
docstring, its caption, the capacity table note and three passages of prose all
said a bar below 1.0 meant the vector *"cannot reach the threshold at any
budget"*. That is false, and the report's own tables refuted it: S1 bribery has
capacity **0.97** and an exact success probability of **0.423**.

The zeros in `table_12` are the *utility optimiser* declining (`n* = 0`) — a
different statement from arithmetic impossibility, reported under one word.

| file | change |
|---|---|
| `visualisation/threshold_plots.py` | Figure 9 rewritten: bars relabelled *expected* capacity, each annotated with the exact `P(X ≥ m)` at full effort |
| `generate_report.py` | Capacity table note rewritten; two new macros for the quoted probabilities |
| `report/sections/findings.tex` | The claim is now that no single vector is a *reliable* route, with the probabilities that make it hold |
| `generate_figures.py` | Caption computes the honest quantities |

## 🔴 5. Figure 9's "all three combined" marker was budget-infeasible

It summed each vector's full independent capacity — funding all three at once,
which **exceeds the budget in four of the five scenarios**. It now plots the
optimal coalition's `mu_total / m` from the coalition search, which is
budget-feasible and clears the threshold in 4 of 5.

## 🔴 6. Arithmetic that could not be true

- *"the inequality fails in 12 of 15 cases"* — 3 deltas × 4 settings is **12**
  cases, and **11** fail. Corrected (the quoted counter-example was right).
- *"combined capacity exceeds it in four of five"* — the printed table showed
  **five of five**. The corrected coalition quantity is genuinely 4 of 5.
- *"evaluating vectors independently found no attack where a decisive one
  existed"* — bribery alone was viable in 4 of 5 scenarios at up to 0.423. Now:
  *"the difference between a one-in-three chance and a near-certainty"*.

## 🟠 7. Claims contradicted by the data

| claim | reality | fix |
|---|---|---|
| "the ordering matches" across layers | analytic puts Sybil above ballot stuffing; the mined-chain layer reverses them (0.33 pp, inside sampling error) | states agreement in magnitude and effect size, and that the top two are indistinguishable |
| "success falls as the electorate grows" | true for bribery and ballot stuffing; **Sybil rises** (corr +0.91) | distinguishes budget-bound from proportionally-capped vectors — a better result than the original |
| "the interior of the simplex dominates its corners" | interior in 1 of 5, edge in 3, corner in 1 | *"mixing at least two vectors"* |
| "every defended threshold sits inside or just above its band" | S5 exceeds `m_α` by ~7× | scoped to four of five, and notes `m_ε` exists for one scenario only |
| detection range "0.072 to 0.118" | the true binding range is **0.050 to 0.118** | uses the min/max macros with the binding qualifier |
| "an order of magnitude below" | 4.7× against the strongest requirement | *"between four and eleven times"* |
| "residual risk concentrates in identity verification" | Sybil 0.136 vs ballot stuffing 0.116 — a near-tie | names both |

## 🟠 8. An unsupported empirical claim

The findings quoted a Monte Carlo convergence sweep. `convergence_curve()`
existed but **was never called** — there was no CSV, no JSON key, no figure.
Rather than delete the sentence, the sweep is now run: `run_experiments.py`
writes `results/csv/monte_carlo_convergence.csv`, and the prose quotes injected
macros. The settling point is reported against a fixed tolerance rather than a
2-SE envelope, because a 95% envelope produces expected excursions that would
make the figure jump with the seed.

## 🟠 9. Documentation contradicted by the code

- `ASSUMPTIONS.md` and `MATHEMATICAL_MODEL.md` said M8 "is not applied to the
  X≥m success condition". True before the two-sided certificate; the certificate
  applies M8 to the **complementary failure event**, which is valid and is what
  fills 3,956 of 15,000 rows. Both files now state this precisely.
- `ASSUMPTIONS.md` claimed *"the figures print 'does not exist' rather than
  drawing a line"*. No figure emits that — `mark_vline` returns silently. Now
  stated accurately.
- `MATHEMATICAL_MODEL.md` claimed the reported `n*` is exact to one attempt.
  True of `optimal_effort`; the function behind Figure 8 uses a 120-point grid
  with no refinement. Both are now described separately, and Figure 8's caption
  says `T*` is the best grid point.

## 🟠 10. Figure defects

| figure | defect | fix |
|---|---|---|
| 1 | `q_v* = 0.10` put the entire method comparison inside the region the figure shades as *"bribe not incentive-compatible"* | reparameterised (R = 2,000, P = 900, B scaled so `T` is unchanged) so `q_v* = 0.69` sits right of the collapse at 0.55 |
| 2 | described as "visual proof" of the solver while evaluating both expressions inline — it touched neither module and could not fail | now calls `voter_utility` (M1) and `voter_indifference_detection` (T2); prose says it checks the code, not the mathematics |
| 3 | the shared legend's `n = …` counts were the left panel's, shown under both | per-panel counts; caption states 7,947 plotted vs 7,053 exact by construction |
| 6 | the labelled `q_d*` line missed the plotted crossing by ~0.012 (60-point sweep); a `−2.15e6` sentinel was plotted as a utility | sweep raised to 400 points (crossing now 0.0726 vs solver 0.0722); sentinel flagged in the CSV and masked, with the region shaded |
| 7 | mean label collided with the legend; "contested band" text sat outside the axes | labels repositioned, headroom set explicitly |
| 9 | eleven "declined" annotations anchored at `y=0` were invisible on a log axis; `0.997` printed as `1.00` | annotations replaced by the `P` labels; 3 dp near 1.0 |
| 10 | baseline and protected rows joined **positionally** after separate `reset_index` calls | joined on `scenario_id` |
| 4 | probability axis autoscaled off zero, exaggerating the reduction | anchored at 0 |

## 🟡 11. Missing content

- **T1 was never defined.** The report claimed seven threshold solvers but
  formulated six; `R* = qP/(1−q)` is now stated as Equation (T1). Table 7 was
  also missing T1 and T3 despite the text saying it collected every threshold —
  both columns added.
- **The parameter table listed 13 of 17 config entries**, omitting all four
  protected-configuration parameters for Sybil and ballot stuffing while showing
  the bribery equivalent. All 17 now listed.

## 🟡 12. Two overclaims of my own, corrected

- *"none is typed by hand"* — configuration values, worked-example arithmetic
  and the analytic counter-examples are typed. Now scoped to experimental
  results, with the exceptions named.
- `FIGURE_07_CORRECTION.md` said `m_α` and `μ` are *"now legible as two distinct
  annotations"*. They are 0.5 apart on an 86-unit axis and still read as one
  line at print size. Now says so.

## 🟢 13. The consistency checker was not doing what it said

`check_consistency.py` advertised a check that stale figure ranges like
`"Figures 22-29"` are caught. The implementation only fired when a range started
at 1, so the stale header sitting in `visualisation/threshold_plots.py` passed
silently. Now any endpoint outside `1..N` fails, and `PROSE_FILES` scans the
Python sources and side documents too. **On its first run after the fix it
immediately caught both stale strings** — that header and a stale test count in
`FIGURE_07_CORRECTION.md`.

## New tests — `tests/test_claim_integrity.py` (10 tests)

These pin *claims*, not computations, because every defect above would pass a
numerical test. Each names the sentence it protects. All ten were
negative-controlled: reintroducing the original defect makes them fail.

- capacity below 1.0 must have a positive success probability somewhere
  (so "cannot reach at any budget" can never be reinstated truthfully)
- no single vector's *expected* capacity may reach the threshold
- the naive capacity sum must overstate the achievable coalition
- the coalition must clear the threshold in exactly the number of scenarios
  claimed
- the optimum must not be generally interior
- the plotted detection curve must cross zero within one grid step of `q_d*`
- the sentinel must stay flagged
- electorate growth must not help every vector uniformly
- Figure 1's `q_v*` must exceed its collapse point
- the wrong-signed Chernoff form must fail in exactly 11 of 12 cases

## Verification

```
python3 /root/devtools/run_tests.py   ->  119 passed, 0 failed
python3 check_consistency.py          ->  No inconsistencies found
report/thesis_report.pdf              ->  56 pages, 0 errors, 0 undefined refs
report/results_compendium.pdf         ->  24 pages, 0 errors
```
