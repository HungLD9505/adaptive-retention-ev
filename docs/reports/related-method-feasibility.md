# Related-method feasibility — Issue #22

Checked 2026-10-26 against primary author/publisher sources. This is an interface and
resource feasibility assessment, not an executable reproduction or novelty claim.
The nine mandatory internal baselines remain required regardless of these findings.

| Related method | Verified primary material | Fit to the current study and disposition |
|---|---|---|
| BOTL | [Author paper](https://wrap.warwick.ac.uk/id/eprint/137446/) and [author repository](https://github.com/hmckay/BOTL) describe bidirectional transfer and ensemble/model selection; the repository documents SVR/RR learners. | A direct comparison needs multistream transfer, model-sharing/culling and a 24-output regression adapter under an explicitly matched budget. It is not the current fixed-Source GRU retention procedure. Public implementation located; environment/data compatibility and an adapted experiment were not executed. |
| R-Tuning | [AAAI paper](https://ojs.aaai.org/index.php/AAAI/article/view/40010) and [official code](https://github.com/Ivan-YinTY/R-Tuning) describe wavelet-based generated replay and latent consistency for pretrained time-series adaptation. | Requires its replay/generation machinery, pretrained model/checkpoint choice, dataset adapter and separate replay cost accounting. Source latent retention alone is not an R-Tuning reproduction. Source/code located; no compatibility install or reproduction executed. |
| GUARD | [Author preprint](https://arxiv.org/abs/2606.19363) and [linked author repository](https://github.com/RupasreeDey/GUARD-KDD2026) concern multi-foundation-model routing and uncertainty-gated distillation. | Requires identified foundation-model teachers, routing/distillation and their compute budgets. Our three-seed GRU dispersion proxy is not GUARD. Paper/repository located; checkpoint acquisition, code completeness and execution compatibility remain unverified. |
| PADRE | [IJCAI proceedings](https://ijcai.org/proceedings/2026/503) describe a historical Pattern Bank, delayed-residual/context/memory views and a learned continuous update gate. | Would need a causally fitted bank, delayed-feedback adapter and gate-training budget. Our load-descriptor threshold policy is not PADRE. Paper available; no author code link was found in the checked proceedings page, which is not proof that no implementation exists elsewhere. No reproduction executed. |
| Hyperon | [Author manuscript](https://minkull.github.io/publications/TabassumDSAA2025.pdf) and [university publication record](https://research.birmingham.ac.uk/en/publications/hyperon-an-online-hyperparameter-tuning-approach-for-data-stream-/) describe online steady-state evolutionary hyperparameter search. | A 24-step GRU comparison needs regression objectives, a genotype/search space and explicit population/update costs. A three-level mean selector is not Hyperon. Paper available; code/runtime compatibility and an adapted study remain unverified. |

These methods need separate reviewed adaptations before numerical comparisons.
No score from a different horizon, output family or task is reported as comparable
24→24 EV accuracy. No external code has been incorporated into the independently
authored implementation. Locating a repository does not establish reproduction,
license compatibility or resource feasibility. Preserve these limits in the thesis.
