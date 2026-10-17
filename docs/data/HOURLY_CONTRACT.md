# Hourly energy contract — version 1 (review proposal)

Issue [#16](https://github.com/HungLD9505/adaptive-retention-ev/issues/16). This minimal interface is proposed for UrbanEV processing, CHARGED adapters (#17), and model-input consumers (#18). It does not make station/site definitions or upstream observation histories equivalent. Consumer/peer review is required before research acceptance; this implementation supplies UrbanEV only.

## Rows and fields

`hourly.csv` is a long table, one row per entity per requested hourly bin. Identity is `(dataset_id, city_id, entity_id, timestamp)`. IDs are strings; the city component prevents collisions between CHARGED city-local site IDs. Preserve leading zeros if provided by a source.

| Field | Type / unit | Meaning |
|---|---|---|
| dataset_id | string | Dataset identity; currently `urbanev`. |
| city_id | string | City identity; currently `SZH`. |
| entity_id | string | Source station/site identifier; the dataset determines its meaning. |
| timestamp | ISO 8601 with offset | Inclusive hourly bin start, under the run's explicit clock assumption. |
| energy_kwh | finite nonnegative number or empty | Sum of interval energy for a file-valid hour; empty when invalid. Never fill labels. |
| file_valid_mask | integer 0/1 | Whether the energy bin meets the run's file/completeness rules. Not an original-observation, meter-accuracy, or no-leakage certificate. |
| valid_sample_count | integer | Unique valid on-grid constituent energy/duration samples. A duplicate can still invalidate a bin with count 12. |
| expected_sample_count | integer | 12 for UrbanEV five-minute input. CHARGED adapter semantics must be reviewed separately; do not invent twelve original observations from one published hourly value. |
| qc_flags | semicolon-separated string | Deterministically ordered reasons for invalid energy; empty for file-valid bins. |

For a CHARGED adapter the constituent count can only describe entries in its released file. No original-observation mask may be invented. Metadata must retain entity kind, upstream processing/imputation limitations, energy provenance, timestamp assumptions, QC rules and original-observation status (`unknown` where not provided). A common interface does not authorize pooling datasets, choosing features or asserting external independence.

## UrbanEV aggregation policy

- Read the provider's station-raw `volume` (kWh) as interval energy; sum, without multiplying again by power or duration. Do not reconstruct it from busy counts. This remains a publisher-derived target.
- A valid hour needs **12 unique expected five-minute timestamps** and finite nonnegative volume **and duration** at every timestamp. Using duration as a companion integrity condition is conservative and explicit; it is not imputation or a claim of physical truth.
- Retain source zeros, including busy>0 with zero estimated activity. Blank/malformed/nonfinite/negative target values are invalid; never replace them with zero, forward/backward filling or prorated totals.
- Duplicate timestamps invalidate their hourly bin; do not sum/select/average duplicate labels. Off-grid timestamps invalidate the affected bin and are not rounded. Malformed timestamps/schema/rows stop the run. Out-of-order rows are counted and cause run-level structural failure even if label-keyed sums can be computed.
- Missing requested hours still get an output row: empty energy, mask 0. `incomplete_hour` records fewer than twelve valid samples. `invalid_target_sample`, `duplicate_timestamp`, `off_grid_timestamp` and `nonfinite_sum` identify additional reasons. Rows outside the requested effective window are counted and excluded deliberately.
- Pricing/occupancy inconsistencies, zero or missing rated-power coverage and values above static capacity are **audit diagnostics**, not fitted thresholds or silent target filters. Infrastructure metadata may be incomplete or inconsistent. Capacity is not inferred where member counts/powers are unreliable. No station is selected for research by full-period statistics.

The target-valid mask is distinct from historical-X masking in #18. #18 must derive its inputs without using unavailable target labels or selecting forecast dates based on future completeness. No cohort/split, scaler, feature engineering, tensor windows or model loader is implemented here.

## Clock assumptions and availability

Both `--timezone` and `--interval-label` are required. There is no implicit UTC, timezone conversion from an established source clock, or hidden choice between start/end labeling.

- `start`: a source timestamp t contributes energy for `[t, t+5min)`.
- `end`: a source timestamp t contributes energy for `[t-5min, t)`.
- Output timestamp always labels `[hour_start, hour_start+1h)`.
- `--start` and `--end` are naive local inclusive/exclusive whole-hour boundaries. The timezone is explicitly attached under the chosen assumption. Offset transitions inside the window are rejected; this UrbanEV implementation is not a generic DST adapter for CHARGED.

The UrbanEV paper describes consecutive busy-state observations and derived energy but the exact timestamp-to-interval generator is unavailable. Therefore both conventions are supported for review, not declared physically verified. The real-data run uses **Asia/Shanghai and start labeling as explicit provisional assumptions**. Its output cannot be accepted as a verified causal benchmark until time semantics are reviewed. Labels at exclusive horizon end in future replay would be a separate availability assumption, not a fact established by this pipeline.

## Execution and evidence

Run from the repository root with Python 3.12:

```sh
python -m tools.urbanev \
  --source-root data/raw/urbanev/official_2026_05_11/extracted/UrbanEVDataset/20220901-20230228_station-raw \
  --output-root data/processed/urbanev \
  --run-id YOUR_NEW_RUN_ID \
  --start 2022-09-01T00:00:00 \
  --end 2023-03-01T00:00:00 \
  --timezone Asia/Shanghai \
  --interval-label start
```

`--storage-root` can point at another root containing the catalog's `data/raw/...` archive. `--source-root` selects its extracted station-raw directory. A missing IANA timezone database (possible on Windows) fails clearly; supply system IANA data or install the standard `tzdata` fallback in the execution environment. Offline fixtures use UTC and do not need that package or real data. No new project dependency is required by the pipeline.

A run creates an exclusive new directory with `hourly.csv`, `station_qc.json` and `manifest.json`; failed runs retain a failed manifest and any incomplete output, plus completed-station evidence. Never reuse a run ID or read partial output as an accepted run. Routine CI uses tiny independent fixtures, not the real archives.

The required archive is reverified against the catalog. Each extracted metadata/time-series file is checked for ZIP member size/CRC, then SHA-256 recorded. The complete station inventory must match metadata and ZIP. Input bytes are never changed. SHA-256 recorded per file provides exact handoff identity; output fingerprints, source code hashes/commit/worktree state, config, environment, timestamps and elapsed runtime are recorded. Logs identify progress.

Exit 0 means technical structural checks passed for the processed scope, with per-hour invalidity and diagnostic warnings still possible. Exit 1 means structural/QC/validation/read failure; the manifest explains failures once a run directory exists. Invalid CLI syntax returns argparse's exit 2. Invalid run IDs/unsafe paths/existing runs can fail before creating a directory. **Technical success is not research acceptance**: `research_acceptance` remains `pending_peer_review` and no strict-online, all-clean or effectiveness claim follows.
