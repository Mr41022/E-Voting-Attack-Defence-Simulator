# Blockchain-Based E-Voting Attack Simulation

A controlled, synthetic-data research simulation built for an MSc
thesis at the University of Glasgow:

> *Blockchain-Based Electronic Voting System with Mathematical
> Modelling and Experimental Evaluation of Bribery, Sybil and Ballot
> Stuffing Attacks.*

This is **not** a real attack tool, does not touch any real election
system, and uses no real voter data or identities anywhere. It is a
mathematical/statistical simulation for academic research.

---

## 1. Research objective

Evaluate, mathematically and experimentally, how three classes of
e-voting manipulation — **bribery**, **Sybil identity attacks**, and
**ballot stuffing** — respond to security countermeasures modelled on
a blockchain-style immutable audit ledger, digital signatures,
identity verification, and ballot validation.

## 2. Architecture

This project has two complementary layers.

**A. A real, working blockchain-based e-voting application** (Phase
1-3, per the original build spec):
```
blockchain_core/            Phase 1 -- Blockchain Foundation
    block.py                    Block structure, SHA-256 hashing
    chain.py                    Blockchain: genesis, mining (proof-of-work),
                                 add_block, is_chain_valid, replace_chain,
                                 tamper_with_block (demo only), count_votes
evoting_app/                 Phase 2 -- E-Voting System
    entities.py                  User/Admin/Voter, Election, Candidate
    service.py                   VotingService: registration, election &
                                  candidate management, vote casting,
                                  duplicate-vote prevention, result publication
demo_blockchain_evoting.py   Phase 3 -- runnable end-to-end demonstration
```
Run it yourself: `python demo_blockchain_evoting.py` -- prints (and
saves to `results/BLOCKCHAIN_EVOTING_DEMO_LOG.md`) a full worked
example of all three phases, including a live tamper-detection
demonstration (a vote is edited after mining; `is_chain_valid()`
catches it and reports the exact block index).

**B. The mathematical/statistical attack-research framework**, which
attacks the layer above:
```
config.py                  parameter ranges (single source of truth)
random_generator.py        reproducible numpy.random.Generator wrapper

models/                    ElectionScenario, Voter, AttackerBudget (M3),
                            evoting_system.py (concrete 2-candidate election
                            helpers: flip_threshold, simulate_fraud_attempts)
mathematics/                binomial.py (M4-M6,M9,M10,M12,M13), chernoff.py (M7,M8),
                             utility.py (M1,M2), probability.py (M11,M14),
                             thresholds.py (T1-T7: critical-threshold solvers)
attacks/                    bribery.py, sybil.py, ballot_stuffing.py
                            (abstract P(X>=m) statistics, large-N Monte Carlo),
                            bribery_game_theory.py (utility-maximizing optimal
                            attacker strategy: searches T for max expected
                            utility U(T) = P(flip)*V - cost - detection penalty),
                            game_theory.py (G1: the same optimisation unified
                            across all three vectors; G2: coalition attack, one
                            budget split across vectors, exact convolution)
countermeasures/            digital_signatures.py, identity_verification.py,
                             ballot_validation.py, audit.py, blockchain.py
                             (lightweight ledger abstraction used by the
                             abstract framework's countermeasure configs)
simulation/                 scenario_generator.py (paired randomisation),
                             experiment_runner.py (abstract, 2,500 trials),
                             election_attack_runner.py (CONCRETE, attacks the
                             real blockchain_core.Blockchain, real vote
                             tallies, real winner-flip outcomes),
                             named_scenarios.py (5 fixed benchmark scenarios:
                             university/organisation/national scale,
                             high-budget, low-budget),
                             threshold_analysis.py (T1-T7 + G1-G2 evaluated on
                             the named scenarios; parameter sweeps),
                             monte_carlo.py
analysis/                   statistics.py, comparison.py, validation.py
visualisation/              style.py (one visual system: validated colourblind-safe
                             palette, typography, threshold-annotation helpers),
                             plots.py (figures 1-5, 7-8), threshold_plots.py
                             (figures 6, 9-10)
report/                     thesis_report.tex (typeset report; every number is
                             injected at build time from results/, none typed by hand)
tests/                      119 pytest tests

run_experiments.py          CLI: abstract 2,500-trial P(X>=m) statistics
run_election_attacks.py     CLI: concrete blockchain election-flip statistics
run_threshold_analysis.py   CLI: critical thresholds, coalition search, sensitivity
generate_figures.py         builds all 10 figures + captions
generate_tables.py          builds 14 CSV tables + 3 LaTeX tables
generate_report.py          builds the typeset PDF report
generate_extract.py         builds the lit-review + methodology extract
generate_key_figures.py     builds the ten-figure visual guide
```

Why two layers? The abstract framework (A) gives thesis-grade
statistical rigour at scale (2,500 paired trials, exact binomial
probability, Chernoff bounds, Monte Carlo validation -- infeasible to
run at that scale against a real mined blockchain). The concrete layer
(B) gives an audited, tamper-evident, genuinely-mined demonstration
that ties every abstract number back to an actual election with an
actual winner -- see `results/ELECTION_OUTCOME_REPORT.md`.

## 3. Threat model

Attacker seeks ≥ `m` successful fraudulent actions out of an
electorate of `N` voters, via one of three vectors:

- **Bribery:** offers reward `R` to voters, constrained by budget
  `B`; a targeted voter accepts only if rationally incentivised
  (`Uv = (1-q)R - qP > 0`); accepted bribes succeed with probability
  `1-q`.
- **Sybil:** submits `S` fake identities, each accepted with
  probability `qs` and independently detected with probability `pd`.
- **Ballot stuffing:** submits `A` fraudulent ballots, each accepted
  with probability `qb` and independently detected with probability
  `pb`.

Each attack is evaluated under a **baseline** configuration (weak
detection/verification) and a **protected** configuration
(blockchain-style ledger + signatures + identity/ballot validation,
modelled as higher detection / lower acceptance probability), using
the *same* underlying randomised scenario for both — a paired design.

## 4. Mathematical framework

Full equation-by-equation traceability (M1–M14) is in
[`MATHEMATICAL_MODEL.md`](MATHEMATICAL_MODEL.md). Summary:

- Rational voter utility: `Uv = (1-q)R - qP` (M1); incentive condition
  `R > qP/(1-q)` (M2).
- Attacker budget: `T = min(N, floor(B/R))` (M3).
- Outcome distributions: `X ~ Binomial(T,1-q)` (bribery, M4),
  `Y ~ Binomial(S,qs)` (Sybil, M9), `Z ~ Binomial(A,qb)` (ballot
  stuffing, M12); attack succeeds when the count `>= m`.
- Chernoff bounds (M7 upper tail, M8 lower tail — **negative-sign
  form explicitly enforced and unit-tested**).
- Detection survival: `(1-p)^n` / `1-(1-p)^n` (M11, M14).

## 5. Countermeasures modelled

- **Simulated blockchain ledger** (`countermeasures/blockchain.py`):
  in-memory, append-only, SHA-256-hashed audit records. **Not** a
  cryptocurrency, **not** a distributed consensus network.
- **Digital signature check**, **identity verification**, **ballot
  validation**, **audit logging** — all modelled as probability
  adjustments between baseline and protected configurations (see
  `countermeasures/`).

Security interpretation is intentionally conservative throughout the
report: the protected configuration *reduces* attack feasibility and
*improves* detection under the simulation's assumptions — it is never
claimed to make bribery, Sybil attacks, or ballot stuffing
impossible. See `ASSUMPTIONS.md` and `results/EXPERIMENTAL_REPORT.md`
§25 for the full security-interpretation discussion.

## 6. Chernoff bound

Implemented with an explicit tail dispatcher
(`mathematics/chernoff.py`) that only applies the upper-tail form when
`m > mu` and only applies the lower-tail form (with the mandatory
**negative** sign, `exp(-mu·delta²/2)`) when `m < mu`. Both are
independently unit-tested; `test_lower_tail_negative_sign_required`
specifically guards against the sign-flip bug called out in the
project brief.

## 7. Experimental methodology

- **Randomisation:** `simulation/scenario_generator.py` draws one
  underlying `TrialScenario` per trial from the ranges in
  `config.py`, using `numpy.random.default_rng(seed)` exclusively (no
  legacy global RNG state).
- **Pairing:** baseline and protected results for a trial always share
  identical `N, m, B, R, P, S, A` — only detection/acceptance
  probabilities differ. This is what makes the baseline-vs-protected
  comparison a fair, paired experiment (see
  `simulation/experiment_runner.py`).
- **Trial count:** 2,500 paired trials by default (5,000 rows per
  attack CSV: baseline + protected) — increased from the original
  1,000-trial minimum specified in the brief for tighter confidence
  intervals.
- **Monte Carlo:** 2,000 repetitions per scenario by default.
- **Reproducibility:** identical `--seed` → bit-for-bit identical
  output (`tests/test_reproducibility.py`); different seeds produce
  different scenarios.

## 8. Parameter ranges

See `config.py::PARAM_RANGES` (also exported as
`results/csv/table_01_parameter_ranges.csv`). Electorate size `N` is
sampled from 200–5,000 voters; the manipulation threshold `m` is
sampled as 2–25% of `N` (so `m` varies per trial — see
`results/csv/table_10_sample_scenarios_with_threshold.csv` for
concrete `(N, m)` pairs from real trials, and
`results/json/summary.json::threshold_m_statistics` for the full
distribution of `m` actually used across all trials).

## 9. Installation

**Windows:**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.11+ recommended (developed and tested on 3.12).

## 10. Running experiments

```
python run_experiments.py --trials 2500 --seed 42
```

Individual attacks:
```
python run_experiments.py --attack bribery --trials 2500 --seed 42
python run_experiments.py --attack sybil --trials 2500 --seed 42
python run_experiments.py --attack ballot_stuffing --trials 2500 --seed 42
```

All attacks explicitly:
```
python run_experiments.py --attack all --trials 2500 --seed 42
```

Then build figures and tables:
```
python generate_figures.py
python generate_tables.py
```

**Concrete blockchain-backed election-attack simulation** (real
proof-of-work blockchain, real vote tallies, real winner-flip
outcomes — the complement to the abstract statistics above):
```
python run_election_attacks.py --trials 300 --seed 42
```

**Phase 1/2/3 blockchain + e-voting demonstration** (genesis block,
mining, tamper detection; voter registration, election, candidate
management, voting, duplicate-vote rejection, tally; full end-to-end
workflow):
```
python demo_blockchain_evoting.py
```

Figures 7-8 (the binomial distribution with its margin thresholds, and
the game-theoretic optimal attacker) and the 5 named benchmark
scenarios are generated automatically as part of `generate_figures.py`
— no separate command needed.

## 11. Running tests

```
pytest -q
```
or
```
python -m pytest -q
```

119 tests covering: voter utility/decision, budget edge cases, exact
binomial correctness, Chernoff upper/lower tail (including the
negative-sign safeguard), Sybil/ballot detection formulas,
countermeasure configs, blockchain ledger, edge cases (m≤0, m>N, B=0,
R=0, B<R, q∈{0,1}, large-N overflow safety), seed reproducibility,
proof-of-work mining correctness, chain-linkage integrity, tamper
detection, duplicate-vote prevention, role-based access control (only
an admin can manage elections/candidates), the game-theoretic optimal
attacker (rational-rejection forces T*=0, interior optima exist),
the 5 named benchmark scenarios (low-budget fails, protected suppresses
all, Chernoff holds, reproducibility), the seven threshold solvers
(each answer is verified to bracket the crossing it claims to find, and
absent thresholds are reported as absent), and the coalition model (the
exact convolution is checked against a 200,000-draw Monte Carlo
simulation; a mixed strategy is never worse than the best pure one), and
figure geometry (the shaded success region in Figure 7 must begin at the
EDGE of the first shaded bar, m-0.5, not at its centre -- drawing the
threshold line at m bisects that bar and makes the shading look like it
starts half a vote early), and
the Chernoff tail forms (the (1-delta) form is demonstrated to be
INVALID as an upper-tail bound -- it fails in 12 of 15 test cases -- while
the (1+delta) form bounds every one of them; the two-sided certificate is
checked to contain the exact value in every scenario).

## 12. Output files

```
results/csv/
    bribery_results.csv, sybil_results.csv, ballot_stuffing_results.csv
    combined_results.csv, chernoff_validation.csv
    cross_attack_comparison.csv, electorate_size_sweep.csv
    election_outcome_results.csv, named_scenarios_results.csv
    table_01 .. table_14 (*.csv)
    detection_sweep.csv, budget_sweep.csv
results/json/summary.json, election_outcome_summary.json, threshold_analysis.json
report/thesis_report.pdf, report/generated/numbers.tex, report/generated/tables/*.tex
results/plots/fig_01 .. fig_10 (*.png, *.pdf)
results/latex/table_attack_comparison.tex, table_chernoff_validation.tex,
              table_countermeasure_effectiveness.tex
results/FIGURE_CAPTIONS.md
results/EXPERIMENTAL_REPORT.md
results/ELECTION_OUTCOME_REPORT.md
results/GAME_THEORY_SCENARIOS_REPORT.md
results/FINAL_RESULTS.md
results/BLOCKCHAIN_EVOTING_DEMO_LOG.md
```

## 13. Interpretation

All headline numbers in this README, in `results/EXPERIMENTAL_REPORT.md`,
and in `results/FINAL_RESULTS.md` are read directly from an actual run
of `results/json/summary.json` (seed 42, 2,500 trials) — none are
invented. Re-running with the same seed reproduces them exactly;
re-running with a different seed will shift the numbers slightly
(within the reported confidence intervals) but not the qualitative
conclusions, which were checked across seeds during development.

## 14. Limitations

See `ASSUMPTIONS.md` for the full list. Headline caveats: voters are
modelled as fully rational; fraud attempts are independent Bernoulli
trials with constant per-scenario probabilities; the "blockchain" is
an educational in-memory ledger abstraction, not a real distributed
system; countermeasure effectiveness is expressed purely through
probability parameters, not a specific cryptographic implementation.

## 15. Reproducibility statement

```python
rng = np.random.default_rng(seed)
```
is used everywhere randomness is required — no `numpy.random.seed()`
global state, no unseeded `random` module calls. `tests/test_reproducibility.py`
enforces this at the experiment-runner level.


## 16. Chernoff tail forms (reviewer note)

The upper-tail bound uses `(1+delta)` and the lower-tail bound uses
`(1-delta)`. These are not interchangeable: the factor records which
side of the mean the threshold lies on. A review suggested swapping
them; `tests/test_chernoff.py::test_lower_tail_form_is_invalid_on_upper_tail`
shows the substitution fails in 12 of 15 cases, at worst claiming a
bound of 4.0e-9 against a true probability of 1.0000.

The review did expose a real gap, which is now closed. The one-sided
dispatcher returns a bound only when `m > mu`, leaving 21-31% of
scenarios -- those where the attack is most likely to SUCCEED -- with no
analytic statement. `mathematics/chernoff.py::chernoff_certificate`
bounds whichever tail the threshold falls in: upper tail certifies
success from above, lower tail (applied to the failure event) certifies
it from below. Every scenario now carries a guarantee, and the certified
interval contains the exact value in 100% of 15,000 evaluations. See
`MATHEMATICAL_MODEL.md` and Figure 3.


## 17. The ten figures

The simulation generates **ten** figures, numbered in order of
appearance in the dissertation, so `fig_07_*` is Figure 7 of the report.
`check_consistency.py` fails if those two ever drift apart.

| Fig | File | Carries |
|----:|------|---------|
| 1 | `fig_01_method_comparison` | exact vs Monte Carlo vs Chernoff; the detection collapse |
| 2 | `fig_02_voter_utility_threshold` | the rational-voter gate |
| 3 | `fig_03_chernoff_two_sided` | both Chernoff directions validated |
| 4 | `fig_04_attack_comparison` | headline countermeasure effect |
| 5 | `fig_05_election_flip_rate` | concrete winner flips on mined chains |
| 6 | `fig_06_critical_detection` | critical detection threshold |
| 7 | `fig_07_binomial_thresholds` | the three margin thresholds |
| 8 | `fig_08_optimal_attacker` | game-theoretic optimal attacker |
| 9 | `fig_09_vector_capacity` | why no single vector suffices |
| 10 | `fig_10_coalition_vs_pure` | coalition vs best single vector |

An earlier version generated thirty. Several were variations on a single
point, and the important figures were diluted by the rest. The analyses
those figures illustrated -- the budget sweep, the feasibility surface,
the electorate-size sweep, the break-even budget, the contested-margin
band, the coalition simplex and the cost-sensitivity sweep -- all still
run, and their outputs remain in `results/csv/`. Only the figures were
removed; no result was.

`report/key_figures.pdf` presents all ten with a plain-language
explanation of each, using the same numbering.

## 18. What the ledger contributes (scope of the security claim)

The pipeline is ordered:

```
fraud attempt -> acceptance / identity / signature / ballot validation
             -> detection -> surviving votes only -> ledger records them
```

Every fraudulent vote stopped in this model is stopped by validation or
detection. The ledger contributes integrity, immutability, auditability
and tamper evidence, and contributes nothing to deciding whether a vote
should have been cast. Nothing here shows that "blockchain prevents
bribery". The supported claim is narrower and conditional: under this
model and over the sampled parameter ranges, a protected architecture
combining ledger-backed auditability with identity verification,
signature validation, ballot validation and raised detection
substantially reduces attack feasibility. The concrete layer measures
the two properties separately, and they come apart: chain integrity held
in every trial while elections were still flipped.
