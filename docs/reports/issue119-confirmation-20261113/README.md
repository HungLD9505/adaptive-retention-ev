# Locked new-identifier confirmation — 13 November 2026

Issue [#119](https://github.com/HungLD9505/adaptive-retention-ev/issues/119).
Dependencies: [#118](https://github.com/HungLD9505/adaptive-retention-ev/pull/118)
and [#116](https://github.com/HungLD9505/adaptive-retention-ev/pull/116).

**Verified outcome:** all 46 selected Development identifiers and three paired
seeds completed. Adaptive has small positive equal-namespace point estimates
against single Fixed and matched static, but both primary intervals include zero.
The prespecified dual-comparator criterion is **not met**. This is a completed
negative confirmation outcome, not an execution failure or a reason to retune on
these outcomes.

## History and selection

The audit checked 107 fetched Git refs, 1,836 reachable metadata objects and
45,481 local run metadata files, with zero skipped files or read failures.
The registry excludes 278 namespace/identifier pairs, including 78 ambiguous
identifiers excluded across namespaces. Target registrations and attempted runs
count as exposure; raw catalogues, coordinates and readiness lists alone do not
prove model execution. The earlier overbroad catalogue-only audit is retained in
external `issue119-confirmation-20261113-v1`; it did not read selected target
vectors and was corrected before selection.

The full scan manifest and referenced exclusion evidence remain outside Git.
[history-audit.json](history-audit.json) and
[history-exclusions-index.json](history-exclusions-index.json) preserve the small
receipts. This establishes absence of recorded target execution/registration in
that bounded audit, not absence of all human inspection or unrecorded remote
runs. Physical aliases across dataset releases are not certified.

Selection used ready fourteen-day Development entity metadata with at least one
complete prefix example and no audited exclusion. Eligible counts were 248
UrbanEV/SZH, 450 AMS, 1 JHB, 38 LOA, 4 MEL, 1 SPO and 268 CHARGED/SZH.
A single fixed SHA-256 ranking selected up to ten per namespace, including all
where fewer remained: **10 + 10 + 1 + 10 + 4 + 1 + 10 = 46 IDs**. No error or
label vector entered selection, and no selected ID was replaced after outcomes.
The exact cohort and rank digests are in the
[protocol](../../../configs/issue119/new-entity-confirmation-lock-v1.json).

Implementation commit: `ea88718`. Cohort/objective lock commit:
`6ef963d00415b79e4075975f3944e716b55005bb`, committed before selected target
forecast/label vectors were decoded. Protocol SHA-256:
`f5e5eca69f1beb31f8ad4fe7f9963301de555e622e731b5fe1cc98317e77f425`.
Before execution, an exposed-entity parity run reproduced both archived experts
exactly (maximum vector difference 0.0 kWh); see
[exposed-parity.json](exposed-parity.json).

## Recipe and coverage

- Reuse 21 namespace-specific Source10 checkpoints; no new source training.
- Past 24 hours to next 24 hourly energy values, 14-day initial target prefix,
  seeds 42/43/44, 90 scheduled daily origins.
- Stable: Fixed latent retention lambda 1, three initial target epochs, one
  online epoch for each newly arrived complete daily example.
- Fast: lambda 0, the same initialization and three initial epochs; one online
  update over the trailing seven calendar days of eligible arrived examples.
  Fast is source initialized and is not target-only.
- Adam learning rate 0.001, batch 64, unchanged GRU/loss/scaling.
- Static: stable weight `0.4307815378871372`; adaptive starts at the same weight,
  eta 0.1 and share 0.1. All were selected previously and frozen here.
- Adaptive changes forecast weights, **not lambda**. Both fusion arms replay the
  exact same saved expert forecasts with complete delayed feedback.

All **138 ID–seed cells**, **276 target expert trainings** and seven namespaces
completed; no failures and no null targets. There are 3,948 scored ID-days per
seed out of 4,140 scheduled: four UrbanEV IDs have 52 days, one 51, one 89,
and four 90; every CHARGED ID has 90. Missing outcomes are not zeros.
[entity-results.csv](entity-results.csv) retains ID-level coverage and outcomes.

## Results

MAE is in kWh; lower is better. Bold marks the best displayed MAE among all four
arms. Percentage reduction is positive when adaptive improves the named reference.
Seeds are first averaged per ID, then IDs per namespace. Namespace kWh means
are never pooled across different demand scales.

| Namespace | IDs | Fixed | Fast | Static | Adaptive | vs Fixed % | vs static % |
|---|---:|---:|---:|---:|---:|---:|---:|
| UrbanEV/SZH | 10 | **7.4023** | 8.8496 | 8.1106 | 7.9944 | −8.00 | +1.43 |
| CHARGED/AMS | 10 | 16.2823 | **16.2107** | 16.2287 | 16.2344 | +0.29 | −0.03 |
| CHARGED/JHB | 1 | 8.0410 | 8.4356 | 7.9544 | **7.9147** | +1.57 | +0.50 |
| CHARGED/LOA | 10 | 2.0621 | 2.1082 | 2.0371 | **2.0317** | +1.48 | +0.26 |
| CHARGED/MEL | 4 | **10.9073** | 11.6425 | 11.1002 | 11.0267 | −1.10 | +0.66 |
| CHARGED/SPO | 1 | 8.4985 | **7.6644** | 7.7956 | 7.8368 | +7.79 | −0.53 |
| CHARGED/SZH | 10 | 4.2698 | 4.3512 | 4.1675 | **4.1578** | +2.62 | +0.23 |

Primary objective: equal-namespace mean of the seven percentage reductions.
Prespecified 10,000 paired entity/shared-calendar seven-day resamples,
seed 20261113. Two contrasts share family alpha 0.05, using alpha 0.025 per
contrast (nominal 97.5% percentile intervals; approximate conditional coverage).

| Reference | Reduction % | Primary interval % | Lower group MAE | Lower ID MAE |
|---|---:|---:|---:|---:|
| Single Fixed lambda 1 | +0.6653 | [−3.6209, +3.3176] | 5/7 | 35/46 |
| Matched static fusion | +0.3610 | [−0.0449, +0.8399] | 5/7 | 28/46 |

Four of the 35 strict wins against Fixed (AMS IDs 1889, 617, 2366 and 1733) are only about 1.43e-9 kWh each. They are numerical-scale differences, not practical gains. A **posthoc** 1e-6 kWh absolute tolerance leaves 31/46 gains against Fixed; the strict count and locked primary analysis remain unchanged. The [JSONL review supplement](../issue121-jsonl-review-20261113/README.md) closes the original Git-extension omission.

Both intervals include zero. Three-day sensitivity also includes zero:
[−2.7635, +3.2716] against Fixed and [−0.0276, +0.7623] against static.
For fourteen-day blocks, two out of 10,000 replicates are undefined in each
contrast, so **both entire intervals are undefined** under the locked rule;
no invalid replicate is dropped or primary profile replaced.

**Interpretation:** these results do not confirm consistent superiority of the
adaptive mechanism to both controls. Static accounts for much of the fusion
benefit; the additional online-weighting gain is small and heterogeneous.
UrbanEV remains 8.00% worse than single Fixed despite improving on static.
JHB and SPO each contain one eligible new ID, so their group estimates cannot
support population-wide claims. Frozen historical dates and Source10 models do
not test a new future period, city or dataset. This is new-ID evaluation relative
to recorded use, not universally certified untouched Final data.

## Independent verification

[independent-verification.json](independent-verification.json) records a fresh
readback of all selected original label vectors and availability times, all
saved expert predictions and scores, **25,392 chronological tick commitments**,
**23,688 expert daily scores**, and **276 latest full checkpoints**. Source
checkpoint bytes/metadata, input file bytes, target bindings, model finiteness,
constant expert coefficients and zero virtual updates are checked. Historical
state bytes were pruned by the declared latest policy; their commitments remain.
This is software replay, not physical issuance-time certification.

The verifier directly computes exponential expert likelihoods without the
production mix helper, and independently reconstructs bootstrap intervals using
calendar multiplicity matrices rather than the summarizer's vector gathers.
Both reproduce saved predictions, daily errors, weights, group means, primary
contrasts and all three sensitivity profiles. It does not rerun training.
The runner's earlier exposed parity receipt is separate from this verification.

## Reproduce

Keep prepared inputs, original Source10 checkpoints and large outputs outside
Git. `BASE` below is their storage root, not the repository checkout. The current
lock references relative paths under that root. Use a fresh output destination;
the commands intentionally refuse replacement. To reproduce the exact executed
implementation, use clean commit `6ef963d` for execution and the PR head for the
separate verifier (the executed-code fingerprints must still match).

```sh
BASE=/path/to/external/TFL-EV
OUT="$BASE/runs/issue119-reproduction-new"
python -m tools.confirmation_run \
  --protocol configs/issue119/new-entity-confirmation-lock-v1.json \
  --input-parent "$BASE/data/inputs/issue18-input-handoff-v1-20261019" \
  --base "$BASE" --output "$OUT/execution" --workers 3
python -m tools.confirmation_summary \
  --protocol configs/issue119/new-entity-confirmation-lock-v1.json \
  --run "$OUT/execution" --output "$OUT/analysis"
python -m tools.confirmation_verify \
  --protocol configs/issue119/new-entity-confirmation-lock-v1.json \
  --run "$OUT/execution" --analysis "$OUT/analysis" \
  --input-parent "$BASE/data/inputs/issue18-input-handoff-v1-20261019" \
  --base "$BASE" --output "$OUT/verification.json"
```

Actual output root:
`/Users/quyenmanh/Developer/TFL-EV/runs/issue119-confirmation-20261113-v2/`.
`history/scan-manifest.json` preserves the full scan identity; `execution-v1/`
contains target checkpoints, committed forecasts and score events; `analysis-v1/`
contains the unrounded analysis. Old audit/parity/verification attempts remain.
Raw publisher archives were not downloaded or freshly checked for this run;
prepared input and source-checkpoint bytes were authenticated.

The updated [manuscript](../../../report/confirmation-review-20261113/adaptive-transfer-learning-ev.pdf)
preserves the earlier report and adds a separately labelled locked evaluation.
No historical method or outcome is silently replaced. GitHub review and CI are
required before any merge; this handoff does not authorize merging.
