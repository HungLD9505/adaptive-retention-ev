# Issue #99 unified integration review candidate

**Status: prepared for team and peer review; not merged into dev or main.**
The branch starts at dev `dffd16a0b37df336330ef9b9d23056facd388681`.
No experiment was rerun or relabelled as execution of the integrated code.

## Current reader manuscript

The [Overleaf-style PDF](../../../report/overleaf-review-20261112-v2/adaptive-transfer-learning-ev.pdf)
and [LaTeX project](../../../report/overleaf-review-20261112-v2/README.md) are the
current reader version. The original two-column template now includes the new
stable/fast GRU pipeline, native LaTeX equations, short figure titles and eight
scientific references. Figure explanations are separate body paragraphs.
Numerical tables and result plots are unchanged. Prior Word layouts and the
11 November artifact identities remain historical snapshots.

## Integration snapshot references

1. [Current manuscript PDF](../../../report/teacher-review-20261111/source-retention-review.pdf)
   and [editable Word file](../../../report/teacher-review-20261111/source-retention-review.docx).
2. [Manuscript, baseline audits and scientific limitations](../issue99-teacher-review-20261111/handoff.md).
3. [Integration inventory](integration-inventory.json): exact included heads and local checks.
4. [Persistent lambda follow-up](../issue99-persistent-results-20261111.md): the
   recorded Calibration promotion gate failed; this arm is preserved as a negative result.

## Included work

The following 14 open PR heads are all ancestors of this candidate. Local merges
preserve author history; they do not merge or approve the GitHub PRs.

| PR | Pinned head | Scope |
| --- | --- | --- |
| [#115](https://github.com/HungLD9505/adaptive-retention-ev/pull/115) | `d88a9765974a` | docs: deliver verified baselines and complete expert-fusion review manuscript |
| [#114](https://github.com/HungLD9505/adaptive-retention-ev/pull/114) | `ecbc4595a961` | feat(benchmark): Huu Duc independent 172-row UrbanEV results and report (#96) |
| [#113](https://github.com/HungLD9505/adaptive-retention-ev/pull/113) | `a0550f3d5cb9` | feat(issue99): evaluate λ-only persistent controller on Kaggle (gate failed) |
| [#112](https://github.com/HungLD9505/adaptive-retention-ev/pull/112) | `8cf00ee3ca48` | research: evaluate expert fusion across the full historical EV cohort |
| [#110](https://github.com/HungLD9505/adaptive-retention-ev/pull/110) | `7e9b0249e7ef` | research: test stable-fast GRU fusion against strong Fixed retention |
| [#109](https://github.com/HungLD9505/adaptive-retention-ev/pull/109) | `671ce224fbf0` | feat: calibrate training across history budgets and deliver review manuscript (#99) |
| [#108](https://github.com/HungLD9505/adaptive-retention-ev/pull/108) | `d7ce1f3c9c35` | feat: measure transfer benefit and isolate confidence-gated selection (#99) |
| [#107](https://github.com/HungLD9505/adaptive-retention-ev/pull/107) | `8c7a5126c31f` | feat: verify retention on twelve additional Development stations (#99) |
| [#106](https://github.com/HungLD9505/adaptive-retention-ev/pull/106) | `6e74aee1c9a3` | feat: compare selective latent retention and encoder L2-SP (#99) |
| [#105](https://github.com/HungLD9505/adaptive-retention-ev/pull/105) | `1e95551c989d` | feat: diagnose paired retention controller decisions (#99) |
| [#104](https://github.com/HungLD9505/adaptive-retention-ev/pull/104) | `1e4c8e17ecbf` | feat(baselines): complete independent UrbanEV benchmark (#95) |
| [#102](https://github.com/HungLD9505/adaptive-retention-ev/pull/102) | `71234eb1b217` | feat: complete and verify fixed/continuous retention study |
| [#101](https://github.com/HungLD9505/adaptive-retention-ev/pull/101) | `aaf863e84fd4` | fix: make retention tests reproducible and record verified pilot evidence |
| [#100](https://github.com/HungLD9505/adaptive-retention-ev/pull/100) | `c33c6228c7f7` | feat: audit Source10 and prototype continuous retention for #99 |

## Conflict resolution and compatibility

- Kept the independent Source10 audit, source/seed lineage, full-horizon and tick
  checks from #102, alongside #100's canonical protocol/config bindings.
  Trusted audit validation runs before the protocol's own Source declaration.
- Kept both registered diagnostic profiles: the historical `diagnostic_every`
  and the nested `diagnostics` profile. Scored execution must bind its chosen
  profile to its protocol; specifying both is rejected. The two diagnostic
  implementations have distinct import names and event types. Their existing
  nonmutation/resume tests pass. Generic Store test bindings may carry a string
  identity instead of a full config; that does not enable legacy diagnostics.
- Kept the immediate controller, #113's persistent shadow controller and the
  source/target-only history-study extension. Persistent execution remains
  explicitly versioned and bound to its locked controller rule.
- The historical `issue99-execution-protocol-v1` archive retains its original
  identity checks. The later `issue99-protocol-v1` requires canonical phase,
  scorer and Source declarations. Old records are not rewritten to pretend
  they were produced with a new code identity.
- Combined the independent security regression tests; temporary fixtures use
  ordinary isolated temporary directories rather than requiring `.cache`.
- Preserved the union of artifact byte rules in `.gitattributes`, both baseline
  submissions, executed-code snapshots, and all earlier report evidence.

## Scientific reading

Verified manuscript scope is the historical 810-unit, 21-group comparison.
The new two-GRU Fixed-share mixture beats historical Fixed in 18/21 groups;
a static blend also wins 18/21. Dynamic sharing beats that static blend in
12/21 groups. These are different comparisons. They do not establish that a
lambda-only controller wins 18/21, or that the adaptive effect explains the
whole improvement. UrbanEV remains adverse in the full-scope comparison.
The baselines support GRU as a practical backbone; they do not establish a
universal GRU winner. Source3 baseline and Source10 retention recipes are distinct.
The additional persistent lambda pilot and Calibration matrix are exploratory
Development evidence; the failed gate did not authorize a Later matrix.

The PDF/DOCX and all 32 manuscript manifest entries are byte-identical to #115.
No fresh data download, new long training, new Final run or raw-archive check was
performed during integration. Prior audit receipts keep their stated boundaries.

## Local validation

At implementation commit `c243748bfe34dfbe919c0bf27587f92b340562fc`:

- Root suite: 1,041 tests, passed, 12 skips: three CUDA checks, eight optional
  classical-baseline dependency checks, one unavailable identified 14-day input.
- Fixed-adaptation suite: 9 passed; confidence-controller suite: 12 passed.
- Focused issue99 suite: 115 tests, passed, two skips (included in root suite).
- Ruff lint and format passed across 654 Python files; `git diff --check` passed.
- Source catalog listed; release checker preserved 17 report assets and 92
  historical source pins. Listing/checking pins is not a fresh upstream download.
- All 14 listed PR heads passed ancestry checks. All 32 manuscript artifact
  entries passed byte-length and SHA-256 checks.

No separate type checker is configured. CPU fixture tests do not establish
research effectiveness. CI for the new PR and peer approval must be inspected
on that PR; these local results are not a claim of CI completion.

## Review and eventual promotion

PR #104 and #114 had `CHANGES_REQUESTED` at the inventory snapshot. Carrying
their work here does not resolve those reviews. A peer other than the author
must approve this candidate and CI must pass before any authorized merge.

Some inherited Python modules exceed 500 lines, including the integrated
continuous-run entry point, comparison regression suite and persistent experiment,
report and verifier. They retain concrete protocol/verification flows and
independent regression cases. Keeping their history reviewable is the reason
for avoiding a mechanical split in this integration; reviewer agreement on
these existing sizes remains required.

After team review, any dev merge needs the repository's normal peer approval.
Updating main requires a separately reviewed promotion and explicit instruction.
Do not close covered PRs/issues or delete active branches before actual integration
and acceptance; preserve unpublished branches and unmerged work.
