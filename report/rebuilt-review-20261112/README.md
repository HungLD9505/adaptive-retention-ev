# Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting

The current manuscript is a 16-page Springer Nature two-column report with native
LaTeX equations, seven vector figures, seven tables and nine scientific references.
Comparison tables emphasize the best displayed values within each stated scope.

## Build

Import the source files into Overleaf, select `main.tex` and use pdfLaTeX.
Local compilation and extracted-source verification use Tectonic 0.17.0.
The Overleaf web editor has not been tested.

Both system flows use editable TikZ paths and text. Five result plots are vector
PDFs. No raster images or rendered equation images are required.

## Files

- `main.tex`, `model-equations.tex`, `tables/baselines.tex`: manuscript, mathematics and tables.
- `references.bib`: scientific bibliography.
- `figures/editorial-system-flow.tex`: stable/fast forecasting and delayed-feedback flow.
- `figures/retention-flow.tex`: historical confidence-guided retention selector.
- `figures/*.pdf`: measured result plots.
- `sn-jnl.cls`, `sn-mathphys-num.bst`: original template files.
- `adaptive-transfer-learning-ev.pdf`: compiled reader.
- `artifact-manifest.json`: report and evidence identities.

## Evidence and interpretation

The report separates historical retention selection, common-bank output selection,
continuous/persistent coefficient updates and stable/fast forecast fusion. Their
cohorts, training recipes and evaluation windows remain distinct. All 21 historical
group means appear in the main results.

The [claim-to-evidence register](../../docs/reports/issue99-report-e2e-evidence-20261112/claim-evidence.md)
provides manuscript locations, source files, SHA-256 identities and interpretation
limits. The [E2E verification record](../../docs/reports/issue99-report-e2e-evidence-20261112/README.md)
documents numerical readback, saved-output checks, package compilation and
remaining limitations. These checks do not constitute independent retraining or
an untouched prospective evaluation.
