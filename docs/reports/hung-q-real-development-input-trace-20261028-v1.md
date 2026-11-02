# Bounded Hùng–Qyroven trace on real Development input — 28 October 2026

**Disposition: additional parity evidence, not implementation parity approval.** This extends the [synthetic common trace](hung-q-common-trace-20261028-v1.md) with the same saved UrbanEV/SZH predictor arrays and next-day labels for both runners. It does not use Final/test inputs, compare method effectiveness, select an architecture or replace the executed Development runs. The [machine-readable v3 result](evidence/hung-q-real-development-input-trace-20261028-v3.json) is authoritative for this bounded run. [V1](evidence/hung-q-real-development-input-trace-20261028-v1.json) and [v2](evidence/hung-q-real-development-input-trace-20261028-v2.json) are preserved as preliminary snapshots; v1 lacks the full Hùng decision fields, and both earlier output files used platform CRLF endings before Git normalized their blobs to LF.

## Pinned input and setup

The source is `.cache/kaggle-payload-v2/payload/inputs.zip` inside this repository, 151,254,390 bytes, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`, matching the tracked [DATA-v1 release catalog](../../data/releases/DATA-v1-20261019.json). The 7-day input-run manifest SHA-256 is `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`. The tool streams and verifies the complete `entities`, `schedule`, `forecasts` and `labels` ZIP members against that manifest, then selects station `1001` and its first 14 consecutive `created` Development origins, 1–14 December 2022. Selected 14-row SHA-256 values are in the JSON (`schedule bbee248d…`, `forecasts c9132872…`, `labels ffc5ac97…`). Every selected label is complete and available at the next daily tick. The tool retains label rows as opaque bytes and decodes their values only in the label callback after the availability gate; it checks the two runners request the same 14 origin/as-of pairs.

Qyroven's runner comes from byte-pinned Git commit `83b877e16e7e690d93bb1f7736ce1870ef08fadd`; three core source SHA-256 values are enforced by the tool. Hùng's runner SHA-256 is `38adc3c9952481e89c1417dfc677f3e9abb3bd3eda8accd2709bc547fdb52baa`. The [trace tool](../../tools/hung_q_real_dev_trace.py) SHA-256 is pinned in the JSON. Python 3.13/PyTorch 2.8 CPU used one Torch thread and deterministic seed 7. The two models start with identical GRU encoder tensors (maximum difference 0) but their existing forecast heads are different; **both models are randomly initialized, not the executed trained Source/Target checkpoints**. Each runner has its own frozen copy as Source reference and a unit latent scale. The common diagnostic controller uses levels 0/0.1/0.2, initial 0, 14-day block, Bmin 5, delta 0, alpha 0.05, two-day bootstrap segments, 100 resamples and learning rate 0.001. These diagnostic identities are not a proposed Final lock.

## Observations

| Check | Result | Meaning and limit |
| --- | --- | --- |
| Label access | Both runners requested exactly 14 labels, each at origin +1 day, and all 14 were complete. | This bounded schedule respects the input's next-day availability; it does not test delayed or missing cases. |
| Core chronology | Both normalize to the same 44-event `forecast → score → update` sequence, followed by decision/fork. | Qyroven logs 72 raw events versus Hùng's 59; normalization collapses Qyroven's three candidate-update events and omits Hùng's provisional deferral events. Raw event equivalence is **not** claimed. |
| Forecasts | Maximum absolute difference across the 14 × three saved candidate forecasts is `0.2929646968841553` **normalized units**; the first-origin difference is `0.2125597596168518`. | Different heads already produce different first forecasts. This is not a tolerance pass or a MAE comparison. |
| Model state after block | Initial shared encoder difference is `0`; selected active encoder difference after the 14 updates is `0.02432682365179062`. | Different heads and update paths prevent attribution to one component. |
| Controller | Both use 14 valid days and keep λ=0 with `no_qualifying_challenger`. Qyroven challenger LCBs are `-0.000434190`/`-0.000849382`; Hùng's are `-0.000344154`/`-0.000693473`. | Same decision in this one block does not settle bootstrap RNG/quantile parity; the [varying-day fixture](hung-q-parity-20261027-v1.md) still shows a marginal-switch difference. |

The JSON preserves every origin-level maximum forecast difference, raw event lists, normalized core events, label access pairs, full decisions, input SHA identities and the diagnostic initial-state SHA. The authoritative v3 JSON was copied byte-for-byte from ignored `.cache/hung-q-real-dev-trace-output-v4/result.json` with canonical LF endings. Its raw **and Git-blob** SHA-256 is `78351693fd21d8ded23be4b13c73a3b39653d873589be665fc0cbe37049b212c` (15,720 bytes). The initial state `.pt` and Qyroven tick files remain in that ignored output directory and were not committed.

## Reproduce and remaining parity gate

From the repository root, with the byte-pinned Qyroven extraction and DATA-v1 ZIP already inside this repository, use a **new** output directory:

```powershell
python -m tools.hung_q_real_dev_trace --qyroven-root .cache/parity-q-20261027-v1 --input-zip .cache/kaggle-payload-v2/payload/inputs.zip --output-dir .cache/hung-q-real-dev-trace-output-NEW
python -m unittest tests.test_hung_q_real_dev_trace -v
```

The tool rejects different ZIP/core-code hashes, malformed selected input, premature or inconsistent label access and an existing output directory. Two focused failure-gate tests pass; Ruff check/format and `py_compile` pass. No full-suite claim is made for this new tool. A non-author reviewer still must choose the correctness-based head and bootstrap/quantile contract and define a matched trained-state, full event/gradient/optimizer/checkpoint-resume trace with declared tolerance. The present 14-origin observation cannot make that decision or authorize Hùng Final.
