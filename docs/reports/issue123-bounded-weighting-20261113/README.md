# One bounded expert-weighting attempt — stopping decision

Issue #123; depends on #122, #120, #118 and #116. **Completed outcome: stop.**
The best new weighting candidate improves slightly over legacy adaptive/static
on the old Development sample, but does not beat single Fixed. The registered
proceed gate fails. No new cohort, no new target GRU training and no repeated
search follow this outcome. The current model/recipe is not replaced.

## Registered scope

Commit `f165552` records
[development-registration-v1.json](../../../configs/issue123/development-registration-v1.json)
before any of the four candidate outputs were inspected. Protocol SHA-256:
`383b5794ab9a62083eb06c6bd5c95f2a8ea7681813c9038071bccef3699668f3`.
The same 12 previously exposed UrbanEV Development IDs and seeds 42/43/44
supply 36 existing stable/fast expert pairs, a fourteen-day prefix and ninety
scheduled origins. Source models, expert training, forecasts, labels and scales
remain unchanged. Replaying four candidates gives 144 candidate cells, not
144 newly trained GRUs.

Selection is the minimum equal-seed/equal-ID MAE across exactly four candidates.
Proceed only if that candidate is strictly lower than **Fixed, static and legacy
adaptive** in this Development aggregate. The objective, tie order, candidate
set and stop rule were recorded before execution. Oracles do not enter selection.
Issue119's 46 IDs are not used to choose or assess these new candidates.

## Methods and formula boundaries

- **No share:** legacy eta 0.1, alpha 0; same initial stable weight
  0.4307815378871372. Isolates removal of sharing.
- **Decreasing share:** eta 0.1, alpha at arrived-feedback event k is 1/(k+1),
  starting k=1. This is a declared engineering ablation; no claim of optimality.
- **AdaHedge:** uniform initial prior, eta=ln(2)/Delta, with eta=infinity while
  the cumulative mixability gap Delta is zero. Recompute exponential weights
  from cumulative arrived expert losses as eta changes; do not just change eta
  in the old multiplicative update. Delta accumulates the difference between
  virtual Hedge loss and mix loss. Infinity uses exact uniform leader ties.
- **FTL:** uniform on experts with the lowest cumulative arrived loss; permits
  pure Fixed/Fast forecasts, with 50/50 ties.

AdaHedge follows equations (8)-(9) and Figure 1 of
[de Rooij et al., JMLR 2014](https://jmlr.org/papers/v15/rooij14a.html).
FTL is the infinite-learning-rate reference from the same paper. The replay
processes only earlier forecast origins whose complete labels have arrived,
in availability/origin order. AdaHedge's gap uses a virtual update in that
arrival sequence. This adapter does not inherit an unmodified delay-free
regret guarantee, and it is not a new lambda or GRU-cell mechanism.

Controls are single Fixed, Fast, the original calibrated static blend, 50/50,
legacy adaptive and loss-free sharing. Original priors are retained for the
fixed-rate ablations; AdaHedge/FTL use their uniform-prior definitions. Thus the
candidate comparison is not an isolated test of eta alone.

## Results

Lower MAE is better. These are old Development outcomes, not a new confirmation.

| Method | Equal-ID/seed MAE (kWh) |
|---|---:|
| Single Fixed lambda 1 | **3.267000** |
| AdaHedge | 3.284880 |
| Decreasing share | 3.290692 |
| FTL endpoint selection | 3.290727 |
| Legacy adaptive | 3.291048 |
| Equal 50/50 | 3.291055 |
| Loss-free sharing | 3.291239 |
| No share | 3.302131 |
| Original static fusion | 3.303021 |
| Fast only | 3.419880 |

AdaHedge reduces MAE by **0.1874% versus legacy adaptive** and **0.5492% versus
static**, but increases it by **0.5473% versus Fixed**. With a posthoc 1e-6 kWh
absolute tolerance, it improves on Fixed at 1/12 IDs, static at 8/12 and legacy
at 5/12. The tolerance is descriptive, not a prespecified practical threshold.
Full precision and every ID/seed/method remain in `development-mae.csv` and
`entity-mae.csv`. The registered gate is false; no favorable subset or new
parameter search replaces it.

The hindsight per-ID optimal static weight yields mean MAE 3.255453, while
choosing the lower-error expert separately each day yields 3.090950. Both use
future outcomes, so neither is deployable. The daily expert oracle benchmarks
an endpoint selector, not the best possible convex mixture. These diagnostics
show some forecast complementarity without demonstrating that past errors can
predict its future benefit. Removing the 50/50 attraction alone worsens the
legacy score; the initial structural suspicion is not sufficient to explain or
fix the performance gap.

## Verification

`source-readback.json` records fresh authentication of the original expert
forecasts and complete arrived labels: 108 fast calibration/evaluation runs,
4,734 rolling updates, 2,628 original feedback updates and 10,656 vectors across
four original arms. The 36 evaluation cells match the originally recorded source
SHA-256. Source readback is separate from the new controller calculation.

`independent-verification.json` reproduces all 144 new candidate cells using
**50-digit Decimal arithmetic** and an independent cumulative mix-loss
implementation. Maximum weight difference is about 1.18e-13; maximum forecast
difference is about 7.20e-14 kWh. It checks every daily error, source-vector
identity, old control forecast, equal-ID aggregation, selected candidate and
stop rule. Six offline regression tests cover paper arithmetic, infinite-rate
leader changes, scale invariance, endpoint decisions and delayed feedback.

## Review follow-up and limits

The only new non-author repository issue comment found for 13 November was
[HungLD9505's #120 review](https://github.com/HungLD9505/adaptive-retention-ev/pull/120#issuecomment-6848388835).
PR #122 addresses both requests: complete original-ref JSONL audit and explicit
qualification of four numerical-scale ID wins. #116/#118 had no comments when
checked; no peer approval is inferred. The first expanded local audit attempt
and conservative additional-exposure exclusions remain documented in #122.

This attempt improves a candidate's old Development mean by a small amount;
it does not improve or replace the previously locked seven-namespace
confirmation. It does not establish adaptive superiority, confidence-controlled
retention, an optimal backbone, new-city performance or an equal-compute result.
The broader source-transfer evidence and historical comparisons remain intact.
The defensible conclusion remains useful source transfer and complementary
forecasts with a small, inconsistent online-weighting increment.

## Reproduce

Use the registered implementation at `f165552` and the identified external
Development results/verification receipt. The evaluator refuses changed source
or code hashes and new output destinations refuse overwrite.

```sh
python -m tools.weighting_development \
  --protocol configs/issue123/development-registration-v1.json \
  --output /new/external/path/development
python -m tools.weighting_verify \
  --protocol configs/issue123/development-registration-v1.json \
  --output /new/external/path/development \
  --receipt /new/external/path/verification.json
```

The verifier is supplied by the follow-up PR head; execution code remains the
registered bytes. Large cell vectors, complete logs and all attempt receipts
remain under external `runs/issue123-bounded-weighting-20261113-v1`. The raw
archives are not freshly checked or modified. No merge or main update occurs.

## Review: optimization-safe verifier guards

[HungLD9505's final review](https://github.com/HungLD9505/adaptive-retention-ev/pull/124#pullrequestreview-5889414743) supports the stopping conclusion and requests hardening of the independent verifier. Its plain Python assertions disappeared under `python -O`, allowing a corrupted selected method or proceed flag to produce a passing receipt. All such guards now raise explicit exceptions, including source/prior hashes, protocol and cell identities, candidate MAE/aggregates, selection and the proceed gate. A malformed input fails before receipt creation in both interpreter modes.

Four regression tests cover valid receipts in normal/optimized Python and corrupt hashes, protocol identity, cell matrix/identity, candidate MAE, aggregate means, selected method and proceed flag. The pre-fix regression reproduced the bypass. The complete real-data readback was then repeated with `python -O`: the same 36 source and 144 candidate cells reproduce the same stop decision and numerical differences. The refreshed receipt records optimization level 1; prior receipts remain in the external run history and earlier Git commits. Protocol, predictions and result hashes are unchanged. This is verification of existing artifacts, not another candidate experiment.
