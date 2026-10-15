# Foundation handoff — 2026-10-15

## Goal and scope

Create a clean working tree for rebuilding processing and developing later phases through review. The previous codebase, commit `528680dd73791322ed12f32b2c72a3b58618a428`, is preserved on remote branch `master`. Git history was not rewritten and `main` was not force-pushed.

This report records the foundation proposal on `feat/research-foundation`, before merge. At that point, Master Flow PR #3 replaced PR #2 after a branch rename and was reviewed separately. Subsequent integration is recorded in [merged foundation PR #4](https://github.com/HungLD9505/adaptive-retention-ev/pull/4) and [merged flow PR #3](https://github.com/HungLD9505/adaptive-retention-ev/pull/3). Current development rules are in [WORKFLOW](WORKFLOW.md).

## Preserved inputs

- Report 1, byte-for-byte, SHA-256 `cafc1db09a7fda4e196808a96cedf1b18098a4e7ff859d272402e049ebd65bbc`.
- URLs/releases, byte sizes, SHA-256 hashes, and publisher checksums for the three archives in the 2026-10-02 acquisition manifest: UrbanEV main, optional supplemental, and CHARGED standard Hourly.
- Provenance pointing to the exact historical commit/manifest path, distinguishing team-observed hashes from publisher checksums.

Old Data/Input code, processed data, window indices, reports, and PASS flags were not carried forward as new pipeline code or evidence. They remain accessible through the backup and Git history. No raw directories existed in the checkout at task start; no raw files were modified or deleted.

## Implemented foundation

- `data/sources.json` and instructions for acquiring the correct archives, local paths, and source limitations.
- `python -m tools.sources list`: list recorded sources without network requests.
- `python -m tools.sources verify`: read local size/SHA-256/publisher checksums without downloading or modifying data; failures return nonzero exit codes.
- Catalog, duplicate ID/path, and resolved path guards; unit fixtures independent of real datasets.
- Python 3.12, virtual environments, and exactly pinned Ruff; old processing/ML dependencies were not carried forward.
- Ubuntu/Windows CI covering the catalog, tests, lint, format, and diff checks; actions pinned to commit SHAs.
- AGENTS, CODEOWNERS, PR template, ignore rules, and the review workflow in effect at the foundation proposal.
- LF text handling; binary/raw checksums are unaffected by text line-ending conversion.

## Local verification at foundation handoff

Commands ran from the repository root using Python 3.12 with a temporary development environment outside the repository.

| Check | Result |
|---|---|
| Unit fixtures | 9 tests PASS: selection, missing/valid files, size mismatch, same-size corruption, publisher checksums, path guards, and CLI exit codes |
| Archive identities against the historical manifest | 3/3 match URLs, sizes, SHA-256, and publisher checksums |
| Report 1 against the pre-reset `origin/main` | Identical bytes and hash |
| `tools.sources list` | PASS; no data downloaded |
| Ruff, dependencies, links, and diff | PASS: lint/format, pip check, local document links, and git diff --check |
| GitHub CI at report creation | Pending execution/review then; workflow configuration alone was not treated as a successful run |

Tests use synthetic bytes, not actual dataset ZIPs, and do not demonstrate download availability. Fixture checksum matches verify tool behavior only. Later CI evidence is available in the merged PRs linked above; it does not prove data reproduction.

## Limitations

- Real archives were not downloaded, extracted, or rehashed. Download endpoints retain historical provenance; current availability is not asserted.
- No new acquisition/processing pipeline, data audit, model inputs, model, loss/controller, or experiments were implemented.
- Upstream processing/masks, time/bin/label arrival, and Shenzhen independence still require audit. Strict online claims remain unsupported.
- Branch protection was not configured: the executing account lacks admin access and the API reported private-repository ruleset restrictions. CI/CODEOWNERS do not enable enforcement themselves.
- Team-wide method understanding and environment setup were not verified. Peer review was required before merging the proposal.

## Next handoff

After foundation review/merge, acquire or restore the correct raw archives on a separate branch, verify sizes/checksums, and record a new acquisition manifest. Then implement new processing with acceptance criteria, fixtures, and its own report under the current WORKFLOW. Do not alter expected hashes to accept a different release or mark later phases complete using historical evidence.
