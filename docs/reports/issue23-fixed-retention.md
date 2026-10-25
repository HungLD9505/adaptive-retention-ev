# Fixed Retention calibration — pre-execution declaration

Declared before running this grid on 2026-10-26, under Issue #23. After independent
verification of the complete Source-duration study, recompute its provisional
Source choice and use the same chosen duration for seeds42/43/44. The original
Source study remains immutable. A choice at its duration-grid boundary remains
a limitation, not a convergence or optimality guarantee.

Assess four **positive fixed lambdas: 0.001, 0.01, 0.1, 1.0**. The fixed-retention
baseline is positive by definition; lambda0 is the separately recorded Full
Fine-tuning comparator from the Source study. No Source weights are retrained or
selected separately for favorable Fixed Retention results. The same predeclared
23 entity-budget combinations and three seeds require **276** 90-day Development
replays, including null-score and source-only initialization units.

Keep the source/target architecture, latent formula/scales/epsilon, target initial
epochs, online updates, batch size/order, learning rate and score rules unchanged.
One positive lambda applies to both initial target adaptation and online updates.
These values span four orders of magnitude as a finite compute budget; they are
not claimed to be exhaustive or equally appropriate across penalty definitions.
Parameter-retention loss has different units and is not calibrated by this grid.

Selection averages paired seeds within stations, then stations within budgets and
the three budget means equally, using original-unit MAE. Exact ties prefer smaller
lambda. Reuse the common candidate-accounting helper; require all cells and equal
coverage, retain nulls and reject score/count contradictions. All sources, profiles,
cohorts, code and outputs are identified. New outputs only; CUDA only for real runs.

No adaptive/proxy controller settings are changed automatically. This selects a
provisional Fixed Retention baseline on Development, not a Final lock, a completed
proxy/controller calibration or evidence that retention improves over lambda0.
The earlier five-method comparison used one-epoch Source weights and must not be
pooled with this new Source-duration family as if weights/configs matched. Every
remaining method requires comparable Development assessment and a matched rerun
under the eventual common Source configuration before Final approval.

Execution status: declared, not yet run. Actual results and Drive links will be
recorded after execution/verification. The sole schedule remains SPRINT_PLAN.md;
task acceptance remains in #23, with independent review and Final lock pending.
