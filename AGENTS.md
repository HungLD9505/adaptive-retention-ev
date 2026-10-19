# Working rules

- Read the issue and acceptance criteria, `README.md`, `docs/WORKFLOW.md`, and `data/README.md` before starting. Stay within the issue scope and record findings outside it.
- Report 1 is the method reference. Do not silently change the 24→24 task, history budgets, loss, retention, or controller. Submit method changes separately for review.
- Do not present the research gap, novelty, or effectiveness as proven. Test fixtures alone are not evidence of research effectiveness.
- Use a separate branch and PR for each implementation. Choose `feat/`, `fix/`, `docs/`, or `chore/` by purpose; use `archive/` for historical snapshots. This applies to people and coding agents. Never push directly or force-push to `main`.
- Branch from `dev`, target PRs at `dev`, and link the issue. Do not merge PRs autonomously. CI must pass and a peer other than the author must approve. Updating `main` requires a separate user/team instruction for that update; `master` preserves the backup.
- `data/sources.json` records download sources and historical fingerprints. State when real archives have not been checked locally; historical checksums are not proof of a fresh download.
- Never overwrite, modify, or delete raw archives. Do not fill target labels, treat missing values as zero, or use future labels before availability.
- Keep datasets, environments, checkpoints, and large runs outside Git. Never commit secrets or credentials.
- Data acquisition, hourly processing and model inputs are implemented; models/controllers remain next. Create modules only when implementing a concrete need; avoid speculative frameworks and abstractions.
- New pipelines must record config, source/input identity, code version, runtime, run ID, and acceptance scope. Create new outputs rather than overwriting old runs.
- Prefer independent test fixtures. Routine tests and CI must not download raw data or run long training jobs.
- Run the README checks and report what passed, failed, or was not run, including limitations. Never change expected hashes or fixtures to conceal an unexplained change.
- Use `docs/reports/` for actual phase handoffs; do not create competing plans.
- After a PR is merged, verify its work is preserved on the target branch, delete the finished remote/local working branch, and close its issue once all acceptance criteria are met. Close superseded PRs with a replacement link. Preserve `main`, `dev`, `master`, and branches with unmerged work or active PRs. This cleanup may run without another permission request; it does not authorize merging.
- Write maintained documentation, code comments, issues, and PR descriptions in English. Preserve original source documents and historical evidence.

## Coding essentials

- Use descriptive names and give each function/module one responsibility. Share logic when a real use case requires it.
- Python files over 500 lines need a PR explanation and reviewer agreement. Do not split files mechanically to satisfy a line count. Keep functions short and readable.
- Add type hints to new public functions/interfaces. Run Ruff lint and format as documented in the README.
- Cover new logic with appropriate tests and bug fixes with regression tests. Documentation and formatting changes do not need artificial tests.
- Pass paths, seeds, and hyperparameters through config or arguments instead of tying algorithms to one machine. Do not build a config framework prematurely.
- Use `logging` for core diagnostics when needed; CLIs may `print` results. Never swallow errors with `except: pass`. Validation/QC failures must report the error and return failure.
