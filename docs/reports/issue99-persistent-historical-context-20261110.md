# Historical context for the lambda-only follow-up

These tables are read from preserved repository reports. They are not new
experiments and do not demonstrate an improvement by persistent_v1.

## PR 102: registered 14-day Development later window

Source: `docs/reports/issue99-study-20261110/method-summary.csv`, inherited from
dependency commit `302fb6b00a190c788ba3ffd81268ace52a151e8a`.

| Method | Later macro MAE, kWh |
| --- | ---: |
| Lambda zero | 4.868597443 |
| Fixed | 4.803054026 |
| Historical discrete controller | 4.798258890 |
| Immediate continuous controller | 4.806223253 |
| Frozen lambda control | 4.803054026 |

The immediate continuous controller was about 0.003169 kWh worse than Fixed.
Fixed used lambda 0.7984450067079901. The follow-up must reproduce the registered
Calibration baseline and compare true forecast trajectories; a better shadow
forecast alone does not establish a better deployed controller. A zero-acceptance
controller may equal Fixed and still fail the registered 0.01 kWh gain criterion.

## Historical Final tables referenced in the earlier discussion

Source: `report/full-results.csv`, UrbanEV-SZH, 29 scored entities. The original
Final protocol remains locked. These are separate history budgets, not arms of
the four-target Development follow-up.

| Initial history | Historical adaptive MAE, kWh | Fixed retention MAE, kWh | Adaptive minus Fixed, kWh |
| --- | ---: | ---: | ---: |
| 7 days | 8.101369308 | 8.039986092 | +0.061383216 |
| 14 days | 8.051655280 | 7.975750984 | +0.075904297 |
| 28 days | 8.001464231 | 7.915858941 | +0.085605290 |

Lower is better. The historical adaptive method did not beat Fixed in these
reported macro rows. Different entities, windows and method settings prevent
using their absolute MAE difference from PR 102 as evidence of improvement.
No Final run was repeated for this follow-up. The 7/28-day extensions remain
future research, not unreported completed results.

## Prior small screen

`issue99-wide-paired-screen-20261110.md` preserves the earlier three-case null
screen, including paths and settings. It used a different proposal/acceptance
variant. The new persistent mean-gate method is a distinct fixed hypothesis;
its outcome must come from its own immutable Kaggle artifacts. No threshold
will be changed to rescue an unfavorable Calibration outcome.
