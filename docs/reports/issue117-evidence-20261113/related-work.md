# Direct related-work comparison

Sources were inspected on 13 November 2026. This is a focused comparison, not a
systematic review or an exhaustive novelty search. Reported accuracies are not
ranked across datasets. None of these papers was added as a newly executed baseline.

| Work | Task/data budget | Mechanism | Scope difference |
|---|---|---|---|
| Narayana Gowda et al., Energy Systems 17:347–366 (2026; online 2024) | Aggregate EV load; 10/20 target days | Transfer and MAML | Direct limited-data precedent; different forecast/evaluation scope |
| Zafar et al., Energy and AI 21:100545 (2025) | Next-day load profiles; 98 target training days | Cluster-specialized BiLSTM transfer | Longer target budget and source specialization |
| Ali et al., arXiv:2409.11862v1 (2024) | Charging-site forecasts; two-week/month target histories | Multi-quantile TCN with inductive transfer | Forecast intervals are different from a paired method-contrast interval |
| Wang et al., IEEE TPWRS 40(2):1241–1254 (2025) | EV demand; target-history budget not established from accessible abstract | MMD clustered federated Transformer transfer | Different privacy/training architecture; abstract-level comparison |
| Qu et al., TRD 136:104470 (2024) | Charging demand with reduced training-data fractions | LLM representation and meta-learning | Different representation/compute; relevant few-shot comparison |

## Primary evidence locators

- Narayana Gowda: [publisher full text](https://link.springer.com/article/10.1007/s12667-024-00682-8), Introduction and Methods. The publisher specifies a 2026 issue and first online publication in June 2024; the bibliography preserves both.
- Zafar: [institution-hosted publisher PDF](https://scholars.cityu.edu.hk/ws/portalfiles/portal/311744873/305320127.pdf), sections 2–3 and Table 3. Publisher HTML returned 403; the deposited version identifies itself as the published PDF.
- Ali: [author preprint](https://arxiv.org/html/2409.11862v1), sections IV–V. Preprint status and version are explicit.
- Wang: [author-institution publication record](https://scholars.cityu.edu.hk/en/publications/domain-adaptive-clustered-federated-transfer-learning-for-ev-char/), abstract and bibliographic metadata. Full text and numeric target budget were not established; no unsupported training detail is imputed.
- Qu: [author-hosted paper](https://senseable.mit.edu/papers/pdf/20241023_Qu-etal_ChatEV_TR_D.pdf), abstract and few-shot experiment discussion; [coauthor copy](https://felix-rz.github.io/pdf/2024_ChatEV.pdf) confirms DOI and publication metadata.
- Dwork et al.: [original NeurIPS proceedings](https://papers.nips.cc/paper_files/paper/2015/hash/bad5f33780c42f2588878a9d07405083-Abstract.html). Supports the caution about adaptive holdout reuse, not a claim that this project implements their reusable-holdout algorithm.

## Positioning supported by this comparison

Transfer, short-history EV forecasting, meta-learning and expert-weight updates
have established precedents. The completed study evaluates the incremental value
of source-influence decisions under its specific causal protocol and matched
Fixed/static controls. This methodological distinction is not proof of a new
algorithm, an unoccupied research gap, or superiority over these papers.
