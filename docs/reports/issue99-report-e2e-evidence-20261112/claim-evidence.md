# Report claim-to-evidence register

This is an explanation companion, not a scientific bibliography or a new experiment. Each prose entry quotes the maintained manuscript and identifies its source set. Full text and SHA-256 identities are in `claim-evidence.json`; `claim-evidence.csv` can be filtered by section. A source link is not proof by itself: fresh numeric checks and artifact readbacks are described in the handoff. Interpretations and verification limits remain explicit.

Coverage: **101 prose entries**, **26 labeled equations/tables/figures**, **71 source files**.

## Abstract

**Status:** verified, inferred. **Claim type:** synthesis.

Empirical summaries are restricted to these executed cohorts. Motivations and research questions are not results; no universal transfer/controller superiority follows.

Manuscript paragraphs: [P001](../../../report/rebuilt-review-20261112/main.tex#L10).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)

## Introduction

**Status:** verified, inferred. **Claim type:** synthesis.

Empirical summaries are restricted to these executed cohorts. Motivations and research questions are not results; no universal transfer/controller superiority follows.

Manuscript paragraphs: [P002](../../../report/rebuilt-review-20261112/main.tex#L15), [P003](../../../report/rebuilt-review-20261112/main.tex#L17), [P004](../../../report/rebuilt-review-20261112/main.tex#L19), [P005](../../../report/rebuilt-review-20261112/main.tex#L21), [P006](../../../report/rebuilt-review-20261112/main.tex#L23), [P007](../../../report/rebuilt-review-20261112/main.tex#L29).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)

## Forecasting backbones

**Status:** verified. **Claim type:** literature_and_implementation.

GRU convention is PyTorch-specific. TimeXer and spatial information sets are distinguished; citations motivate families, not the project ranking.

Manuscript paragraphs: [P008](../../../report/rebuilt-review-20261112/main.tex#L33), [P009](../../../report/rebuilt-review-20261112/main.tex#L35).

Evidence:
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [report/rebuilt-review-20261112/references.bib](../../../report/rebuilt-review-20261112/references.bib)

## Transfer and explicit retention

**Status:** verified. **Claim type:** definition_and_literature.

L2-SP is a parameter-reference precedent. It does not specify our latent penalty, lambda values, or EV effectiveness.

Manuscript paragraphs: [P010](../../../report/rebuilt-review-20261112/main.tex#L38), [P011](../../../report/rebuilt-review-20261112/main.tex#L40).

Evidence:
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [report/rebuilt-review-20261112/references.bib](../../../report/rebuilt-review-20261112/references.bib)

## Adaptive decisions and evidence

**Status:** verified. **Claim type:** definition_and_literature.

Published principles are distinguished from project choices. No performance theorem is transferred to this replay.

Manuscript paragraphs: [P012](../../../report/rebuilt-review-20261112/main.tex#L43), [P013](../../../report/rebuilt-review-20261112/main.tex#L45).

Evidence:
- [ev_control/confidence.py](../../../ev_control/confidence.py)
- [ev_control/hypergradient.py](../../../ev_control/hypergradient.py)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [report/rebuilt-review-20261112/references.bib](../../../report/rebuilt-review-20261112/references.bib)

## Inputs, labels and missingness

**Status:** verified. **Claim type:** implementation.

Prepared feature and eligibility semantics verified in code; upstream raw-data causality is not authenticated here.

Manuscript paragraphs: [P014](../../../report/rebuilt-review-20261112/main.tex#L49), [P015](../../../report/rebuilt-review-20261112/main.tex#L51), [P016](../../../report/rebuilt-review-20261112/main.tex#L53).

Evidence:
- [ev_inputs/features.py](../../../ev_inputs/features.py)
- [ev_inputs/scaling.py](../../../ev_inputs/scaling.py)
- [ev_inputs/windows.py](../../../ev_inputs/windows.py)
- [ev_inputs/splits.py](../../../ev_inputs/splits.py)
- [ev_inputs/loader.py](../../../ev_inputs/loader.py)
- [ev_runner/replay.py](../../../ev_runner/replay.py)
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)

## Causal replay

**Status:** verified. **Claim type:** implementation.

Availability is enforced in replay. This is not physical real-time issuance verification or proof that IDs are distinct physical sites.

Manuscript paragraphs: [P017](../../../report/rebuilt-review-20261112/main.tex#L56), [P018](../../../report/rebuilt-review-20261112/main.tex#L58).

Evidence:
- [ev_inputs/features.py](../../../ev_inputs/features.py)
- [ev_inputs/scaling.py](../../../ev_inputs/scaling.py)
- [ev_inputs/windows.py](../../../ev_inputs/windows.py)
- [ev_inputs/splits.py](../../../ev_inputs/splits.py)
- [ev_inputs/loader.py](../../../ev_inputs/loader.py)
- [ev_runner/replay.py](../../../ev_runner/replay.py)
- [ev_runner/engine.py](../../../ev_runner/engine.py)
- [ev_runner/continuous.py](../../../ev_runner/continuous.py)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [docs/reports/issue99-study-20261110/local-byte-verification.json](../../../docs/reports/issue99-study-20261110/local-byte-verification.json)

## Experimental scopes

**Status:** verified. **Claim type:** recorded_protocol_and_arithmetic.

Counts refer to prepared IDs, examples and recorded scored origins. Namespaces/history groups are not cities or independent replications.

Manuscript paragraphs: [P019](../../../report/rebuilt-review-20261112/main.tex#L74), [P020](../../../report/rebuilt-review-20261112/main.tex#L76), [P021](../../../report/rebuilt-review-20261112/main.tex#L78), [P022](../../../report/rebuilt-review-20261112/main.tex#L80).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [docs/reports/issue99-history-review-20261110/source-record-counts.json](../../../docs/reports/issue99-history-review-20261110/source-record-counts.json)
- [docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json](../../../docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json)

## Architecture and latent state

**Status:** verified. **Claim type:** equation_and_implementation.

Equations match code and parameter counts. Gradient magnitude is not an empirical claim about retained knowledge.

Manuscript paragraphs: [P023](../../../report/rebuilt-review-20261112/main.tex#L86), [P095](../../../report/rebuilt-review-20261112/model-equations.tex#L1), [P096](../../../report/rebuilt-review-20261112/model-equations.tex#L13), [P097](../../../report/rebuilt-review-20261112/model-equations.tex#L15).

Evidence:
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [ev_runner/diagnostics.py](../../../ev_runner/diagnostics.py)
- [report/rebuilt-review-20261112/references.bib](../../../report/rebuilt-review-20261112/references.bib)

## Optimization meaning

**Status:** verified. **Claim type:** equation_and_implementation.

Equations match code and parameter counts. Gradient magnitude is not an empirical claim about retained knowledge.

Manuscript paragraphs: [P024](../../../report/rebuilt-review-20261112/main.tex#L89), [P025](../../../report/rebuilt-review-20261112/main.tex#L91).

Evidence:
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [ev_runner/diagnostics.py](../../../ev_runner/diagnostics.py)
- [report/rebuilt-review-20261112/references.bib](../../../report/rebuilt-review-20261112/references.bib)

## Historical fixed recipes

**Status:** verified. **Claim type:** executed_configuration.

Fixed comparators differ between historical and calibrated-bank studies; lambda zero preserves source initialization.

Manuscript paragraphs: [P026](../../../report/rebuilt-review-20261112/main.tex#L95), [P027](../../../report/rebuilt-review-20261112/main.tex#L97).

Evidence:
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-history-review-20261110/7d-selection-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-selection-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-selection-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-selection-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-selection-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-selection-lock.json)

## Expanded fixed-coefficient diagnostic

**Status:** verified. **Claim type:** measured_calibration.

Best measured candidate only. Domain multipliers, surrogate and acquisition-grid settings are engineering choices; sampled regimes are not continuous thresholds.

Manuscript paragraphs: [P028](../../../report/rebuilt-review-20261112/main.tex#L100), [P029](../../../report/rebuilt-review-20261112/main.tex#L107), [P030](../../../report/rebuilt-review-20261112/main.tex#L109), [P031](../../../report/rebuilt-review-20261112/main.tex#L111), [P032](../../../report/rebuilt-review-20261112/main.tex#L116), [P033](../../../report/rebuilt-review-20261112/main.tex#L123), [P034](../../../report/rebuilt-review-20261112/main.tex#L125).

Evidence:
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [docs/reports/issue99-study-20261110/fixed-regimes.csv](../../../docs/reports/issue99-study-20261110/fixed-regimes.csv)
- [docs/reports/issue99-study-20261110/fixed-diagnostics.csv](../../../docs/reports/issue99-study-20261110/fixed-diagnostics.csv)
- [tools/issue99_study.py](../../../tools/issue99_study.py)

## Confidence-gated block selection

**Status:** verified. **Claim type:** equation_and_executed_configuration.

Formula, shared draws, tie and trained-state continuation match the implementation. No sequential or next-block improvement guarantee.

Manuscript paragraphs: [P035](../../../report/rebuilt-review-20261112/main.tex#L133), [P036](../../../report/rebuilt-review-20261112/main.tex#L135), [P037](../../../report/rebuilt-review-20261112/main.tex#L141), [P038](../../../report/rebuilt-review-20261112/main.tex#L143), [P039](../../../report/rebuilt-review-20261112/main.tex#L145).

Evidence:
- [ev_control/confidence.py](../../../ev_control/confidence.py)
- [ev_runner/engine.py](../../../ev_runner/engine.py)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)

## Common-bank online selection

**Status:** verified. **Claim type:** implementation_and_result.

Output selection from independent trajectories differs from historical reforked model training.

Manuscript paragraphs: [P040](../../../report/rebuilt-review-20261112/main.tex#L148), [P041](../../../report/rebuilt-review-20261112/main.tex#L150).

Evidence:
- [tools/issue99_history_study.py](../../../tools/issue99_history_study.py)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-selection-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-selection-lock.json)

## Continuous validation hypergradient

**Status:** verified. **Claim type:** equation_and_executed_configuration.

One virtual Adam step from a fixed real starting state, not differentiation through the entire online history. U and step-size selection are project choices.

Manuscript paragraphs: [P042](../../../report/rebuilt-review-20261112/main.tex#L153), [P043](../../../report/rebuilt-review-20261112/main.tex#L161), [P044](../../../report/rebuilt-review-20261112/main.tex#L163).

Evidence:
- [ev_control/hypergradient.py](../../../ev_control/hypergradient.py)
- [ev_control/continuous.py](../../../ev_control/continuous.py)
- [ev_runner/continuous.py](../../../ev_runner/continuous.py)
- [docs/reports/issue99-study-20261110/controller-selection.json](../../../docs/reports/issue99-study-20261110/controller-selection.json)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)

## Persistent scalar-only follow-up

**Status:** verified. **Claim type:** executed_followup.

Kaggle-reported saved-run audit and transcribed cells. No fresh local persistent checkpoint readback or Later execution.

Manuscript paragraphs: [P045](../../../report/rebuilt-review-20261112/main.tex#L166), [P046](../../../report/rebuilt-review-20261112/main.tex#L168).

Evidence:
- [docs/reports/issue99-persistent-results-20261111.md](../../../docs/reports/issue99-persistent-results-20261111.md)
- [ev_control/persistent.py](../../../ev_control/persistent.py)
- [ev_runner/continuous.py](../../../ev_runner/continuous.py)
- [docs/reports/issue99-persistent-calibration-cells-20261111.csv](../../../docs/reports/issue99-persistent-calibration-cells-20261111.csv)

## Complementary trajectories

**Status:** verified. **Claim type:** implementation_and_executed_configuration.

Stable and fast differ in retention and update memory. Their lambda values stay fixed; training updates the full forecasters.

Manuscript paragraphs: [P047](../../../report/rebuilt-review-20261112/main.tex#L174), [P048](../../../report/rebuilt-review-20261112/main.tex#L176), [P049](../../../report/rebuilt-review-20261112/main.tex#L178).

Evidence:
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [docs/reports/issue99-stable-fast-20261110/summary.json](../../../docs/reports/issue99-stable-fast-20261110/summary.json)

## Weight update

**Status:** verified. **Claim type:** equation_and_implementation.

Exponential update followed by share-to-other. Weight w is not lambda or a confidence probability. Fresh independent reconstruction checks the recorded events.

Manuscript paragraphs: [P050](../../../report/rebuilt-review-20261112/main.tex#L181), [P051](../../../report/rebuilt-review-20261112/main.tex#L185), [P052](../../../report/rebuilt-review-20261112/main.tex#L190), [P053](../../../report/rebuilt-review-20261112/main.tex#L197), [P054](../../../report/rebuilt-review-20261112/main.tex#L199), [P055](../../../report/rebuilt-review-20261112/main.tex#L201).

Evidence:
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)
- [docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json](../../../docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json)

## Calibration and matched fusion controls

**Status:** verified. **Claim type:** executed_calibration.

Finite grid and weighted-median calibration. Equal-weight/loss-free controls are explicitly posthoc; no global optimum or independent confirmation.

Manuscript paragraphs: [P056](../../../report/rebuilt-review-20261112/main.tex#L204), [P057](../../../report/rebuilt-review-20261112/main.tex#L206), [P058](../../../report/rebuilt-review-20261112/main.tex#L208).

Evidence:
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)
- [docs/reports/issue99-teacher-review-20261111/fusion-controls-groups.csv](../../../docs/reports/issue99-teacher-review-20261111/fusion-controls-groups.csv)
- [docs/reports/issue99-teacher-review-20261111/fusion-controls-summary.json](../../../docs/reports/issue99-teacher-review-20261111/fusion-controls-summary.json)

## Baseline and training-budget controls

**Status:** verified. **Claim type:** executed_recipes.

Nonspatial neural, spatial and classical recipes differ. Source3 and reused Source10 studies must not be pooled.

Manuscript paragraphs: [P059](../../../report/rebuilt-review-20261112/main.tex#L212), [P060](../../../report/rebuilt-review-20261112/main.tex#L214).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [experiments/member_studies/cyber_baselines/models/graph.py](../../../experiments/member_studies/cyber_baselines/models/graph.py)
- [experiments/member_studies/cyber_baselines/training.py](../../../experiments/member_studies/cyber_baselines/training.py)

## Four-target chronological objectives

**Status:** verified. **Claim type:** executed_protocol.

Scheduled objectives differ from actual scored-day counts. Legacy discrete compute/initialization are not matched to continuous tuning.

Manuscript paragraphs: [P061](../../../report/rebuilt-review-20261112/main.tex#L217), [P062](../../../report/rebuilt-review-20261112/main.tex#L219).

Evidence:
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [docs/reports/issue99-study-20261110/comparison-runs.csv](../../../docs/reports/issue99-study-20261110/comparison-runs.csv)
- [docs/reports/issue99-study-20261110/daily-errors.csv](../../../docs/reports/issue99-study-20261110/daily-errors.csv)

## Aggregation and interpretation

**Status:** verified. **Claim type:** definition_and_arithmetic.

Equal seeds within entity then equal scored entities. Zero denominators/nulls and dependent groups cannot become significance claims.

Manuscript paragraphs: [P063](../../../report/rebuilt-review-20261112/main.tex#L222), [P064](../../../report/rebuilt-review-20261112/main.tex#L228), [P065](../../../report/rebuilt-review-20261112/main.tex#L230).

Evidence:
- [tools/issue99_history_study.py](../../../tools/issue99_history_study.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)

## Results: transfer and backbone choice

**Status:** verified, inferred. **Claim type:** observed_result_and_interpretation.

All paired transfer wins and displayed MAEs are checked from ledgers. Competitive/compact is an interpretation, not universal architecture superiority or observed runtime speed.

Manuscript paragraphs: [P066](../../../report/rebuilt-review-20261112/main.tex#L234), [P067](../../../report/rebuilt-review-20261112/main.tex#L236), [P068](../../../report/rebuilt-review-20261112/main.tex#L238), [P069](../../../report/rebuilt-review-20261112/main.tex#L260), [P070](../../../report/rebuilt-review-20261112/main.tex#L262).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [experiments/member_studies/cyber_baselines/runs_v3.csv](../../../experiments/member_studies/cyber_baselines/runs_v3.csv)
- [experiments/member_studies/duc_baselines/runs.csv](../../../experiments/member_studies/duc_baselines/runs.csv)
- [experiments/member_studies/duc_baselines/runs_graph.csv](../../../experiments/member_studies/duc_baselines/runs_graph.csv)

## Results: retention adaptation

**Status:** verified. **Claim type:** observed_result.

Later and Calibration remain separate; calibration positives cannot replace adverse Later aggregate. Frozen-lambda reuses Fixed, not independent retraining.

Manuscript paragraphs: [P071](../../../report/rebuilt-review-20261112/main.tex#L278), [P072](../../../report/rebuilt-review-20261112/main.tex#L280), [P073](../../../report/rebuilt-review-20261112/main.tex#L293).

Evidence:
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [docs/reports/issue99-persistent-results-20261111.md](../../../docs/reports/issue99-persistent-results-20261111.md)
- [docs/reports/issue99-persistent-calibration-cells-20261111.csv](../../../docs/reports/issue99-persistent-calibration-cells-20261111.csv)
- [docs/reports/issue99-study-20261110/controller-trajectory-summary.json](../../../docs/reports/issue99-study-20261110/controller-trajectory-summary.json)
- [docs/reports/issue99-study-20261110/comparison-verification.json](../../../docs/reports/issue99-study-20261110/comparison-verification.json)

## Results: historical adaptive fusion

**Status:** verified, inferred. **Claim type:** observed_result_and_interpretation.

9/21 original selector; 18/21 adaptive and static fusion; 12/21 adaptive versus static. Previously inspected cohort; no significance/untouched-test claim.

Manuscript paragraphs: [P074](../../../report/rebuilt-review-20261112/main.tex#L331), [P075](../../../report/rebuilt-review-20261112/main.tex#L333), [P076](../../../report/rebuilt-review-20261112/main.tex#L335), [P077](../../../report/rebuilt-review-20261112/main.tex#L337), [P078](../../../report/rebuilt-review-20261112/main.tex#L344), [P079](../../../report/rebuilt-review-20261112/main.tex#L357), [P080](../../../report/rebuilt-review-20261112/main.tex#L359).

Evidence:
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)
- [docs/reports/issue99-teacher-review-20261111/fusion-controls-groups.csv](../../../docs/reports/issue99-teacher-review-20261111/fusion-controls-groups.csv)
- [docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json](../../../docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json)

## What the results establish

**Status:** inferred. **Claim type:** inference_from_observed_results.

Conditional interpretation of the recorded comparisons only. No universally optimal backbone or controller claim.

Manuscript paragraphs: [P081](../../../report/rebuilt-review-20261112/main.tex#L363), [P082](../../../report/rebuilt-review-20261112/main.tex#L365), [P083](../../../report/rebuilt-review-20261112/main.tex#L367), [P084](../../../report/rebuilt-review-20261112/main.tex#L369).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)

## When source influence should be reduced

**Status:** verified, inferred. **Claim type:** definition_and_hypothesis.

w is prediction contribution; lambda is an optimization coefficient. Suggested explanations for losses are hypotheses, not causally verified diagnoses.

Manuscript paragraphs: [P085](../../../report/rebuilt-review-20261112/main.tex#L372), [P086](../../../report/rebuilt-review-20261112/main.tex#L374).

Evidence:
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)
- [ev_control/hypergradient.py](../../../ev_control/hypergradient.py)
- [ev_control/confidence.py](../../../ev_control/confidence.py)

## Limitations and reproducibility

**Status:** verified. **Claim type:** verification_boundary.

Code/ledger/saved-vector verification does not reproduce training, certify raw publishers, reconstruct all bootstrap draws, or supply an untouched test.

Manuscript paragraphs: [P087](../../../report/rebuilt-review-20261112/main.tex#L377), [P088](../../../report/rebuilt-review-20261112/main.tex#L379), [P089](../../../report/rebuilt-review-20261112/main.tex#L381), [P090](../../../report/rebuilt-review-20261112/main.tex#L383), [P091](../../../report/rebuilt-review-20261112/main.tex#L385).

Evidence:
- [docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json](../../../docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json)
- [docs/reports/issue99-teacher-review-20261111/baseline-verification.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-verification.json)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [docs/reports/issue99-teacher-review-20261111/duc-reused-audit-receipt.md](../../../docs/reports/issue99-teacher-review-20261111/duc-reused-audit-receipt.md)
- [docs/reports/issue99-persistent-results-20261111.md](../../../docs/reports/issue99-persistent-results-20261111.md)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)

## Conclusion

**Status:** verified, inferred. **Claim type:** synthesis.

Empirical summaries are restricted to these executed cohorts. Motivations and research questions are not results; no universal transfer/controller superiority follows.

Manuscript paragraphs: [P092](../../../report/rebuilt-review-20261112/main.tex#L388).

Evidence:
- [docs/reports/issue99-teacher-review-20261111/cyber-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/cyber-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/duc-summary.csv](../../../docs/reports/issue99-teacher-review-20261111/duc-summary.csv)
- [docs/reports/issue99-teacher-review-20261111/baseline-provenance.json](../../../docs/reports/issue99-teacher-review-20261111/baseline-provenance.json)
- [experiments/member_studies/cyber_baselines/artifacts_v3/environment.json](../../../experiments/member_studies/cyber_baselines/artifacts_v3/environment.json)
- [experiments/member_studies/duc_baselines/session.json](../../../experiments/member_studies/duc_baselines/session.json)
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-study-20261110/protocol-lock.json](../../../docs/reports/issue99-study-20261110/protocol-lock.json)
- [docs/reports/issue99-study-20261110/fixed-trials.csv](../../../docs/reports/issue99-study-20261110/fixed-trials.csv)
- [docs/reports/issue99-study-20261110/fixed-selection.json](../../../docs/reports/issue99-study-20261110/fixed-selection.json)
- [docs/reports/issue99-study-20261110/controller-lock.json](../../../docs/reports/issue99-study-20261110/controller-lock.json)
- [docs/reports/issue99-study-20261110/method-summary.csv](../../../docs/reports/issue99-study-20261110/method-summary.csv)
- [ev_control/expert_mix.py](../../../ev_control/expert_mix.py)
- [tools/issue99_stable_fast.py](../../../tools/issue99_stable_fast.py)
- [tools/issue99_full_scope.py](../../../tools/issue99_full_scope.py)
- [docs/reports/issue99-stable-fast-20261110/selection-lock.json](../../../docs/reports/issue99-stable-fast-20261110/selection-lock.json)
- [docs/reports/issue99-stable-fast-20261110/verification.json](../../../docs/reports/issue99-stable-fast-20261110/verification.json)

## Initial-training calibration

**Status:** verified. **Claim type:** measured_calibration.

All five measured epoch choices shown. Calibration entities differ from the twelve evaluation entities; finite minima only.

Manuscript paragraphs: [P093](../../../report/rebuilt-review-20261112/main.tex#L397).

Evidence:
- [docs/reports/issue99-history-review-20261110/cells.csv](../../../docs/reports/issue99-history-review-20261110/cells.csv)
- [docs/reports/issue99-history-review-20261110/verified-summary.json](../../../docs/reports/issue99-history-review-20261110/verified-summary.json)
- [docs/reports/issue99-history-review-20261110/14d-registration.json](../../../docs/reports/issue99-history-review-20261110/14d-registration.json)
- [docs/reports/issue99-history-review-20261110/7d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/7d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/14d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/14d-epoch-lock.json)
- [docs/reports/issue99-history-review-20261110/28d-epoch-lock.json](../../../docs/reports/issue99-history-review-20261110/28d-epoch-lock.json)
- [tools/issue99_manuscript_figures.py](../../../tools/issue99_manuscript_figures.py)

## Recorded forecast-weight examples

**Status:** verified. **Claim type:** recorded_trace_selection.

Recorded seed42 upper-median examples, not best-case or measured confidence envelopes. Source cells rehashed in the fresh readback.

Manuscript paragraphs: [P094](../../../report/rebuilt-review-20261112/main.tex#L404).

Evidence:
- [tools/issue99_manuscript_figures.py](../../../tools/issue99_manuscript_figures.py)
- [report/teacher-review-20261111/trajectory-data.csv](../../../report/teacher-review-20261111/trajectory-data.csv)
- [report/teacher-review-20261111/trajectory-selection.json](../../../report/teacher-review-20261111/trajectory-selection.json)
- [docs/reports/issue99-full-scope-20261110/cells.csv](../../../docs/reports/issue99-full-scope-20261110/cells.csv)
- [docs/reports/issue99-full-scope-20261110/group-results.csv](../../../docs/reports/issue99-full-scope-20261110/group-results.csv)
- [docs/reports/issue99-full-scope-20261110/execution-lock-v3.json](../../../docs/reports/issue99-full-scope-20261110/execution-lock-v3.json)
- [report/full-results.csv](../../../report/full-results.csv)
- [docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json](../../../docs/reports/issue99-controller-identity-audit-20261112/saved-mixture-readback.json)

## Forecast loss and latent retention

**Status:** verified. **Claim type:** equation_and_implementation.

Equations match code and parameter counts. Gradient magnitude is not an empirical claim about retained knowledge.

Manuscript paragraphs: [P098](../../../report/rebuilt-review-20261112/model-equations.tex#L18), [P099](../../../report/rebuilt-review-20261112/model-equations.tex#L23), [P100](../../../report/rebuilt-review-20261112/model-equations.tex#L28), [P101](../../../report/rebuilt-review-20261112/model-equations.tex#L32).

Evidence:
- [ev_models/model.py](../../../ev_models/model.py)
- [ev_models/training.py](../../../ev_models/training.py)
- [ev_runner/diagnostics.py](../../../ev_runner/diagnostics.py)
- [report/rebuilt-review-20261112/references.bib](../../../report/rebuilt-review-20261112/references.bib)
