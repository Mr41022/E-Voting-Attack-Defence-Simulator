# Final Results

Generated from an actual run: `python run_experiments.py --trials 2500 --seed 42`,
followed by `python generate_figures.py` and `python generate_tables.py`.
Source of truth: `results/json/summary.json`.

## Run configuration

| | |
|---|---|
| Total paired trials | 2,500 |
| Random seed | 42 |
| Monte Carlo repetitions per scenario | 2,000 |
| Attacks evaluated | bribery, sybil, ballot_stuffing |
| Wall-clock time for 2,500-trial simulation | ~6.1 seconds |

## Parameter ranges used

Full ranges in `config.py::PARAM_RANGES` / `results/csv/table_01_parameter_ranges.csv`.
Electorate size N: 200-5,000. Manipulation threshold m: sampled as
2%-25% of N per trial (actual realised range across all 2,500 trials:
min m = 5, max m = 1,206, mean m = 344.3, median m = 273.5 -- see
`results/json/summary.json::threshold_m_statistics` and
`results/csv/table_10_sample_scenarios_with_threshold.csv` for
concrete per-trial (N, m) pairs).

## Baseline results

| Attack | Mean success probability | 95% CI |
|---|---|---|
| Bribery | 0.350 | [0.331, 0.369] |
| Sybil | 0.480 | [0.461, 0.500] |
| Ballot stuffing | 0.442 | [0.423, 0.461] |

## Protected results

| Attack | Mean success probability | 95% CI |
|---|---|---|
| Bribery | 0.064 | [0.054, 0.073] |
| Sybil | 0.136 | [0.123, 0.148] |
| Ballot stuffing | 0.116 | [0.104, 0.128] |

## Bribery findings

Rational voters reject bribes whenever `Uv=(1-q)R-qP <= 0`; the
attacker's reach is hard-capped at `T=min(N,floor(B/R))` regardless of
detection probability. Mean reduction from countermeasures: 81.9%
relative (largest of the three attacks), 0.287 absolute.

## Sybil findings

Mean reduction: 71.8% relative, 0.345 absolute (largest absolute
reduction of the three attacks). Remained the most resilient attack
under protection (mean protected success 0.136).

## Ballot stuffing findings

Mean reduction: 73.7% relative, 0.325 absolute.

## Chernoff validation

| Attack | Valid trials | Bound holds | Mean conservativeness |
|---|---|---|---|
| Bribery | 1,088 | 100.0% | 0.042 |
| Sybil | 3,471 | 100.0% | 0.026 |
| Ballot stuffing | 3,604 | 100.0% | 0.022 |

## Monte Carlo validation

| Attack | Mean \|MC-Exact\| | Max \|MC-Exact\| |
|---|---|---|
| Bribery | 0.00008 | 0.0149 |
| Sybil | 0.00039 | 0.0300 |
| Ballot stuffing | 0.00039 | 0.0230 |

## Countermeasure effectiveness

| Attack | Absolute reduction | Relative reduction | Bootstrap 95% CI (absolute) |
|---|---|---|---|
| Bribery | 0.287 | 81.9% | [0.269, 0.304] |
| Sybil | 0.345 | 71.8% | [0.327, 0.362] |
| Ballot stuffing | 0.325 | 73.7% | [0.308, 0.343] |

## Statistical results

Bootstrap 95% CIs on the paired mean reduction exclude zero for all
three attacks -- the countermeasure effect is statistically robust
under the tested parameter distribution. See
`results/EXPERIMENTAL_REPORT.md` §19 for the reasoning behind using
bootstrap rather than a parametric test.

## Important limitations

Full list in `ASSUMPTIONS.md`. Headline: rational-voter assumption,
independent Bernoulli trials with constant per-scenario probabilities,
non-adaptive single-shot attacker, blockchain modelled as an
in-memory audit-ledger abstraction (not a real distributed system),
and all headline numbers are conditional on the specific uniform
parameter ranges sampled in `config.py`.

## Research implications

The results support the thesis's central claim in a carefully bounded
way: blockchain-audited countermeasures substantially reduce (but do
not eliminate) attack feasibility across all three vectors tested, and
the reduction is large enough (>70% relative in every case) to be
practically as well as statistically significant. The distinct
resource-ceiling effect uncovered in the controlled electorate-size
sweep (sharp collapse once attacker resources fall below the manipulation
threshold as N grows; see `results/csv/electorate_size_sweep.csv`)
is a novel, reproducible observation directly attributable to the
`T=min(N,floor(B/R))` budget formula (M3) and is worth highlighting as
an independent contribution in the thesis discussion chapter.
