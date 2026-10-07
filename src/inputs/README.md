# Published-release input pipeline

Run from repository root with the same Python/dependencies as `src/data`:

```powershell
python -m unittest src.inputs.test_inputs -v
python -m src.inputs.build --dataset urbanev --run-id UNIQUE_URBAN_RUN
python -m src.inputs.build --dataset charged --run-id UNIQUE_CHARGED_RUN
```

`--limit-per-role 3` is smoke only. It still locks all split IDs and computes the fallback from the complete source-role prefix. Existing run IDs are rejected, not overwritten. Configuration is locked to the user-approved 2026-10-04 protocol in `build.py`; each run persists its exact config, code hashes/snapshots and provenance.

Local index: `data/inputs/<dataset>/<run_id>/window_index.parquet`. Audit/plots/reports: `reports/inputs/<run_id>/`. The large local indices, canonical panels and raw archives are excluded from Git. Rebuild requires those exact local panels; hashes identify them. No model, controller or experiment is run.

```python
from src.inputs.core import InputLoader

loader = InputLoader('data/inputs/urbanev/urbanev_inputs_full_20261004_02')
sample = loader.load(0)                         # offline X_hist/C_future
row = loader.index.iloc[0]
scored = loader.load(0, include_labels=True,
                     as_of=max(row.assumed_available_at, row.scaler_frozen_at))
# A stream prediction may be made even if future labels are incomplete:
inputs = loader.forecast(entity_id, budget_days=7, origin='2022-12-01')
```

Warmup/source indices are offline batch samples available at deployment, not historical online predictions. The scale uses the entire approved prefix and is frozen at deployment. `forecast` rejects source entities and predeployment origins. Main index excludes incomplete labels; it must not be used as the sole schedule for live forecasts. Use daily origins with `forecast` and consult scoring index only for evaluation.

Input math: `s = percentile95(valid permitted-prefix energy)` with source-positive p95 fallback, then 1 kWh if no source positives exist. Observed release values use `x=e/s, mask=1`; missing use `x=0, mask=0`. Labels use `y=e/s` only for complete24 labels. Inverse prediction `energy_kwh = prediction_scaled * s`. Mask means numerical file validity, not proof of original observation. Both tensors are float32; X `[24,7]`, future calendar `[24,5]`, Y `[24]`. Calendar order is recorded in config.

Fallback positives come only from eligible source-training entities before cutoff. Source windows permit masked history (at least one valid X hour and24 valid Y hours); the full48-hour eligibility rule applies only to the target cohort in its7-day warmup. `python -m src.inputs.qa --primary RUN --repeat REBUILD_RUN` checks a complete rerun, recalculates every scaler and emits prefix missing/zero QC.

Physical timezone/bin convention, original masks, real label arrival and Shenzhen independence remain unverified. Local causal guards do not repair publisher interpolation or IQR processing. Availability is only the explicitly assumed exclusive horizon end/next midnight. CHARGED is replication within its own release, not independent UrbanEV generalization.
