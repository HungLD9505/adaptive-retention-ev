# Hùng Development paired-gain seed stability — 29 October 2026

**Scope: descriptive Development comparison only.** This create-only audit extends the [851-run CPU analysis](../hung-development-audit-20261028-v2/report.md) with seed-level paired MAE/RMSE gain. It does not select a method or Final configuration, infer effectiveness on the 407 zero-scored runs, or use Final/test data. The saved merged source `.cache/development-851-merged-results.json` is 14,030,042 bytes, SHA-256 `82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d`.

## Identical comparison support

The pinned source contains 816 valid paired station×seed cells in 72 method×reference×budget groups. **66 groups** have seeds 7/11/19 at every participating station; **six Seasonal Naive groups** contain seed 7 only and cannot support a seed-stability claim. For each of the 288 station×group strata, the saved `paired_day_ids_sha256` and paired-day count agree across the participating seeds. Each [seed row](seed_gains.csv) therefore averages paired gains over the same station set and paired days within its group. Gain is **reference error minus method error** in original kWh; positive means the method's error is lower. The 72 group means were checked against the saved station-first MAE and RMSE rows within `1e-9` kWh.

The complete [72-row stability table](seed_stability.csv) records seed-specific minimum, maximum and span of station-first MAE/RMSE gain, paired station and seed denominators, paired-day range, and station sign consistency. The [204 seed rows](seed_gains.csv) include each seed's station-first gain and positive/negative/zero station counts. The six one-seed groups have **null** seed spans, not zero variability.

## Observed variation

Four of the 66 three-seed groups have station-first MAE gain below zero for one seed and above zero for another: `block28` versus Main at 7 and 14 days, `fixed_retention` versus Main at 7 days, and `online_best` versus Main at 7 days. The exact seed values are in the CSV. Across the 264 station×comparison strata within three-seed groups, 49 show both gain signs or a zero among seeds, 162 have positive gain at every seed, 50 negative at every seed and three zero at every seed. These strata repeat stations and references across methods; the counts are **not an independent win rate or a pooled method ranking**.

For example, at 7 days Online Best-lambda versus Main has station-first MAE gains of about `-0.02155`, `+0.01815` and `+0.01134` kWh for seeds 7, 11 and 19, with two of three stations changing sign across seeds. The proxy/controller rows for Source Error, Uncertainty and Drift are present in the tables for each budget and seed. Their method-level paired gains describe observed comparisons, **not a correlation between proxy signal and retention value**.

## Context and proxy limits

The pinned `paired_cells`/`station_first` records have no context, season, weekday, hour or period columns. The 851 merged run records contain aggregate proxy call/time costs, but no per-origin proxy signal values. Thus this source cannot support a context-sliced error curve or a per-origin proxy-signal/retention relationship. Such an analysis would require a separately pinned, same-origin join of saved forecast errors, controller/proxy signals and input context; no context category is invented here. The 407 zero-scored runs remain null because the [frozen-input audit](../hung-zero-score-label-audit-20261028-v1/report.md) found incomplete 24-hour labels.

## Reproduce and checks

From the repository root, use Python 3.12+ and a **new** output directory:

```powershell
$env:PYTHONUTF8='1'
python -m tools.hung_development_seed_stability --input .cache/development-851-merged-results.json --sha256 82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d --output-dir docs/reports/hung-development-seed-stability-reproduction-NEW
python -m unittest tests.test_hung_development_seed_stability -v
```

The tool refuses a changed source hash, an existing output directory, duplicate paired cells, different station sets or paired-day hashes across seeds, missing seed coverage, or a mismatch to the saved station-first aggregates. The output is create-only. Its source code is [here](../../../tools/hung_development_seed_stability.py). Output SHA-256: `seed_stability.csv` `a409276df1b32f80973d6d5551d808774269e8bdcd653633b4d1cd3cf5ccda4c`; `seed_gains.csv` `1157fb0dd1d43989ec2255219866e2bab7b7edee00d4bfd8a5d28cc4ba8a4001`; `summary.json` `6ac21a99e2ef02baefaf1062d51d4950c98c1fbe1ba5882124ee0cbd08a17d6d`.

Checks on this artifact: create-only command completed, 3 focused offline tests passed, Ruff lint/format and `py_compile` passed, exact relative links and `git diff --check` passed. No training, provider API or Final/test input was used.
