# Issue #99 method review checkpoint

This is an implementation checkpoint for review, not a completed calibration or
comparison. The historical Fixed sweep and frozen Final evidence are unchanged.

## Implemented

- `tools/issue99_local_audit.py` verifies the input ZIP, both relevant manifests,
  all five data files per budget, ordered Source training rows, Source10 ZIPs,
  strict checkpoint loading, optimizer state, latent scales and historical code.
- `ev_control/hypergradient.py` computes a one-step validation derivative through
  the current Adam moments, bias correction, epsilon, coupled weight decay and
  AMSGrad setting. The virtual step leaves real model/optimizer state untouched.
  A subnormal variance clamp exposes the finite limiting derivative at an exact
  zero second moment; this is a numerical implementation choice for review.
- `ev_control/continuous.py` builds older A and newer untrained V only from
  complete arrived labels. Its outer objective is forecast MAE alone. The Source
  encoder and source-derived scales stay fixed. The coefficient is projected to
  `[0, U]`; no bootstrap guarantee is inherited.
- `ev_runner/continuous.py` stores one real branch, its pending forecasts, arrived
  A/V eligibility, coefficient and counters at every committed day. It scores
  saved pre-label forecasts, makes an optional meta-decision, trains the real
  branch once per newly complete day, and only then issues the next forecast.
  `ev_runner/continuous_run.py` starts each invocation from the same verified
  seed-specific Source10 with a fresh Adam target optimizer. `frozen_lambda=true`
  gives a real-valued Fixed path in this versioned runner.

## Review and execution boundary

The finite-difference fixtures cover float64 toy Adam at zero and positive
coefficients. Synthetic replay fixtures cover A/V arrival, consumed-label
exclusion, interrupted/resumed state and predictions, and independent original-
unit MAE recomputation. A bounded three-tick CPU run exercised the real 14-day
input and checkpoint, including resume and one finite controller decision.

The draft protocol in `configs/issue99-protocol-draft-v0.json` deliberately has
null calibration/evaluation origins, domain, BO settings, controller budget and
T4 measurements. The new CLI rejects a scored phase without a matching reviewed
protocol file and exact objective-origin list. Pilot output has no scored
objective. The audit PASS permits a Kaggle T4 pilot, but this PR does not upload
artifacts or initiate it.

## Required next increment

1. Review the A/V reuse policy, one-batch virtual Adam semantics, zero-variance
   derivative, chronological objective boundary and cost matching.
2. Run a measured Kaggle T4 pilot after verifying code/input/Source SHA-256 in
   that runtime; register finite numerical protocol values and obtain peer review.
3. Implement the bounded BO plus sensitivity trial dispatcher and diagnostic
   ledger, then run only the reviewed calibration search.
4. Lock Fixed and controller settings; run the paired matrix and independent
   metric/artifact audit. Keep all new Development results exploratory unless a
   genuinely unused evaluation subset is established.

No performance comparison, favorable regime or paper result is claimed here.
