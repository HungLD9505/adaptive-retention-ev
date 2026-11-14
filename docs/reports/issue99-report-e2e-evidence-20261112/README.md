# Report integration and E2E evidence review — 12 November 2026

**Scope:** integrate the approved native flow into the current report and review
its claims against executed code, locked protocols and saved results. No method
change, search, model training, new Later matrix or untouched-test result.
The review continues PR #116 into `dev`; it does not merge or update `main`.

## Deliverables

- [Current 16-page reader](../../../report/rebuilt-review-20261112/adaptive-transfer-learning-ev.pdf).
- [Readable claim register](claim-evidence.md), [filterable CSV](claim-evidence.csv)
  and [full paragraph/source/hash register](claim-evidence.json).
- [Primary-reference check and retrieval limits](literature-check.md).
- Fresh receipts: [ledger arithmetic](ledger-readback.json),
  [independent saved-mixture replay](saved-mixture-readback.json),
  [additional numerical checks](supplementary-checks.json),
  [displayed tables/PDF](report-audit.json), [source ZIP rebuild](package-check.json),
  [check execution](checks.json).

The register covers **101 prose entries and 26 labeled equations/tables/figures**
against **71 source files**. Each entry has the actual manuscript text/location,
claim type, verified/inferred status, evidence paths and an interpretation limit.
This is a source-coverage record with manual method review, not a claim that
file existence automatically proves every sentence. Engineering choices are
identified as such; motivation and causal explanations remain interpretations.

## Corrections and integration

Figure 1 is the approved native, flat TikZ flow on page 3. Vehicle symbols,
connectors, labels and formulae remain editable LaTeX paths/text. Both expert
GRUs receive history; known future calendar bypasses the encoder to the head.
The frozen source reference supplies the stable penalty. Saved expert forecasts
are scored only with complete earlier labels, and weight/model updates apply
to subsequent forecasts. It updates forecast weight **w**, not retention **lambda**.
The historical bootstrap lambda selector remains a separate figure/method.

The E2E review found an overbroad recipe description: the three-epoch target
schedule, batch four and learning rate 0.0005 apply to **nonspatial neural**
baselines. GCN–LSTM uses five initial epochs, learning rate 0.001 and single-example
steps. Classical fitting/refitting remains method-specific. The report now
states this distinction, supported by both baseline configurations and graph
training code. Numerical results were not changed.

The discussion now calls nonstationarity and local-gradient mismatch **possible
reasons**, avoiding an unsupported causal explanation of the observed losses.

## Recomputed results and their denominators

| Comparison | Fresh recorded-result check | Interpretation |
|---|---:|---|
| Source initialization versus target-only neural baselines | 60/60 paired cells in each implementation | Four entities, three seeds and five neural families per implementation; fixed recipes |
| Calibrated Source fine-tuning versus target-only | 33.35%, 31.64%, 29.80% MAE reduction | Twelve Development entities at 7/14/28-day prefix |
| Original confidence lambda selector versus fixed-one | 9/21 lower group means | Fixed is lower in 12; not the fusion method |
| Adaptive two-GRU fusion versus single Fixed | 18/21 lower group means | All 18 CHARGED groups; all three UrbanEV groups worsen |
| Matched static fusion versus single Fixed | 18/21 lower group means | Much of the broader win count exists without online weight adaptation |
| Adaptive versus matched static fusion | 12/21 lower, 9 higher | Small, mixed incremental weighting benefit |
| Continuous lambda versus calibrated Fixed Later | 4.806223 versus 4.803054 kWh | Continuous is worse; retain registered Later objective |
| Persistent lambda promotion | Fails; no Later execution | Favorable Calibration gain is only 0.000118478 kWh |

Group counts are namespace–history comparisons, not independent cities,
stations or significance counts. The historical cohort was already inspected.

Fresh arithmetic recomputed both 172-row baseline ledgers, all 612 Development
rows and 810 historical units (including nine null units), then matched the
reported aggregates. All 810 external cell files were rehashed; independent direct
exponentials reconstructed **66,492 consumed feedback events** and
**67,293 scored 24-hour vectors per mixture arm**, including adaptive weights,
predictions and errors. The same readback checked 52,376 GRU and 65,368
same-head LSTM parameters.

Additional checks covered all 21 measured fixed coefficients, three representative
gradient points, 60 four-target Later method cells, 12 transcribed persistent
Calibration rows, 18 original finite intervals containing zero plus three
undefined UrbanEV intervals, and 142 recorded trace rows. The upper-median example
selection reproduced JHB entity 13 and UrbanEV entity 1272.

## Commands and observed verification

Code basis before these manuscript-only edits:
`7d0e47d1d904b8ba8656b9292db516055533847f`.
The main suite ran on that clean checkout, as its provenance fixture requires.
No model/controller/test/fixture file was changed by this review.

| Check | Result |
|---|---|
| `python -m unittest discover -s tests -v` | 1,041 tests; PASS; 12 skips; 37.041 s |
| `python -m unittest discover -s experiments/fixed_adaptation -v` | 9 tests; PASS |
| `python -m unittest discover -s experiments/confidence_controller -v` | 12 tests; PASS |
| `python -m tools.check_release` | PASS; 17 frozen report assets and 92 historical source pins |
| `python -m tools.sources list` | PASS; catalog listing only, no archive verification |
| `python -m ruff check .` | PASS |
| `python -m ruff format --check .` | PASS; 671 files already formatted |
| Tectonic 0.17.0 compile and extracted source ZIP compile | PASS; 16 page texts match |
| PDF/table review | 52 baseline display cells, 21 historical rows, five Later rows and seven Development rows match; bold minima checked |
| PDF content/layout | Seven vector figures, two native TikZ flows, zero embedded rasters; no overfull boxes, unresolved references or missing characters |

Ordinary underfull box warnings remain. The PDF is not described as warning-free.
All sixteen pages were rendered again. Changed pages and the flow were inspected;
byte/pixel comparison against the approved previous render is in the package receipt.
The archive compiles locally from its extracted inputs; the Overleaf web UI was
not exercised. No separate type checker is configured; external-artifact tests
and fresh expert retraining were not rerun.

Run directory (outside Git):
`/Users/quyenmanh/Developer/TFL-EV/runs/issue99-report-e2e-20261112-v10/`.
It retains scripts, full logs, renders, the source ZIP, extracted recompilation
and the audit bundle. Script identities are recorded in `checks.json`.

## Verification limits

**Verified:** code/formula correspondence within the reviewed methods, recorded
recipe identities, numerical aggregation, saved-mixture bytes and arithmetic,
source package compilation and documented layout checks.

**Inferred:** reasons for choosing a competitive compact GRU, source/fast
complementarity and possible explanations for adverse controller outcomes.
These are supported interpretations, not new causal experiments.

**Unknown/not re-executed:** raw-publisher archive authenticity, physical issuance
clocks, a full independent retraining replication, every historical bootstrap
draw, equal end-to-end compute and an untouched prospective test. Baseline A's
previous private saved-output/label audit and baseline B's unchanged-ledger audit
remain reused, not fresh private-checkpoint audits. Persistent Calibration cells
are documented transcriptions of Kaggle output; their fresh aggregation does not
turn them into locally authenticated training artifacts. Retrieval limits for
three publisher full texts are recorded in the literature check.
