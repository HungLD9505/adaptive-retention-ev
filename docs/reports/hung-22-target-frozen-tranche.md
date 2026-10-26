# Hung Issue #22: Target-only and Frozen Source adapter tranche

This branch stacks on PR #57, and therefore on PRs #56, #53 and #46. It uses
Hung's model, training step and accepted input replay schedule. It does not
reuse Qyroven code, weights or execution results. Only offline fixture runs
were performed; there is no new real-data Development or Final result.

## Method definitions and provenance

`target_only` constructs a seeded GRU without loading a Source checkpoint. Its
separate `target-only-init` command trains exactly one pass over the accepted
Development target's pre-deployment complete examples, with a declared batch
size and Adam learning rate. Zero-prefix targets retain a distinct zero-step
initialization stratum. The create-only initial checkpoint and manifest bind
input manifest, role/entity, budget, scale, seed, architecture, steps, optimizer,
code hashes and checkpoint SHA. Replay rejects a Source checkpoint argument and
records `source_checkpoint_sha256: null`.

`frozen_source` loads a hash-checked Source checkpoint with its own Source input
binding and dataset/city identity. The model remains eval/frozen. There is no
target adaptation or online optimizer; update steps and update time stay zero.
Its replay binding records the exact Source input-manifest and checkpoint SHAs. Source pretraining
cost, when available in that run's manifest, is referenced separately as reused
upstream work and is not silently charged as a new target run.

Both methods use one model and the same authenticated Development daily
schedule, scale, created/missing origin rules, delayed full-label gate and
original-kWh scoring. Only Target-only updates after all 24 labels arrive.
Incomplete or unavailable days stay unscored/null, never zero-filled. Each
method's replay checkpoint contains model, optional Adam state, pending labels,
issued forecasts, cursor, RNG, cost counters and exact method/input/initial
checkpoint binding. Resume requires a larger horizon with matching code,
method, source/initial checkpoint and configuration; historical runs are not
relabelled. Each newly issued forecast or skipped origin gets a create-only
`forecast-N.pt` snapshot and an fsynced append-only `forecasts.jsonl` record
before its label row is parsed. The record binds the exact prediction, origin,
method/input/code and snapshot SHA. An independent verifier checks every
record against its snapshot and the accepted schedule; completed manifests
bind the journal SHA and count. Every journal covers contiguous origins from
index zero. A resumed output copies all verified ancestor forecast records and
their immutable snapshots into the new output, so the final evidence is
self-contained. The final runner checkpoint must contain the same issued
predictions and scores; scored label vectors are cross-checked against the
authenticated Development label artifact. The verifier independently derives
which complete labels had arrived by the bounded/full replay cutoff, and binds
the expected score/update events and cost counts. A scored day cannot be
rewritten as null. If a run crashes after issuance,
resume accepts only the latest committed forecast checkpoint and replays its
label in a new output directory. A torn final append is ignored only for an
interrupted run; a malformed complete line or missing middle row is rejected.
Completed runs verify the full journal hash. The output directory and each
forecast checkpoint are create-only. This is a durable issuance boundary for
future Final lock, not Final execution evidence.

The one-model cost record includes inference calls/time and Target-only update
steps/time; no audit or unused candidate is charged. Total replay duration
includes verification, loading and I/O. Logical model/optimizer tensor bytes
are reported separately from process memory and GPU peak allocation. Target
initialization elapsed time lives in its own run and is linked from replay.

## Reader correction

The earlier shared Hung replay reader decoded every JSONL row before selecting
one Development target. This branch filters the accepted writer's identity/role
header before JSON decoding forecasts, entities, schedule and labels. The input
manifest still authenticates whole artifact bytes. A regression fixture places
malformed non-target/Final payloads behind valid headers and confirms the same
selected forecasts, events, coverage and metrics as the unmodified fixture.
This corrects a consumer boundary; it does not imply previous runs fitted,
tuned or scored Final rows, and it does not retroactively change their identity.

## Verification and remaining work

Offline tests cover pre-deployment one-pass Target-only initialization, no
Source use, Frozen Source weight immutability, same-origin and null-day parity,
exact SHA rejection, split/resume parity for each method and the reader
boundary. A simulated crash at label-read verifies durable issuance and
interrupted resume parity for both methods. Tests also reject missing middle
journal rows, malformed committed prefixes and final checkpoint divergence in
prediction, score or Development label, including masking a scored day as null.
No large dataset, GPU training or Final set is opened by these tests.

Seasonal Naive remains separately proposed in PR #45. Adaptive and mean/fixed
three-candidate selection policies are in PRs #46/#56/#57. Source-error,
Uncertainty and Drift proxy controllers, parameter-retention and no-source-init
ablations, 7/28-day block variants, complete Development calibration, all
accepted UrbanEV/CHARGED city matrices with three seeds, measured capacity,
independent review, immutable Final lock and full report are still required.
The Target-only and Frozen Source adapters here are implementation/fixture
readiness only, not accepted comparison cells or scientific effectiveness.
