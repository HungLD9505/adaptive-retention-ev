# Issue #99 transfer and confidence evidence

Transfer initialization gives a large improvement under the tested adaptation budget. Adding confidence to online mean-based selection gives a small improvement, while the calibration-selected constant level remains better.

| Method on twelve additional stations | Macro MAE, kWh |
| --- | ---: |
| Random target-only | 5.462870 |
| Source fine-tune, λ=0 | 3.304605 |
| Fixed bank λ=1 | 3.267000 |
| Lowest past MAE, start λ=1 | 3.290432 |
| Same challenger with confidence gate, start λ=1 | 3.279916 |
| Lowest past MAE, historical start λ=0.1 | 3.292236 |
| Same challenger with confidence gate, start λ=0.1 | 3.286280 |

The λ=1 start matches the initial expert used by Fixed. Source fine-tuning reduces MAE by 39.508% relative to target-only and improves all twelve station means. Confidence reduces MAE by 0.320% relative to mean-only selection at the matched λ=1 start, improving seven of twelve station means. It still increases error by 0.395% relative to Fixed and improves only three station means relative to Fixed.

These outcomes support transfer under this limited adaptation budget. They do not establish that changing retention outperforms the best calibration-selected constant or that the GRU is a superior backbone.

## Experiment scope and chronology

The same twelve UrbanEV/SZH Development stations selected in the preceding extension are used. Source10 seeds are 42/43/44. Each station has a 14-day initial history and thirteen trainable prefix examples. The 90-day causal replay, input normalization, complete-day label gate, original missingness, GRU, Adam learning rate 0.001, three initial epochs and one online epoch per arrived day remain fixed.

The target-only arm uses randomly initialized GRU/head weights and zero retention. It loads Source metadata for compatibility checks, but its model weights are constructed after resetting the seed; Source weights and source latent scales do not enter its training objective. Immutable run bindings explicitly record source_initialization=false and source_weights_used_for_training=false. An independent reconstruction using only the target prefix and a fresh random GRU exactly reproduced the first forecast for station 1691 in all three seeds.

The comparison is matched by target adaptation budget. Target-only convergence, its learning-rate schedule and its epoch count have not been separately tuned. The large transfer difference is conditional on this budget; it cannot be presented as a comparison against a fully optimized target-only learner.

## Common bank and confidence isolation

For each station/seed, train three independent constant-retention experts at λ=0/0.1/1. Each expert is initialized from the same Source10 checkpoint and follows its own adaptation trajectory. Both selectors consume exactly the same saved expert predictions and arrived score vectors. Selecting an expert never changes its training or another expert's state.

This permanent common bank is a separate controlled ablation. The primary historical controller forks all candidates from the selected state at block boundaries. These common-bank results must not be relabeled as closed-loop results of that historical implementation.

Both selectors recommend the lowest mean-error candidate from the previous seven-day block, requiring at least five complete arrived days. Ties use distance from the current level and configured level order. The confidence variant considers that same candidate and accepts it only if its paired moving-block-bootstrap lower confidence bound exceeds zero. It does not switch to a different candidate merely because that other candidate has a higher bound. Segment length is three, resamples 2000, alpha 0.05, delta zero. All candidate errors are normalized by the same fixed target prefix scale before statistical decisions; reported errors and future audits are in kWh.

The original four calibration targets select a single Fixed bank level by original-unit macro MAE across three seeds. λ=1 was locked before additional-target expert training. The first policy comparison retains historical initial λ=0.1. The matched λ=1 initialization was added after that comparison was inspected to remove the initialization disadvantage against Fixed. Both variants are retained. This additional analysis is posthoc and exploratory.

There are 144 expert-training runs: four calibration targets plus twelve additional targets, each with three seeds and three levels. Another 36 random target-only runs complete the training matrix. Policies are then replayed against the authenticated bank without model retraining. The final table has 36 cells per method, including the matched-start diagnostic arms.

## What the evidence answers

**When is Source useful?** At the tested 14-day history and training budget, Source fine-tuning beats random target-only in all twelve stations, spanning the four predefined prefix-sparsity strata. This cohort contains no station where transfer initialization loses on station-mean error. It therefore does not identify a threshold for abandoning Source initialization.

**When does reducing retention help?** From the matched-start confidence trajectory, the lowest-past-MAE rule recommends reducing retention 118 times with later complete labels. Reducing retention improves the following block in 67 of those cases (56.8%). This is a retrospective test of the past-error signal, not an oracle supplied to the selector.

**Does confidence improve decisions?** On the matched-start trajectory, the gate accepts 84 recommendations: 55 improve the following block and 29 worsen it. It rejects 110 recommendations: 53 would worsen the following block and 57 would improve it. The other 238 boundaries have no recommendation to change level. The gate avoids some harmful changes and also misses beneficial changes; the resulting mean gain over mean-only is small.

**Does adaptive selection outperform Fixed?** It does not in this cohort. Fixed bank λ=1 has lower aggregate error and wins nine of twelve station means against the matched-start confidence selector. The two adaptive selectors share the same expert bank and match Fixed's initial expert, so the residual aggregate gap cannot be attributed solely to the historical λ=0.1 starting choice.

## Paired uncertainty and subgroup diagnostics

Seeds are averaged within station before making 20,000 paired bootstrap draws within the four predefined sparsity strata. Intervals are exploratory, unadjusted for multiple comparisons, and do not account for posthoc analysis choices or establish city-wide generalization.

| Comparison | Mean MAE difference, kWh | Station bootstrap interval |
| --- | ---: | --- |
| Source fine-tune − target-only | −2.158265 | [−2.505863, −1.827184] |
| Fixed − target-only | −2.195870 | [−2.556337, −1.859031] |
| Confidence − mean-only, start λ=1 | −0.010516 | [−0.021063, −0.000443] |
| Confidence − Fixed, start λ=1 | +0.012916 | [+0.000771, +0.025458] |
| Mean-only − Fixed, start λ=1 | +0.023432 | [+0.008505, +0.037511] |

With matched initialization, confidence minus mean-only is −0.025888/−0.029820/+0.008167/+0.005475 kWh across sparsity strata 0/1/2/3. Each stratum contains three stations. These subgroup outcomes were inspected after scoring. They motivate a subsequent hypothesis about sparse demand and evidence quality, but do not validate a sparsity threshold or a subgroup-specific controller.

The bootstrap bound describes a past-block paired mean, not a guarantee about the next week. The challenger is selected using the same block used for its confidence calculation, and station errors are temporally dependent. No calibrated future probability of successful switching is established.

## Readback, unit correction and provenance

The initial offline pass supplied original-unit errors to the statistical helper. The final readback converts all expert errors to the helper's documented fixed normalized scale and recalculates every policy choice. The model training and prediction vectors are unchanged. Intermediate outputs are preserved at their separate locations.

The final readback additionally preserves each authenticated canonical saved score for bootstrap input hashing, after independently checking it against the vector/label recomputation. This avoids introducing last-bit arithmetic differences into deterministic bootstrap seeds. The final v4 readback and current production CLI use the same score-unit convention. The v3/v4 outcomes agree; v4 adds duplicate-forecast rejection and normalized readback provenance.

Independent verification recomputed 11,691 saved scores across the original calibration experts, additional-station experts and target-only runs, checked prediction-file hashes and complete label availability at score time, required identical expert and target-only masks, and verified random-initialization bindings. Future decision audits are computed only after the causal choices are complete and never feed back into a selector.

Current core source bytes match all initial loaded core-file hashes. The exact initial executed-evidence.py and intermediate readback scripts are preserved outside Git. The Source byte hashes, input manifest identity and script identities are retained in training-registration.json, summary.json and core-code-verification.json. Input bytes were authenticated before execution and rehashed after readback. Publisher raw archives were not freshly checked.

External root:
 /Users/quyenmanh/Developer/TFL-EV/runs/issue99-confidence-evidence-20261110-v1

Final analysis:
 /Users/quyenmanh/Developer/TFL-EV/runs/issue99-confidence-evidence-20261110-v1/normalized-readback-v4

Reproduce training with python -m tools.issue99_confidence_evidence and --input, --sources, --inventory and a new --output directory. Reproduce final normalized policy readback with python -m tools.issue99_confidence_readback and --input, --run, --inventory and a new --output. Large checkpoints and per-forecast results remain outside Git. cells.csv, decisions.csv and station-results.csv provide full-precision review tables.

The current evidence remains Development-only. Tracked metadata checks do not exhaustively establish the absence of prior remote/untracked exposure, and the twelve stations have already been inspected in the preceding extension. Neither Final performance nor a new-method effectiveness claim follows from this study.
