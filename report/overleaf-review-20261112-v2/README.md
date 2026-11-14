# Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting

This is the current reader version in the original Springer Nature two-column
format. It uses twelve native LaTeX display equations, a new illustrated method
flow and six scientific data figures. Figure titles are short; explanations
remain separate body paragraphs. Best comparable MAEs are bold, with displayed
ties receiving the same emphasis.

- `main.tex`: select this file in Overleaf; use the pdfLaTeX compiler.
- `references.bib`: eight scientific or dataset references.
- `sn-jnl.cls`, `sn-mathphys-num.bst`: unchanged original template files.
- `figures/`: publication assets referenced by the manuscript.
- `adaptive-transfer-learning-ev.pdf`: compiled reader copy.
- `artifact-manifest.json`: source identities and verification results.

The source ZIP excludes the reader PDF, QA images, logs and experiment artifacts.
Locally, compile with `latexmk -pdf main.tex` or `tectonic main.tex` in a TeX
environment. Local compilation is verified with Tectonic 0.17.0.

The revised charts use the registered calibration locks and independently
verified history summaries; numerical results are unchanged. Their plotting
entry point is `tools/issue99_paper_comparison_charts.py`. Image-generation and
numeric verification records remain outside the paper in
`docs/reports/issue99-figure-revision-20261112/`.
