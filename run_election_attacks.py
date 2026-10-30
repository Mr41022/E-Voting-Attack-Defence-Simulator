#!/usr/bin/env python3
"""
run_election_attacks.py

Runs the CONCRETE election-attack simulation (real proof-of-work
blockchain, actual vote tallies, actual winner-flip outcomes) -- the
complement to run_experiments.py's abstract P(X>=m) statistics.

Usage:
    python run_election_attacks.py --trials 300 --seed 42
"""
from __future__ import annotations
import argparse
import json
import os
import time

from config import CSV_DIR, JSON_DIR
from simulation.election_attack_runner import run_election_attack_trials


def parse_args():
    p = argparse.ArgumentParser(description="Concrete blockchain election-attack simulation.")
    p.add_argument("--trials", type=int, default=300)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)

    print(f"[run_election_attacks] Running {args.trials} concrete blockchain-backed "
          f"election trials (seed={args.seed})...")
    t0 = time.time()
    df = run_election_attack_trials(n_trials=args.trials, seed=args.seed)
    elapsed = time.time() - t0
    print(f"[run_election_attacks] Done in {elapsed:.1f}s.")

    out_path = os.path.join(CSV_DIR, "election_outcome_results.csv")
    df.to_csv(out_path, index=False)
    print(f"[run_election_attacks] Wrote {out_path} ({len(df)} rows)")

    assert df["chain_valid_after_attack"].all(), "Blockchain integrity check failed on at least one trial!"

    summary = {"total_trials": args.trials, "seed": args.seed, "elapsed_seconds": elapsed}
    flip_rates = {}
    for attack_type in ["bribery", "sybil", "ballot_stuffing"]:
        sub = df[df.attack_type == attack_type]
        baseline_flip = float(sub[sub.system_type == "baseline"]["flipped"].mean())
        protected_flip = float(sub[sub.system_type == "protected"]["flipped"].mean())
        flip_rates[attack_type] = {
            "baseline_flip_rate": baseline_flip,
            "protected_flip_rate": protected_flip,
            "absolute_reduction": baseline_flip - protected_flip,
            "relative_reduction": (baseline_flip - protected_flip) / baseline_flip if baseline_flip > 0 else float("nan"),
        }
    summary["flip_rates"] = flip_rates
    summary["chain_integrity_never_violated"] = bool(df["chain_valid_after_attack"].all())

    summary_path = os.path.join(JSON_DIR, "election_outcome_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print(f"[run_election_attacks] Wrote {summary_path}")

    for atk, v in flip_rates.items():
        print(f"  {atk}: baseline flip rate {v['baseline_flip_rate']:.3f} -> "
              f"protected {v['protected_flip_rate']:.3f} "
              f"({v['relative_reduction']*100:.1f}% relative reduction)")


if __name__ == "__main__":
    main()
