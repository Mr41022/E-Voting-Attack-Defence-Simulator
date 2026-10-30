"""
config.py

Central configuration for parameter ranges used by the randomised
scenario generator (simulation/scenario_generator.py). Editing ranges
here propagates to all experiments; nothing is hard-coded elsewhere.
"""

from __future__ import annotations

SEED = 42
DEFAULT_TRIALS = 2500
MC_TRIALS_PER_SCENARIO = 2000  # Monte Carlo repetitions per paired scenario

# ---------------------------------------------------------------------
# Randomised parameter ranges (uniform unless noted). These bound the
# random sampling in simulation/scenario_generator.py.
# ---------------------------------------------------------------------

PARAM_RANGES = {
    # Election model
    "N": (200, 5000),          # electorate size (int)
    "m_fraction": (0.02, 0.25),  # m sampled as a fraction of N (then rounded)

    # Bribery
    "B": (1000, 200000),       # attacker budget
    "R": (10, 500),            # reward per voter
    "P": (10, 2000),           # penalty if detected
    "q_baseline": (0.02, 0.25),   # baseline detection probability
    "q_protected_boost": (0.15, 0.6),  # additional detection prob. added for protected system

    # Sybil
    "S": (10, 1000),           # attempted fake identities
    "qs_baseline": (0.4, 0.95),   # baseline probability fake identity passes registration
    "qs_protected_reduction": (0.3, 0.8),  # relative reduction in qs for protected system
    "pd_baseline": (0.02, 0.3),   # baseline Sybil detection probability
    "pd_protected_boost": (0.2, 0.7),

    # Ballot stuffing
    "A": (10, 1000),           # attempted fraudulent ballots
    "qb_baseline": (0.3, 0.9),
    "qb_protected_reduction": (0.3, 0.8),
    "pb_baseline": (0.02, 0.3),
    "pb_protected_boost": (0.2, 0.7),
}

# Chernoff / Monte Carlo validation sweep of q values (thesis section 4)
Q_SWEEP = [round(x, 2) for x in
           [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
            0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]]

RESULTS_DIR = "results"
CSV_DIR = f"{RESULTS_DIR}/csv"
JSON_DIR = f"{RESULTS_DIR}/json"
PLOTS_DIR = f"{RESULTS_DIR}/plots"
LATEX_DIR = f"{RESULTS_DIR}/latex"
