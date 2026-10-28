# Bounded Hùng–Qyroven same-input runner trace — 28 October 2026

**Disposition: partial synthetic trace only; implementation parity remains pending.** This extends the [component audit](hung-q-parity-20261027-v1.md) and [forecast-head contract aid](hung-q-head-contract-review-20261028.md). It does not choose a shared architecture, calibrate a controller, compare research performance or authorize Hùng Final. The [machine-readable trace](evidence/hung-q-common-trace-20261028-v1.json) records both event streams and source hashes.

## Pinned fixture

The create-only CPU fixture invokes Qyroven's runner from extracted Git commit `83b877e16e7e690d93bb1f7736ce1870ef08fadd` and Hùng's current runner. The Qyroven engine, controller and model file bytes were compared with `git show` for that commit and matched; the trace tool also rejects any different SHA-256 for those three files. The Hùng runner SHA-256, tool SHA-256 and fixture-array SHA-256 are in the JSON. Runtime was Python 3.13, PyTorch `2.8.0+cu126` on CPU with deterministic seed 42 and one Torch thread.

Both runners receive the same two synthetic 24×7 history and 24×5 future-calendar arrays, energy scale 10, retention levels `(0, 0.1, 0.2)`, initial lambda 0.1, two-day block, Bmin 2, segment length 1, 20 bootstrap draws, alpha 0.05 and a deliberately high delta 100. The first 24-hour label vector is 4 kWh at each hour and becomes available at the next daily tick. The second day's label is incomplete. Qyroven's timestamped label provider records the two next-day accesses and rejects future access. Hùng's explicit `arrive` events are fed in that same chronological order. Both use Adam at learning rate 0.001, frozen Source references and epsilon 0.001. The Qyroven head is width 64; Hùng's calendar hidden width is 8. The Qyroven GRU encoder state is copied exactly into Hùng's encoder before either runner begins.

## Observations

| Check | Observed result | Limit |
| --- | --- | --- |
| Initial shared encoder | Maximum parameter difference `0.0`. | Forecast heads and their initial weights are different. |
| First forecast | Maximum absolute difference `0.2534717321395874` normalized units. | This is a deliberately unmatched head comparison, not an allowed numerical tolerance verdict. |
| One complete-label update | Maximum encoder parameter difference after update `0.001999996602535248`. | Different forward heads and update implementations prevent an attribution to one cause. |
| Chronological event order | Both normalize to `forecast, score, update, forecast, unscored, decision, fork`. Qyroven logs three candidate updates; Hùng logs one aggregate update event. | A two-origin synthetic order check, not a common real-input trajectory or checkpoint-resume comparison. |
| Low-information block | Both keep lambda 0.1 with only one complete day and Bmin 2. | The high-delta keep fixture does not exercise the known bootstrap convention discrepancy; the [varying-day audit](hung-q-parity-20261027-v1.md) does. |

The trace confirms a shared causal event skeleton for this fixture and independently shows that identical GRU encoder state does **not** produce matched forecasts with the executed heads. It does not establish prediction, gradient, optimizer, RNG, controller or checkpoint parity on a real Development input. A non-author reviewer still needs to select a correctness-based head and bootstrap/quantile contract, then request a common pinned real-input event trace and declared tolerance. Historical executions retain their original architecture and identity.

## Reproduce and checks

From the repository root, with the byte-pinned Qyroven commit extracted at an unused path **inside** this repository:

```powershell
python -m tools.hung_q_common_trace --qyroven-root .cache/parity-q-20261027-v1 --output-dir .cache/hung-q-common-trace-output-NEW
```

The output directory must be new; the tool refuses to overwrite it or read a Qyroven extraction outside the repository. It writes Qyroven's committed tick files and one `result.json`; it does not train a Development job, open Final/test data or contact a provider. This execution used `.cache/hung-q-common-trace-output-20261028-v3`, and its `result.json` was copied byte-for-byte to the tracked JSON evidence. A prior trial output and its script remain preserved in ignored `.cache`.

Checks: pinned three Qyroven source files matched the cited Git commit bytes; tool self-assertions for normalized chronology and the keep decision passed; `ruff check tools/hung_q_common_trace.py`, `ruff format --check tools/hung_q_common_trace.py`, `python -m py_compile tools/hung_q_common_trace.py` and `git diff --check` passed. `python -m ruff` was unavailable in Python 3.13, so the repository's `.cache/local-tools/bin/ruff.exe` was used. No independent reviewer disposition or full-suite result is claimed by this bounded report.
