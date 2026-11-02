# Input-reader boundary correction — 2026-10-26

## Finding and correction of earlier wording

The historical model consumer parsed shared JSONL rows before filtering by role or
entity. `InputRun.training()` decoded discarded training rows, including Final
initial-prefix arrays. The former #19 static evaluator also decoded shared forecast
and label rows before selection; the #21 replay constructor decoded other entities'
forecast histories before selection. Runner label delivery itself was already
restricted to the requested Development identity and availability time.

Those discarded rows were not returned for fitting, scored as Final targets, or used
to select configurations. This follows the explicit filter before result append/model
access. It does **not** justify the stronger earlier wording that no Final arrays
were decoded at all. That wording is withdrawn. Historical experiment outputs keep
their original code identity; no strict unread-Final boundary is retroactively claimed.
No Final fitting, tuning or evaluation result is reported.

## Implementation hardening

The consumer now authenticates the complete artifact bytes and filters the accepted
#18 writer's role/identity header **before JSON array deserialization**. It rejects
unsupported serialization instead of falling back to unrestricted parsing. Training
row counts must equal the identified entity summaries. Replay requests permit only
one ready Development target; the static evaluator decodes labels only for that
target's already-issued origin set. Prediction-field validation and label availability
checks remain. This is a narrow producer-profile adapter, not an operating-system
sandbox; metadata and artifact bytes can still be read/authenticated.

No raw/input bytes, split, scaler, tensors, forecasting task, loss, retention or
controller settings are changed. The first consumer in each scope previously paid
for parsing/validating a shared training file; cached later methods did not pay the
same cost. Historical elapsed totals are therefore pipeline observations, not isolated
method-speed rankings. GPU peak counters also were not reset between those cells.

## Verification

- 242 local offline tests passed, including spies that fail if an unselected role or
entity body reaches the JSON decoder, issued-origin-only label decoding, Final
request rejection, count failures and the existing source/target/runner regressions.
- A read-only real-input check compared every returned field and record order against
the pinned prior consumer at `a392505`, supplied only the same selected raw rows.
All65,888 Source examples at7d and all23 selected Development prefix groups matched
exactly:66,063 returned records in24 cases, including empty prefixes. The parity
check did not deserialize discarded role histories/labels and did not train locally.
- [Record hashes/counts](issue23-reader-parity.json) identify the cases and limitations.

The source/config/data identities of the earlier138+207 runs stay unchanged. An
additional fixed-reader GPU parity replay is recorded separately after execution;
it is an integrity check, not an extra independent comparison replication. Reproduce
historical analysis with its archived code (`a392505`) because its strict algorithm
hash check deliberately rejects a different reader implementation. Future training
must use the hardened reader and record its new code identity.

## Actual CUDA parity replay

Code `757612427293422f5e85acfc9bb4a7a73f621c37` passed all 242 fixture tests
on Colab. One preselected integrity case, UrbanEV 1405 / 7d / seed42 / Adaptive,
replayed the same 90-day schedule (92 ticks including label-delivery tail). All
92 forecast files are byte-identical to the pinned historical run. Final complete
branch-state hashes (model/optimizer/RNG), decisions, issued/scored counts,
original-unit MAE/RMSE, initial logs and online/audit steps match exactly.

The first harness compared live Python decision tuples to deserialized JSON lists
and rejected that representation difference. Persisted JSON decisions match with
no field differences. The original failed harness status/log is retained; no second
training run was performed to resolve it.

[Parity result](issue23-reader-gpu-parity.json), [Drive artifacts/hashes](issue23-reader-gpu-artifacts.json),
and [independent downloaded verification](issue23-reader-gpu-download-verification.json)
record the scope. The entire 9.58 MB ZIP was downloaded, SHA/CRC checked, all 92
forecasts compared again and the latest complete branch state CPU-loaded/content-
rehashed locally. This is an integrity replay, not an added scientific replication
or proof that every possible consumer invocation is isolated.
