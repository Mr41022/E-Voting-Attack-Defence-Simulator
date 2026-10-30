# Project Architecture Audit

## Purpose

This repository is a synthetic e-voting security simulation with two linked but non-equivalent layers:

1. An abstract probability and game-theory framework for bribery, Sybil and ballot-stuffing attacks.
2. A small in-memory proof-of-work voting demonstration and a separate concrete election-flip runner.

The project does not model a production distributed election system. Its strongest defensible claim is conditional: under the declared Bernoulli, independence, parameter-range and rational-voter assumptions, the protected parameter configuration reduces modelled attack success.

## Dependency flow

`config.py` -> `simulation/scenario_generator.py` -> `simulation/experiment_runner.py` -> `attacks/*` -> `mathematics/*` and `analysis/*` -> `results/csv` and `results/json`.

The concrete path is `simulation/election_attack_runner.py` -> `blockchain_core/*` -> concrete election result CSV/JSON. It does not call `evoting_app/service.py` and does not exercise the countermeasure classes as implementations; it directly calls `models/evoting_system.simulate_fraud_attempts`.

The reporting path consumes existing generated files: `generate_figures.py`, `generate_tables.py`, `generate_report.py`, `generate_extract.py`, `generate_key_figures.py`, `build_compendium.py`, and `build_submission.py`. There is no single orchestrator and no manifest of required inputs.

## Major modules

- `models/`: scenario, voter, attacker-budget and abstract election data structures.
- `mathematics/`: exact binomial probabilities, utility, detection probability, Chernoff bounds and threshold solvers.
- `attacks/`: bribery, Sybil, ballot stuffing and game-theoretic optimisation.
- `countermeasures/`: lightweight ledger/audit abstractions and probability-adjustment helpers.
- `simulation/`: paired abstract trials, concrete mined-election trials, named scenarios and sweeps.
- `blockchain_core/`: mutable in-memory blocks, SHA-256 hashes and proof-of-work.
- `evoting_app/`: small service-layer voting demo with registration, election lifecycle, duplicate-vote flag and tallying.
- `analysis/`: descriptive statistics, paired comparisons and validation summaries.
- `visualisation/`: ten PNG/PDF figures and captions.
- `report/`: thesis, extract, compendium and generated LaTeX fragments.
- `tests/`: 119 pytest tests, concentrated on formulas, reporting claims, blockchain basics and selected service behavior.

## Experiment and data flow

`run_experiments.py` creates one `TrialScenario` per trial, derives baseline/protected probabilities, runs exact and Monte Carlo calculations, computes Chernoff outputs, and writes three attack CSVs plus summaries. Baseline and protected structural parameters are paired, but their Monte Carlo draws are sequential draws from one generator, not common random numbers.

`run_election_attacks.py` creates a fresh two-candidate election, mines legitimate ballots, selects the current loser as the target, simulates accepted-and-undetected fraud, mines surviving fraud, recounts the chain, and checks chain validity. Its parameter ranges and estimand differ from the abstract experiment.

`run_threshold_analysis.py` computes T1-T7, G1 and G2 analytically for five fixed scenarios and performs cost/ceiling sensitivity. Figures and tables then read these outputs. Reports inject many numbers, but static Markdown result reports remain separately maintained and are stale in places.

## Architectural risks

- Generated outputs are both inputs and outputs; partial runs can mix new and stale data.
- Concrete results are not a replay of abstract scenarios and therefore are not validation of the same estimand.
- The service layer trusts object roles and permits duplicate identifiers to overwrite state.
- The blockchain is single-process and mutable; proof-of-work demonstrates hashing, not consensus, availability, privacy or coercion resistance.
- PDF compilation requires external `pdflatex`, which is absent in the audited Windows environment.
