# CHARGED — publisher preprocessing and data semantics (Issue #17, Step 2)

## Scope and evidence levels

This is a source investigation and a read-only AMS cross-file analysis, following the [six-city inventory in PR #26](https://github.com/HungLD9505/adaptive-retention-ev/pull/26). It does not implement city acceptance, a shared adapter, site exclusions, interpolation, model windows or cohort selection. Raw archives and existing runs are preserved. Issue #17 remains open; forecasting suitability, Shenzhen/UrbanEV overlap and the final contract remain later steps.

Keep three evidence levels separate:

1. **Publisher statement:** what the paper/documentation describes.
2. **Published code behavior:** what the pinned public scripts would do; not proof they generated every released value.
3. **Release observation:** a direct check of the acquired Hourly v3 archive. No pre-imputation observations or per-cell processing masks are reconstructed.

## Sources and reproducibility

- Paper: Guo et al., [Scientific Data, DOI 10.1038/s41597-025-05584-7](https://doi.org/10.1038/s41597-025-05584-7), especially *Data cleansing*, *Temporal alignment*, *Spatial formalization* and *Data Records*. Full text was retrieved through [Europe PMC XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12271547/fullTextXML); the Nature page and PMC HTML encountered access barriers, so their HTML was not used as evidence.
- Publisher repository, pinned at [`ff13cefe0c9e15073d02ad1e57efb4054dd70c5a`](https://github.com/IntelligentSystemsLab/CHARGED/tree/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a), also the remote `main` observed on 2026-10-17. All 28 locally inspected Python/Markdown files matched their Git blob identities from the remote tree. This pins source text, not release-build provenance.
- Dataset: [Zenodo v3, record 15814263](https://zenodo.org/records/15814263), standard `Hourly.zip`, 268,720,500 bytes; SHA-256 `1ec9c9513b64f3f492fe73261bf08a5955c268dfb876ef0fe283d05cc5a02fab`, publisher MD5 `099a592653ca74fa1f1051e9c23d6456`. Both were verified for the AMS run. No alternate release or `remove_zero` inputs were selected.
- [Source fingerprints and AMS run evidence](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/charged-preprocessing-evidence.json) record the paper XML hash, upstream file hashes, archive identity, executed analysis commit/script hash, config/scope, runtime and exact counts.

Reproduce the release checks with Python 3.12:

```sh
python -B -m tools.charged_semantics \
  --output runs/charged-semantics/issue17-step2-ams-v1-20261017.json
```

Use a fresh output filename for a rerun; existing evidence is refused. `--storage-root /path/to/storage` supports another machine with the catalog's directory layout. The tool streams four AMS members directly from the verified ZIP (`volume`, `duration`, `sites`, `chargers`), checks matching headers/clocks/row lengths, and produces descriptive JSON. It does not execute publisher scripts, extract files, change values or create a validity mask. Comparisons of static/hourly sums use `rel_tol=1e-9`, `abs_tol=1e-6`; the zero classification itself uses exact numeric zero.

## 1. What the publisher reports

The paper describes this workflow:

- Parse plug status/power into derived duration and energy; substitute rated power for a subset of MEL records when instantaneous power is unavailable.
- Filter geography/time; flag implausible values and outliers beyond four IQRs as missing.
- Impute charger series using temporal interpolation and further linear/forward/backward filling. Reported proportions are 10.70% and 0.99%, respectively; these are publisher-wide figures, not AMS percentages or masks of the acquired hourly cells.
- Round collection timestamps down to five-minute boundaries and average duplicate charger/timestamp records.
- Retain **each city's local time**, then aggregate duration/volume by summation and prices by averaging over time and clustered sites.

This explains why complete released matrices may contain estimates or replacements. It does not identify the origin of any particular zero. The paper describes the all-zero variant as inactivity; that interpretation is not independent evidence of physical inactivity at every released site.

## 2. What the pinned scripts actually show

| Source | Verified behavior | Consequence / limit |
| --- | --- | --- |
| [`aggregate_temporal.py`, lines 39–95](https://github.com/IntelligentSystemsLab/CHARGED/blob/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a/script/aggregate/aggregate_temporal.py#L39-L95) | Floors `time_new` to hours, sums duration/kWh, pivots and applies `fillna(0)` | Absent pivot combinations can become zero; absence of blank cells does not prove original completeness. The code alone does not establish every release zero's origin. |
| [`detection_and_imputation.py`, lines 38–69](https://github.com/IntelligentSystemsLab/CHARGED/blob/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a/script/optimize/detection_and_imputation.py#L38-L69) | Marks zero runs of at least a supplied threshold as NaN; uses time interpolation, then bounded forward/backward fill | This operation can replace actual zero values. An interior replacement may depend on later data. |
| [Same file, lines 72–142](https://github.com/IntelligentSystemsLab/CHARGED/blob/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a/script/optimize/detection_and_imputation.py#L72-L142) | `read_and_preprocess` uses threshold **24 samples**, then fills residual NaNs with 0; applies full-column quartiles with weight 4, linear interpolation in both directions, and further fills | Do not call this a 24-hour threshold without establishing the input frequency. Full-series quartiles/interpolation/backfill are not causal prefix operations. |
| [`remove_zero.py`, lines 36–54](https://github.com/IntelligentSystemsLab/CHARGED/blob/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a/script/optimize/remove_zero.py#L36-L54) | Intersects columns whose minimum and maximum are zero in duration and volume | The code's selection uses both metrics, rather than a per-hour validity test. Using full-period activity to choose target sites would look ahead; no such rule is adopted here. |
| [`api/dataset/common.py`, lines 95–163](https://github.com/IntelligentSystemsLab/CHARGED/blob/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a/api/dataset/common.py#L95-L163) | Fits price scaling to loaded arrays; optionally ranks sites using static total duration | This example loader is not a safe template for this project's permitted-data-only scaling or target selection. It has not been imported into this project. |

For a wholly zero series, the cleaning helper can turn the entire run into NaNs; without a nonmissing anchor, interpolation/filling cannot recover observations, and the wrapper's final zero fill can produce a wholly zero series again. This is a code-path inference, **not proof that this happened to AMS's 1,061 sites**.

### Important provenance gap

The pinned repository publishes helper/example scripts with placeholder paths. Searching its inspected Python files found the definition of `read_and_preprocess` but no external invocation connecting it to archive generation. The paper describes denoising before imputation; this helper applies zero-run treatment before IQR repair. Therefore, the paper and current scripts cannot be treated as an exact, replayable v3 build recipe.

No released per-cell original/imputed mask was found in the ten standard files per city. The original platform responses, build configuration/logs, and intermediate pre-imputation series have not been obtained. The additional publisher five-minute archives were **not** downloaded or inspected in this step. Whether they preserve original missingness requires separate investigation; their existence does not establish that they are untouched observations.

Consequently, the exact fraction of imputed hourly cells, which boundary replacements consulted future observations, and the physical reason for individual zeros remain unknown.

## 3. Direct AMS evidence: all-zero sites and paired values

The verified release contains 2,449 AMS sites over 4,392 hourly rows. The following checks align by the actual site IDs and identical timestamp labels, rather than assuming metadata row order.

| Check | Actual result |
| --- | ---: |
| Sites with all hourly volume values zero | 1,061 |
| Sites with all hourly duration values zero | 1,061 |
| Intersection of those two sets | 1,061 |
| Charger members of the 1,061 sites | 1,354 |
| All-zero-volume sites with positive static site total volume | 0 |
| All-zero-volume sites with positive static site total duration | 0 |
| All-zero-volume sites with any positive member-charger total volume/duration | 0 |
| Site charger-count mismatches against actual member rows | 0 |
| Static site total-volume mismatches against member-charger totals | 0 |

Thus the zero condition is consistent across released hourly values and static activity summaries. **These are related products of the same publisher pipeline, not independent sensors or operating-history evidence.** They cannot distinguish true no-demand sites from unavailable observations that upstream processing may have rendered as zero. No site has been removed, and no causal explanation has been assigned.

### Paired hourly cells across all AMS sites

| Released pair | Cells |
| --- | ---: |
| Volume = 0, duration = 0 | 6,060,587 |
| Volume > 0, duration > 0 | 4,695,189 |
| Volume > 0, duration = 0 | 205 |
| Volume = 0, duration > 0 | 27 |
| Total | 10,756,008 |

These 232 mismatched zero/nonzero pairs occur outside the wholly zero sites. Separate upstream processing, power/status derivation or other causes are possible; none has been proven for these cells. They are diagnostics, not automatic reasons to invalidate energy. Exact source-value examples are retained in the evidence JSON for traceability.

### Static/hourly totals do not reconcile

| Measure | Sum of hourly release | Sum of static sites metadata | Sites with unequal sums |
| --- | ---: | ---: | ---: |
| Volume (kWh) | 149,692,010.346366 | 239,175,391.291590 | 1,388 |
| Duration (h) | 18,388,657.432719 | 28,808,415.087280 | 1,388 |

The mismatch affects all 1,388 sites outside the wholly zero group. Static volume totals do reconcile with member-charger totals within the stated tolerance. The reason static totals differ from hourly totals is unresolved: period differences, processing stages or population differences must not be asserted without source evidence. Static full-period activity totals are not assumed available at simulated target deployment.

## 4. Header and clock semantics

### Four info.csv headers

Step 1 observed 8 header names and 9 row values in LOA/MEL/SPO/SZH, with the token `total_siteBSCAN_eps`. AMS/JHB headers, the publisher's [field dictionary](https://github.com/IntelligentSystemsLab/CHARGED/blob/ff13cefe0c9e15073d02ad1e57efb4054dd70c5a/data/README.md), and the paper's city-specific clustering radii support the interpretation that the intended fields are `total_sites` and `DBSCAN_eps`.

This is a **supported candidate mapping for review**, not evidence of a missing data value and not an implemented repair. Raw files remain unchanged. Any later parser override must be explicit, validated against actual site/charger counts, and recorded in processed-output provenance.

### Local clocks: partly resolved

The paper explicitly says city-local time was retained. This resolves publisher intent; the files themselves remain offset-free. Exact IANA zones, handling of daylight-saving repeated/skipped hours, and mappings to absolute instants are not demonstrated by that statement or by the 4,392-row grid. `floor('H')` in an illustrative aggregator does not prove the original interval endpoint or label-availability time. No UTC conversion, timezone assignment or DST repair is performed here.

## 5. Implications for subsequent review

| State | Evidence after Step 2 |
| --- | --- |
| File-valid | Step 1 file diagnostics remain available; paired anomalies and header interpretation are now documented. No new acceptance mask or city verdict. |
| Forecasting-eligible | Feasibility assessment remains Step 3; official windows/cohorts remain #18. File completeness alone is insufficient. |
| Strict-online-ready | **Not established.** Publisher-described and published-code imputation can use later values, and per-cell provenance/build history is absent. This is not a measured leakage rate or proof every cell leaks. |

Future-only influence cannot be undone merely by applying a chronological split to an already imputed release. It may affect historical inputs, labels and any comparisons based on them. A strict online claim needs stronger upstream availability evidence or a separately approved data/protocol decision. No core Report 1 requirement is dropped, and no replacement benchmark or method change is selected here.

Decisions requiring review include how to describe CHARGED's derived target and upstream limitations; whether further source/intermediate evidence can be obtained; and how future eligibility rules can use only permitted history rather than full-release activity. No all-zero rule is proposed for adoption in this handoff.

## 6. Verification and remaining limits

- **12 offline tests passed** on this branch (9 existing source tests and 3 new semantics tests); Ruff lint/format, source listing, pip check and diff checks passed. PR #26 is unmerged, so its separate inventory tests are not part of this branch.
- Real AMS archive analysis completed successfully. Exact run identity and elapsed time are in the committed evidence. Tests validate diagnostic logic and failure behavior, not research effectiveness.
- All six cities' publisher semantics were reviewed through common paper/code sources; the new paired/static empirical analysis covers **AMS only**. It does not establish matching zero mechanisms or mismatch rates in other cities.
- The source investigation is complete to the evidence available in this slice. Exact v3 build provenance, original missingness, cell-level interpolation lineage, DST conventions, physical inactivity, and static/hourly discrepancy causes remain unresolved and are explicitly carried forward. No source files, datasets, prior outputs or experimental settings were changed.
