# Hung Issue #22: fixed retention and full fine-tuning policy tranche

This branch stacks on PR #56 at `aa5a5520149d588821312c505d3cf45fba8af471` and uses Hung's existing three-candidate runner. It adds code and offline fixtures only. No new Development or Final data run, metric or checkpoint is claimed.

## Policy semantics and input binding

`replay-development --selection-rule fixed_retention` keeps the configured positive `initial_level` through every completed block. `full_finetuning` keeps level zero. Both begin with Source-initialized target weights; full fine-tuning is **not** Target-only training. Future `target-smoke` checkpoints record their actual initial-adaptation `retention_weight` inside the checkpoint payload. Replay checks that payload against the configured fixed level and the target run manifest; the manifest's checkpoint SHA and input binding are also checked. A mismatched or missing value is rejected before creating a replay output. This binding applies even when the accepted target is `source_checkpoint_only` and has zero initial target steps, so the intended policy remains explicit.

Historical target checkpoints lacking the payload field are preserved unchanged and expose `target_initial_retention_weight_verified=false` in new replay manifests. They remain loadable for the original Adaptive/mean-selection rules, but **cannot** establish Fixed Retention or Full Fine-tuning λ provenance and are rejected for those policies. Merely editing an old run manifest cannot upgrade them. The new field binds the declaration to checkpoint bytes and their recorded SHA; it does not retroactively prove which loss a historical training process executed.

Neither fixed policy consults observed scores when selecting the future block. Complete arrived days and missing days are still counted, and forecasts are still scored in the normal causal order. A block decision records `reason=fixed_policy`, `selection_statistic=fixed_level`, null LCBs and null observed-mean improvements. The selected **trained** candidate and optimizer are carried forward. The selection rule, initial level, target/source checkpoint hashes, input binding and code identity remain in the replay manifest and resume checks. A changed policy or initialization cannot resume an old run under another name.

## Compute and comparison scope

This tranche deliberately runs all three candidate forecasts and online update trajectories at levels `{0, λlow, λhigh}` for each issued/scored day. Thus fixed retention and full fine-tuning have the **same candidate forecast/update budget as Adaptive and Online Best** when compared in this runner. The existing per-candidate runtime, inference/update counts and tensor-memory fields expose the actual cost. The isolated old-policy audit has no switch to follow for these fixed policies, so its cost remains zero. Fixed Retention with the identical configuration may also serve as the Fixed-λ ablation, counted once.

These are three-candidate equal-budget comparison policies. Their measured time/memory must **not** be reported as the cost of a deployable one-model Fixed Retention or Full Fine-tuning baseline. A separate one-model execution and cost record would be needed for that practical-cost claim. The three-candidate trajectories also mean the unused candidates are computed but do not influence the fixed deployment choice.

## Offline verification and remaining work

Focused fixtures check score-independent keep, missing-day accounting, positive/zero level validation, three equal candidate update/inference counts, trained-state carry, policy and initial-adaptation binding, rejection before output creation, and resumed versus uninterrupted forecast/decision equivalence. A regression trains a nonempty synthetic Development prefix at λ=0.1, changes only its run-manifest λ to zero, and proves Full Fine-tuning replay rejects it while the checkpoint SHA stays unchanged. No fixture reads raw datasets or Final targets.

The other #22 methods and ablations, reviewed Development settings, matched real-data execution, calibration, accepted CHARGED city matrices, three-seed comparison matrix, capacity acceptance, independent review and immutable Final lock remain open. Historical PR #46/#56 runs are not relabeled as fixed-policy results.

## Checks on this branch

On Windows with Python 3.13, `python -m tools.sources list` passed (catalog listing only). With `PYTHONUTF8=1` and a temporary directory inside the worktree, `python -m unittest discover -s tests -q` ran 189 tests successfully with one skip; 24 focused replay CLI, training and model tests passed. Ruff lint and format checks and `git diff --check` passed. The first full-suite attempt without UTF-8 mode failed in unrelated input-loader fixtures because the Windows default `cp1252` codec could not handle the Vietnamese checkout path; that environment error was resolved for the successful rerun. Fixture messages about expected QC failures are part of passing tests.
