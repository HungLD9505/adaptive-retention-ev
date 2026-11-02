# Prepared compact Kaggle per-job proof route — 28 October 2026

**Status:** prepared and locally exercised; no new Kaggle verification job was submitted. This is a bounded route to close the 560 Kaggle rows still lacking reviewable per-job bytes in the [v2 Development ledger](hung-development-782-ledger-audit-20261028-v2.md). It does not change or rerun any of the 782 training jobs.

The live saved [group08 GPU output](https://www.kaggle.com/code/hungluongduc/hung-matched-group08-44b8532-20261027-v2/output), version `362902889`, visibly contains shard0035/0036 `artifacts.zip`, `receipt.json`, `execution.json` and logs. Its page reports 5.85 GB total output; shard0035's archive is 949,818,304 bytes with SHA-256 `44b2d40372948ffc98c7a19398d1e707df095bb2bb16a56d11b04db1`. The saved receipt lists the exact 20 job IDs, byte count, archive SHA, CRC `passed`, and execution/verifier exit codes zero. This UI observation is a saved-shard inventory, **not** a fresh archive-byte or per-job proof.

## Route

Use the existing eight saved GPU execution outputs: shard0001 alone; groups containing 0002–0003, 0008–0013, 0014–0019, 0020–0025, 0026–0028, 0033–0034 and 0035–0036. For each output, a distinct CPU-only verifier can mount the **exact saved version** and the pinned payload, then stream each shard archive rather than extracting or downloading all output files. It must pin the saved-version ID and independently read the matching CPU archive-readback record before publishing a compact proof. Run at most one such verifier while the CPU metrics/export route is active, to avoid competing for provider capacity.

The new [streaming verifier](../../tools/hung_kaggle_compact_proof.py) accepts the canonical parent plan/partition, the provider's derived plan/partition, one archive and its pinned SHA/byte count. It compares scientific job/cell/config/source/target pins across parent and provider plans, checks the exact shard jobset, hashes the compressed archive, runs full ZIP CRC verification including unreferenced members, checks job/stage receipt SHA and every referenced member/log SHA, and validates completed run manifests. It emits one small row per job with receipt and stage-manifest hashes using exclusive file creation. Caller-supplied version IDs are recorded as **claims**, not independently authenticated by this local tool; the saved Kaggle source list and readback proof must establish that binding.

The local smoke exercised the verifier on the existing 48,346,859-byte shard0039 archive without training. It produced 16 rows, and all 16 receipt and manifest hashes exactly matched the already committed v2 ledger. The output remains ignored at `.cache/recovered-shards-v2/shard_0039/compact-proof-local-test.json`; it is a test of the verifier, not one of the 560 missing Kaggle jobs.

After adding full ZIP CRC verification, a repeat positive check passed for the 16-job shard0039. Three negative checks also rejected the expected fault: an incorrect archive SHA, a foreign shard jobset, and a run manifest with a corrupted completion status. The manifest test intercepted the in-memory ZIP read and changed only the returned JSON; it did not alter saved files. `python -m py_compile` and `git diff --check` passed. These local checks do not establish provider-version authenticity or validate a Kaggle archive.

The tracked offline [regression tests](../../tests/test_hung_kaggle_compact_proof.py) use a synthetic one-job ZIP and no ignored `.cache` inputs. `python -m unittest tests.test_hung_kaggle_compact_proof -v` passed 4/4: one valid proof and rejection of wrong archive SHA, foreign receipt jobset, and failed manifest despite matching receipt hashes.

## Required acceptance before a v3 ledger

1. Review the verifier and freeze a new CPU proof notebook/source hash with the eight exact saved GPU version IDs, CPU readback version IDs, archive hashes/sizes and disjoint shard IDs. Verify mounted source versions through the provider before opening outputs.
2. Execute on existing saved outputs only; no GPU or training command. Save each compact proof under a new run ID and independently read back its bytes/SHA. Reject any missing, duplicate or foreign job, wrong plan/config/input/Source/Target, failed status, member CRC or SHA mismatch.
3. Import the compact proof rows into a **new** ledger snapshot with a status distinct from `VERIFIED_LOCAL_BYTES`, preserving v1/v2 CSVs. Review every job → saved version → archive → receipt → manifest hash and the exact 560-row set. Only then can the per-job gate be considered for acceptance.

The current proof route is **not yet remotely run**. No 560-row result, remote version binding, full metrics or Final acceptance is inferred from this preparation.
