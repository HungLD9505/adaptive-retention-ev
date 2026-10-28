# Hùng Block7 replay contingency preflight (v2, 2026-10-29)

**Status: prepared candidate, not an approved executable plan.** No reviewer has rejected the historical Block7 mapping. No replay job was submitted, executed, scheduled, or counted toward Development here. The historical 69 Block7 IDs and their results remain separate from the 69 new candidate IDs in `candidate_jobs.csv`; neither set is overwritten.

## Exact candidate set and checked inputs

The offline builder `tools/hung_block7_replay_preflight.py` produced 69 unique candidate IDs, one for each of the 69 matched cells: 18 at seven days, 24 at 14 days, and 27 at 28 days. Every candidate ID is `block7_replay_candidate_v1_<cell_id>`, distinct from the historical `block7_<cell_id>`, Main `main_<cell_id>`, and 782-job Development ledger IDs. Each CSV row binds its historical Block7 ID and manifest SHA, Main ID and manifest SHA, input manifest SHA, the saved Main Source and Target checkpoint SHA/manifest SHA/byte count, and the Block7 config SHA. The historical checkpoint *bytes* were not present in the repo-local availability scan; the historical mapping remains a review question, not a proven equivalence.

The builder independently rehashed the saved 782-job parent plan (`2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee`), portable plan (`b7c79f501230ea5e1308b4bc02b2707089a8c788e4ee3df229aadec005a05198`), 69-pair table (`e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de`), Development ledger v5 (`bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004`), and input ZIP (`2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`). It checked all 9 distinct Source and 69 distinct Target `.pt` bytes and adjacent run manifests against their frozen hashes. The payload Main and Block7 configs differ only in `replay.block_days` (14 versus 7), with Block7 config SHA `91ef6159391c8fa2b30e82d4cea740667135466bf36b7e797e7bf73e9fccf24f`. The candidate CSV SHA is `05d660c72962d51ec3e8c22a57cd015977ceb333f23b1408f891d343f785d802`.

## Execution readiness and gates

`experiments/hung_sprint2/dispatch_matched.py` can structurally dispatch a controller job that reuses an existing Source and Target checkpoint. For Block7 it would run `replay-21` and resume into `replay-90`, without retraining Source or Target. This is an implementation inspection, **not** a run or confirmation that the frozen payload is executable today.

The frozen parent plan pins code commit `44b8532959d76fb20691881539f991ca44983727`; the current repository HEAD at inspection was `e491cf35c2b8f12c3934bb6726d08e66c088760a`, and may advance. The dispatcher requires the plan's `code_commit` to equal the checkout HEAD and the tracked worktree to be clean. The frozen parent plan also refers to selection/config paths from another worktree, while the portable plan refers to payload-local paths; neither is a ready local dispatch plan. An approved plan must be regenerated and reviewed against a *fresh pinned code commit*, current repository-contained paths, extracted accepted inputs, and a new Git-ignored create-only output root. It must preserve the exact 69-cell jobset and predeclared non-score-based policy. An independent reviewer must explicitly decide that the historical 69 are inadequate before replay is authorized. The selected Final contract and any parity/CHARGED decisions must remain separate from this Development contingency.

Local execution currently fails the dispatcher's storage gate: it requires at least **8 GiB free** at the output root; `Get-Volume -DriveLetter D` showed **3,829,444,608 bytes** free at this preflight. A provider route would need its own quota/storage and saved-output readback check. Do not start a replay on either route until these gates are met. No new GPU/CPU cost estimate is claimed here; the 138 planned replay stages are a count, not a measured runtime.

If the reviewer later requires replay, the next finite preparation is: record the review decision; freeze one code/config/input/jobset SHA and a create-only output location; validate all 69 dispatch entries and available storage/provider capacity; execute only the newly authorized Development jobs; then independently read back every saved artifact with manifest and byte/SHA/CRC checks. Existing historical and Development outputs remain immutable. The candidate ledger itself supplies no authorization or completion evidence.

## Reproduction and validation

From the repository root, the create-only builder command was:

```powershell
python tools/hung_block7_replay_preflight.py --payload .cache/kaggle-payload-v2/payload --pairs docs/reports/hung-block7-manifest-pairs-20261028.csv --ledger docs/reports/hung-development-782-job-ledger-20261028-v5.csv --output-dir docs/reports/hung-block7-replay-contingency-20261029-v2
```

The output directory must be new. The earlier v1 directory is retained as the initial candidate snapshot; v2 adds an explicit portable-plan hash pin. The builder never calls a provider or dispatcher. See `summary.json` for the machine-readable result. Any later approved executable plan must receive its own version and review record.
