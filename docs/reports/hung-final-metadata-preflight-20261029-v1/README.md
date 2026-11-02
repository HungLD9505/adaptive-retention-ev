# Hùng Final metadata and lock preflight — 29 October 2026

**Status: candidate only; not an executable lock or Final result.** This packet responds to [#23 comment 6476049006](https://github.com/HungLD9505/adaptive-retention-ev/issues/23#issuecomment-6476049006), which records a Hùng-specific lead pre-execution exception. It is **not** independent scientific approval, a merger approval or a waiver of integrity/capacity checks. The comment directs Hùng to freeze an outcome-blind feasible scope, implement a distinct Final runner and preserve shortfalls. [#15](https://github.com/HungLD9505/adaptive-retention-ev/issues/15) still commits each co-lead to 24→24, budgets 7/14/28, at least three comparison seeds, all nine baselines and five ablation categories, accepted UrbanEV plus separately scoped CHARGED cities, own execution, full analysis and an E2E report. None of Qyroven's jobs is counted as Hùng's.

## Metadata-only findings

The repository-local frozen [UrbanEV/SZH input ZIP](../../../.cache/kaggle-payload-v2/payload/inputs.zip) has SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. It contains 18 members for 7/14/28-day inputs. The preflight reads **only** each `manifest.json` and `entities.jsonl` after hashing the ZIP; it never opens `labels.jsonl`, `forecasts.jsonl`, `schedule.jsonl`, `training.jsonl`, runner checkpoints for Final, or any Final score. Entity records contain other coverage fields, but selection uses only the declared Final role and ID. Each budget has exactly **373 Final-role UrbanEV/SZH IDs**, and the sets are identical across budgets. Their input-manifest SHA-256 values are in [summary.json](summary.json).

[urban_final_entity_metadata.csv](urban_final_entity_metadata.csv) lists all 373 IDs, the deterministic hash rank `SHA256("hung-final-urban-candidate-v1|" + entity_id)`, and a **candidate** first-30 flag. The 30-ID option is outcome-blind and mirrors a bounded primary cohort size, but is not selected or approved as Hùng's Final scope. It leaves 343 eligible UrbanEV IDs outside that *option* and cannot be represented as full-population evaluation. The current #15 obligations include separate CHARGED city scopes; this package contains no CHARGED input, so the 30-ID option is not a complete Hùng E2E jobset. No CHARGED IDs or numbers are invented.

The pinned Development portable plan has SHA-256 `b7c79f501230ea5e1308b4bc02b2707089a8c788e4ee3df229aadec005a05198`. [development_source_candidates.csv](development_source_candidates.csv) authenticates **9/9** existing Source checkpoint file and adjacent manifest hashes for budget × seed `7/14/28 × 7/11/19`, and checks each plan cell's input-manifest binding. They are **Development Source reuse candidates**, not automatically accepted Final Source states. No model payload was loaded or refit.

## Required immutable execution lock

The distinct Final runner and the exact Final jobset are still being implemented. A future create-only `hung-final-lock-v1` must pin `scope=final_only`, the executed code commit/source tree, the exact #23 authorization comment ID and `lead_exception_not_peer_approval`, Report 1 head/bootstrap/controller conventions chosen from the written method and Development, frozen config and thresholds, all input ZIP/member/Source identities, an exact `hung-final-jobset-v1` JSON and separate `hung-final-execution-plan-v1` JSON (both byte count and SHA-256), frozen analysis definitions, output root, and `resources` (provider, device, minimum free bytes, estimated GPU seconds/output bytes). `input`, `jobset`, `execution_plan` and `analysis` each use `{path, bytes, sha256}`; `jobset` also has `count`. `source_checkpoints` is a sorted list of reused `{path, bytes, sha256}` entries, every job's Source SHA must match exactly one entry. Every job's dataset/city/entity/budget/seed/method and stage arguments must match across jobset and plan. The executed-source tree must match the pinned code even if the lock document itself is committed later; the worktree must be clean.

For a Target checkpoint **created by Final initialization**, the pre-run jobset value is explicit `null`; the immutable stage receipt records its actual SHA-256 after creation. A non-null Target SHA is allowed only for an explicitly reused, pre-existing checkpoint. No lock field is backfilled after outcome access. Final readback must bind every archive, receipt, manifest, checkpoint, forecast and metric file to that lock; missing or duplicate jobs fail closed. The unresolved Block7 equivalence, trained-state parity, CHARGED attribution and independent #39 readback remain disclosed scientific limitations under the lead exception, not manufactured approvals.

## Concrete blockers and resource snapshot

| Item | Current evidence | Before executable lock/dispatch |
| --- | --- | --- |
| Final input/cohort | 373 UrbanEV/SZH metadata IDs per budget; no CHARGED input package in this repository-local ZIP or file inventory | Pin exact Hùng Final entity IDs for every accepted city and the immutable input/Source identity; declare any shortfall from #15 rather than silently shrinking scope |
| Method/jobset | Development has physical methods and aliases; Final head/bootstrap convention and exact execution plan are not frozen | Resolve correctness contract from Report 1/Development, enumerate exact unique Hùng Final jobs and all stage args, then hash jobset/plan |
| Code/runner | Distinct Final-capable runner is in progress, without a reviewed commit | Finish fixture-tested create-only/resume/readback behavior and pin executed-source hashes |
| Local storage | `Get-PSDrive D` reported **3,827,458,048 free bytes**; existing dispatch reserve is **8,589,934,592 bytes** | Select an output location/provider with measured capacity and adequate margin; no local dispatch under this reserve |
| GPU/provider | Local RTX 3050 Ti: 4,096 MiB total, 3,962 MiB free, driver 592.82. Read-only Kaggle quota query could not start because repo-local venv lacked `kagglehub`; authenticated login is pending. | Measure actual selected provider quota, runtime and output budget without paid scaling or usage reset; stop at a durable boundary if insufficient |

The only failed command was the read-only Kaggle quota probe (`ModuleNotFoundError: kagglehub` before any API call). It neither accessed an account nor submitted work. Do not infer current provider capacity from prior Development runs. No Final/test values were opened, no training or Final job submitted, no old archive modified and no usage reset used.

## Reproduce and file identities

From the repository root, with the frozen ZIP and portable plan present, use a **new** output directory:

```powershell
python -m tools.hung_final_metadata_preflight --root . --output-dir docs/reports/hung-final-metadata-reproduction-NEW
python -m unittest tests.test_hung_final_metadata_preflight -q
```

The tool refuses a changed input ZIP or portable plan hash, duplicate/mismatched Final ID sets, changed Source/checkpoint/manifest hashes, and an existing output directory. `urban_final_entity_metadata.csv`: SHA-256 `512cd9f036832bb5502deb5bed3cda3df5cd1ef0e98023ba97724e8d531a10b7`; `development_source_candidates.csv`: `05035160f3fef3cf58ebdb9f70deec0475ddd8e0d1f2dd55ee6ec6c87b29302f`; `summary.json`: `76add4875ae2120e33646a49d2aea1f4efdc2173c13a9318d63ea935ad2899b2`.

Three focused offline tests, Ruff lint/format, `py_compile`, and `git diff --check` are the packet's checks. This is a metadata preflight, not a passing Final runner or accepted Final lock.
