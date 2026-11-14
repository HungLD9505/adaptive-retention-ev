# EV manuscript evidence strengthening — 13 November 2026

Completed scope for issue #117: paired uncertainty on recorded forecasts, direct
related-work comparisons and an outcome-blind inventory for a possible confirmation.
The modeling task, model/loss/controller implementations and recorded predictions
remain unchanged. The prior-reference registry is pinned for reruns, so later report additions do
not silently alter the exposure scan. This analysis depends on the integration candidate in PR #116;
its own branch and PR target `dev`. No merge or `main` update is authorized here.

## Deliverables

- [Current manuscript](../../../report/evidence-review-20261113/adaptive-transfer-learning-ev.pdf)
  and [native source project](../../../report/evidence-review-20261113/README.md).
- [Primary paired-entity intervals](entity-intervals.csv),
  [calendar-block sensitivity](calendar-sensitivity.csv),
  [entity-level effects](entity-effects.csv), [analysis profile](analysis-profile.json).
- [Related-work comparison and primary locators](related-work.md).
- [Confirmation inventory summary](cohort-inventory.json).
- [Independent verification](independent-verification.json),
  [claim register](claim-evidence.json), [numeric summary](summary.json).

## What was recomputed

All 810 historical cell files were authenticated against the saved manifest.
Nine null units for UrbanEV entity 2193 remain null. Complete daily errors were
reconstructed from the matched stable/fast forecasts, labels and saved mixture
weights. Every group point estimate matches the prior full-precision ledger.
No model was trained and no scoring origin, source checkpoint or method setting
was selected again.

The primary estimator averages daily errors within an entity after averaging
its paired seeds 42/43/44, then weights entities equally within namespace/history.
For each of the two comparisons in each of 21 groups, 5,000 paired entity draws
produce marginal 2.5/97.5 percentile intervals. A replicate's percentage reduction
is computed from its two group means, not by averaging entity percentages.
An independent scalar implementation reproduced all 42 primary intervals.

Sensitivity jointly resamples entities and shared circular calendar blocks of
3, 7 and 14 days, with the same local-calendar indices across entities/arms.
Missing scheduled dates stay missing; seeds are not independent entities. If
any resample lacks a scored day for a sampled entity, the entire corresponding
interval is undefined. All 126 profiles and their failure counts are retained.
The resampling conditions on recorded forecasts; it does not retrain experts or
rerun a controller on a synthetic reordered training trajectory.

## Results and interpretation

Positive reductions favor adaptive fusion. All counts below are exploratory,
marginal interval descriptions on previously inspected entities and dates.
They are not multiplicity-corrected significance counts or independent tests.

| Reference | Lower group mean / 21 | Favorable gap interval | Adverse gap interval | Includes zero |
|---|---:|---:|---:|---:|
| Single Fixed | 18 | 13 | 1 | 7 |
| Matched calibrated static fusion | 12 | 3 | 5 | 13 |

All three favorable adaptive/static primary intervals are UrbanEV histories;
this does not make their mixtures better than single Fixed. Five intervals favor
static and thirteen include zero. At fourteen days, JHB improves its namespace
mean by 0.580% versus static while only 3/10 entity means improve; LOA and SPO
improve 4/10 and 2/10 entities. Thus positive group means do not imply broad
entity-level improvements.

At each calendar-block length, all six UrbanEV method/history intervals are
undefined due to sampled missingness. They are not imputed, silently dropped or
replaced by a preferred profile. Other profiles remain available in the ledger.
Selected small cohorts, shared source models, overlapping histories, circular
seams and nonstationarity limit population/future interpretation. Stronger
mixture-family results do not establish consistent adaptive-weight superiority.

## Outcome-blind cohort inventory

Only prepared manifests and entity metadata were read for eligibility. Target
label/forecast vectors, training records and checkpoints were not opened by this
inventory. The separate historical uncertainty analysis reads only already
exposed saved forecasts and labels.

| Namespace | Metadata eligible, exposure unresolved |
|---|---:|
| UrbanEV/SZH | 558 |
| CHARGED/AMS | 943 |
| CHARGED/JHB | 11 |
| CHARGED/LOA | 82 |
| CHARGED/MEL | 19 |
| CHARGED/SPO | 8 |
| CHARGED/SZH | 549 |
| **Total** | **2,170** |

There are 5,962 prepared IDs: 3,589 Source IDs, 116 identified prior target/support
IDs, 87 not ready or without a complete prefix example, and 2,170 remaining
metadata-eligible IDs. IDs and reasons are retained in the external
`inventory-pinned-v1/entity-exposure.csv`; prepared metadata and prior-evidence hashes are
in the committed summary. The scan covers identified scored repository ledgers,
the historical execution lock, the twelve-entity registration and graph support
metadata. It cannot exhaust earlier remote/untracked work or human inspection.
Consequently **zero entities are certified untouched**. No confirmation cohort
has been selected, promoted or executed. Remaining eligibility is a metadata
finding, not a measured forecast result or proof of independent test availability.

## Literature positioning

Five directly relevant EV studies are compared using publisher, author or
institutional sources: limited-data TL/MAML, cluster-specialized BiLSTM transfer,
inductive multi-quantile TCN, clustered federated domain adaptation and ChatEV
meta-learning. A sixth added reference motivates caution about adaptive holdout
reuse. The federated comparison is explicitly limited to the accessible abstract;
its numeric history budget is unknown. Preprint/issue/online-publication dates
are preserved. No cross-paper accuracy ranking or exhaustive novelty claim is made.

## Reproduction

Run from a checkout containing the identified code, supplying the actual external
saved-cell manifest and prepared-input root. Every output path must be new.

```sh
python -m tools.fusion_evidence --manifest SAVED_CELL_MANIFEST \
  --lock configs/issue23/final-execution-lock-candidate-v2.json \
  --output NEW_FUSION_ANALYSIS --resamples 5000 --seed 20261113
python -m tools.confirmation_inventory --input-parent PREPARED_INPUT_PARENT \
  --repository . --prior-manifest docs/reports/issue117-evidence-20261113/cohort-inventory.json \
  --output NEW_INVENTORY
python -m unittest tests.test_fusion_uncertainty tests.test_fusion_evidence \
  tests.test_confirmation_inventory -v
```

Run directory:
`/Users/quyenmanh/Developer/TFL-EV/runs/issue117-evidence-20261113-v2/`.
It retains the full metadata inventory, analysis outputs, independent scalar
oracle, figure/table generation, source-package extraction, compile logs and
page renders. The executed source is bound by the base commit plus explicit
script/module SHA-256 values in the analysis/inventory receipts; publication
commits preserve those exact source bytes. The earlier `v1` output attempt is
preserved separately and produced no scientific result.

## Completed checks

On clean commit `7fc0e9ced8eec1c2e25ad32cad776a8d7a78707a`, the root
suite passed 1,053 tests in 39.533 seconds with 12 skips. Fixed-adaptation and
confidence-controller suites passed 9 and 12 tests. Ruff lint/format passed
(682 files); source listing and frozen release checks passed (17 assets / 92 pins).
The 18-file extracted source package independently compiled to 20 matching page
texts. The final PDF has no embedded rasters, overfull boxes, missing characters
or unresolved references; ordinary underfull warnings remain. All pages were
rendered and visually reviewed. See [checks.json](checks.json) and
[report-check.json](report-check.json) for exact boundaries and byte identities.

## Verification boundary

New independent fixtures cover paired estimands, common-calendar identity,
missing-date failures, zero denominators, input invariance, invalid/mismatched
vectors, saved prediction tampering, metadata fingerprints and conservative
exposure status. Source-package and full README check receipts accompany delivery.
Normal underfull typesetting warnings are distinguished from clipping, missing
glyphs or unresolved references. Staged whitespace checks pass outside the two
byte-preserved vendor template files; their original trailing whitespace and CR
line endings are retained and their bytes match the previous verified source.

During development, a fixture expecting a defined interval despite a possible
all-missing sampled calendar was corrected to use complete data; a separate test
retains that missingness failure case. The first manifest adapter also rejected
the historical lock's list-form namespaces; explicit normalization resolved the
schema mismatch. No recorded results, fixtures for historical behavior or source
archives were modified to conceal those failures.

Raw archives were not freshly authenticated. Total source pretraining, search and
matched end-to-end model costs are not jointly measured; equal-compute superiority
is unknown. No new untouched-cohort result, full retraining replication or
statistical guarantee is claimed.
