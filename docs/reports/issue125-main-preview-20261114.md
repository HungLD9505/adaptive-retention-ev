# Reviewed integration and repository presentation — 14 November 2026

Issue #125. The project owner explicitly authorized merging the four reviewed
research PRs into `dev` and preparing the repository presentation for a future
`main` promotion. Main has not been modified by this task.

## Integrated research snapshot

| PR | Reviewed head | Merge into dev |
|---|---|---|
| #118 | `af9112bf9896021e111ee77527009d8e165b0384` | `1d26e67b6206d6cab1260a4f14fa73d8a7ef6d5a` |
| #120 | `017341ab0965d3d4d56f0688c1e81aebcc7185a6` | `e43bbbc67df23c52b07b98dadcffb88be52a1640` |
| #122 | `5399050f2ca8aff9b21e59b57e402bd13942f829` | `e7d3a7a3f702ee967b4f639f632f57e19c7d1f7a` |
| #124 | `8c3dedd623ce66b2abc4f036c42d8771e7f19e2e` | `fc52e07f6574386826572fb74b79692d16193e85` |

Before every merge, the exact head, peer approval from HungLD9505, successful
Ubuntu/Windows CI, `dev` target and clean merge state were checked. Merge commits
preserve contributor/execution ancestry. After each merge, the reviewed head
was verified as an ancestor and the entire resulting dev tree matched that head.
The final merged tree is identical to the approved `8c3dedd` snapshot.

Issues #117, #119, #121 and #123 are closed as completed evidence tasks. The
failed confirmation/progression criteria remain failed scientific outcomes.
Their closure does not assert model superiority. PR/issue description links
were converted to reviewed commit permalinks before deleting the four completed
remote/local branches. Active worktrees and unrelated branches remain intact.

## Presentation scope

Only the root README, documentation index, evidence index, report index and this
handoff change. The landing page uses the exact manuscript title, prominent
PDF/source/evidence/data links, protocol overview and a five-study findings table.
Retention selection and forecast fusion remain distinct, with positive and
adverse results and explicit evidence boundaries. The indices link the current
23-page manuscript first and retain historical reports.

The manuscript PDF remains byte-identical to the reviewed version:
`136ad772ad368e36fe98d401f3a331ce2a5d95f0fc0858ce72dd7f06b59c7240`.
All manuscript assets and evidence fingerprints were rechecked. No code, data,
model, execution lock, numerical result or manuscript/source asset is edited.
There is no new experiment or assistant contributor attribution.

## Preview and verification

- 106 local Markdown/HTML links resolve; the reproduce anchor is present.
- GitHub's GFM API renders the new README. An isolated headless-browser preview
  was inspected for the title, navigation and findings-table layout. It uses a
  GitHub-style container and existing SVG; it is a presentation preview, not a
  screenshot of the live main branch.
- Render inputs, HTML and PNG remain outside Git under
  `runs/issue125-main-preview-20261114/`. The existing SVG bytes are unchanged.
- The repository README documents the complete offline checks. Their final
  outcome is recorded in the PR after the clean-checkout run.

Main was `17823b38bcc75bb2dbfb1ff527fb4bd8fa7ec49d` at preparation. The
[main comparison](https://github.com/HungLD9505/adaptive-retention-ev/compare/17823b38bcc75bb2dbfb1ff527fb4bd8fa7ec49d...ab1bca2f39ee4234369f75bacb2e47c3c9b251c7)
shows the complete proposed contents; the documentation PR targets dev. Review
and promotion are separate from the already completed research merges. No main
merge, new tag or release is performed by this handoff.

## Completed validation and review

On clean presentation commit `ab1bca2`, the root suite ran **1,081 tests**,
with **12 skips and no failures** in 41.277 seconds. Fixed-adaptation (9),
confidence-controller (12), Ruff lint/format (704 files), source listing, release
and diff checks passed. The existing optional-dependency/CUDA/input preflight
skips are retained; no expected fixture/hash is changed. The post-merge dev CI
run at `fc52e07` completed successfully.

A read-only three-way merge preview against the recorded main head completed
without conflicts and produced the exact presentation tree. Main is not an
ancestor of this branch, so later promotion should preserve both histories
through the normal reviewed merge rather than assume a fast-forward. No main
ref was written. Subsequent closeout text changes do not alter the landing page,
frozen manuscript, code or numerical evidence.

Presentation PR: [#126](https://github.com/HungLD9505/adaptive-retention-ev/pull/126),
targeting dev, with HungLD9505 requested as reviewer. The commit-bound comparison
above preserves the tested layout snapshot even after working-branch cleanup.
The reviewed main presentation can be checked before any promotion decision.
