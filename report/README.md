# Research manuscript sources

Current reader version: [Overleaf-style PDF](overleaf-review-20261112-v3/adaptive-transfer-learning-ev.pdf)
and [LaTeX project](overleaf-review-20261112-v3/README.md). It follows the original
Springer Nature two-column layout, includes the current causal pipeline, and uses
short figure titles with explanations in the body. Select `main.tex` in Overleaf.

## Original frozen report

This is the canonical LaTeX source for the report delivered on 31 October 2026.
It supersedes the earlier thesis outline in PR #54.

Read the exported [main report](Adaptive_Retention_Report.pdf) and
[supplement](Adaptive_Retention_Supplement.pdf) directly. These are the unchanged
31 October exports authenticated by `verification.json`, not newly compiled PDFs. The report distinguishes the
primary UrbanEV/CHARGED evaluation from the separate supporting implementation.

- Main document: `retention-manuscript-v8.tex`.
- Supplement: `retention-supplement-v8.tex`.
- Exact result lookups: `full-results.csv`, `switch-audits.csv`.
- Springer Nature class/bibliography style and every referenced figure are included.

Import these files into Overleaf and select the corresponding main document, or
compile each document with a LaTeX installation containing the required packages.
The source names retain their original version identifiers to preserve references.
No text, numerical result or figure bytes were changed during repository packaging.

`manifest.json` records the original source ZIP identity and the exact hashes of
all 17 copied files. The original export records a 14-page main report and a six-page
supplement; its compile verification is preserved in `verification.json`. This
cleanup did **not** perform a new LaTeX compilation or claim a new PDF layout check.
The methodology PNG is the same original-resolution image embedded in that export.

Experimental evidence/provenance remains in `docs/reports/` and the frozen execution
lock in `configs/issue23/`; large runs, checkpoints and data are outside Git. The
primary historical scientific source is preserved at tag
`evidence/primary-final-20261027-v2`, commit
`61c32328d9829a69037dca629f727b4863015122`. Later verifier hardening does not replace
or relabel the report's frozen run outputs.

## Earlier review drafts

[11 November integrated manuscript](teacher-review-20261111/README.md) includes
verified independent baseline evidence, the Fixed-share formula, all 21 historical
groups, scientific figures and explicit ensemble/controller ablations. This is a
separate exploratory review version; the frozen release files above are preserved.
