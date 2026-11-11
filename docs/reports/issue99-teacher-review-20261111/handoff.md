# Baseline verification and integrated teacher review 11 November 2026

## Delivered scope

The owner's request was to finish baseline verification, integrate the new
controller formula, full results and visuals into the teacher-review paper, and
publish the work to Git for the joint retention owners. This handoff relates to
#99 and depends on PR #112. It does not merge any implementation or replace the
frozen primary report.

The new review version is [here](../../../report/teacher-review-20261111/README.md):
eleven pages, twelve equation images with maintained LaTeX, six scientific figures,
a complete 21-group result table, and full-precision group/unit CSVs. The Word
body and tables remain editable. The PDF is produced from that same Word file.

## Baseline evidence now verified

Cyber reviewed head: `3d6847b4e043ec6b7b5cbcf4c544e50225b794f7`, PR #104.
The current release `v0.9.5-cyber-benchmark-v3` was downloaded completely before
checking it: 47,124,280 bytes, SHA-256
`5edbea2fe6a4e12d4f4236da9913032ec2848ba9fa885cbb38d4d4cea6f7a2b0`,
valid ZIP CRC. A read while the download was still in progress initially found
an incomplete file; that was not treated as a publisher artifact mismatch or a
completed audit. The completed archive is retained outside Git.

Reviewer-side code independently checked all 367 manifest entries and sizes,
13 executed source-file identities, and byte equality of the bundle ledger and
manifest with the current committed evidence. All 172 per-run metrics were
recomputed from 10,535 scored forecasts / 252,840 hourly predictions; ground
truth matched authenticated prepared labels exactly. Within each station, all
methods have the same scored origins. All 147 tensor files load with
`weights_only=True` and finite tensor values. Classical joblib files were hashed,
not deserialized. The exports do not provide physical issuance timestamps;
current complete-arrival eligibility and the submitted causal code were checked,
not independently proven physical execution chronology.

The archive's executed classical-model code predates the current optional
SARIMA-dependency guard. This post-execution code difference is explicit rather
than misrepresented as the executed source. Current Ubuntu/Windows CI passes in
run [42859382487](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42859382487).
Missing prospective tuning/protocol scope acceptance and the custom attention
substitution remain separate from artifact/metric correctness; this handoff does
not approve or close #95.

Duc reviewed head: `ecbc4595a9616f7a7fa42679e595947d3832f6d5`, PR #114;
PR #111 is superseded pilot history. This task recomputed all 172 ledger rows into
station-equal summaries. The current ledgers, session and executed notebook are
byte-identical to audited revision `a2a7b6d`. Therefore the existing published
[737-file reviewer readback](https://github.com/HungLD9505/adaptive-retention-ev/pull/114#issuecomment-6783698688)
is reused with explicit attribution; this task does not claim another download
or independent reexecution of those 737 files. That audit verified all daily
metrics, label eligibility, common origins, Source bindings and 147 finite tensor
checkpoints. Current CI passes in run
[42950550735](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42950550735).
The explicitly recorded fixed-recipe exploratory scope decision is preserved;
this task neither approves a merge nor closes #96.

Audit outputs: [baseline-verification.json](baseline-verification.json),
[provenance](baseline-provenance.json), [Cyber means](cyber-summary.csv),
[Duc means](duc-summary.csv), [reused receipt](duc-reused-audit-receipt.md).
The audit script is `tools/issue99_baseline_review.py`.

GRU transfer is 5.3150 kWh in Cyber and 5.3157 in Duc, but Duc's official TimeXer
is lower at 5.1979. The manuscript therefore supports a compact competitive GRU
control rather than declaring a universal winning backbone. Cyber's materially
different attention adapter is explicitly labeled as custom. Both benchmark
recipes use three Source epochs, unlike the primary Source10 retention study;
absolute errors and author implementations are not pooled.

## Controller evidence and additional controls

The main 810-unit experiment is preserved: Fixed-share beats the original Fixed
in 18/21 groups versus 9/21 for the original selector, but the same calibrated
static ensemble also wins 18/21. Adaptive weights improve on that static control
in 12/21. Three UrbanEV groups remain adverse.

The review adds two posthoc diagnostic controls without new training or parameter
selection: constant 50/50 blending, and a loss-free sharing update with identical
initial weight/arrival clock/alpha but posterior equal to prior. This removes the
loss feedback while retaining the pull toward half weight. All 810 source cell
hashes were checked against the existing independent artifact manifest. The
adaptive method is below both controls in all 21 group means, with reductions
of 0.00084–0.263% against equal weights and 0.00097–0.227% against sharing alone.
These are small, descriptive, posthoc increments; no significant or large
independent controller effect is claimed. Results and code identities are in
[fusion-controls-summary.json](fusion-controls-summary.json) and
[fusion-controls-groups.csv](fusion-controls-groups.csv).

The paper clarifies that the original historical selector reforks models every
fourteen days. The seven-day readbacks only select among that archived causal
forecast stream; they do not execute seven-day reforked model training. Those
shadow-comparator semantics do not change any saved scores or the independent
stable/fast fusion trajectories.

## Visual and artifact checks

Figures show independent backbone results, target-training calibration, matched
history comparisons, all 21 groups against Fixed, incremental effects against
three fusion controls, and actual weight/cumulative-error traces. The two traces
use a documented median-station-gain rule and seed 42, with both a favorable
namespace and an adverse one. They are examples, not a population effect.

Every page was rendered and visually inspected. After a reference-only edit,
pages 1–10 were byte-identical PNGs to those inspected; changed page 11 was
inspected again. The equations, tables, figures, footers and references were
readable with no clipping/overlap. Twelve equation images and six figure images
match the DOCX's eighteen inline objects. The delivered PDF has eleven pages.
Full structural, numeric and hash checks are recorded in `artifact-checks.json`.

Large archives, states and QA page images stay outside Git. No raw archive was
modified, freshly downloaded or rechecked upstream. The manuscript and all
scientific figures are versioned; no unreviewed change is made to Report 1,
`dev` or `main`. Validation results and the published PR are recorded below.
