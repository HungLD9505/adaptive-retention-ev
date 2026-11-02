# UrbanEV dataset reference

This document explains the UrbanEV source data used by the project, from the archive layout to individual CSV fields. Station `1001` is the running example. The scope is data interpretation, not a completed quality audit or processing pipeline.

Decimal values use a period, matching the CSV files. Tables preserve source column names, order, and sample values; illustrative calculations are labeled separately.

## 1. Dataset and source

UrbanEV describes public electric-vehicle charging activity in Shenzhen, China. The project uses the station-level source data in `UrbanEVDataset.zip`, obtained from the Google Drive folder linked by the authors under [Data Access][access].

| Property | Scope |
|---|---|
| Location | Shenzhen, China |
| Stations in station-raw metadata | 1682 |
| Observation dates | 2022-09-01 through 2023-02-28 |
| Published station-series resolution | 5 minutes |
| Source catalog | [data/sources.json](../../data/sources.json) |
| Download and checksum instructions | [data/README.md](../../data/README.md) |

The archive's identity was checked against the catalog during local acquisition. The dataset is not stored in Git. Acquisition evidence is reviewed separately in [PR #9][acquisition-pr].

Three objects must be distinguished:

- **Station:** a charging location containing one or more charging piles.
- **Pile:** an individual charging unit belonging to a station, called a charger in this document where appropriate.
- **Traffic Analysis Zone (TAZ):** a geographic analysis area that may contain several stations.

## 2. Archive layout

The archive contains three principal groups. Actual folder names include the date prefix `20220901-20230228_`.

| Group | Contents |
|---|---|
| `station-raw` | Station-level source records before the provider's described correction/preprocessing stage. |
| `station-processed` | Station-level records processed by the provider. |
| `zone-cleaned-aggregated` | Cleaned records aggregated to geographic zones. |

The project uses **station-raw as the source for its processing pipeline**. Its energy fields are already derived by the provider from activity and rated power; the folder name does not establish that every field is an unmodified meter observation.

```text
UrbanEVDataset/
├── 20220901-20230228_station-raw/
│   ├── station_information.csv
│   ├── pile_rated_power.csv
│   ├── station_distance.csv
│   └── charge_5min/
│       ├── 1001.csv
│       ├── 1002.csv
│       ├── ...
│       └── 2682.csv
├── 20220901-20230228_station-processed/
└── 20220901-20230228_zone-cleaned-aggregated/
```

| Station-raw component | Purpose |
|---|---|
| `station_information.csv` | Static station attributes. |
| `pile_rated_power.csv` | Charger attributes and station membership. |
| `station_distance.csv` | Pairwise distances between stations. |
| `charge_5min/` | One activity time series per station. |

## 3. station_information.csv

### Purpose and sample

Each row describes one station. The file has 1682 rows with distinct station IDs from `1001` to `2682`.

| station_id | longitude | latitude | slow_count | fast_count | charge_count | TAZID |
|---:|---:|---:|---:|---:|---:|---:|
| 1001 | 113.784724 | 22.714121 | 20 | 0 | 20 | 559 |
| 1002 | 113.785002 | 22.7259 | 22 | 0 | 22 | 558 |
| 1003 | 113.787971 | 22.735538 | 6 | 0 | 6 | 558 |

### Fields

| Field | Meaning |
|---|---|
| `station_id` | Station identifier assigned by the provider. |
| `longitude` | Published station longitude. |
| `latitude` | Published station latitude. |
| `slow_count` | Number of slow chargers. |
| `fast_count` | Number of fast chargers. |
| `charge_count` | Total number of chargers. |
| `TAZID` | Identifier of the traffic analysis zone associated with the station. |

Station `1001` has longitude `113.784724`, latitude `22.714121`, 20 slow chargers, no fast chargers, and 20 chargers in total. Its assigned TAZID is `559`.

The ID does not establish construction order or commissioning date. No source explaining why station numbering starts at `1001` has been identified.

### TAZID

UrbanEV adopts traffic zones from the sixth Residential Travel Survey of Shenzhen, as described in the [dataset paper][paper]. TAZID links a station to its zone; several stations can share one value. For example, stations `1002` and `1003` both reference zone `558`.

Inspection found:

- 331 distinct TAZIDs in station metadata, with no missing TAZID values.
- 491 distinct zone records in the supplemental GIS archive.
- IDs ranging from `102` to `1173` in both inspected sets, without a continuous sequence.
- A GIS record and geometry for TAZID `559`, with published centroid attributes `X = 113.7744037`, `Y = 22.7104822`, and `AREA = 5.73`.

The GIS contains separate `OBJECTID`, `TAZID`, and `ZONE` fields. They are not interchangeable. No numbering dictionary explaining TAZID digits, prefixes, or ranges was found in the inspected source descriptions, GIS attributes, or QGIS project.

**Use the published TAZID as a categorical join key.** Do not infer district, land-use category, traffic intensity, energy demand, or numeric ordering from its magnitude. A numbering convention may exist, but it has not been established from the available sources.

### Coordinate-reference limitation

The official [GitHub README][access] says station coordinates use **GCJ-02**; the [Dryad description][dryad] labels them **WGS-84**. Preserve this source discrepancy when mapping or performing spatial analysis. Do not silently convert the coordinate values or claim that the discrepancy has been resolved.

## 4. pile_rated_power.csv

### Purpose and sample

Each row describes one charger and identifies its parent station.

| pile_id | power | pileType | station_id |
|---|---:|---|---|
| 10010001.0 | 7.0 | AC | 1001.0 |
| 10010002.0 | 7.0 | AC | 1001.0 |
| 10010003.0 | 7.0 | AC | 1001.0 |

### Fields

| Field | Meaning | Unit |
|---|---|---|
| `pile_id` | Charger identifier assigned by the provider. | Identifier |
| `power` | Rated charging power. | kW |
| `pileType` | Alternating current (`AC`) or direct current (`DC`). | Category |
| `station_id` | Parent station identifier. | Identifier |

IDs appear with a `.0` suffix in this CSV. Normalize identifier representation consistently when joining `1001.0` to station `1001`; these must not become two different stations. Use `station_id` for membership rather than inventing a rule from the digits of `pile_id`.

### Rated power and energy

Rated power is the published equipment capability, not a record of actual delivered power or energy. Actual charging power may be lower because of vehicle limits, battery state, or operating conditions.

- **kW:** power, the rate of energy transfer.
- **kWh:** accumulated energy.

For constant actual power:

```text
Energy (kWh) = Power (kW) × Time (hours)
```

Illustration: maintaining 7 kW for 30 minutes corresponds to 3.5 kWh of transferred energy before considering losses. This is a unit calculation, not an observed charging session in the dataset.

AC charging supplies alternating current to the vehicle, whose onboard charger converts it to DC. DC charging performs the conversion outside the vehicle. AC/DC describes the current type; the `power` column supplies the power rating. See the [government charging-equipment explanation][charging-equipment].

### Station 1001 cross-check

The file records 20 chargers belonging to station `1001`, all `AC` with rated power `7.0` kW. This agrees with the 20 slow chargers in station metadata.

Their summed rated power is 140 kW. This does not establish constant station consumption, the site's electrical connection limit, or energy delivered over any particular interval.

## 5. station_distance.csv

### Purpose and sample

This is a 1682-by-1682 matrix of distances **between stations**, in meters. It does not describe distances between chargers inside one station.

| ID | 1001 | 1002 | 1003 |
|---:|---:|---:|---:|
| 1001 | 0 | 1304.72042675002 | 2395.06383965684 |
| 1002 | 1304.72042675002 | 0 | 1110.03575575026 |
| 1003 | 2395.06383965684 | 1110.03575575026 | 0 |

The first column and header contain station IDs. The cell at row `1001`, column `1002` is approximately `1304.72 m`, or `1.30472 km`.

### Numerical verification

All 2829124 matrix cells were recomputed from the published station coordinates using inverse geodesic distances on the WGS84 ellipsoid, without coordinate conversion. Every cell matches within `1e-6 m`; the maximum absolute difference is about `3.24e-9 m`.

The matrix therefore matches a **direct geodesic coordinate-distance calculation**, not a routed driving distance. This reconstructs a matching formula; it does not identify the provider's exact software or resolve the coordinate-reference discrepancy above. The small residual is numerical agreement, not physical positioning accuracy.

The matrix is symmetric and its diagonal is zero. All 316 off-diagonal zero cells correspond to identical published coordinate pairs. Do not merge station IDs solely because their coordinates or distances match.

Details and input hashes are recorded in the [verification evidence](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/urbanev-verification.json).

## 6. charge_5min/<station_id>.csv

### Purpose and coverage

The directory contains 1682 CSV files, one per station: `1001.csv` belongs to station `1001`, and so on through `2682.csv`. Each row summarizes the **whole station** at a 5-minute timestamp; it does not expose individual charger histories.

The following coverage was checked specifically for `1001.csv`; it must not be assumed for every station without audit.

| Property | Verified value |
|---|---|
| First timestamp | 2022-09-01 00:00:00 |
| Last timestamp | 2023-02-28 23:55:00 |
| Timestamp spacing | 5 minutes |
| Days | 181 |
| Rows / unique timestamps | 52128 / 52128 |

The timestamp grid is complete for this station, but some rows contain blank fields. A complete grid does not establish complete observations.

### Sample

| time | busy | idle | s_price | e_price | fast_busy | fast_idle | slow_busy | slow_idle | duration | volume |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-09-01 00:15:00 | 8 | 12 | 0.47 | 1.2 | 0 | 0 | 8 | 12 | 0.0833333333333333 | 0.5833333333333333 |
| 2022-09-01 00:20:00 | 6 | 14 | 0.47 | 1.2 | 0 | 0 | 6 | 14 | 0.0833333333333333 | 0.5833333333333333 |

### Fields

| Field | Meaning | Unit |
|---|---|---|
| `time` | Observation timestamp. | Date/time |
| `busy` | Total reported busy/unavailable chargers, interpreted under the provider's availability note. | Chargers |
| `idle` | Total reported idle/available chargers. | Chargers |
| `s_price` | Charging-service unit price. | CNY/kWh |
| `e_price` | Electricity unit price. | CNY/kWh |
| `fast_busy` | Reported busy fast chargers. | Chargers |
| `fast_idle` | Reported idle fast chargers. | Chargers |
| `slow_busy` | Reported busy slow chargers. | Chargers |
| `slow_idle` | Reported idle slow chargers. | Chargers |
| `duration` | Total charging duration calculated by the provider across chargers. | Hours |
| `volume` | Total charging energy estimated by the provider. | kWh |

### Availability and utilization

At `00:15`, the source reports 8 busy and 12 idle chargers, all slow chargers, totaling 20.

The authors explicitly distinguish **availability**, covering unavailable or busy chargers, from **utilization**, covering chargers actively supplying electricity. A busy count is not a power measurement or guaranteed active-charging count. See the [official README note][availability-note].

Consequently, positive busy counts with zero duration/volume are not by themselves proof of an error. The station CSV does not reveal why an individual charger was unavailable; do not invent physical explanations for particular rows.

### Electricity and service prices

`e_price` and `s_price` are unit prices, not amounts actually paid. In the sample:

```text
Electricity price:  1.2 CNY/kWh
Service price:      0.47 CNY/kWh
Combined rate:      1.67 CNY/kWh
```

Illustration: applying both unchanged rates to 10 kWh gives 16.7 CNY before discounts or other charges. The file does not contain individual-session invoices. The paper describes station prices as averages of the underlying charger prices.

### Charging duration

`duration` is summed charger-time, not elapsed time since the beginning of the dataset or necessarily the length of a complete charging session.

Illustration: three chargers each charging for 5 minutes contribute 15 charger-minutes, or 0.25 hours, even though only 5 minutes of clock time pass. Station-level duration can therefore exceed the length of one observation interval.

### Estimated energy

The provider describes energy as duration multiplied by each charger's rated power, summed across the station:

```text
Station energy = sum(charger duration × charger rated power)
```

For station `1001`, every charger has a 7 kW rating. All inspected rows with busy/duration/volume present satisfy `volume ≈ duration × 7` within `1e-8`. This confirms arithmetic consistency, not true measured energy.

For stations with mixed charger ratings, do not multiply total duration by an arbitrary single rating. Energy estimates are not direct meter readings.

### Reconstruction limits

The paper describes using consecutive observations of the same charger in the activity calculation. The distributed station CSV lacks those individual histories. Two equal station-level busy totals do not establish that the same chargers were busy.

No original pile-state-to-station duration/volume generator was found in the 21 Python files inspected at the pinned upstream commit. Therefore:

- Do not recompute duration as the current busy count multiplied by 5 minutes.
- Do not infer individual charger behavior from aggregate counts.
- Do not equate source energy estimates with independently measured consumption.
- Do not automatically recode zeros as missing values or fill blank target labels. Processing decisions require a separate reviewed rule and evidence.
- Exact interval alignment and first-timestamp treatment still require upstream implementation details.

## 7. Relationships between files

```text
station_information.csv
  station_id ──> pile_rated_power.csv: charger membership and rated power
             ├─> station_distance.csv: distance to other stations
             └─> charge_5min/<station_id>.csv: station activity over time
  TAZID ──────> zone attributes and GIS geometry
```

Together, these files describe where station `1001` is, its 20 AC chargers rated at 7 kW, distances to other stations, time-varying availability/prices/estimated activity, and its zone assignment `559`.

Source columns are not automatically model features. Input/label selection, hourly aggregation, missing/zero treatment, valid cohorts, scaling, and leakage checks belong to the Data Processing & QC and Model Input phases under Report 1.

## 8. Supplemental archive

`UrbanEVSupplemental.zip` contains airport/central weather CSVs, a Shenzhen POI CSV, and GIS files (`Shenzhen.shp`, `.shx`, `.dbf`). It supplements UrbanEV rather than forming a third independent station dataset.

The archive was inspected in temporary research storage and its catalog size/SHA-256 verified. This does not change the required acquisition scope in PR #9 or enable supplemental model inputs. Weather/POI/GIS use requires a concrete research purpose and appropriate availability checks.

## 9. Verification status

| Item | Status |
|---|---|
| Archive identity | Size/SHA-256 checked during local acquisition. |
| Station 1001 metadata and charger membership | Inspected directly. |
| Station-distance calculation | Full matrix numerically reconstructed. |
| TAZID-to-GIS linkage | Verified in source attributes. |
| Station-ID origin / TAZID numbering rules | No defining codebook found; do not invent digit/range meanings. |
| Station coordinate reference system | GitHub/Dryad descriptions disagree; unresolved. |
| Availability versus utilization | Explicitly distinguished in the official README. |
| Exact duration/volume reconstruction | Original charger histories and generator code unavailable in inspected sources. |
| Full quality audit of all 1682 station series | Not completed by this document. |

See the [verification evidence](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/urbanev-verification.json) for scope, source versions, hashes, and numeric outcomes. This reference does not claim that data processing, model inputs, models, or experiments have been implemented.

[access]: https://github.com/IntelligentSystemsLab/UrbanEV#data-access
[dryad]: https://datadryad.org/dataset/doi:10.5061/dryad.np5hqc04z
[paper]: https://doi.org/10.1038/s41597-025-04874-4
[availability-note]: https://github.com/IntelligentSystemsLab/UrbanEV/blob/44f2aa0c8d89f192bce00bafb0def74a21b39c68/readme.md#L122
[charging-equipment]: https://www.energy.gov.au/electric-vehicles/owning-electric-vehicle/electric-vehicle-charging-equipment
[acquisition-pr]: https://github.com/HungLD9505/adaptive-retention-ev/pull/9
