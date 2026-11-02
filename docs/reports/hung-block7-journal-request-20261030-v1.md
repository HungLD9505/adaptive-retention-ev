# Exact Block7/Main event-journal request — 30 October 2026

The [create-only 138-row request CSV](hung-block7-journal-request-20261030-v1.csv) (SHA-256 `38295dade44c779b381cd7b54fe7983699c688754e597d88ede50c1e1127fc02`) lists each historical Block7 and paired Main `events.jsonl` SHA and its intended filename in ignored `.cache/block7-journal-import-v1/`. It is derived only from the pinned coverage and 138 locally copied, SHA-verified run manifests. The original absolute paths remain in the ignored coverage record; they are not published in the CSV.

The [byte-stage verifier](../../tools/hung_block7_journal_stage.py) currently reports **0/138 verified, 138 missing, 0 mismatched**, with no unexpected staged file. A repository-local scan found no matching SHA among 130 direct `.jsonl` files or 1,196 `events.jsonl` members in 45 ZIP archives. This is a bounded availability result for the current repository, not a claim that the original journals are absent from the old worktree.

The prior [frozen-input eligibility audit](hung-block7-input-eligibility-20261030-v1.md) verifies 6,210 scheduled origins against input data and both run-manifest tags. It cannot independently authenticate execution-journal bytes, forecast-before-label ordering or per-origin numeric values. Those checks require the exact 138 journal files or an equivalent immutable provider readback. Importing journal bytes by itself would still require a separate numeric/causal audit and a non-author Block7 decision.

Reproduce the request and stage status from repository root:

```sh
python -m tools.hung_block7_journal_stage --write-request
python -m unittest tests.test_hung_block7_journal_stage -v
```

The command exits 1 until all 138 requested files are present and SHA-correct. It never reads the old worktree or launches replay/training. An existing request file is checked byte-for-byte rather than overwritten.
