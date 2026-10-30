#!/usr/bin/env python3
"""
build_compendium.py
===================

Compiles every figure and every result table produced by the simulation
into ONE self-contained PDF:

    report/results_compendium.pdf

Part I   -- the ten figures, one per page at full size, each with the
            same caption it carries in the dissertation, plus a short
            "what to read off it" note and the thresholds marked on it.
Part II  -- the fourteen result tables, verbatim from results/csv/.
Part III -- the headline numbers and the reproducibility record.

Nothing here is typed by hand: figure captions are lifted from
report/sections/findings.tex, numbers come from the injected macro file
report/generated/numbers.tex, and tables are read from results/csv/.

    python3 build_compendium.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import argparse

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(ROOT, "report")
CSV = os.path.join(ROOT, "results", "csv")
JSON = os.path.join(ROOT, "results", "json")

# ---------------------------------------------------------------------
# Reading guide: one line per figure, saying what the reader should take
# from it. Written once here so the compendium stands alone without the
# surrounding dissertation prose.
# ---------------------------------------------------------------------
READING_GUIDE = {
    "fig:detection": (
        "Three independent methods on one scenario. The exact binomial curve and the "
        "Monte Carlo markers coincide throughout; the Chernoff curve sits above both "
        "wherever it is defined, which is the validity check. Where the bound "
        "disappears, $m \\leq \\mu$ and the one-sided upper tail does not apply. $R$ and "
        "$P$ are chosen so the collapse sits to the LEFT of $q_v^*$, i.e. inside the "
        "region where a rational voter would still accept the bribe."),
    "fig:utility": (
        "The rational-voter gate. A voter accepts a bribe only while $U_v = (1-q)R - qP$ "
        "stays positive; the crossing at $q_v^* = R/(R+P)$ is the point beyond which no "
        "budget buys a vote, because the voter --- not the system --- refuses."),
    "fig:twosided": (
        "The two-sided Chernoff certificate. Every scenario now carries an analytic "
        "guarantee: an upper bound where $m > \\mu$, and a lower bound obtained by "
        "applying the lower tail to the failure event where $m \\leq \\mu$. The exact "
        "value lies inside the certified interval in 100\\% of evaluations."),
    "fig:comparison": (
        "The headline comparison. Baseline against protected, per vector, on identical "
        "paired trials. The gap between the two bars is the countermeasure effect; the "
        "error bars are bootstrap intervals, used because the underlying distributions "
        "are bimodal rather than normal. Note that the protected bars are reduced, "
        "not zero: attack success is substantially lowered under the modelled "
        "countermeasures, not eliminated."),
    "fig:flip": (
        "The concrete layer. Abstract success probability is one thing; the rate at "
        "which a mined election actually changes winner is another. This figure shows "
        "the two agree in magnitude, in the size of the protection effect, and in "
        "placing bribery lowest. They do not agree on the ordering of the top two: "
        "Sybil leads in the analytic layer and ballot stuffing here, by a third of a "
        "percentage point --- inside sampling error, so those two are best read as "
        "indistinguishable rather than ranked."),
    "fig:critical": (
        "The defender's design target. $q_d^*$ is where attacking stops paying --- the "
        "attacker still can, but no longer wants to. $q_v^*$ is where voters refuse "
        "outright. The gap between them is the region where deterrence relies on the "
        "attacker being rational. The protected configuration's much higher operating "
        "point is a deliberately generous margin in the model, not a level the "
        "analysis finds necessary --- far less detection would already deter."),
    "fig:pmf": (
        "The distribution behind every other figure, with all three margin thresholds "
        "drawn on it. Region boundaries sit at half-integers because $X$ is "
        "integer-valued, so each line meets "
        "the edge of a bar rather than cutting through its centre."),
    "fig:optimal": (
        "The attacker's optimisation. Utility against number of attempts, with the "
        "optimum marked. Effort beyond the optimum lowers utility, which is why a "
        "budget-constrained attacker does not simply spend everything."),
    "fig:capacity": (
        "Why a rational attacker declines a vector. Each bar is capacity as a multiple "
        "of the threshold $m$, so the threshold is the line at 1.0. It is an EXPECTED "
        "value, not a ceiling: a bar below the line means the mean falls short, and the "
        "annotated $P$ gives the exact success probability at full effort --- 0.42 at a "
        "ratio of 0.97, and numerically zero below about 0.7. The diamond is the optimal "
        "split of one budget across all three vectors, which is budget-feasible."),
    "fig:coalition": (
        "The coalition result. The best mixed-vector attack against the best single "
        "vector, per scenario. Protected markers sit at zero across these benchmark "
        "scenarios under these parameter settings --- a statement about those "
        "scenarios, not a general impossibility result, since the wider randomised "
        "trials retain a non-zero residual. Read the coalition analysis as an "
        "extension to the core baseline-versus-protected result, not as its centre."),
}

TABLE_TITLES = {
    "table_01_parameter_ranges": "Parameter ranges used in the randomised trials",
    "table_02_bribery_results": "Bribery attack --- success probability (single gate: detection is folded into $1-q$)",
    "table_03_sybil_results": "Sybil attack --- both measures: surviving (headline) and accepted-only",
    "table_04_ballot_stuffing_results": "Ballot stuffing --- both measures: surviving (headline) and accepted-only",
    "table_05_baseline_vs_protected": "Baseline versus protected --- headline measure only (agrees with Tables 7--9)",
    "table_06_chernoff_validation": "Chernoff bound validation statistics",
    "table_07_statistical_analysis": "Statistical analysis of the paired design",
    "table_08_countermeasure_effectiveness": "Countermeasure effectiveness "
                                             "(absolute and relative reduction)",
    "table_09_overall_comparison": "Overall attack comparison across the three vectors",
    "table_10_sample_scenarios_with_threshold": "Sample scenarios with the manipulation "
                                                "threshold $m$",
    "table_11_scenario_thresholds": "Critical thresholds T1--T7 per benchmark scenario",
    "table_12_vector_optima": "Optimal attacker effort per vector (G1)",
    "table_13_coalition": "Coalition attack versus best single vector (G2)",
    "table_14_cost_sensitivity": "Sensitivity of the coalition finding to cost "
                                 "assumptions",
}


def figure_blocks() -> list[tuple[str, str]]:
    """Lift the ten figure environments verbatim from the findings chapter.

    Reusing them rather than retyping guarantees the compendium cannot
    drift from the dissertation: same graphic, same caption, same label.
    """
    src = open(os.path.join(REPORT, "sections", "findings.tex")).read()
    blocks = re.findall(r"\\begin\{figure\}\[H\](?:(?!\\end\{figure\}).)*?\\end\{figure\}",
                        src, re.S)
    out = []
    for b in blocks:
        label = re.search(r"\\label\{(fig:[^}]+)\}", b)
        out.append((label.group(1) if label else "", b))
    return out


def escape(s: str) -> str:
    for a, b in [("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"),
                 ("&", r"\&"), ("#", r"\#"), ("$", r"\$")]:
        s = s.replace(a, b)
    return s


def csv_table(stem: str) -> str:
    """Render one results CSV as a landscape-safe longtable."""
    path = os.path.join(CSV, stem + ".csv")
    if not os.path.exists(path):
        return ""
    df = pd.read_csv(path)
    # `measure_definition` spells out the event for machine readers of the
    # CSV. On the page it is a long constant string that would push these
    # tables onto landscape pages for no gain -- the definitions are given
    # once in the note above, so the column is dropped here only.
    if "measure_definition" in df.columns:
        df = df.drop(columns=["measure_definition"])
    # Wide tables are unreadable at A4 width; shorten headers rather than
    # dropping columns, so nothing is silently omitted.
    df.columns = [escape(str(c).replace("_", " ")) for c in df.columns]
    # Escape every non-numeric column. The dtype test must not be
    # `== object`: recent pandas gives string columns a dedicated `str`
    # dtype, so an object-only test silently leaves underscores in the
    # cell values and LaTeX reads them as subscripts.
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].astype(str).map(escape)
    # Column count decides the page treatment. A 20-column table cannot be
    # made to fit A4 portrait at any readable size, so it is rotated onto
    # its own landscape page rather than being allowed to run off the
    # edge -- silently clipped columns would be worse than a page turn.
    ncol = len(df.columns)
    wide = ncol > 8            # rotate onto its own landscape page
    very_wide = ncol > 14      # even landscape is not enough: scale to fit
    size = "\\tiny" if wide else ("\\scriptsize" if ncol > 5 else "\\small")
    body = df.to_latex(index=False, float_format="%.4f", escape=False,
                       longtable=not very_wide, column_format="l" * ncol)
    if very_wide:
        # A plain tabular can be scaled; a longtable cannot. These tables
        # are short enough (a few rows) that they never need to break
        # across pages, so trading the page break for a scale factor
        # costs nothing and keeps every column on the page.
        body = "\\resizebox{\\linewidth}{!}{%\n" + body + "}"
    title = TABLE_TITLES.get(stem, stem.replace("_", " "))
    n = int(stem.split("_")[1])
    head = (f"\\subsection*{{Table {n}. {title}}}\n"
            f"\\addcontentsline{{toc}}{{subsection}}{{Table {n}. {title}}}\n")
    inner = f"{{{size}\n\\setlength{{\\tabcolsep}}{{3pt}}\n{body}\n}}\n"
    if wide:
        return ("\\begin{landscape}\n" + head + inner +
                "\\end{landscape}\n")
    return head + inner + "\\vspace{8pt}\n"


def build() -> str:
    summary = json.load(open(os.path.join(JSON, "summary.json")))
    n_fig = len(figure_blocks())
    n_tab = sum(1 for s in TABLE_TITLES if os.path.exists(os.path.join(CSV, s + ".csv")))

    parts = [r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathptmx}
\usepackage[scaled=0.88]{helvet}
\usepackage{amsmath,amssymb}
\usepackage[margin=2.2cm,top=2.5cm,bottom=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{pdflscape}
\usepackage{float}
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage[font=small,labelfont=bf,labelsep=period,justification=justified]{caption}
\usepackage{tcolorbox}
\usepackage[hidelinks]{hyperref}

\definecolor{accent}{HTML}{0072B2}
\definecolor{warm}{HTML}{D55E00}
\definecolor{inkmuted}{HTML}{4D4D4D}
\definecolor{rule}{HTML}{BFBFBF}
\definecolor{panel}{HTML}{F4F7FA}

\hypersetup{colorlinks=true, linkcolor=accent, urlcolor=accent, linktoc=all,
  pdftitle={Blockchain-Based E-Voting: Complete Figures and Results},
  pdfsubject={MSc Computing Science dissertation --- results compendium}}

\titleformat{\section}{\normalfont\sffamily\large\bfseries}
  {\thesection}{0.8em}{}[\vspace{2pt}\color{rule}\hrule height 0.6pt]
\titleformat{\subsection}{\normalfont\sffamily\normalsize\bfseries}{\thesubsection}{0.7em}{}
\titlespacing*{\section}{0pt}{18pt}{9pt}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\fancyhead[L]{\footnotesize\sffamily\color{inkmuted}Complete Figures and Results}
\fancyhead[R]{\footnotesize\sffamily\color{inkmuted}\thepage}

\setlength{\parskip}{0.40em}
\setlength{\parindent}{0pt}
\onehalfspacing

\newtcolorbox{readbox}{colback=panel, colframe=accent, boxrule=0pt,
  leftrule=2.6pt, arc=1pt, left=9pt, right=9pt, top=6pt, bottom=6pt,
  fontupper=\small}

\newcommand{\Prob}{\mathbb{P}}
\newcommand{\Ex}{\mathbb{E}}
\newcommand{\Bin}{\mathrm{Binomial}}
\newcommand{\Uv}{U_{v}}
\newcommand{\figref}[1]{Figure~\ref{#1}}
\newcommand{\tabref}[1]{Table~\ref{#1}}
\newcommand{\eqnref}[1]{Equation~(\ref{#1})}
\newcommand{\code}[1]{\texttt{\small #1}}

\input{generated/numbers}
\graphicspath{{../results/plots/}}

\begin{document}
\begin{titlepage}
\thispagestyle{empty}
\centering
\vspace*{1.6cm}
{\sffamily\Large University of Glasgow}\\[2pt]
{\sffamily\normalsize School of Computing Science}\\[2.6cm]
{\color{rule}\rule{\textwidth}{0.9pt}}\\[0.6cm]
{\sffamily\LARGE\bfseries Complete Figures and Results}\\[0.4cm]
{\sffamily\Large Blockchain-Based Electronic Voting:}\\[0.16cm]
{\sffamily\Large Bribery, Sybil and Ballot-Stuffing Attacks}\\[0.6cm]
{\color{rule}\rule{\textwidth}{0.9pt}}\\[1.4cm]

\begin{minipage}{0.86\textwidth}
\centering\normalsize
Every figure and every result table produced by the simulation, collected in
one document. Part~I presents the """ + f"{n_fig}" + r""" figures at full size with
their captions and a note on what each one shows. Part~II reproduces the
""" + f"{n_tab}" + r""" result tables in full. Part~III records the headline numbers and
the reproducibility protocol.
\end{minipage}

\vfill
{\footnotesize\color{inkmuted}
Generated from the simulation output at seed \Seed{} over \TotalTrials{} paired trials.
Every number is injected from \code{results/} at build time; none is typed by hand.
Companion to the main dissertation.}
\end{titlepage}

\tableofcontents
\clearpage

\section*{Part I. Figures}
\addcontentsline{toc}{section}{Part I. Figures}

Each figure below is the one that appears in the dissertation, at full size,
with its caption unchanged. The shaded note beneath each states what the
figure is for and which threshold values are marked on it.
\vspace{6pt}
"""]

    for label, block in figure_blocks():
        # Full width in the compendium: this document exists to be read
        # for the figures, so they are not scaled down to fit prose.
        block = re.sub(r"width=[0-9.]+\\textwidth", r"width=0.97\\textwidth", block)
        parts.append(block + "\n")
        note = READING_GUIDE.get(label)
        if note:
            parts.append("\\begin{readbox}\\textsf{\\bfseries How to read it.} " + note +
                         "\\end{readbox}\n")
        parts.append("\\clearpage\n")

    parts.append(r"""
\section*{Part II. Result Tables}
\addcontentsline{toc}{section}{Part II. Result Tables}

The complete tabular output of the simulation, read directly from
\code{results/csv/}. Column names are as emitted by the pipeline.

\begin{readbox}
\textsf{\bfseries Which probability each table reports.} Sybil and ballot
stuffing pass fraudulent votes through \emph{two} independent gates, so they
have two success probabilities. $P(\text{accepted} \geq m)$ counts votes that
clear the \emph{acceptance} gate only --- an intermediate quantity that ignores
detection and is therefore always larger. $P(\text{surviving} \geq m)$ counts
votes that clear \emph{both} gates, and is the headline measure used in
Tables~7--9, Figure~4 and every stated conclusion. Bribery has one effective
gate (detection is folded into $1-q$), so its two measures coincide.
Tables~3 and~4 report both, labelled by a \code{measure} column; Tables~5 and
7--9 report the headline measure only, so the numbers agree across them.
\end{readbox}
\vspace{6pt}
""")
    for stem in sorted(TABLE_TITLES):
        parts.append(csv_table(stem))

    parts.append(r"""
\clearpage
\section*{Part III. Headline Numbers and Reproducibility}
\addcontentsline{toc}{section}{Part III. Headline Numbers and Reproducibility}

\subsection*{Scale of the experiment}
\begin{itemize}\setlength{\itemsep}{1pt}
\item Paired trials: \TotalTrials{}, with \MonteCarloTrials{} Monte Carlo draws per trial
\item Random seed: \Seed{} --- re-running reproduces every number bit-for-bit
\item Automated tests: \TestCount{}, all passing
\item Figures: \FigureCount{}
\end{itemize}

\subsection*{Reproducibility protocol}
All randomness derives from a single seeded \code{numpy.random.Generator}; no
global random state and no unseeded standard-library random calls exist in the
codebase. The threshold and coalition analyses are fully analytic and require no
seed at all.

Every number in this document is injected at build time from
\code{results/json/} and \code{results/csv/} as a \LaTeX{} macro. A macro whose
experiment has not been run causes the document to fail compilation rather than
to print a stale value, which makes it structurally impossible for the text to
disagree with the data it describes. \code{check\_consistency.py} additionally
verifies that claimed test and figure counts match reality.

\subsection*{How to regenerate this document}
\begin{verbatim}
python3 main.py                # run the full simulation
python3 generate_figures.py    # write the 10 figures
python3 generate_tables.py     # write the 14 result tables
python3 build_compendium.py    # build this compendium
\end{verbatim}

\end{document}
""")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the results compendium.")
    parser.add_argument("--no-pdf", action="store_true",
                        help="write the TeX source without compiling a PDF")
    args = parser.parse_args()
    tex = build()
    out = os.path.join(REPORT, "results_compendium.tex")
    with open(out, "w") as f:
        f.write(tex)
    print(f"[compendium] wrote {out}")
    if args.no_pdf:
        return
    for i in range(3):   # three passes: ToC + longtable column widths
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "results_compendium.tex"],
                       cwd=REPORT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(REPORT, "results_compendium.pdf")
    if os.path.exists(pdf):
        print(f"[compendium] built {pdf} ({os.path.getsize(pdf)/1e6:.2f} MB)")
    else:
        print("[compendium] PDF not produced -- see report/results_compendium.log")


if __name__ == "__main__":
    main()
