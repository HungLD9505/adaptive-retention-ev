# Issue #99 expanded Development comparison

On twelve additional UrbanEV/SZH Development stations, the aggregate advantage of encoder L2-SP over Fixed latent retention was 0.002773 kWh (0.0847%). L2-SP improved five station means and worsened seven relative to Fixed. The paired station bootstrap interval for L2-SP minus Fixed was [−0.012742, +0.007676] kWh. The larger L2-SP advantage observed on the original four stations did not replicate clearly in this extension.

| Method | Macro MAE, kWh | Reduction versus λ=0 | Stations improved versus λ=0 | Invocation time, seconds |
| --- | ---: | ---: | ---: | ---: |
| Source fine-tune λ=0 | 3.304605 | — | — | 30.06 |
| Fixed latent | 3.274849 | 0.900% | 8/12 | 35.45 |
| Encoder L2-SP | 3.272075 | 0.984% | 8/12 | 31.68 |
| Calibrated discrete controller | 3.281367 | 0.703% | 8/12 | 69.98 |

Invocation times sum the 36 current CPU calls per method, including loading and replay. Source pretraining cost is excluded and was not estimated. The controller maintains three shadow branches and uses about 1.97 times Fixed's measured wall time. Equal hyperparameter candidate counts do not imply equal training compute.

This remains exploratory Development evidence. The inventory excludes IDs found in tracked JSON metadata; untracked runs, remote notebooks and older exposure were not exhaustively audited. None of the results is claimed as an untouched holdout, a Final result, or evidence of a novel algorithm.

## Inventory and selection before outcomes

The prepared 14-day UrbanEV/SZH input has 328 Development identities, of which 296 are ready and 32 have undefined scale. The candidate rule requires ready Development role, at least four trainable prefix examples and no entity_id match in existing configs/docs report JSON metadata. The metadata scan is conservative across namespaces. It leaves 267 eligible identities. No candidate forecast error or replay-label energy is used for selection.

Sort candidates by prefix zero-hour fraction, then entity ID, split the rank list into four equal-sized strata, and choose the three smallest SHA-256("issue99-expanded-v1:" + entity_id) ranks within each. This owner-authorized bounded selection produces twelve stations:

1691, 2564, 2398, 1114, 1225, 1169, 1885, 1802, 2035, 1836, 1303, 1325.

Their prefix zero fractions span 0% to 97.3%. All twelve have thirteen trainable prefix examples. The study therefore extends station identities and demand sparsity, while adding no new evidence about sparse usable initial-history counts. inventory.json records the rule, exclusions and every selected ID before replay.

## Calibration and frozen methods

All methods reuse the three authenticated Source10 seed checkpoints, the same input manifest, GRU architecture, source-frozen reference, 14-day target prefix, model learning rate 0.001, three initial adaptation epochs, one online epoch per complete arrived day, and the same delayed-label causal runner semantics.

Fixed latent and L2-SP reuse the existing twelve-cell-per-candidate calibration evidence from the original four targets. Each has three strengths, 0.1/1/10, converted to a per-target/seed constant lambda using forecast-gradient norm divided by penalty-gradient norm at a disposable prefix-only adapted state. This uses only predeployment labels and remains fixed throughout online replay. Both selected strength 1 by minimum macro calibration MAE. It is a prefix-calibrated Fixed method, not the historical single absolute coefficient across all stations.

The historical controller's decision mechanism and levels 0/0.1/1 remain in use. Its initial lambda is 0.1. The added calibration searches three decision periods: 7 days with minimum 5 valid days, 14 days with minimum 7, and 21 days with minimum 7. Segment length 3, bootstrap count 2000, alpha 0.05 and delta 0 remain fixed. Thirty-six new calibration runs on the original four targets score their registered first-window origins. Macro calibration MAE was 5.388123, 5.437066 and 5.425297 kWh respectively. Period 7 was selected. These are equal three-candidate search budgets with unequal shadow-model computation.

selection-lock.json was saved before any additional-station replay. All 144 per-cell experimental bindings match its SHA-256 and the three registered Source checksums.

## Evaluation and missingness

Twelve stations × three paired seeds × four methods give 144 full 90-day replays. Every complete scored origin in the full replay is used, since the additional stations are separate from calibration stations. Score counts per seed are 52/90/90/89/52/52/90/90/90/52/51/90 in the station order above. Missing inputs or incomplete labels remain explicit. Every method within each station/seed has exactly the same scored-origin set.

The macro averages days within seed, seeds within station, and twelve stations equally. Per-station results are in station-results.csv; cells.csv retains all seed values, actual constant coefficients and measured invocation times. The new full-replay macro should not be pooled with the earlier four-target later-window score.

The uncertainty calculation makes 20,000 paired bootstrap draws of stations within the four prefix-sparsity strata, averaging seeds before sampling. It describes this small selected cohort under that resampling scheme. Intervals are exploratory, unadjusted for multiple contrasts, and do not establish general effectiveness across cities or budgets.

| Comparison | Mean MAE difference, kWh | Bootstrap interval |
| --- | ---: | --- |
| Fixed − λ=0 | −0.029756 | [−0.046025, −0.012530] |
| L2-SP − λ=0 | −0.032529 | [−0.052557, −0.014380] |
| Controller − λ=0 | −0.023238 | [−0.032612, −0.012747] |
| L2-SP − Fixed | −0.002773 | [−0.012742, +0.007676] |
| Controller − Fixed | +0.006519 | [−0.004965, +0.018876] |

## Implementation and reproducibility

The expanded tool reuses the existing fixed and discrete replay entry points. The continuous study and prepared-input cache now accept an explicit target allowlist, with their original four-target defaults retained. The discrete runner has an explicit programmatic CPU diagnostic option restricted to adaptive Development runs at 14 days; its ordinary CLI still requires CUDA. CPU memory fields are null. Regression fixtures cover default CPU rejection, Final/other-budget rejection, ambiguous allowlists, expanded opt-in and the original cache authenticity behavior.

L2-SP remains an encoder-only half-squared parameter displacement penalty. It is applied with a scoped single-threaded replacement of the training loss inside the dedicated experiment, with explicit per-cell method bindings. The base training primitives, GRU cell and controller confidence rule remain shared.

Reproduce with tools.issue99_expanded_development using --input INPUT_ROOT --sources SOURCE_PARENT --calibration PRIOR_CALIBRATION_ROOT --inventory inventory.json --output NEW_RUN_ROOT. Recompute independent scores with tools.issue99_expanded_verify using --input INPUT_ROOT --run RUN_ROOT --inventory inventory.json --output NEW_ANALYSIS_ROOT.

External artifact root:
 /Users/quyenmanh/Developer/TFL-EV/runs/issue99-expanded-development-20261110-v1

The full execution contains 36 new controller calibration cells and 144 evaluation cells and completed in 209.33 seconds on CPU. The parent calibration has 72 reused candidate cells for Fixed/L2-SP. The original executed-expanded.py is preserved under its registration hash. A subsequently removed unused import does not change execution. Initial loaded core bytes were reconstructed and matched all 24 initial runtime-binding hashes, recorded in executed-code-reconstruction.json. Later target validation/error-message edits during execution did not change training or replay formulas; executed-core retains the initial implementation. Per-call bindings and the explicit experimental script hash remain available.

## Verification

The independent readback matched all 144 cell identities, checked prediction-file hashes, recomputed 10,656 MAEs from actual saved vectors and labels available at each recorded score time, verified active controller branch selection, compared matched-origin masks, and recomputed every cell mean. Maximum score discrepancy was below 1e-9 kWh. Input bytes were authenticated before execution and rehashed afterward. The Source bytes were reused locally; publisher raw archives were not freshly downloaded.

The implementation passed all 944 root tests with two CUDA skips, nine fixed-adaptation tests, twelve confidence-controller tests, Ruff lint/format, release checks and git diff checks. The optional all-namespace external-artifact suite was not run. Validation fixtures check software behavior; the real-input evidence is the saved replay and independent readback.
