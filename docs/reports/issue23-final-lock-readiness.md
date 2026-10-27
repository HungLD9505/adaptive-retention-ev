# Issue23 — Final lock readiness (not approved)

Executed October27,2026 ICT. This handoff inventories the remaining lock gate;
it is not a competing schedule, a chosen Final cohort or permission to evaluate.
Task tracking stays in #23 and the sole schedule stays in `SPRINT_PLAN.md`.

## Frozen Development choices available for review

The identified primary Development summary SHA-256 is
`ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6`.
It selects Source duration10 epochs; initial adaptation3 epochs; online1 epoch;
batch64, learning rate0.001 and retention epsilon0.001. The controller uses
levels0/0.1/1, starts at0.1,14-day blocks, Bmin7, delta0, alpha0.05, three-day
bootstrap segments and2,000 draws. Seeds42/43/44 are paired replications, not
winner candidates. Fixed Retention uses lambda1. The frozen proxy recipe indices
are Source-error1, Uncertainty1, Drift3 and Parameter Retention2. Fourteen unique
variants retain all required main/baseline/ablation categories through explicit
Without Confidence→Online Best and Fixed lambda→Fixed Retention aliases.

These are existing Development selections, not independently approved Final
settings. Full configs, estimator mappings, analysis/context definitions, actual
Source identities and all limitations must be reviewed together, not inferred
from these abbreviated numbers. No new configuration search is authorized by
this handoff. Current point estimates do not establish Adaptive superiority.

## Metadata-only population inventory

The actual accepted21 input manifests/entity summaries were authenticated using
`InputRun`. No Final forecast, training or label JSONL records were decoded;
training files were hashed as opaque bytes. The full ID/manifest/clock/Source-
population inventory remains outside Git on
[Drive](https://drive.google.com/file/d/1-imvDibNds7asZguLDvnEI7fQytHNu3W/view),
SHA-256 `8a6d71cb881c14e86cf3315d1561076e7273e218adba960f2fc633ddfb023b07`.
The independently rerunnable inventory script is retained with that local run.

| Namespace | Ready Final IDs,7d | 14d | 28d |
|---|---:|---:|---:|
| UrbanEV SZH |340|341|345|
| CHARGED AMS |478|478|478|
| CHARGED JHB |13|13|13|
| CHARGED LOA |41|41|41|
| CHARGED MEL |15|15|15|
| CHARGED SPO |10|10|10|
| CHARGED SZH |271|271|271|

There are3,510 ready entity-budget pairs, including35 with no initially trainable
prefix samples. All-ready coverage at three seeds and14 unique variants would
require147,420 target replays, plus the identified Source models and complete
verification/storage/analysis. This is a population count, not a committed cohort,
a runtime prediction or a reduced experimental design. Budgets can contain
different IDs. No future activity/outcome was used to choose a favorable subset.
Any bounded Final cohort requires an explicit outcome-blind declaration and review;
it cannot be silently substituted to satisfy a compute deadline.

## Gates still open

- Complete/reverify the primary artifact recovery and six-city Development scope.
  SPO/MEL raw-runtime access remains unresolved; their cached logs are not a
  portable full handoff. Other city execution remains explicit in #23.
- Preserve runtime fairness: after Colab termination, the authenticated new-runtime
  plan retains16 complete old units (224 selected cells) and replays all14 methods
  for53 incomplete units (742 cells:212 selected-proxy plus530 matched). This
  includes documented repeats; it is not742 lost outputs. Choices/weights stay
  frozen. Do not mix environments within paired station/budget/seed units. See the [exact replay/queue evidence](issue23-primary-recovery-plan-evidence.json).
- Declare the actual Final cohort, source checkpoint identities, measured total
  compute/storage envelope, complete configs and analysis/profile hashes.
- Implement/review Final-capable execution and independent verification under a
  fail-closed lock/approval gate. Existing Development-only readers/verifiers
  must not be silently relabeled or bypassed. No Final execution was attempted.
- Obtain independent immutable code/config/data/cohort/analysis approval before
  opening Final for the locked algorithm. A hash or an author's prepared JSON
  is not peer approval. Correctness changes after lock require reviewed relock
  and affected reruns, not selection of favorable old/new results.
- Verify complete outputs, independent reproduction and #10 report handoff before
  declaring Sprint3 done. Negative/null findings are valid; missing required
  evidence is not completion.

## Outcome-blind cohort candidate for later review — not selected

The all-ready147,420-cell inventory has no accepted compute envelope. A concrete
bounded alternative can be prepared for review using the existing Development
cohort rule applied to Final entity metadata: for each separate namespace and
7/14/28-day budget, sort ready positive-prefix IDs by initial_trainable and an
identity hash; partition rank positions into three equal-count bins; take the
hash-minimum ID in each nonempty bin; add one hash-minimum no-initial-trainable
ID when present. Hash payload is the JSON array
`["final-three-prefix-rank-bins-plus-one-empty-proposal-v1", manifest_sha256,
[dataset,city], budget, entity_id]` with compact separators. This exact rule is
recorded before executing the candidate selection. It does not inspect any
forecast/label records, energy values, post-deployment activity, missing-label
counts, errors, zero fractions, or outcomes. Prefix counts/readiness/IDs only.
All methods/ablations, three seeds, budgets and seven separate namespaces remain
in the candidate; CHARGED SZH stays separately reported. Empty target prefixes
retain their existing initialization policy. No city is silently removed.

This is a proposal, not an amendment or permission to run Final. The actual IDs,
manifest/Source-population identities and cell count will be exported for review.
A small cohort weakens station-level inference and cannot be called a population
validation. Its limitations must be accepted explicitly or a larger/all-ready
cohort selected by the lead/reviewers. No Final evaluation may start merely
because this candidate is feasible or its JSON has a checksum. Complete
Development evidence, actual Source/config/code/analysis identities, Final-capable
interfaces and independent lock approval remain required. This handoff does not
change the sole sprint schedule or create a competing execution plan.

The rule-predeclared metadata-only candidate was executed after commita825ff4.
It contains66 entity-budget pairs and2,772 three-seed/fourteen-variant cells:
UrbanEV4 IDs per budget (three positive-prefix and one empty-prefix); every
CHARGED city3 per budget. All seven namespaces and three budgets are represented.
The [candidate, script and log](https://drive.google.com/file/d/1EbuB8A2iB1ZMhTgHzgQC2cYjGFvZtKJU/view)
ZIP is9,349 bytes, SHA-256
`1fe4665d998e9e8d89275712512046c086f02aab98b5dc6bdf30f02ffca7cbb0`;
actual fresh Drive readback, ZIP CRC and every manifest member hash passed.
Candidate JSON SHA-256 is
`b1202774d85f24540ade9d2f8024c9a63e9284a537eeef5a719a7a9041cb2703`.
No Final value records were decoded. There is still no cohort selection or
independent Final-lock approval; PR52 review submissions were empty at inspection.
A three-positive-site sample per budget has limited station-level inference,
and budget groups can have different IDs. The all-ready147,420-cell inventory
remains an alternative; the candidate cannot silently replace it. No measured
Final capacity or Source/config/code/analysis lock is claimed.

### Static-coordinate review risk; candidate unchanged

A metadata-only audit of the unchanged66-pair candidate uses only station/site
identity and coordinate columns plus prefix-trainable Source IDs. Publisher
aggregate activity columns are ignored. Exactly one candidate entity-budget pair
shares numeric coordinates with a trainable Source: UrbanEV14-day Final ID2155
and Source ID2154. No Source coordinate is missing in this audit. Equal coordinates
do not prove identical stations, time series or leakage; nonmatches do not prove
geographic independence. The candidate was not reselected or silently filtered.

The [audit/script and unchanged candidate](https://drive.google.com/file/d/1-taZc84doswZeKHlag1ZmzzuZjXLNhJI/view)
ZIP is12,971 bytes, SHA-256
`2fb694edacded8e34b382bd0dc7b2aacbaee82f4bea9c542dc124448ecf26353`;
fresh Drive download/CRC/all member hashes passed. No Final forecast/training/label
JSONL values were decoded. Review must distinguish unseen author IDs from physical
site independence before approving claims. A scope-choice question is pending
with the lead; it does not authorize Final or amend the method. Development work
continues independently.


## AMS Source optimization risk identified before lock

All three fixed AMS Source checkpoints are technically verified and retained.
A one-input Development diagnostic observed near-zero outputs and Softplus
derivatives for seeds42/44, but not43. Source normalized training MAE also
varies materially across these seeds. See the durable recovery report and
linked diagnostic proof for exact checkpoint/input/metric identities.
This is not evidence for dropping seeds or silently changing initialization,
head, loss, or training duration. Complete the frozen Development comparisons,
report seed sensitivity/negative transfer, and explicitly review this risk
before Final approval. A proposed method change requires separate review and
a new lock; checkpoint validity alone does not establish useful pretraining.
