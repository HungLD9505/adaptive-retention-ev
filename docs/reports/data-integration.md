# Data/input integration — final technical acceptance

## Decision and scope

On 2026-10-20 the team lead requested a final combined check, integration into dev, synchronization to main and cleanup of completed branches/issues. The instruction also accepts the minimum 1/24 historical availability gate subject to coverage/missing-rate reporting, identical gates across methods and separate reporting of `source_checkpoint_only` targets.

**Independent peer approval has not been supplied.** This integration proceeds under that specific lead instruction as a one-time exception to waiting for peer approval. No GitHub Approve review is fabricated, no branch-protection setting is weakened, and the normal peer-review rule remains for subsequent work. Technical tests are executed by the implementing agent and are not described as independent human/research review.

Technical verification is complete for the scope below. Merge/promotion must use PRs and successful Ubuntu/Windows checks on the integrated state; PR metadata records actual merge completion. The data handoff covers #16/#17/#18; model training, checkpoint serialization, runner and effectiveness evaluation remain future #19/runner responsibilities.

## Integration strategy and duplicate handling

- Branch from dev `62c7e2a`; integrate original PR heads in dependency order **#25 → #26 → #27 → #28 → #29 → #30 → #31 → #32 → #33 → #34 → #35 → #36**.
- Use merge ancestry, preserving all 12 original heads rather than applying those changes again as independent patches. The combined runtime snapshot is `538156c`.
- README conflicts use the current #36 guide/status/navigation; CHARGED reference conflicts preserve both semantics and suitability links. Final loader/CLI conflicts select the tested #36 v2 policy, not the earlier unresolved-policy v1 implementation.
- Every original PR head is verified as an ancestor. The integrated `ev_inputs/*.py` and model-input CLI are byte-identical to #36. Report 1, the raw-source catalog, published release catalog and old artifacts are unchanged.
- Use one integration PR to dev with a merge commit, then a separate dev-to-main promotion PR. After ancestry preservation is verified, original slices are merged/closed as appropriate and finished branches removed. Main/dev/master are retained; any branch with unmerged work is preserved.

## Verification results

| Gate | Actual check |
| --- | --- |
| Offline regression suite | **119 tests PASS** across all producers, audits, features, splits/scalers, windows, loader and missing-data policy. |
| Environment/style | Python 3.12; pip check, source listing, Ruff lint/format and diff checks PASS. No new runtime dependencies. |
| UrbanEV producer | Fresh verification/read of the original archive and extracted station members; full station raw → hourly run. New hourly bytes exactly match the published 7,306,608-row producer output. |
| CHARGED producer | Fresh archive verification and all six cities adapted; all six new hourly files match the published output bytes, totaling 18,797,760 rows. |
| Fresh end-to-end input runs | Full UrbanEV SZH budget 7 and full CHARGED AMS budget 7 from the **new** producers. Counts and all five data-artifact identities match the released handoff exactly. New manifests keep new provenance. |
| All released input configurations | All 21 manifests and every named artifact freshly rehashed/recounted against recorded handoff evidence; every ID/count remains unchanged. These are not claimed to be 21 newly rerun loaders. |
| Coverage/missingness | All emitted historical masks counted; all requested dates remain accounted; emitted labels stratified by initialization mode. No model accuracy measured. |
| Shared distribution | Live Drive contains 2 raw, 2 processed and 7 input archives; all IDs/names/sizes match the immutable catalog, release folder has anyone-with-link reader access. SHA-256 remains a recipient-side download check; no remote-content rehash is claimed. |
| Repository storage | No tracked raw/processed/input artifacts, files over 1 MB, or matches for the inspected private-key/token patterns. This is a bounded inspection, not a complete security certification. |

Fresh execution details:

| Dataset | Producer seconds | Loader seconds | Input profile | Result |
| --- | ---: | ---: | --- | --- |
| charged | 31.76 | 174.32 | charged-AMS-7d | All hourly/data-artifact bytes match released snapshot |
| urbanev | 247.90 | 108.41 | urbanev-SZH-7d | All hourly/data-artifact bytes match released snapshot |

## Coverage and historical missing rate

The following missing rate counts missing/unavailable energy positions **within emitted 24-hour inputs**. It excludes fully skipped histories and scale-blocked origins, which are shown separately. Do not describe that conditional rate as full-schedule completeness. An input with only one valid hour is permitted by the lead-selected gate and is not proven to be predictive.

| UrbanEV budget | Requested dates | Emitted inputs | Scale-blocked | Empty-history skips | Partially observed emitted inputs | Inputs with 1 valid hour | Missing fraction within emitted histories |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7d | 63,090 | 48,701 | 6,030 | 8,359 | 3,041 | 586 | 3.688% |
| 14d | 63,090 | 48,792 | 5,760 | 8,538 | 3,060 | 596 | 3.714% |
| 28d | 63,090 | 49,116 | 4,950 | 9,024 | 3,089 | 616 | 3.741% |

All 18 CHARGED profile/budget runs have zero missing historical positions under the released-file gate and 153,824 emitted inputs per budget across the six separate city experiments. Publisher-filled values cannot be distinguished from original observations; this is not strict-online evidence or a joint pretraining pool.

### Initialization strata remain separate

These are record/label counts, not performance results. Complete labels use the declared bin-end availability convention.

| UrbanEV budget | Initially adaptable: emitted / complete-label days | Source-checkpoint-only: emitted / complete-label days |
| --- | ---: | ---: |
| 7d | 47,037 / 45,222 | 1,664 / 194 |
| 14d | 47,040 / 45,222 | 1,752 / 268 |
| 28d | 47,222 / 45,296 | 1,894 / 493 |

Every compared method must use the same reviewed schedule/history gate and report requested/emitted/scorable coverage. Source-only-initialization targets must be reported separately from initially adapted targets. Initial training counts and scalers are unchanged. No target is reassigned, no missing Y is filled and no history budget is widened. Do not tune the policy using Final outcomes.

## Handoff and scientific limits

Use [shared downloads](../data/DATA_DOWNLOADS.md), [the full flow/training explanation](../data/DATA_FLOW.md), [input policy and checkpoint binding](../data/INPUT_ACCEPTANCE.md), and [release catalog](../../data/releases/DATA-v1-20261019.json). Existing prepared data remains DATA-v1-20261019; byte-identical reproduction does not require another data upload/version. The new validation runs remain separate local outputs:

- `data/processed/urbanev/integration-v1-20261020-urbanev/`
- `data/processed/charged/integration-v1-20261020-charged/`
- `data/inputs/issue18-integration-v1-20261020/`
- `runs/issue18-integration-v1-20261020/` for explicit commands, configs, logs and verification drivers.

The compact [evidence JSON](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/data-integration-evidence.json) records exact commands/config/source identities and per-run results. New producer/input manifests bind their new paths and code/runtime while old manifests and release hashes remain untouched.

The data-to-checkpoint interface is specified as `ev-checkpoint-input-binding-v1`. Actual model weight/optimizer/RNG serialization/reload tests are #19/runner implementation, not claimed as already implemented by the input loader. No checkpoint/model/controller code is added or required methods silently removed by this acceptance.

Unresolved scientific limits remain: UrbanEV energy is estimated/derived; bin labeling, timezone and actual arrival assumptions are provisional; CHARGED upstream preprocessing lacks per-cell provenance and may involve future values; ID-disjoint splits do not prove disjoint physical locations. Keep UrbanEV primary, CHARGED supplementary and SZH separately reported. Local causal checks/CI do not certify upstream causality or effectiveness.

This report records data/input technical acceptance under the explicit lead direction. It does not establish the research gap, novelty, adaptive-model effectiveness, strict-online readiness or independent external SZH validation. The sole sprint plan remains unchanged.
