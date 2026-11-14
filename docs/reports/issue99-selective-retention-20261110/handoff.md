# Issue #99 experimental retention loss screen

Encoder L2-SP achieved the lowest later Development MAE in this bounded loss ablation, 4.710197 kWh. Uniform latent retention achieved 4.815521, the prefix-weighted latent variant 4.792105, and lambda-zero fine-tuning 4.868598. L2-SP is 2.187% below the matched uniform arm and 3.253% below lambda zero. These are exploratory results on previously inspected Development targets.

| Target | Fine-tune λ=0 | Uniform latent | Selective latent | Encoder L2-SP |
| --- | ---: | ---: | ---: | ---: |
| 1405 | 5.386144 | 5.333351 | 5.297888 | 5.049886 |
| 2152 | 6.124389 | 6.050237 | 5.971323 | 5.987069 |
| 1153 | 6.532764 | 6.419273 | 6.416653 | 6.367623 |
| 1693 | 1.431095 | 1.459222 | 1.482555 | 1.436211 |
| Equal-target macro | 4.868598 | 4.815521 | 4.792105 | 4.710197 |

Each entry averages seeds 42/43/44. L2-SP still harms 1693 relative to lambda zero, by 0.005117 kWh. Selective latent is better than L2-SP at 2152. No method dominates all targets. The prior #102 Fixed result (4.803054) came from a different search and GPU/runtime; it is historical context rather than the matched uniform comparator here.

## Separate method experiment

This separate experiment evaluates alternative retention implementations while preserving the primary loss and Report 1 method. All arms reuse the same existing two-layer GRU Source10 checkpoints, 14-day target prefix, three initial adaptation epochs, one online epoch per complete arrival, model learning rate 0.001, complete 24→24 labels, deterministic CPU execution and causal runner.

Uniform penalty is the existing mean square latent displacement after dividing by source standard deviation plus 0.001. Selective penalty multiplies each of the 64 squared normalized displacements by a prefix-derived weight with mean one. To derive weights, ablate each source latent coordinate to zero in the source prediction on the predeployment target prefix. Take the positive increase in prefix forecast MAE, normalize to mean one, then mix 90% importance with 10% uniform weight. If all positive effects vanish, use uniform weights. Weights stay frozen throughout adaptation and replay. The uniform mixing fraction is an engineering choice; its robustness was not searched.

This is an adaptation of the feature-selection motivation of [DELTA](https://arxiv.org/abs/1901.09229), originally proposed for convolutional networks, rather than a reproduction of its attention algorithm. L2-SP uses half the sum of squared encoder parameter displacement from Source10; the head remains free. It follows the source-reference penalty rationale of [Li et al., ICML 2018](https://proceedings.mlr.press/v80/li18a.html). This implementation and these EV results do not establish method novelty.

## Equal search and selection

For each target/seed, make a disposable source copy and take one unregularized prefix epoch. At that same probe state, measure encoder forecast-gradient norm and each penalty-gradient norm. Set lambda to strength times their norm ratio. Strengths 0.1, 1 and 10 therefore anchor one-tenth, equal and tenfold penalty-gradient magnitude at that probe. This mapping uses only the initial prefix and is frozen before replay. The instantaneous gradient ratio subsequently changes.

All three penalty types receive the same three strengths and the same twelve target/seed cells per strength. A further twelve lambda-zero cells give 120 calibration runs. Select one strength per penalty by minimum equal-target macro calibration MAE, averaging seeds within targets. All three selected strength 1. Calibration MAEs at strengths 0.1 / 1 / 10 were:

| Penalty | 0.1 | 1 | 10 |
| --- | ---: | ---: | ---: |
| Uniform | 5.454382 | 5.346405 | 5.367365 |
| Selective | 5.434102 | 5.364783 | 5.367244 |
| L2-SP | 5.369099 | 5.307612 | 5.308380 |

The L2-SP strength-1 and strength-10 calibration results are extremely close; no stable optimal coefficient is established. The same three-point strength budget is a bounded screening experiment, not exhaustive hyperparameter optimization.

Freeze these choices, rerun the twelve cells per selected method plus twelve lambda-zero controls for the full 90-day replay, and score only the existing later-origin list. This produces 48 evaluation runs, with 60/22/22/22 complete later days at 1405/2152/1153/1693. The later outcomes were not used by the selection code. This Development cohort and prior later outcomes were already exposed, so the results remain exploratory.

## Dimension audit

After the disposable unregularized prefix epoch, the five largest coordinates account for 24.1–78.1% of normalized latent displacement penalty across the twelve cells; the median is 39.5%. This measures penalty contribution, not per-coordinate encoder-gradient norm. Source standard deviations range approximately 0.191–0.830 across the seeds, so this probe supplies no evidence of near-zero source variance driving normalization blow-up. Penalty concentration alone does not establish harmful retention.

The selective variant loses to uniform on calibration and improves later MAE slightly. Its broader reliability and its feature-weight rule remain unresolved. The evidence currently favors evaluating L2-SP further before developing a more complicated controller.

## Execution identities and verification

Inputs are pinned to manifest SHA-256 66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9. Source10 byte hashes and all dimension weights are in dimension-audit.json. Fresh publisher archives were not checked. Runtime is Python 3.12.13, Torch 2.11.0, CPU with one thread.

Each run retains the normal causal-runner inputs/code/optimizer binding and an experimental-loss-binding.json giving the actual penalty, coefficient, strength and weights. The implementation uses scoped single-threaded replacement of the existing training penalty inside the experimental tool. It must not be run concurrently in one Python process. Hypergradient decisions and the original loss diagnostic are disabled in these fixed-coefficient arms.

Both independent score checks passed, recomputing all 3,330 calibration and 1,512 later scores from checksummed saved vectors and complete labels at their recorded availability times. Maximum MAE discrepancy is 3.56e-15 kWh. The verifier also checks duplicate origins and cell means. Input bytes were rehashed after each phase. It does not reproduce training independently or establish statistical significance.

Large run roots remain outside Git:
- /Users/quyenmanh/Developer/TFL-EV/runs/issue99-selective-screen-20261110-v1
- /Users/quyenmanh/Developer/TFL-EV/runs/issue99-selective-evaluation-20261110-v1

Calibration's original executed-screen.py is preserved with its recorded script hash. Type annotations and an evaluation option were added before the evaluation invocation; the two registration records identify the respective script hashes. Model-training formulas were unchanged between phases. summary.csv and cells.csv retain full precision, per-cell lambda and per-target outcomes.

Reproduce calibration using python -m tools.issue99_retention_screen with --input, --sources and a new --output directory. Reproduce the later phase with the same arguments plus --calibration-from pointing to the completed calibration directory. Recompute score checks with python -m tools.issue99_retention_verify --input INPUT_ROOT --run RUN_ROOT. The diagram exports method-comparison.png/pdf show later macro MAE with a zero-based axis.

## Validation

The committed implementation passed 940 root tests with two CUDA skips, nine fixed-adaptation tests, twelve confidence-controller tests, Ruff lint/format, release checks and git diff whitespace checks. The three new fixtures check uniform-weight equivalence to the primary penalty, encoder-only L2-SP and reference-gradient isolation, and positive mean-one prefix weights. Both independent real-input score readbacks passed. No external 18-test all-namespace artifact suite or fresh raw archive acquisition was run. The plotted artifact was visually inspected.

Per-seed equal-target later L2-SP minus uniform MAE is −0.137600, −0.028451 and −0.149921 kWh for seeds 42/43/44. These descriptive differences do not supply independent station replication or a significance claim.
