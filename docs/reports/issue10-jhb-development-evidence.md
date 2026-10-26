# Issue #10 evidence register: five CHARGED Development cities

**Status (2026-10-26): Development evidence, pending independent acceptance.** This register supports the [thesis draft](../THESIS_REPORT.md). It records JHB, SPO, MEL, AMS, and SZH as separate-city CHARGED replications and the evidence still needed for the Results, Discussion, and Conclusion. SZH is separate because of UrbanEV coordinate overlap. It does not report a Final result or establish an effectiveness claim.

## Where this evidence belongs in the report

| Report section | Evidence-supported content now | Pending content |
| --- | --- | --- |
| Motivation, research questions, and method | Retain Report 1 and the existing thesis draft as the method source. | Peer review of the final claim boundaries. |
| Data and protocol | JHB, SPO, MEL, AMS, and SZH are separate supplementary cities, each with 7/14/28-day initial histories and three seeds. | Accepted input and cohort handoff for every reported city; publisher-processing and SZH overlap limits remain. |
| Development evaluation | Separate JHB, SPO, MEL, AMS, and SZH matrices, independent daily and latest-state proofs, analyses, catalogued exports, and fresh restores below. LOA has a completed matrix, proofs, and analysis. | LOA export/restore, peer review, and independent teammate reproduction. |
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

## MEL Development addendum

The private Kaggle `mel_20261026_v6` run used committed execution code `83b877e16e7e690d93bb1f7736ce1870ef08fadd` and native Save & Run All persistence. Its complete `_output_.zip` was downloaded to a different host, then a 34-part export was checked against its catalog and restored into a new local root. The original Kaggle proofs and fresh local daily/latest-state proofs are distinct. All 14 methods appear in 27 cells each; all 378 runs have 90 scheduled, issued, and scored days. These repeated method/seed days are not independent sites.

| Artifact (under `D:\Đồ Án\.cache\charged-kaggle-four\runs\kaggle-cli-mel-v6`, except where stated) | SHA-256 | Check or role |
| --- | --- | --- |
| `issue23_charged_MEL_kaggle_v6_mel_20261026_v6.ipynb` | `879ff4ef4aae853672da5143e11c04d543194662df7f0250618e32b749a63c95` | Submitted MEL notebook. |
| `complete-v1-key/issue23-charged-mel-kaggle-v6-mel-20261026-v6.log` | `171c2532e8a482d4122ae2daf9671965625879b7d6ac28320a5c93b2a937b42c` | Kaggle execution log, including the recorded handoff identities. |
| `complete-v1-all/_output_.zip` | `1e88f2a0a9e35aab0d2e302d505307f08af9df87b41d9a32d84e18e72274b2a0` | Complete downloaded Output ZIP, 1,222,809,497 bytes. |
| `complete-v1-export-and-proof/charged-MEL-mel_20261026_v6/matrix.json` | `38768a5c42bce398add908f975f2c256a9e0b575c9204d81d45017ce5314344f` | `technical_success`; 378 cells, three newly trained same-city Source models. |
| `complete-v1-export-and-proof/stage-MEL-mel_20261026_v6/daily-verification.json` | `8df3710c9e73f0b45ade83888bbb0e636c4062bae8defbd8fdffd1ceec2ed0c9` | Kaggle daily proof: 378 runs, 69,930 committed files hashed. |
| `complete-v1-export-and-proof/stage-MEL-mel_20261026_v6/latest-states.json` | `14455607f174fee1cab33fa9bd1a6ed43f56da52f6734d4362490b4b139a993c` | Kaggle latest-state proof: 378 states. |
| `complete-v1-export-and-proof/analysis-MEL-mel_20261026_v6/summary.json` | `264cf39399420ab576beaf41ccefb33554119998e43f736d10131953a0a759fd` | Separate-city Development analysis bound to the matrix and daily proof. |
| `complete-v1-export-and-proof/export-MEL-mel_20261026_v6/catalog.json` | `31530af6f1c666c2cd5ddc8a2a162bd133cc141c1b0cd4ff93402ac6e976b21a` | Complete export, 32 run ZIPs plus `metadata.zip` and `code.bundle`; all 34 part hashes, ZIP CRCs and populations checked after download. |
| `D:\Đồ Án\.cache\charged-kaggle-four\runs\mel-r1-daily.json` | `87701ec69deb09dbfa43288290e9fd562fd77eb1c0973368f7252df40122867d` | Fresh local verification from restored root `mel-r1`: 378 runs, 69,930 files hashed against authenticated MEL inputs. |
| `D:\Đồ Án\.cache\charged-kaggle-four\runs\mel-r1-latest.json` | `8d0026708bfc7f7523486490bc6d18424d3b88a459e3aa30f095c1819763e8d9` | Fresh local CPU verification of 378 latest states, bound to the fresh daily proof. |
| `evidence-register-v1.json` | `98f140d5857635da9c4af9fdc093cd868325220fdc27dca142456e24b65099b3` | Ignored local register of exact notebook, metadata, log, handoff, full ZIP, every package part, Source, and restored-proof paths/hashes. |

The pinned catalog restored 378 runs and 105,886 files to `D:\Đồ Án\.cache\charged-kaggle-four\runs\mel-r1`. Three Source checkpoints loaded on CPU during export and match their restored hashes. The local verifier independently rechecked the daily/input chronology and latest model/optimizer/RNG states after the Kaggle download; it did not train or replace forecasts. The Kaggle notebook's 2,712.99-second wall time and matrix's 2,472.29-second wall time cover different scopes, and neither includes independent teammate reproduction. MEL remains a Development supplement subject to publisher preprocessing/clock limits and peer review. Its scores must not be used to retune a Final design after lock or presented as Final effectiveness.

## SZH and AMS Development addendum

The private Kaggle `szh_20261026_v7` and `ams_20261026_v7` runs used the committed execution code `83b877e16e7e690d93bb1f7736ce1870ef08fadd`. Each completed a separate 378-cell matrix: 14 methods, nine entity-history combinations, three seeds, and 90 issued/scored days per run. Both full Kaggle Output ZIPs were downloaded; all recorded files below were rehashed locally without mismatch. Each complete export has 32 run ZIPs, one metadata ZIP, and one code bundle, and all part SHA-256/CRC checks pass. Fresh local restores and independent daily/input and latest-state checks passed for 378 runs, 69,930 committed daily files, and 378 latest states per city. Three city-specific Source checkpoints per catalog were CPU-loaded. These are Development checks, not Final effects or five-city pooled estimates.

| City / artifact (under `D:\Đồ Án\.cache\charged-kaggle-four\runs`) | SHA-256 | Check or role |
| --- | --- | --- |
| `kaggle-cli-szh-v7/complete-v1-all/_output_.zip` | `f8bf92109165a52a323aebd1322b42c2389e091defbaa4b09d48cc6e922f1a3c` | Complete SZH Output download, 1,498,740,151 bytes; outer ZIP CRC PASS. |
| `kaggle-cli-szh-v7/complete-v1-export-and-proof/charged-SZH-szh_20261026_v7/matrix.json` | `05c2c8909a13fac28b0854105901379191020d219b01962fdb59fe470e22ed5b` | `technical_success`, 378 cells. |
| `kaggle-cli-szh-v7/complete-v1-export-and-proof/stage-SZH-szh_20261026_v7/daily-verification.json` | `632400471f47ac1c041af66b5d53f76ffb18022b5f6dbe1de871db210e9a08b3` | Kaggle daily proof, 378 runs / 69,930 files. |
| `kaggle-cli-szh-v7/complete-v1-export-and-proof/stage-SZH-szh_20261026_v7/latest-states.json` | `6ce078cc23e78739faac3bd3fc90f92f76330b4f02ea9d8a8d24c17edae74ff2` | Kaggle latest-state proof, 378 states. |
| `kaggle-cli-szh-v7/complete-v1-export-and-proof/analysis-SZH-szh_20261026_v7/summary.json` | `f48f2be08dc707748973f1b1a7e3c578bd7dbf943513b66803190fdfb8d102b6` | Separate-city Development analysis. |
| `kaggle-cli-szh-v7/complete-v1-export-and-proof/export-SZH-szh_20261026_v7/catalog.json` | `1aa0fd6c229911afc5e1359ec06a3096e1f73278308aab06506290964d8a09d8` | Complete 34-part export. |
| `kaggle-cli-szh-v7/restored-v1-daily-verification-v1.json` | `70d6cad10da7302c07531cca0b7f3d9bca9fb1ada3de939e93bd75db334f9af1` | Fresh restored daily/input proof, 378 runs / 69,930 files. |
| `kaggle-cli-szh-v7/restored-v1-latest-states-v1.json` | `2341b2916b084e9647462d850e7584a6e4e7b063a10d888409af08a50afa02dd` | Fresh restored latest-state proof, 378 states, bound to fresh daily SHA. |
| `kaggle-cli-szh-v7/evidence-register-v1.json` | `91f7f9c6e23bbe504c98e4cfe016d478aafc328e6c0957ce482e1fb052d43de7` | Ignored register: approved/remote notebooks, log, Output ZIP, every export part, restored files and proof hashes. |
| `kaggle-cli-ams-v7/complete-v1-all/_output_.zip` | `78306dbcf4e8d454eb04b7dc93250fba2abca9098cdf0db4dd5c82c54205de18` | Complete AMS Output download, 1,660,644,042 bytes; outer ZIP CRC PASS. |
| `kaggle-cli-ams-v7/complete-v1-export-and-proof/charged-AMS-ams_20261026_v7/matrix.json` | `1fb798e0dc976c283febc812585951a859e460718552a2f9e3f4553c27015f9b` | `technical_success`, 378 cells. |
| `kaggle-cli-ams-v7/complete-v1-export-and-proof/stage-AMS-ams_20261026_v7/daily-verification.json` | `74c6a9a201349fc824ef80109fdbf9bbc1c95981b53b6074d231f00b8d34ebc7` | Kaggle daily proof, 378 runs / 69,930 files. |
| `kaggle-cli-ams-v7/complete-v1-export-and-proof/stage-AMS-ams_20261026_v7/latest-states.json` | `a7cdb12785ac8ee82d55e8c29fb126307614aadfe333c336cfd190b0f203d349` | Kaggle latest-state proof, 378 states. |
| `kaggle-cli-ams-v7/complete-v1-export-and-proof/analysis-AMS-ams_20261026_v7/summary.json` | `909d946e6223bf191853a0c0bcb652ee4e8d0c936440ce43fef79d4c94f9f2d9` | Separate-city Development analysis. |
| `kaggle-cli-ams-v7/complete-v1-export-and-proof/export-AMS-ams_20261026_v7/catalog.json` | `5cba024958d117274200f8ecd8fa4885d1eeddc4c33cd25b3ea3b670d0882a33` | Complete 34-part export. |
| `ams-r1-daily.json` | `2fb806ea8ddaff8c7223af29e251aaa79092a7de1906b701a1a1ed2b48508d6c` | Fresh restored daily/input proof, 378 runs / 69,930 files. |
| `ams-r1-latest.json` | `9888550f5195a7d0748af990d6c7295a528485d98f469e89b140b83ca340e44b` | Fresh restored latest-state proof, 378 states, bound to fresh daily SHA. |
| `kaggle-cli-ams-v7/evidence-register-v1.json` | `dbdd26d2b169f7099194676a15d6123d519db5e05b1215a17f23097e57d1bf54` | Ignored register with notebook, log, Output ZIP, export parts, restored files and proof hashes. |

SZH has documented coordinate overlap with UrbanEV and must remain an overlap-limited supplement, not independent unseen-location validation or part of a five-city geographic score. AMS belongs to the five-city geographic supplement, but its provider-processed demand and publisher-local-naive clock do not certify strict-online causality. The raw Windows fresh-verifier JSON hashes above differ from Kaggle's Linux JSON because of CRLF versus LF line endings; the registers document byte normalization and proof binding. The verifier results agree in content, and each fresh latest-state proof binds the exact fresh daily bytes. Independent teammate reproduction and peer approval remain open.

## Evidence slots before closing Issue #10

| Scope | Current local state | Required handoff for report completion |
| --- | --- | --- |
| CHARGED JHB Development | Matrix, daily/state proof, relocation, local analysis, complete export, and fresh same-host restore with daily/state re-verification above. | Off-host transfer/readback and independent teammate reproduction; peer review of analysis and cost interpretation. |
| CHARGED SPO Development | Preserved 229-cell interrupted root; new 378-cell matrix, daily/state proofs, relocation, analysis, complete export, and fresh same-host restore with proof re-verification above. | Off-host transfer/readback and independent teammate reproduction; peer review of analysis and cost interpretation. |
| CHARGED MEL Development | Kaggle 378-cell matrix, proofs, analysis, full Output download, 34-part catalog, and fresh local restore/daily/state proof above. | Independent teammate reproduction and peer review of analysis, coverage, and cost interpretation. |
| CHARGED LOA Development | A resumed 378-cell matrix, original daily/latest proofs, Source relocation, and separate-city analysis have passed locally; analysis summary SHA-256 `e7b933ef840e9ef2231bc63e7c3ade177432464fdad9fdb9746e090cca259e26`. The interrupted original root and partial first export are preserved. | Complete fresh catalogued export and restore with independent daily/state proofs, then peer review of provenance, coverage, and cost. |
| CHARGED AMS Development | Private Kaggle 378-cell matrix, full Output download, 34-part export, fresh local restore and independent daily/latest proofs above. | Independent teammate reproduction and peer review of analysis, coverage, and cost interpretation. |
| CHARGED SZH Development | Private Kaggle 378-cell matrix, full Output download, 34-part export, fresh local restore and independent daily/latest proofs above; coordinate overlap with UrbanEV limits the claim. | Independent teammate reproduction and peer review; report separately from the five-city geographic supplement. |
| Qyroven implementation/evaluation | PR #51/#52 are separate implementation evidence; no integrated acceptance is inferred here. | Cross-implementation reconciliation, reviewer decisions, accepted artifact handoff, and explicit treatment of incompatible configurations or cohorts. |
| Final lock and Final evaluation | Not locked or reported by this evidence register. | Independent immutable code/data/cohort/config lock, Final-only execution, complete paired metrics and uncertainty, coverage/null/cost tables, and peer approval. |
| Issue #10 report PR | The existing draft is open for review. | Reconcile each result paragraph with accepted #23 evidence; independent non-author review of the final report PR targeting `dev`. |

Do not fill a pending slot from an unverified run directory, a passed unit test, a Development score, or a favorable subset. Record exact artifact identity and the reviewer decision before moving any claim into the Final Results, Discussion, or Conclusion.
