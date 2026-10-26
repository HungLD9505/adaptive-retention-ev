# Issue #10 evidence register: CHARGED JHB and SPO Development

**Status (2026-10-26): local Development evidence, pending independent acceptance.** This register supports the [thesis draft](../THESIS_REPORT.md). It records two separate-city CHARGED replications and the evidence still needed for the Results, Discussion, and Conclusion. It does not report a Final result or establish an effectiveness claim.

## Where this evidence belongs in the report

| Report section | Evidence-supported content now | Pending content |
| --- | --- | --- |
| Motivation, research questions, and method | Retain Report 1 and the existing thesis draft as the method source. | Peer review of the final claim boundaries. |
| Data and protocol | JHB is one supplementary city, evaluated separately with 7/14/28-day initial histories and three seeds. | Accepted input and cohort handoff for every reported city; publisher-processing limitations remain. |
| Development evaluation | Separate JHB and SPO matrices, independent daily and latest-state proofs, local analyses, catalogued exports, and fresh same-host restores below. | Off-host transfer/reproduction, peer review, and other city matrices. |
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
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\jhb-export-pathfix-20261026-v2/catalog.json` | `4fb9e3c0c83d08a2436886a419b2fe0614b34e9942f7e4102a39f8452aaa3d40` | Complete local package: 32 run ZIPs, one `metadata.zip`, one `code.bundle` (34 parts); 378 run IDs and three CPU-loaded Source checkpoints. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\jhb-restored-daily-v1.json` | `1b501d9fac936f0ed213b61b8ef378315f006f33513fbda89e7ad9643db1f63a` | Fresh restored root `jhb-r2`: 378 runs, 69,930 committed files hashed; matrix SHA matches the catalog. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\jhb-restored-latest-v1.json` | `bb886001009dd76bdf0d01b474d0879bca54e1abae2a926b8d38d55c100372dc` | 378 latest-state checks bound to the restored matrix and new daily proof. |

The matrix covers 14 unique methods or ablations, 27 cells each: nine entity-history combinations times seeds 42, 43, and 44. Every run records 90 scheduled, issued, and scored days, for 34,020 scored run-days; this repeats origins across methods and seeds and is **not** 34,020 independent evaluation units. All 378 runs have no pending days and non-null MAE/RMSE. Six Seasonal Naive cells on two near-zero-load entity-history combinations have zero MAE/RMSE. The analysis must retain these cells and disclose their influence rather than selecting them away.

All three original Source checkpoints and their copied execution counterparts were independently rehashed against the relocation record; the three original/copied completion records also match. The catalogued package was restored to a fresh same-host root with 105,887 files, including `code.bundle`; restored matrix, original proofs, and all three Source checkpoint hashes match the catalog. New daily and latest-state verifiers passed against that root. This is local transport and re-verification evidence, not proof of an off-host download or independent teammate reproduction. The matrix's 3,675.20-second `wall_seconds` covers only the resumed segment. Recorded Source training was 42.16 seconds once, and completed target-run elapsed times sum to 5,331.92 seconds; their 5,374.08-second sum is a component cost, not an end-to-end city wall time. Original interrupted compute, setup, verification, export, and transfer costs are not fully measured.

The JHB analysis labels itself a five-city geographic supplement with publisher preprocessing and clock limitations. It forbids city pooling, city-specific retuning, reuse of UrbanEV Source weights, and strict-online or independent-external certification. Its intervals and proxy associations are exploratory Development diagnostics. They do not support a superiority or null-effect conclusion for Final.

## SPO Development addendum

SPO uses its own Source population and the same transferred primary Development recipe; it is a separate city, not an extra seed or pooled JHB result. The original interrupted SPO root remains preserved. A relocation record verifies 229 copied completed cells and 149 newly completed cells in a new 378-cell matrix. Execution code is `83b877e16e7e690d93bb1f7736ce1870ef08fadd`; clean analysis/export code is `5b6b7531b9db7398307bef8d5f17244c7d0b8efd`. The files below are ignored local artifacts, not included in this report PR.

| Artifact (relative to `D:\Đồ Án\.cache\charged-replication\runs`, except where stated) | SHA-256 | Check or role |
| --- | --- | --- |
| `hung-charged-SPO-development-20261026-resumed-v1/matrix.json` | `eeec1516fc3c58e16bce0815e9e1bb782410a637dad634dfec3d3295deba8f82` | `technical_success`; 378 distinct method/entity-history/seed cells. |
| `hung-charged-SPO-development-20261026-resumed-v1-verification.json` | `0b0594592b513774f81ba063a272c4c138dd0c792c1c5f42bb4f3dcc56d7b688` | `verified`; 378 runs, 69,930 committed files hashed. |
| `hung-charged-SPO-development-20261026-resumed-v1-latest-states.json` | `21257ed43779d25821ce8fbb80a8d6804b002147c0d07d21f57e7cd88e95ce40` | `verified`; 378 latest-state checks. |
| `hung-charged-SPO-development-20261026-resumed-v1-source-relocation.json` | `b0aa005b081266389a35549ec0f2e3f4831f3c02c6736ed9b5ffbe982d2d4374` | 229 copied/reverified completed cells, 149 newly completed cells; original interrupted root preserved. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\spo-analysis-pathfix-20261026-v1/summary.json` | `24279c4f361d458b6c25ac553f6d6e47753c5a736e731d6c6d85328b3bdc0dfc` | Separate-city Development analysis; 378 lineage rows. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\spo-analysis-pathfix-20261026-v1/runs.csv` | `b9cc353fb2726b9b0bae28066d7e75cbb0e927bd950d897f1928cb0f6b18d779` | Per-run Development table. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\spo-export-pathfix-20261026-v1/catalog.json` | `3437ab0282a1e17e9d6b02e09111b13ed25718c73cf03d2f4dd716d58d479381` | Complete local package: 32 run ZIPs, one metadata ZIP, one code bundle; 34 parts/378 runs. All part hashes and ZIP CRCs passed; both analysis and relocation records attached. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\spo-restored-daily-v1.json` | `0b0594592b513774f81ba063a272c4c138dd0c792c1c5f42bb4f3dcc56d7b688` | Fresh restored root `spo-r1`: 378 runs and 69,930 files; all run records match the original proof. |
| `D:\Đồ Án\.cache\charged-analyzer-paths\.cache\spo-restored-latest-v1.json` | `21257ed43779d25821ce8fbb80a8d6804b002147c0d07d21f57e7cd88e95ce40` | 378 latest-state records match the original proof and bind to the fresh daily proof. |

The matrix and analysis retain all 14 methods, three Development entities per 7/14/28-day budget, seeds 42/43/44, and 90 issued/scored days in every run. There are 34,020 scored run-days across repeated methods and seeds, not 34,020 independent sites. No null MAE cells were removed. The 34-part package totals 591,599,208 bytes; its code bundle has SHA-256 `b37fc974ce26ede077f920eba7071f9f4a16d34b186362c309f1329446fc2561` and verifies at the analysis/export commit. Fresh same-host restore passed with 105,887 files. Restored Source seeds 42/43/44 were independently CPU-loaded at epoch 10 with SPO identity and catalogued hashes. This proves local transport and re-verification, not off-host transfer or independent teammate reproduction.

The matrix's 3,275.29-second `wall_seconds` covers the resumed segment only. Source training cost was 26.86 seconds once; target-run elapsed times sum to 5,317.54 seconds. These component costs do not establish end-to-end city wall time. SPO retains the same publisher preprocessing, local-clock, conditional-cohort, and descriptive-interval limitations as JHB. No SPO Development score is a Final result or an effect claim.

## Evidence slots before closing Issue #10

| Scope | Current local state | Required handoff for report completion |
| --- | --- | --- |
| CHARGED JHB Development | Matrix, daily/state proof, relocation, local analysis, complete export, and fresh same-host restore with daily/state re-verification above. | Off-host transfer/readback and independent teammate reproduction; peer review of analysis and cost interpretation. |
| CHARGED SPO Development | Preserved 229-cell interrupted root; new 378-cell matrix, daily/state proofs, relocation, analysis, complete export, and fresh same-host restore with proof re-verification above. | Off-host transfer/readback and independent teammate reproduction; peer review of analysis and cost interpretation. |
| CHARGED MEL Development | Pending in this local evidence register. | Separate-city complete matched matrix, proofs, analysis, and restore. |
| CHARGED LOA Development | Pending in this local evidence register. | Separate-city complete matched matrix, proofs, analysis, and restore. |
| CHARGED AMS Development | Pending in this local evidence register. | Separate-city complete matched matrix, proofs, analysis, and restore. |
| CHARGED SZH Development | Pending in this local evidence register; coordinate overlap with UrbanEV limits the claim. | Separate-city complete matched matrix, proofs, analysis, and restore; report separately from the five-city geographic supplement. |
| Qyroven implementation/evaluation | PR #51/#52 are separate implementation evidence; no integrated acceptance is inferred here. | Cross-implementation reconciliation, reviewer decisions, accepted artifact handoff, and explicit treatment of incompatible configurations or cohorts. |
| Final lock and Final evaluation | Not locked or reported by this evidence register. | Independent immutable code/data/cohort/config lock, Final-only execution, complete paired metrics and uncertainty, coverage/null/cost tables, and peer approval. |
| Issue #10 report PR | The existing draft is open for review. | Reconcile each result paragraph with accepted #23 evidence; independent non-author review of the final report PR targeting `dev`. |

Do not fill a pending slot from an unverified run directory, a passed unit test, a Development score, or a favorable subset. Record exact artifact identity and the reviewer decision before moving any claim into the Final Results, Discussion, or Conclusion.
