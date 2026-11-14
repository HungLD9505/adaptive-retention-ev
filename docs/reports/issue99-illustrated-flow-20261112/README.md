# Illustrated system figure — 12 November 2026

The owner requested the rich illustration style of the supplied older method
figure: isometric charging sites, cars, sequence sheets, GRU pictograms and
forecast curves. Current Figure 1 on page 3 replaces the plain box artwork with
that visual style while retaining the newer stable/fast forecasting mechanism.

The figure is a hybrid: an illustration layer generated with the built-in image
tool and separately maintained native TikZ wiring. Raster-generation drafts had
ambiguous connectors, so the selected artwork has no inter-module wires. The
final connections are in `figures/illustrated-system-flow.tex` and are checked
against the existing implementation:

- Historical X_t enters both GRU encoders; known future C_t bypasses the encoders
  and enters both prediction heads.
- Source parameters initialize both full forecasters. A separate frozen encoder
  and fixed latent scales supply the stable representation penalty, alongside
  the stable model's latent output. The fast expert has no explicit penalty.
- Stable and fast forecasts enter soft fusion. Issued expert forecasts and later
  observed complete labels meet at scoring, before the weight update.
- Model-training feedback returns to the correct model; weight feedback returns
  to the subsequent fusion operation. Neither lambda is changed.

Site artwork, network pictograms, sequence curves and weight bars are schematic,
not measured results, confidence intervals or literal GRU gate diagrams. The
body explicitly states this. Main equations remain native LaTeX; all five result
plots remain vector. The report still has 16 pages and seven figures; its one
embedded raster image is the new illustration layer.

## Verification and delivery

[report-audit.json](report-audit.json) rechecks all 52 baseline display cells,
21 historical rows, five Later rows and seven Development rows. Underlying
method-code and evidence hashes are unchanged. All sixteen rendered pages were
reviewed as contact sheets and the complete illustrated wiring at full size.
Final compile has no overfull boxes, missing characters or unresolved references.
Ordinary underfull justification warnings remain. Frozen release checks pass.
No model training, raw archive download or full root-suite rerun is part of this
illustration-only revision; the preceding report/method checks remain recorded
in their dated handoffs.

The 15-file source-only ZIP was extracted and compiled independently; all sixteen
page texts match the reader. Source ZIP SHA-256:
`0950c7a460c67ce81b9f7825f5a02d246022a60b829096f1d63aeb33a55d02c4`.
The original template class and bibliography style are unchanged.

Delivery/QA root:
`/Users/quyenmanh/Developer/TFL-EV/runs/issue99-illustrated-flow-20261112-v6`.
It includes the standalone vector-wired figure PDF/PNG, source ZIP, full prompt
set (`generation-prompts.json`), page renders, audit scripts and previous reader.
The selected illustration artwork and its vector-wiring source are versioned
with the report. No contributor or scientific bibliography entry is added for
a tool. Publication stays on the current review branch / PR #116, without merge.
