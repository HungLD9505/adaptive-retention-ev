# Hung #22 Without Source Initialization ablation

This draft ablation changes the target **weight initialization** only. Its
target GRU/calendar/head is constructed from the same architecture with a
declared seed instead of copying the city's Source weights. The Source
checkpoint is still required and fingerprinted: it supplies the frozen
reference encoder and Source-only latent scale for the unchanged latent
retention loss. The target uses the same permitted initial Development prefix,
24→24 forecast task, scaler, complete-label gates, three candidate forks,
confidence rule, block schedule, isolated audit and measured per-candidate
costs as the main method. No city/dataset pools its Source weights with
another. This isolates transfer initialization rather than conflating it with
the one-model Target-only baseline, which has no Source reference or
three-candidate controller.

`--initialization-kind random_target` is explicit for `target-smoke` and
`replay-development`. The target checkpoint payload and manifest bind the kind,
seed and SHA-256 of all named initial model tensors before prefix adaptation.
Replay reconstructs the seeded random initial model and verifies that digest;
it also verifies Source checkpoint, target prefix/input binding, target lambda
and frozen Source latent scale. The replay config and resume manifest bind the
initialization kind and digest. Legacy Source-initialized checkpoints remain
readable as Source initialization, but cannot be relabeled as this ablation.
The Source-initialized path also checks its newly recorded initial tensor
digest against the bound Source checkpoint.

`development_no_source_initialization_proposal_v1.json` changes only status
and target/replay initialization kind from the existing Development proposal.
The lambda, seed list, 7/14/28-day histories, update settings and controller
are unchanged. This is a method proposal for independent review, not an
approved Final lock. It must be evaluated on real Development entities and
matched origins under the full accepted matrix; a fixture score or code path
does not establish effectiveness. Related Source training and all three
candidate/audit costs remain actual costs of this ablation, rather than being
assigned Target-only's cheaper one-model cost.

Offline regressions verify same-seed reproducible random weights distinct from
the Source, frozen Source reference, empty initial optimizer, checkpoint and
manifest provenance, same-origin uninterrupted/split-resume parity and rejection
of a jointly rewritten false initial model digest. The config fixture rejects
unintended tuning differences. No raw data, CHARGED/UrbanEV real training,
Final labels or old artifacts were accessed or changed for this tranche.

This branch is stacked on PR #59 head `4453944`; sibling PRs #60 Seasonal,
#61 Parameter Retention/block-size and #62 proxy calibration must be reconciled
into one reviewed integration path. The required real Development comparison,
finite calibration, complete seeds/budgets/cities, measured feasibility,
independent peer acceptance, immutable Final lock, Final execution and report
handoff remain open.
