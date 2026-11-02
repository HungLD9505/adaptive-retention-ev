# Frozen-input cause of the common unscored Final origin

The [scored-origin symmetry audit](hung-final-coverage-symmetry-20261030-v1.md) found that all 120 unscored job-origins correspond to station 2118 on 9 December 2022, repeated across 40 physical jobs and three history budgets. This audit reads the **same frozen input ZIP** carried into Final, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`, and checks the exact station/origin label record in each 7/14/28-day member. The [machine evidence](hung-final-null-label-input-20261030-v1.json), SHA-256 `98f0b1f1c94118802a6ad2473a69545bcb26f626abe20299e6e0c35cd0d7599b`, records the member and record hashes without publishing the energy series.

| History budget | `labels.jsonl` member SHA-256 | Exact matching label-record SHA-256 | Valid bins | Invalid local hours |
| --- | --- | --- | ---: | --- |
| 7 days | `de1353e8c93f61f2ccf904cf81ae8481b2be978c37964bc175b514581ccb13cc` | `85f47b1e46355ffce81522f85e79d6cc3be878e3784eb987ae6743d7ba66232b` | 21/24 | 11:00, 12:00, 13:00 |
| 14 days | `64707cfe755767e0e0b76bab8bb6066bab5a60acef8b30133c573c8cf659015f` | Same exact record hash | 21/24 | 11:00, 12:00, 13:00 |
| 28 days | `dca145ce60b3e321e8205becb5dabce4b9154121ef266ca3a50141df78f9dcf2` | Same exact record hash | 21/24 | 11:00, 12:00, 13:00 |

At all three invalid hours (`+08:00`), `file_valid=false` and `energy_kwh=null`. The remaining 21 hours have valid flags and non-null energy. The three budget-specific records are byte-identical even though their surrounding `labels.jsonl` members differ. Under the locked all-24-valid scoring/update gate, this origin is issued but cannot be scored or used for a candidate update. This is the **proximate input-level reason** for the observed null metric. The ZIP does not reveal why the original station data lack those three hours; no value is imputed and no upstream cause is invented.

Reproduce from the repository root with a new output path:

```sh
python -m tools.hung_final_null_label_input_audit_v1 \
  --input-zip .cache/kaggle-payload-v2/payload/inputs.zip \
  --output NEW_CREATE_ONLY_PATH.json
```

The CLI refuses an existing output. Three synthetic tests check identical budget records, budget divergence and an invalid flag/null-energy inconsistency. The 151 MB input ZIP remains ignored and was read without modification. This audit does not change the frozen Final or constitute independent scientific approval.
