# Issue #10 evidence register: CHARGED Johannesburg Development

**Status (2026-10-26): local Development evidence, pending independent acceptance.** This register supports the [thesis draft](../THESIS_REPORT.md). It records one separate-city CHARGED replication and the evidence still needed for the Results, Discussion, and Conclusion. It does not report a Final result or establish an effectiveness claim.

## Where this evidence belongs in the report

| Report section | Evidence-supported content now | Pending content |
| --- | --- | --- |
| Motivation, research questions, and method | Retain Report 1 and the existing thesis draft as the method source. | Peer review of the final claim boundaries. |
| Data and protocol | JHB is one supplementary city, evaluated separately with 7/14/28-day initial histories and three seeds. | Accepted input and cohort handoff for every reported city; publisher-processing limitations remain. |
| Development evaluation | The JHB matrix, independent daily and latest-state proofs, and local analysis below. | Off-runtime export/restore, peer review, and other city matrices. |
| Final results, discussion, conclusion | Reporting table and questions already defined in the thesis draft. | Immutable Final lock, complete Final runs and proofs, paired effects/uncertainty, and cost interpretation. |

## JHB evidence available locally

The completed matrix identifies execution code `83b877e16e7e690d93bb1f7736ce1870ef08fadd`. The later analysis identifies code `5b6b7531b9db7398307bef8d5f17244c7d0b8efd` with the cross-platform path comparison fix. The analysis binds the matrix and daily verifier by SHA-256. These files are ignored local artifacts, not files included in this PR.

| Artifact (relative to `D:\Đồ Án\.cache\charged-replication\runs`, except where stated) | SHA-256 | Check or role |
| --- | --- | --- |
| `hung-charged-JHB-development-20261026-resumed-v1/matrix.json` | `ba4d016258572d217e5100b4b549ac8b0f93e253dfa80fb09442c4578f372827` | `technical_success`; 378 distinct method/entity-history/seed cells. |
| `hung-charged-JHB-development-20261026-resumed-v1-verification.json` | `469fe2a4b08235063aa31565778233b3dfd372d123014b5562396d6df9f5c091` | `verified`; all 378 runs, 69,930 committed files hashed. |
| `hung-charged-JHB-development-20261026-resumed-v1-latest-states.json` | `ef8c1b7d1be98d3dca09dd5e7fdb62beb7216805ac90ba4f9084972468a3292a` | `verified`; 378 latest-state checks, bound to the matrix and daily proof. |
| `hung-charged-JHB-development-20261026-resumed-v1-source-relocation.json` | `e5880cb4661dc870234ad0505e947b7c25698912bff7d9b190359597e7afe275` | 156 copied/reverified completed cells, 222 newly completed cells; original interrupted study preserved. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\jhb-analysis-pathfix-20261026-v3/summary.json` | `53383cc223cd745d65255f9c856cbc93e3dfc222f2eee5f0a7699aedf95ab5ba` | Local separate-city Development analysis, bound to matrix and daily-proof hashes. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\jhb-analysis-pathfix-20261026-v3/runs.csv` | `04cffb99324ded541206b5fd2efdb157854b42042d5357d6fcee2e07fc6b5d64` | Per-run analysis table; not a Final score table. |

The matrix covers 14 unique methods or ablations, 27 cells each: nine entity-history combinations times seeds 42, 43, and 44. Every run records 90 scheduled, issued, and scored days, for 34,020 scored run-days; this repeats origins across methods and seeds and is **not** 34,020 independent evaluation units. All 378 runs have no pending days and non-null MAE/RMSE. Six Seasonal Naive cells on two near-zero-load entity-history combinations have zero MAE/RMSE. The analysis must retain these cells and disclose their influence rather than selecting them away.

All three original Source checkpoints and their copied execution counterparts were independently rehashed against the relocation record; the three original/copied completion records also match. The relocation evidence binds Source identity across the resumed study, but a complete, portable export and independent restore are still pending. The matrix's 3,675.20-second `wall_seconds` covers only the resumed segment. Recorded Source training was 42.16 seconds once, and completed target-run elapsed times sum to 5,331.92 seconds; their 5,374.08-second sum is a component cost, not an end-to-end city wall time. Original interrupted compute, setup, verification, export, and transfer costs are not fully measured.

The JHB analysis labels itself a five-city geographic supplement with publisher preprocessing and clock limitations. It forbids city pooling, city-specific retuning, reuse of UrbanEV Source weights, and strict-online or independent-external certification. Its intervals and proxy associations are exploratory Development diagnostics. They do not support a superiority or null-effect conclusion for Final.

## Evidence slots before closing Issue #10

| Scope | Current local state | Required handoff for report completion |
| --- | --- | --- |
| CHARGED JHB Development | Matrix, daily/state proof, relocation, and local analysis above. | Complete catalogued export; fresh off-runtime restore with daily/label/state re-verification; independent review of analysis and cost interpretation. |
| CHARGED SPO Development | Original interrupted study has 229 completed cells; no accepted completed matrix. | Verified prefix continuation to a fresh root, then complete matrix, proofs, analysis, and restore. Preserve the original run. |
| CHARGED MEL Development | Pending in this local evidence register. | Separate-city complete matched matrix, proofs, analysis, and restore. |
| CHARGED LOA Development | Pending in this local evidence register. | Separate-city complete matched matrix, proofs, analysis, and restore. |
| CHARGED AMS Development | Pending in this local evidence register. | Separate-city complete matched matrix, proofs, analysis, and restore. |
| CHARGED SZH Development | Pending in this local evidence register; coordinate overlap with UrbanEV limits the claim. | Separate-city complete matched matrix, proofs, analysis, and restore; report separately from the five-city geographic supplement. |
| Qyroven implementation/evaluation | PR #51/#52 are separate implementation evidence; no integrated acceptance is inferred here. | Cross-implementation reconciliation, reviewer decisions, accepted artifact handoff, and explicit treatment of incompatible configurations or cohorts. |
| Final lock and Final evaluation | Not locked or reported by this evidence register. | Independent immutable code/data/cohort/config lock, Final-only execution, complete paired metrics and uncertainty, coverage/null/cost tables, and peer approval. |
| Issue #10 report PR | The existing draft is open for review. | Reconcile each result paragraph with accepted #23 evidence; independent non-author review of the final report PR targeting `dev`. |

Do not fill a pending slot from an unverified run directory, a passed unit test, a Development score, or a favorable subset. Record exact artifact identity and the reviewer decision before moving any claim into the Final Results, Discussion, or Conclusion.
