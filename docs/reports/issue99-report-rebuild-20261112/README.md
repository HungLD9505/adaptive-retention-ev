# Evidence-based report rewrite — 12 November 2026

## Delivered change

The owner clarified that the request was to rewrite the report from completed
results and evidence, not choose or implement another research method. The new
[reader](../../../report/rebuilt-review-20261112/adaptive-transfer-learning-ev.pdf)
and [Overleaf project](../../../report/rebuilt-review-20261112/README.md) replace
the current-reader links. Existing reports, raw inputs, checkpoints, run outputs,
methods and scoring windows are unchanged.

The report is rebuilt around the problem, data/availability protocol, standard
GRU and loss, fixed-coefficient calibration, retention controllers, two-expert
fusion and their separate results. All 21 historical group means appear in the
main results. The expanded 21-coefficient experiment has a new vector figure
showing measured forecast error and encoder-gradient ratios, with the zero
reference and selected measured coefficient. Its sampled behavior is not
misrepresented as continuous regime boundaries.

Eight figures comprise three native TikZ flows and five vector plots. Equations
are native LaTeX. Captions remain short and explanations stay in the body.
Blue-white-red comparison colors follow the owner reference. Table minima are
bold within the stated scope. Scientific references contain no repository-member
or assistant contributor entries. No generic page titles, Studio publishing
instructions or conversational authoring text are introduced.

## Evidence identity and conclusions

The report preserves all of these outcomes:

- Source fine-tuning lowers the calibrated twelve-entity Development MAE by
  29.8–33.4% versus target-only training.
- GRU is competitive; implementation B's official TimeXer is lower. Universal
  GRU superiority is not claimed.
- The original historical confidence-gated lambda selector beats Fixed in 9/21.
- The separate common-bank confidence selector loses to its calibrated Fixed
  comparator at 7/14 days and wins at 28 days.
- Four-target discrete Later MAE is 4.798259 versus Fixed 4.803054; continuous
  hypergradient is worse at 4.806223. Unequal tuning/training budgets are explicit.
- Immediate/persistent coefficient updates have favorable means in their separate
  Calibration execution, but persistent fails its promotion criterion. No Later
  values are invented.
- Historical adaptive and static fusion both beat single Fixed in 18/21;
  adaptive beats matched static in 12/21. All three UrbanEV groups still favor
  single Fixed. The update changes forecast weight w, not retention lambda.
- On the additional twelve Development entities at fourteen days, both fusion
  rules remain worse than single Fixed. The unexecuted seven/twenty-eight-day
  fusion cells on this cohort are not filled from historical results.

The report is an exploratory synthesis, not a new untouched test result. Its
limits distinguish metric/file verification from training reproduction and fresh
publisher-archive authentication.

## Verification

[report-audit.json](report-audit.json) records the source hashes and checks:
52 baseline display cells, 21 historical rows, five Later rows and seven
Development rows match their full-precision ledgers. Best-value formatting and
all four historical win counts were independently checked. The reader has
16 pages, eight figures, three native flows and zero embedded raster images.
Compilation has no overfull boxes, undefined references or missing characters;
ordinary underfull justification warnings remain. Every final page was visually
inspected, or is byte-identical to a page already inspected during this rewrite.

The source-only ZIP has 15 entries. It was extracted into a fresh directory and
compiled separately; its page text matches the delivered reader. Local Tectonic
verification is not a claim that the Overleaf web editor was used. The original
class and bibliography-style bytes are unchanged.

External delivery and QA root:
`/Users/quyenmanh/Developer/TFL-EV/runs/issue99-report-rebuild-20261112-v4`.
It retains the source ZIP, compile logs, page PNGs, numerical audit and plotting
scripts. The PDF and source assets are versioned; large QA files remain outside
Git. The source manifest binds every delivered report asset and evidence input.

README checks: Fixed adaptation 9/9, confidence-controller 12/12, Ruff lint and
format, source catalog listing, and frozen release checks (17 assets / 92 source
pins) passed. The first root-suite run executed 1,041 tests with 12 skips and one
provenance error: the proxy-calibration fixture rejects nonempty Git worktree
status, and the new report files were then uncommitted. The failure condition was
confirmed in `tools/hung_proxy_calibration.py`; no test, fixture or validation
rule was weakened. A clean-checkout rerun is recorded below after the report
commit. No separate type checker is configured and the external-artifact suite
was not rerun for this documentation change.

No PR is merged and neither `dev` nor `main` is modified by publication on the
existing review branch.

## Clean-checkout verification and publication

At report commit `45a9de0e477b90a29fc75f9fcae90629f0f6636f`, the clean-checkout
root suite ran 1,041 tests in 42.133 seconds: PASS, with 12 documented skips.
This confirms the earlier failure was the dirty-worktree provenance gate; no
implementation, test expectation or fixture was changed. This final receipt is
an additional documentation-only commit.

The final source ZIP SHA-256 is
`300e328141fafaab9c273922d913083fdc4a73b6e8ebc764a49cfdb603a69e6a`.
All source-manifest asset and evidence hashes were rechecked. After the final
source whitespace cleanup, all 16 rendered page PNGs were byte-identical to the
visually inspected reader. The extracted final ZIP rebuilt matching page texts
with no overfull boxes or unresolved references. The source class/style retain
their original whitespace; other added/changed files pass `git diff --check`.

Publication uses the existing `chore/99-integration-review` branch and
[PR #116](https://github.com/HungLD9505/adaptive-retention-ev/pull/116) to `dev`.
Latest-head CI and peer approval remain separate from these local checks. The
reader is a review artifact; no merge is performed.
