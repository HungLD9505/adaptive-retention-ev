# Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting

The 13 November evidence review contains 20 pages, native equations, eight vector
figures, ten tables and fifteen scientific references. It adds direct EV
related-work comparisons, paired-entity intervals, shared-calendar sensitivity
and an outcome-blind confirmation-eligibility inventory to the completed studies.

## Build

Import the source files into Overleaf, select `main.tex` and use pdfLaTeX.
The extracted source package is verified locally with Tectonic 0.17.0.
The Overleaf web editor has not been tested. Native TikZ flows remain editable;
result plots are vector PDFs and equations remain LaTeX text.

## Files

- `main.tex`, `model-equations.tex`, `tables/*.tex`: manuscript, equations and native tables.
- `references.bib`: scientific bibliography.
- `figures/editorial-system-flow.tex`: stable/fast forecasting and delayed-feedback flow.
- `figures/retention-flow.tex`: historical confidence-guided retention selector.
- `figures/*.pdf`: six measured-result plots.
- `sn-jnl.cls`, `sn-mathphys-num.bst`: original template files.
- `adaptive-transfer-learning-ev.pdf`: compiled reader.
- `artifact-manifest.json`: report, evidence and build identities.

## Interpretation and evidence

Entity and shared-calendar resampling are posthoc, conditional on the recorded
forecasts and paired seeds. Marginal interval signs are not corrected significance
claims. Undefined sensitivity intervals remain explicit. The metadata inventory
certifies no untouched entity; it does not report a new confirmation experiment.

The [evidence handoff](../../docs/reports/issue117-evidence-20261113/README.md)
contains numeric verification, related-work sources and exposure limits.
The [claim register](../../docs/reports/issue117-evidence-20261113/claim-evidence.json)
maps manuscript paragraphs to evidence, distinguishing inherited verified
statements from the new posthoc analysis and interpretations.
