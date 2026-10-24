# Development seasonal-naive rerun check — 2026-10-24

**Status:** the user reran all five code cells of the proposed seasonal-naive comparison notebook. This is a reproducibility check of the two-entity diagnostic, not another independent model-training experiment or acceptance of #22.

## Evidence inspected

- [Executed Colab notebook](https://colab.research.google.com/drive/1WjwJDhPEC18qlXNFNIjq6oqCQnad6HFV): code cells show execution counts `[1]` through `[5]`. The first cell printed run ID `hung-urbanev-7d-seasonal-comparison-20261024T070157944924Z`; the last printed its Drive path and six comparisons. The configured runtime remained T4, while the code used pinned CPU PyTorch.
- [New Drive run folder](https://drive.google.com/drive/u/0/folders/1bw5Ik0V4H1NqCXwn3Fe7QdhHKxApVa6a): `comparison_summary.json`, `handoff_complete.json`, and `entity-1001`/`entity-1871` folders are present. Each entity folder contains `run_manifest.json` and `issued_forecasts.jsonl`. There is no separate stdout/stderr `.log` file in this handoff; the saved notebook outputs and manifests are the available execution records.
- The marker identifies code commit `1d33418e8953fcf9bff8f360c802a3daeb45878c`, summary SHA-256 `66edfa2300f61de7105d0c6ebf08fc340f5cd648e462d47b7da5e87eb02b02f3`, and hashes for all four entity files. Both entity manifests report `status: completed`, `max_origins: 90`, and the accepted 7-day input manifest SHA-256 `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`. The notebook's publication helper checks hashes after copying to Drive. The Drive preview and marker were inspected; the Drive bytes were not independently downloaded and rehashed in this check.
- The summary pairs the baseline with the previously saved adaptive three-seed run `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`. The new notebook does **not** retrain Source or the adaptive model.

## Result and coverage

| Entity / initialization in adaptive run | Requested origins | Issued | Scored days | Baseline MAE (kWh) | Adaptive mean MAE, seeds 7/11/19 (kWh) | Scored fallback hours |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1001 / target initial adaptation | 90 | 59 | 52 | 4.8798 | 4.2836 | 0 |
| 1871 / source checkpoint only | 90 | 75 | 38 | 4.0443 | 2.6487 | 23 |

All six paired adaptive MAEs are lower than the proposed baseline MAE. The detailed pairs are in the [first comparison report](hung-development-seasonal-comparison-20261024.md) and both Drive summaries. The rerun produced the **same forecast-file SHA-256 values** as the prior run: entity 1001 `8c59a2fcdc8c2e2ff78c82b639fe8ba0ef3caa29a2d6856a761a07ebf810a41d`, entity 1871 `748498968acceb6464ccaed646ffe56524d9021c7753dc584df64a96f90213c6`. Summary and manifest hashes changed because the run ID and run paths changed. This demonstrates repeatability of this deterministic baseline artifact, not independent evidence from additional seeds, entities, or budgets.

Entity 1871 used 23 fallback hours among its 912 scored forecast hours; the fallback definition remains a proposed choice pending #22 review. Coverage is limited: 52/90 and 38/90 requested origins produced fully scored days. The Colab setup cell again printed `pip check` warnings for missing `jedi` in the preinstalled IPython environment and a `torchvision`/CPU-PyTorch version mismatch; execution continued and all five cells completed.

## Assessment and remaining gates

For these two 7-day Development entities, the adaptive model beats this *proposed* seasonal baseline. The result cannot establish overall model quality or #21/#22/#39 acceptance. Source training used one bounded pass in the earlier adaptive run; this rerun does not satisfy #39's representative Source training or its 7/14/28-day Development evidence. #22 still requires nine reviewed baselines and five ablations, comparable tuning/cost evidence, and real Development smoke for each method. Final remains untouched until configuration is locked from Development evidence. No new GitHub claim or issue closure follows from this repeat run.
