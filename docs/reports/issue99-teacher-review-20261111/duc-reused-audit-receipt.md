@huuduc32 — **artifact-access blocker is now resolved, and the full reviewer-side artifact audit has passed.** This supersedes the earlier 404/access statements.

Readback against the unchanged committed ledgers/session at a2a7b6d:
- Listed the entire 190-item session root (not the truncated 100-item folder preview), including all 187 run/Source folders.
- Downloaded all **737 files / 161,061,658 bytes** through authenticated file references, with no failed downloads or size discrepancies.
- All **532 per-run manifest entries** match their actual file bytes. All **15 Source checkpoint hashes** match source.json and every transfer row binds to its correct backbone/seed Source checkpoint.
- Drive runs.csv, runs_graph.csv and session.json are byte-identical to the committed copies.
- Reimplemented readback independently of the notebook: verified all **172 runs**, **11,481 issued forecasts**, **10,535 scored forecasts / 252,840 hourly predictions**, and every daily/run MAE/RMSE. No mismatch.
- Matched every scored ground-truth vector against the local authenticated prepared labels; checked complete-label eligibility, actual arrival timestamps, forecast-before-label ordering, monotonically ordered replay events and full schedule/skip accounting. No mismatch.
- Exact common scored-origin identities agree across configurations within each station, and all **60/60 matched within-backbone Transfer pairs** improve on Target-only.
- Safely loaded all **147 tensor checkpoint files** with torch.load(weights_only=True); all model weight tensors are finite. Joblib estimators were hashed but deliberately not deserialized/executed.
- CI run 42885607831 passed on Ubuntu and Windows. Source identifier and immutable notebook exclusion were already checked.

Independent metric readback: TimeXer transfer 5.197934, TCN transfer 5.302738, GRU transfer 5.315693, LSTM transfer 5.316825, graph 7.178997 kWh. No statistical superiority is asserted.

**Disposition:** execution completeness, transport/hash integrity, daily metric readback, common-origin identity and the previously reported technical CI/access findings now pass. Do not continue listing reviewer access/per-origin readback as outstanding; update the report/PR status with this evidence.

**The remaining acceptance decision is scope**, not an artifact defect: neither study performed the originally requested advance joint protocol/tuning process. An explicit lead decision is needed to accept this as a fixed-recipe exploratory Development study or to require a separately registered harmonized/tuned follow-up. No retroactive lock, retraining merely to fix historical lint, or new Final claim is requested. Full training reproduction, upstream raw-data audit and bootstrap superiority analysis were not performed here. I am not merging or closing #96 on this scope decision's behalf.
