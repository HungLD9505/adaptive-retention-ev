# Curated evidence

This directory contains technical evidence, explicit limitations and small files still
consumed by verification code/configuration/tests. It is not a current task queue.
The report PDFs and exact tables live under [report/](../../report/README.md).

| Evidence | Read first |
|---|---|
| Controller identity and apparently conflicting results | [Method/cohort audit](issue99-controller-identity-audit-20261112/README.md), [fresh arithmetic](issue99-controller-identity-audit-20261112/identity-audit.json) |
| Current manuscript method, numerical and layout audit | [E2E evidence verification](issue99-report-e2e-evidence-20261112/README.md), [claim register](issue99-report-e2e-evidence-20261112/claim-evidence.md), [current reader](../../report/rebuilt-review-20261112/README.md) |
| Primary frozen Final and its limits | [Final handoff](issue23-final-complete-handoff-20261029.md) |
| Primary vs separate supporting evidence | [Joint synthesis](issue23-joint-evidence-synthesis-20261030.md) and [full-precision record](issue23-joint-evidence-synthesis-20261030-v1.json) |
| Posthoc interpretation and report consistency | [Retention analysis](issue23-retention-posthoc-20261031.md), [Report 1 audit](issue23-manuscript-report1-review-20261031.md) |
| Alternate implementation and bounded evaluation | [Latest supporting report](hung-e2e-research-report-draft-20261030-v47.md), [remaining gates](hung-e2e-gate-register-20261030-v70.md) |
| Exploratory continuous-retention study (10 November) | [Results and method](issue99-study-20261110/paper-method-and-results.md), [verified execution](issue99-study-20261110/execution-verification.md), [full-precision means](issue99-study-20261110/method-summary.csv) |
| Additional-station retention comparison (10 November) | [Twelve-station handoff](issue99-expanded-development-20261110/handoff.md), [paired means](issue99-expanded-development-20261110/station-results.csv), [verification](issue99-expanded-development-20261110/verification-and-summary.json) |
| Transfer and isolated confidence ablation (10 November) | [Common-bank and target-only handoff](issue99-confidence-evidence-20261110/handoff.md), [station means](issue99-confidence-evidence-20261110/station-results.csv), [future decision audits](issue99-confidence-evidence-20261110/decisions.csv) |
| Calibrated training and 7/14/28-day review manuscript | [History handoff](issue99-history-review-20261110/handoff.md), [baseline audit](issue99-history-review-20261110/baseline-audit.json), [teacher-review manuscript](../../report/teacher-review-20261110/README.md) |
| Stable/fast expert fusion follow-up | [Negative-result handoff](issue99-stable-fast-20261110/handoff.md), [verified scores](issue99-stable-fast-20261110/verification.json) |
| Full historical-cohort controller follow-up | [810-unit / 21-group handoff](issue99-full-scope-20261110/handoff.md), [full-precision groups](issue99-full-scope-20261110/group-results.csv), [verification](issue99-full-scope-20261110/verification.json) |
| Integrated teacher review 11 November | [Baseline and manuscript handoff](issue99-teacher-review-20261111/handoff.md), [historical review version](../../report/teacher-review-20261111/README.md) |
| Diagnostic studies | [Fixed adaptation](member-duc-retention.md), [Confidence controller](member-cyber-controller.md) |
| Data and input handoff | [Data integration](data-integration.md), [inputs](input-handoff.md) |
| Software and package validation | [Verification reference](main-readiness-20261102.md), [machine-readable checks](release-curation-20261102-v1.json) |
| Issue #99 Source10 studies and handoff | [Task handoff](issue99-task-handoff-20261110.md), [controller follow-up](issue99-controller-followup-20261110.md) |

Earlier progress snapshots, temporary recovery notes and superseded report drafts
are preserved at tag `archive/pre-doc-curation-20261102`, commit
`8cdab1bc096a9c116c7b7f911d548a7621dd81ac`. See the
[archive manifest](../archive-manifest.json) for exact removed paths and hashes.
Some old report versions remain because regression tests deliberately read them;
their presence does not make them current conclusions or accepted Final results.

Retained JSON/CSV bytes and the canonical report assets are unchanged.
Current technical summaries identify implementation scope without assigning work
to individuals. Historical scheduling, execution coordination and self-reported
handoff text are available through compatibility links to
`archive/pre-technical-docs-20261102`, commit
`c8a2afc007bb6e8f739dec219d43ae06f492139c`.
Original regression-test snapshots retain their bytes where tests require them;
they are evidence fixtures rather than current task instructions. Unfavorable/null
outcomes and validation limitations remain in the report and archived originals.
