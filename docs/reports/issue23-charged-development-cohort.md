# CHARGED supplementary Development cohort declaration

Issue #23 / PR #52. Before any new CHARGED results, declare an outcome-blind small
cohort for all six separate cities and all 7/14/28-day budgets. This is a concrete
execution cohort, not a second schedule or a Final cohort. CHARGED remains
supplementary and publisher-processed; Shenzhen must be analyzed separately for
possible UrbanEV overlap. Strict upstream online causality remains unproven.

`tools.charged_development_cohort` authenticates the earlier six-city smoke matrix
against its independent verifier and derives each city/budget's input fingerprint
from those actual bindings. Recheck each complete input manifest/training/entity
fingerprint, split roles, prefix metadata, common Source population and declared
publisher-local-naive clock with the current hardened input reader. No raw bytes,
processed data or accepted input artifacts are modified.

Within each city/budget, take ready Development entities only. Sort positive
initial-trainable counts, break count ties by the fixed SHA-256 of the rule ID,
manifest, namespace, budget and entity ID, then divide that ordered population
into three equally sized rank bins. Choose the smallest hash in each nonempty
bin. Even when every count ties, three distinct identities are selected if at
least three are eligible. These are count-rank bins, not asserted behavioral
clusters. If any ready entity has no initial trainable sample, select one of those
by the same fixed identity-hash order as an explicit separate stratum. Small/empty
bins are reported; never invent or silently duplicate an entity.

The selection never reads forecast errors, future activity, energy outcomes or
full-release zero flags. Zero-energy observations remain valid; no all-zero site
is deleted. Metadata/byte hashing does not decode Final training or label arrays.
Keep the original split salt and roles; do not choose a new salt or favorable seed.
The three paired comparison seeds remain 42/43/44, with 90 scheduled days.

The output contains a separate city cohort JSON and an inventory of code/version,
source/input identities, runtime, exact rule, eligible populations, selected
strata, hashes and unfilled bins. These files define small nonrandom Development
cohorts; they cannot establish population generalization or Final performance.
They also do not authorize new cross-dataset pretraining: every city's Source
model must train only on its own allowed Source population. Reusing a primary-
Development hyperparameter recipe is different from reusing UrbanEV model weights.

Actual supplementary experiment matrices, frozen recipe identities, cost
feasibility and results remain to be executed/reported. If a required city/budget
has no ready Development target, the declaration fails rather than silently
removing that scope. No Final run, independent lock, merge or acceptance follows
from creating these metadata files.

## Status

273 local fixture tests pass with Ruff lint/format/diff checks. The rule is being
committed before real cohort generation; real output identities/counts are not yet
claimed. CPU-only metadata/fingerprint verification is permitted locally; no local
real-data model training occurs. This extends the accepted six-city supplementary
scope and preserves all documented preprocessing/time/overlap limitations.

## Actual metadata-only execution

Committed rule code `b96d75f6bb08306cedf35496e50d86a7251f18e0` generated
`runs/issue23-charged-cohort-20261026-v1` by CPU-only metadata/byte verification.
No training or forecast outcomes were read. [Inventory and identities](issue23-charged-cohort-inventory.json)
and the six cohort files in `configs/issue23/charged-cohorts-v1/` are the actual
outputs. All 18 budget inputs passed their recorded fingerprints and Source/clock
checks. No city/budget was dropped.

| City | Ready Development IDs per budget | Selected IDs per budget | Initial trainable counts, 7/14/28d | Empty prefixes |
|---|---:|---:|---|---:|
| AMS | 475 | 3 | 6 / 13 / 27 | 0 |
| JHB | 8 | 3 | 6 / 13 / 27 | 0 |
| LOA | 51 | 3 | 6 / 13 / 27 | 0 |
| MEL | 14 | 3 | 6 / 13 / 27 | 0 |
| SPO | 8 | 3 | 6 / 13 / 27 | 0 |
| SZH | 288 | 3 | 6 / 13 / 27 | 0 |

This gives 54 entity-budget combinations and 162 paired seed units. Counts tie
within each budget, so rank bins are identity-hash tie partitions, not different
coverage/behavioral regimes. Selected IDs differ across budgets; compare methods
within each budget and do not interpret cross-budget mean differences as a causal
history-budget effect. All-zero energy sites remain eligible. These are
trainable-window counts, not evidence of physical station activity or upstream
unimputed observations.
