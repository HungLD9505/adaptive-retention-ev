# CHARGED supplementary versus primary run-ID receipt audit — 29 October 2026

**Status:** metadata refinement for independent review; not execution attribution or CHARGED scientific acceptance. This audit extends the [172-ID overlap](hung-charged-lineage-audit-20261028-v1.md) by inspecting receipt objects at the unchanged PR #52 head `377723f5d55a91cde6229807300429365c764117` and six supplementary proof JSONs at the unchanged PR #67 head `c1c62fcb49bdedab42aeb913e8dc3c6821104a57`.

| Evidence | SHA-256 |
| --- | --- |
| PR #52 `issue23-primary-recovery-plan-evidence.json` | `c52031d0f33f19db14667b0059959eea772913ceca26b48fab454d6ddef66815` |
| Existing 172-ID overlap CSV | `dba3deaf5ed3412b9d221b61dbc8771079b07cb99aeb184bfadb43f337093530` |
| New [172-row receipt-binding CSV](hung-charged-pr52-receipt-binding-20261029-v1.csv) | `e7a6bc12cc5db4950e00b13c63a55e8e8e0c88fe0c4cc8eb16d2ef63ad46415a` |

Of the 172 exact run-ID strings appearing in both PRs, **160** also appear in a PR #52 embedded receipt with a declared archive byte count/SHA-256, target code identity and `remote_readback_verified=true`. The remaining **12** are the LOA ID `charged-LOA-201-7d-*-seed42` methods other than Adaptive and block28: PR #52's plan names them, but this tracked evidence has no corresponding receipt object. This is a count of **PR #52 metadata bindings**, not proof that PR #67 reused those 160 physical archives. The CSV lists the exact JSON path for every available receipt and leaves absent values blank.

One overlapping ID has numeric metrics directly present on both sides:

| Run ID | PR #67 proof MAE / RMSE (kWh) | PR #52 publication MAE / RMSE (kWh) |
| --- | ---: | ---: |
| `charged-LOA-201-7d-adaptive-seed42` | 1.1442003942198224 / 1.6620191815006125 | 1.2677443789939085 / 1.6112256974509374 |

The PR #52 values occur at `/loa_first_target_publication`, beside the same run ID and a remote-readback receipt for archive SHA-256 `cc24309d24cd473838b0ce3073d8aec328b6a104f563a6c0771bf5f2887073b5`. The PR #67 values occur in its LOA proof's `runs[]` row. **The MAE and RMSE differ**, so the matching string cannot identify one interchangeable metric record. The reason for the difference is not authenticated here: it could involve a distinct execution/configuration, record derivation or provenance mismatch. Do not overwrite either value or combine the two matrices.

**Method:** read the two immutable Git blobs with `git show`; assert their recorded SHA-256 values and the SHA-256 of every referenced PR #67 proof JSON; traverse PR #52 dictionaries for `receipt.run_ids[]`; require each matching ID to map to at most one embedded receipt; join by exact ID to the existing overlap CSV; export the sorted table create-only. No remote archive, raw data, model or GPU was accessed.

**Reviewer action:** for each proposed Hùng-owned CHARGED result, bind the PR #67 proof row to its own remote version/archive/receipt, Source and Target checkpoints, config/code identity and physical executor; then compare immutable artifact identity to PR #52. Explain the direct LOA metric divergence before any shared-run, independence or cross-city conclusion. Preserve `SUPPLEMENTARY_ONLY`, adverse AMS values and SZH overlap limits until a non-author decision is recorded.
