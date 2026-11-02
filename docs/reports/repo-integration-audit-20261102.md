# Repository integration and cleanup audit — 2 November 2026

Snapshot: `2026-11-02T09:10:46+07:00`. Repository: https://github.com/HungLD9505/adaptive-retention-ev. Related work: #15, #19–#23, #39–#41 and #10.

This is an inventory and proposed disposition, not peer approval, issue acceptance, a new research scope, or authorization to merge. No remote mutations were performed. Local `git fetch origin` refreshed tracking refs without pruning. The machine-readable companion pins every observed branch and PR head.

## Verified snapshot

- 37 remote branches, 34 open PRs, 10 open issues.
- All 34 PR branch tips are outside both `dev` and `main`: **zero immediately deletable PR branches** under the current preservation rule.
- GitHub currently reports every open PR as mechanically MERGEABLE. This does not mean compatible research methods, passing checks, independent approval, or acceptable integration.
- Nine PRs report APPROVED, two CHANGES_REQUESTED, and 23 no approving decision. Approvals concern their incremental diff and the reviewed SHA, not all inherited code.
- Five PRs have failed latest check conclusions: #52, #72, #73, #74, #75. All five have GitHub check annotations stating the jobs were not started because recent payments failed or a spending limit was reached: CI was not executed, not a test failure and not a pass. Other 29 show successful latest checks. No check was rerun or spending setting changed by this audit.
- Current worktree has uncommitted report edits, post-hoc outputs, and output/tmp directories. These are not present in remote #75. This audit did not stage, stash, delete, or commit them.

## Proposed integration policy

Use the Qyroven implementation as the proposed primary reproducible pipeline because the delivered report primary results were produced by that implementation. This is a recommendation requiring code review, not an assertion that its current tip is the frozen execution commit. Preserve the Hùng implementation as a separately identified supporting track. Keep Đức and Cyber studies isolated. Do not silently reconcile their differing heads, bootstrap rules, seeds, cohorts or checkpoints into one claimed historical experiment.

Review dependencies in their component PRs, then accept one verified combined path per track. There are two valid Git strategies: component merges in dependency order, or one reviewed integration PR followed by explicit superseded closures. Do not blindly merge both cumulative stacks. Preserve authored commits and exact frozen execution identities.

Refactor only after a working integrated checkpoint is accepted. Preserve the original frozen code/config/lock identity and keep raw data, checkpoints, immutable runs and historical evidence outside destructive cleanup. This audit runs no training.

## Every open PR: proposed disposition

| PR | Author | Base | Files | Review / CI | Proposed action and condition |
|---|---|---|---:|---|---|
| [#42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) | HungLD9505 | `dev` | 13 | NO APPROVING DECISION; SUCCESS; draft | **Review component; integrate through one Hung stack.** Exact head is an ancestor of #72. Preserve model authorship; do not independently merge the same cumulative diff twice. |
| [#43](https://github.com/HungLD9505/adaptive-retention-ev/pull/43) | HungLD9505 | `dev` | 15 | NO APPROVING DECISION; SUCCESS; draft | **Review component after #42.** Exact head is an ancestor of #72. Controller/bootstrap contract differs from the primary implementation; retain its identity. |
| [#44](https://github.com/HungLD9505/adaptive-retention-ev/pull/44) | HungLD9505 | `dev` | 31 | NO APPROVING DECISION; SUCCESS; draft | **Review component after #42/#43.** Exact head is an ancestor of #72. Preserve runner/checkpoint and real-run evidence; do not describe this as the primary runner. |
| [#45](https://github.com/HungLD9505/adaptive-retention-ev/pull/45) | HungLD9505 | `dev` | 38 | NO APPROVING DECISION; SUCCESS; draft | **Reconcile unique Seasonal Naive work.** Four patch-unique commits versus #72; cannot close as already absorbed without file/behavior review. |
| [#46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) | HungLD9505 | `dev` | 68 | NO APPROVING DECISION; SUCCESS; draft | **Use as history/review component of #72.** Exact head is an ancestor of #72; do not treat its earlier completion report as current full acceptance. |
| [#47](https://github.com/HungLD9505/adaptive-retention-ev/pull/47) | Qyroven | `dev` | 17 | NO APPROVING DECISION; SUCCESS | **Review primary model component.** Exact head is in #52; preserve original commits. Refresh shared CI/dependencies only in the integration work. |
| [#48](https://github.com/HungLD9505/adaptive-retention-ev/pull/48) | hung00cyber | `dev` | 9 | NO APPROVING DECISION; SUCCESS | **Review and integrate isolated Cyber study.** Independent member study; preserve scope and real authorship. CI success does not establish scientific acceptance. |
| [#49](https://github.com/HungLD9505/adaptive-retention-ev/pull/49) | Qyroven | `dev` | 9 | NO APPROVING DECISION; SUCCESS | **Review primary controller component.** Exact head is in #52; review bootstrap, clock and next-block state contract, not only fixture success. |
| [#50](https://github.com/HungLD9505/adaptive-retention-ev/pull/50) | Qyroven | `dev` | 39 | NO APPROVING DECISION; SUCCESS | **Review primary runner after #47/#49.** Exact head is in #52. Later reader hardening is in #52, so the earlier slice alone is not the final production code. |
| [#51](https://github.com/HungLD9505/adaptive-retention-ev/pull/51) | Qyroven | `dev` | 52 | NO APPROVING DECISION; SUCCESS; draft | **Review baselines after primary runner.** Exact head is in #52. Draft; keep aliases, costs and proxy limitations; verify later fixes in the combined head. |
| [#52](https://github.com/HungLD9505/adaptive-retention-ev/pull/52) | Qyroven | `dev` | 299 | NO APPROVING DECISION; FAILURE; draft | **Primary execution integration candidate; hold for review.** 299 changed files; latest CI blocked before execution (billing/spending limit). PR body still describes Final in progress; reconcile completed evidence through #75. Historical execution authorization is not merge approval. |
| [#53](https://github.com/HungLD9505/adaptive-retention-ev/pull/53) | HungLD9505 | `codex/39-completion` | 5 | CHANGES_REQUESTED; SUCCESS | **Repair maintained English documentation.** CHANGES_REQUESTED at current head: README/four canonical reports and PR metadata require English. Exact head is inherited by #72; fix there too without editing historical evidence. |
| [#54](https://github.com/HungLD9505/adaptive-retention-ev/pull/54) | HungLD9505 | `dev` | 10 | NO APPROVING DECISION; SUCCESS; draft | **Reconcile thesis report with current report/evidence.** Standalone thesis draft; not an ancestor of #72. Compare with current delivered PDFs; preserve evidence JSON and historical sources. |
| [#55](https://github.com/HungLD9505/adaptive-retention-ev/pull/55) | HungLD9505 | `codex/39-completion` | 2 | APPROVED; SUCCESS; draft | **Review/preserve diagnostic separately.** Increment approved, but two patch-unique commits versus #72. Do not assume umbrella already contains this controller variance regression. |
| [#56](https://github.com/HungLD9505/adaptive-retention-ev/pull/56) | HungLD9505 | `docs/39-report-consolidation` | 7 | APPROVED; SUCCESS | **Retain reviewed increment in Hung integration.** Exact head is in #72; approval covers mean-selection increment only, not its inherited stack. |
| [#57](https://github.com/HungLD9505/adaptive-retention-ev/pull/57) | HungLD9505 | `feat/22-hung-core-baselines` | 9 | APPROVED; SUCCESS; draft | **Retain reviewed increment in Hung integration.** Exact head is in #72; preserve fixed/full-finetuning initialization and three-candidate cost provenance. |
| [#58](https://github.com/HungLD9505/adaptive-retention-ev/pull/58) | HungLD9505 | `feat/22-hung-fixed-finetuning` | 6 | APPROVED; SUCCESS; draft | **Retain reviewed increment in Hung integration.** Exact head is in #72; preserve Target-only random initialization and Frozen Source no-update behavior. |
| [#59](https://github.com/HungLD9505/adaptive-retention-ev/pull/59) | HungLD9505 | `feat/22-hung-target-frozen` | 8 | APPROVED; SUCCESS; draft | **Retain reviewed increment in Hung integration.** Exact head is in #72; retain provisional proxy interpretation and causal label availability. |
| [#60](https://github.com/HungLD9505/adaptive-retention-ev/pull/60) | HungLD9505 | `feat/22-hung-proxy-baselines` | 6 | APPROVED; SUCCESS; draft | **Candidate for superseded closure after verification.** Not exact-head ancestry, but all three reachable non-ancestor patches are equivalent in #72. Review final content/fallback behavior and preserve credit before closure. |
| [#61](https://github.com/HungLD9505/adaptive-retention-ev/pull/61) | HungLD9505 | `feat/22-hung-proxy-baselines` | 11 | APPROVED; SUCCESS; draft | **Candidate for superseded closure after verification.** Not exact-head ancestry, but all three reachable non-ancestor patches are equivalent in #72. Verify retained parameter/block-size semantics before closure. |
| [#62](https://github.com/HungLD9505/adaptive-retention-ev/pull/62) | HungLD9505 | `feat/22-hung-proxy-baselines` | 4 | APPROVED; SUCCESS; draft | **Candidate for superseded closure after verification.** Not exact-head ancestry, but all seven reachable non-ancestor patches are equivalent in #72. Verify current calibration bindings; no historical Final approval implied. |
| [#63](https://github.com/HungLD9505/adaptive-retention-ev/pull/63) | HungLD9505 | `dev` | 174 | NO APPROVING DECISION; SUCCESS; draft | **Review one analyzer-path correction against #52.** One patch-unique commit versus #52; preserve separate-city scope/config fixes. Do not assume already included. |
| [#64](https://github.com/HungLD9505/adaptive-retention-ev/pull/64) | HungLD9505 | `feat/22-hung-proxy-baselines` | 7 | APPROVED; SUCCESS; draft | **Reconcile partially cherry-picked ablation.** One equivalent and one patch-unique commit versus #72; verify conflict resolution for retention kind and initialization kind. |
| [#65](https://github.com/HungLD9505/adaptive-retention-ev/pull/65) | HungLD9505 | `dev` | 45 | NO APPROVING DECISION; SUCCESS; draft | **Reconcile historical Colab preflight.** One equivalent and one patch-unique commit versus #72. Preserve bundle/runtime identity; do not revive obsolete launches. |
| [#66](https://github.com/HungLD9505/adaptive-retention-ev/pull/66) | HungLD9505 | `dev` | 100 | NO APPROVING DECISION; SUCCESS; draft | **Review umbrella conflict resolution, then consolidate.** Two patch-unique commits versus #72; later #72 ancestry does not contain its exact tip. Compare actual integrated files before declaring replacement. |
| [#67](https://github.com/HungLD9505/adaptive-retention-ev/pull/67) | HungLD9505 | `dev` | 184 | NO APPROVING DECISION; SUCCESS; draft | **Separate verifier code review from disputed evidence.** Eight patch-unique commits versus #52; supplementary CHARGED LOA same-ID lineage dispute is documented. Require immutable bindings or mark unresolved; never pool with primary outputs. |
| [#68](https://github.com/HungLD9505/adaptive-retention-ev/pull/68) | HungLD9505 | `dev` | 108 | NO APPROVING DECISION; SUCCESS; draft | **Reconcile dispatcher tip against #70/#72.** One patch-unique commit versus #72 despite being a declared stack dependency. Compare its exact generator/dispatcher changes. |
| [#69](https://github.com/HungLD9505/adaptive-retention-ev/pull/69) | huuduc32 | `dev` | 10 | NO APPROVING DECISION; SUCCESS | **Review and integrate isolated Duc study.** Three commits mapped by GitHub to huuduc32. Keep fixed-model Development scope; not a substitute production runner. |
| [#70](https://github.com/HungLD9505/adaptive-retention-ev/pull/70) | HungLD9505 | `dev` | 111 | NO APPROVING DECISION; SUCCESS; draft | **Review resume/locking component within #72.** Exact head is in #72. Existing large-file reviewer agreement and historical fairness decisions remain separate gates. |
| [#71](https://github.com/HungLD9505/adaptive-retention-ev/pull/71) | HungLD9505 | `dev` | 5 | NO APPROVING DECISION; SUCCESS; draft | **Preserve/reconcile separate storage handoff.** Two patch-unique commits versus #72. Snapshot records pending readback; check later evidence before updating current status, preserve original record. |
| [#72](https://github.com/HungLD9505/adaptive-retention-ev/pull/72) | HungLD9505 | `dev` | 809 | CHANGES_REQUESTED; FAILURE; draft | **Hung supporting pipeline integration candidate; hold.** 809 changed files; CHANGES_REQUESTED remains. Latest CI blocked before execution (billing/spending limit). Older review findings need exact-head recheck; gate register retains parity/lineage/reproduction/scope decisions. Bounded 360-job Final is separate from primary 810-unit Final. |
| [#73](https://github.com/HungLD9505/adaptive-retention-ev/pull/73) | Qyroven | `dev` | 5 | NO APPROVING DECISION; FAILURE; draft | **Review as optional operational tooling.** One patch-unique commit versus #52; latest CI blocked before execution (billing/spending limit). Keep operational support separate from scientific method; no need to restart finished production. |
| [#74](https://github.com/HungLD9505/adaptive-retention-ev/pull/74) | Qyroven | `dev` | 4 | NO APPROVING DECISION; FAILURE; draft | **Preserve optional hardware metadata proposal.** One patch-unique commit versus #52; latest CI blocked before execution (billing/spending limit). No hardware trial/child allocation is established by this PR; do not imply it ran Final. |
| [#75](https://github.com/HungLD9505/adaptive-retention-ev/pull/75) | Qyroven | `dev` | 4 | NO APPROVING DECISION; FAILURE; draft | **Review current synthesis and reconcile local report edits.** Four tracked changed files; latest CI blocked before execution (billing/spending limit). Local uncommitted post-hoc/manuscript work is outside the remote head and must be preserved separately. |

## Branch preservation and deletion table

Every remote branch is listed below. “Ancestor of PR” means exact Git ancestry at this snapshot, not equivalent behavior. Patch equivalence is only a review aid: it does not prove the final file tree retains the intended behavior or scientific provenance.

| Remote branch | Head SHA | Open PR | Already in dev / main | Proposed disposition |
|---|---|---|---|---|
| `chore/23-final-runtime-hardware` | `9a9d31a6e200` | #74 | no / no | KEEP NOW; Preserve optional hardware metadata proposal. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `chore/39-controller-comparison` | `c25497c2dd92` | #55 | no / no | KEEP NOW; Review/preserve diagnostic separately. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `codex/22-hung-integrated-methods` | `c269cfa18198` | #66 | no / no | KEEP NOW; Review umbrella conflict resolution, then consolidate. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `codex/22-hung-matched-dispatcher` | `315113f73840` | #68 | no / no | KEEP NOW; Reconcile dispatcher tip against #70/#72. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `codex/22-hung-no-source-init` | `c8f908f5882f` | #64 | no / no | KEEP NOW; Reconcile partially cherry-picked ablation. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `codex/23-verifier-completion-gates` | `c1c62fcb49bd` | #67 | no / no | KEEP NOW; Separate verifier code review from disputed evidence. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `codex/39-colab-drive-fix` | `b140fb2a87a8` | #65 | no / no | KEEP NOW; Reconcile historical Colab preflight. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `codex/39-completion` | `e85a53cd02de` | #46 | no / no | KEEP NOW; Use as history/review component of #72. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `dev` | `7a57e9e8954e` | — | yes / yes | KEEP: protected workflow role; no deletion or default-branch change. |
| `docs/hung-e2e-execution-handoff-20261027` | `78764b072142` | #71 | no / no | KEEP NOW; Preserve/reconcile separate storage handoff. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `docs/10-thesis-report` | `4f3c23c73f47` | #54 | no / no | KEEP NOW; Reconcile thesis report with current report/evidence. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `docs/23-final-evidence-synthesis` | `f0fdd760fca9` | #75 | no / no | KEEP NOW; Review current synthesis and reconcile local report edits. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `docs/39-report-consolidation` | `9ebefe516086` | #53 | no / no | KEEP NOW; Repair maintained English documentation. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/19-duc-retention-study` | `6b45c00f1188` | #69 | no / no | KEEP NOW; Review and integrate isolated Duc study. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/19-hung-model-retention` | `b76d62a9d86f` | #42 | no / no | KEEP NOW; Review component; integrate through one Hung stack. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/19-qyroven-model-retention` | `f91527b21ebe` | #47 | no / no | KEEP NOW; Review primary model component. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/20-cyber-controller-study` | `31f8264ea0ed` | #48 | no / no | KEEP NOW; Review and integrate isolated Cyber study. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/20-hung-controller` | `8f93d79275da` | #43 | no / no | KEEP NOW; Review component after #42. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/20-qyroven-confidence-controller` | `6135a0014c09` | #49 | no / no | KEEP NOW; Review primary controller component. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/21-hung-runner` | `a70015c2450d` | #44 | no / no | KEEP NOW; Review component after #42/#43. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/21-qyroven-prequential-runner` | `bf941645dec3` | #50 | no / no | KEEP NOW; Review primary runner after #47/#49. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-baselines-stacked` | `597be9641f34` | #45 | no / no | KEEP NOW; Reconcile unique Seasonal Naive work. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-core-baselines` | `aa5a5520149d` | #56 | no / no | KEEP NOW; Retain reviewed increment in Hung integration. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-fixed-finetuning` | `4bac232d64e5` | #57 | no / no | KEEP NOW; Retain reviewed increment in Hung integration. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-parameter-retention` | `f9b8e2708048` | #61 | no / no | KEEP NOW; Candidate for superseded closure after verification. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-proxy-baselines` | `44539449c75d` | #59 | no / no | KEEP NOW; Retain reviewed increment in Hung integration. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-seasonal-common` | `d82a15b3d783` | #60 | no / no | KEEP NOW; Candidate for superseded closure after verification. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-hung-target-frozen` | `0b8a0a5ce886` | #58 | no / no | KEEP NOW; Retain reviewed increment in Hung integration. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/22-qyroven-baselines` | `0f3245be9145` | #51 | no / no | KEEP NOW; Review baselines after primary runner. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/23-hung-provider-execution` | `1b730c7f83d6` | #72 | no / no | KEEP NOW; Hung supporting pipeline integration candidate; hold. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/23-hung-proxy-calibration` | `e0e3f13724d9` | #62 | no / no | KEEP NOW; Candidate for superseded closure after verification. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `feat/23-qyroven-evaluation` | `377723f5d55a` | #52 | no / no | KEEP NOW; Primary execution integration candidate; hold for review. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `fix/22-hung-matched-resume` | `44b8532959d7` | #70 | no / no | KEEP NOW; Review resume/locking component within #72. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `fix/23-charged-analyzer-paths` | `5b6b7531b9db` | #63 | no / no | KEEP NOW; Review one analyzer-path correction against #52. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `fix/23-final-receipt-backpressure` | `c3c46f276313` | #73 | no / no | KEEP NOW; Review as optional operational tooling. Delete only after accepted work/credit is preserved and the PR is merged or explicitly superseded. |
| `main` | `953ecd79ed7b` | — | no / yes | KEEP: protected workflow role; no deletion or default-branch change. |
| `master` | `528680dd7379` | — | yes / yes | KEEP: protected workflow role; no deletion or default-branch change. |

## Nontrivial overlap checks

| PR compared with candidate umbrella | Patch-unique commits | Patch-equivalent commits | Interpretation |
|---|---:|---:|---|
| #45 → #72 | 4 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #55 → #72 | 2 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #60 → #72 | 0 | 3 | Candidate absorbed patch set; verify final tree before closure. |
| #61 → #72 | 0 | 3 | Candidate absorbed patch set; verify final tree before closure. |
| #62 → #72 | 0 | 7 | Candidate absorbed patch set; verify final tree before closure. |
| #63 → #52 | 1 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #64 → #72 | 1 | 1 | Unique history remains; reconcile before closure or branch deletion. |
| #65 → #72 | 1 | 1 | Unique history remains; reconcile before closure or branch deletion. |
| #66 → #72 | 2 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #67 → #52 | 8 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #68 → #72 | 1 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #71 → #72 | 2 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #73 → #52 | 1 | 0 | Unique history remains; reconcile before closure or branch deletion. |
| #74 → #52 | 1 | 0 | Unique history remains; reconcile before closure or branch deletion. |

## Issue closure map

| Issue | Proposed treatment |
|---|---|
| [#10](https://github.com/HungLD9505/adaptive-retention-ev/issues/10) docs: restructure the full thesis report around Report 1 and final experiments | Compare #54 with the current delivered report and supplement; agree canonical maintained source, verify criteria, then close. |
| [#15](https://github.com/HungLD9505/adaptive-retention-ev/issues/15) docs: establish the 21-day research sprint execution plan | Keep parent open until child disposition and completion/incomplete scope are reconciled. Do not mark all four E2E scopes complete by inference. |
| [#19](https://github.com/HungLD9505/adaptive-retention-ev/issues/19) feat: implement source GRU adaptation and latent retention | Keep open until reviewed model work is integrated and outstanding acceptance is recorded; training completion alone is insufficient. |
| [#20](https://github.com/HungLD9505/adaptive-retention-ev/issues/20) feat: implement confidence-based retention decisions | Keep open until controller contract/code integration and exact-head independent review are recorded. |
| [#21](https://github.com/HungLD9505/adaptive-retention-ev/issues/21) feat: implement prequential runner and end-to-end smoke | Keep open until combined runner/reader/resume path and required reproducibility checks are accepted. |
| [#22](https://github.com/HungLD9505/adaptive-retention-ev/issues/22) feat: implement required baselines and ablation variants | Keep open until the baseline/ablation definitions, costs, review and integration are reconciled per implementation. |
| [#23](https://github.com/HungLD9505/adaptive-retention-ev/issues/23) research: tune on development and run locked final evaluation | Record primary frozen Final completion and separate Hùng bounded Final; keep unresolved acceptance explicit. Close only against actual criteria or an explicitly agreed scope revision. |
| [#39](https://github.com/HungLD9505/adaptive-retention-ev/issues/39) feat: co-lead Sprint 2 end-to-end implementation and cross-validation — Hung | Keep open: Hùng gate register retains lineage/parity/reproduction and scope decisions. Do not trigger new training as a cleanup side effect. |
| [#40](https://github.com/HungLD9505/adaptive-retention-ev/issues/40) feat: independent target-adaptation and retention study — Duc | Review #69 against its complete checklist; integrate accepted isolated work with authored history, then close when satisfied. |
| [#41](https://github.com/HungLD9505/adaptive-retention-ev/issues/41) feat: independent confidence-controller training study — Cyber | Review #48 against its complete checklist; integrate accepted isolated work with authored history, then close when satisfied. |

## Four-person attribution acceptance

- Required accounts: `Qyroven`, `HungLD9505`, `huuduc32`, `hung00cyber`. Current contributors API returned the first two only.
- #69 has three original commits with GitHub-recognized author `huuduc32`; #48 head `31f8264ea0ed6c9c7958ce1f91c9f8f265e02af5` maps to `hung00cyber` through the GitHub commits API. Both branches are outside main/dev.
- Preserve accepted real contributions and original author identities. Prefer history-preserving merges over squashing multi-author stacks into a single author. Do not create empty commits or fabricate co-authorship to satisfy a counter.
- Before main promotion, verify accepted commits from all four accounts are reachable in the proposed main history and still mapped correctly by GitHub. After promotion, verify the contributor display/API after normal cache refresh. Commit reachability alone does not control GitHub display timing.
- GitHub contributors graph uses the default branch and associated author email; merge/empty commits alone do not count. Official reference: https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors

## Next concrete work

1. Preserve uncommitted manuscripts/post-hoc outputs and frozen execution code/artifact references; inspect other active worktrees before changing their branches. Inventory is not a completed backup.
2. Review #48 and #69 as independently attributable isolated studies, while reviewing primary #47/#49/#50/#51 in dependency order. Do not merge merely to obtain contributor credit.
3. Resolve #52 combined-state review and CI root causes; reconcile its stale status with #75 plus the uncommitted report work.
4. Review #72 latest exact head rather than assuming old review findings persist; incorporate the #53 language correction and reconcile each unique side-branch change. Keep disputed evidence unaccepted.
5. Prepare an integration candidate into dev, then refactor and verify from a clean checkout using offline tests and bounded smoke fixtures. No new long training is required for repository cleanup.
6. Present exact-head changes/checks/review and all-four attribution evidence before main promotion. Only then close satisfied issues and delete safely preserved branches.

## Verification and limits

- Inputs: live GitHub PR/branch/issue APIs, paginated changed-file/review/comment lists for all 34 PRs, refreshed Git history, merge-base ancestry and `git cherry` patch comparisons.
- No full code review, numerical output replay, raw data/archive revalidation, fresh-clone tests or CI reruns were performed for this inventory. Existing check statuses and reviewer findings are observations, not new verification.
- No blanket deletion is recommended. #60/#61/#62 are only candidate superseded closures, conditional on accepted umbrella integration and final-tree/credit checks.
- Existing workflow still requires non-author review and checks; this report does not waive them. Historical experiment/CI billing exceptions are not approval to merge.
