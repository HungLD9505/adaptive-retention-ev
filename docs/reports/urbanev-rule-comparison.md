# UrbanEV QC rule comparison — review response for PR #25

## Question and scope

Does requiring valid `duration` remove otherwise complete hourly energy labels? Compare:

- **Rule A:** all 12 unique on-grid five-minute `volume` values are finite and nonnegative.
- **Rule B:** all 12 unique on-grid `volume` AND `duration` values are finite and nonnegative, as in the existing pipeline.

Both rules use exactly the same source records, requested window, clock convention and structural constraints. They sum interval energy, do not interpolate or prorate, and preserve zeros. This is an audit of rule impact, not a pipeline rewrite or a decision that either rule certifies physical correctness. The pipeline predicate and previous outputs are unchanged.

All 1,682 station files / 87,679,296 unique source-grid samples were compared. Each input SHA-256 matched the original full-run record. Independent Rule B retained-hour counts matched the existing pipeline **at every station**, not only in the total.

[Numeric evidence](urbanev-rule-comparison.json), including examples, token classifications, monthly patterns, per-hour sample-count histograms, input lineage and executed analysis identity. Full per-station comparisons remain in ignored local run storage.

## Results

| Quantity | Rule A | Rule B |
|---|---:|---:|
| Requested station-hours | 7,306,608 | 7,306,608 |
| Retained hours | 5,745,899 | 5,745,899 |
| Rejected hours | 1,560,709 | 1,560,709 |
| Retained share | 78.64% | 78.64% |

**Hours rejected only because duration was invalid: 0. Stations affected by such extra losses: 0.**

The explanation is exact validity co-occurrence in this release:

| Five-minute sample classification | Count |
|---|---:|
| Valid volume and valid duration | 69,123,930 |
| Invalid volume and invalid duration | 18,555,366 |
| Valid volume, invalid duration | 0 |
| Invalid volume, valid duration | 0 |

All invalid tokens in these two fields were **blank strings**. No negative, nonfinite or malformed numeric tokens were found for them in this scan. Thus no valid energy value is currently lost solely because its companion duration is blank. This is an empirical property of these bytes, not a rule about every UrbanEV release or every future input.

### Impact of demanding a complete 12-sample hour

| Valid volume samples within hour | Hours |
|---|---:|
| 0 | 1,531,778 |
| 1–10 | 21,522 |
| 11 | 7,409 |
| 12 | 5,745,899 |

There are 28,931 partially populated hours, including 7,409 hours missing exactly one valid volume. The majority of rejected hours have no valid volume at all. Rule A/B comparison does not establish that twelve is statistically optimal or that missingness is random. The rule preserves an exact one-hour target without inventing unobserved energy. Accepting partial sums or extrapolating would change the target/measurement assumption and requires a separate reviewed proposal; this audit does not do so.

## What do the volume/duration disagreements look like?

Missingness and numerical consistency are different questions. Among samples where both fields pass the finite/nonnegative test:

| Pattern | Samples | Stations |
|---|---:|---:|
| volume = 0, duration > 0 | 39,805 | 3 |
| volume > 0, duration = 0 | 0 | 0 |

The 39,805 samples touch **3,643 hours retained by Rule B**. Hence the companion condition is only a missingness/numeric-validity condition: **it is not an energy-duration consistency test**. This answers the review concern about asymmetric treatment. The original rule did not test proportionality or scientific plausibility; this distinction must not be presented as assurance that duration makes energy trustworthy.

### Station-level characteristics

| Station | Zero-volume / positive-duration samples | First occurrence | Last occurrence | Positive duration range (h) | Metadata observations |
|---|---:|---|---|---|---|
| 1135 | 5,762 | 2022-10-21 01:05 | 2023-02-21 07:20 | 0.08333–0.41667 | Station table: 11 chargers; power table: 22 assigned entries, all power 0 |
| 2172 | 7,423 | 2022-10-21 01:05 | 2023-02-21 08:25 | 0.08333–0.33333 | Station table: 16 chargers; power table: 27 assigned entries, 22 power 0 and five power 7 kW |
| 2300 | 26,620 | 2022-09-01 00:05 | 2023-02-21 08:25 | 0.08333–0.25 | Station table: six chargers; power table: 12 assigned entries, all power 0 |

These are published metadata entries, not verified physical charger inventories. Stations 1135 and 2300 have no positive-volume samples anywhere in their valid numeric source records; station 2172 has 9,340 positive-volume samples elsewhere. Monthly distributions are recorded in the JSON evidence. The patterns span extended periods rather than one isolated blank interval.

Actual source examples:

| station_id | time | volume (kWh) | duration (h) |
|---|---|---|---|
| 1135 | 2022-10-21 01:05:00 | 0.0 | 0.0833333333333333 |
| 2172 | 2022-10-21 01:05:00 | 0.0 | 0.1666666666666666 |
| 2300 | 2022-09-01 00:05:00 | 0.0 | 0.25 |

Zero rated-power entries co-occur with these patterns. Because the publisher derives energy using rated power, this provides a plausible upstream-data explanation worth investigating; **it does not identify which original pile states or power entries generated each value**. The inconsistent memberships and unavailable original generator prevent causal attribution. No energy is repaired or station excluded here. Numerically retained zero energy is not established physical inactivity.

## Scientific basis and limits

The [UrbanEV paper, EV charging data](https://www.nature.com/articles/s41597-025-04874-4?error=cookies_not_supported#Sec4) describes duration from consecutive busy states and energy estimated from duration and rated power. This supports interpreting `volume` as derived energy and summing interval energy rather than averaging it or multiplying by power again. It does **not** establish that every missing duration mandates rejection of a separately present volume. The hypothetical valid-volume/missing-duration case in the review is handled differently by A and B (covered by a regression fixture), but it does not occur in this release.

**Conclusion on duration:** the extra condition is empirically redundant on this release. There is no measured additional data loss, but also no evidence here that it improves physical correctness. Keep Rule B labeled provisional pending team review. Rule A is a simpler energy-target validity predicate to consider; any adopted change must be recorded explicitly. Neither rule detects the positive-duration/zero-volume pattern as invalid.

**Conclusion on timestamp/timezone:** still unresolved. The paper states observations are five minutes apart and activity uses two consecutive timestamps; neither that description nor the [inspected pinned README](https://github.com/IntelligentSystemsLab/UrbanEV/blob/44f2aa0c8d89f192bce00bafb0def74a21b39c68/readme.md) identifies which endpoint labels the distributed station interval or proves the source clock/timezone conversion. This audit reuses the explicit **start-label, Asia/Shanghai assumption** to isolate QC-rule impact. A=B is not evidence that the hour assignment is correct. Shenzhen's geographic timezone is not a collection/conversion log. Peer approval of an explicit benchmark assumption or upstream generator evidence is still needed before research acceptance; actual label arrival remains unknown.

The diagnostic scan uses the entire release to describe data quality, not final-target forecasting outcomes. Do not tune exclusions or select favorable final targets from these patterns. Any research use/exclusion rule must be set through the agreed source/development protocol before final evaluation. No novelty, effectiveness, imputation-causality or meter-accuracy claim follows.

## Reproduction and checks

Executed analysis commit: `e830db6a9c8426cc3291f0952969b7f380f38aef`; Python 3.12.14; runtime approximately 105.07 seconds. The analysis script hash, reference manifest/archive identities, and local station-comparison hash are recorded in JSON.

```sh
python -m tools.audit_urbanev_rules \
  --reference-run data/processed/urbanev/issue16-start-v1-20261017 \
  --output-root runs/urbanev-rule-audit \
  --run-id YOUR_NEW_ANALYSIS_RUN_ID
```

The reference run must be complete and its raw extraction available. The script verifies every input hash, evaluates both rules together and checks each station's Rule B count against the reference. It writes new analysis files only, refuses existing run IDs and does not modify the original hourly run, archive or raw CSVs. Six new independent tests cover duration-only loss, joint missingness, zero disagreement retained by both, invalid volume, duplicate clocks and token categories; 34 total offline tests pass. CI still uses no real datasets.

Research approval remains pending. This report answers rule-impact questions; it does not close #16 or resolve the interval convention.
