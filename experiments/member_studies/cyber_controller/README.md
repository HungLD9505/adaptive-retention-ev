# Cyber independent study

Original implementation: PR #48, head
`31f8264ea0ed6c9c7958ce1f91c9f8f265e02af5`; historical report:
`docs/reports/member-cyber-controller.md`. Original scores and source/checkpoint
identities remain unchanged. They are not validated or replaced by this refactor.

## Input and replay corrections

The guarded IO version shares only the authenticated input/availability adapter
with the primary pipeline (`InputRun` and `Replay`), not its model or checkpoints.
It validates externally pinned manifests, roles, prefixes, features and scalers.
Predictor values and the calendar schedule are loaded without decoding label arrays.
Each forecast is written, flushed and synced to a create-only JSONL before the
separate label provider is called. Incomplete days never update. Late labels fail
closed rather than being used early. This bounded study supports zero configured
label delay and complete calendar blocks only; the primary runner supports the
more general delayed/pending schedule. No tail is silently discarded.

`study_data.py` owns input adaptation; `study_runner.py` owns model/update/replay;
`cli.py` owns configuration, create-only output and provenance. The old fixed
machine paths and overwritable checkpoint/output names are removed. Root offline
regressions cover the corrected IO boundaries; original model/controller fixtures
run separately with the command below.

No new real-data training or numerical reproduction was performed. The historical
runner selected days by a forecast/label join; the corrected calendar/input behavior
may change future outcomes. Never label old scores as outputs of the corrected code.

## Method and evidence limits

The study retains its original model/loss/controller settings: head width 128,
sample-standard-deviation source scales with a minimum clamp, five initial epochs,
Bmin 10 and its own bootstrap convention. These differ from the primary Final lock.
No model/controller parity is asserted. Historical keep decisions alone do not
prove protection against harmful switches. Target terminal states/resume are not
provided by this bounded study, and it is not a production benchmark entry point.

## Offline tests

```sh
python -m unittest discover -s experiments/member_studies/cyber_controller -v
python -m unittest discover -s tests -p test_cyber_study_io.py -v
```

The isolated historical requirements remain a record of that study's environment.
The root integration environment is tested with fixtures, not as a numerical
reproduction of the historical run. The guarded CLI supports `--help`; it requires
explicit input root, external budget-to-manifest SHA mapping, target identity and
a new output directory. Running it on real data requires a separate experiment
instruction; this repository cleanup launches no training.
