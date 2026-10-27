# Issue23 — bounded Final preparation, October 27, 2026

## Decision and actual preparation

The human lead selected30 UrbanEV stations and10sites in **each** of AMS/JHB/LOA/MEL/SPO/SZH, with the same selected namespace/entity IDs across7/14/28days, seeds42/43/44, all14unique variants and90-day replay. This is90 namespace/entity IDs,270pairs,810whole units and11,340cells. Author IDs do not establish90 physically independent locations. UrbanEV remains primary; CHARGED is city-wise supplementary and SZH remains a separate temporal/possible-overlap analysis. The old3,510pair/147,420cell config and evidence are preserved as historical; expansion requires another decision.

Scope approval is not execution-lock approval. No real Final forecast/training/label values were decoded, and no Final fit/inference/evaluation was performed. Both Development GPU sessions remain released and the old monitoring automation was deleted. No valid Development/Source fit was repeated, purchase made, check bypassed, merge performed or issue closed.

The [bounded cohort](../../configs/issue23/final-bounded-cohort-v1.json), [analysis profile](../../configs/issue23/final-analysis-profile-v1.json) and [lock candidate v2](../../configs/issue23/final-execution-lock-candidate-v2.json) are concrete review artifacts. The lock pins exact method templates for all three seeds,21input manifests,21original Source checkpoints/reports, selection, analysis and code files. `runtime_profile` is deliberately null: it **cannot pass the production execution gate**. Earlier preliminary candidate evidence remains outside Git; none is approval.

## Outcome-blind sampling and eligibility

Selection rule `issue23-bounded-final-same-ids-v1` was committed in82f405d before execution against real metadata. `tools.final_cohort` authenticates the historical manifest/entity/Source-population pins, intersects ready Final IDs over all three budgets, then reserves one hash-minimum ID with an empty initially trainable prefix in any budget, if present. It fills the remaining quota from hash-minimum IDs positive across all budgets. Hash payload is compact JSON `[rule,[dataset,city],entity_id]`. No future activity, replay coverage, outcomes, energy arrays or coordinate exclusion enters selection. Insufficient quota fails; no post-outcome station replacement is allowed.

| Namespace | Shared ready IDs | Selected IDs used in all budgets |
|---|---:|---|
|UrbanEV SZH|340|1143,1171,1240,1272,1355,1468,1511,1556,1572,1593,1615,1616,1641,1642,1645,1697,1856,1914,1925,1939,1958,2013,2193,2369,2397,2420,2436,2520,2607,2653|
|CHARGED AMS|478|1413,1432,1444,1867,1924,24,298,35,358,689|
|CHARGED JHB|13|13,18,24,28,3,31,35,36,40,46|
|CHARGED LOA|41|108,122,127,129,166,18,202,205,208,49|
|CHARGED MEL|15|11,14,19,22,34,37,48,49,50,54|
|CHARGED SPO|10|12,16,20,21,22,27,28,30,42,43|
|CHARGED SZH|271|1074,1213,1227,1326,169,31,383,654,71,88|

UrbanEV has11shared IDs empty in at least one prefix;2193is selected and has0initial trainable examples at all three budgets. That is3empty-prefix pairs/126cells, **not a prediction that replay scores will be null**. No CHARGED selected prefix is empty. Metadata readiness means the allowed-prefix scale exists; it does not establish future label coverage. Undefined-scale/nonshared IDs are outside this declared eligible frame and must be distinguished from later missing/null scores inside it. Missing/Source-checkpoint-only/adverse cases inside the cohort remain included; labels are never filled.

The30/10 quotas are a resource choice, not a power calculation or proven sample size. The reserved empty-prefix stratum has unequal inclusion probabilities; unweighted summaries describe this selected cohort. SPO is a census of its ten metadata-ready Final IDs, not proof of geographical independence or representation of all chargers. Seeds are paired replications, not extra stations. Budget membership is fixed; conditional bootstrap intervals still face small/nonrandom/possibly dependent sites, time-block seams and multiplicity. No superiority, equivalence or novelty is established by this preparation.

## Source reuse and physical overlap

All21existing own-namespace seed42/43/44 epoch10checkpoint bytes were freshly hashed, CPU-loaded with optimizer state and checked against original Source population/stage/seed/epoch and finite nonnegative64-dimensional latent scale. Materialized copies retain the original report and original environment/code identities; no Source was trained or relabeled. New target code adds guarded role/entry-point support and leaves the model, loss, optimizer, controller, candidate retention and frozen recipes unchanged.

Static coordinate audit found **zero** selected entity-budget pairs sharing exact coordinates with prefix-trainable Sources of their own namespace, and zero selected peer-coordinate matches within namespace. No Source coordinates were missing in this audit. These are exact numeric comparisons, not distance/site/trace equivalence tests.

Cross-release Shenzhen audit found **27exact selected-ID→Source-ID coordinate pairs**:21UrbanEV selected IDs match CHARGED SZH Sources and6CHARGED SZH selected IDs match UrbanEV Sources. No selected-UrbanEV/selected-CHARGED-SZH coordinate pair matched. This rules out any global physical-disjointness claim; nonmatches do not establish independence. Source models remain strictly separate by namespace; no cross-release model/label pooling is introduced. Coordinates alone do not establish duplicate traces or a causal leakage mechanism. IDs were not reselected after this audit. Original raw archives were not freshly downloaded/rehashed locally; reading identified static coordinate files is not upstream availability/causality certification.

## Implemented guarded interfaces and verification limits

`tools.final_replay` authorizes **before constructing any Final value reader**. The gate requires a clean tracked lock at the open PR52 head into dev, a current-head non-author GitHub APPROVED review, explicit lead Issue23 lines naming the exact lock SHA, and a measured CUDA runtime profile. The three lines are `DEVELOPMENT_ACCEPTED <sha256>`, `FINAL_CAPACITY_ACCEPTED <sha256>` and `FINAL_EXECUTION_APPROVED <sha256>`. These are a concrete review proposal, not approval already obtained. GitHub evidence is fetched live; unavailable, stale, author-only or withdrawn review/markers fail closed. Ordinary InputRun/CLI still reject Final target values. This is a procedural research gate, not a sandbox against someone editing Python.

The Final adapter checks selected target, exact input/Source population, seed-specific config, reused Source bytes and exact locked runtime. Uncertainty reuses exactly the three locked Source checkpoints. Resume uses the same daily Store binding, committed forecast/event chain and full latest model/optimizer/RNG/controller/cursor/pending/audit state. A separately bound/fsynced initialization record permits resume before `run.json` exists without refitting initial adaptation. Environment/config/Source/code differences reject resume.

Final verification checks the report against saved binding, rehashes daily files and recomputes scores from selected labels; latest-state verification CPU-loads/re-hashes branch contents. `tools.analyze_final` requires every locked cell for one complete namespace, fresh daily/latest proofs and common issued/scored origins before reusing the existing station-first metrics, gain/NTR, context/proxy/switch/audit/cost and calendar-block interval helpers. Prefix density thresholds are the existing21Development values; assignment occurs only after approval, with no Final threshold fit. Nulls and zero denominators retain the existing policies.

All five README checks passed locally: source listing,401offline tests, Ruff lint, Ruff format for218Python files and diff checks. Independent synthetic producer fixtures verified the Final reader, delayed-label boundary, exact resume semantics and independent daily verifier. Full/resumed branch/model/optimizer/RNG, pending, scores, active policy, next cursor, audit and step identities agree. Tampered artifacts, changed lock/Source/config, unselected IDs and missing/stale/author approval fail. Synthetic logs, inputs and checkpoints are retained with a manifest. A wrapper regression reaches Store creation with synthetic Source tensors and proves resume never calls initial training even without a prior `run.json`. These are fixture/CPU observations, **not a production CUDA E2E benchmark or research effectiveness evidence**. The analysis collector has focused completeness/density tests and reuses tested mathematical helpers; full real Final collection execution remains prohibited and unverified.

## Measured observations and remaining capacity gate

All seven complete Development matrices provide observed14-method whole-unit process sums. Scaling budget-specific observed minima/maxima to this cohort gives an illustrative **16.71–26.84serial runner-hour** range. This is neither a confidence interval, provider wall time, compute-unit quote nor E2E delivery promise. Sparse/null UrbanEV and mixed T4/A100/CUDA Development environments restrict transfer of these rates. Data/setup, Source restoration, transport, verification, failures, idle allocation, analysis and review add time; no specific concurrency/speedup is promised.

Observed-copy extrapolation gives5.63–39.94GB logical retained target bytes; all21opaque input artifacts total10,929,850,639bytes, and materialized Source checkpoint/sidecar/report payload totals13,829,041bytes. These are external-resource planning observations, not measured provider scratch requirements. Logical retained-run bytes, archive bytes, allocated scratch and provider peak are different quantities; compressed/extracted copies overlap. Original Sources are charged once. Selected resumed reports retain current-invocation elapsed separately from cumulative state counters; predecessor invocations must be retained and unknown costs remain unknown, not zero.

No current CUDA allocation/profile or measured full transport/verification envelope is available. A preflight on an authorized allocation must restore the pinned code/input/Source bytes, record actual runtime/storage/throughput and validate a safe permitted fixture/Development path before a revised exact lock can be reviewed. Preserve one whole-unit/14-cell/20-minute dispatch bound,120-second no-completed-run deadman,30-unit reserve and full external readback before subsequent units. Failed capacity cannot justify dropping cells or buying resources.

## Human review blockers

1. Hung's scientific Development acceptance, including adverse AMS/seed sensitivity, all crossing-zero intervals, nulls, cost limitations and cross-release overlap.
2. Authorized measured CUDA/scratch/durable capacity and transport/verification envelope; fill a **new** runtime-bound lock candidate and retain this candidate unchanged.
3. Independent review of the current code/cohort/analysis/Source/lock and explicit lead execution acceptance for that exact lock. Scope approval alone does not satisfy this gate.
4. GitHub Actions remains blocked by account billing; local checks do not establish Windows execution. The lead instructed proceeding with the pushed handoff despite that blocker; billing/protections were not changed. No autonomous merge follows.

Issue23 and draft PR52 remain the tracking/review destinations. The sole schedule remains `docs/SPRINT_PLAN.md`. Further Final execution, scope enlargement, method changes, merge/main promotion and issue closure remain unauthorized.
