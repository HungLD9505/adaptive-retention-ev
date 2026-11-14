# Main publication audit — 14 November 2026

Issue #128. Baseline: main `0cab33388ec015992bd4d008404ab302945094ec`,
following the approved merges of #126 and #127. Editorial changes branch from
dev `eb035bccaa07b7cc4913e75a7e75b98c5afc4b0b`; its tree matches that main
snapshot. No method, result or manuscript asset changes are included.

## Review scope

The review covers the root README, documentation/evidence/report indexes,
current manuscript source and extracted PDF text, model equations, result
tables, references and the two flow diagrams. All 23 PDF pages were rendered
with Poppler and inspected in page sheets for visible layout defects. The
figure/table pages were compared with their source definitions. Rendered pages
and text remain outside Git in `runs/main-editorial-audit-20261114/`.

The root README already had no member roster. No conversational assistant
phrases, tool attribution, unresolved drafting placeholders or member lists
were found in the current manuscript sources. Historical authorship, original
reports, executed notebooks and audit records remain intact. This is not a
claim that every retained historical document is a current submission draft.

## Corrections

| Location | Finding | Correction |
|---|---|---|
| Root README | The introduction emphasized manuscript asset counts rather than research content. | Link directly to methods, experiments and uncertainty analysis. |
| Root README | “Separate contributions” could imply that every studied mechanism improves accuracy. | Describe separate controls used to assess the mechanisms. |
| Root README | “Numerical-scale wins remain qualified” did not explain the issue. | State that four identifier-level differences are approximately 1.43 × 10⁻⁹ kWh and have no practical significance. |
| Root README | “Exposed” and “progression gate” were unexplained shorthand. | Use “previously evaluated” and describe the criterion for further evaluation. |
| Root README | Dataset reuse, computational fairness and artifact availability were combined into one limitation. | State their distinct implications for generalization, cost comparison and reproduction. |
| Documentation/report indexes | Administrative wording obscured the scientific entry points. | Use direct descriptions of the linked methods, results and evidence. |
| Issue #96 benchmark README | Personal-name heading and stale pending-review statements. | Use a study title and link the recorded approval/merged integration, preserving the exploratory scope. |
| Issue #125 handoff | Preparation text still stated that main had not been promoted. | Append the verified promotion outcome while preserving the dated preparation record. |

## Scientific consistency

The current manuscript distinguishes a training coefficient, lambda, from
forecast mixing weights. It reports the original selector's 9/21 historical
wins separately from adaptive fusion's 18/21 wins against Fixed. Matched static
fusion also wins 18/21, and adaptive wins only 12/21 against static. The
46-identifier evaluation retains both intervals containing zero and the failed
dual-comparator criterion. The bounded weighting study retains AdaHedge's
higher MAE than Fixed and its stopping decision. These statements agree with
the linked evidence and remain unchanged.

The GRU recurrence and latent-loss expressions remain native equations. Figure
titles are separate from explanatory paragraphs; the inspected comparison
tables emphasize the lowest displayed MAEs within their declared scopes.
No obvious text/arrow collisions or table clipping were observed in the page
renderings. The abstract remains dense and some tables use small type; these
are presentation limitations, not newly established scientific errors.

## Verification and limits

- All 46 asset/evidence SHA-256 entries in the current manuscript manifest match.
- All 108 local file links in the six reviewed landing/handoff documents resolve.
- Root README has no member roster or assistant attribution.
- Main's post-merge Foundation checks passed on baseline commit
  `0cab33388ec015992bd4d008404ab302945094ec`: [run 43584468530](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/43584468530)
  completed successfully on Ubuntu and Windows.
- Relevant local check outcomes for the editorial commit are recorded in its PR.

The PDF and its complete source package are unchanged. No new training,
external-artifact replay, raw-archive download, fresh literature verification
or scientific confirmation was performed. This audit checks presentation and
consistency with the retained evidence; passing it does not strengthen the
reported statistical conclusions. For the six Markdown files at `65409f7`, the
project owner recorded a one-time waiver of additional peer review in
[PR #129](https://github.com/HungLD9505/adaptive-retention-ev/pull/129); current-head
Ubuntu and Windows CI passed before #129 and #130 merged. The waiver does not
apply to later changes or replace the repository's ordinary review policy.
