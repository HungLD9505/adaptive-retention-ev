# Controller identity and result-scope audit — 12 November 2026

## Verified conclusion

The 18/21 result is real, but it belongs to adaptive **forecast fusion of two
retention experts**, not to the confidence-gated lambda selector. The screenshot
of v3 Table 3 shows another experiment: a common-bank retention-selector study
on twelve UrbanEV Development entities. Its values are correct for that study.
It does not contain the 810-unit historical mixture result.

It is also incorrect to say that a retention selector never beats Fixed. The
four-target Later comparison gives discrete selection MAE 4.798258890 versus
calibrated Fixed 4.803054026, and the twelve-target common-bank study favors
confidence selection over its calibrated Fixed comparator at 28 days. Neither
observation establishes the historical 18/21 claim for a lambda controller.

## End-to-end method/result crosswalk

| Method | What changes online | Cohort/window | Verified comparison |
| --- | --- | --- | --- |
| Original confidence-gated retention | Selected lambda and subsequently forked training state; 14-day block decisions | Historical 90 entities, 7 namespaces, 3 histories, 3 seeds | Below single Fixed lambda 1 in 9/21 group means; above it in 12/21 |
| Common-bank confidence selector (v3 Table 3) | Output choice among independent constant-lambda trajectories, with a seven-day confidence gate | 12 additional UrbanEV Development entities, 7/14/28-day histories | Above calibrated Fixed at 7/14 days; below it at 28 days |
| Discrete retention comparator in the four-target study | Discrete retention-selection policy | Four-target registered Later window | 4.798258890 vs calibrated Fixed 4.803054026 kWh, a reduction of about 0.100% |
| Immediate continuous-lambda controller | Lambda through an Adam hypergradient | Four-target registered Later window | 4.806223253 vs Fixed 4.803054026 kWh; worse |
| Immediate/persistent lambda follow-up | Scalar lambda, under their separately locked update policies | Four-target Kaggle Calibration window | Immediate 5.318961684 and persistent 5.331587155 vs Fixed 5.331705633. These are favorable Calibration means. Persistent fails its required gain gate, so no Later matrix follows. |
| Static stable/fast mixture | No online weight update; weight 0.4307815378871372 | Historical 810-unit cohort | Below single Fixed in 18/21 groups |
| Adaptive stable/fast mixture | Mixture weight w through exponential-loss plus Fixed-share updates | Same historical 810 units and same expert forecasts | Below single Fixed in 18/21 groups; below matched static mixing in 12/21 and above it in 9/21 |

These are numerical comparisons of matched recorded means, not significance
claims. Calibration, Later, Development and historical cohorts remain separate.
The single Fixed comparator and the fixed-weight mixture are different models.
At 28-day Development history, calibrated Fixed selected lambda zero; a
retrospectively selected lambda-one constant scores 3.292501 kWh, below the gate
at 3.313967. That diagnostic uses evaluated labels and is not an admissible
replacement for the calibration-selected comparator.

All eighteen CHARGED namespace/history groups favor adaptive fusion over single
Fixed. All three UrbanEV groups favor single Fixed. The full-scope 18/21 count
therefore does not conflict with adverse UrbanEV-only results.

The newer mixture was also evaluated on the twelve Development entities at
14-day history: adaptive mixture 3.291048173, static mixture 3.303020734 and single
Fixed 3.266999927 kWh. Thus inserting the newer mixture into Table 3 would not
make it win at fourteen days. Its 7/28-day cells on these twelve entities must not
be invented from the different historical cohort.

## Code-to-artifact trace

1. `tools/issue99_history_study.py` creates separate lambda 0/0.1/1 trajectories,
   selects Fixed using calibration, and calls the same policy replay with its
   confidence gate enabled/disabled. These are v3 Table 3's `fixed_bank`,
   `mean_only` and `confidence_gate` records.
2. `ev_runner/engine.py::boundary` implements the original historical selector's
   reforking semantics. Its old forecast stream is not the independently trained
   common bank used in Table 3.
3. `tools/issue99_full_scope.py` authenticates historical Fixed/selector streams,
   trains or authenticates a Fast-only trajectory, then passes the same paired
   expert forecasts into static and adaptive `forecast_mixture` calls.
4. `ev_control/expert_mix.py::update_stable_weight` accepts weight, expert losses,
   eta and share. It updates w, not lambda. Its code hash matches the recorded
   execution lock. This branch does not invoke the bootstrap/LCB gate.
5. `forecast_mixture` consumes only complete earlier feedback in availability
   order and origin order, then mixes the current saved forecasts. Both expert
   coefficients remain fixed: stable lambda 1, fast lambda 0. Both experts were
   initialized from Source; lambda zero is not a target-only model.
6. The identity audit freshly reconstructs historical station-first group means
   from all 810 unit rows, the Table 3 means from the 612-row ledger, reads the registered four-target
   Later summary and recomputes the separate persistent Calibration matrix. Source hashes are
   in [identity-audit.json](identity-audit.json).
7. A fresh [saved-mixture readback](saved-mixture-readback.json) checks all 810 cell
   hashes against the existing private readback manifest and independently
   reproduces weights, forecasts/errors for adaptive, static and Fast-only arms:
   67,293 scored vectors per arm and 66,492 consumed feedback events. Nine null
   units remain explicit. It also independently checks the reported parameter
   counts. No expert is retrained.

This is saved-output verification and arithmetic, not a new prepared-label audit,
fresh upstream raw-data acquisition, full bootstrap-decision reconstruction or
prospective evaluation. The ten existing expert-mixture fixtures passed again.
No new offline fixture success is treated as effectiveness evidence.

## Alignment with the original teacher proposal

The proposal has four elements: transferred GRU, multiple retention levels,
performance-and-confidence-driven retention adjustment, and comparison with
Fixed/ordinary online selection. The original selector and common-bank study
test those mechanisms, with conditional rather than universal favorable results.

The newer 18/21 system reuses transferred GRUs and two retention settings, but
changes the adaptation mechanism to a prediction mixture with different update
memories. It has no bootstrap/LCB acceptance test in its weight update. Its
normalized posterior is not a calibrated confidence interval for future benefit.
Mixing predictions at weight w is not equivalent to training one GRU at lambda w.

**Interpretation:** the newer system can be described as adaptive weighting over
source-retaining and recent-adaptation experts. It cannot be presented as proof
that the originally proposed confidence-gated lambda controller wins 18/21.
The static mixture's own 18/21 count further prevents assigning the entire family
gain to the adaptive update.

## Manuscript presentation defect

V3 accurately states many individual results but fails to make the experiment
identities prominent enough: Table 3's generic `Fixed` and `Confidence gate`
labels stand beside the headline discussion of a different, newer controller;
the complete new 21-group table is in an appendix. This makes a reader reasonably
expect those Table 3 rows to be the newer system.

Required reporting corrections are to identify every controller by its mechanism
and scope, distinguish single Fixed from static fusion, and place the main new
comparison prominently if fusion remains the paper's main method. Preserve the
positive discrete-Later/28-day results and the adverse UrbanEV results together.
Do not replace old-study cells with numbers from another cohort, retrofit an LCB
into the description of an executed loss-only update, or call all favorable
comparisons one successful controller.

This audit does not choose a new scientific method or retrain a controller. The
original confidence-based proposal and the newer fusion extension must be
explicitly reconciled before presenting them as one research contribution.

## Referenced chats and current source check

All four user-referenced chats were read through the thread tool. In
[Review AIP491 meeting script](thread://01a1c480-33c8-76d2-9b92-bddfa17f749f?hostId=local),
turn `01a1c95d-8c31-76c1-8e89-9901ed6c75fd` explicitly attributes 18/21 to two-GRU
mixing and 12/21 to its adaptive-vs-static increment. The older
[project explanation](thread://01a13446-0da0-7fd1-b984-e655242b5497?hostId=local),
[Final recovery](thread://01a18179-3eaa-7121-8ed0-ce222a597fa7?hostId=local), and
[historical synthesis](thread://01a1858d-d1a1-7e01-81a1-aba0326d8377?hostId=local)
describe earlier implementation/execution states. Their completion counts are
not evidence of the newer controller's mechanism or superiority. This audit does
not claim to reread every historical turn.

On 12 November, PR #112 still pointed to `8cf00ee3ca48f65064209943d2b9ce67476ed44c`
and PR #113 to `a0550f3d5cb9df2690e48204cafb7458b95c9d25`; no newer successful
lambda-only experiment was found on those heads. That is not a claim about
unpublished work. No PR, issue, branch, dataset or historical report is merged,
closed, overwritten or relabelled by this audit.
