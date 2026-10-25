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
