# CHARGED — six-city inventory (Issue #17, Step 1)

## Scope and decision status

This handoff inventories the **standard** AMS, JHB, LOA, MEL, SPO and SZH directories from the acquired `Hourly.zip`. It records actual file shapes, identifiers, clocks, blank cells, zeros and other numeric diagnostics. It does not repair, impute, resample, filter sites, select `remove_zero`, create a shared hourly adapter, or create model windows/cohorts. No research method or experimental protocol is changed.

Issue #17 remains open: publisher preprocessing/availability, forecasting suitability, Shenzhen/UrbanEV overlap and final QC decisions are later work. PR #25 remains separate and unmerged; this implementation branches from `dev` and imports no code or contract from that PR.

| State | Meaning | Result of this step |
| --- | --- | --- |
| File-valid | A value exists and meets explicitly agreed checks on the released file | Diagnostics recorded; no city-level acceptance decision or validity mask yet |
| Forecasting-eligible | Data meets protocol requirements for constructing forecasting samples | Not assessed here; official windows/cohorts belong to #18 |
| Strict-online-ready | Evidence establishes information availability and absence of upstream future leakage | Not established; file completeness cannot establish this |

Zero, blank and invalid numeric tokens are counted separately. A zero is not converted to missing, and a blank is not converted to zero. An all-zero site is only a descriptive count: every released hourly value in that file is numerically zero. It is not an exclusion decision or proof of inactivity.

## Reproduce

Use Python 3.12 from the repository root after obtaining the archive and extracting the six standard city directories unchanged:

```sh
python -B -m tools.charged_inventory \
  --source-root data/raw/charged/zenodo_15814263/extracted \
  --output-root runs/charged-inventory \
  --run-id issue17-inventory-v2-20261017
```

Choose a fresh run ID when rerunning; an existing output directory is refused. The tool verifies the original archive against the catalog (size, SHA-256 and publisher MD5), then checks each extracted file's size/CRC against its verified ZIP member and records its SHA-256. It only reads inputs and creates a new `inventory.json` outside raw storage. A read/archive failure returns nonzero and records failure evidence. Reported data anomalies remain diagnostics, not an automatic QC verdict.

The manifest records config/scope, source identity, script hash, Git commit, Python/platform, UTC start, elapsed runtime, per-file headers/hashes/counts and per-site numeric counts. Full output stays in ignored `runs/`; the compact tables below are the reviewable handoff. Tests use independent temporary CSV/ZIP fixtures and require no downloads.

## Verified run identity

- Run: `issue17-inventory-v2-20261017`; UTC start `2026-10-17T16:02:21.596256+00:00`; runtime **52.19 s**, Python 3.12.14.
- Executed code: `cce2556e5f9e1699567aab04e7c00517d7996163`; script SHA-256 `a9b828f6c8ba75ed21ed5582f7b931a56206f5c6160dfb228528f1938baa481f`.
- Archive: **268,720,500 bytes**; freshly verified SHA-256 `1ec9c9513b64f3f492fe73261bf08a5955c268dfb876ef0fe283d05cc5a02fab` and publisher MD5 `099a592653ca74fa1f1051e9c23d6456`.
- Full local manifest SHA-256: `bb270e18cfebc892f232e7d7510c3e7cb7c6ce760950e5fdae2a0a204ab1008a`. A [compact evidence snapshot](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/charged-inventory-evidence.json) preserves run metadata, file fingerprints, shapes and counts; long site-ID lists and per-site counts remain in the full local manifest.

## City overview

Counts below come from actual `sites.csv` and `chargers.csv` rows, not positional interpretation of malformed `info.csv`. All site IDs are unique and nonblank.

| City | Sites | Charger rows | Literal hourly range | Blank / nonfinite volume cells | Zero volume cells | All-zero volume sites | QC |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| AMS | 2,449 | 3,526 | Apr 1–Sep 30, 2023; 4,392 hours | 0 / 0 | 6,060,614 / 10,756,008 (56.35%) | 1,061 | Not decided |
| JHB | 47 | 61 | Apr 1–Sep 30, 2023; 4,392 hours | 0 / 0 | 74,417 / 206,424 (36.05%) | 12 | Not decided |
| LOA | 229 | 506 | Apr 1–Sep 30, 2023; 4,392 hours | 0 / 0 | 219,676 / 1,005,768 (21.84%) | 5 | Not decided |
| MEL | 63 | 64 | Apr 1–Sep 30, 2023; 4,392 hours | 0 / 0 | 82,397 / 276,696 (29.78%) | 1 | Not decided |
| SPO | 47 | 50 | Apr 1–Sep 30, 2023; 4,392 hours | 0 / 0 | 58,384 / 206,424 (28.28%) | 6 | Not decided |
| SZH | 1,445 | 2,195 | Apr 1–Sep 30, 2023; 4,392 hours | 0 / 0 | 440,585 / 6,346,440 (6.94%) | 68 | Not decided |

Total: **4,280 sites**, **6,402 charger rows** and **18,797,760 hourly site-volume cells**. The released charger-row population must not be substituted for the paper's 11,953-charger claim without a later population/provenance explanation. No sites have been removed by this audit.

## Files, schemas and identifiers

All six directories contain exactly these ten expected CSVs; there are no missing or unexpected files. Shapes exclude the header row. `N` denotes that city's site count.

| File | Actual shape / role | Inventory result |
| --- | --- | --- |
| `info.csv` | 1 data row; 9 values | AMS/JHB have 9 header fields; LOA/MEL/SPO/SZH have only 8 (see below) |
| `sites.csv` | N × 9 | Site IDs match the columns of all four hourly matrices |
| `chargers.csv` | Charger rows × 7 | All member site IDs resolve in the same city; charger IDs are unique/nonblank |
| `distance.csv` | N × (N+1), including row-ID field | Row/column ID sets match sites; finite, nonnegative values; no blank cells |
| `volume.csv` | 4,392 × (N+1) | Time field plus hourly site-energy columns; numeric diagnostics below |
| `duration.csv` | 4,392 × (N+1) | Time field plus hourly duration columns |
| `e_price.csv` | 4,392 × (N+1) | Time field plus electricity-price columns |
| `s_price.csv` | 4,392 × (N+1) | Time field plus service-price columns |
| `weather.csv` | 4,392 × 19 | Parsed clock matches hourly matrices; preciptype blanks recorded separately |
| `poi.csv` | POI rows × 4 | No blank data cells or ragged rows; counts below |

### Actual headers

The detailed meaning/units and AMS examples remain in [CHARGED.md](../data/CHARGED.md). This inventory records schema differences rather than changing them.

- `sites.csv`: `site_id,longitude,latitude,charger_num,total_duration,total_volume,avg_power,perimeter,area`; MEL/SPO use `site` instead of `site_id`.
- `chargers.csv`: `charger_id,longitude,latitude,site_id,total_duration,total_volume,avg_power`; LOA/SPO/SZH use `site` instead of `site_id`.
- `info.csv` in AMS/JHB: `city,country,abbreviation,total_chargers,total_sites,DBSCAN_eps,total_duration,total_volume,avg_power`.
- **Malformed `info.csv` in LOA/MEL/SPO/SZH:** `city,country,abbreviation,total_chargers,total_siteBSCAN_eps,total_duration,total_volume,avg_power`. Each has 8 header fields and 9 row values. No automatic split of `total_siteBSCAN_eps`, column shift, or repair has been applied. A positional dictionary/reader could silently mislabel the row. Site/charger counts above come from their own tables.
- `volume.csv` / `duration.csv`: first header is blank; remaining headers are literal site IDs. Price matrices use `time` for the first field. Column order can be lexical (`0,1,10,...`); join by IDs, not column position.
- `distance.csv`: blank first header plus site IDs. The first data field is the row site ID.
- `poi.csv`: blank first header, `type,longitude,latitude`.
- `weather.csv`: `time,temp,feelslike,humidity,dew,precip,snow,snowdepth,preciptype,windgust,windspeed,winddir,pressure,visibility,cloudcover,solarradiation,solarenergy,uvindex,conditions`.

Except for the four `info.csv` rows above, all 60 files have data-row widths matching their headers. No duplicate site/charger/distance-row IDs or hourly/distance site-column IDs were found. Identifier consistency does not validate physical clustering or geographic accuracy.

## Clock and missing-value inventory

For every city, all four hourly matrices have **4,392 rows** from literal `2023-04-01 00:00:00` through `2023-09-30 23:00:00`, in 3,600-second steps, with no parse failures, duplicates or missing clock hours within that literal span. Their timestamp sequences match exactly.

Weather uses a different text format (`2023/4/1 0:00` through `2023/9/30 23:00`), but parsing produces the same ordered clock values, with no missing/duplicate hours. This is a comparison only; no source timestamps were rewritten.

**All timestamps lack an explicit UTC offset.** Equal literal clock ranges across cities do not establish equal UTC instants. Timezone, daylight-saving conventions, bin endpoints and information availability remain unverified in this step. No timezone was assigned.

Across all four hourly matrices in all cities, physically present data cells contain **zero blanks, zero nonnumeric tokens, zero NaN/infinity and zero negative numbers**; no absent fields or ragged rows were found there. This establishes released-file completeness for these checks only; it does not show that values were observed rather than interpolated upstream.

| City | Duration zero cells | e_price zero cells | s_price zero cells | Weather preciptype blanks / 4,392 | POI rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| AMS | 6,060,792 | 3,579,480 | 10,738,440 | 3,968 | 51,340 |
| JHB | 72,984 | 80,830 | 206,424 | 4,354 | 47,488 |
| LOA | 219,670 | 988,200 | 1,005,768 | 4,321 | 42,782 |
| MEL | 82,397 | 207,434 | 276,696 | 4,147 | 617,806 |
| SPO | 58,384 | 43,988 | 206,424 | 4,341 | 49,719 |
| SZH | 431,810 | 4,505,643 | 5,318,712 | 3,977 | 47,181 |

All other weather fields have no blank cells. No blank data cells were found in `sites`, `chargers`, `info`, `distance` or `poi`; this is a blank-cell check, not full semantic validation of their numeric attributes. A blank `preciptype` may encode no precipitation or another provider convention; this step leaves that meaning unresolved and does not fill it.

`s_price` is entirely zero in JHB, LOA, MEL and SPO. This does not establish that service was free. Zero duration and zero volume counts differ in some cities; aggregate counts alone do not locate or explain paired mismatches. Pairwise consistency, static/hourly reconciliation, units and publisher preprocessing remain later audit work.

## Checks and handoff

- Local checks: **15 offline unit tests passed**, Ruff lint passed, Ruff format passed, `tools.sources list` passed, `pip check` passed, and `git diff --check` passed.
- Real-data run: all 60 extracted files matched size/CRC of members in the freshly verified archive; inventory completed in the run above. Archive verification PASS is an identity check, not a data-quality or research-acceptance verdict.
- Fixtures cover zero versus missing/nonfinite/nonnumeric values, short rows, malformed metadata without repair, clock gaps/duplicates/formats, observed ID aliases, and extracted-file corruption detection. They do not demonstrate model effectiveness.
- Still pending: city-level QC acceptance, upstream interpolation/outlier/zero handling, time/availability evidence, paired duration/volume diagnostics, static/hourly population discrepancies, and SZH/UrbanEV overlap. No strict-online, external-independence or forecasting-eligibility claim is made.
- **Stop here for review.** The next decision is which findings require QC rules and further evidence. This report does not authorize site exclusion, data alteration, an adapter, or #18 windows/cohorts. Issue #17 is not complete.
