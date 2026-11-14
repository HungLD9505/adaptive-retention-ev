# Integrated E2E system flow — 12 November 2026

The owner requested a new overall pipeline corresponding to the newer executed
system, rather than disconnected sketches. The current reader now places the
integrated source/target/fusion/feedback flow in **Figure 1, page 3**. The old
model and feedback sketches are replaced by one editable native TikZ figure.
The separate original selector diagram is explicitly captioned as historical.

The new flow shows:

- Namespace-specific Source10 training, copied initialization and a separately
  frozen encoder/latent scale reference.
- Identical permitted historical and future-calendar inputs to both GRUs.
- Stable latent retention at lambda 1 and fast adaptation at lambda 0.
- Soft fusion, persisted forecasts and independently observed complete labels.
- One stable update on the arrived day, one fast update over the available
  seven-calendar-day window, and a distinct update of weight w.
- The implemented log-odds/Fixed-share formula, initial weight about 0.4308,
  eta/share 0.1 and resulting weight interval [0.1, 0.9].

The system is forecast fusion; no bootstrap selector is drawn as part of its
weight update. It does not change either expert's constant lambda. Labels flow
from an independent observation input, and the weight loss uses saved pre-update
expert forecasts. Feedback influences subsequent forecasts only. No method,
training run, result ledger or evaluation window changes.

## Validation and artifacts

[report-audit.json](report-audit.json) freshly rechecks the same 52 baseline
display cells, 21 historical rows, five Later rows and seven Development rows.
Evidence and method-code hashes match the previous manifest. The displayed
log-odds formula agrees with `update_stable_weight` in 64 numeric combinations.
The ten existing expert-mixture tests pass; Ruff lint/format, frozen release
checks and whitespace checks pass. The full root suite was not repeated for
this document-only change; its prior clean-checkout 1,041-test result and 12
skips remain recorded in the preceding rewrite handoff.

The current report has 16 pages, seven figures, two native TikZ flows and no
embedded raster images. All pages were inspected or matched an inspected render.
Final compilation has no overfull boxes, unresolved references or missing
characters. Bibliography font is 9.5 pt to maintain clean two-column placement;
original class/style bytes remain unchanged. Ordinary underfull warnings remain.

The 14-file source-only ZIP was independently extracted and compiled, with all
16 page texts matching the delivered reader. Overleaf's web editor was not used.
Its SHA-256 is
`bf01457fde8b1f61453fd3e6d6650b18f8c7c216e82642ec0f52cd4189c760b1`.

External preview, source ZIP, compile logs and page renders are retained at
`/Users/quyenmanh/Developer/TFL-EV/runs/issue99-system-flow-20261112-v5`.
The preceding reader is retained there as `previous-reader.pdf`, and its original
source remains in Git history. No historical frozen report is overwritten.

The revision is published on the existing review branch / PR #116; no merge,
main/dev update or new experiment is performed.
