# Full manuscript audit — 12 November 2026

The [current reader](../../../report/overleaf-review-20261112-v3/adaptive-transfer-learning-ev.pdf)
and [editable Overleaf project](../../../report/overleaf-review-20261112-v3/README.md)
supersede v2. This audit addresses the owner's request to recheck the whole paper,
including method fidelity, formulas, comparisons, data identity and layout. It
relates to the integration candidate in PR #116; no merge is authorized.

## Verified findings and corrections

| Area | Finding and action |
| --- | --- |
| Method diagrams | V2 left target inputs disconnected, obscured the frozen-reference penalty, and made the label/forecast relationship ambiguous. Replaced it with two native vector diagrams: source/target forecasting and causal complete-label feedback. |
| Controller identity | Production code updates mixture weight `w`, not lambda. Both expert coefficients stay fixed at 1 and 0. The paper separates this method from the historical selector and failed lambda-only diagnostics. |
| Formulas | GRU gates match `ev_models/model.py` and PyTorch's reset-after-affine convention. Forecast/retention losses match the code; normalization precedes squaring, and reference/scales are frozen. Grouped equations improve indexing and typesetting without changing the algorithm. |
| Metrics and scope | Added a formal daily-vector MAE definition, seed-then-entity aggregation, null handling, named percentage denominators and distinct study scopes. No pooled cross-namespace kWh score is introduced. |
| Complete comparison | Added the omitted Fast-only component to the 21-group table. It is lowest at AMS 7/14 days, so those two bold minima now belong to Fast-only. V2 minima were correct among its four listed methods but that presentation omitted this necessary comparator. |
| Tables | Fresh source-ledger arithmetic matches existing baseline and Development values. All 105 displayed historical values match the group CSV. Twenty-eight bold numeric minima are checked at printed precision; ties share emphasis. The control table reports a different reference in each row and is not ranked as competing models. |
| Charts | Rebuilt all four retained result charts as vector assets. Removed redundant history plots from the main narrative, separated family gain from the static-mixture increment, kept denominator-specific color scales explicit, and corrected UrbanEV's year label to 2022–2023. |
| Layout | Two-column main text, full-width appendices, short captions and native equations. Full historical results and supporting plots remain present. Removed orphaned conclusion/diagnostic pages and internal drafting history. |
| References | Added the primary TimeXer paper and checked its nine-author list against NeurIPS rather than the older repository README citation. No repository members or AI tools are listed as scientific sources or contributors. |

The owner subsequently supplied a blue–white–red reference. All diagrams and
plots now use that palette family. Heatmaps retain their reduction formula and
values: blue indicates lower MAE, red higher MAE, and white zero. This is the
same favorable/unfavorable color meaning as the reference, without copying its
historical methods or numbers.

## Fresh numerical and saved-output checks

[numeric-audit.json](numeric-audit.json) independently recomputes both 172-row
baseline ledgers, all 612 history-study rows, 42 history MAE/RMSE aggregates and
147 historical group means from 810 unit rows. It retains nine null units and
67,293 scored daily vectors. The 60 paired neural transfer comparisons in each
baseline implementation favor Source initialization.

[mixture-readback.json](mixture-readback.json) records a fresh SHA-256 check of all
810 saved cell artifacts against their existing readback manifest. Independent
direct exponential arithmetic reconstructs 66,492 delayed-feedback updates,
adaptive predictions and MAEs, plus static and Fast-only MAEs. This check reads
saved labels/forecasts; it does not repeat training or independently reauthenticate
all prepared labels and model states. The previous broader artifact checks retain
their own independent/reused boundaries.

The original result counts remain: adaptive and static each beat single Fixed in
18/21 groups; adaptive beats static in 12/21 and loses nine. UrbanEV remains worse
than single Fixed at all histories. These comparisons do not establish a
successful continuous-lambda controller or universal GRU superiority.

## Attribution checks

The native GRU equations follow the [PyTorch GRU documentation](https://docs.pytorch.org/docs/2.11/generated/torch.nn.GRU.html).
The reference is a recurrence convention, not a claim that original executions
used that documentation's runtime version. The two-expert update is the
specialization of the share-to-other rule in Figure 1, equation 4 of
[Herbster and Warmuth (1998)](https://mwarmuth.bitbucket.io/pubs/J39.pdf).
Nonuniform calibrated initialization, the EV loss scale and delayed replay are
project choices. No theorem or EV-specific hyperparameter optimum is imported.

[TimeXer metadata](https://proceedings.neurips.cc/paper_files/paper/2024/hash/0113ef4642264adc2e6924a3cbbdf532-Abstract-Conference.html),
[GRU attribution](https://aclanthology.org/D14-1179/),
[L2-SP](https://proceedings.mlr.press/v80/li18a.html) and
[hypergradient attribution](https://proceedings.mlr.press/v48/luketina16.html)
were checked at primary sources. Dataset and bootstrap bibliography metadata
were checked through DOI/Crossref records. Nature's full article pages were not
accessible in this audit; that metadata check is not a fresh dataset audit.

## Publication checks and limits

All eleven final pages were visually inspected. The first two final page renders
also match the preceding inspected render exactly. [table-audit.json](table-audit.json)
records source-value, emphasis, bibliography and template checks. Original class
and bibliography-style bytes are preserved, including their existing whitespace.
All six figures have short captions with explanations in separate prose.

The final source-only ZIP is built outside Git and is independently extracted and
compiled with Tectonic 0.17.0. Matching page text and absence of overfull boxes or
unresolved references are required. The Overleaf web editor is not run. Ordinary
underfull spacing warnings are not suppressed. Exact publication identities are
recorded in the project artifact manifest.

Unknown or unverified: full training reproduction, newly downloaded publisher
archives, physical-site independence, physical issuance chronology, complete
end-to-end compute accounting, untouched-test generalization, and scientific
peer/style acceptance. Local software and arithmetic checks do not resolve these
limitations. No dataset, checkpoint, historical reader or frozen Report 1 output
is overwritten.
