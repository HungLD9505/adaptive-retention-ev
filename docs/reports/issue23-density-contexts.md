# Development prefix load-density thresholds

Issue #23 / PR #52. CPU metadata analysis only; no training or forecast-outcome selection. This implements a review proposal for Report 1 sparse/dense context analysis. It is not a Final lock or a change to the controller, cohorts or model inputs.

Density is the fraction of valid initial-prefix hours with positive energy. The threshold is the equal-entity median among all ready Development entities in the same namespace/budget. Sparse is strictly below the threshold; dense includes ties. Missing hours are excluded and coverage stays explicit. A completely tied population can leave one group empty.

| Namespace | Budget | Ready Dev with density | Median | Sparse | Dense | Tied | Undefined |
|---|---:|---:|---:|---:|---:|---:|---:|
| charged-AMS | 14 | 475 | 0.997024 | 230 | 245 | 10 | 0 |
| charged-AMS | 28 | 475 | 0.998512 | 236 | 239 | 85 | 0 |
| charged-AMS | 7 | 475 | 1.000000 | 224 | 251 | 251 | 0 |
| charged-JHB | 14 | 8 | 0.907738 | 4 | 4 | 0 | 0 |
| charged-JHB | 28 | 8 | 0.902530 | 4 | 4 | 0 | 0 |
| charged-JHB | 7 | 8 | 1.000000 | 3 | 5 | 5 | 0 |
| charged-LOA | 14 | 51 | 0.821429 | 25 | 26 | 1 | 0 |
| charged-LOA | 28 | 51 | 0.803571 | 25 | 26 | 1 | 0 |
| charged-LOA | 7 | 51 | 0.815476 | 25 | 26 | 2 | 0 |
| charged-MEL | 14 | 14 | 0.870536 | 7 | 7 | 0 | 0 |
| charged-MEL | 28 | 14 | 0.869048 | 7 | 7 | 0 | 0 |
| charged-MEL | 7 | 14 | 0.776786 | 7 | 7 | 0 | 0 |
| charged-SPO | 14 | 8 | 1.000000 | 3 | 5 | 5 | 0 |
| charged-SPO | 28 | 8 | 0.998512 | 4 | 4 | 0 | 0 |
| charged-SPO | 7 | 8 | 1.000000 | 3 | 5 | 5 | 0 |
| charged-SZH | 14 | 288 | 1.000000 | 54 | 234 | 234 | 0 |
| charged-SZH | 28 | 288 | 1.000000 | 60 | 228 | 228 | 0 |
| charged-SZH | 7 | 288 | 1.000000 | 48 | 240 | 240 | 0 |
| urbanev-SZH | 14 | 296 | 0.824405 | 147 | 149 | 3 | 0 |
| urbanev-SZH | 28 | 301 | 0.818182 | 150 | 151 | 1 | 0 |
| urbanev-SZH | 7 | 294 | 0.808871 | 147 | 147 | 0 | 0 |

These are Development-defined descriptive groups, not physical charger occupancy, energy magnitude, behavioral ground truth, or a reason to remove all-zero sites. CHARGED publisher preprocessing still limits interpretation. Groups and thresholds differ across budgets/cities, so these are not causal history-budget or geographic comparisons. No Final values or online forecast scores are used to fit thresholds. Grouped forecast-error aggregation is still pending after the matched GPU collection completes.

Reproduction: `python -m tools.development_contexts --inputs-root PATH_TO_ACCEPTED_INPUTS --output NEW_OUTPUT.json`. The full local output contains each eligible Development entity’s density and valid-hour count; large metadata output stays outside Git. The attached compact registry records all namespace/budget input/metadata fingerprints and the full output checksum.

Executed code: `3e34bebd4cac0ec5ff197d868d6c37b84c651d84`. Full local output SHA-256: `686c9adf4b56d834787f98dd47d80059e214b7d57192bc4e0778c02a13ef0393`. All 21 accepted namespace/budget manifests and entity-metadata fingerprints passed. 286 offline tests, Ruff lint/format and diff checks passed locally; Kaggle currently runs the earlier pinned training commit and its 281-test validation. No training code changed.
