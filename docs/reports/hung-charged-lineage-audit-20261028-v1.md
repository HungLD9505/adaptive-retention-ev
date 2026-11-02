# CHARGED supplementary lineage audit — 28 October 2026

**Status: bounded metadata comparison for reviewer, not attribution or scientific acceptance.** This audit compares the six tracked proof JSONs at [PR #67 commit `c1c62fc`](https://github.com/HungLD9505/adaptive-retention-ev/pull/67) with tracked metadata at [PR #52 commit `377723f`](https://github.com/HungLD9505/adaptive-retention-ev/pull/52). It did not read raw data, Source/Target checkpoints, remote provider execution logs, Final inputs or the external original matrices. The older [six-city descriptive result](hung-charged-supplementary-proof-summary-20261028.md) remains unchanged.

## Source identities and checks

PR #67 contains six `issue23-charged-*-development-verification-v2.json` proofs, 378 unique run IDs per city (2,268 total). Each top-level proof contains `status`, `matrix_sha256`, `runs` and `input_authentication`. Each run contains a run ID, MAE/RMSE, chain/origin hashes and completion counts. None of these proof JSON fields identifies the remote executor or directly supplies the run's Source checkpoint SHA-256, exact execution config SHA-256 or code SHA-256. The PR description says the matrices came from a supplementary Hùng branch and depend on the Qyroven primary analysis; Git author and that prose alone cannot authenticate remote executor ownership.

The three PR #67 input manifest hashes per city exactly equal the corresponding 7/14/28-day hashes in PR #52's tracked `issue22-execution-evidence.json`: **18/18 matches** across MEL, SZH, AMS, JHB, SPO and LOA. The PR #52 JSON is SHA-256 `f96d24969023ab60c462b6f1e8e20694d54f64be6542c4a6044e934e30aa0169` at `377723f`. This establishes common declared input-manifest identities, not common Source states, identical output bytes or independent execution.

The PR #52 `issue23-primary-recovery-plan-evidence.json` (SHA-256 `c52031d0f33f19db14667b0059959eea772913ceca26b48fab454d6ddef66815`) contains 465 unique strings under fields named `run_ids`. Comparing those strings to the 2,268 PR #67 proof run IDs yields **172 exact identifier matches**. The complete [172-row overlap table](hung-charged-pr67-pr52-run-id-overlap-20261028.csv) pins each proof path and its SHA-256 beside the PR #52 evidence SHA-256; CSV SHA-256 is `dba3deaf5ed3412b9d221b61dbc8771079b07cb99aeb184bfadb43f337093530`.

| City | PR #67 proof IDs | IDs also named in PR #52 recovery-plan metadata |
| --- | ---: | ---: |
| MEL | 378 | 37 |
| SZH | 378 | 13 |
| AMS | 378 | 61 |
| JHB | 378 | 0 |
| SPO | 378 | 24 |
| LOA | 378 | 37 |
| **Total** | **2,268** | **172** |

These are **identifier-string overlaps only**. The PR #52 plan is not a complete selected-output catalog, so 172 is neither a count of shared physical artifacts nor an upper bound on overlapping runs. The same naming scheme may legitimately label distinct executions. Conversely, distinct branches and matching input manifests cannot establish that runs are independent. A per-run mapping must bind actual archive/receipt/remote version, Source and Target checkpoint hashes, config/code/runtime identity, and the selected PR #52 record before any independence or Hùng ownership claim.

## Geographic and review limits

PR #52's [SZH Development report](https://github.com/HungLD9505/adaptive-retention-ev/blob/377723f/docs/reports/issue23-szh-development.md) explicitly records extensive coordinate overlap with UrbanEV. Thus SZH cannot be pooled as unseen geography without a physical-site/time mapping. Qyroven's [PR #67 scoped review](https://github.com/HungLD9505/adaptive-retention-ev/pull/67) found no blocking defect in the origin-verification increment, but explicitly did not independently restore all 2,268 run/checkpoint artifacts or approve Hùng attribution. PR #67 and #52 are draft and do not supply the required independent scientific disposition.

**Reviewer action:** request a create-only, exact 2,268-row run-to-executor/source/input/config/code/archive/receipt mapping; compare any colliding IDs by immutable artifact identity, then decide each city's accepted/limited/supplementary-only scope and the SZH overlap rule. Preserve adverse AMS and all null/negative rows. Until then, report these six-city numbers as supplementary Development observations only.

## Reproduction

Fetch the immutable PR heads into local Git refs, parse each PR #67 proof's `runs[].run_id` and `input_authentication.sources[].manifest_sha256`, and compare with PR #52's `issue23-primary-recovery-plan-evidence.json` `run_ids` fields and `issue22-execution-evidence.json` city `input_manifests`. The overlap CSV was written create-only, with sorted IDs; no original proof or matrix was changed. The count assertions were 378 unique IDs per city, 465 unique PR #52 plan IDs, 18 input-manifest matches and overlap counts `37/13/61/0/24/37` in city order MEL/SZH/AMS/JHB/SPO/LOA. This metadata audit requires no model execution or GPU.
