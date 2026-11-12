# Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting

This version supersedes the v2 reader after a full method, numerical and layout
audit. The original Springer Nature two-column main text is followed by full-width
appendices. Select `main.tex` and pdfLaTeX in Overleaf. Local compilation uses
Tectonic 0.17.0; the Overleaf web editor itself was not run.

The manuscript has native equations, two native TikZ method diagrams and four
vector result figures. The diagrams separate source initialization, frozen-reference
retention, forecast issuance and complete-label feedback. The controller updates
mixture weights; both expert lambda coefficients remain fixed.

The complete historical table includes Fast-only and marks the lowest displayed
MAE among all five listed methods per group. Baseline and Development tables mark
minima within their stated comparison columns. Underlying experimental values
are unchanged. The full result table, paired baseline plot, recorded trajectories
and calibration curves are in the appendices.

The blue–white–red heatmap palette follows the supplied visual reference.
Blue denotes lower MAE and red higher MAE. The plotted quantity remains MAE
reduction: positive values are blue and negative values red. Diagram colors
distinguish components; they do not encode measured model performance.

Files:

- `main.tex`, `references.bib`: maintained manuscript and nine scientific references.
- `figures/*.tex`: editable method diagrams.
- `figures/*.pdf`: vector plots produced by `tools/issue99_manuscript_figures.py`.
- `sn-jnl.cls`, `sn-mathphys-num.bst`: byte-preserved original template files.
- `adaptive-transfer-learning-ev.pdf`: compiled reader.
- `artifact-manifest.json`: file identities and verification boundaries.

The source-only upload ZIP excludes the reader PDF, manifest, build files,
experiments and QA previews. The fresh numerical/readback audit is documented in
`docs/reports/issue99-manuscript-audit-20261112/`. No raw data or model training is
included in this revision. Existing historical evidence and reader versions remain
preserved, with no change to the frozen Report 1 method or results.
