# Block7/Main saved-journal to manifest binding — 30 October 2026

The [machine-readable 138-row audit](hung-block7-journal-manifest-binding-20261030-v1.json), SHA-256 `9fa2380683fd014e1cbffc7c8468d370c66ccb461a9cd19a104a5a9ae71eea1`, extends the [saved-journal byte and segment audit](hung-block7-journal-audit-20261030-v1.md). It uses the same 69 historical Block7 and 69 Main exact-SHA staged `replay-90` journal segments. All **138/138** pass the pinned manifest's journal SHA, start/end indices and event count, plus header schema, input binding, resumed checkpoint identity and terminal runner cursor. Each JSON row names the journal SHA, manifest SHA, event range and resume stage.

The verifier reads only the repository-local staged files, rejects missing or mismatched bytes, and writes the JSON create-only. Reproduce with `python -m tools.hung_block7_journal_stage` and `python -m tools.hung_block7_journal_manifest_bind_v1`; the regression test rejects a journal header attached to the wrong resume checkpoint.

This establishes that the authenticated saved suffixes belong to their pinned run manifests. It does **not** authenticate earlier pre-resume journal segments, numerical forecast values, controller bootstrap draws or equivalence of the 7- and 14-day policies. The non-author Block7 fairness decision remains pending; no replay or method change was performed.
