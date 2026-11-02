# Hùng Final scope: Source checkpoint availability for omitted UrbanEV IDs

**Scope, 30 October 2026.** This read-only audit narrows one prerequisite for a possible extension of the frozen three-station Final. It does not add jobs to the lock, read Final labels, run training, or approve a new cohort. The [machine record](hung-final-scope-source-audit-20261030-v2.json) has SHA-256 `4570150203d98628147ad66182838bafbab3ff211833e8b0ffe7838290041e4c`.

The auditor checked all **nine** existing Development Source checkpoints, one for each 7/14/28-day budget and seed 7/11/19, against the pinned [Source candidate CSV](hung-final-metadata-preflight-20261029-v1/development_source_candidates.csv) SHA-256 `05035160f3fef3cf58ebdb9f70deec0475ddd8e0d1f2dd55ee6ec6c87b29302f`. Each file has the stated byte count and SHA-256, loads with PyTorch `weights_only=True`, has a nonempty model/optimizer state, 64-value latent scale and the expected two-layer hidden-64, 24-to-24 architecture. Its embedded binding declares the matching UrbanEV/SZH budget input manifest, `stage=source` and `entity_id=null`. These are **budget/seed Source checkpoints**, not checkpoints trained for one of the three selected Target stations.

The same nine Source hashes and budget input-manifest hashes agree with all **360** jobs in the immutable Final [jobset](hung-final-candidate-jobset-20261029-v1/candidate_jobset.json), SHA-256 `7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2`. Target-only and Seasonal Naive correctly have no Source checkpoint. The [370 omitted-ID input ledger](hung-final-scope-gap-20261029-v1/scope_gap.csv), SHA-256 `c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681`, still has 326 IDs with `ready`, positive initial training samples and positive scheduled forecasts at **all three** budgets (326/326/330 separately at 7/14/28 days).

Thus, lack of an existing generic Source checkpoint is **not** the limiting prerequisite for those 326 minimal-input IDs under the current Hùng architecture. This does **not** establish method-specific Target initialization, complete-label coverage, metric comparability, provider capacity or scientific authorization. The remaining 44 IDs fail the all-budget minimal-input filter; six CHARGED city scopes are outside this UrbanEV audit. No additional jobset is selected by this result, and the 360-job Final result is not used to choose stations.

Reproduce from the repository root with a new output path:

```powershell
py -3 -m tools.hung_final_scope_source_audit_v1 --output docs/reports/NEW_CREATE_ONLY_PATH.json
py -3 -m unittest tests.test_hung_final_scope_source_audit_v1 -v
```

The script pins source CSV, omitted-ID CSV and immutable jobset hashes, rejects altered checkpoint bytes or identity and writes create-only. Three focused tests pass, including changed Source and jobset fingerprints. The [earlier resource scenario](hung-final-scope-feasibility-20261030-v1.md) remains a sensitivity calculation, not a dispatch plan. A reviewer must decide the extension scope and separately lock its method, identity, analysis and resources before any run.
