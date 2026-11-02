# Issue23 manuscript v6: end-to-end review against Report 1

Reviewed 31 October 2026 on the existing evidence-synthesis branch. Scope: user-selected Figure 3 heatmap and an evidence-driven editorial review. No training, model/controller change, Final tuning, merge, issue closure or external submission was performed. This is an authoring review, not independent scientific approval.

## References and verification boundary

The supplied proposal `/Users/quyenmanh/Downloads/adaptive_retention_report_1.pdf` has SHA256 `cafc1db09a7fda4e196808a96cedf1b18098a4e7ff859d272402e049ebd65bbc`. All seven pages were extracted; the complete contact sheet and detailed equation/conclusion pages were visually inspected. The supervisor message specifies limited-history EV forecasting, GRU, varying source retention, observed forecasting performance and confidence, compared against Fixed and ordinary online selection. It does not promise a positive outcome.

The primary scientific pin is `61c32328d9829a69037dca629f727b4863015122`. Model, training, runner initialization/fork logic, controller bootstrap, evaluation metrics and frozen method settings were read from that commit. Aggregate results were checked against the joint synthesis and post hoc JSON files. The existing daily-output hash/arithmetic audits were reused; raw archives, remote provider checkpoints and independent peer approval were not reverified in this editorial pass. This review does not claim that every upstream data, software or checkpoint defect has been excluded.

The main and supplementary source documents were read. Existing figures, captions, equations, declarations and the previous full-result CSV were included in the review. The new heatmap uses all 30 original site contrasts at 14-day initial history. Its colors saturate at ±0.25 kWh, with real signed values printed; each city has a separate sorted ID list. It is a vector plot, not AI-generated result data.

## Corrections and material omissions addressed

| Finding in v5 | Correction in v6 | Evidence or reason |
| --- | --- | --- |
| New-station motivation could be read as verified newly opened stations. | Explicitly state simulation by withholding initial history from existing dataset entities. | Report 1 section 1 explicitly makes this distinction. ID/age equivalence is not established. |
| Abstract could imply a causal separation of initialization and later retention effects. | Describe distinct procedure contrasts; no clean component attribution is claimed. | Adaptive vs Target-only changes initialization, retention, selection and work. Fixed also starts at a different penalty. |
| Larger lambda was described as keeping the representation closer. | Describe a stronger loss penalty; do not guarantee realized distance, learning rate, speed or accuracy. | Objective weight is not an optimizer-outcome guarantee; Report 1 section 5.4. |
| Initial target adaptation was described unconditionally as three epochs. | State the complete-prefix-example condition and skipped-stage fallback. Qualify Figure 1. | Pinned `ev_runner/run.py` guards training with `initial_records`; source-initialized/random state is retained if empty. |
| Illustrated GRU branches could be mistaken for the complete architecture. | Caption identifies omitted future-calendar, MLP/Softplus, mask and scale operations; internal GRU drawings are icons, not literal layer/gate wiring. | Pinned `ev_models/model.py`: two-layer 64-unit encoder plus a 184→64→24 head and Softplus. The illustration is schematic, not a complete computation graph. |
| Source usefulness could be read as a directly measured quantity of retained knowledge. | Define it operationally through procedure forecast-error contrasts; disclose that source-task forgetting was not re-evaluated. | No source forgetting evaluation is claimed or supplied by these target-stream results. |
| RQ1/RQ3 wording obscured proxy/context/cost parts of the proposal. | Restore those questions without asserting complete answers. | Report 1 RQ1–RQ3. |
| Relevant prior latent consistency and evidence-dependent adaptation were omitted from Related Work. | Add R-Tuning, GUARD and PADRE, with verified primary-source identities. | Primary sources below. They are related work, not reproduced baselines. |
| “Development-selected” lacked the finite, staged, UrbanEV-cohort search boundary. | State tested Source durations, positive Fixed grid, four joint recipes, fixed alpha/resample count and endpoint winners. | Pinned calibration declarations/results and Final lock. No exhaustive optimality or equal-compute tuning claim. |
| Gain/NTR lookup values lacked a local definition and denominator. | Define station-level three-seed gain, NTR denominator and zero-baseline handling; report AMS NTR as 5/10 at each history. | Pinned `ev_evaluation/metrics.py`, `station_first`. Exact signs are not practical-harm thresholds. |
| Figure 3 caption still described bars and referred to “large-site” contrasts. | Replace with a heatmap caption; explicitly separate large error differences from physical station size. | Site power/charger count does not follow from the magnitude of a model-error difference. |
| Exact-sign continuation audits could silently stand in for the proposed thresholded adverse-switch rate. | State that a locked practical-harm threshold is absent; the proposed rate has not been supplied. | Frozen analysis profile explicitly provides descriptive audits without a harm threshold. |
| Recovery-time scope was not explicitly disposed of. | State it is not reported because no event/criterion-based recovery evaluation was performed. | Report 1 allows this metric only with a defined change event and locked recovery criterion. |
| Full runtime/memory and independent reproduction could be inferred from completion of execution. | Explicitly retain incomplete end-to-end cost and independent-review boundaries. | Recorded updates/timers/peaks have limited scopes and do not form complete end-to-end comparisons. |
| Source package claimed evidence identities but previous packages mainly held figure and CSV checks. | Include scientific commit, exact lock, input evidence hashes and the aggregate/post hoc evidence JSON files. | Provenance is supplied rather than merely asserted. Large raw/checkpoint archives are still excluded. |

## Alignment with the original research direction

| Original item | Verified status | Permissible interpretation |
| --- | --- | --- |
| 24 historical hours → 24 forecast hours; 7/14/28-day initial histories | Implemented and retained in frozen settings. Online observations accumulate afterward. | Initial-history simulation; not a fixed total training-data cap. |
| GRU backbone, transferred encoder/head, frozen source reference | Consistent with the pinned implementation. | GRU and transfer initialization are not novelty claims. |
| Normalized MAE plus coordinate-scaled representation retention | Formula matches pinned loss implementation. | Lambda controls a constraint, not a fraction of source “knowledge” or learning rate. |
| Three cloned candidate learning states and evidence-gated next-block choice | Code/config align; labels precede scoring and updates in the recorded replay contract. | A past-block decision rule, not proof of future safety or causal availability of publisher-imputed data. |
| Fixed and ordinary online selection comparisons | Present. Fixed starts at 1; Adaptive/Online-best at 0.1. Online-best is the closer confidence-rule contrast. | Do not describe Fixed contrast as changing only the confidence gate. |
| Comparable evaluation and three seeds | Paired station-first analysis with same main candidate-step count for Adaptive and Online-best. | Three candidates have extra update work relative to Fixed. Three seeds are not independent stations. |
| Proxy adequacy / context-dependent usefulness | Available descriptive correlations and station/context/phase diagnostics. | No prospectively validated rule for an unseen station or causal density/drift effect. |
| Better accuracy and practical cost from the confidence controller | Not established. | A negative/inconclusive superiority result is valid; Report 1 section 9 explicitly requires narrowing the claim. |
| Full efficiency, thresholded harmful-switch rate, external method reproductions | Not completed by this evidence package. | Keep these as limitations/unmet scope; do not label them completed. |
| Independent acceptance, portable public reproduction, submission declarations | Still separate/pending. | Completed Final execution is not submission readiness or CI/peer approval. |

## Numerical checks and conclusions preserved

- 21 namespace/history panels; 14 methods each; 294 full-precision aggregate MAE/RMSE rows matched exactly.
- Figure 3 uses 30 exact original site contrasts; none removed, changed or filled.
- Adaptive vs Fixed: 9 lower / 12 higher point-MAE panels; 18 finite intervals contain zero; 3 undefined.
- Adaptive vs Online-best: 11 lower / 10 higher; 18 finite intervals contain zero; 3 undefined.
- Adaptive vs Target-only: 18 lower / 3 higher; 15 finite intervals below zero and 3 above zero; 3 undefined.
- Adaptive vs Full fine-tuning: 17 lower / 4 higher; 6 finite intervals below zero, 12 containing zero, 3 undefined.
- Frozen Final accounting remains 810 whole units / 11,340 declared cells; 126 null cells leave 11,214 scored cells and 89/90 scored entities.
- MEL/SPO concentration, seed sensitivity, adverse AMS, stronger JHB Frozen Source and CHARGED/SZH fine-tuning/seasonal alternatives remain visible. Confidence superiority, equivalence, SOTA, universal robustness, future safety and full efficiency are not asserted.

The review checker initially expected the three adverse Target-only intervals in the “crossing zero” bucket; it failed. Reading the actual endpoints confirmed all three were above zero, as the manuscript already states. The editorial checker was corrected to track above-zero intervals separately. No experimental fixture, interval or manuscript result was changed to pass this check.

## Related-work verification

- [R-Tuning, AAAI official article](https://ojs.aaai.org/index.php/AAAI/article/view/40010): frequency-aware replay plus latent consistency. Author list, title, venue, pages and DOI were checked. Abstract/method-level description only; not a new numerical baseline.
- [GUARD, author arXiv record](https://arxiv.org/abs/2606.19363): contextual teacher routing and uncertainty-gated distillation. Its related ACM DOI is present in the arXiv record. The author-affiliated university publication record supplies proceedings pages. No claimed replication.
- [PADRE, official IJCAI proceedings](https://ijcai.org/proceedings/2026/503): delayed-residual/context evidence and gradient-step gating. Metadata and mechanism were checked; no matched 24-hour reproduction or performance ranking.

Initial direct DOI opens were unavailable, so official venue/author records were used. Other bibliography entries retain the earlier limited source checks. This is not a comprehensive novelty search, plagiarism certification or fresh full-paper reproduction audit.

## Validation and remaining boundaries

The companion `output/paper-v6` files contain the exact change list, numerical verification, frozen lock and evidence provenance. The main and supplementary sources require no model/test-suite execution for these editorial changes. Training and remote CI were not rerun. Relevant checks are numeric/config/label/bibliographic target reconciliation, actual Overleaf compile and rendered-PDF inspection. Final compile/render outcomes are recorded in the artifact verification after export.

Authors still need to approve names/order/affiliations, funding/conflicts, venue-specific policies and the scientific interpretation. The illustrated Figure 1 remains AI-generated and must not be relabeled as measured architecture/experimental output or original hand-drawn art. This review narrows unsupported implications; it does not certify the entire study as correct or ready for publication.

Final artifact verification: the exported v6 main manuscript has 14 pages, Errors 0 / Warnings 0, no missing-reference markers, and all pages rendered. Method/equation, Figure 3, result, limitations and references were inspected in detail. See `output/paper-v6/pdf-verification.json` for the final PDF hash.
