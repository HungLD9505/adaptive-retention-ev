# Hùng Final resource preflight addendum v2 — 29 October 2026

**Status: measured Development extrapolation, not a Final scope selection or capacity approval.** This addendum follows the [metadata/lock preflight v1](../hung-final-metadata-preflight-20261029-v1/README.md) and [#23's Hùng-specific pre-execution exception](https://github.com/HungLD9505/adaptive-retention-ev/issues/23#issuecomment-6476049006). It does not resolve #15's UrbanEV-plus-separate-CHARGED scientific scope, choose a Final cohort, open Final labels, submit work or authorize spending.

## Measured source and method accounting

The [v5 Development ledger](../hung-development-782-job-ledger-20261028-v5.csv) is pinned at SHA-256 `bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004`. The CPU tool rehashed all **40 archive files**, re-read exact job receipts and every listed stage manifest through ZIP CRC, and measured all **782 new Development jobs** from saved `dispatch_measurement.json` files. [Per-job rows](measured_development_jobs.csv) retain job, budget, method/config, stage count, summed stage subprocess wall seconds, summed stage output bytes before measurement, ZIP member compressed payload bytes, archive and receipt SHA. This is the authenticated saved execution footprint, not a benchmark on the Final role.

The Development design has **23 entity × budget groups** (6 at 7 days, 8 at 14, 9 at 28), each with **34 new physical jobs across the fixed seeds 7/11/19**: three confidence configs × three seeds (9), eight other seeded methods × three seeds (24), and one deterministic Seasonal Naive run (1). The required Final method/ablation coverage would additionally need Main confidence × three seeds and Block7 confidence × three seeds per group if all three seeds are executed without treating historical jobs as Hùng Final. These six have no complete same-scope new-job stage measurements; the scenario uses the observed Block28 confidence stage profile as an **explicit proxy**, yielding an assumed **40 physical jobs per entity × budget, already including all three seeds**. Method aliases are views, not extra jobs. The scenario count is therefore entity IDs × three budgets × 40, with **no further seed multiplier**. Whether this is the final required jobset awaits the correctness contract and immutable lock.

For each budget, the tool takes the median and nearest-rank 95th percentile of **whole observed 34-job Development groups** (with only 6–9 groups, this p95 is the observed maximum), then adds six Block28-proxy job profiles. It multiplies by 3/10/30 candidate UrbanEV IDs at every budget. The storage column adds measured raw stage-output bytes and compressed ZIP member payload bytes, then displays a separate 1.5 multiplier. This approximates raw-plus-archive coexistence; ZIP headers/shared metadata, raw input, Source fit, provider setup/upload/readback and failures are excluded. It is not a statistical upper bound or a measured Kaggle/Final quota.

| Candidate UrbanEV IDs at each budget | Assumed Hùng Final physical jobs | Median Development-stage scenario | Observed-p95 stage scenario | Raw + ZIP observed-p95 scenario | With 1.5 multiplier |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 360 | 3.562 h | 3.808 h | 8.110 GB | 12.165 GB |
| 10 | 1,200 | 11.873 h | 12.694 h | 27.034 GB | 40.551 GB |
| 30 | 3,600 | 35.620 h | 38.081 h | 81.102 GB | 121.653 GB |

The exact unrounded bytes and scenario assumptions are in [candidate_scenarios.csv](candidate_scenarios.csv); budget-level group/proxy observations are in [summary.json](summary.json). These are aggregate sequential *stage subprocess* seconds, not wall-clock delivery times or GPU quota guarantees. Final-role label completeness, initialized target size, provider hardware/runtime, serialization/compression, Source reuse, and failure/retry behavior can change them substantially. The 1.5 multiplier is a planning cushion, not evidence of sufficient capacity. No speedup from parallelism is assumed.

## Capacity decision and committed shortfall

At this preflight, local D had **3,827,458,048 bytes free**, below the existing **8,589,934,592-byte dispatch reserve** and even below the 3-ID raw-plus-ZIP scenario. Local RTX 3050 Ti had 4,096 MiB total/3,962 MiB free, but no Final-role memory test was run. Kaggle's current authenticated quota remains **unknown**; an attempted read-only SDK call failed before API access because the repo-local venv lacked `kagglehub`, and the user is completing login. No paid scaling or usage reset is authorized. Provider feasibility therefore requires a fresh quota/storage read and bounded shard size/output persistence test after an exact lock; none of these scenario rows authorizes dispatch.

The table covers **UrbanEV/SZH only**. It excludes all six CHARGED cities and their independently attributable Hùng Source/input/artifact requirements, which remain missing from this repository-local package. A smaller UrbanEV cohort or partial saved run must be reported as a shortfall against [#15](https://github.com/HungLD9505/adaptive-retention-ev/issues/15), never called full E2E completion or substituted with Qyroven's runs. All nine baseline families, five ablation categories, budgets 7/14/28 and at least three fixed seeds remain the declared method scope. Block7/parity/CHARGED scientific dispositions remain explicit limitations under the Hùng lead exception.

## Reproduce and checks

From repository root with the exact 40 saved Development archives, create a **new** output directory:

```powershell
python -m tools.hung_final_resource_preflight --root . --output-dir docs/reports/hung-final-resource-reproduction-NEW
python -m unittest tests.test_hung_final_resource_preflight -q
```

The command verifies 782 unique ledger jobs, archive bytes/SHA, job receipt SHA, exact stage names and stage-manifest SHA before measuring. `measured_development_jobs.csv`: SHA-256 `5580706d2b2e006261492a1c711844d16a8456e6d26ff3e76900c89a62d817dc`; `candidate_scenarios.csv`: `d5eee62c42b8b21d82fe40324cb077576ca8d6725fb939caa73b75e8ab45be5c`; `summary.json`: `49943d70dda67e6ba070a6c338f92159f0d1593bc3cd349f8e763b082765b838`.

Two focused offline tests, Ruff lint/format, `py_compile` and `git diff --check` passed. No Final/test labels, new training, provider submit, old output overwrite or usage reset occurred.
