# Issue #39: varying-day controller comparison

**Status:** reproducible synthetic diagnostic, not a controller-method decision, Development result, or independent peer approval. No real dataset, model weights, training, Final targets, or previous run artifacts were read or changed for this comparison.

## Inputs and provenance

The comparison was run on 2026-10-26 using the two independently authored controllers already submitted for review:

| Component | Git revision read | File SHA-256 |
| --- | --- | --- |
| Hung `experiments/hung_sprint2/controller.py` | `e85a53cd02deaa3a3440df8c6922eb679773801b` (#46 head) | `42ebc1c308569e41ca404c34af1c96daff509db3f6bf4544c6b95a4cbb158c2f` |
| Qyroven `ev_control/confidence.py` | `83b877e16e7e690d93bb1f7736ce1870ef08fadd` (#52 documentation head; controller bytes match its pinned dependency) | `27b8d7709fc07442cc4461082e4d6599108ed70591f4398c5c60a3d60e6f36a` |

The read-only comparison used Python 3.13.7 on Windows. Neither controller requires a GPU or dataset for this calculation. The [bounded component comparison in #52](https://github.com/HungLD9505/adaptive-retention-ev/blob/83b877e/docs/reports/implementation-comparison-readiness.md) already records identical GRU encoder outputs under shared weights, equal retention loss/target gradients, and four **constant-score** controller cases. Those cases do not cover a varying-day lower bound.

Both controllers received levels `(0.0, 0.1, 0.2)`, active level `0.0`, block 0 with 14 complete days, `Bmin=5`, `delta=0.0`, overall `alpha=0.05`, moving segment length 2, 100 resamples, seed 7, and two-challenger Bonferroni adjustment. Daily normalized MAEs, in level order, were generated for `i=0..13` by:

```text
(2.0,
 1.8  + 0.3 * ((i % 5) - 2),
 1.75 + 0.3 * ((i % 7) - 3))
```

Every day was marked as issued, arrived, and complete. The Qyroven helper also received a synthetic midnight origin, an available-at timestamp one day later, distinct prediction IDs, a fixed scale ID, and a decision time after day 14. No future score was passed before that boundary. The Hung helper received matching day IDs and complete-score flags. The fixture in `tests/test_hung_controller.py` pins Hung's current result so an implementation change cannot silently rewrite this diagnostic.

## Observed decisions

| Implementation | LCB for λ=0.1 | LCB for λ=0.2 | Next level |
| --- | ---: | ---: | ---: |
| Qyroven | −0.025535714285714307 | −0.061249999999999964 | **0.0 (keep)** |
| Hung | +0.007142857142857102 | −0.07142857142857138 | **0.1 (switch)** |

The output is reproducible under the exact pinned source bytes and fixture inputs above. It does not establish that either implementation is statistically preferable or incorrect. Their lower bounds use different bootstrap random-stream derivation and empirical-quantile conventions: Qyroven uses linear interpolation, while Hung uses the order statistic at `ceil((alpha/2) × R) − 1`. Different resampled means and quantile extraction can move a marginal LCB across strict `LCB > δ`. A previous constant-score fixture could not expose this difference.

## Review decision still required

Before #39/#20 integration, the co-leads and an independent reviewer must choose and document one bootstrap RNG and quantile convention using Report 1 and Development-only methodological criteria, then add a varying-day regression to the selected shared implementation. Compare both controllers again with identical resampled day indices if the team needs to isolate the quantile rule from RNG. Reconcile the separate head-topology and training-config differences recorded in [comparison readiness](https://github.com/HungLD9505/adaptive-retention-ev/blob/83b877e/docs/reports/implementation-comparison-readiness.md) before interpreting model-score gaps. Do not select a convention because it makes Adaptive's Development or Final score look better; do not relabel old training outputs or merge both implementations unchanged.

No review has been submitted on #42–#46, #47, #49, #50, or #53 at this check. This fixture is additional evidence for review, not acceptance, merge authority, or a claim that #39 is complete.
