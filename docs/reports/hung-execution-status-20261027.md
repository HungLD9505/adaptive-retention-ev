# Hung Development execution and artifact status — 2026-10-27

Refs #10, #15, #22, #23, and #39. Snapshot taken at approximately 01:43 ICT on 2026-10-27, before the remaining matched Development jobs. This is a preliminary evidence handoff for Hung's attributable runs. It is not a Final evaluation, an accepted method comparison, or a claim of effectiveness. Qyroven's runs and recovery are separate.

## Executed runs and retained output

| Scope | Actual execution | Output and transfer check |
| --- | --- | --- |
| Six separate CHARGED Development cities (JHB, SPO, MEL, LOA, AMS, SZH) | Six completed 378-cell matrices, **2,268/2,268 runs** in total; 18 city-specific Source models. The six-city handoff records 419,580 committed daily files hashed and 2,268 latest-state checks. | MEL, SZH, and AMS private Kaggle runs have complete Output ZIPs downloaded locally, 34-part catalogs checked by SHA-256/CRC, fresh local restores, and independent daily/latest-state verification. JHB, SPO, and LOA have complete local runs and 34-part exports. Their canonical private Kaggle archive copies passed byte-exact streaming readback for **36/36 remote files per city**. Original and interrupted roots remain preserved. |
| UrbanEV/SZH representative integrated Development, code `969f3de` | CUDA execution exited 0: 9 Source, 69 Target, 138 replay stages, **216/216**. Independent audit checked 354 artifact hashes with zero missing. | Complete forecasts, logs, checkpoints, audit, and code bundle are in the private archive; all 3 remote files matched local size/SHA-256 on readback. |
| Finite proxy calibration, code `969f3de` | **108/108** declared Development recipe runs authenticated; nine calibration cells and zero null run cells. | Complete plan, event logs, runner checkpoints, selection and code bundle are in the private archive; all 3 remote files matched on readback. |
| Block-size-7 representative Development, code `a0edded` | CUDA execution exited 0 with **216/216** stages; audit checked 354 hashes with zero missing. | Complete run archive and code bundle are private on Kaggle; all 3 remote files matched by streaming SHA-256 readback. This is a completed historical diagnostic, not yet a matched block-size ablation against Main. |
| Parameter Retention lambda grid, code `ffa1336` | Four predeclared candidates completed **252/252** CUDA stages. The selector authenticated all 36 adaptation cells and selected low lambda **10** on Development. | Four output roots, checkpoint/forecast/log/config evidence, selector proof and code bundle are in the private archive; **4/4** remote files matched size/SHA-256 on readback. |

The CHARGED handoff JSON is preserved locally with SHA-256 `0ab82b3378e9a9da2e2e5c4d65f6ff38096f711b268bd815a6fc791fcecfe9c6`. The [six-city evidence register](issue10-jhb-development-evidence.md) gives city-level matrix, catalog, restore, and readback hashes, including the private Dataset links. The [UrbanEV integrated execution report](https://github.com/HungLD9505/adaptive-retention-ev/blob/codex/22-hung-integrated-methods/docs/reports/hung-integrated-development-20261026.md) gives the four local GPU scopes and their private archive identities. The lambda selector proof SHA-256 is `275f440d981f45d8b4ea69795d46859be40ed80dd851c32adc133d2832933e0b`; its private readback proof SHA-256 is `c6a083e79f8ae95cb45eb62f355110874284604beeb9ba72a4fee11c4c5b60c4`.

The private-archive readbacks prove that the listed remote bytes matched the local packages at verification time. They do not establish access for every reviewer or independent teammate reproduction. Large raw outputs and checkpoints remain outside Git; Git contains the small proof and report files.

## What the Development results currently say

- The six CHARGED city matrices each contain 14 methods or ablations across 27 cells per method. Each run records 90 scheduled, issued, and scored days with non-null MAE/RMSE. These repeated method/seed origins are not independent physical sites; city scores must not be pooled. Six JHB Seasonal Naive cells on near-zero-load strata have zero MAE/RMSE and remain visible in the analysis.
- UrbanEV Main and block 7 each have **33/69 null MAE rows** where complete labels were unavailable. No null row is replaced with zero or omitted to improve a score.
- The equal-budget Development mean MAE for the four Parameter Retention low-lambda candidates is 6.841455 (0.1), **6.836163 (10)**, 6.887297 (1000), and 7.020288 kWh (10000). Lambda 10 is a conditional Development choice from the declared verification cells, not an approved Final lock or a superiority result.
- The provisional Development proxy recipes are Drift 1, Source-error 1, and Uncertainty 3. Their evidence is limited to the declared calibration cells.
- Historical block 7 remains separate from an accepted matched ablation: its Source checkpoint matches Main in **0/9** budget/seed strata and its Target checkpoint matches Main in **0/69** representative cells, although the 11 executed source-file hashes agree. Preserve both original run identities; a fairness decision is required before interpreting their difference.

## Prepared work that has not been trained

[Draft PR #68](https://github.com/HungLD9505/adaptive-retention-ev/pull/68) contains a Development-only matched plan and dispatcher. Its authenticated coverage is **920 logical jobs = 69 reused Main + 69 externally complete historical block-7 + 782 scheduled new jobs** (759 CUDA and 23 Seasonal CPU). The 782 new jobs have **no training output yet**; the new output root had not been created at this snapshot. The full dispatcher dry-run was still performing dependency checks and had no confirmed exit code. PR #68 local tests passed (264, with one skipped), and Ubuntu/Windows CI passed at head `7423cf1`; these checks are not training evidence. A safe missing-stage continuation design, independent plan/capacity review, and the block-7 fairness decision remain gates before execution.

Issue #39 still lacks an actual Colab GPU/Drive checkpoint-log handoff or an authorized accepted substitute. No immutable Final lock, Final run, Final result table, or final effect conclusion exists. The [thesis draft](../THESIS_REPORT.md) therefore leaves Results, Discussion, and Conclusion dependent on accepted Final evidence. Independent cross-implementation review, reviewer access and bounded reproduction remain open.

## Reporting and verification boundary

This report summarizes existing executed artifacts; preparing it does not run training or alter any checkpoint. Detailed manifests and SHA-256 catalogs in the linked reports are the authority for individual files. The CHARGED six-city matrix is Hung's separate Development work; it does not complete or relabel Qyroven's Issue #23 recovery. Private Kaggle archives are backups, not Git attachments or public downloads. No test/Final labels were used to choose the Development lambda or proxy recipes.
