# CHARGED — forecasting suitability and Shenzhen/UrbanEV overlap

Issue #17, Steps 3 and 4. **Disposition proposal for peer/lead review; not an approved input artifact or a change to the experimental protocol.**

## 1. Scope and unchanged method

Report 1 §4 already identifies UrbanEV station-level as the planned primary dataset and CHARGED as a generalization option after audit. [Master Research Flow](../MASTER_RESEARCH_FLOW.md) and [Sprint Plan](../SPRINT_PLAN.md) retain this conditional role. This handoff does not demote a mandatory benchmark, waive a generalization objective, or certify UrbanEV strict-online readiness.

The task remains 24 historical hourly values plus permitted calendar/mask information → 24 hourly energy forecasts, once daily; initial target histories remain 7/14/28 days. Source training must precede deployment; source/development/final entities stay distinct within the approved protocol. Forecasts must be saved before scoring/updating. Retention, loss, controller, baselines, ablations and seed requirements remain unchanged.

Steps 1/2 are independently reviewable in [PR #26](https://github.com/HungLD9505/adaptive-retention-ev/pull/26) and [PR #27](https://github.com/HungLD9505/adaptive-retention-ev/pull/27). This branch starts from dev and does not import their unmerged code. It adds only a read-only overlap/period diagnostic, fixtures, evidence and this handoff. No adapter, windows, cohort, exclusions, data fixes, training or final evaluation are created. The full issue remains open pending review and the contract/input handoff.

## 2. What CHARGED can and cannot support

| Proposed use / claim | Disposition | Reason / condition |
| --- | --- | --- |
| Compare methods on the same released site-level hourly energy under chronological replay | **Limited candidate**, subject to lead approval and #18 input/QC gates | All six cities have complete nominal hourly matrices; upstream processing and derived targets must be disclosed. Same data across methods does not guarantee upstream artifacts leave relative rankings unbiased. |
| Simulate targets with only 7/14/28 days initially exposed to the project's algorithm | Structurally feasible; **official eligibility pending** | This is limited-history replay of a publisher-processed release, not proof that the underlying information was available in real time or that a site had just opened. |
| Claim strict causal online deployment or untouched meter-label accuracy | **Blocked by missing evidence** | Upstream imputation/availability lineage and exact label/bin semantics are unresolved. Energy is derived; no original/imputed cell mask is available. |
| Call SZH an independent unseen-location external test against UrbanEV | **Not supported** | Very extensive exact coordinate overlap; no verified physical-entity crosswalk. Different record periods do not establish location independence. |
| Use AMS/JHB/LOA/MEL/SPO for additional geographic coverage | Limited candidate under **shared-release** limitations | Different city scope from UrbanEV, but preprocessing/availability evidence remains shared/limited. No automatic certification of independent original measurements. |
| Pool both releases, transfer across them, or select target entities using full-period activity | **Not authorized by this handoff** | Requires explicit protocol/identity/availability review. This report does not introduce cross-release training or selection. |

“Blocked” above refers to a particular claim, not a finding that every CHARGED value is unusable or leaks. No measured leakage percentage or proof of universal contamination is asserted. A chronological benchmark on publisher-processed data is a bounded research setting; its results cannot establish performance on untouched causal streams.

## 3. Structural capacity for 24→24 — not sample creation

Step 1 found 4,392 nominal hourly labels per city, spanning Apr 1–Sep 30, 2023: **183 complete 24-label days**. Four hourly matrices share the same literal clocks; weather aligns after parsing. Basic energy checks found no blank, nonnumeric, nonfinite or negative cells. These are released-file facts, not original-observation provenance.

The existing Research Flow reference uses **CHARGED deployment on July 1, 2023**, entity-hash splits of 60/20/20 separately per city, `X_hist[24,7]`, `C_future[24,5]`, `Y[24]`, and p95 scaling from permitted history. These remain reference settings requiring protocol review and #18 implementation; this handoff changes none of them.

Under that existing reference and the release's nominal daily clock, April 1–June 30 provides at most 91 days of pre-deployment source history; July 1–September 30 provides at most **92 daily forecast origins**. For a target prefix immediately preceding July 1:

| Initial history | Nominal target-prefix start | Fully contained daily 24→24 adaptation pairs inside prefix | Potential replay days from July 1 | Complete 14-day blocks plus remainder |
| --- | --- | ---: | ---: | --- |
| 7 days | June 24 | 6 | 92 | 6 blocks + 8 days |
| 14 days | June 17 | 13 | 92 | 6 blocks + 8 days |
| 28 days | June 3 | 27 | 92 | 6 blocks + 8 days |

These are arithmetic upper bounds under the existing reference, not accepted sample counts. No windows, entity splits or p95 scalers were generated. A fixed midnight origin and 24 release labels per day are nominal-clock assumptions for this calculation; timezone/bin/availability review and eligibility rules may reduce or block usable samples. #18 must compute actual counts from accepted artifacts and report the 8-day tail according to the reviewed runner policy, without changing the 14-day block method or counting an incomplete block as complete.

Calendar features are deterministic under the eventual agreed clock convention. Future actual weather, future realized prices, static whole-period activity totals and later labels are not assumed available. Optional features remain optional; this audit enables none.

## 4. City-level disposition proposal

**Every row below is “Limited candidate for published-data replay; not accepted for model input yet.”** Basic checks have passed on released numeric cells; city-level file-valid masks and protocol eligibility are not approved. Strict-online readiness is not established for any city.

| City | Released sites | Entirely zero-volume sites | Specific evidence / review condition | Independence boundary |
| --- | ---: | ---: | --- | --- |
| AMS | 2,449 | 1,061 | Step 2 paired/static audit: 232 mismatched zero/nonzero volume-duration cells; static/hourly totals differ for 1,388 sites. All-zero site's metadata agrees, without proving physical inactivity. | Additional geography; shared-release upstream limitations |
| JHB | 47 | 12 | Small entity pool; upstream masks/availability unresolved. New paired/static analysis has not been performed here. | Additional geography; shared-release upstream limitations |
| LOA | 229 | 5 | info.csv header mismatch; source/member IDs and numeric matrices checked in Step 1. No new paired/static acceptance. | Additional geography; shared-release upstream limitations |
| MEL | 63 | 1 | info.csv/header aliases, local-time/DST interpretation and publisher-reported rated-power substitution need bounded claims. No DST repair or per-cell substitution mask. | Additional geography; shared-release upstream limitations |
| SPO | 47 | 6 | Small pool, info.csv header mismatch and site aliases; upstream availability unresolved. | Additional geography; shared-release upstream limitations |
| SZH | 1,445 | 68 | info.csv header mismatch and extensive coordinate overlap with UrbanEV; exact device identities unresolved. | Do not claim independent unseen-location external validation |

No site was removed. All-zero counts describe the entire release for audit purposes and must not become a full-future-informed target selection rule. If an eligibility rule later uses activity, it must be agreed using development and only permitted history. Any separate activity analysis must preserve the same approved samples for compatible methods.

Zero-heavy sites can dominate aggregate scores or make percentage gains undefined when a reference error is zero. Report 1's original-unit MAE/RMSE, station-first aggregation and explicit zero-denominator handling remain required. Do not silently exclude easy/zero sites, choose favorable cities, or invent a new metric to obtain an improvement.

## 5. Shenzhen/UrbanEV — empirical overlap evidence

### Inputs and comparison method

Both catalog archives were freshly checked for size/SHA-256, with the CHARGED publisher MD5 also checked. The diagnostic reads original ZIP members directly:

- UrbanEV `20220901-20230228_station-raw/station_information.csv` — 1,682 station rows.
- CHARGED standard `SZH/chargers.csv` — 2,195 charger rows; `SZH/sites.csv` — 1,445 clustered-site rows.

Coordinates are compared as **exact Decimal numeric pairs**, without rounding, tolerance, nearest-neighbor search, physical-distance computation or CRS conversion. Equivalent decimal formatting compares equal; genuinely different decimals do not. Shared coordinates are not a one-to-one ID join. UrbanEV station IDs and CHARGED charger/site IDs use different namespaces and entity definitions.

| Comparison | UrbanEV station rows at shared coordinates | CHARGED rows at shared coordinates | Shared distinct coordinate pairs |
| --- | ---: | ---: | ---: |
| UrbanEV stations ↔ SZH chargers | 1,614 / 1,682 | **2,176 / 2,195 (99.13%)** | 1,481 |
| UrbanEV stations ↔ SZH clustered sites | 1,495 / 1,682 | **1,378 / 1,445 (95.36%)** | 1,378 |

UrbanEV has 1,543 unique coordinate pairs across its 1,682 rows; SZH chargers have 1,500 pairs across 2,195 rows. Repeated coordinates prevent interpreting the match counts as confirmed numbers of shared physical devices. Cluster centroids can also differ from member coordinates, so the smaller site match count is not evidence of disjointness for the remaining sites.

Related #18 risk: repeated coordinates within UrbanEV also mean ID-disjoint hash splits are not automatically proven to be physically disjoint locations. Preserve the existing reference split; record the claimed unit and review any proposed physical-grouping rule separately. This diagnostic does not redesign splits or merge co-located IDs.

An actual coordinate example: UrbanEV station `1001`, CHARGED charger `122318` and CHARGED site `149` all record `(113.784724, 22.714121)`. This is a candidate association, not an authenticated device/station identity crosswalk. No mapping was applied to training data or cohorts.

### Coordinate reference limitation

The pinned [UrbanEV README](https://github.com/IntelligentSystemsLab/UrbanEV/blob/44f2aa0c8d89f192bce00bafb0def74a21b39c68/readme.md#L79-L88) explicitly labels station coordinates **GCJ-02**. CHARGED describes coordinate harmonization and WGS-84-based geodesic distances, but that does not independently verify the transformation lineage of each released SZH coordinate.

The exact numerical overlap remains an observed fact, even with unclear CRS lineage. It strongly argues against assuming independent location populations. It does not validate geographic distances or prove copied measurements. No coordinate transformation is guessed to strengthen or weaken the overlap result.

### Time and collection-source comparison

| Item | UrbanEV | CHARGED SZH |
| --- | --- | --- |
| Publisher-described collection period | Sep 1, 2022–Feb 28, 2023 | Apr 1–Sep 30, 2023 |
| Direct timeline member checked here | station-raw `charge_5min/1001.csv`: 52,128 unique clocks, Sep 1 00:00 through Feb 28 23:55 | `SZH/volume.csv`: 4,392 unique clocks, Apr 1 00:00 through Sep 30 23:00 |
| Published collection description | Mobile EV-driver platform; the inspected paper does not name it | Multi-platform collection; paper explicitly lists Chongdianba among its sources |
| Physical entity | Station with pile counts | Charger and spatially clustered virtual site |

The published and sampled calendar periods do not overlap. This scan does not compare every UrbanEV entity timeline or perform a record-value duplication search. It establishes neither duplicated timestamped observations nor a clean identity-disjoint external test. Exact platform equivalence is also unproven: geographic overlap and common research lineage alone do not identify the UrbanEV mobile platform.

A bounded description is **“a later-period Shenzhen dataset with extensive overlap in released coordinates and unresolved physical-entity/source lineage.”** If used, report SZH separately from the other cities. Do not pool it into a headline independent external result or silently drop it. Any entity-grouped protocol across releases requires a separately approved crosswalk; a different numeric ID is not evidence of a new entity.

## 6. Source evidence and remaining scientific limits

Primary sources:

- [UrbanEV paper, DOI 10.1038/s41597-025-04874-4](https://doi.org/10.1038/s41597-025-04874-4), *Study area and data acquisition*, *Processing raw information into well-structured data*. Full text retrieved from [Europe PMC XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11953418/fullTextXML).
- [CHARGED paper, DOI 10.1038/s41597-025-05584-7](https://doi.org/10.1038/s41597-025-05584-7), *Methods* and *Data Records*, [Europe PMC XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12271547/fullTextXML).
- UrbanEV README pinned above; CHARGED public source pinned in Step 2 at `ff13cefe0c9e15073d02ad1e57efb4054dd70c5a`.
- Report 1 §4/7, Research Flow §9, Sprint Plan conditional CHARGED/strict-online gates.

The UrbanEV paper also describes filling/outlier correction in its processed-data workflow. This is not proof that those operations were applied identically to the newer station-raw release used by #16. The README advertises that variant as before preprocessing; its energy is nevertheless derived. Its exact generation/availability provenance must be checked under #16/#18. Choosing UrbanEV as the planned primary dataset does not make strict-online claims automatically valid.

No original mobile-platform responses, per-cell imputation masks, publisher v3 execution log or authenticated physical-ID mapping were obtained. The five-minute CHARGED archives were not downloaded; no claim about their untouched/raw status is made. Strict causal availability cannot be restored merely by splitting or re-aggregating processed hourly values. Pairwise diagnostics outside AMS remain unmeasured in this slice.

## 7. Review gate and handoff to #18

The proposed disposition is to preserve Report 1's UrbanEV-primary role and consider CHARGED only within the bounded chronological-release claims above, after explicit team acceptance. This is not a new method or automatic approval to train.

Before a CHARGED input handoff, reviewers need to resolve/record:

1. Whether the limited published-data benchmark satisfies any intended generalization claim; identify an unmet objective if stronger evidence remains unavailable. Do not call required cross-dataset evidence complete merely because this report exists.
2. City scope and schema/time assumptions, including explicit metadata-header mapping, ID aliases and nominal local clock/bin semantics. Any reviewed override belongs in new processed outputs, never raw.
3. Whether any prefix-only eligibility rule is needed and how the source/development/final and deployment design avoids full-release activity/static lookahead. #18 owns official cohorts, windows, masks and scaling.
4. How SZH is described separately and how global unseen-entity claims avoid unsupported identity assumptions. No source pooling or cross-release target mapping is authorized here.
5. If stronger upstream provenance is required but unavailable, record blocked claims and the delivery/generalization shortfall for lead review. No controller/loss/budget/baseline requirement is waived.

Step 5 (shared contract/adapter handoff), #18 inputs and final city QC acceptance remain pending. The three states stay separate: **released-file diagnostics available; forecasting eligibility pending; strict-online readiness not established**.

## 8. Reproduction and verification

```sh
python -B -m tools.charged_suitability \
  --output runs/charged-suitability/issue17-step34-v1-20261017.json
```

Use Python 3.12 and a fresh output filename; `--storage-root` supports another machine with the catalog layout. Existing evidence is refused, raw storage is blocked as output, missing/corrupt archives fail, and no source members are written/extracted. Clock parsing and Decimal matching are diagnostic operations only; original values are untouched.

[Committed evidence](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/charged-suitability-evidence.json) records both archive identities, source/Report 1/plan hashes, code commit and script hash, UTC start, runtime/environment, comparison semantics, exact counts and sampled members. Exact identity/run counts are distinct from the structural arithmetic bounds above.

Local checks: **12 offline tests passed** (9 existing dev tests and 3 new diagnostic tests), Ruff lint/format, `tools.sources list`, `pip check` and `git diff --check` passed. Fixtures cover repeated coordinates, exact-decimal versus approximate equality, invalid coordinates, sampled clock scope and ragged metadata; they do not validate model effectiveness or physical identity. The real-data evidence run completed successfully on both verified archives. Windows/Ubuntu CI is reported on the PR. No training was run.
