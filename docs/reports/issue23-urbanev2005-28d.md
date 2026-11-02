# UrbanEV2005 — three-seed28-day Development case

All14 variants and fixed seeds42/43/44 have externally accepted daily/input,
latest-state and Source evidence through publications02/03. The42 runs share the
same90 scored origins (90 scheduled/issued), fixed input/scaler, actual Colab
runtime and unchanged core implementation. Sources are the original frozen
three-seed epoch10 weights; no refitting or seed selection was performed.

| Method | Mean seed MAE,kWh |
|---|---:|
| Adaptive |4.860253|
| Fixed Retention |4.811535|
| Full Fine-tuning |4.788682|
| Online Best |4.816429|
| Target-only |7.636828|
| Seasonal Naive |8.843982|

Adaptive's mean seed MAE exceeds Fixed by0.048718kWh. It is also worse than
Full Fine-tuning and Online Best here, while outperforming Target-only and
Seasonal Naive descriptively. This is one predeclared Development entity-budget;
it is not a station-population estimate, significance test, causal Source-quality
experiment or Final result. Source/model/controller RNG vary together.

The [reproducible analysis](https://drive.google.com/file/d/1arEFBb1ElEsN_M-0yzhMPYD8OxbFKZ9w/view)
contains per-seed metrics for all14 methods, exact input/evidence pins, shared
origins, scripts, PNG/SVG and a member manifest.115,877bytes, SHA-256
`7957287a73f514474fd8b3e50ec9c60fe332ebe19973de84e7dd3967bdec2e67`.
Fresh authenticated native Drive readback matched bytes/hash, ZIP CRC and all6
manifest members. The chart was rendered and visually inspected. Analysis used
the plotting environment separately from the CPU artifact verifier; no local
training was performed. All adverse comparisons remain explicit.
