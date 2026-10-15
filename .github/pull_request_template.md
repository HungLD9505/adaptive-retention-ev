Issue: #... (target `dev`; update/close the issue when acceptance criteria are met).

## Problem and outcome

Describe the problem, scope, and resulting behavior.

## Method / data scope

- Does this change the method, protocol, or data sources? If so, identify the decision requiring review.
- Relevant source/input/run IDs and config:

## Checks and evidence

- Commands run and results:
- Handoff report / small reviewable artifacts:
- Checks not run, assumptions, and limitations:

## Checklist

- [ ] Appropriate tests, lint, format, and diff checks pass.
- [ ] No raw data, checkpoints, environments, or secrets are committed.
- [ ] Raw archives and old runs are preserved; future data is not used outside the protocol.
- [ ] Reports and documentation match the actual implementation.
- [ ] The target is `dev`; updating `main` requires separate authorization for this update.
- [ ] A peer other than the author approved the latest commit (Approve review or `approved merge` + SHA comment under WORKFLOW).

After merge: verify the work is preserved, delete the working branch, and close the issue when all acceptance criteria are met. Keep `main`, `dev`, and `master`.
