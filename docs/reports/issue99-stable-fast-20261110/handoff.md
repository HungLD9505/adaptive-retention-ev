# Stable and fast expert experiment — 10 November 2026

## Outcome

**The selected controller does not beat strong Fixed retention.** This is a separate
method-change experiment under #99, authorized by the owner, rather than a change
to Report 1 or the frozen Final. It controls forecast weights, not retention lambda.
No scientific approval or fresh Final evidence is claimed.

| Arm | Macro MAE, kWh |
|---|---:|
| Stable Fixed retention | 3.2669999266187126 |
| Fast rolling-window GRU | 3.4198799774019424 |
| Calibration-optimal static blend | 3.303020734429099 |
| Selected Fixed-share controller | 3.291048172930262 |

Fixed-share reduces MAE by 0.3625% relative to the calibrated static blend, but
increases it by 0.7361% relative to stable Fixed. The new fast expert is individually
worse; a moving controller weight is not evidence of useful adaptation. Do not
replace the manuscript's main method or claim controller superiority on this basis.

The controller has lower station-mean MAE on only two of twelve stations; one
(ID 1303) is a numerically tiny near-zero case. Excluding that station does not
reverse the macro comparison (Fixed 3.5639999085 versus controller 3.5902343649).
Weights span 0.4307815379–0.5111811266, averaging 0.4958011684. The selected high
share and low eta keep mixing close to half-weight, rather than strongly favoring
the stable expert. Stronger tested updates had worse calibration scores, so this
evaluation result cannot justify choosing them retrospectively. These observations
explain the realized blend, without proving a universal failure of expert methods.

## Scope and selection

Unchanged 24→24 energy forecasting, UrbanEV/SZH Development, 14-day initial history,
90-day causal replay, seeds 42/43/44. Original calibration IDs are 1405, 2152, 1153,
1693. The twelve additional evaluation IDs and input/source fingerprints are in
[registration.json](registration.json). Both cohorts have prior Development exposure;
there is no unseen test set here. Some station periods have incomplete labels.
All comparisons use identical complete-day score masks within a station/seed cell;
station/seed cell MAEs receive equal weight.

Stable expert: reuse the preceding history study's locked lambda=1, Source epoch-10
GRU, three initial target epochs, Adam 0.001, one online epoch per complete arrival.
Fast expert: same initialization and initial epoch count, lambda=0, one online epoch
on a rolling calendar window of already available complete training examples.
It does not repeatedly train on inaccessible or imputed target labels.

Six fast recipes cross windows 3/7/14 days with learning rates 0.001/0.003. Learning
rate applies to both initial and online training. These are explicit bounded design
choices, not paper-prescribed EV optima. Windows bracket short and full-prefix
memory; rates test the established rate and a faster alternative. No exhaustive
search or optimality is claimed. Initial training uses the permitted prefix;
rolling-window training begins with online arrivals. Each window fits one optimizer
step, so the online step count matches stable Fixed, although the example counts
and computation differ. The fast arm needs a second GRU and additional training.

For each recipe, minimize original-unit calibration MAE exactly over a single
static mixing weight w in [0,1], using a weighted median of the MAE breakpoints.
Select the fast recipe by this static-blend objective. Then select Fixed-share eta
from {0.1,1,10} and share from {0.001,0.01,0.1} on the same locked expert pair and
calibration cohort. These are finite exploratory candidate sets; they do not
establish the best controller or a principled universal range. No evaluation labels
enter either selection. Calibration used the preceding protocol's first 28
registered origins, with the same actual complete-label availability.

Selected: seven-day window, learning rate 0.001, initial/static stable weight
0.4307815378871372; eta=0.1, share=0.1. The complete six-plus-nine search results are
preserved, including worse candidates. Selection is saved before evaluation replay.

## Formula and chronology

Forecast: `y_hat = w * y_stable + (1-w) * y_fast` in original kWh.
After a complete day's labels arrive, calculate each expert's daily MAE divided by
the fixed target prefix scale. Update:

```
p = w exp(-eta L_stable) /
    (w exp(-eta L_stable) + (1-w) exp(-eta L_fast))
w_next = (1-share) p + share (1-p)
```

This is the two-expert share-to-other update from
[Herbster and Warmuth, Tracking the Best Expert (1998)](https://mwarmuth.bitbucket.io/pubs/J39.pdf).
The project's normalization, GRU experts, search grid and application are local
adaptations; no regret guarantee for these unbounded energy losses is asserted.
The weight domain is [0,1], and with positive share the updated weights lie between
share and 1-share. These are forecast probabilities, not lambda bounds.

At each issued forecast, process only previously issued complete-day losses whose
availability time is no later than that forecast origin, ordered by arrival time
and then origin. Unscored/incomplete days cannot update weights. The update has no
per-calendar-day decay, so omitting intervening unscored forecasts leaves the same
weights at scored forecast origins. Error calculation afterward cannot influence
earlier predictions. Prefix scale and expert recipe never change using future data.

## Execution and verification

108 actual new fast-GRU invocations: 72 calibration and 36 evaluation. Stable
predictions are authenticated reuse, not newly trained runs. The original run
reported 60.46 seconds wall time on this machine with one Torch CPU thread;
verification and prior source/stable training are excluded. This is not a runtime
comparison or a promised runtime on another machine.

Run location, outside Git:
`/Users/quyenmanh/Developer/TFL-EV/runs/issue99-stable-fast-20261110-v1`.
Input root: `data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-14d` under the
original Developer checkout. Immutable prepared inputs were reauthenticated;
publisher raw archives were not freshly checked. Runtime: Python 3.12.13,
Torch 2.11.0, CPU, one thread. Parent repository commit:
`671ce22`; original executed script and mixing-source SHA-256 values are in registration.

The post-run clock hardening compares parsed timestamps, validates controller
parameters even for a single forecast, and has independent fixtures. Readback
requires its predictions, weights and events to reproduce the originally executed
outputs exactly on these inputs. Both source hashes remain recorded. No real run
was overwritten. The first readback failed on Python tuple-versus-JSON-list equality
for labels; normalized JSON comparison fixes that verification representation issue.
No numeric label difference occurred. A second readback completed the checks but
failed serializing NumPy station-win counts; converting counts to Python integers
resolved the report-writing error. The third readback completed successfully.

Readback authenticates saved expert vector hashes and recomputes original score
MAEs; reconstructs rolling windows from permitted prefixes and actual arrived
updates; compares example and optimizer-step counts; independently reconstructs
Fixed-share using direct normalized exponentials; checks every mixture prediction
and MAE; and reauthenticates prepared input files. See
[verification.json](verification.json) and [cells.csv](cells.csv).

The daily expert oracle is hindsight-only: MAE 3.0909500201550384. It chooses the
better expert *after* seeing each day's true labels and therefore cannot be used as
a deployable method or as evidence that the selected controller can realize that gain.
The previous three-lambda weekly oracle likewise provided limited hindsight headroom;
its separate diagnostic is not pooled with this experiment.

## Reproduction and limits

```
python -m tools.issue99_stable_fast --input INPUT --sources SOURCES \
  --inventory INVENTORY --stable-root HISTORY14 --output NEW_RUN
python -m tools.issue99_stable_fast_readback --input INPUT \
  --run NEW_RUN --output NEW_READBACK
```

Verified counts: 108 fast runs, 4,734 rolling-window updates, 2,628 independent
controller updates, 10,656 daily mixture vectors. Ten new regression fixtures cover
probabilities, direct exponential arithmetic, extreme losses, convex calibration,
equal-cell weighting, future/delayed labels, equivalent timezones and invalid data.

The bounded runner rejects existing output roots. It is fresh-run only: rolling
memory is not included in the standard runner checkpoint and resume is unsupported.
The calibration search and evaluation cohort are small and exposed; all results
are exploratory. The strong Fixed baseline is retained. Any further method search
must remain explicit and eventually be tested on an untouched cohort; repeated
selection on this cohort cannot substantiate generalization.
