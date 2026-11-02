# Shard 12 publication failure and bounded recovery — 2026-10-27

## Observed evidence

The group03 recovery GPU version 362649842 stopped after shard 12 execution and local verification, while submitting its independent CPU readback. Upload acknowledgement alone remains insufficient. The old readback **was created** as version 362681814 and failed in 10.3 seconds because the exact input receipt was missing. Its identity and submission claim must never be retried. Relay04 (362681515) correctly stopped on the parent ERROR; this is not evidence of a relay routing defect.

The private owner Dataset UI exposes version 1, two files, a 452,751,164-byte archive, SHA-256 `d0f7f0335745843adbf16b5c05aafd7fb7a4505ba13c92ab649849677d9b92dc`, and a receipt with execution/verification exit 0, CRC passed and 20 unique jobs. Runtime plan SHA is `34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4`, partition SHA `3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342`; execution wall time 1789.087070955 seconds. These remain receipt claims until independent readback passes.

The owner Code dialog still displayed **awaiting compression**, supporting a publication readiness race as a hypothesis, not a proven root cause. No permission-denied Dataset status/download endpoints were retried. A CPU-only verifier with exact archive and jobset pins was prepared from the existing shard8 verifier. Source SHA `577587fa93cbbe97e6f464e39d35f2ce94e7731713041da6ed35122063e8e14b`. A first Dataset-created draft stalled without any version; a new editor initialized from the ready payload Dataset was used instead, with shard12 explicitly attached. One Save & Run All created **CPU version 362686291**, [reconcile v2](https://www.kaggle.com/code/hungluongduc/hung-shard0012-reconcile-cpu-20261027-v2?scriptVersionId=362686291). Submission is not a completed readback.

## Minimal code correction

`validate_submission` now records returned version, URL, provider error and exact invalid Dataset/Notebook sources before rejecting an incomplete submission. Version 1 can exist even when inputs were rejected; the diagnostic explicitly forbids resubmitting that identity. No retry, storage-readiness assumption, training allocation, model method, historical receipt or live worker source was changed. Regression tests cover rejected Dataset inputs, rejected Notebook inputs, unexpected versions and provider errors.

## Local progress and gates

The local CPU report worker independently generated through-shard_0006: 271 catalog runs (69 historical Main + 202 new), 144 scorable and 127 zero-scored. All snapshot files and input archive/receipt/verification hashes were reread successfully; snapshot receipt SHA `1b005801353a6a113355d4b25331c4243c33e451d4ff3087cd1307c136783684`. Worker processes 35940 and 8124 were observed live. These metrics do not imply complete experiment coverage or independent approval.

GPU Kaggle remains stopped before shard13 pending shard12 independent durability, fresh quota, capacity and parity. Reuse shards8–12; do not retrain them to fix naming or infrastructure. The failed metric coordinator needs an evidence-bound continuation; the portable export coordinator was still shown running and must not be duplicated. Batch00's 80-job verified export and hybrid311 report remain valid historical snapshots. #39 substitution, independent fairness/review, complete Development coverage and immutable Final lock remain pending. No Final labels, merge, promotion or issue closure.

## Validation

Focused queue/storage/recovery suite: 19 tests passed. Ruff lint/format and diff checks passed. Full suite results will be recorded separately after freezing the new commit. The earlier full suite at d434ffc passed 373 tests with one skip; it does not validate this new commit.
