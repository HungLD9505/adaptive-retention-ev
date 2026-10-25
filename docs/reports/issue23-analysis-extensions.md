# Selected Development analysis: contexts, proxy relationships and cost

Issue #23 / PR #52. These are explicit exploratory Development analysis proposals,
implemented while the Kaggle calibration batch is running. They do not alter
training, forecasts, controller decisions, tuning grids, cohorts or Report 1.
No Final result or independent analysis lock is claimed.

| Analysis | Definition and safeguards | Actual execution status |
|---|---|---|
| Load density | Authenticate the full context output, recompute its groups from current manifest-bound allowed-prefix metadata, then join selected entities. Sparse/dense/undefined groups retain explicit coverage and null outcomes. | All 21 threshold groups fitted and uploaded; full matched metric join pending. |
| Online phase | Fixed deployment-calendar days 1–30, 31–60 and 61–90. Calendar gaps remain gaps; no scored-day compression or favorable burn-in. | Fixture-tested; full matched analysis pending. |
| Proxy versus retention | For each selected proxy trajectory, pair its available policy signal with zero-minus-low and zero-minus-high candidate MAE on exactly the same decision-used days. Positive difference favors retention. | Fixture-tested; complete matched GPU collection pending. |
| Cost | Candidate count, Source ensemble members, initial optimizer steps, online/audit steps, inference/update/controller/proxy/audit timers, allocated/reserved GPU peaks, and reused Source training separately. | Extraction implemented; complete matched cost/capacity assessment pending. |

## Proxy interpretation

Signals are the recorded normalized Source error, normalized Source-ensemble spread
or drift descriptor signal defined by the existing baseline implementation.
The analysis rehashes forecasts/events and follows their prediction identities.
Source-error signals are checked against the paired independently verified Frozen
Source daily MAE divided by the same fixed target scale. Uncertainty/drift signals
are checked against their authenticated saved forecast payloads. Every signal and
candidate score used by a decision must have been available by that decision's
effective time; the day must fall inside its declared block. A later snapshot's
future signals cannot enter an earlier decision's block mean.

Both low and high comparisons are retained; the analysis does not choose whichever
looks best. Candidate differences describe the three learning trajectories forked
from their common block-start state, conditional on this controller's past path.
This is a same-block retrospective relationship, not a causal effect of retention,
an oracle or evidence that the signal predicts the next block's best policy.

Report descriptive Pearson r separately within each station/seed/budget/proxy.
Constant or fewer-than-two paired-block populations have undefined r. Average the
three paired seed correlations only if all are defined, then weight defined
stations equally. Include all per-seed values and counts of undefined stations;
the arithmetic mean of within-station correlations is not a pooled-population
correlation. No p-values, independent-block assumption or significance ranking.
Empty/insufficient-signal blocks remain recorded with null estimates. With only
about six block boundaries in a 90-day replay, these associations can be unstable.

## Reproduction and current boundaries

`configs/issue23/analysis-profile.json` explicitly identifies the fixed calendar
phases, density policy and proxy-relationship definition. Changed/absent extension
identities fail closed. Existing archived profiles and outputs remain untouched;
this is a new analysis output, not a replacement for earlier published bytes.
Clean committed analysis code and its identity are recorded in the new summary.

Run `tools.analyze_matched` with its five authenticated matrix/verification pairs,
the accepted input root and cohort, and the updated analysis profile. To include
load-density metrics, also supply:

```sh
--density-contexts DEVELOPMENT_CONTEXTS.json \
--density-sha256 686c9adf4b56d834787f98dd47d80059e214b7d57192bc4e0778c02a13ef0393
```

[Download the complete context output](https://drive.google.com/file/d/1CKJzrTO24nCEDa_gnNB8Km1TpuNlhJ29/view).
[Exact hashes, sizes and six-file byte-identical Drive readback](issue23-recovery-context-artifacts.json)
also cover the reconstructed controller matrix, selection, daily proof, latest-state
proof and original backup registry. Drive metadata reports shared=true; independent
download using another team account remains untested.

The still-running GPU batch remains pinned to `54131cbb8ce47f9d064b80f03956e8e62ec48346`.
Do not change that checkout while its subprocesses are active. Its original
collection output can be followed by a fresh-directory analysis using this newer
code only after required GPU stages and verifiers pass. The implementation has
295 local offline tests plus lint/format/diff checks; full real-data execution of
these extensions is not yet claimed.

Runtime counters are not an end-to-end wall-clock benchmark. Reused Source cost is
reported once, not once per target or silently omitted. Reconstructed controller
loop wall time remains null; setup, input reading, latent-scale extraction,
packaging, transfer and verification still need separate accounting. Audit timers
and extra uncertainty estimators must remain visible. Complete compute/storage
feasibility and matched method timing conclusions remain pending.

An adverse-switch margin has not been independently locked; retain descriptive
new-minus-old audit gaps without declaring a harmful-switch rate. Recovery time is
not invented without an identified stress/intervention onset. Sparse/dense
thresholds and all analysis definitions require review before any Final lock.
