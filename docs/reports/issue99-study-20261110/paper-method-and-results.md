# Method addition for exploratory retention study

Let F be the mean absolute error across complete normalized 24-hour forecast days and R the frozen-source latent penalty:

$$F(B;\theta)=\frac{1}{24|B|}\sum_{i\in B}\sum_{j=1}^{24}|\hat y_{ij}^{scaled}(\theta)-y_{ij}^{scaled}|,\qquad R(B;\theta)=\frac{1}{64|B|}\sum_{i\in B}\sum_{k=1}^{64}\left(\frac{h_k(x_i;\theta)-h_k(x_i;\theta_s)}{s_k+\epsilon_R}\right)^2.$$

Source parameters theta_s and population latent standard deviations s remain frozen; epsilon_R=0.001. The division occurs before squaring. Fixed trains with F+lambda R using a constant real coefficient. The model remains the existing two-layer, 64-unit GRU and calendar-aware head; no custom GRU cell is introduced. Lambda changes the retention penalty, not the learning rate, and is not a percentage of retained knowledge.

The one-step controller follows the validation-hypergradient rationale of [Luketina et al. (2016)](https://proceedings.mlr.press/v48/luketina16.pdf), specialized here to current-Adam dynamics. From the current real weights/moments, form g(lambda)=grad_theta[F_A+lambda R_A], virtual moments m'=beta1*m+(1-beta1)*g and v'=beta2*v+(1-beta2)*g^2, and a bias-corrected Adam virtual update. Previous weights and moments are treated as fixed starting state for this local derivative; the virtual update does not mutate the real optimizer.

$$\tilde\theta_t(\lambda)=\operatorname{AdamStep}(\theta_t,m_t,v_t;\nabla_\theta[F_A+\lambda R_A]),\qquad\lambda_{t+1}=\Pi_{[0,U]}\left(\lambda_t-\eta\frac{\partial F_V(\tilde\theta_t(\lambda))}{\partial\lambda}\bigg|_{\lambda_t}\right).$$

A contains two older complete arrived label days; V contains the newest complete arrived day not yet used in real training. The outer loss is forecast MAE alone. After the meta decision, the real branch trains on the newly arrived day and marks its label consumed, then issues future forecasts. Learning rate 0.001, Adam betas (0.9,0.999) and Adam epsilon 1e-8 remain fixed; these differ from retention epsilon_R. The exact-zero variance treatment is the documented tested numerical choice, not a convergence guarantee.

Fixed uses finite GP/EI optimization in log-positive lambda plus a separately evaluated zero and a coverage sensitivity grid, following the hyperparameter-optimization rationale of [Snoek et al. (2012)](https://arxiv.org/pdf/1206.2944). The 4097-point acquisition grid approximates maximization of EI over the numeric domain. Numerical endpoints, kernel/noise choices, finite budgets, gradient-derived step scaling and projection are study choices, not EV-specific constants established by these papers. The registered calibration determines Fixed and controller settings before later exploratory comparison.


# Issue #99 completed exploratory Development study

This study compares calibrated fixed latent retention with a continuous one-step validation controller. On the registered later objective, Continuous MAE is 4.806223 kWh and Fixed MAE is 4.803054 kWh. Source10, four selected UrbanEV/SZH targets, three paired seeds and 14-day initial history were reused. This is exploratory Development evidence, not fresh held-out or scientifically peer-approved evidence. The task remains 24→24. Historical reports and Final results are unchanged.

## Registered scope and selection

The first 28 scheduled origins supplied calibration, the next two were excluded from both score objectives, and the final 60 supplied the later objective. Online replay covered all 90 scheduled days with actual delayed label availability. Prior exposure to this cohort makes every result exploratory. Expected later score counts are 60/22/22/22, not 60 complete days for every station; all missing/skipped outcomes remain.

Fixed selection: lambda=0.798445006708, calibration MAE=5.331705633 kWh versus lambda0=5.443630218. Boundary unresolved: False. The selected value is best among evaluated points, not a proven global optimum. The full fixed ledger, failed/null trials and sampled regimes are exported separately; sensitivity lines connect measurements and do not estimate exact transition boundaries.

Controller interval: [0,33.8442461273], initialized at 0.798445006708. Selected eta=211.295003431, cadence=1 complete arrivals, A=2 older arrived days and V=1 newer untrained day. Selection used only registered calibration MAE among six declared recipes. The numerical bounds and scale fractions are study choices; cited hypergradient papers do not prescribe EV-specific values.

## Matched results

| Method | Later-objective MAE, kWh | Delta vs lambda0 | Full-90 descriptive MAE |
| --- | ---: | ---: | ---: |
| lambda0 | 4.868597 | +0.000000 | 5.144953 |
| fixed | 4.803054 | -0.065543 | 5.053859 |
| discrete | 4.798259 | -0.070339 | 5.098825 |
| continuous | 4.806223 | -0.062374 | 5.052390 |
| frozen_lambda | 4.803054 | -0.065543 | 5.053859 |

Continuous minus calibrated Fixed on the later objective is **+0.003169 kWh**; a negative value favors Continuous. This is the main mechanism comparison, not the earlier calibration improvement.

| Target | lambda0 | Fixed | Discrete | Continuous | Frozen |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1405 | 5.386140 | 5.235166 | 5.283969 | 5.203826 | 5.235166 |
| 2152 | 6.124389 | 5.981652 | 6.030500 | 6.090296 | 5.981652 |
| 1153 | 6.532764 | 6.426777 | 6.393199 | 6.393993 | 6.426777 |
| 1693 | 1.431097 | 1.568621 | 1.485368 | 1.536778 | 1.568621 |

All entries average paired seeds within station, then give the four stations equal weight. The full-90 column mixes calibration and later days and is descriptive only. Frozen lambda may exactly reuse Fixed when all executable configurations match; it is not an independently retrained replicate. The legacy discrete controller keeps its original recipe and three shadow models, with greater compute and different initialization than the single-branch methods. It was not retuned for this new calibration split, so tuning budgets differ and its gap cannot be attributed solely to the controller mechanism.

## Interpretation and limits

Read the paired station results and seed ranges with the aggregate. Four historically selected stations in one city are a small dependent cohort. No significance, universal transfer/GRU superiority, or calibrated safe-adaptation guarantee is established. Coefficient movement and gradient ratios are diagnostics, not proof of forecast improvement. Negative comparisons remain visible. This study does not replace the separate backbone/transfer baseline work in issue #97.

The implemented loss/update formulas and paper attribution remain in the preceding verification handoff. Fixed uses a constant real coefficient; continuous uses a projected one-step current-Adam validation hypergradient with a frozen Source encoder/reference scale. No custom GRU cell or silent loss redesign was introduced.

## Verification and artifacts

The independent matrix verifier recomputed saved-prediction errors from authenticated complete arrived labels, required exact method/seed/target identities, matched scored origins and checked each retained tick commitment. It permits explicitly pruned historical states under latest-only retention, while checking the newest full checkpoint. Input bytes were rehashed after execution and report extraction. Runtime/source/code/config hashes are in the run bindings. Publisher raw archives were not freshly checked.

See CSV/JSON records for full precision, costs, coverage, regimes, per-day errors and trajectories; PNG/PDF figures are standalone export artifacts. Historical Source pretraining/billing totals are unknown and must not be reconstructed from update counts. Owner execution authorization does not waive the repository's merge policy.
