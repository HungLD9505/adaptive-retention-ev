# Manuscript figure revision — 2026-11-12

The current reader is [the revised manuscript](../../../report/overleaf-review-20261112-v2/adaptive-transfer-learning-ev.pdf), titled *Adaptive Transfer Learning for Cold-Start Electric Vehicle Charging Demand Forecasting*.

The revision replaces the method flow with an illustrated source, target and causal forecast-weight update pipeline. The calibration plot now compares initializations on a shared MAE scale. The history plot separates the transfer benefit from incremental retention gains. Figure captions remain short and interpretation stays in body paragraphs.

All four table bodies and twelve display equations match the preceding reader after removing bold formatting. Twenty-eight best comparable MAE cells were independently checked at displayed precision: minima per implementation/mode column in Table 2, per history column in Table 3, and per namespace/history row in Table 4. No experiment or scientific result changed. `table-best-cells.json` records the highlighted cells; `chart-values.json` preserves the values and transformations behind the revised plots.

All twelve rendered pages were inspected. Tectonic 0.17.0 compiled both the project and an extracted source-only upload ZIP without overfull boxes or unresolved references. Ordinary underfull spacing warnings remain. The Overleaf web editor itself was not run. The project artifact manifest records source, figure and ZIP hashes. The illustration was produced with built-in Imagegen, corrected for causal direction and complementary weights, and checked against the method equations; its prompt is kept with the external delivery bundle.

No training or new raw-archive download was performed. Research limitations and unfavorable results remain visible. This revision does not authorize merging the integration PR.
