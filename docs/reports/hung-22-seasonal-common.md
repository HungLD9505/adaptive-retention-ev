# Proposed Seasonal Naive in Hung's common Development replay

This tranche integrates the separate draft [PR #45](https://github.com/HungLD9505/adaptive-retention-ev/pull/45) proposal into the single-policy replay introduced by the Target-only and Frozen Source tranches. It is based on final [PR #59](https://github.com/HungLD9505/adaptive-retention-ev/pull/59) head `4453944`. Report 1 requires a Seasonal Naive comparator and a declared fallback when history is insufficient; it does not approve one particular fallback. This branch does not claim approval, real-data reproduction of #45, or Final evaluation.

## Exact proposed rule

At a created daily origin, repeat the 24 scaled load values from the immediately preceding 24-hour history, hour by hour. For any masked hour, use the **last observed load value within that same 24-hour history**. If every history hour is missing, follow the authenticated schedule's `skipped_all_missing_history` event and issue no forecast. Masked filler is never treated as an observed zero. No target or future label participates in issuance. This is PR #45's proposed `previous_day_24h_last_observed_fallback`; changing it requires separate Development review.

The common `replay-development --method seasonal_naive` path requires an authenticated Development input manifest, entity, scale and daily schedule. It rejects Source, initial model and Source-input arguments. One CPU policy issues forecasts; it has no trainable model, optimizer, candidate forks, audit, Source training or online update. Its cost record reports one forecasting-policy call per created origin, zero model tensor bytes and update steps, plus fallback hours and elapsed inference time. This keeps its budget separate from the three-candidate controller methods.

Every issued forecast and its fallback count are appended to the create-only journal with a state checkpoint **before** the matching label record is read. Scoring requires a complete arrived 24-hour label through the shared replay. The final state, journal and Development input are checked together; interrupted and completed split resume copy and authenticate the prior issued journal into a fresh output. The manifest binds input, code, policy, coverage, original-unit metrics, cost and checkpoint hashes. Existing run directories are never overwritten.

## Verification and remaining gates

Fixture tests cover the masked-hour fallback, all-missing rejection, source/checkpoint rejection, pre-label durable issuance, journal/fallback tamper detection, original-unit scoring, cost accounting and split-resume equivalence. These are implementation tests, not observed dataset performance. PR #45's earlier 7-day two-entity CPU Development observations remain historical evidence under their own code/input identities; this tranche has not rerun those values or expanded the 7/14/28-day cohort.

Before integration, an independent reviewer must approve the fallback definition and verify the full #22 comparator coverage, matched origins, compute capacity and Development evidence. Final stays untouched.
