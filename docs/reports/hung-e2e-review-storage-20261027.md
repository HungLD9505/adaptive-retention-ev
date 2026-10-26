# Hung review evidence storage — October 27, 2026

Refs #10, #15, #22, #23 and #39. Addendum to the
[earlier handoff](hung-e2e-execution-handoff-20261027.md); its ledger, logs,
hashes and historical scope remain preserved.

The 212,497-byte review bundle and 419-byte transport map were uploaded to
[Private Kaggle review storage](https://www.kaggle.com/datasets/hungluongduc/hung-e2e-review-gates-44b8532-20261027-v1),
version 1. The authenticated page confirmed **Private** and listed both files.
It also retained the saved description linking PRs #70/#71, the original
bundle SHA, suffix/CRC instructions and outstanding acceptance gates.

**Remote SHA/CRC readback is pending.** After refreshing the Dataset page,
Kaggle still displayed `Download dataset as zip (awaiting compression)`.
Upload success and visible filenames are not evidence that downloaded bytes
match the source. No remote hash, restore or teammate-reproduction pass is claimed.

| File | Expected bytes | Expected SHA-256 |
| --- | ---: | --- |
| `e2e-review-bundle-v1.zip.bin` | 212,497 | `7e088184c279fed43c3f7cfc2a312e1400e44baa4aceb0fcf5c0bd826d4267eb` |
| `transport-map.json` | 419 | `aed7fc2f2e38cf08bac3be345e4cc2f1dfdd70dbced46b46e61db0f86afdf8d8` |

The `.bin` suffix preserves the original ZIP bytes through Kaggle upload.
The bundle has 94 members: plan/config/ledger/log/reproduction evidence,
without raw data, labels, forecasts or model checkpoints. It is a review
package, not a GPU capacity result or an execution approval.

The [storage observation](evidence/hung-e2e-review-storage-20261027.json)
records privacy, file expectations, the still-pending readback and actual
local verification commands. The small
[stdlib verifier](evidence/verify_review_download_20261027.py) accepts either
the eventual two-file Dataset ZIP or a project-local directory containing
both files. It checks exact size/SHA for both files, ZIP CRC, and uniqueness
of all 94 inner members; paths and outputs stay inside the project and old
reports are not overwritten. Verification failure writes no success report.

Actually run: the verifier accepted the original local staging directory
(exit 0) and rejected a separate copy with one byte changed (exit 1, no
success output). Ruff lint/format passed. These checks validate the worker
and local source package only. They are not remote readback. The preceding
277-test suite and actual-input dry-run apply to unchanged implementation
commit `44b8532`; this addendum does not retrain or change that plan.

When the download is available, save it inside the supplied repository and run
from this documentation worktree:

```powershell
python docs/reports/evidence/verify_review_download_20261027.py `
  --download .cache/review-download-v1.zip `
  --output .cache/review-remote-readback-v1.json
```

Pair that output with the actual download URL/version and receipt. The
verifier intentionally does not infer remote origin from an arbitrary local
path. Reviewer account access and bounded independent teammate reproduction
remain separate requirements.

The [recorded #39 request](https://github.com/HungLD9505/adaptive-retention-ev/issues/39#issuecomment-6425183225)
still awaits a non-author decision on the Colab substitute and Block-7
fairness. No approval appeared in the inspected #39/#70/#71 discussions.
GPU pilot, the 782 new jobs, Final lock and Final evaluation remain unexecuted.

This addendum adds exactly the Markdown report, storage JSON and verifier
script listed above. The original report/evidence files are unchanged.
