# Six-city supplementary CHARGED proof summary — 28 October 2026

**Scope:** read-only, descriptive Development analysis of the six proof JSONs on [draft PR #67](https://github.com/HungLD9505/adaptive-retention-ev/pull/67) at `c1c62fcb49bdedab42aeb913e8dc3c6821104a57`. These are supplementary configuration replications, not Hung's accepted independent E2E matrix, not Qyroven's primary matrix, and not Final. Remote executor attribution and independent scientific review remain open. The proof run IDs use seeds **42/43/44**; Hung's representative UrbanEV/SZH work declares **7/11/19**, so authorship and comparison scope must not be inferred from the branch or commit author.

## Source and computation

Each city proof contains 378 rows: three history budgets, three entities per budget, three seeds and 14 methods. All 378 rows per city record 90 issued and 90 scored origins. The [read-only summarizer](../../tools/hung_charged_proof_summary.py) rejects duplicate IDs, missing methods/seeds, invalid metrics and mismatched scored-origin hashes within a unit. For each entity and budget it calculates the mean of three `Target-only MAE − Adaptive MAE` differences, then weights the three entities equally within that budget. A positive gain favors Adaptive; a negative gain means Adaptive has higher MAE. The worse count is based on the entity's three-seed mean, not on 27 seed-level observations. Budgets and cities remain separate.

| City | History days | Entities × seeds | Mean MAE gain, kWh | Worse entities |
| --- | ---: | ---: | ---: | ---: |
| MEL | 7 | 3 × 3 | 14.788 | 0/3 |
| MEL | 14 | 3 × 3 | 21.311 | 0/3 |
| MEL | 28 | 3 × 3 | 7.093 | 0/3 |
| SZH | 7 | 3 × 3 | 0.635 | 0/3 |
| SZH | 14 | 3 × 3 | 7.176 | 0/3 |
| SZH | 28 | 3 × 3 | 26.457 | 0/3 |
| AMS | 7 | 3 × 3 | **−5.202** | **2/3** |
| AMS | 14 | 3 × 3 | **−15.579** | **1/3** |
| AMS | 28 | 3 × 3 | **−1.808** | **1/3** |
| JHB | 7 | 3 × 3 | 2.168 | 0/3 |
| JHB | 14 | 3 × 3 | 0.921 | 1/3 |
| JHB | 28 | 3 × 3 | 1.310 | 0/3 |
| SPO | 7 | 3 × 3 | 0.849 | 0/3 |
| SPO | 14 | 3 × 3 | 0.333 | 0/3 |
| SPO | 28 | 3 × 3 | 0.544 | 0/3 |
| LOA | 7 | 3 × 3 | 0.687 | 0/3 |
| LOA | 14 | 3 × 3 | 0.996 | 0/3 |
| LOA | 28 | 3 × 3 | 1.991 | 0/3 |

The adverse AMS rows are retained. These small, predeclared supplementary groups do not support a global method ranking, a significance claim, a CHARGED population estimate or a Final selection. Same-origin proof hashes and per-run summary MAE do not substitute for fresh independent daily-byte readback or full station/time uncertainty. SZH may overlap UrbanEV and cannot automatically be called independent geographic validation.

## Reproduction and open gate

With PR #67 checked out in a separate repository worktree, run from the PR #72 checkout:

```sh
python -m tools.hung_charged_proof_summary --proof-dir <PR67-worktree>/docs/reports
python -m unittest tests.test_hung_charged_proof_summary -v
```

The summarizer emits JSON to stdout and does not create, overwrite or delete run artifacts. This checkpoint inspected the six tracked proof files in the local PR #67 worktree and obtained 18 city/budget rows. Its two focused tests passed. Before including these rows in Hung's accepted #22/#23 or #10 results, a reviewer must establish remote executor identity, the relationship to PR #52 and Qyroven's primary matrix, exact Source/input/config lineage, and independent proof access. Neither the code nor these descriptive numbers resolve that gate.
