# Hùng Final frozen-input scope gap — 29 October 2026

This read-only inventory compares the 360-job Hùng Final lock (SHA-256 `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`) with the `final`-role UrbanEV/SZH identities in its **same frozen input ZIP** (SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`). It does not open Final labels, select a new model, authorize another Final run or establish eligibility for every method.

The lock contains three station IDs: `2118`, `2534`, `2579`. Each 7/14/28-day input manifest names the same 373 `final`-role IDs; the [370-row gap ledger](scope_gap.csv) is their exact set difference. The three `entities.jsonl` members were checked against their manifest byte counts and SHA-256, the input ZIP and jobset against the lock, and every frozen job's input-manifest SHA against its budget manifest.

| Frozen input status among the 370 omitted IDs | 7 days | 14 days | 28 days |
| --- | ---: | ---: | ---: |
| `ready` | 337 | 338 | 342 |
| `undefined_scale` | 33 | 32 | 28 |
| Zero initially trainable samples | 44 | 44 | 40 |

Across budgets, 337 omitted IDs are `ready` in all three; 33 have `undefined_scale` in at least one. The status patterns are 337 ready/ready/ready, 28 undefined/undefined/undefined, four undefined/undefined/ready and one undefined/ready/ready. A `ready` input status alone is not proof that a particular training method has sufficient initial labels: the zero-trainable counts remain explicit. The six CHARGED city scopes are absent from Hùng's frozen Final input ZIP and are not assessed by this UrbanEV ledger.

The [summary](summary.json) pins the input/jobset/lock hashes and all budget manifest hashes. `scope_gap.csv` SHA-256 is `c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681`; `summary.json` SHA-256 is `b5f4b1cd64c713ba98af8f01d7a5851d81135ef2c21b6dc666a2ced80f879053`.

Reproduce without extraction or provider calls from the repository root:

```powershell
python -X utf8 -m tools.hung_final_scope_gap --output-dir docs/reports/hung-final-scope-gap-20261029-v2
```

The destination must not exist; a reproduction creates a new version and must be compared to v1 before any acceptance. The 370 IDs require a reviewed scientific scope/protocol decision before execution. Do not relabel them as already evaluated or tune the frozen 360-job Final from held-out outcomes.
