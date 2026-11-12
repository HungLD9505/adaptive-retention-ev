# Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting

Current report: 16 pages in the original Springer Nature two-column template.
Select `main.tex` and pdfLaTeX in Overleaf. Local verification uses Tectonic 0.17.0;
the Overleaf web editor itself was not exercised.

Figure 1 is a restrained native LaTeX/TikZ system figure: white background,
flat tensor/GRU/forecast graphics, consistent typography and light blue/red
categorical accents. All seven figures are vector; there are no raster images
or rendered equation images in the reader. Titles are short and descriptions
are in the body. Comparison tables bold the best displayed values within their
stated scope.

## Source files

- `main.tex`, `model-equations.tex`, `tables/baselines.tex`: text, native mathematics and tables.
- `references.bib`: nine scientific references.
- `figures/editorial-system-flow.tex`: editable E2E system figure.
- `figures/retention-flow.tex`: separate historical confidence selector.
- `figures/*.pdf`: five vector result plots.
- `sn-jnl.cls`, `sn-mathphys-num.bst`: unchanged original template files.
- `adaptive-transfer-learning-ev.pdf`: compiled reader.
- `artifact-manifest.json`: asset, evidence and verification identities.

The report distinguishes the original retention selector, common-bank selection,
continuous/persistent coefficient updates and the stable/fast fusion extension.
All numerical evidence and experimental scopes are unchanged by this visual
revision. The full 21-group historical table remains in the main results.

The source-only ZIP contains compilation inputs plus this README; it excludes
the reader, manifest and QA files. See the current [visual revision handoff](../../docs/reports/issue99-editorial-flow-20261112/README.md)
and the earlier [evidence-based rewrite](../../docs/reports/issue99-report-rebuild-20261112/README.md).
