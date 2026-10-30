# Game-Theoretic Bribery Attack & Named Scenarios Report

This report documents two additions to the core simulation:
(1) a **game-theoretic optimal-attacker layer** on top of the bribery
model, which searches over the number of bribery attempts `T` for the
utility-maximizing choice rather than evaluating a single fixed `T`;
and (2) five **named, fixed benchmark scenarios** (as opposed to the
2,500 randomised paired trials in `EXPERIMENTAL_REPORT.md`) chosen to
be individually quotable worked examples at different electorate
scales.

All numbers below come from `simulation/named_scenarios.py` (executed
automatically by `generate_figures.py`) and are saved in
`results/csv/named_scenarios_results.csv`.

---

## Notation reconciliation

An earlier version of this model (and some standard textbook
presentations of bribery-attack probability) label the per-attempt
success probability directly as `q` (i.e. `X~Binomial(T,q)`), with
`T=floor(B/c)`. This project's convention throughout
(`mathematics/utility.py`, `attacks/bribery.py`, `MATHEMATICAL_MODEL.md`)
instead uses `q` = **detection** probability, so success probability
is `1-q` (`X~Binomial(T,1-q)`), and `T=min(N,floor(B/R))` additionally
caps attempts at the electorate size `N`. The two formulations are
identical under the substitution `q_alt = 1 - q_here`; this project
keeps the detection-probability convention because it composes
directly with the rational-voter utility formula `Uv=(1-q)R-qP` (M1),
where `q` naturally means "risk of being caught."

## The game-theoretic optimal attacker (`attacks/bribery_game_theory.py`)

Expected utility for attempting `T` bribes:

```
U(T) = P(X>=m)*V  -  T*R*1[voter accepts]  -  P(at least one of T accepted
        bribes is detected)*D_attack
```

where `V` is the attacker's payoff if the flip succeeds and `D_attack`
is the expected cost incurred if the attack is caught. `optimal_attempts()`
searches `T` over `[0, min(N,floor(B/R))]` for the utility-maximizing
value, respecting the same rational-voter gate as the rest of the
project: if bribery is not incentive-compatible at all
(`Uv=(1-q)R-qP<=0`), the optimal strategy is trivially `T*=0`
regardless of budget (verified in `tests/test_bribery_game_theory.py`).

**Figure 8** illustrates this with a scenario chosen to have enough
budget headroom that `P(flip)` saturates near 1 well before the budget
is exhausted: utility climbs sharply as `T` approaches the
manipulation threshold `m` (marked explicitly on the secondary axis),
peaks at `T*=319`, and then **declines** for `T>T*` as additional
bribes add cost and detection risk without materially increasing an
already-near-certain flip probability. This is the clearest
illustration of "more attempts is not always rational," a genuinely
non-obvious finding that a pure P(X>=m) success-probability framework
(without the utility layer) cannot express.

**Figure 7** grounds the abstract `P(X>=m)` formula used everywhere
else in the project in one concrete picture: the full binomial PMF of
successful fraudulent votes, with the threshold `m` marked as a
vertical line and the success region shaded.

## The five named scenarios

| ID | Scenario | N | m | B | Baseline P(flip) | Protected P(flip) | Chernoff bound (baseline) |
|---|---|---|---|---|---|---|---|
| S1 | Small university election | 100 | 35 | 3,000 | 0.423 | 0.000 | 0.987 |
| S2 | Medium organisation election | 10,000 | 1,943 | 250,000 | 0.328 | 0.000 | 0.991 |
| S3 | Large national-scale election | 100,000 | 19,015 | 3,000,000 | 0.320 | 0.000 | 0.994 |
| S4 | High-budget attack | 5,000 | 4,758 | 5,000,000 | 0.316 | 0.000 | 0.993 |
| S5 | Low-budget attack | 5,000 | 550 | 8,000 | ~0.000 | ~0.000 | ~1.3e-267 |

(The full named-scenario table, with Monte Carlo estimates, standard errors,
and game-theoretic `T*`/utility values in
`results/csv/named_scenarios_results.csv`.)

**Calibration note:** for S1-S4, the threshold `m` is deliberately set
close to (0.3-0.5 standard deviations above) the baseline mean
`mu=T(1-q)`, rather than at an extreme -- this is what makes the
exact/Monte-Carlo/Chernoff three-way comparison actually informative.
Placing `m` far below `mu` would make baseline success trivially ~1;
far above would make it trivially ~0; in both cases the Chernoff
dispatcher (`mathematics/chernoff.py`) returns no bound at all for the
degenerate `m<=mu` case, and the comparison has nothing to show.

### S3 -- Monte Carlo vs Chernoff at national scale

This scenario is specifically built to exercise the exact/Monte
Carlo/Chernoff comparison at `N=100,000`. Exact probability is
**0.3204**; the 5,000-draw Monte Carlo estimate is **0.3262**
(absolute error 0.0058, consistent with a 5,000-sample binomial
standard error at this probability, roughly 0.0066); the Chernoff
upper bound is **0.9941** -- correctly an upper bound, and, as
expected of Chernoff bounds generally, far from tight at this
particular `(T,m)` combination. This is reported honestly rather than
cherry-picking a `(T,m)` pair where Chernoff happens to look tighter
-- see `EXPERIMENTAL_REPORT.md` Section 17 for the aggregate statement
(over 8,163 trials) that the bound is conservative but never violated.

### S5 -- Low-budget attack validated to fail

With `B=8,000` and `R=100`, the attacker can approach at most
`T=floor(8000/100)=80` voters -- far short of the `m=550` votes
needed to flip this particular (deliberately larger-margin) election.
Exact `P(X>=m)` is **0.0** to floating-point precision (the Chernoff
bound correctly computes as an astronomically small but technically
nonzero number, ~1.3e-267, correctly reflecting "essentially
impossible" while never literally claiming impossibility) -- directly
validating this scenario's design intent.

## Security evaluation: with vs without blockchain (game-theoretic view)

Across S1-S4, the protected configuration (`q=0.55`, i.e. a
blockchain-audited system with substantially higher detection
probability than the `q=0.05-0.08` baseline) drove exact flip
probability to **0.000** in every scenario, and correspondingly the
game-theoretic optimal attacker's utility collapses to exactly 0
(`T*=0` -- a rational attacker facing these detection odds should not
attempt the attack at all, independent of how large their budget is).
This is the sharpest possible statement of countermeasure
effectiveness available from this model: not merely "success
probability is lower," but "the attack is no longer rational to
attempt in the first place" for a rational, utility-maximizing
attacker under the tested parameter choices.

This finding should be read alongside the caveats in
`ASSUMPTIONS.md`: it depends on `q_protected=0.55` genuinely being
achievable by a real system's audit/signature/identity pipeline, and
on the rational-voter and rational-attacker assumptions holding in
practice -- see `EXPERIMENTAL_REPORT.md` Sections 23-24 for the full
threats-to-validity discussion, which applies here identically.
