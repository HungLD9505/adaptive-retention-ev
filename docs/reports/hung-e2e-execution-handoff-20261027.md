# Hung E2E execution handoff — October 27, 2026

Refs #10, #15, #22, #23 and #39. This report records completed engineering and
artifact checks, prepared execution, and unresolved acceptance gates. The sole
schedule remains [SPRINT_PLAN.md](../SPRINT_PLAN.md). No new real-data training
or Final evaluation was performed for this handoff.

## Current evidence and implementation

[Draft implementation PR #70](https://github.com/HungLD9505/adaptive-retention-ev/pull/70)
is stacked on #68 (`7423cf1`) and targets `dev`. Its execution code is
`44b8532959d76fb20691881539f991ca44983727`; #66 remains at `c269cfa`, #68 at
`7423cf1`, and inspected `dev` at `7a57e9e`. All remain subject to independent
review and an agreed integration order. The dispatcher already exceeded 500
lines and is larger after this change; AGENTS.md requires explicit reviewer
agreement on its structure. This report does not provide that agreement.

The [machine-readable evidence register](evidence/hung-e2e-gate-20261027.json)
contains all 920 logical job statuses, manifest pins, the exact checkpoint
comparison, full partition, terminal dry-run result, test status, quota
observation and unmet gates. Its SHA-256 is
`ba2e3f07724815a02bd362087027d18c66fd1ac93923f20f440357cea8b09139`.

| Evidence unit | Current result | Acceptance boundary |
| --- | --- | --- |
| Main representative Development | 69 `VERIFIED_REUSE` run manifests/checkpoints/journals authenticated | Reuse within the declared Development scope; not independent teammate reproduction |
| Historical Block-7 | 69 `EXTERNAL_COMPLETE_UNMATCHED` runs authenticated | Retains original SHA/run identities; independent fairness disposition pending |
| New matched workload | 782 `PLANNED` jobs; full dry-run enumerates 1,909 stages | Zero new trained jobs; 759 CUDA and 23 deterministic Seasonal CPU declarations |
| Missing matched Block-7 acceptance | 69 cells remain an explicit `MISSING` requirement | Historical runs are not automatically reclassified or rerun |
| Six separate CHARGED cities | Historical 2,268 runs; 21 pinned proof/catalog/matrix files freshly rehashed | Reuses the existing verified collection; does not claim a fresh restore of all 419,580 daily files |
| Pilot / Development GPU / Final | Not executed | Gates below remain open |

The complete ignored G0 ledger is at
`.cache/hung-safe-resume-v1/.cache/g0-ledger-v2.json`, SHA-256
`13723182071619b32567db39f6f53f1c2362dcdfeedaff8de1107cbafbc22463`.
No historical artifact was renamed, rewritten or replaced. The six CHARGED
cities retain their separate code/run attribution and existing
[PR #54 report register](https://github.com/HungLD9505/adaptive-retention-ev/pull/54).
SZH remains overlap-limited; there is no pooled or independent unseen-location claim.
The completed proxy and Parameter Retention calibration collections remain
identified by [#66's execution report](https://github.com/HungLD9505/adaptive-retention-ev/blob/c269cfa181981224198f3d8535f8c87135e62620/docs/reports/hung-integrated-development-20261026.md).
They were not retrained or promoted to Final selections.

## Block-7 diagnosis and scientific boundary

Raw file SHA matches remain **0/9 Source strata and 0/69 Target cells**.
Weights-only CPU loads show exact equality of model tensors, optimizer state,
latent scale, RNG state, architecture, seed and training step in **9/9 Source
pairs and 69/69 Target pairs**. Target initial-model hashes also agree.
The only differing Source payload field is `code_sha`. Target payloads differ
in `code_sha` and `input_binding`; the binding difference is the original
Source checkpoint SHA. This supports a metadata/lineage explanation for the
raw hash mismatch, rather than a demonstrated numerical initialization difference.

That diagnosis is evidence for the reviewer, not an automatic acceptance
decision. Preserve both original byte identities and the unmatched status
until a non-author reviewer accepts the equivalence and comparison scope.
Do not duplicate completed Block-7 runs merely to equalize file names or hashes.
If reconciliation changes coverage, issue a new immutable coverage/plan version.

Report 1's task, method and input contracts are retained: 24 history hours to
24 outputs, separate 7/14/28-day initial histories, fixed Source/Development/Final
roles, and forecast before arrived-label scoring/update. The objectives remain

\[
L_{forecast}=\frac{1}{24}\sum_h|\hat y_h-y_h|,\qquad
L_{retain}=\frac{1}{64}\sum_k\left(\frac{z_{T,k}-z_{S,k}}{s_k+\epsilon}\right)^2,
\qquad L=L_{forecast}+\lambda L_{retain}.
\]

Source reference and latent scales stay frozen. No backbone, loss, controller,
calibration or data-split change was made. Full matched paired MAE/RMSE, gain,
negative transfer, context/switch/audit and cost conclusions await accepted
run outputs. Existing Main/Block-7 null metrics remain null; the historical
reports record 33/69 null cells in each collection.

## Safe continuation and measured checks

The dispatcher now supports fixed disjoint shards, `--resume`, atomic stage/job
receipts and an OS lock released on process death. It verifies the complete
selected shard before starting missing stages. Exact plan, partition, code,
config, input and checkpoint dependencies are bound; receipts also hash the
complete output tree and log. Missing receipts with existing output/log,
corrupt bytes, extra artifacts or changed identities fail closed. Historical
unreceipted outputs are not adopted. `--resume --verify-only` authenticates a
complete shard without training. Atomic publication requires provider-local
hardlink-capable storage; remote backup remains a separate gate.

| Check | Actually observed |
| --- | --- |
| Full offline suite on clean `44b8532` | 277 tests, 1 skipped, exit 0; 151.302 seconds |
| Resume/failure coverage | Complete skip, interruption after a receipt, unreceipted partial output, changed plan/log/forecast/receipt, OS lock/process termination, disjoint shard continuation and verifier-only path |
| Ruff check / format check / diff check | Passed; 90 Python files formatted consistently |
| `python -m tools.sources list` | Passed; catalog listing only, not a fresh raw-data download |
| Complete actual-input dry-run | Exit 0, 782 jobs / 1,909 stages; 119.365 seconds; no output-root creation or training |
| Local environment | Python 3.13.7, Torch 2.8.0+cu126; documented Python 3.12 CPU environment not claimed as locally tested |

The first full-suite attempt had two calibration identity errors while tracked
changes were uncommitted. Its log and exit 1 are preserved. The unchanged
clean-worktree gate passed after commit; it was not weakened to hide the errors.
Synthetic CUDA fixtures may use the available local GPU; these are not
real-data pilot or training evidence.

The earlier #68 dry-run process PID 13548 was observed live with the exact
782-job command, and later absent with a terminal summary in its log. Its
separate exit code was not retained, so it is not used as the terminal gate.
The new worker explicitly captured exit 0 at 02:12:53 ICT on October 27.
Its log SHA-256 is
`83616e083caa067ef89e520ba86589e29b00c9c022fc369542bdbc13a4d466b1`.

The derived plan SHA is
`2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee`;
only execution commit, byte-identical config locations and new output root
changed from #68's parent plan. Cells, job specifications, seeds, inputs and
historical model dependencies are identical. The complete 40-shard partition
SHA is `7dd340b84a51abca9dcb2e83490d088c07178ffbdbb9d81d68225d665a279c7f`.

## Prepared pilot, capacity and durability

The first shard contains exactly six jobs chosen before performance inspection:
Seasonal and Target-only at 7d/entity 2264, Frozen Source and Online Best-lambda
at 14d/entity 1153, Uncertainty and Parameter Retention at 28d/entity 1165;
all use seed 7. These are the predeclared first verification adaptation entities.
The remaining 776 jobs occur exactly once in the other 39 shards, at most 20
jobs per shard. This is an allocation candidate for review, not execution approval.

At **02:06 ICT on October 27**, the authenticated Kaggle menu displayed
**GPU 23h 57m available of 30h**. This is an observed quota snapshot, not a
guessed 27-hour balance; recheck it immediately before approved execution.
The local device reports RTX 3050 Ti Laptop GPU, 4 GiB; numerical/checkpoint
parity for allocating this new plan has not been approved.

Pilot runtime/P95, VRAM, output bytes, remote upload and independent readback
cost are explicitly **unmeasured/null**. No feasibility claim or full-matrix
launch follows from local dry-run timing. New stages can record subprocess
wall time, local hash/readback cost and output bytes; existing manifests retain
device, candidate/audit and update accounting. Provider relocation must produce
a newly pinned plan without altering model/input hashes, then pass review and
restore/readback before training allocation.

The local evidence-only review bundle is
`.cache/hung-safe-resume-v1/.cache/e2e-review-bundle-v1.zip`, SHA-256
`7e088184c279fed43c3f7cfc2a312e1400e44baa4aceb0fcf5c0bd826d4267eb`.
Its 94 members passed ZIP CRC; it contains plan/config/ledger/log evidence and
reproduction workers, with no raw data, labels, forecasts or checkpoints.
No new remote archive URL or independent remote readback is claimed for this
bundle. Existing model archives remain at the private URLs in #54/#66; reviewer
access and independent teammate reproduction remain acceptance requirements.

## Review decisions and remaining delivery

1. Review #70's latest commit and the #66/#68 integration path; explicitly
   resolve the dispatcher-size exception and reproduce one identified shard.
2. Accept or reject the Block-7 state-equivalence/fairness evidence without
   changing historical identities. Until accepted, matched Block-7 remains open.
3. Record a decision on #39's proposed Colab substitute: attributable CUDA
   execution on Kaggle/local plus durable private archives, hash/CRC readback,
   reviewer access and bounded independent restore/reproduction. User preference
   alone is not recorded peer acceptance; #39 stays open until decided.
4. After those prerequisites, approve and run the bounded Kaggle pilot, measure
   capacity and remote persistence, and approve only feasible Development shards.
   The current stop is **before GPU execution**.
5. Complete all nine baseline families, five ablation categories with explicit
   aliases, 7/14/28 budgets and at least three seeds. Compute paired original-unit,
   station-first MAE/RMSE, coverage, gain/NTR and full candidate/audit costs from
   verified outputs; retain zero-denominator and missing-label cases.
6. Obtain independent immutable configuration/data/cohort/code lock approval
   before any Final execution. Then verify locked Final artifacts and complete
   Results/Discussion/Limitations for #10. The existing thesis draft remains in
   #54; this handoff does not create a competing thesis or schedule.

No merge, issue closure, Final execution or `main` promotion occurred. The
unresolved items above are unmet acceptance requirements, not completed results.

## Files and commands

Code changes are the dispatcher, new `dispatch_state.py`, `tools/hung_e2e_gate.py`,
their two regression-test modules and the dispatcher contract, listed exactly
in the JSON register. This documentation PR adds this report and that register.
Actual commands include the SHA-pinned `tools.hung_e2e_gate ledger`, full
`unittest discover -s tests -v`, Ruff check/format check, `tools.sources list`,
`git diff --check`, and the complete dispatcher command without `--execute`.
The register contains exact code/plan/log hashes and terminal command arguments;
the local bundle preserves full logs and worker scripts for replay.
