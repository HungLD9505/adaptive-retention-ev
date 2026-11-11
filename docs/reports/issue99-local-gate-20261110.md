# Issue #99 local artifact gate (10 November 2026)

**Result: PASS for local artifact compatibility.** This gate permits preparing a
Kaggle pilot; it does not authorize scored search or establish a clean held-out
evaluation. The machine-readable [audit](issue99-local-audit-v2.json) records all
ZIP, manifest, file and checkpoint hashes. The audit script is
`tools/issue99_local_audit.py`.

The UrbanEV/SZH input ZIP matches the release catalog SHA-256 and passes ZIP CRC.
All five data files in each 7-day and 14-day package match their own manifest.
The 65,888 Source training rows match in order and value after removing only the
budget-specific `forecast.input_run_id`. Independently computed Source population
identities match `c77778935190a7acd3cc00c35d7940a5c9bd59fa3dc0dca14b86505ead87b760`.

The three seed 42/43/44 Source10 ZIPs match historical ZIP and epoch-10 hashes.
The repository checkpoint loader loaded all three with strict model weights and
Adam state; seed, ten completed epochs, architecture, config, run metadata,
source-derived latent scales and historical source-file hashes were checked.
The recorded source code commit is `ff42ea944bf05b4b77e2b730edf500b1fee6e851`.
The current `ev_models/data.py` differs from that version in access-control
refactoring; the Source identity computation itself is unchanged.

The current `InputRun` and `Replay` loaders accepted the extracted 14-day package.
The four declared Development targets have 4/12/13/13 initial trainable examples.
Every target has 90 scheduled days; issued forecasts number 90/59/59/59 in target
order 1405/2152/1153/1693. The ZIP labels contain 89/52/52/52 complete days;
these are file-completeness counts, not a measured run's scored coverage. The
remaining days are incomplete; the three 59-forecast targets each have 31
all-missing-history schedule skips. Label availability timestamps are no earlier
than the completed forecast horizon. The input manifest itself reports
`technical_success_with_coverage_limits`.

This audit authenticated the prepared input and checkpoint bytes, not the
publisher's underlying raw archive or its physical causality. Earlier Development
outcomes for this cohort were inspected, so subsequent scores are exploratory
unless an actually unused evaluation population is established. No new training,
Kaggle upload or scored search was performed for this gate.

After the gate, a separate two-tick CPU implementation smoke used the real 14-day
input and seed-42 Source10 for target 1405, then resumed for one more tick. The
runner saved two initial forecasts, processed one arrived label, and on resume
logged a finite one-step Adam hypergradient decision. This bounded smoke is not
the planned Kaggle T4 pilot, a Fixed search trial, or a forecast-effectiveness
result. Its ignored local artifacts are under `.cache/issue99-smoke-cpu-*`.
