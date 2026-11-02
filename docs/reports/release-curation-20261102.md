# Curated release tree — 2 November 2026

Refs #15; continues the integrated source candidate and diagrams without promoting
main. This is a documentation/package cleanup, not a new experiment or method.

## What changed

- Integrated the three source-backed diagrams through #81; README now presents the
  research task, system overview, report links, descriptive results, reproduction
  commands, code map and four-member source attribution.
- Added the unchanged exported main/supplement PDFs (about 2.5 MB combined), checked
  against the existing `report/verification.json`. This is not a new compilation.
  All 17 original source-package assets remain byte-identical.
- Archived 564 of the original 719 tracked files under `docs/reports/`. Retained
  155 historical files: 39 Markdown, 87 JSON and 29 CSV. The remaining older draft
  versions have actual test/code/config consumers; they are not current conclusions.
- Added documentation and evidence indexes. Retained historical Markdown links to
  archived files now address their original pinned GitHub snapshot. Source/report
  conclusions and retained machine-readable result bytes are not edited.

Before removal, the complete remote tag `archive/pre-doc-curation-20261102` was
verified at `8cdab1bc096a9c116c7b7f911d548a7621dd81ac`. The
[archive manifest](../archive-manifest.json) records original path, size and SHA-256
for every removed file, original hashes/reasons for retained files and navigation
edits. Restore original bytes with `git show <tag>:<path>`; no history was rewritten.
This preserves adverse/null evidence and original attribution.

## Main inclusion decision

The candidate includes the primary packages, separate member implementations,
versioned configs/utilities, offline tests, report PDFs/source/results, three
vector diagrams, data/causality contracts and curated provenance. Superseded
operational documents stay in the archive tag. Datasets, environments, checkpoints,
large runs and preview/build files remain outside Git. Original numerical method,
cohorts, seeds, labels and source lock are unchanged.

Main still requires a separate instruction. Use a merge commit to preserve all
four source histories; do not squash the integrated history into one author.
The draft main PR should identify the current dev SHA after this curation merges.
Its existence does not establish final delivery or close #15.

## Verification boundary

The initial static checks authenticated archive bytes and retained machine-readable
evidence, report source/PDF identities, all diagram source-reference bounds and
local Markdown destinations. A historical metadata README still names an ignored
`.cache/.../inputs.zip` as an external artifact; this cleanup neither reconstructs
nor claims to verify it. All navigation to newly archived files points to the
pinned snapshot rather than a missing local target.

Clean-checkout test/lint/release results are recorded after execution. No real-data
training, artifact download, fresh PDF compile, remote CI success or independent
peer approval is implied. The lead's paid-CI/non-author-review exceptions remain
explicit. Previously documented scientific gaps and the 18 external-artifact tests
remain unverified; retiring their scope does not fulfill their original criteria.
