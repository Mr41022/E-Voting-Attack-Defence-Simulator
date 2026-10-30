#!/usr/bin/env python3
"""
check_consistency.py

Verifies that what the project SAYS about itself matches what it IS.

Documentation drift is the failure mode this guards against: the test
suite grows, a figure is added, and a count buried in a README or a
report section quietly becomes wrong. Those errors are invisible to the
test suite (nothing is broken) and highly visible to a reader.

Checks performed:
  1. Test count claimed in prose == number of test functions on disk.
  2. Figure count claimed in prose == number of generated figures.
  3. Figure-range statements (e.g. "Figures 22-29") name the real range.
  4. Every figure the report embeds exists as a vector PDF.
  5. Every LaTeX macro the report uses is defined in numbers.tex.
  6. Headline numbers quoted in README match results/json/summary.json.

Exit code 0 if consistent, 1 otherwise, so it can gate a release.

Usage:
    python check_consistency.py
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

PROSE_FILES = [
    "README.md",
    "MATHEMATICAL_MODEL.md",
    "ASSUMPTIONS.md",
    "report/thesis_report.tex",
    "report/key_figures.tex",
    "report/lit_and_method.tex",
    "report/sections/literature_review.tex",
    "report/sections/methodology.tex",
    "report/sections/experiment.tex",
    "report/sections/findings.tex",
    # Source and side documents drift too: the stale "Figures 22-29"
    # header lived in a .py file, and FIGURE_07_CORRECTION.md carried a
    # stale test count. Both were invisible to this check.
    "visualisation/plots.py",
    "visualisation/threshold_plots.py",
    "generate_figures.py",
    "generate_key_figures.py",
    "FIGURE_07_CORRECTION.md",
    "CHANGES_FROM_REVIEW.md",
    "results/FIGURE_CAPTIONS.md",
]

problems: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def ok(msg: str) -> None:
    notes.append(msg)


# Change logs and correction notes QUOTE superseded values on purpose:
# CHANGES_FROM_REVIEW.md records the stale figure range this script now
# catches, and FIGURE_07_CORRECTION.md records the test count at the time
# of that fix. Scanning them for claims would make this script fail on the
# documents that describe what it caught. They are still scanned for
# everything else; only the two "current value" checks skip them.
#
# Blanking quoted spans instead was tried and rejected: README's repo
# layout lives in a fenced code block and carries a real test-count
# claim, which blanking silently swallowed -- the checker then passed
# while the README was wrong.
HISTORICAL_FILES = {"CHANGES_FROM_REVIEW.md", "FIGURE_07_CORRECTION.md"}


def read(path: str) -> str:
    return read_raw(path)


def read_raw(path: str) -> str:
    """The file as written. Offsets match read()'s output character for
    character, because blanking substitutes spaces rather than deleting,
    so a match position from one can index into the other."""
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


# ---------------------------------------------------------------------
# Ground truth: what the project actually contains
# ---------------------------------------------------------------------

def actual_test_count() -> int:
    """Number of test functions across tests/test_*.py."""
    total = 0
    for path in glob.glob("tests/test_*.py"):
        total += len(re.findall(r"^def (test_\w+)", read(path), flags=re.M))
    return total


def actual_figure_count() -> int:
    return len(glob.glob("results/plots/fig_*.pdf"))


def actual_figure_numbers() -> list[int]:
    nums = []
    for path in glob.glob("results/plots/fig_*.pdf"):
        match = re.search(r"fig_(\d+)_", os.path.basename(path))
        if match:
            nums.append(int(match.group(1)))
    return sorted(nums)


# ---------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------

def check_test_counts(actual: int) -> None:
    pattern = re.compile(r"(\d+)\s+(?:pytest\s+)?tests\b", re.I)
    found_any = False
    for path in PROSE_FILES:
        if path in HISTORICAL_FILES:
            continue
        text = read(path)
        for match in pattern.finditer(text):
            claimed = int(match.group(1))
            # Ignore incidental numbers that are plainly not the suite size
            # (e.g. "200,000-draw"); the suite is in the tens-to-hundreds.
            if claimed < 10 or claimed > 10_000:
                continue
            # Ignore PER-FILE counts. "(10 tests)" following a test module
            # name is a count of that module, not a claim about the suite,
            # and flagging it would force documentation to lie about how
            # many tests a given file holds.
            # Must be a test MODULE filename, not merely the tests/
            # directory: "tests/   119 pytest tests" in the README layout
            # table IS a suite-level claim, and an earlier, looser version
            # of this rule skipped it and let real drift through.
            before = read_raw(path)[max(0, match.start() - 90):match.start()]
            if re.search(r"test_\w+\.py", before):
                continue
            found_any = True
            if claimed != actual:
                line = text[:match.start()].count("\n") + 1
                fail(f"{path}:{line} claims {claimed} tests; the suite has {actual}")
    if found_any:
        ok(f"test count: {actual} (claims checked across prose files)")
    else:
        fail("no prose file states the test count -- expected at least one")


def check_figure_counts(actual: int, numbers: list[int]) -> None:
    for path in PROSE_FILES:
        text = read(path)
        for match in re.finditer(r"(?:all\s+)?(\d+)\s+figures\b", text, re.I):
            claimed = int(match.group(1))
            if claimed < 5:
                continue
            if claimed != actual:
                line = text[:match.start()].count("\n") + 1
                fail(f"{path}:{line} claims {claimed} figures; {actual} exist")
    ok(f"figure count: {actual}")

    if numbers:
        expected_last = max(numbers)
        for path in PROSE_FILES:
            if path in HISTORICAL_FILES:
                continue
            text = read(path)
            for match in re.finditer(r"Figures?~?\s*(\d+)\s*(?:-|--|to)\s*(\d+)", text):
                lo, hi = int(match.group(1)), int(match.group(2))
                line = text[:match.start()].count("\n") + 1
                # ANY endpoint outside 1..expected_last names a figure that
                # does not exist. The earlier version only flagged ranges
                # starting at 1, so a stale "Figures 22-29" left over from
                # the thirty-figure set passed silently -- which is exactly
                # what happened, and was caught in review rather than here.
                if lo < 1 or hi > expected_last or lo > hi:
                    fail(f"{path}:{line} says 'Figures {lo}-{hi}' but figures run "
                         f"1-{expected_last}")
        missing = [n for n in range(1, expected_last + 1) if n not in numbers]
        if missing:
            fail(f"figure numbering has gaps: {missing}")
        else:
            ok(f"figure numbering is contiguous 1-{expected_last}")


def check_embedded_figures_exist() -> None:
    referenced = set()
    for path in PROSE_FILES:
        referenced |= set(re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", read(path)))
    missing = [f for f in referenced if not os.path.exists(os.path.join("results/plots", f))]
    if missing:
        fail(f"report embeds figures that do not exist: {sorted(missing)}")
    else:
        ok(f"all {len(referenced)} embedded figures resolve to files")


def check_macros_defined() -> None:
    numbers_path = "report/generated/numbers.tex"
    if not os.path.exists(numbers_path):
        fail(f"{numbers_path} missing -- run generate_report.py")
        return
    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", read(numbers_path)))
    # LaTeX built-ins and document-local macros that are not injected values.
    local = {"Prob", "Ex", "Bin", "Uv", "figref", "tabref", "eqnref", "code",
             "finhead", "lookat", "shows", "matters", "keynumber", "LaTeX",
             "Large", "LARGE", "Huge", "S", "P", "N", "T", "R", "B"}
    used = set()
    for path in PROSE_FILES:
        text = read(path)
        # Injected macros are CamelCase with no argument, used as \Name{} or \Name
        used |= set(re.findall(r"\\([A-Z][A-Za-z]{3,})(?:\{\}|(?=[\s.,;:)%]))", text))
    undefined = sorted(u for u in used - defined - local
                       if not u.startswith(("begin", "end", "text", "emph")))
    if undefined:
        fail(f"report uses macros not defined in numbers.tex: {undefined}")
    else:
        ok(f"all injected macros used in prose are defined ({len(defined)} available)")


def check_readme_numbers() -> None:
    summary_path = "results/json/summary.json"
    if not os.path.exists(summary_path):
        fail("results/json/summary.json missing -- run run_experiments.py")
        return
    summary = json.load(open(summary_path))
    readme = read("README.md")
    trials = summary["total_trials"]
    if re.search(r"--trials\s+(\d+)", readme):
        claimed = int(re.search(r"--trials\s+(\d+)", readme).group(1))
        if claimed != trials:
            fail(f"README documents --trials {claimed}; summary.json reports {trials}")
        else:
            ok(f"README trial count matches summary.json ({trials})")


def main() -> None:
    tests = actual_test_count()
    figures = actual_figure_count()
    numbers = actual_figure_numbers()

    check_test_counts(tests)
    check_figure_counts(figures, numbers)
    check_embedded_figures_exist()
    check_macros_defined()
    check_readme_numbers()

    print("Consistency check\n" + "=" * 60)
    for note in notes:
        print(f"  OK    {note}")
    if problems:
        print()
        for problem in problems:
            print(f"  DRIFT {problem}")
        print(f"\n{len(problems)} inconsistency(ies) found.")
        sys.exit(1)
    print("\nNo inconsistencies found.")


if __name__ == "__main__":
    main()
