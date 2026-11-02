# Hùng Final scope: Source lineage and Target prefix metadata for omitted IDs

**Scope, 30 October 2026.** This read-only audit extends the [first Source availability audit](hung-final-scope-source-audit-20261030-v1.md) with the Source run manifests and Target initialization metadata from the **same frozen input ZIP**. It does not read Final labels or scores, run training, select an extension cohort, or alter the 360-job lock. The [machine record v4](hung-final-scope-source-audit-20261030-v4.json) has SHA-256 `11b443ea1f0ad2f3b8394d75590aba4c55a7c1138256230707f941c4c6e0e0d6`. Earlier exploratory v3 bytes remain preserved in ignored `.cache` and are superseded by this versioned v2 auditor output.

All **nine** budget/seed Source checkpoint files pass the pinned byte/SHA, PyTorch `weights_only=True` and model-state checks reported in v1. This audit additionally reads each adjacent `run_manifest.json`: its checkpoint SHA and full input binding equal the checkpoint payload and pinned Source candidate row. The Source binding has `entity_id=null` and the budget-specific manifest SHA used by the immutable 360-job Final jobset. Thus the Source checkpoint and **required CLI run-manifest lineage** are both physically available for the original Hùng method, without claiming the omitted Target adaptations have executed.

The frozen 151,254,390-byte `inputs.zip` is authenticated by SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7` and the original lock. The auditor independently reconciles the 370 omitted ID set, all three budget input-manifest hashes and every status/initial-count/forecast-count cell with its `entities.jsonl` members. Among the **326/326/330** IDs passing the minimal input filter at 7/14/28 days, every corresponding entity declares `initialization=target_initial_adaptation` and a nonempty frozen `scale.fit_sha256`. Exactly **326** IDs meet these metadata conditions at all three budgets.

This closes **Source checkpoint/run-manifest availability and Target-prefix metadata** as specific prerequisites. It does **not** validate the actual Target training-example contents or labels, guarantee a successful adaptation/replay for each method, bind a new Target checkpoint, establish statistical power, authorize GPU capacity, or decide whether broader UrbanEV/CHARGED coverage is scientifically required. The remaining 44 omitted IDs fail the all-budget minimal filter; no held-out outcome is used to choose the 326. The 40-job-per-ID resource scenario remains unapproved and prohibitively large as currently written.

Reproduce create-only from the repository root:

```powershell
py -3 -m tools.hung_final_scope_source_audit_v2 --output docs/reports/NEW_CREATE_ONLY_PATH.json
py -3 -m unittest tests.test_hung_final_scope_source_audit_v2 -v
```

The auditor pins the [Source candidate CSV](hung-final-metadata-preflight-20261029-v1/development_source_candidates.csv), [370-ID ledger](hung-final-scope-gap-20261029-v1/scope_gap.csv), [360-job set](hung-final-candidate-jobset-20261029-v1/candidate_jobset.json), frozen lock and ZIP. Four focused regressions pass, including altered Source bytes, altered jobset and altered Source run-manifest rejection. An independent reviewer must determine the extension scope and a separately locked protocol before execution.
