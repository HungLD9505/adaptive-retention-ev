# Foundation verification — 2026-10-15

## Scope

The repository provides the research flow, collaboration rules, data source catalog, and local archive verification tool for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. [Report 1](../adaptive_retention_report_1.pdf) defines the method; [WORKFLOW](WORKFLOW.md) defines development and review.

## Implemented

- `data/sources.json`: archive URLs/releases, sizes, SHA-256 hashes, publisher checksums, and acquisition provenance.
- `python -m tools.sources list`: list recorded sources without network requests.
- `python -m tools.sources verify`: read local sizes/checksums without downloading or modifying data; failures return nonzero exit codes.
- Catalog, duplicate ID/path, and resolved path guards; tests independent of real datasets.
- Python 3.12, Ruff, Ubuntu/Windows CI, working rules, CODEOWNERS, and PR workflow.

## Verification

Local checks use Python 3.12 with a temporary development environment outside the repository.

| Check | Result |
|---|---|
| Unit fixtures | 9 tests PASS: selection, missing/valid files, size mismatch, same-size corruption, publisher checksums, path guards, and CLI exit codes |
| Archive identities against the acquisition manifest | 3/3 match URLs, sizes, SHA-256, and publisher checksums |
| Report 1 integrity | SHA-256 `cafc1db09a7fda4e196808a96cedf1b18098a4e7ff859d272402e049ebd65bbc` |
| `tools.sources list` | PASS; no data downloaded |
| Ruff and dependencies | Lint/format and pip check PASS |

Check each PR's CI run for its exact commit. Fixture checksum matches verify tool behavior; they do not establish real dataset availability or reproduction.

## Pending work and limits

- Real archives have not been downloaded, extracted, or rehashed in this foundation task. Current endpoint availability is unverified.
- Acquisition/processing pipelines, data audits, model inputs, models, loss/controller, and experiments are not implemented.
- Upstream processing/masks, time/bin/label arrival, and Shenzhen independence require audit. Strict online claims remain unsupported.
- Branch protection is not configured. The executing account has no admin access. CI/CODEOWNERS do not enable enforcement themselves.

## Next phase

Acquire the catalog's raw archives, verify sizes/checksums, and record an acquisition manifest. Implement processing with acceptance criteria, fixtures, and a report under WORKFLOW. Keep dataset identity and run evidence traceable.
