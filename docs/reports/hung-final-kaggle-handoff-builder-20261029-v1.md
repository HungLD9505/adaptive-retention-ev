# Hùng Final Kaggle handoff builder — 29 October 2026

**Prepared code and synthetic tests only.** No executable Hùng Final lock exists, no real Final input ZIP was extracted, no private Dataset was created, and no Kaggle API was called.

`experiments.hung_sprint2.final_handoff` accepts an exact SHA-pinned `hung-final-lock-v1` only after it exists. It runs the lock validator without opening Final-role run files. The validator authenticates the code commitment, input ZIP bytes, Source checkpoint bytes, jobset, execution plan, analysis specification, coverage, resources and Hùng-specific #23 authorization. The builder then requires the Kaggle wrapper bytes at the pinned Git commit to equal the working source and verifies each adjacent Source `run_manifest.json` binds its checkpoint SHA. It creates a fresh Git bundle and copies the lock, jobset, execution plan, analysis, frozen input ZIP, nine applicable Source checkpoints and adjacent manifests to a **new ignored repository-local** packet. Every mounted filename receives an exact byte length, SHA-256 and create-only checkout target in `final-handoff-manifest.json`; the wrapper source SHA and requested private Dataset version `owner/slug/1` are pinned there too. The builder does not upload or submit the packet.

The future executable lock files and Source/input artifacts must be under ignored `.cache` paths. This matches the current lock generator's planned layout and lets the Kaggle checkout remain clean for `final_lock._code_unchanged`. A tracked analysis file must first be copied byte-identically to an ignored lock packet and pinned there; the builder will refuse a non-`.cache` overlay. The wrapper will independently hash all mounted bytes before checkout or Final-role extraction. Existing packet paths, changed references, missing/extra files, wrong pinned commit, unsafe paths and duplicate target paths fail closed; an interrupted packet remains for inspection and is never overwritten.

When a reviewed lock, authenticated provider quota/storage and private Dataset route are available, a human operator can prepare a new packet with:

```powershell
python -m experiments.hung_sprint2.final_handoff --lock .cache/hung-final-lock-NEW/lock.json --lock-sha256 EXACT_SHA --dataset-version owner/new-private-slug/1 --packet .cache/hung-final-handoff-NEW
```

This command is intentionally **not run** against the candidate 360-row jobset: that candidate has no executable lock or accepted Kaggle capacity. A prepared packet would still require create-once private Dataset upload, provider version authentication, full exact-jobset execution or a separately reviewed partial-checkpoint path, local archive and independent remote SHA/CRC readback. The Hùng-specific lead exception does not resolve scientific parity, Block7 or CHARGED coverage.

Offline checks: three synthetic builder tests cover exact packet, changed/missing/extra bytes, duplicate packet, unsafe output path and wrong code commit; three earlier wrapper tests cover mount and quota refusal. No test reads Final/test data or calls Kaggle.
