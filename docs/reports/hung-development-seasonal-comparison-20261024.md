# Proposed seasonal baseline: Development comparison (2026-10-24)

**Status:** completed diagnostic, not #22 baseline acceptance or model selection. No Final examples or labels were accessed.

## Executed runs and identity

- New Colab [notebook](https://colab.research.google.com/drive/1WjwJDhPEC18qlXNFNIjq6oqCQnad6HFV), [Drive handoff](https://drive.google.com/drive/u/0/folders/1k0D6iZa_fBx8BFb4D_0ZuUGL5ZYqstuS), run ID `hung-urbanev-7d-seasonal-comparison-20261023T170548401281Z`. All five code cells produced outputs, including the final Drive path. The Drive folder contains `comparison_summary.json`, two entity folders, and `handoff_complete.json`. The marker lists SHA-256 `51ab02c4c3efae066252509fd6dec54017862fb8b0853a8d448114bcaa2618f2` for the summary and hashes for four forecast/manifest files. The publishing cell verified copied file hashes.
- Code commit `1d33418e8953fcf9bff8f360c802a3daeb45878c`; uploaded code bundle SHA-256 `29a6aa4959bb574e3a1d7a96b5ea3745a980fd6e4e199a6e178d6b5f3e26df14`; accepted 7-day input manifest SHA-256 `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`.
- Comparison uses the previous [three-seed Development run](https://drive.google.com/drive/u/0/folders/1cNfTOxWk1SPD77W0P4bszED4cYkDuYW7), run ID `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`. Its handoff marker and replay-manifest hashes were checked. Each paired comparison has the same scored origin set and input identity. The candidate model uses seeds 7, 11, 19; the deterministic baseline is computed once per entity.
- Colab was configured for T4. The pinned PyTorch package was `2.8.0+cpu`, so this run did not use the GPU. `pip check` warned that Colab's preinstalled IPython lacks `jedi` and `torchvision` expects another PyTorch version; the experiment cells nevertheless completed. Colab later reported a disconnected runtime and an empty Active sessions list while requesting another T4 allocation. The saved handoff files were inspected on Drive.

## Paired results

MAE is in kWh per hourly forecast, scored only after the label availability cutoff. `model − baseline` below is negative when the candidate has lower error. These values are transcribed from the Drive `comparison_summary.json`.

| Entity | Seed | Scored days | Candidate MAE | Proposed seasonal MAE | Model − baseline |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1001 | 7 | 52 | 4.3940 | 4.8798 | -0.4858 |
| 1001 | 11 | 52 | 4.2122 | 4.8798 | -0.6677 |
| 1001 | 19 | 52 | 4.2446 | 4.8798 | -0.6352 |
| 1871 | 7 | 38 | 2.6776 | 4.0443 | -1.3667 |
| 1871 | 11 | 38 | 2.6051 | 4.0443 | -1.4392 |
| 1871 | 19 | 38 | 2.6635 | 4.0443 | -1.3809 |

The candidate has lower MAE in all six paired cells. Mean candidate MAE across seeds is 4.2836 for entity 1001 and 2.6487 for entity 1871, versus 4.8798 and 4.0443 for the proposed seasonal baseline. This is evidence for these two entities, one 7-day budget, and 90 requested origins only. Repeating a deterministic baseline against three candidate seeds does not create three independent target cohorts.

The baseline repeats the prior 24-hour observed pattern, with an explicit fallback for missing hourly history. Report 1 does not fix this fallback rule, so the run is labeled `proposed_not_accepted`. Entity 1871 is `source_checkpoint_only` in the candidate run; its target has zero adaptation steps. The candidate Source training used one pass, not the representative budget required by #39.

## Remaining acceptance work

Do not infer that the candidate is generally good, that #22 is complete, or that Final is ready. #22 still requires the other baselines, five ablations, full Development cohort/budgets and a reviewed fallback definition. #39 still requires representative Source training. Compare seed distributions and coverage for both `target_initial_adaptation` and `source_checkpoint_only`, then lock the configuration using Development evidence before evaluating Final once. The [capacity note](hung-development-capacity-20261023.md) counts 891 eligible entity-budget cells before multiplying by seeds for one method; this two-entity diagnostic is far smaller.
