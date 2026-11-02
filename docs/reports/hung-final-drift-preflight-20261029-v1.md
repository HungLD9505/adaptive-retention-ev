# Hùng Final Drift reference preflight (2026-10-29)

This is a code and synthetic-test milestone; no Final ZIP was extracted and no Final job was run.

The executable lock now requires `drift_reference` with schema `hung-final-drift-reference-v1`, rule `first_created_final_forecast_valid_load_population_sd`, and the Development scale floor `0.1`. Every Drift execution-plan row must leave `drift_reference_mean` and `drift_reference_scale` as `null`. A copied or preselected numeric reference fails lock validation.

After full lock and input-run verification, the dispatcher reads only the selected Final entity's `forecasts.jsonl` and its hash-pinned manifest. It uses the earliest issued forecast's `x_hist`, keeps finite load values with the seventh validity flag equal to one, then calculates the arithmetic mean and population standard deviation, floored at `0.1`. This reproduces the executed Development `_drift_reference` formula with Final role isolation. It does not open `labels.jsonl` for reference derivation.

Before Target initialization, a create-only `drift_reference` stage stores the origin, mean, scale, forecast SHA, input-manifest SHA and lock identity in its manifest and byte receipt. Resume recomputes the same reference from the pinned history and requires exact equality with the receipt-bound stage. Changed history, altered stage bytes, a missing Drift stage behind replay, or an unexpected Drift stage on another method fails closed.

The existing 360-row candidate remains non-executable: this code does not create a lock, supply a resource allocation, extract the input ZIP, or resolve wider CHARGED and scientific review gaps. Local stage completion still needs immutable archive and independent remote readback for Final acceptance.
