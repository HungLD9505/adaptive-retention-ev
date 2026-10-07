# QC bổ sung và tái lập — charged

Primary `charged_inputs_full_20261004_02`; rebuild `charged_inputs_repro_20261004_02` giữ nguyên raw/config/preprocessing code. So sánh tất cả split/cohort/scalers/audit và index values sau khi bỏ run_id. Tensor samples lặp lại bit-exact; scaler được tính lại từ prefix cho mọi entity-budget. Raw/panel hashes không đổi giữa hai lần dựng.

Checks: `{'raw_panel_hashes_unchanged': True, 'preprocessing_code_same': True, 'protocol_same': True, 'split_manifest_reproducible': True, 'cohort_manifest_reproducible': True, 'scalers_reproducible': True, 'window_audit_reproducible': True, 'cohort_counts_reproducible': True, 'window_counts_reproducible': True, 'allowed_prefix_counts_reproducible': True, 'index_values_reproducible': True, 'hash_split_recomputed': True, 'all_scalers_recomputed_from_allowed_prefix': True, 'tensor_repeat_samples': 234, 'real_stream_future_perturbation_samples': 108, 'canonical_actual_availability_not_overwritten': True, 'artifact_hash_readback': True, 'html_and_figures_readback': True, 'passed': True}`.

`prefix_quality.csv` chỉ dùng lịch sử được phép, phân biệt missing/zero; `05_prefix_quality.png` minh họa phân phối. CHARGED missing=0 trong release không chứng minh original observation. `window_ranges.csv` ghi origin đầu/cuối theo city/role/budget/phase.

Future perturbation chỉ bảo vệ X/calendar/scale/cohort đã quyết định trước origin stream. Y và scoring eligibility có thể thay đổi nếu sửa nhãn tương lai; đó là lý do forecast schedule tách khỏi retrospective scoring index. Không claim kiểm tra này loại leakage upstream.

Tái chạy QC: `python -m src.inputs.qa --primary charged_inputs_full_20261004_02 --repeat charged_inputs_repro_20261004_02`. QC từ chối ghi đè artifacts cùng tên; dùng run mới khi thay thiết kế. Model/controller/experiment vẫn chưa thực hiện.
