# Research manuscript 12 November 2026

The reader manuscript contains the research question, methods, experiments,
results, limitations and eight scientific or dataset references.

- [PDF](source-retention-review.pdf): rendered reading copy.
- [Word](source-retention-review.docx): editable text, tables and twelve native
  Word equations (OMML). The six embedded images are scientific figures.
- [Markdown source](manuscript.md) and `figures/`: maintained content and figure assets.
- `artifact-manifest.json`: file identities and document verification results.

The numerical results are unchanged from the 11 November manuscript. The
separate [evidence handoff](../../docs/reports/issue99-teacher-review-20261111/handoff.md)
retains experiment identities, audit records and full-precision companion tables;
these operational records are not part of the paper's scientific references.

Rebuild with the bundled document runtime (python-docx, lxml and Pillow), plus
the pinned converters in `requirements-document-math.txt`:

```sh
BUNDLED_PYTHON tools/issue99_review_docx.py --root report/teacher-review-20261112
BUNDLED_PYTHON DOCUMENT_SKILL/render_docx.py \
  report/teacher-review-20261112/source-retention-review.docx \
  --output_dir NEW_RENDER --emit_pdf
```

Inspect every rendered page before replacing the delivered PDF. Only the final
reader PDF and editable Word file are needed when submitting the manuscript.
