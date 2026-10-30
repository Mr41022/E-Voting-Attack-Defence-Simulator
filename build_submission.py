#!/usr/bin/env python3
"""
build_submission.py
===================

Builds the SINGLE submission PDF:

    report/submission.pdf

    cover page (candidate details)
  + the full dissertation
  + Appendix: the complete figures-and-results compendium

This is one LaTeX build rather than a merge of two finished PDFs, so the
table of contents, the PDF bookmarks and the page numbers run
continuously through the whole document.

How it works
------------
`report/thesis_report.tex` and `report/results_compendium.tex` are both
complete standalone documents. This script takes the preamble from the
thesis (the compendium's is a subset plus `pdflscape`), takes the BODY of
each, and concatenates them under one `\\begin{document}`.

Two things have to be handled or the build breaks or misleads:

1. Duplicate labels. The appendix repeats each figure, and each repeat
   carries the same `\\label{fig:...}` as the inline original. Left alone,
   LaTeX warns and every `\\ref` silently retargets the appendix copy.
   The labels are stripped from the appendix copies.
2. The compendium's own title page and table of contents are dropped;
   the submission has one of each.

Candidate details are supplied on the command line and typeset on the
cover page. With none given the cover keeps the "to be completed"
placeholder rather than inventing anything.

    python3 build_submission.py \\
        --author "Name" --student-id "1234567" \\
        --supervisor "Dr X" --date "September 2026" \\
        --degree "MSc Computing Science"
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(ROOT, "report")


def read(name: str) -> str:
    with open(os.path.join(REPORT, name), encoding="utf-8") as f:
        return f.read()


def split_document(tex: str) -> tuple[str, str]:
    """Return (preamble, body) either side of the document environment."""
    b = tex.index("\\begin{document}")
    e = tex.rindex("\\end{document}")
    return tex[:b], tex[b + len("\\begin{document}"):e]


def strip_titlepage_and_toc(body: str) -> str:
    """Drop the compendium's own front matter."""
    body = re.sub(r"\\begin\{titlepage\}.*?\\end\{titlepage\}", "", body, flags=re.S)
    body = body.replace("\\tableofcontents", "")
    return body


def strip_figure_labels(body: str) -> str:
    """Remove \\label{fig:...} from the appendix copies of the figures.

    Without this, every label is defined twice: LaTeX takes the LAST
    definition, so every \\figref in the dissertation would quietly point
    at the appendix reprint instead of the inline figure. The appendix is
    referred to as a whole, so its figures need no labels of their own.
    """
    return re.sub(r"\\label\{fig:[^}]*\}\s*", "", body)


COVER = r"""
\begin{titlepage}
\thispagestyle{empty}
\centering
\vspace*{1.0cm}

{\sffamily\Large University of Glasgow}\\[2pt]
{\sffamily\normalsize School of Computing Science}\\[2.6cm]

{\color{rule}\rule{\textwidth}{0.9pt}}\\[0.65cm]
{\sffamily\LARGE\bfseries Blockchain-Based Electronic Voting}\\[0.40cm]
{\sffamily\Large Mathematical Modelling and Experimental Evaluation of}\\[0.16cm]
{\sffamily\Large Bribery, Sybil and Ballot-Stuffing Attacks}\\[0.65cm]
{\color{rule}\rule{\textwidth}{0.9pt}}\\[1.1cm]

{\large A game-theoretic and probabilistic security evaluation,}\\[3pt]
{\large with exact binomial analysis, Chernoff bounds and}\\[3pt]
{\large critical-threshold identification}\\[1.8cm]

%%CANDIDATE%%

\vspace{1.2cm}
\begin{minipage}{0.86\textwidth}
\centering\small
This document contains the complete dissertation together with a full
appendix of every figure and every result table produced by the
simulation. All results are generated from the accompanying code
(seed \Seed, \TotalTrials{} paired trials per vector) and are
reproducible bit-for-bit; \TestCount{} automated tests pass and
\code{check\_consistency.py} reports no drift between the text and the
data it describes.
\end{minipage}

\vfill
{\footnotesize\color{inkmuted}
No real election system, voter record or personal datum is used anywhere in this work.}
\end{titlepage}
\clearpage
"""

PLACEHOLDER = r"""\begin{minipage}{0.8\textwidth}
\centering\itshape
Author, supervisor and submission date to be completed by the candidate.
\end{minipage}"""

APPENDIX_INTRO = r"""
\clearpage
\section{Complete figures and result tables}
\label{app:compendium}

This appendix reproduces every figure in the dissertation at full size,
each with a short note on how to read it, followed by the complete
tabular output of the simulation --- all fourteen result tables exactly
as written by the pipeline to \code{results/csv/}.

The figures appear twice by design. In the body they are sized to sit
inside the argument that uses them; here they are given a page each, so
that individual values, thresholds and annotations can be read directly
off the axes. Nothing in this appendix is retyped: the figures are the
same vector PDFs, and the tables are read from the result files.
"""


def build_candidate_block(args) -> str:
    """Typeset whichever details were supplied; placeholder if none."""
    lines = []
    if args.author:
        lines.append(r"{\sffamily\Large " + args.author + r"}\\[0.30cm]")
    if args.student_id:
        lines.append(r"{\normalsize Student number: " + args.student_id + r"}\\[0.55cm]")
    if args.degree:
        lines.append(r"{\sffamily\large " + args.degree + r"}\\[0.22cm]")
    lines.append(r"{\sffamily\normalsize Dissertation}\\[0.55cm]")
    if args.supervisor:
        lines.append(r"{\normalsize Supervisor: " + args.supervisor + r"}\\[0.22cm]")
    if args.date:
        lines.append(r"{\normalsize " + args.date + r"}")
    if not (args.author or args.supervisor or args.date or args.student_id):
        return PLACEHOLDER
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="")
    ap.add_argument("--student-id", default="")
    ap.add_argument("--supervisor", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--degree", default="MSc Computing Science")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()

    thesis = read("thesis_report.tex")
    comp = read("results_compendium.tex")

    preamble, thesis_body = split_document(thesis)
    _, comp_body = split_document(comp)

    comp_body = strip_figure_labels(strip_titlepage_and_toc(comp_body))

    # The compendium rotates its widest tables onto landscape pages.
    if "pdflscape" not in preamble:
        preamble = preamble.replace("\\usepackage{longtable}",
                                    "\\usepackage{longtable}\n\\usepackage{pdflscape}")
    # A compendium-only box environment used by its figure notes.
    if "newtcolorbox{readbox}" not in preamble:
        preamble = preamble.replace(
            "\\newcommand{\\finhead}",
            "\\newtcolorbox{readbox}{colback=panel, colframe=accent, boxrule=0pt,\n"
            "  leftrule=2.6pt, arc=1pt, left=9pt, right=9pt, top=6pt, bottom=6pt,\n"
            "  fontupper=\\small}\n\n\\newcommand{\\finhead}")

    preamble = preamble.replace(
        "pdfsubject={MSc Computing Science dissertation}",
        "pdfsubject={MSc Computing Science dissertation --- submission copy}")

    # The thesis body opens with its own title page; the submission uses
    # the cover below instead, so that one is dropped.
    thesis_body = re.sub(r"\\begin\{titlepage\}.*?\\end\{titlepage\}", "",
                         thesis_body, count=1, flags=re.S)

    cover = COVER.replace("%%CANDIDATE%%", build_candidate_block(args))

    # The compendium body ends with its own "Part III" reproducibility
    # section, which duplicates the dissertation's. Drop it.
    cut = comp_body.find("\\section*{Part III.")
    if cut != -1:
        comp_body = comp_body[:cut]

    out = (preamble + "\\begin{document}\n" + cover + thesis_body
           + APPENDIX_INTRO + comp_body + "\n\\end{document}\n")

    path = os.path.join(REPORT, "submission.tex")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"[submission] wrote {path}")

    if args.no_pdf:
        return
    for _ in range(3):          # toc, refs, longtable widths
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "submission.tex"],
                       cwd=REPORT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(REPORT, "submission.pdf")
    if os.path.exists(pdf):
        print(f"[submission] built {pdf} ({os.path.getsize(pdf)/1e6:.2f} MB)")
    else:
        print("[submission] PDF not produced -- see report/submission.log")


if __name__ == "__main__":
    main()
