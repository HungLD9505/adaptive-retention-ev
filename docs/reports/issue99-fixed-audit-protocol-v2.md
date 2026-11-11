# Issue #99: independent Fixed audit, protocol v2

The [saved Kaggle verifier E notebook](https://www.kaggle.com/code/hungluongduc/issue99-fixed-protocol-v2-independent-audit-e-v1) Version 1 finished successfully in 885.0 seconds. It read the [saved Fixed search v2](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-fixed-search-protocol-v2) as a read-only input. The verifier was imported from its separately authenticated E package, not from the scorer's saved code.

## Verdict

- Verifier E manifest SHA-256: `87cbdbf5ff5b7356a114d7771b1ecc94cfbad779869b7c778e10adcfb03f2f0c`; all 51 extracted members matched its recorded sizes and hashes in Kaggle. The E ZIP and each member were also checked locally against commit `19812d66ef62f40e3bde2c812f3c5e4f14bbbd6d`.
- Subprocess exit code: `0`. Its `fixed_verify` and `comparison_verify` modules both resolved inside the mounted E package.
- `status: PASS`, `search_complete: true`, `verified_objectives: 14`; all 14 trial objectives were recomputed against authenticated forecasts and labels. The verification JSON is saved inside Kaggle with SHA-256 `233f893338b41e1ac39da9cd0b79b56ad70fa4c86f024900de4ad6dc8fde991e`.
- The independently recomputed macro MAE values match the displayed [Fixed search report](issue99-fixed-search-protocol-v2.md), within floating-point serialization differences in trials 5 and 13.

## Calibration-only selection

The registered `ev_search.select.select_fixed` function ran interactively on the verified calibration ledger, protocol v2 and fixed-search config. It printed λ `0.5634538227695682` from trial 13, with best calibration MAE `5.243579767518362` kWh. The output file SHA-256 was `5d7f834ff6ad4c36d328516e24a25ca2968b67fdc1c068b99aa0b0f7750bf3cb`; its separate [saved selection notebook](https://www.kaggle.com/code/hungluongduc/issue99-fixed-selection-protocol-v2-v1) Version 1 is pending verification.

An independent read-only check of the published calibration table confirmed the registered 0.05 kWh practical-equivalence rule: trials 4, 5, 8 and 13 are within 0.05 kWh of the best; trial 13 has the smallest λ. No Evaluation or Final outcome was used. The result is exploratory because no untouched Development evaluation set has been established.

At this snapshot, browser download access was denied and the full Kaggle artifact had not been copied into the repository. The saved Kaggle notebooks retain the search, audit and selection outputs; local possession and local hash verification of those outputs remain outstanding.
