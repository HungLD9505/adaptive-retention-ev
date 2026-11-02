# Curated evidence

This directory contains technical evidence, explicit limitations and small files still
consumed by verification code/configuration/tests. It is not a current task queue.
The report PDFs and exact tables live under [report/](../../report/README.md).

| Evidence | Read first |
|---|---|
| Primary frozen Final and its limits | [Final handoff](issue23-final-complete-handoff-20261029.md) |
| Primary vs separate supporting evidence | [Joint synthesis](issue23-joint-evidence-synthesis-20261030.md) and [full-precision record](issue23-joint-evidence-synthesis-20261030-v1.json) |
| Posthoc interpretation and report consistency | [Retention analysis](issue23-retention-posthoc-20261031.md), [Report 1 audit](issue23-manuscript-report1-review-20261031.md) |
| Alternate implementation and bounded evaluation | [Latest supporting report](hung-e2e-research-report-draft-20261030-v47.md), [remaining gates](hung-e2e-gate-register-20261030-v70.md) |
| Diagnostic studies | [Fixed adaptation](member-duc-retention.md), [Confidence controller](member-cyber-controller.md) |
| Data and input handoff | [Data integration](data-integration.md), [inputs](input-handoff.md) |
| Software and package validation | [Verification reference](main-readiness-20261102.md), [machine-readable checks](release-curation-20261102-v1.json) |

Earlier progress snapshots, temporary recovery notes and superseded report drafts
are preserved at tag `archive/pre-doc-curation-20261102`, commit
`8cdab1bc096a9c116c7b7f911d548a7621dd81ac`. See the
[archive manifest](../archive-manifest.json) for exact removed paths and hashes.
Some old report versions remain because regression tests deliberately read them;
their presence does not make them current conclusions or accepted Final results.

Retained JSON/CSV bytes are unchanged. Relative Markdown links to archived files
now point to the pinned original snapshot; only navigation was changed in those
historical documents. Original Markdown bytes remain available in the archive tag.
No unfavorable result, null outcome or known limitation was removed from the
canonical report or relabeled as a success.
