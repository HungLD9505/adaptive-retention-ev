# Issue #21 — Qyroven prequential runner handoff

Executed 2026-10-25. Implementation and real Development technical smoke are ready
for review. **Not merged, not a Final configuration lock, not a completed research
experiment matrix.** Issue #21 remains open for peer/integration acceptance and the
full experiment-matrix cost gate described below.

## Implementation and review map

Branch `feat/21-qyroven-prequential-runner` starts from dev
`7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c`. It locally integrates the author's pending
#47/#49 dependency commits using normal Git merges, not cherry-picks or copied Hung
code. No GitHub PR merge was performed. Review/accept those dependencies first;
refresh this branch against updated dev before integrating #21, especially if the
dependencies are squash-merged. The initial PR diff includes their pending changes.

- [Runner contract](../data/PREQUENTIAL_RUNNER.md): formulas/policy, per-target state,
  arrival gates, boundary order, audit isolation, persistence and limitations.
- `ev_runner/engine.py`: score → update → boundary/selected-state fork → forecast.
- `ev_runner/state.py`: independent candidate model/optimizer/Python/CPU/CUDA RNG.
- `ev_runner/replay.py`: accepted #18 artifacts, Development-only role gate, schedule
  accounting and separate delayed-label provider.
- `ev_runner/store.py`: durable forecasts, hash-linked daily transactions, weights-only
  checkpoints; new-directory resume, fail-closed uncommitted tick handling.
- `ev_runner/run.py`, `tools/issue21_colab_smoke.py`: explicit GPU CLI and declared matrix.
- `notebooks/issue21_development.ipynb`: clean-runtime Colab reproduction; reuse the
  exact identified #19 Source checkpoint, never train real datasets locally.

The update profile is declared before scores: common target initialization at
lambda=0.01 for three prefix epochs; one online epoch on each newly arrived full
24-hour vector; three candidates `[0, 0.01, 0.1]`; initial 14-day blocks, Bmin7,
alpha0.05, segment3, 2,000 resamples, delta0, seed42. These are unvalidated Development
example choices, not claims of optimal settings. The #20 valid-day ordinal bootstrap
and missing-gap caveat remain. No new controller/retention methodology is introduced.

## Actual real-data execution

Runtime code SHA: `ac493144ded18e0f8419ad002179588af4302d4b`, clean checkout.
Colab: Python 3.13.16, PyTorch 2.11.0+cu130, CUDA13, Tesla T4.
Source checkpoint SHA-256:
`28d61828a35be69b04f907df9128e7cf4743868060addd113cc61b60363e2905`.
This is #19's full-Source-pool one-epoch checkpoint, reused without selecting a new
seed/checkpoint based on these scores. All target runs are UrbanEV Development 1001.

Run `qyroven-i21-20261025-seed42-v1`: three independent budget runs, each 29 forecast
origins **2022-12-01–2022-12-29**, plus a ten-tick interruption/resume for budget7.
Each whole run includes 31 midnight ticks, with trailing label polling after the last
forecast. There is no moving the forecast start to the first convenient valid day.

| Budget | Initial examples | Issued/scored days | Candidate online steps | Dec 15 decision | Dec 29 decision | Active MAE kWh |
|---|---:|---:|---:|---|---|---:|
| 7 days | 6 | 29/29 | 87 | Keep 0.01 | Switch 0.01 → 0.1 | 4.327766 |
| 14 days | 13 | 29/29 | 87 | Keep 0.01 | Keep 0.01 | 4.316982 |
| 28 days | 27 | 29/29 | 87 | Keep 0.01 | Switch 0.01 → 0.1 | 4.648015 |

Each boundary comparison used 14 complete paired days. Scores above belong to one
smoke target/seed and are **not** evidence that a budget or method is superior.
Initial adaptation steps are recorded separately in `initial_logs`; 87 means
29 arrived examples × 3 online candidates × 1 step, not 87 Source training steps.

Budget7 and28 each executed one audit update after the late switch. **No complete
next-block real audit summary exists in this 29-day run**; the next block has only
one forecast. Full audit-block aggregation/isolation is tested with independent
fixtures, and a longer real run remains necessary before harmful-switch analysis.
Real smoke did not exercise missing histories/labels or `source_checkpoint_only`;
those paths are fixture-tested, not claimed as real cohort evidence.

The budget7 interrupted run issued ten forecasts and had one pending day. Resuming
into a fresh directory reproduced all 29 forecast bytes/IDs, all candidate states
(model, Adam state, Python/CPU/CUDA RNG), audit state, block decisions and counters
exactly. The committed prefix was copied unchanged. Timing fields are deliberately
excluded from exact-equality claims. Mid-operation/crash recovery is **not** claimed:
interrupted `.pending-*` ticks fail closed rather than rewrite issued forecasts.

## Persistent artifacts and independent verification

[Team folder](https://drive.google.com/drive/folders/1B6b51u6CR3MgAU9OJxnKtQxY1naRsWvk),
with inherited team access verified through Drive metadata:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| [ZIP: checkpoints, forecasts, events, logs and checks](https://drive.google.com/file/d/1o-ncefUprcx2BPGulfrsadgVgeQwKWeD/view) | 218,132,244 | `ff1e0a3471ec2ad8c9b7693e373b974a6abe2e79d4c1bc8098379ee8cdd9f392` |
| [Matrix JSON](https://drive.google.com/file/d/1Kew_WcQdn65O57nDjYk5OpzJpw1sZGSA/view) | 58,773 | `4233666de32802ba04db2e715ec052837c0ce69daf3411dd5f5589e01a4d4840` |

[Executed Colab](https://colab.research.google.com/drive/1h0AlP8b_0TLx_zV4Zx13U4ANq9ch0X-E)
retains the earlier #19 execution and adds explicitly marked #21 cells. Drive copies
were hash-checked and flushed/unmounted, then downloaded again independently:
ZIP hash/CRC, all **556 file hashes**, all daily commit chains, prediction-before-score
order, eight fork events (including the reproduced run), candidate step accounting,
final checkpoint state digests and exact resumed-prefix/forecast/state equality passed.
Verification only read/loaded artifacts locally; no local real-data training occurred.

[Small committed evidence](issue21-qyroven-evidence.json) contains the actual matrix
and independent verification summary. Large files remain outside Git. Original local
verification files are under ignored `runs/issue21-colab-20261025/`.

## Checks and cost gate

Local Python3.12.13: **174 tests PASS** (119 foundation +20 model +19 controller
+16 runner/replay). Colab: **174 tests PASS in 10.663s**. Ruff lint/format, sources
listing and diff checks passed locally; Colab lint/format and environment freeze are
in the ZIP. Fixture diagnostics intentionally exercise missing/hash/QC failures.
The source catalog listing is not a fresh verification of raw archives.

The three whole stage timers measured 13.566, 13.740 and15.555 seconds; 42.861 seconds
for 87 scored target-days, or **0.493 stage-seconds/target-day** on this T4. GPU peak
allocated memory was 90,912,768 /89,912,832 /93,920,256 bytes respectively; reserved
memory and separate inference/update/controller/audit time are in the matrix.
These are allocated model-operation measurements, not total GPU process memory.

**Timing limitation:** stage timing starts after `InputRun`/`Replay` construction.
Input hash/schema validation/loading, Python startup, unit checks and packaging are
excluded. Do not present the stage estimate as total wall time. The matrix's explicit
100-target ×29-day ×3-budget ×3-seed ×10-method scenario assumes every method costs a
three-candidate replay: 128,581.745 stage-seconds (~35.72h). This is an illustrative
capacity scenario, not an official cohort/method selection or reliable upper bound.

The **full experiment-matrix runtime gate is still pending**: #22/#23 must supply the
reviewed baseline/ablation/tuning grid and per-method costs, include validation/I/O,
Source training, audits and hardware variability, and revise the capacity budget
before Sprint3 execution. No smaller seed/method/cohort matrix is silently substituted
for Report1. This limitation and acceptance item stay visible in #21.

## Acceptance remaining

Independent peer review, acceptance of the Development example update/bootstrap
profile, dependency integration and combined-dev CI remain pending. No Final data,
CHARGED training, official baseline comparison, multi-seed effectiveness analysis,
configuration lock or main promotion occurred. Preserve the existing upstream
preprocessing/clock and same-location split limitations. The code and technical smoke
can support #22 preparation while these review/cost gates are completed.
