# Data acquisition and verification — 2026-10-15

## Scope and evidence

Issue #8. Download the two required archives, verify their identity, inspect ZIP structure, and arrange usable provider files locally. Evidence: [acquisition manifest](acquisition_20261015_1633.json).

| Archive | Bytes | SHA-256 | Publisher checksum | ZIP integrity |
|---|---:|---|---|---|
| UrbanEVDataset.zip | 647,305,188 | Matches catalog | Not provided | All members passed CRC |
| Hourly.zip | 268,720,500 | Matches catalog | MD5 matches catalog | All members read with CRC validation |

`python -B -m tools.sources verify` returned exit 0 with both required sources PASS. The catalog and original Report 1 are unchanged. Download intermediates were removed only after complete archive verification.

## Local arrangement

```text
data/raw/
  urbanev/official_2026_05_11/
    UrbanEVDataset.zip
    extracted/UrbanEVDataset/20220901-20230228_station-raw/
      charge_5min/              1,682 CSV files
      pile_rated_power.csv
      station_distance.csv
      station_information.csv
  charged/zenodo_15814263/
    Hourly.zip
    extracted/
      AMS/ JHB/ LOA/ MEL/ SPO/ SZH/   60 files in total
```

UrbanEV contains 3,130 files and 15,571,958,407 uncompressed bytes across station-raw, station-processed, and zone variants. Only station-raw was extracted: 1,685 files, 5,383,456,417 bytes. Remaining variants are preserved inside the original ZIP.

CHARGED contains standard and `remove_zero` directories in the same Hourly archive. All members were read successfully. Only standard city directories are retained as extracted copies: 60 files, 814,006,070 bytes. Redundant extracted `remove_zero` copies were removed; their original archive members remain intact. No city has been accepted into an experimental cohort by this acquisition step.

The sampled UrbanEV charging header is `time, busy, idle, s_price, e_price, fast_busy, fast_idle, slow_busy, slow_idle, duration, volume`. CHARGED city directories include `chargers`, `distance`, `duration`, `e_price`, `info`, `poi`, `sites`, `s_price`, `volume`, and `weather` CSVs. These are structural observations, not decisions to use every field as a model feature.

## Download and cleanup notes

UrbanEV used the catalog Drive endpoint. The initial CHARGED urllib request returned HTTP 403. curl could access the catalog endpoint; the slow transfer was resumed through validated byte ranges on the same Zenodo record/file web endpoint. The assembled archive matched both SHA-256 and publisher MD5. The manifest records the actual URL and transfer details.

Python/Ruff caches and this run's temporary download parts were removed. No existing raw archive or user file was overwritten/deleted. Both ZIPs and extracted directories are Git-ignored; only documentation and the small manifest are committed. Other machines still need to download/copy and verify their own local data.

## Reproduction and limits

Follow [data/README](../../data/README.md) to obtain exact archives and run the verifier. Extract UrbanEV's station-raw subtree and CHARGED standard city directories without changing archive bytes. Validate member paths and CRC on extraction; preserve provider names and headers.

This run does not implement data cleaning, hourly aggregation, missing/zero handling, accepted cohorts/splits, scaling, model inputs, training, or experiments. Headers were sampled, not fully audited. Time/bin/unit semantics, label availability, upstream processing, and dataset independence still need investigation. Supplemental was not downloaded.
