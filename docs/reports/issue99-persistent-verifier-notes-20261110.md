# Independent verifier preparation — 2026-11-10

File: `tools/issue99_persistent_verify.py` (591 lines). It is one cohesive read-only auditor for pilot, Calibration, and conditional Later runs. Its length comes from independently checking the persisted tick chain, issued forecast vectors, delayed labels, controller decisions, pair identity, paired coverage, and promotion gate in one pass.

## Code-only checks run locally

In `D:\Đồ Án\.cache\issue99-persistent-lambda`:

```powershell
$env:PYTHONPATH='.cache/dev-tools'; python -m ruff format tools/issue99_persistent_verify.py; python -m ruff check tools/issue99_persistent_verify.py; python -m py_compile tools/issue99_persistent_verify.py; python -m tools.issue99_persistent_verify --help
```

Result: Ruff formatted the file; Ruff check passed; compilation passed; `--help` showed the pilot, calibration, and evaluation phase choices. An earlier `ruff format --check` reported formatting differences, which were resolved by the subsequent format command. No local model, data replay, or metric verification ran. These code-only checks preceded the later instruction to stop local lint/testing.

## Kaggle execution and output contract

Run inside Kaggle against the locked stage input and protocol:

```bash
python -m tools.issue99_persistent_verify --phase pilot --root /kaggle/working/issue99-persistent-v1 --inputs "$STAGE/inputs" --protocol configs/issue99-persistent-protocol-v1.json --output /kaggle/working/issue99-persistent-v1/pilot-independent-verification.json
python -m tools.issue99_persistent_verify --phase calibration --root /kaggle/working/issue99-persistent-v1 --inputs "$STAGE/inputs" --protocol configs/issue99-persistent-protocol-v1.json --output /kaggle/working/issue99-persistent-v1/independent-verification.json
python -m tools.issue99_persistent_verify --phase evaluation --root /kaggle/working/issue99-persistent-v1 --inputs "$STAGE/inputs" --protocol configs/issue99-persistent-protocol-v1.json --output /kaggle/working/issue99-persistent-v1/later-independent-verification.json
```

`$STAGE` is a Kaggle runtime placeholder, not a measured path. The verifier creates each output with exclusive mode and refuses overwrite. Pilot records zero empirical proposals/decisions if observed. For each target/seed pilot case, it recomputes MAE from the **actual** Persistent and Fixed trajectories on identical complete scored origins and stops Calibration if Persistent minus Fixed exceeds +0.05 kWh. Shadow candidate differences are excluded from this external screen; they are checked separately for controller decision integrity. Calibration reports integrity `status=PASS` separately from numerical `gate_pass`, and binds the SHA-256 of `calibration-gate.json`. Later recomputes 48 paired cells only if dispatched after both gates. All empirical results remain pending Kaggle execution. A focused synthetic test in `tests/test_issue99_persistent_verify.py` distinguishes rejected shadow harm from actual trajectory harm; it has been prepared for Kaggle execution and has not been run locally.
