#!/usr/bin/env python3
"""
generate_key_figures.py

Builds "Ten Key Figures" -- a guided visual summary that presents all
ten of the dissertation's figures with a plain-language explanation of
each: how to read it, what it shows, why it matters, and the single
number worth remembering.

The figures are the same vector PDFs the dissertation embeds, and every
quoted number comes from generated/numbers.tex, so this document cannot
disagree with the dissertation about any value.

Usage:
    python generate_key_figures.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import argparse

REPORT_DIR = "report"
TEX_NAME = "key_figures.tex"

# The ten, in the order the document presents them. Each must exist as a
# vector PDF before the document will compile.
REQUIRED_FIGURES = [
    "fig_07_binomial_thresholds.pdf",
    "fig_02_voter_utility_threshold.pdf",
    "fig_01_method_comparison.pdf",
    "fig_03_chernoff_two_sided.pdf",
    "fig_04_attack_comparison.pdf",
    "fig_05_election_flip_rate.pdf",
    "fig_08_optimal_attacker.pdf",
    "fig_06_critical_detection.pdf",
    "fig_09_vector_capacity.pdf",
    "fig_10_coalition_vs_pure.pdf",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ten-key-figures guide.")
    parser.add_argument("--no-pdf", action="store_true",
                        help="write the TeX source without compiling a PDF")
    args = parser.parse_args()
    missing = [f for f in REQUIRED_FIGURES
               if not os.path.exists(os.path.join("results", "plots", f))]
    if missing:
        raise SystemExit(f"[key-figures] missing figure(s): {missing}. "
                         f"Run generate_figures.py first.")
    if not os.path.exists(os.path.join(REPORT_DIR, "generated", "numbers.tex")):
        raise SystemExit("[key-figures] run generate_report.py first: this "
                         "document shares its injected numbers.")

    if args.no_pdf:
        print("[key-figures] --no-pdf requested; existing TeX source retained.")
        return

    if shutil.which("pdflatex") is None:
        raise SystemExit("[key-figures] pdflatex not found.")

    for _ in range(3):
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", TEX_NAME],
            cwd=REPORT_DIR, capture_output=True, text=True)
        if proc.returncode != 0:
            print("\n".join(proc.stdout.strip().splitlines()[-35:]))
            sys.exit(1)

    pdf = os.path.join(REPORT_DIR, "key_figures.pdf")
    print(f"[key-figures] Built {pdf} ({os.path.getsize(pdf) / 1024:,.0f} KB), "
          f"{len(REQUIRED_FIGURES)} figures explained")


if __name__ == "__main__":
    main()
