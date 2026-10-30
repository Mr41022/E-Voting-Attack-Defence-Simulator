# SecureVoteSim
### E-voting Attack Simulation & Countermeasure Evaluation

SecureVoteSim is a research-oriented simulation project for studying the resilience of electronic voting systems under three adversarial scenarios: **bribery, Sybil attacks, and ballot stuffing**. It compares recorded attack outcomes under a baseline configuration with outcomes under a protected configuration, and uses statistical validation to assess the simulation results.

The project is intended to support controlled experimentation and security analysis—not to certify, deploy, or prove the security of a real-world election system.

## At a glance

- **Research focus:** electronic voting security and countermeasure effectiveness
- **Attack scenarios:** bribery, Sybil attacks, and ballot stuffing
- **Evaluation approach:** repeated trials, baseline-versus-protected comparisons, Monte Carlo validation, and Chernoff-bound checks
- **Recorded main run:** 2,500 trials per attack category
- **Recorded Monte Carlo setting:** 2,000 Monte Carlo trials per scenario
- **Reproducibility:** the main summary records random seed `43`
- **Recorded runtime:** approximately 9.1 seconds for the summarised run (environment-dependent)

## Why this project?

Electronic voting systems must account for threats that target voter choice, voter identity, and ballot integrity. A security mechanism should be assessed not only by whether it sounds plausible, but by how the system behaves under clearly specified assumptions and repeatable experiments.

SecureVoteSim explores that question by modelling multiple attack classes, comparing baseline and protected outcomes, and recording statistical evidence about the observed differences. It also includes checks related to Monte Carlo estimation and Chernoff bounds, helping make the evaluation more rigorous than a single illustrative simulation.

## Attack scenarios

| Attack class | What it represents |
|---|---|
| **Bribery** | An adversary attempts to influence how eligible voters cast their votes through incentives or coercion represented by the model. |
| **Sybil attack** | An adversary attempts to gain influence by representing multiple identities or participants. |
| **Ballot stuffing** | An adversary attempts to introduce unauthorised ballots or inflate the vote count. |

These are model-level descriptions of the threat categories. The exact attack mechanics, parameters, and assumptions should be read from the implementation and experiment configuration.

## Experimental results

The included `run_a_summary.json` records the following mean outcomes for the baseline and protected configurations.

| Attack scenario | Baseline mean | Protected mean | Absolute reduction | Relative reduction |
|---|---:|---:|---:|---:|
| Bribery | 34.40% | 6.22% | 28.19 percentage points | 81.93% |
| Sybil | 45.92% | 11.50% | 34.42 percentage points | 74.95% |
| Ballot stuffing | 41.68% | 9.83% | 31.85 percentage points | 76.41% |

**How to interpret this table:** these are the mean values recorded by the simulation for its baseline and protected configurations. The absolute reduction is the difference between the two means; the relative reduction is that difference divided by the baseline mean. They describe results under the modelled conditions and are not estimates of real-world election-fraud reduction.

### Bootstrap intervals for paired reductions

The summary also records bootstrap intervals for the mean paired reduction:

| Attack scenario | Recorded lower bound | Recorded upper bound |
|---|---:|---:|
| Bribery | 26.51 percentage points | 30.07 percentage points |
| Sybil | 32.64 percentage points | 36.22 percentage points |
| Ballot stuffing | 30.07 percentage points | 33.66 percentage points |

The JSON stores the interval endpoints but does not itself label the confidence level. Confirm the bootstrap implementation and confidence level in the source code before describing these as, for example, 95% confidence intervals.

### What the results suggest

Within this particular run, the protected configuration has a lower mean simulated attack outcome for all three attack classes. The largest recorded relative reduction is for bribery, while the largest absolute reduction is for Sybil attacks.

These comparisons do **not** establish that one attack is universally more dangerous than another. The ranking depends on the model, parameter ranges, attack definitions, and protection mechanisms used in the experiment.

## Statistical validation recorded in the results

### Monte Carlo convergence check

The summary includes a reference binomial case with:

- \(n = 200\)
- \(p = 0.55\)
- Threshold \(m = 120\)
- Exact reference probability: approximately `0.088073`
- Recorded final absolute error: approximately `0.001493`
- Recorded tolerance: `0.01`
- First recorded sample size meeting that absolute-error tolerance: `3,000`

This provides a check of Monte Carlo estimation against a case with an exact probability available. The recorded convergence result applies to this reference case; it should not be interpreted as a universal guarantee that every simulation scenario converges at the same sample size.

### Chernoff-bound checks

The main summary records that the Chernoff-bound checks held for **100% of the rows marked valid** for each attack category. It also records that the generated Chernoff certificates contained the exact value in **100% of the certificate rows** for the tested data.

These percentages are results from the project's recorded validation set, not a proof that every possible parameter combination or implementation path is correct. The exact bound formulas, validity conditions, and certificate construction should be documented alongside the code.

## Methodology overview

At a high level, the recorded experiment follows this evaluation pattern:

1. Configure an attack scenario and its model parameters.
2. Run repeated trials to obtain baseline outcomes.
3. Run the corresponding protected configuration.
4. Compare the resulting means and paired reductions.
5. Use bootstrap resampling to quantify uncertainty in the paired reduction.
6. Check Monte Carlo estimates against an exact binomial reference case.
7. Evaluate the stated Chernoff bounds and associated certificates on valid test rows.
8. Save aggregate statistics and validation outputs as JSON.

This overview reflects the available experiment summary. Consult the implementation for the exact mathematical definitions, probability distributions, parameter ranges, pairing strategy, and treatment of dependencies between events.

## Reproducibility

The main run summary records random seed `43`, 2,500 trials, and 2,000 Monte Carlo trials per scenario. Fixing a seed can help reproduce a run when the code, dependencies, parameters, and execution environment are also held constant.

For a reproducible research release, include:

- The simulation source code and experiment configuration.
- A dependency manifest with pinned or documented package versions.
- Exact commands for running the simulation and tests.
- The random seed and trial counts used for each published result.
- Definitions of every reported metric and confidence interval.
- The generated result files and instructions for regenerating them.
- A description of the hardware and software environment if runtime is reported.

**Run instructions:** add the verified installation and execution commands for the committed source tree before publishing. The archive used to prepare this README contained the JSON summaries but not the Python source files or dependency manifest, so project-specific commands could not be verified from it.

## Repository contents

The supplied archive includes these experiment summaries:

```text
run_a_summary.json
s42_a.json
s42_b.json
```

The main summary contains aggregate attack outcomes, protected outcomes, countermeasure-effectiveness statistics, Monte Carlo convergence information, Monte Carlo validation, Chernoff-bound validation, certificate-validation statistics, and threshold statistics. The `s42_a.json` and `s42_b.json` files record runs associated with seed `42`; inspect their provenance and intended role before treating them as independent replications or combining them with the main run.

When publishing the complete project, organise the repository so that implementation code, tests, configuration, results, and documentation are clearly separated. Do not commit virtual environments, interpreter binaries, caches, or other generated environment files.

## Limitations and responsible use

- This is a simulation-based study. Results depend on the assumptions and parameters encoded in the model.
- Simulated attack outcomes are not observed real-world fraud rates.
- A lower simulated outcome under a protected configuration does not by itself prove that a countermeasure is secure or effective in a deployed election.
- The result summaries alone do not identify the exact countermeasure mechanisms; document those from the implementation rather than guessing.
- Statistical checks support confidence in specific calculations under their stated conditions; they do not prove the entire system correct.
- This project is not a production voting system, a security certification, or a substitute for independent review, formal verification, adversarial testing, and legal or election-specific assurance.

## Technology

The provided archive does not include the source code or dependency manifest, so the complete technology stack cannot be verified from the archive alone. Add the confirmed language, libraries, testing tools, and plotting or analysis packages here after checking the project files.

## Suggested citation

If you use this project in academic work, cite the repository and the accompanying dissertation or report, once its bibliographic details are finalised.

## Author

**Mitali Rananavare**  
MSc Computing Science, University of Glasgow

---

*Research project: mathematical modelling and experimental evaluation of bribery, Sybil, and ballot-stuffing attacks against an electronic voting model.*
