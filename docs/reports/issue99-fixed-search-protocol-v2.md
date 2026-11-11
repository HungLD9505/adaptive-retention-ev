# Issue #99: Fixed calibration with protocol v2

Status: Fixed search completed on Kaggle T4 x2; independent verification and selection pending.

## Bindings

- Scorer commit: `27983845b5d446e3915b0b4353570466f1da23ef`.
- Protocol v2 SHA-256: `f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0`.
- Scored bundle manifest SHA-256: `a09f6a03ae5911717fd5afd070e93b52e0a3a066398278dac7b598bfd89ae088`.
- [Saved Fixed search v2](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-fixed-search-protocol-v2): Version 1, GPU T4 x2, Kaggle reported a successful 967.7-second run. The notebook's search loop reported 916.995 seconds. Its preflight printed `SCORED_PREFLIGHT_PASS` and `ORIGIN_STRING_PREFLIGHT_PASS 4`.

## Observed search log

These are the scorer's calibration outputs as displayed in the saved notebook. They are **not yet independently verified**. All 14 trials reported `complete` with finite macro MAE; the final invocation reported zero new trials.

| Trial | Role | λ | Macro MAE (kWh) |
| ---: | --- | ---: | ---: |
| 0 | zero baseline | 0 | 5.33768456151314 |
| 1 | initial | 0.001 | 5.3376222584571495 |
| 2 | initial | 0.01 | 5.333883344128309 |
| 3 | initial | 0.1 | 5.320981042775908 |
| 4 | initial | 1 | 5.243579767518362 |
| 5 | initial | 2 | 5.249242597193046 |
| 6 | BO EI | 0.40245653239712215 | 5.304914539311685 |
| 7 | BO EI | 0.03323292088182809 | 5.338229437919117 |
| 8 | BO EI | 1.3197902563967503 | 5.249621604940717 |
| 9 | sensitivity | 0.003549536659755571 | 5.335235124418618 |
| 10 | sensitivity | 0.012599210498948734 | 5.333347332603177 |
| 11 | sensitivity | 0.04472135954999578 | 5.338114546768308 |
| 12 | sensitivity | 0.15874010519681997 | 5.3392165668565035 |
| 13 | sensitivity | 0.5634538227695682 | 5.2655805536766715 |

## Verification gate

The first independent verifier package (D) passed its manifest/member checks on Kaggle but lacked the `ev_baselines` import dependency, so it produced no audit verdict. A new immutable verifier package (E) includes 51 byte-matched files from commit `19812d66ef62f40e3bde2c812f3c5e4f14bbbd6d`. Its local ZIP SHA-256 is `091f9ee697818195daedf01202e47c6037ada51cf6ad3abf451051313ff709f5`; manifest SHA-256 is `87cbdbf5ff5b7356a114d7771b1ecc94cfbad779869b7c778e10adcfb03f2f0c`. The verifier E preflight passed inside Kaggle. [Saved verifier E](https://www.kaggle.com/code/hungluongduc/issue99-fixed-protocol-v2-independent-audit-e-v1) Version 1 is running or queued. Selection and the paired comparison remain gated on its `PASS` result with at least one verified objective.

Kaggle output has not been transferred into the repository because the browser denied download access and the user cannot download it manually at present. The linked notebook retains the saved search output. No Evaluation or Final result was used for search or selection.
