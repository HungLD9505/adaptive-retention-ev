# Overleaf research manuscript

This is the current reader version. It uses the same Springer Nature two-column
class as the original report, with native LaTeX equations and a vector TikZ
pipeline for the stable/fast GRU forecast and delayed-feedback loop.

- `main.tex`: main document; select this file in Overleaf.
- `references.bib`: eight scientific or dataset references.
- `sn-jnl.cls` and `sn-mathphys-num.bst`: unchanged original template files.
- `figures/pipeline.tex`: editable pipeline drawing.
- `figures/*.png`: six unchanged scientific result figures.
- `source-retention-review.pdf`: compiled reader copy.
- `artifact-manifest.json`: source identities and verification results.

Upload the source ZIP to a new Overleaf project, select `main.tex`, and use the
pdfLaTeX compiler. Locally, `latexmk -pdf main.tex` builds the document with a full
TeX installation; `tectonic main.tex` is an alternative. Local verification uses
Tectonic 0.17.0. Build logs and intermediate files are excluded from Git.

The numerical tables and twelve scientific display equations are unchanged
from the curated manuscript. Earlier report versions and detailed experiment
provenance remain separate from this reader package.
