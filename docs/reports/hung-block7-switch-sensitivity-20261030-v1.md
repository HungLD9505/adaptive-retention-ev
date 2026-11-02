# Development old-policy switch sensitivity by station

This create-only analysis reads the [87-row switch audit](hung-block7-switch-effect-20261030-v1/switches.csv) by its exact SHA-256 `0b863d2fce6d6f95b701ffd24a40999061d3158c405a482fe077b3dca9f0527b`. The [machine summary](hung-block7-switch-sensitivity-20261030-v1.json) keeps the 55 historical Block7 and 32 Main switches separate. It checks unique run/decision IDs, paired-score arithmetic, missing-score status and the run ID's budget, seed and station before aggregating. It does not access Final outcomes or change the frozen method.

Main has **28/32** evaluable switches in **20 runs across six stations** and **352 paired scored next-block days**. The old-policy audit has lower mean next-block MAE after **19/28** evaluable switches. The switch-weighted mean difference (selected minus old-policy audit) is **+0.2713 kWh**; averaging the six station-specific switch means equally gives **+0.1452 kWh**. These are two descriptive summaries of the same observed switches, not estimates from 28 independent stations.

| Station | Evaluable switches | Old-policy lower | Mean selected minus audit MAE (kWh) |
| --- | ---: | ---: | ---: |
| 1153 | 3 | 1 | −0.0399 |
| 1165 | 3 | 3 | +0.3059 |
| 1405 | 12 | 10 | +0.5263 |
| 2005 | 3 | 2 | +0.1249 |
| 2264 | 5 | 3 | +0.0669 |
| 2472 | 2 | 0 | −0.1128 |

Station 1405 contributes **10/19** old-policy-lower switches and **12/28** evaluable switches. Omitting it leaves **9/16** old-policy-lower switches and a switch-weighted mean difference of **+0.0801 kWh**. Thus the adverse direction survives this deletion but its magnitude falls substantially. By history budget, the observed fractions are **8/11** (7 days, two stations), **6/9** (14 days, two stations) and **5/8** (28 days, three stations). These budget cells have different station sets and repeated runs, so they cannot be compared as independent or balanced budget effects.

The old-policy audit is a saved counterfactual branch after a switch, not a randomized intervention. Station, seed, run, block and scored day are nested or repeated units. Four Main switches have no paired scored next-block day. This analysis makes no confidence interval, p-value, causal decision-error claim or Final-old-policy claim. Historical Block7's **26/55** old-policy-lower count remains subject to its separate run-admissibility review.

Reproduce from the repository root:

```sh
python -m tools.hung_block7_switch_sensitivity_v1 --output docs/reports/hung-block7-switch-sensitivity-20261030-v2.json
python -m unittest tests.test_hung_block7_switch_sensitivity_v1 -v
```

The command writes create-only; use a new output path when reproducing and compare its bytes with the published JSON. No prior artifact is overwritten.
