# Cyber independent study — preserved implementation, review pending

Related issue: #41; original PR: #48. Original implementation head:
`31f8264ea0ed6c9c7958ce1f91c9f8f265e02af5`.

This directory preserves the contributor's historical implementation and report.
It does not replace the primary runner or establish that the reported Development
replay satisfies the production availability/input contract. No experiment was
rerun, repaired retrospectively, or pooled with primary Final results during integration.

## Open findings from the integration source review

- `load_development_stream` opens and joins the complete label file before the
  replay; neither it nor the replay gates score/update using each label's
  `available_at` timestamps and `file_valid` flags. A label being present in a
  local file does not establish that it was available at the simulated clock.
  This missing contract does not by itself quantify leakage in a saved run.
- The loader supplies `energy_scale=1.0` when the forecast lacks that field,
  accepts infinite/negative labels through its current completeness predicate,
  and does not authenticate input manifests. These are unresolved input guards.
- Predictions live in memory; the returned payload has block decisions and counts,
  not the per-origin issued forecasts required for independent numerical replay.
  The CLI overwrites its fixed checkpoint names and output path on repeated runs.
- Source scale uses the sample-standard-deviation default plus a minimum clamp;
  its declared bootstrap defaults, head and initial adaptation also differ from
  the locked primary pipeline. No cross-implementation equivalence is asserted.
- The original report's statement that observed keep decisions confirm protection
  against unwarranted churn is unsupported: it requires future-outcome evaluation.

Do not use the real-data CLI as a validated production command. Resolve findings
in a separate reviewed change if this study is to be promoted; preserve historical
checkpoint identities and do not relabel existing scores as corrected results.
The current cleanup authorizes no new real-data training.

## Offline checks only

From the repository root, with Python 3.12 and the root model dependencies installed:

```sh
python -m unittest discover -s experiments/member_studies/cyber_controller -v
```

The directory's original requirements record its separate study dependency range.
Compatibility with the integration environment is checked by offline fixtures only;
this is not a numerical reproduction of its historical training run.
