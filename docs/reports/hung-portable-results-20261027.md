# Portable daily-error reconciliation — 27 October 2026

Related: #22, #23, #10 and PR #72. This handoff supplements the existing sprint
schedule; it does not change the research method or authorize Final.

Existing result JSON intentionally omits per-day errors. Combining its summary
MAE/RMSE values across providers would lose paired-day intersections and could
produce invalid comparisons. `tools/hung_portable_results.py` exports the existing
pinned scorer's daily absolute/squared errors and label hashes after rechecking
checkpoint, manifest, input, initialization and proof hashes. The exported records
retain historical run IDs, cost fields and code provenance.

Completed CPU receiver outputs can be consumed through an explicit read-only mount
relocation. The original receiver proof, official verify-only exit/log and catalog
hash are checked before any paths change. Content hashes remain unchanged. This
does not retrain a model or repeat the official dispatcher verification.

The merger requires SHA-pinned exports and explicit disjoint expected job sets.
Repeated Main anchors, duplicate logical runs, unmatched status, altered daily
errors or metrics, and unequal scope/plan/scorer are rejected. Pairing uses the
existing scorer's exact shared-day and label-hash checks, then station-first seed
aggregation. Missing labels stay missing; partial cohorts are not globally ranked.
An export's hash is an integrity binding, not independent scientific approval.

## Actual local parity

The existing 191-run through-shard0031 catalog was exported in 29.051 seconds,
exit 0: 101 scorable and 90 zero-scored. Reconciliation produced exact logical JSON
equality for runs, counts, all 68 paired cells, 57 blocked pairs and station-first
metrics against the existing report worker output. Metadata and transport formats
differ. Details and hashes are in `hung-portable-local-parity-20261027.json`.

Eleven focused offline tests passed, including a real saved-checkpoint fixture,
cross-collection day intersection, corrupt evidence, duplicate anchors, initialization
and label mismatches, missing labels and explicit mount relocation.

`kaggle_portable_shard0008_v1.ipynb` prepares a CPU-only export from completed CPU
receiver version 362658126. Its expected original receiver-proof SHA is
`16d39bce5ed7b5998204ca592490152d3810c550b658dab8dd76a2dcade6142b`.
It emits a small compressed, hash-checked transport of daily error statistics.
At this report's creation the notebook is prepared; actual cloud export and
cross-provider reconciliation are not yet claimed. The running training and CPU
receiver queues and their source pins are unchanged.
