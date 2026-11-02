# Hùng Final scope extension — frozen-input feasibility and resource scenario

**Status, 30 October 2026:** This is a read-only planning audit of the **370 UrbanEV/SZH Final-role IDs omitted** by Hùng's locked 360-job, three-station Final. It does not create an extension jobset, approve another Final evaluation, inspect held-out labels, change the original lock or cover any CHARGED city. The original [scope ledger](hung-final-scope-gap-20261029-v1/README.md) is bound to input ZIP SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7` and lock SHA-256 `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`.

The 370-row [source CSV](hung-final-scope-gap-20261029-v1/scope_gap.csv), SHA-256 `c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681`, has 370 unique IDs. I reran `python -X utf8 -m tools.hung_final_scope_gap --output-dir .cache/hung-final-scope-gap-recheck-20261030-v1` against the frozen 151,254,390-byte input ZIP; both generated `scope_gap.csv` and `summary.json` match their published files **byte for byte**. For each budget, the minimal filter here is **`status == ready`, `initial_trainable > 0`, and `scheduled_forecasts > 0`**. It is an input inventory filter, not a method-specific trainability proof or an outcome-based selection rule.

| Omitted-ID input inventory | 7 days | 14 days | 28 days |
| --- | ---: | ---: | ---: |
| `ready` status | 337 | 338 | 342 |
| `ready` and positive initial training/forecast counts | **326** | **326** | **330** |
| `ready` but zero initial training samples | 11 | 12 | 12 |
| `undefined_scale` | 33 | 32 | 28 |

Exactly **326 omitted IDs** pass the minimal filter at **all three** budgets; 330 pass it at least once. The 337 `ready` at all budgets include 11 with zero initial training samples for one or more budgets: `1004`, `1023`, `1075`, `1079`, `1106`, `1274`, `1737`, `1851`, `2193`, `2314`, `2609`. The remaining 33 IDs have `undefined_scale` in at least one budget. The subset of 326 is still **not** a locked or method-ready cohort; source/checkpoint, label eligibility, method-specific initialization and scientific scope decisions are not resolved by these columns.

## Resource implication if the old 40-job template were copied

The existing [Development-based preflight](hung-final-resource-preflight-20261029-v2/README.md) assumes **40 physical jobs per entity × budget**, including fixed seeds and a six-job Block28 proxy for unmeasured Main/Block7 profiles. Its [summary](hung-final-resource-preflight-20261029-v2/summary.json), SHA-256 `49943d70dda67e6ba070a6c338f92159f0d1593bc3cd349f8e763b082765b838`, records only 6–9 observed Development groups per budget. Its reported “p95” is the observed group maximum, **not** a statistical upper bound for new Final-role stations. The scenario omits Source fit, provider setup, retries and CHARGED.

Applying that *same unapproved template* to the 326 minimal-input IDs would imply **39,120 additional physical jobs** (326 × 3 budgets × 40), about **387.1 hours** of summed median Development-stage subprocess times or **413.8 hours** under the observed-maximum profile, and **881.3 GB** of raw-stage-plus-ZIP bytes (decimal GB), rising to **1,322.0 GB** with the preflight's 1.5 working-storage multiplier. Applying it indiscriminately to all 370 omitted IDs would imply 44,400 jobs, 469.7 observed-maximum stage hours and 1,500.4 GB with the same multiplier; that row is **not executable as stated** because the input conditions above fail for some IDs. These are linear sensitivity scenarios, not GPU quota, end-to-end wall time, storage guarantees, or a dispatch recommendation.

The calculation uses each budget's `group_stage_wall_*_seconds + 6 × block28_proxy_stage_wall_*_seconds` and `group_raw_plus_zip_p95_bytes + 6 × block28_proxy_raw_plus_zip_p95_bytes` from the pinned preflight summary, sums the three budgets, then multiplies by 326 or 370. The original three-station Final actually took 17,497.5 provider seconds, whereas the Development proxy estimated 13,709.0 observed-maximum stage seconds for three IDs. Different quantities and stations make direct runtime scaling unsafe.

**Decision needed:** An independent reviewer and experiment owner must determine whether bounded three-station evidence is acceptable for the stated claim, or define a separately locked extension with exact eligible IDs, methods, Source lineage, analysis, provider capacity and the role of all six CHARGED cities. Do not promote the 326 minimal-input IDs into a new Final cohort, use the observed Final scores to select them, or resubmit the original 360 jobs. The current report remains evidence-bound to the executed three-station lock.
