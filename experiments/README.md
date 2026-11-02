# Experiment modules

| Package | Purpose |
|---|---|
| `supporting_pipeline/` | GRU training, retention policies, chronological replay, job dispatch and result verification |
| `fixed_adaptation/` | Source pretraining, fixed-λ target adaptation and fixed-model forecast evaluation |
| `confidence_controller/` | Candidate-model updates and confidence-based switch/keep experiments |

The primary pipeline remains in the root `ev_*` packages. These implementations
retain separate configurations and validation boundaries; scores are not pooled.

Each package provides its own model/configuration or execution entry points.
Python imports and module CLI commands use the package paths listed above.
Read each package's technical README/configuration before execution.

## Reproducing recorded executions

Original source paths were `experiments/hung_sprint2`,
`experiments/member_studies/duc_retention`, and
`experiments/member_studies/cyber_controller`. They remain available at
`archive/pre-experiment-paths-20261102` and their original execution commits.
Frozen JSON/CSV evidence, lock hashes and notebook snapshot bytes are unchanged.
Recorded fingerprints describe their original source layout, not a rerun of this
checkout. Historical notebooks may contain old file paths: use the identified
historical checkout to reproduce those saved executions. Current Python CLIs use
the new names. Changing package paths does not reproduce or revalidate recorded numerical results.

An import-only legacy alias supports immutable pinned readers without rewriting
their source/hash. It does not remap filesystem paths or validate old locks against
changed source. Existing checkpoints, data and result bytes remain untouched.
