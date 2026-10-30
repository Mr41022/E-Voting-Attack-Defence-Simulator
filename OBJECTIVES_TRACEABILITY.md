# Objectives Traceability

The README states the central objective as evaluating bribery, Sybil and ballot-stuffing manipulation under modelled countermeasures, with exact probability, Monte Carlo, Chernoff and concrete blockchain demonstration. The original project plan/specification was not separately located, so any objective beyond the README is **NOT VERIFIED**.

| Objective | Code | Experiment/evidence | Status |
|---|---|---|---|
| Model bribery | `attacks/bribery.py`, `mathematics/utility.py` | Abstract CSV/JSON, tests, Figures 1/2/4 | FULLY SATISFIED within assumptions |
| Model Sybil and ballot stuffing | `attacks/sybil.py`, `attacks/ballot_stuffing.py` | CSV/JSON, Figures 4 and threshold outputs | FULLY SATISFIED within two-gate assumptions |
| Compare baseline/protected configurations | `simulation/experiment_runner.py` | 2,500 paired trials and bootstrap summaries | FULLY SATISFIED for scenario-level pairing |
| Establish exact binomial calculations | `mathematics/binomial.py` | Exact-vs-Monte-Carlo checks and tests | FULLY SATISFIED computationally |
| Validate Chernoff bounds | `mathematics/chernoff.py` | Upper-tail checks and certificate figure | PARTIALLY SATISFIED: conditional and partly tautological validation |
| Demonstrate reproducibility | seeded NumPy generators and tests | same seed equal, different seed differs | PARTIALLY SATISFIED: data path works, clean full report pipeline does not |
| Demonstrate working blockchain voting flow | `evoting_app/service.py`, `blockchain_core/*`, demo | tests and demo log | PARTIALLY SATISFIED: educational single-process system; service security gaps remain |
| Demonstrate winner flips | `simulation/election_attack_runner.py` | 300 concrete trials and Figure 5 | FULLY SATISFIED as a separate model-defined estimand |
| Find critical thresholds and coalition strategies | `mathematics/thresholds.py`, `attacks/game_theory.py` | five named scenarios, sweeps, Figures 6-10 | PARTIALLY SATISFIED: fixed scenarios and grid/cost assumptions limit generality |
| Claim real-world e-voting security | None | No production cryptography, consensus, privacy or coercion resistance | NOT DEMONSTRATED and should not be claimed |

Features outside the core objective are the game-theoretic coalition extension, report compendium and figure-guide tooling. These should be presented as extensions, not as evidence that a real election system is secure.
