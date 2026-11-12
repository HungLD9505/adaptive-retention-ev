# Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting

This is a rewritten report based on the completed experiments and their existing
evidence. It supersedes the previous reader, without changing any experiment,
method implementation, training run, scoring window or historical export.

Select `main.tex` and pdfLaTeX in Overleaf. The original Springer Nature class
and bibliography style are preserved byte for byte. Local verification uses
Tectonic 0.17.0; the Overleaf web editor itself has not been exercised.

The report follows the forecasting problem, source transfer, GRU/loss equations,
fixed-coefficient calibration, retention controllers, two-expert fusion, and
separate experimental results. The complete 21-group historical comparison is
in the main results. Seven figures include an illustrated E2E figure with editable TikZ wiring,
a native historical flow and five vector result plots. Equations are native LaTeX. Figure captions are short; explanatory
text is in the body. Comparison tables bold the best displayed values within
the stated comparison. The blue-white-red palette distinguishes favorable and
adverse MAE reductions; component colors in flows are categorical.

The report distinguishes the original confidence-gated selector, the independent
common-bank selector, continuous and persistent coefficient updates, and adaptive
fusion. It reports the 18/21 fusion result alongside the static fusion's 18/21
result and the adaptive-vs-static 12/21 result. The favorable discrete Later and
28-day common-bank results are retained together with adverse outcomes. No result
from another cohort fills an unexecuted cell.

## Files

- `main.tex`, `model-equations.tex`, `tables/baselines.tex`: report text and native equations/tables.
- `references.bib`: scientific references; repository participants are not bibliography entries.
- `figures/*.tex`: editable historical flow and vector wiring for the illustrated system.
- `figures/illustrated-system-artwork-v1.png`: the illustration layer; compile its TikZ wrapper to see the complete figure.
- `figures/*.pdf`: vector fixed-sensitivity, backbone, calibration, comparison and trajectory plots.
- `adaptive-transfer-learning-ev.pdf`: compiled reader.
- `artifact-manifest.json`: source/evidence identities and verification scope.

The source-only ZIP contains only files needed to compile, plus this README.
Large run artifacts and preview images remain outside Git. Old reader versions
and the frozen original report are preserved.

Evidence, numerical checks and validation limitations are recorded in
[the rewrite handoff](../../docs/reports/issue99-report-rebuild-20261112/README.md).
The subsequent [E2E flow revision](../../docs/reports/issue99-system-flow-20261112/README.md)
replaces the separate model/feedback sketches with Figure 1 of the current system.

The [illustration revision](../../docs/reports/issue99-illustrated-flow-20261112/README.md)
replaces the plain Figure 1 artwork with isometric charging sites, sequence cards
and GRU pictograms. Calendar inputs bypass the encoders, the frozen reference
feeds retention only, and model/weight feedback routes are explicit. Equations
in the article remain native LaTeX; plotted result figures remain vector.
