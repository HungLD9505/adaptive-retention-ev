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
[Exact hashes, sizes and byte-identical Drive readback](issue23-recovery-context-artifacts.json)
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

## Recorded switching and stronger independent audit verification

The next analysis revision adds the explicit profile identity
`recorded-calendar-next-block-drain-separated-v1`. It reads every recorded decision
in chronological order, checks active/selected-level continuity and paired-day
counts, then reports switch counts, decision opportunities, reasons, insufficient
evidence, missing-day counts and the actual deployed MAE/RMSE in the following
calendar block. Missing labels remain missing; the final partial block is clipped
to the forecast horizon. Rates use scheduled decision opportunities within that
horizon, with actual issued/scored coverage alongside them. Fixed single-policy
methods have no switching opportunity and a null rate, not a claim of superior
stability. All sites and all paired seeds remain present, including unscored sites;
seed-specific paths/counts, ranges and equal-site summaries are descriptive.

The runner continues polling after the forecast horizon to drain available labels.
For example, block7 can record a decision on day91 in a 90-day replay. That event
is retained as drain-only; it cannot change a forecast in the reported horizon and
is excluded from deployed switch/opportunity counts. A keep decision may still
follow a previous switch; next-block errors remain descriptive actual policy-path
outcomes, not causal treatment effects or recovery time. Different block sizes
retain their own opportunity counts and actual candidate/update budgets.

Previously, `tools.verify_comparison` independently recomputed candidate/deployed
errors but only hashed audit forecast/event bytes. The enhanced verifier also
recomputes the old-policy audit forecast's original-unit MAE using the same arrived
complete label vector, pairs it with the deployed error, and checks each saved
daily normalized gap and audit mean/count. Report decisions and audit summaries
must exactly match authenticated event payloads; an altered report or even a
hash-consistent false audit mean is rejected. Unfinished final audits are not
invented as completed summaries. This does not independently rerun the statistical
decision rule or establish confidence coverage; existing controller tests and
runner isolation evidence retain those distinct scopes.

New proofs must use fresh output names. The older independent proofs and archives
retain their original narrower scope and bytes. The remote training remains
unchanged; this is read-only verification/analysis. 316 fixture tests and local
lint/format/diff checks pass, including a corrected older core-analysis fixture
whose synthetic report audit had previously lacked a corresponding event. No
scientific expected value or historical artifact was changed to pass that test.
Real controller audit re-verification and staging this newer analysis are pending
at this code commit; their actual results must be recorded after execution.

## Actual original-controller re-verification and switching analysis

Code `e13fc42a3bfa688dfc08c95b7678d72ecb60cad0` passed 316 tests/checks and
[Ubuntu/Windows CI40241925450](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40241925450).
The enhanced verifier then read all 276 recovered original controller runs and
51,060 daily files, checked 1,656 decision-event identities, independently
recomputed 752 old-policy audit forecast scores and verified all 61 finalized
audit summaries. Every field for all 276 rows of the older daily proof remains
unchanged; the new proof extends its scope without replacing archived evidence.
This was CPU read/verification, not local training or new GPU outcomes.

| Original calibration recipe | Recorded switches over 69 seed/entity/budget replays | Finalized audit summaries | Unfinalized last-block audits |
|---|---:|---:|---:|
| 0 | 31 | 31 | 0 |
| 1 | 27 | 26 | 1 |
| 2 | 0 | 0 | 0 |
| 3 | 4 | 4 | 0 |

Recipe1's unmatched last switch is station2005, budget28, seed44, effective
2023-02-23 (day84). Its next14-day audit cannot finalize within the90-day forecast
plus label-drain window; it is not filled with a zero gap. Recipe2 never switches
in these original runs. That describes its realized path, not a general proof of
stability or a reason to delete a required comparator. Selection still recomputes
recipe1, and its earlier conditional MAE remains worse than selected Fixed
Retention. These are four calibration recipes, not four additional independent
method trials or the still-pending matched Kaggle collection.

For recipe1, equal-site means of the three-seed switch counts are0.4444/0.5000/
0.2593 for budgets7/14/28; insufficient-evidence opportunity fractions are0.5556/
0.6250/0.5926. These denominators retain all6/8/9 selected IDs, including null-score
sites. Different budget populations, missing labels, possible co-location and
fixed seeds prevent a causal budget or population-stability interpretation. Full
per-seed paths and post-boundary coverage/errors are in the downloadable summary.

[Exact identities and reproduction](issue23-switch-audit-evidence.json) ·
[complete analysis/proof/producer/code package](https://drive.google.com/file/d/13-fFNgjsj0yRFqZklBPJ7wOEixa4WCdv/view).
The142,548-byte ZIP passed anonymous byte/hash readback, CRC and all10 member
fingerprints. It retains the first ad-hoc producer's final-status `KeyError`
(`selected` versus `provisional_choice`) and its output/log, plus the corrected
producer and successful fresh v2 recomputation. Both summaries agree in every
non-producer-identity field. No scientific expected value or training artifact
was changed. Independent teammate reproduction remains pending.

An exact-source cell is now staged after the complete primary-export gate in the
Kaggle editor. Execution was requested, but the inspected UI does not expose a
validated queue status; it has not executed. It requires prior GPU success and
both export catalogs, then loads the pinned newer code, runs fixtures, re-verifies
controller/proxy/matched audits and writes a fresh full analysis plus a small
supplemental ZIP. Existing training checkout, forecasts and exports stay unchanged.
Actual full-collection execution, transfer, capacity acceptance and peer review
are still required.

## Committed verification and remote staging

Implementation `5fa321fea2c9097d92d0d4fc4e6965ff05f059cf` passed all 295
local fixture tests, lint/format/diff checks and [Ubuntu/Windows CI40237694408](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40237694408).
The full stored context output was then re-authenticated against all 21 fresh
namespace/budget metadata groups; every group matched exactly. No model training
was performed by these local checks.

All six shared recovery/context files and the incremental analysis code bundle
were downloaded without browser cookies or account authentication; their sizes
and SHA-256 identities matched. This now verifies anonymous-link retrieval, not
independent reproduction by another developer. The bundle extends the pinned
training commit and has SHA-256
`edc0d2679161139c145da928eb2c265f0543b68a2484cebf0d5d0e15745a24f0`.

A new Kaggle cell is queued behind the current complete primary batch. It requires
a successful prior batch exit before checking out this newer analysis code, runs
its fixtures/checks, downloads/authenticates the context output, CPU-checks every
latest proxy/matched target state, then writes a new context/proxy summary. It
does not update the active GPU checkout or overwrite earlier analysis outputs.
The queued cell has not executed yet. A private Quick Save with output was
requested at the 116-run calibration observation; do not claim uninspected
snapshot contents or future outputs as verified durable backups.
