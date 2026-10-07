# Bàn giao phase đầu vào model — 04/10/2026

**Đã nghiệm thu cả UrbanEV và CHARGED cho published-data benchmark.** Không huấn luyện model/controller/experiment. Nguồn chuẩn Report1; kế hoạch hiện hành [plan.md](plan.md).

## Kết quả thực

| Dataset | Source đủ/total | Development đủ/total | Final đủ/total | Window records |
| --- | --- | --- | --- | --- |
| urbanev | 898/1009 | 292/336 | 292/337 | 226486 |
| charged | 2567/2567 | 856/856 | 857/857 | 782616 |

Window records tính theo entity × budget × origin, gồm source, warmup và stream; ba budgets là thí nghiệm riêng, không coi records là các forecast độc lập. UrbanEV final292 vượt gate100. Source/dev/final không giao nhau; CHARGED chia hash riêng từng city.

UrbanEV stream01/12/2022–28/02/2023 (90 daily origins); CHARGED01/07–30/09/2023 (92). Warmup có6/13/27 daily origins theo budgets7/14/28 trước khi loại incomplete labels. Source labels và input đều trước cutoff; target warmup toàn X/Y nằm trong budget. Target cohort khóa bằng full48 trong7 ngày; source chỉ cần một window full24Y và nonemptyX, không áp gate full48 của target.

Scale-only p95 linear trên prefix entity/budget; fallback positive-source-training p95 cùng dataset (UrbanEV117.25kWh; CHARGED175.085625kWh), nếu không có positive dùng1kWh. Không center/fit stream. MissingX=scaled0/mask0; zero hợp lệ mask1; Y không fill. Strata zero chỉ dùng lịch sử ban đầu được phép.

X_hist float32[24,7], C_future float32[24,5], Y float32[24]. Tensor contract/loader: [src/inputs/README.md](src/inputs/README.md). `load()` là offline sampler; labels cần as_of hợp lệ và scaler frozen tại cutoff. `forecast()` tạo input stream cả khi future labels thiếu; main index là retrospective train/score index, không dùng nó làm lịch forecast duy nhất.

## Evidence và visual

- [UrbanEV report](reports/inputs/urbanev_inputs_full_20261004_02/input_report.md), [QC/tái lập](reports/inputs/urbanev_inputs_full_20261004_02/qc_supplement.md).
- [CHARGED report](reports/inputs/charged_inputs_full_20261004_02/input_report.md), [QC/tái lập](reports/inputs/charged_inputs_full_20261004_02/qc_supplement.md).
- [Gallery10 visual](reports/inputs/index.html): cohort, scales, masked window, zero-prefix và missing/zero distributions cho mỗi bộ.
- [Execution summary](reports/inputs/execution_summary.json), [active run manifest](reports/inputs/active_runs.json).

11 fixtures đầu vào và13 regression data pass. Readback39 UrbanEV +234 CHARGED samples đầu/giữa/cuối từng city/role/budget/phase. Rebuild cả hai bộ: tất cả split/cohort/scalers/index values/audit counts khớp, tensors mẫu bit-exact; mọi scaler được tính lại từ prefix. Future perturbation trên18 UrbanEV và108 CHARGED stream samples giữ nguyên X/calendar/scale/cohort; không claim loại leakage upstream.

Raw/panel hashes giống nhau giữa primary và rebuild; PDF Git blob khớpHEAD. Không sửa raw/candidate panel/PDF hoặc ghi đè run cũ. Index Parquet local dưới `data/inputs/<dataset>/<active_run>/`; không materialize toàn bộ tensors.

## File đã thêm/sửa

- `src/inputs/__init__.py`, `core.py`, `build.py`, `qa.py`, `test_inputs.py`, `README.md`: protocol, CLI, lazy loader, fixtures và readback/tái lập.
- `.gitignore`: thêm `data/inputs/`; `README.md`: links và scope phase mới; `plan.md`: protocol và trạng thái thực thi.
- `data/inputs/`: versioned window indices (local). `reports/inputs/`: contracts/config/manifests/scalers/cohort/audit/counts/ranges/checks/logs/source snapshots/figures/HTML/Markdown; danh sách artifact mỗi run được ghi manifest.
- `BAO_CAO_DAU_VAO_MODEL.md`: báo cáo bàn giao này. Các run rebuild là evidence QA; các runv1 được giữ với `superseded_by.json`, không phải active.

## Lệnh đã chạy và cách tái chạy

Runtime thực: bundled Python3.12 cùng `.deps`, cấu hình/version tại manifests. Chạy từ project root; mọi build mới cần run_id chưa tồn tại. Với `python` trỏ đúng runtime:

```powershell
python -m unittest src.inputs.test_inputs -v
python -m unittest discover -s src/data -p 'test_*.py' -v
python -m src.inputs.build --dataset urbanev --run-id urbanev_inputs_smoke_20261004_03 --limit-per-role 3
python -m src.inputs.build --dataset urbanev --run-id urbanev_inputs_full_20261004_02
python -m src.inputs.build --dataset urbanev --run-id urbanev_inputs_repro_20261004_02
python -m src.inputs.qa --primary urbanev_inputs_full_20261004_02 --repeat urbanev_inputs_repro_20261004_02
python -m src.inputs.build --dataset charged --run-id charged_inputs_full_20261004_02
python -m src.inputs.build --dataset charged --run-id charged_inputs_repro_20261004_02
python -m src.inputs.qa --primary charged_inputs_full_20261004_02 --repeat charged_inputs_repro_20261004_02
python -m compileall -q src/inputs
git diff --check
git hash-object adaptive_retention_report_1.pdf
git rev-parse HEAD:adaptive_retention_report_1.pdf
```

Các run IDs trong lệnh đã tồn tại; thay bằng UNIQUE_ID để tái dựng, không ghi đè. QA cũng giữ artifacts cũ. Regression command cũ import package names lỗi vì legacy tests dùng imports trực tiếp; command discover ở trên đã pass. Git cảnh báo LF→CRLF trên working copy, `diff --check` pass.

## Lỗi đã sửa, giới hạn và việc chưa làm

Smoke đầu tiên lỗi xuất Markdown do thiếutabulate; đã bỏ dependency và chạy smoke mới thành công. V1 gate source full48 quá chặt, bỏ sót một source station có input masked dùng được; fallback còn chứa source không có training window. Đã thêm fixture/sửa scope và rebuildv2. Final hash split, target cohort/dates không thay đổi; đây là sửa logic theo plan, không tuning bằng final error. Các runv1/partial không xóa.

Clock phát hành chưa xác minh timezone/DST/bin vật lý. Actual label_available_at vẫn unknown; benchmark giả định vector24labels available đúng exclusive horizon end/00:00 ngày kế tiếp, lưu assumed_available_at riêng. Mask phản ánh validity trong release, không proof original observed. CHARGED có interpolation/IQR; chỉ benchmark trong release, Shenzhen chưa xác minh độc lập với UrbanEV. Strict online gate chưa đạt.

Model/loss/latent64/frozen-source encoder/controller/baselines, costs và full experiments còn ở phase sau. Không dùng final để chọn model/hyperparameter/threshold/calibration. Split60/20/20 và scale-only là thiết kế được chọn, chưa chứng minh tối ưu.

## Đối chiếu trạng thái — 04/10/2026

Lần cập nhật tài liệu đã đối chiếu execution summaries của data/input, active runs, data readback và QC supplements hai bộ. Các kết quả PASS ở trên là evidence đã lưu của runs được bàn giao; không chạy lại full processing/rebuild hoặc training trong lần cập nhật này.

Lệnh kiểm tra lại `python -m unittest src.inputs.test_inputs -v` **exit 1 ở bước import**, chưa chạy được 11 fixtures: `python` hiện là 3.13, nhưng NumPy trong `.deps` có extension `cp312-win_amd64`. Cần chạy bằng Python 3.12 tương thích như runtime của full runs; chưa sửa dependencies hoặc thay dữ liệu/run cũ. Đây là lỗi runtime của lần kiểm tra lại, không phải kết luận fixtures/model thất bại.

File cập nhật: `README.md`, `BAO_CAO_PHASE_DATA.md`, `BAO_CAO_DAU_VAO_MODEL.md`, `plan.md`. Strict online, model/controller và experiments vẫn chưa hoàn thành.

## Kiểm tra lại — 07/10/2026

Bundled Python 3.12: `-m unittest src.inputs.test_inputs -v` (11 PASS) và `-m unittest discover -s src/data -p "test_*.py" -v` (13 PASS), exit 0. Lỗi runtime 3.13 trước được tránh bằng runtime đúng. Không sửa dependencies hoặc full rebuild. Đã bổ sung Input gallery index thiếu; chưa browser visual QA trong lần này. [Evidence mới](reports/review/roadmap_20261007/verification.json). Chưa model training.
