# Hùng E2E gate register v25 — Final technical archive readback

This create-only checkpoint updates [v24](hung-e2e-gate-register-20261029-v24.md) for the Final execution/readback gate. Earlier Development analysis, null cells and scientific review limits remain current.

| Gate | Status |
| --- | --- |
| Development | 782/782 new jobs locally byte/stage verified; 560/560 Kaggle proof/export; 851 analytical runs. The 407 null-scored runs and 748 blocked paired cells retain their documented reasons. |
| Final lock/input | 360-job lock SHA-256 `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`; 24/24 input payload files passed independent Kaggle CPU readback. |
| Final GPU and archive | [GPU saved version `/1`](hung-final-gpu-launch-20261029-v1.md) `COMPLETE`, producer receipt 360 jobs. [Independent Kaggle CPU output readback](hung-final-direct-kaggle-readback-20261029-v1.md) passed exact **360/360** job archive byte/SHA/CRC and job→artifact ledger; 711 stage maps. No GPU output archive was downloaded locally. |
| Final analysis | Pending: compute scored coverage, MAE/RMSE, paired Transfer Gain, uncertainty, NTR, switching/audit and cost under the frozen analysis plan. Missing labels must stay null. |
| Scientific review | Block7/parity `NEEDS_EVIDENCE`, CHARGED `SUPPLEMENTARY_ONLY`, Colab #39 peer readback open. The locked 360 jobs omit 370 other eligible UrbanEV IDs and six CHARGED city scopes. PR #72 remains draft. |
| CI | Local pinned-code suite 497 tests OK, one skip; Ruff passes. GitHub Actions OS jobs were blocked before tests by account billing/spending-limit. |

Final technical readback is a verified milestone, not completion of the E2E study or thesis report #10.
