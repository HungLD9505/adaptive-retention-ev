# Clean-tree local validation and exact-head CI diagnosis — 30 October 2026

This create-only record supersedes [v2](hung-e2e-validation-20261030-v2.md) for audit-code head `776d2c82ffb376d48295cbee46ab97d44681e778`. Its ignored repository-local test log is `.cache/hung-test-run-20261030-v6.log`, SHA-256 `e5c2fa95f73abfb9e0234cef8c52f2fde21e0b3743817b3fa18c201b076f90ec`.

Python 3.13 in UTF-8 mode on a clean tree: full `unittest` discovery ran **553 tests**, with zero failures, zero errors and one skip. Ruff lint/format, source listing, Block7 file and numeric gates, the 90-cell Final report numeric audit, 111 local Markdown links and five artifact SHA checks also passed in the same validation checkpoint. These are software and artifact-transformation checks, not scientific acceptance.

The exact-head [GitHub Actions run 40936185756](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40936185756) did not start the Ubuntu or Windows tests because of account payment/spending-limit settings. Classification: `CI_NOT_EXECUTED — ACCOUNT_BILLING_OR_SPENDING_LIMIT`, neither a CI test failure nor a CI pass. Later documentation-only commits require their own exact-head CI observation.

Independent reviewer decisions on historical Block7 fairness, Hùng–Quyền parity, CHARGED physical lineage and Colab #39 remain separate gates.
