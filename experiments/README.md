# Experimental implementations

| Package | Purpose |
|---|---|
| `supporting_pipeline/` | Alternate end-to-end GRU, retention, replay, baselines and evaluation implementation |
| `fixed_adaptation/` | Bounded source training and fixed-model target adaptation diagnostics |
| `confidence_controller/` | Diagnostic online candidate and confidence-controller replay |

The primary pipeline remains in the root `ev_*` packages. These implementations
retain separate configurations and validation boundaries; scores are not pooled.

Names identify function rather than author or sprint. Current Python imports,
module CLI commands and source-identity collection use these package paths.
Read each package's technical README/configuration before execution.

## Historical reproduction

Original source paths were `experiments/hung_sprint2`,
`experiments/member_studies/duc_retention`, and
`experiments/member_studies/cyber_controller`. They remain available at
`archive/pre-experiment-paths-20261102` and their original execution commits.
Frozen JSON/CSV evidence, lock hashes and notebook snapshot bytes are unchanged.
Recorded fingerprints describe their original source layout, not a rerun of this
checkout. Historical notebooks may contain old file paths: use the identified
historical checkout to reproduce those saved executions. Current Python CLIs use
the new names. No new training is performed by this migration.

An import-only legacy alias supports immutable pinned readers without rewriting
their source/hash. It does not remap filesystem paths or validate old locks against
changed source. Existing checkpoints, data and result bytes remain untouched.
