# Issue #18 — calendar and historical-row helpers (fixture-only handoff)

## Scope and version pin

This is the second #18 slice: five calendar features and one seven-column historical row, using **independent fixtures only**. No producer data, official model inputs, windows, loader, fitted scaler, entity split, model or runner is used/created. No datasets were downloaded, read or freshly verified in this slice; `tools.sources list` reads catalog metadata only.

The implementation targets schema `ev-input-v1` from [PR #30's contract at commit c406ae07606ca48859cf93f8b24dfffab79c7803](https://github.com/HungLD9505/adaptive-retention-ev/blob/c406ae07606ca48859cf93f8b24dfffab79c7803/docs/data/INPUT_CONTRACT.md).

Exact contract-file SHA-256: `b10178d106713670e7ba7f884dd640559ce1788b3c792447843300457df63adf`. The digest refers to the contract's Git blob bytes (LF), not platform-transformed checkout bytes. The module exposes this pin and ordered feature-name tuples. It does not fetch or silently track a moving PR branch.

PR #30 is still a proposal. Before integrated acceptance, compare the reviewed contract against this pin. If it changes, explicitly reconcile semantics/order and update implementation/fixtures/reference with an explanation; changing the digest alone is not evidence of compatibility. Independent numerical fixtures supplement the pin; no claim is made that these helpers implement all of the contract.

## API and behavior

Implementation: [ev_inputs/features.py](../../ev_inputs/features.py).

```python
from datetime import datetime
from ev_inputs.features import calendar_features, historical_features

stamp = datetime.fromisoformat("2022-11-29T06:00:00+08:00")
calendar = calendar_features(stamp, clock_mode="offset-aware-local")
row = historical_features(
    stamp,
    energy_kwh=10.0,
    file_valid=True,
    energy_available=True,
    energy_scale=20.0,
    clock_mode="offset-aware-local",
)
```

Rounded for display, `calendar` is `(1, 0, 0.7818, 0.6235, 0)` and `row` is `(0.5, 1, 0, 0.7818, 0.6235, 0, 1)`. This is the pinned Tuesday-06:00 mathematical example, not a station observation. Actual calculations are not rounded to four decimals.

- Calendar order: hour sin/cos, weekday sin/cos, weekend; Monday=0, weekend=Saturday/Sunday. History order: scaled energy, those five calendar fields, energy-present mask.
- Returns tuples of Python floats containing float32-representable values. Standard-library `struct` performs IEEE-754 float32 conversion; no NumPy/PyTorch dependency or tensor/batch implementation is introduced. Round-off near mathematical zero is retained; there is no arbitrary clamping.
- The **caller supplies** a finite positive energy scale. The helper only divides; it fits no p95/scaler, chooses no prefix, introduces no fallback and clips neither energy nor values above 1. Nonfinite or float32-overflow results fail.
- Both `file_valid` and `energy_available` must be explicit booleans. True zero with both flags true yields energy/mask `(0,1)`; either flag false yields `(0,0)` and ignores the energy value. Calendar fields remain unchanged.
- If both flags are true but energy is missing, nonfinite, negative or the wrong type, raise a clear error: inconsistent caller input is not silently repaired. A producer-invalid/missing value should arrive with `file_valid=False`; lack of availability with `energy_available=False`.
- `offset-aware-local` requires an offset-bearing whole-hour datetime; `publisher-local-naive` requires an offset-free whole-hour datetime. Unknown modes, mismatched representations, strings or non-hour labels fail. The helper performs no timezone conversion, DST inference or timestamp rounding.

**Clock limitation:** these modes validate representation, not a producer's complete manifest/profile or the correctness of a supplied IANA zone/offset. The future loader must validate those producer assumptions. The helpers extract local calendar fields from the supplied datetime; an aware timestamp is not automatically certified as UrbanEV/Asia-Shanghai.

**Availability limitation:** the caller must derive availability from the later approved chronology. A boolean argument does not prove label arrival or upstream causality. No Y argument, label imputation, forecast schedule or update gate is implemented here.

## Independent fixture checks

[tests/test_input_features.py](../../tests/test_input_features.py) has **12 new test methods**, plus the 9 existing source tests: **21 total passed**, zero failures/errors/skips. Expected numerical examples are explicitly specified rather than derived by calling the same encoding helper.

| Area | Passing fixture evidence |
| --- | --- |
| Schema identity/order | Exact pinned commit/hash, proposed schema ID, five/seven ordered field names |
| Known timestamps | Monday 00:00, Sunday 23:00, documented Tuesday 06:00 |
| Wraparound | 23→00 and Sunday→Monday distances agree with the next adjacent step; year boundary retains correct calendar/weekend |
| Clock handling | +08:00 local midnight stays midnight/Monday; aware/naive mismatches, unknown mode, non-hour and non-datetime inputs fail |
| History rows | Seven values in order; explicit supplied scale; values above 1 are not clipped |
| Missing/zero | Genuine zero has mask 1; missing or unavailable energy has mask 0 and unchanged calendar |
| Unavailable-value isolation | Changing a masked/unavailable energy value cannot alter the output row |
| Invalid caller state | Valid+available missing/negative/NaN/infinite energy fails; text/boolean energy and nonboolean flags fail |
| Scale/precision | Zero/negative/nonfinite/non-numeric scale fails; float32 overflow/scaled infinity fails without a fallback |

These fixtures establish local feature/validation behavior only. They do not establish prefix leakage safety of an unimplemented scaler/window/loader, upstream observation provenance, full-data eligibility or research effectiveness.

## Verification and handoff

Run the standard README checks with Python 3.12:

```sh
python -B -m tools.sources list
python -B -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
git diff --check
```

All local checks passed. The [fixture evidence snapshot](input-features-evidence.json) records actual test count/results/runtime, Python/platform, executed code commit, contract pin and module/test-file hashes. Local run: `runs/input-features/issue18-features-v1-20261019.json`; no official data input artifact is claimed. Ubuntu/Windows CI is tracked on the PR. No new dependencies were added.

Review this small helper API and pin reconciliation before later split/scaler work. In particular, the caller-supplied scale and availability flags are not substitutes for the future permitted-prefix/chronology implementation. #16/#17/#30 remain independent review/integration dependencies; #18 stays open. No merge is authorized.
