# Teacher review manuscript 11 November 2026

This is the current review version, integrating baseline verification, the
Fixed-share controller equations, the complete 21-group historical comparison,
and six scientific figures. The earlier review version and frozen primary
Report 1 remain preserved.

- `source-retention-review.pdf`: eleven-page rendered review manuscript.
- `source-retention-review.docx`: editable body and tables; equations are high
  resolution images with their LaTeX source in `manuscript.md`.
- `manuscript.md`: complete maintained manuscript source.
- `figures/`: six figures in PNG/PDF plus twelve equation images.
- `full-scope-results.csv`: all 21 groups and all original comparator arms, with
  posthoc equal-weight and loss-free-sharing controls appended.
- `full-scope-cells.csv`: all 810 units, preserving nine unscored/null units.
- `trajectory-data.csv` and `trajectory-selection.json`: figure source values,
  deterministic example selection and verified artifact identities.
- `artifact-manifest.json`: byte identities for the review bundle.

Evidence and baseline acceptance boundaries are in
[`docs/reports/issue99-teacher-review-20261111`](../../docs/reports/issue99-teacher-review-20261111/handoff.md).
This version is ready for teacher review; it does not claim peer approval,
untouched Final confirmation, or universal GRU/controller superiority.

Rebuild figures with the model-analysis environment and document with the bundled
workspace Python, then render and inspect every page:

```
python -m tools.issue99_review_figures --output report/teacher-review-20261111 \
  --full-run FULL_SCOPE_RUN
BUNDLED_PYTHON tools/issue99_review_docx.py --root report/teacher-review-20261111
BUNDLED_PYTHON DOCUMENT_SKILL/render_docx.py \
  report/teacher-review-20261111/source-retention-review.docx \
  --output_dir NEW_RENDER --emit_pdf
```

The PDF delivered here is the render of the delivered DOCX, not a separately
laid out document. Local render images are QA intermediates outside Git.
