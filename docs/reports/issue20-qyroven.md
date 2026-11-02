# Issue #20 — Qyroven confidence-controller handoff

Date: 2026-10-25. Status: implementation/fixture verification ready; peer approval,
Development configuration selection and integration acceptance pending. Issue #20
remains open. No merge or main promotion is authorized by this report.

## Delivered

Independently authored from dev `7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c`,
without reading/copying Hung's controller implementation. This branch does not
cherry-pick #19 and does not duplicate its model code.

- `ev_control/confidence.py`: three-level paired daily MAE comparison, Bmin gate,
  percentile moving-block lower bound, explicit two-challenger correction, strict
  threshold/tie rule, deterministic local RNG and decision audit metadata.
- [Controller contract](../data/CONTROLLER_CONTRACT.md): fields/units, clock and
  availability rules, bootstrap formulas/profile, example values and #21 boundary.
- `tests/test_confidence_controller.py`: 19 offline tests, including an independently
  enumerated nonconstant bootstrap distribution with expected LCB=1.2, strict
  equality/keep, Bmin, both challengers, lambda=0, scale/lineage validation, pending
  value mutation invariance, naive clocks and global-RNG isolation.
- `tools/controller_smoke.py`: six predeclared synthetic decisions, new output
  directory only, code/config/module identities and environment/runtime evidence.

## Actual verification

Run `issue20-fixture-20261025-qyroven-v1` executed at clean code commit
`b485011110dfb62fcc63224f49753685f3431c10`, Python 3.12.13 on macOS arm64.
Runtime: 0.020661875 seconds. Config SHA-256:
`74d7816f2e0538d8aed13c20ed5e47079926b6620b3f035cc01fd04468a7cd41`.

The complete small [fixture evidence](issue20-qyroven-evidence.json) is committed
for review; original ignored run path is
`runs/issue20-fixture-20261025-qyroven-v1/evidence.json`. Its SHA-256 is
`3324b2f4c60a53ffddfb0d1eb51a96a169a95ed8c90df577a1ef6d5b92fb03f9`.
No large artifact/Drive upload is needed for this fixture-only helper.

| Synthetic case | Complete days | Active → selected | Outcome |
|---|---:|---|---|
| Consistently better high level | 14 | 0.01 → 0.1 | Switch |
| Zero active, high better | 14 | 0 → 0.1 | Switch |
| Zero challenger better | 14 | 0.1 → 0 | Switch |
| Equal errors | 14 | 0.01 → 0.01 | Keep |
| Below Bmin=7 | 6 | 0.01 → 0.01 | Keep, insufficient evidence |
| All missing | 0 | 0.01 → 0.01 | Keep, no bootstrap |

Commands actually run before the code commit:

```sh
python -m tools.sources list
python -m unittest discover -s tests -q
python -m ruff check .
python -m ruff format --check .
git diff --check
```

All succeeded: **138 tests (119 existing + 19 controller)**. Negative-path fixtures
intentionally print missing/hash/QC diagnostics; the unittest run exits 0. No raw
datasets, Torch import, GPU or network are needed for these tests. The catalog
listing is not a fresh raw-archive checksum verification.

## Review decisions and limits

The supplied 14-day/0.01/0.1/Bmin7/alpha0.05/L3/R2000/seed42 configuration is an
**unvalidated example**, not the locked research configuration. The implementation
makes the following choices explicit for peer review and Development assessment:

1. Percentile lower quantile with alpha/2 for two challengers within one boundary.
   This does not control repeated tests across future boundaries or establish exact
   finite-sample coverage under nonstationarity.
2. Moving blocks on valid-day ordinal indices: missing calendar days are removed
   before resampling, so a segment may span a gap. Decision evidence records gaps,
   coverage and used dates. It is not a calendar-gap-preserving bootstrap.
3. Supported configuration domain `1 <= L < Bmin <= block_days`, with at least two
   resamples. This is an implementation-domain constraint, not a Report 1 constant.
4. Midnight fixed-offset or naive clocks and an exact boundary snapshot. Late
   decisions/offset changes fail. Caller-supplied score and availability provenance
   remain a runner obligation; helper validation is not upstream strict-online proof.

No real-data controller replay, three-candidate training, Final access, hyperparameter
selection, confidence calibration or effectiveness claim occurred. #19's two-lambda,
seven-day fixed-checkpoint smoke does **not** satisfy a three-candidate 14-day online
controller experiment and is not reused as one.

## Handoff to #21

#21 must integrate reviewed #19/#20 interfaces on a separate branch, bind each score
to saved predictions and a fixed scale, process arrived full labels before boundary
selection, preserve identical candidate starts/budgets/paired randomness and carry
the selected trained model/optimizer/RNG state. Exercise real Development data across
at least one block boundary on Colab, and test checkpoint/resume plus causal forecast
immutability. Review this bootstrap/configuration profile before official experiments;
lock selected values on Development before touching Final. Preserve the known
UrbanEV/CHARGED clock, upstream-processing and physical-location split limitations.
