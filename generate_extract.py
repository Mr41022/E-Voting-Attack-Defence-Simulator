#!/usr/bin/env python3
"""
generate_extract.py

Builds a standalone, presentable PDF containing only the Literature
Review and the Research Design and Methodology chapters --- the extract
a supervisor or reviewer is typically shown before the full
dissertation exists.

The two chapters are NOT rewritten for this document. They are the same
source files the full report uses (report/sections/*.tex), passed
through one preprocessing step that rewrites cross-references pointing
at chapters this extract does not contain. A reference such as
"Section~\\ref{sec:findings}" would otherwise compile to "Section ??",
which looks like an error rather than a deliberate extract; it becomes a
named reference to the chapter instead ("the Findings chapter").

Keeping one source for both documents means the extract cannot drift
away from the dissertation: editing a chapter updates both.

Usage:
    python generate_extract.py            # preprocess and compile
    python generate_extract.py --no-pdf   # preprocess only
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

REPORT_DIR = "report"
SECTION_DIR = os.path.join(REPORT_DIR, "sections")
OUT_DIR = os.path.join(REPORT_DIR, "generated", "extract")
TEX_NAME = "lit_and_method.tex"

# Cross-references to chapters this extract does not carry. Each entry is
# (regex over the source, replacement). Whitespace is matched loosely with
# \s+ because the source is hard-wrapped and a reference can straddle a
# line break.
REWRITES: list[tuple[str, str]] = [
    # --- literature review -------------------------------------------
    (r"Section~\\ref\{sec:limitations\}\s+returns\s+to\s+this\.",
     r"The \\emph{Limitations} chapter of the full dissertation returns to this."),
    (r"as\s+Section~\\ref\{sec:findings\}\s+reports,",
     r"as the \\emph{Findings} chapter reports,"),
    (r"the\s+critical-detection\s+threshold\s+of\s+Section~\\ref\{sec:thresholds\}\s+is",
     r"the critical-detection threshold developed in this work is"),
    (r"reported\s+in\s+Section~\\ref\{sec:findings\},\s+that\s+identity\s+verification",
     r"reported in the \\emph{Findings} chapter, that identity verification"),
    (r"\(Section~\\ref\{sec:coalition-model\}\),\s+which\s+are\s+otherwise",
     r"(described in the methodology below), which are otherwise"),
    (r"margin\s+of\s+Section~\\ref\{sec:thresholds\}\s+a\s+security\s+claim",
     r"margin defined in this work a security claim"),
    (r"Section~\\ref\{sec:thresholds-results\}\s+shows\s+that\s+a",
     r"the \\emph{Findings} chapter shows that a"),
    (r"Sections~\\ref\{sec:model\}\s+and~\\ref\{sec:findings\}\s+supply\s+exactly\s+that,",
     r"The \\emph{Threat Model} and \\emph{Findings} chapters supply exactly that,"),
    (r"Section~\\ref\{sec:thresholds\}\s+formulates\s+seven\s+such\s+thresholds\s+and\s+solves\s+them\.",
     r"The \\emph{Critical Thresholds} chapter formulates seven such "
     r"thresholds and solves them."),
    (r"Section~\\ref\{sec:coalition\}\s+shows\s+this\s+omission",
     r"The \\emph{Coalition Attacks} chapter shows this omission"),
    # --- methodology --------------------------------------------------
    (r"\(Section~\\ref\{sec:coalition-model\}\);\s+the\s+threshold\s+solvers",
     r"(Section~\\ref{sec:method-coalition}); the threshold solvers"),
    # "(see the ...)" rather than "(reported in the ...)": several of these
    # sit inside sentences that already contain the word "reported".
    (r"\(Section~\\ref\{sec:findings-methods\}\)\.",
     r"(see the \\emph{Findings} chapter)."),
    (r"\(Section~\\ref\{sec:exp-sensitivity\}\)\.",
     r"(see the \\emph{Findings} chapter)."),
    (r"Section~\\ref\{sec:findings-concrete\}\s+reports\s+that\s+they\s+agree\s+in\s+both\.",
     r"The \\emph{Findings} chapter reports that they agree in both."),
    (r"Section~\\ref\{sec:coalition\}\.\s*\\\\",
     r"the coalition analysis. \\\\"),
    (r"\\figref\{fig:detection\}\s+therefore\s+holds\s+every\s+other",
     r"the detection-sweep figure of the \\emph{Findings} chapter therefore "
     r"holds every other"),
    (r"\\figref\{fig:chernoff\};\s+none\s+occurs\s+across",
     r"the bound-validation figure of the \\emph{Findings} chapter; none "
     r"occurs across"),
    (r"\(Section~\\ref\{sec:findings-concrete\}\)\.",
     r"(see the \\emph{Findings} chapter)."),
]

DANGLING = re.compile(
    r"\\(?:ref|figref|tabref|eqnref)\{("
    r"sec:(?:model|thresholds|thresholds-results|coalition|coalition-model|"
    r"findings|findings-methods|findings-concrete|exp-sensitivity|limitations)"
    r"|fig:(?:chernoff|detection)"
    r")\}")


def preprocess(name: str) -> str:
    """Apply the rewrites to one chapter and verify none was missed."""
    src = open(os.path.join(SECTION_DIR, name)).read()
    for pattern, replacement in REWRITES:
        src = re.sub(pattern, replacement, src)

    leftover = DANGLING.findall(src)
    if leftover:
        raise SystemExit(
            f"[extract] {name}: unresolved cross-reference(s) to omitted "
            f"chapters: {sorted(set(leftover))}. Add a rewrite rule in "
            f"generate_extract.py rather than letting the PDF print '??'.")

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, name)
    with open(out_path, "w") as fh:
        fh.write(src)
    return out_path


def compile_pdf() -> str | None:
    if shutil.which("pdflatex") is None:
        print("[extract] pdflatex not found -- skipping PDF compilation.")
        return None
    for _ in range(3):
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", TEX_NAME],
            cwd=REPORT_DIR, capture_output=True, text=True)
        if proc.returncode != 0:
            print("\n".join(proc.stdout.strip().splitlines()[-35:]))
            return None
    pdf = os.path.join(REPORT_DIR, TEX_NAME.replace(".tex", ".pdf"))
    return pdf if os.path.exists(pdf) else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the standalone extract")
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(os.path.join(REPORT_DIR, "generated", "numbers.tex")):
        raise SystemExit("[extract] run generate_report.py first: the extract "
                         "shares its injected numbers.")

    for name in ("literature_review.tex", "methodology.tex"):
        print(f"[extract] preprocessed {preprocess(name)}")

    if not args.no_pdf:
        pdf = compile_pdf()
        if pdf:
            print(f"[extract] Built {pdf} ({os.path.getsize(pdf) / 1024:,.0f} KB)")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
