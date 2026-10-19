# Entity split and prefix scaler — implementation proposal

Issue [#18](https://github.com/HungLD9505/adaptive-retention-ev/issues/18), fixture-only slice. These algorithms are **proposed for peer review**, not an accepted experimental protocol or official dataset partition. Report 1 §7 remains authoritative. The user authorized this slice while the contract and producer PRs await review.

## References and implementation boundary

The implementation follows [Input Contract at c406ae0](https://github.com/HungLD9505/adaptive-retention-ev/blob/c406ae07606ca48859cf93f8b24dfffab79c7803/docs/data/INPUT_CONTRACT.md), SHA-256 `b10178d106713670e7ba7f884dd640559ce1788b3c792447843300457df63adf`, and Research Flow §9. It introduces explicit choices that the contract deliberately left open. Reconcile them with reviews of PR #30 before official use.

`ev_inputs/splits.py` and `ev_inputs/scaling.py` use only the standard library and independent fixtures. They do not import unmerged PR #31 or producer code. The eventual loader must join these components and validate producer profiles, entity membership and budgets. No real data was read, split manifest produced, scaler fitted to a real entity, cohort accepted or artifact handed to #19 in this slice.

## 1. Source / Development / Final split

Policy: `entity-sha256-threshold-v1`.

For each preserved string identity `(dataset_id, city_id, entity_id)` and **explicit recorded salt**, encode a JSON array:

```text
[policy_id, dataset_id, city_id, entity_id, salt]
```

Use UTF-8, `ensure_ascii=False`, separators `(',', ':')`, without whitespace or Unicode normalization. Hash the bytes with SHA-256 and interpret the digest as an unsigned big-endian integer `H`. With `M=2^256`:

| Condition | Role | Use |
| --- | --- | --- |
| `5H < 3M` | source | Pretrain, using pre-deployment history only |
| `3M <= 5H < 4M` | development | Choose and lock design/settings |
| Otherwise | final | Evaluate the locked method; no design tuning |

These thresholds implement **expected 60/20/20 proportions**, not exact quotas in each finite city. Small cohorts may have an empty role. Do not silently reroll the salt or move entities to improve metrics or force counts; flag the cohort for review. Role assignment does not read energy, missingness, full-period totals, target outcomes or other entities. Adding another ID does not move existing IDs. Keep role assignment separate from later eligibility checks.

CHARGED is partitioned within each city namespace, without pooling cities or UrbanEV. Always preserve leading zeros: `01` and `1` are distinct IDs. Identical numeric IDs across cities/datasets are not a physical crosswalk. A single entity has exactly one role, shared across budgets, seeds, methods and the replay. Lock and record the salt before final evaluation; do not search for a favorable split. The fixture salt `review-v1` is **not** a selected production salt.

**Physical overlap limitation:** identifier separation is not proof of distinct real locations. UrbanEV has duplicate/co-located coordinates; CHARGED SZH may overlap UrbanEV. This slice does not invent a grouping or geographic split. Before official cohorts, report co-location across roles and obtain an explicit decision about any stronger unseen-location claim. Keep SZH separate in analysis; do not claim independent external validation.

## 2. Permitted scaler population

Policy: `entity-prefix-p95-linear-v1`. Fit **one scalar per entity and allowed fit scope**, not one pooled value using source plus held-out entities.

| Entity role | Proposed fit population | Frozen when? |
| --- | --- | --- |
| Source | Valid available hourly kWh in explicitly configured source history, ending before deployment | Before source training |
| Development/final target | Its own exact 7-, 14- or 28-day initial prefix ending at deployment | At initialization for that budget |

The target's scalar may differ by budget because the permitted history differs. Within one entity/budget, use the same scalar for all compared methods, candidates, frozen reference and trainable encoder, and all replay days. No later stream refit. Source pretraining uses source-entity scalars; target adaptation/reference evaluation uses the target scalar for both encoders. This is a proposed normalization choice to review on development, not a claim that it improves transfer.

`target_prefix_start(deployment, history_days)` accepts integer budgets 7/14/28 only. Reference dates remain UrbanEV 2022-12-01 and CHARGED 2023-07-01. No default dates are hardcoded in the helper. Arithmetic uses the producer clock: CHARGED days are nominal labels, without an invented DST interpretation.

For each supplied hourly bin, require its start `s` inside `[start, cutoff)` and explicit availability `a <= cutoff`. Bins/bounds must be whole hours; the caller must supply a validated bin-start clock profile. The proposed conservative availability rule requires `a >= s+1h`: no complete-hour energy before its exclusive end. This is a replay convention, **not a verified arrival fact**; later actual arrival delays remain configurable by the caller. No helper infers availability from a filename or mere presence in a release.

Only `file_valid=True`, finite nonnegative available energy enters fitting. True zero is included. Invalid and unavailable values are excluded, never replaced with zero. A value marked valid/available but malformed raises an error. Duplicate prefix bins and mixed aware/naive clocks fail. Outside-prefix energy is ignored. Gaps remain gaps; this is not a continuity validator or model-window eligibility test.

The API takes one identity and an iterable of that entity's rows. The future loader must verify row ownership, profile/offset consistency, source role and deployment cutoff, exact target prefix, and producer identity. These are not guaranteed by the low-level iterable interface. Do not pass a multi-entity population under one name.

## 3. Exact p95 definition and edge cases

Sort the `n` permitted energies as `x[0], ..., x[n-1]`. For `n >= 1`:

$$
r=0.95(n-1),\quad j=\lfloor r\rfloor,\quad w=r-j,
$$

$$
p_{95}=(1-w)x_j+w x_{\min(j+1,n-1)}.
$$

This linear interpolation is fully specified; no library-dependent default quantile is used. Arithmetic uses Python float64. For `[0, 10, 20]` kWh, `r=1.9`, so p95 is **19 kWh**. Both X and Y use `energy_scaled = energy_kwh / energy_scale`; evaluation returns to kWh by multiplying by the same scale. No clipping to `[0,1]`; 38 kWh becomes 2 with a 19 kWh scale. PR #31 handles conversion to float32 feature values.

| Prefix condition | Proposed behavior | Reason / limit |
| --- | --- | --- |
| Positive p95 | Scale = p95, even if below 1 kWh | Do not silently clamp a positive quantile |
| p95 = 0 | Scale = **1 kWh**, record `zero-p95-unit-kwh` | Avoid division by zero without inventing energy or discarding zeros |
| No valid available values | Fail with an undefined-scale error | Missing data is not an all-zero prefix |

A zero p95 does **not** imply all energies are zero: `[0 repeated 99 times, 10]` also has p95 zero. The unit fallback retains that activity, possibly producing large normalized values. This is an engineering proposal, not a scientific necessity; review its effect on development before locking it. Do not change the rule using final results. No automatic fallback for an empty prefix and no automatic site exclusion is introduced. The eventual runner must record that unresolved eligibility/fitting failure rather than silently dropping a target after inspecting its future.

## 4. Provenance and integration gate

`FittedScale` stores policy ID, entity identity, fit bounds, valid/zero counts, p95, actual scale, fallback and a SHA-256 of policy/identity/bounds plus sorted **included** `(bin, availability, energy)` rows. This digest identifies the fitted population; it is not a hash of the full producer file, its excluded rows, or a proof of upstream causality.

The eventual input manifest must additionally record salt/split policy and realized counts, source input/run fingerprints, clock and availability profiles, source/target role and budget, code revision, runtime, run ID, output identities and acceptance scope. The helpers do not write manifests or overwrite outputs. Scaler record fields are not extra model features.

Review gates before official artifacts:

- Accept approximate hash allocation, salt policy and co-location claim limits; inspect realized per-city roles without choosing by final outcomes.
- Accept per-entity source versus per-budget target fitting, linear p95, zero-p95 fallback and undefined empty-prefix behavior.
- Reconcile PR #30/#31 and reviewed hourly producer profiles; define actual input-run availability and source-history bounds explicitly.
- Implement window/label separation and loader tests, then report real eligibility counts and failures. Preserve all Report 1 requirements and report any feasibility risk instead of silently reducing them.

UrbanEV stays primary; all six CHARGED cities remain supplementary with SZH analyzed separately. File-valid data does not establish strict-online readiness. This slice does not undo publisher preprocessing or certify leakage-free research results.
