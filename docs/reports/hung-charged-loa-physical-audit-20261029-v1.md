# CHARGED LOA colliding run ID — physical PR #52 archive audit

**Scope, 29 October 2026:** one overlapping Development run ID, `charged-LOA-201-7d-adaptive-seed42`. This extends the [metadata/receipt audit](hung-charged-pr52-receipt-binding-20261029-v1.md). It does not certify the other 171 colliding IDs or all six cities, and does not turn supplementary CHARGED results into independent Hùng Final evidence.

## Source bytes and checks

| Source | Identity and verification |
| --- | --- |
| [PR #67 LOA proof](https://github.com/HungLD9505/adaptive-retention-ev/blob/c1c62fcb49bdedab42aeb913e8dc3c6821104a57/docs/reports/issue23-charged-loa-development-verification-v2.json) | Git blob at `c1c62fc`, SHA-256 `cb454462ccd10710d83086e119629674d4d9f730782659749219637032961ee5` |
| [PR #52 recovery evidence](https://github.com/HungLD9505/adaptive-retention-ev/blob/377723f5d55a91cde6229807300429365c764117/docs/reports/issue23-primary-recovery-plan-evidence.json) | Git blob at `377723f`, SHA-256 `c52031d0f33f19db14667b0059959eea772913ceca26b48fab454d6ddef66815` |
| [PR #52 independent proof ZIP](https://drive.google.com/file/d/1D3PwdC8mRSTl4ESMDp201qen48Ox3TuA/view) | 11,292 bytes, SHA-256 `3f2ba5eb36af82751304586395c3b8bd47b2dd9eb04bacf9931c8bb47e0a93f9`; ZIP CRC and embedded receipt/verification hashes checked |
| [PR #52 physical target archive](https://drive.google.com/file/d/1NVFIpDSSJLOfTvZsb6u45amf5WnEEduu/view) | 12,584,285 bytes, SHA-256 `cc24309d24cd473838b0ce3073d8aec328b6a104f563a6c0771bf5f2887073b5`; outer and nested run ZIP CRC passed; contains the target's binding, 90 forecast days and terminal run record |
| New [machine comparison](hung-charged-loa-physical-audit-20261029-v1.json) | 1,924 bytes, SHA-256 `b14422f643a0fb0033370bcd88c86384c99d0f774cfd0ad20b06d295bd60758b` |

The PR #52 publication receipt binds the downloaded archive's exact bytes/SHA and code commit `aa9f91cdc828e0d48c693a26b306208ec41de640`. The nested physical `binding.json` and `run.json`, the independent proof ZIP and the PR #52 recovery evidence agree on that identity. The PR #67 proof and PR #52 proof both declare input manifest SHA-256 `cb09d9d5c751b3bc1fcbad79ef548800c33e1506e6863f2600f88b167ac5e384`; their manifest, entity and label file byte/SHA records also match. Both record 90 issued and 90 scored days. This establishes a common declared input snapshot and coverage, not identical model state or forecasts.

| Field | PR #67 proof | PR #52 physical archive/proof |
| --- | --- | --- |
| Matrix SHA-256 | `a9cc73055694711e1471c0485bd178a5d0872f700f469319dd8e465b9bbc85ec` | `f1ea041e6eee3eae3bf9a35ae0dcc985163ad006bcb55f6a195aaee081969bb8` |
| Run commit chain | `0076f67bff82557e74b42cf4a8fc97c6511e0edcacbaa3fb5e1e686d8843bcd2` | `cf9d73b380af2ae0afe1c4f3d43331955ad5632981d84c6887becc06faaff972` |
| MAE / RMSE, kWh | 1.1442003942 / 1.6620191815 | 1.2677443790 / 1.6112256975 |
| Physical archive/code/Source binding in this audit | Absent | Archive SHA above; code `aa9f91c`; Source checkpoint SHA `ca703dc98859cefc8ac9145a97970c0b0c2f083eb07fcc39d56fd417d3d1b419` |

The PR #52 minus PR #67 MAE difference is **+0.123543985 kWh** and the RMSE difference is **−0.050793484 kWh**. Since the matrix hashes and run chains differ, the two same-named rows are **different recorded trajectories** and cannot be deduplicated as one physical experiment or averaged as replications. The audit does not establish *why* they differ: PR #67's physical archive, code/config/Source checkpoint and executor are not bound by its proof JSON. Its origin hash cannot be compared directly to the PR #52 proof, which does not publish the same origin-hash field; schedule equality is not claimed.

## Reproduce and review disposition

The [read-only auditor](../../tools/hung_charged_loa_physical_audit_v1.py) pins both Git blobs and the downloaded ZIP SHA-256 values; it checks outer/nested ZIP CRC, receipt-to-archive/code binding, input file identities, run/coverage/metric consistency and the two commit chains. The binary ZIPs remain in ignored repository `.cache`, outside Git. With those two exact files present:

```powershell
python -m tools.hung_charged_loa_physical_audit_v1 --proof-zip .cache/hung-charged-loa-pr52-review-20261029-v1/independent-proof.json --archive .cache/hung-charged-loa-pr52-review-20261029-v1/target-archive.bin --output .cache/hung-charged-loa-pr52-review-20261029-v1/reproduction-new.json
python -m unittest discover -s tests -p test_hung_charged_loa_physical_audit_v1.py -v
```

The output path must not exist. A separate create-only rerun matched the published JSON SHA. Reviewer should either bind PR #67's own physical output to its declared row and explain the divergent trajectory, or mark the PR #67 row unverified for any shared-run/independence claim. Keep both original values, adverse AMS results and `SUPPLEMENTARY_ONLY` status until a non-author city-level decision is recorded. No training, GPU or Final lock was changed.
