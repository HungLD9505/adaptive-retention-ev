# Research snapshot: contents and limitations

This repository contains the primary 24→24 forecasting implementation, separate
supporting/diagnostic implementations and the report's identified evidence.

| Location | Contents |
|---|---|
| `ev_inputs`, `ev_models`, `ev_control`, `ev_runner` | Prepared-input contracts, GRU and losses, retention selection and causal replay |
| `ev_baselines`, `ev_evaluation`, `tools`, `configs` | Comparisons, analysis, verification utilities and versioned settings |
| `experiments/supporting_pipeline` | Alternate end-to-end implementation and bounded three-station evaluation |
| `experiments/fixed_adaptation`, `experiments/confidence_controller` | Fixed-adaptation and confidence-controller diagnostics |
| `report` | Exported report/supplement PDFs, original LaTeX source, figures and result tables |
| `docs`, `tests` | Technical contracts, vector diagrams, provenance and validation fixtures |

Raw/input data, environments, trained checkpoints, large runs and preview/build
outputs are stored outside Git. Superseded operational records remain available
through the [archive index](docs/ARCHIVE_INDEX.md).

## Evidence boundaries

- The primary frozen Final covers 810 units and 11,340 method cells, with null
  outcomes retained. Complete end-to-end runtime/memory/billing information is
  unavailable; missing or lost compute is not inferred from update counts.
- The alternate implementation's 360-job evaluation covers three stations. Expanded
  cross-city execution and full independent private-artifact reproduction are not
  established. Physical-lineage limitations remain explicit.
- The CPU fixed-adaptation study records 152 artifact and 49 checkpoint checks.
  A verified distribution link for its reported 23,035,669-byte bundle is unavailable.
- Diagnostic-controller IO guards are fixture-tested. Its historical scores are
  not outputs of the corrected IO version; corrected-code real-data results remain
  unverified.
- Source-based and adaptive-selection benefits are distinct. These results do not
  establish universal Adaptive superiority, full cross-implementation equivalence
  or a calibrated guarantee of future switch benefit.

## Reproduction identity and verification

Original primary scientific source: `evidence/primary-final-20261027-v2`, commit
`61c32328d9829a69037dca629f727b4863015122`. The 92 tracked frozen pins match that
historical source; later verification/metadata changes have a separate identity.
Existing run bytes, cohorts, seeds, source references and numerical results are
not replaced by the current checkout.

Run `python -m tools.check_release` for an offline source/package check. It verifies
report-source bytes, original tracked source pins, preserved source history and
excluded tracked-storage paths. It does not download missing artifacts, train,
compile PDFs or establish scientific effectiveness. Eighteen external-artifact
checks require original files and are separate from the offline fixtures.

The exported PDF identities are recorded in `report/verification.json`. Offline
checks do not constitute remote CI success or independent scientific approval.
See the [evidence index](docs/reports/README.md) for results and validation records.
