# Matched Development comparator completion

Issue #23 / PR #52. This pre-execution declaration completes missing comparators
in the independently implemented Qyroven Source10 Development family, after the
identified controller calibration. It does not create another schedule or Final
configuration lock. Source1 diagnostic results remain a separate family.

Use the same identified Development cohort, 90 scheduled days, 7/14/28-day budgets,
seeds 42/43/44, source checkpoint family, target prefix/scaling, training schedule
and forecast/label gates. Independently verify the controller matrix before using
its provisional winner; recompute selection from every recipe cell rather than
trust a winner pointer. Calibrated proxy/parameter winners remain conditional
Development selection results, not unbiased held-out estimates.

## Actual unique methods and reuse

The completed collection must contain proposed Adaptive plus all nine baselines
and five ablation categories. It assembles authentic existing selected rows and
new missing runs, rather than retraining identical rows or calling aliases
independent evidence:

- Adaptive: selected controller recipe, all 69 paired entity-budget-seed cells.
- Full Fine-tuning: Source-duration study's selected-epoch rows, all 69 cells.
- Fixed Retention: fixed-positive-lambda study's selected rows, all 69 cells;
  this is also the Fixed-lambda ablation.
- Source-error, Uncertainty, Drift and Parameter Retention: each selected recipe
  from its four-config grid, 69 cells each. Authenticate the completed proxy matrix
  and recompute its selections before collection/analysis.
- New runs: Seasonal Naive, Target-only, Frozen Source, Online Best-lambda,
  Without Source Initialization and 7/28-day block sensitivity, 69 cells each.
- Without Confidence aliases Online Best-lambda only when selected delta is zero.
  For nonzero delta, add 69 mean-margin `without_confidence` runs retaining that
  same delta/Bmin; Online Best-lambda remains the unconditional mean selector.

Thus the new CLI runs 483 cells for a selected Bmin7/delta0 recipe. It runs 621
cells for a selected Bmin10/nonzero-delta recipe, including the bridge below.
Mandatory identities and null scores cannot be dropped to reduce the count.
Source-only initialization and unscored strata stay explicit. Full-method coverage
is not established until all actual artifacts and paired origin sets are verified.

## Block-size supported domain and causal interpretation

The unchanged controller requires bootstrap segment < Bmin <= block length.
A selected Bmin10 cannot be used with a seven-day block. For block7, explicitly
use Bmin7, retaining selected segment length (3 or 5), levels, delta, alpha and
resamples. Add a **14-day adaptive/Bmin7 reference** when selected Bmin is 10.
The seven-day block is compared against this 14-day reference at the same Bmin7;
the 28-day block is compared against the main 14-day adaptive at its selected
Bmin. These paired sensitivity comparisons isolate block length under their
respective common evidence requirements. A naive comparison of block7/Bmin7
against main adaptive14/Bmin10 is confounded and must not be called a pure block
size effect. The bridge is a diagnostic reference, not a tuned extra main method
or a best-of-two adaptive selection. No confidence-controller algorithm changes.

## Implementation and verification

`tools.matched_development` creates each baseline/ablation from the exact selected
reference config, changing only the declared method and block/evidence fields.
Source provenance, architecture, clock, per-target isolation, complete-label gates,
optimizer/RNG state handling and online update order remain in the unchanged runner.
No outcomes choose baseline/ablation inclusion. Output must be a fresh CUDA
location. The CLI validates expected cell identities, aliases, actual config
bindings, input identities, coverage counts and null score/count consistency.
A separate verifier and origin-set comparison must authenticate the actual daily
forecasts, label arrival, scores, commit chains and latest states before reporting.

Record code/Source/input/controller/cohort identities, exact configs, runtime,
updates, per-run reset GPU peaks, audit costs and logs. Separate reused Source
cost, startup/input validation, backing-up I/O and artifact verification/export.
Tests from overlapping setup are not isolated GPU runtime benchmarking. Preserve
old outputs and failures; partial-matrix resume remains manual/identified, not an
invented automatic guarantee.

## Status and remaining scope

264 fixture tests pass locally and on Colab with local Ruff lint/format and diff
checks. Ubuntu/Windows CI passed for code
`81334d25d6bb91561c8b4396e24425e2e046eb20` (run 40232042288). The matched
CLI is implemented and staged in a third serial worker, but real-data matched
training has not started at this snapshot. It waits for both calibration stages
to finish and verify/export successfully; a failed upstream worker prohibits launch. No laptop real-data training, Final evaluation or merge.

The selected UrbanEV cohort is small and nonrandom, budget IDs differ and physical
co-location may remain. Development calibration/comparisons cannot replace Final
inference or independent review. CHARGED still requires its own separate declared
Development experiments under the accepted upstream/time/overlap limitations;
never pool datasets/cities or present Shenzhen as independent geographic validation.
Exact feasible cross-dataset/Final capacity and independent immutable lock remain
unresolved acceptance gates, not grounds for silently removing mandatory scope.

## Actual serial staging identity

Code increment SHA-256: `1b858dd7adcbf10503d8ca04a3ac317e07dab96d17384fa17c215ab4b4b4a66a`.
Checkout `/content/ev-issue23-matched-development` is a clean exact checkout of the
recorded commit, cloned from the existing proxy checkout and advanced by that
identified increment. Fresh output is
`/content/qyroven-i23-matched-development-20261026-v1`.
The notebook's `MD_THREAD` was observed alive, waiting for the live `CAL_THREAD`;
controller process was still live at 99/276 runs. Eight 12-run backup chunks had
owner-Drive byte/hash readback at that snapshot. This is ongoing work, not a
completed matrix, server flush, second-account distribution or model ranking.
The third worker performs independent daily artifact verification and exports
coverage/config/code/source/log evidence after its own successful completion.
All selected-row collection, paired origin-set checks and scientific analysis
remain required after these staged jobs finish.

After Colab GPU eviction, the optional identified Fixed-study arguments enable
explicit new-runtime replay of Adaptive, Full Fine-tuning and Fixed Retention.
These add207 fresh references under the selected recipe1, giving690 target runs.
Old original matrices remain unchanged. This option exists to preserve fair
within-environment comparisons, not to retune a favorable source/configuration.
See the runtime-recovery handoff for actual limits and selection evidence.
