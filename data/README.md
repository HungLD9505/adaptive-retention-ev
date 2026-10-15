# Nguồn dữ liệu — tải về để xây pipeline mới

Catalog chuẩn: [sources.json](sources.json). File này chứa URL tải, release, đường dẫn local, số bytes, SHA-256 và publisher checksum nếu có. Các giá trị được trích từ [acquisition manifest lịch sử](https://github.com/HungLD9505/adaptive-retention-ev/blob/528680dd73791322ed12f32b2c72a3b58618a428/reports/data/acquisition_20261002_03/source_manifest.json), ngày 02/10/2026.

**Chưa tải hoặc kiểm tra lại archive thật trong lần dựng foundation này.** SHA-256 là fingerprints team ghi ở lần acquisition trước, không trình bày như SHA-256 do publisher công bố. CHARGED còn có MD5 publisher được ghi trong manifest. Lệnh `list` chỉ đọc catalog, không xác nhận URL đang tải được.

## Lấy những gói nào?

| Source ID | Gói | Bytes đã ghi | Bắt buộc? |
|---|---|---:|---|
| `urbanev-main` | `UrbanEVDataset.zip` từ official Drive mirror | 647.305.188 | Có, khi làm UrbanEV |
| `urbanev-supplemental` | `UrbanEVSupplemental.zip` | 6.052.188 | Không; chưa mặc định dùng weather/POI làm features |
| `charged-hourly` | Standard `Hourly.zip`, Zenodo record 15814263 | 268.720.500 | Có, khi làm CHARGED |

Nguồn chính thức: [UrbanEV repository](https://github.com/IntelligentSystemsLab/UrbanEV), [CHARGED Zenodo release](https://zenodo.org/records/15814263), [CHARGED repository](https://github.com/IntelligentSystemsLab/CHARGED).

## Cách tải và kiểm tra

1. Từ root repo, xem URL và đúng vị trí cần đặt file:

   ```sh
   python -m tools.sources list
   ```

2. Nếu team còn bản raw cũ, sao chép nguyên bytes về đúng đường dẫn; nếu chưa có, mở URL trong catalog để tải từ provider. Không ghi đè một file đã có; kiểm tra file đó trước. Gói Drive có thể cần thao tác trong browser. Nếu link hết hiệu lực, quay lại nguồn chính thức và ghi evidence; không thay release/hash âm thầm.

   ```text
   data/raw/urbanev/official_2026_05_11/UrbanEVDataset.zip
   data/raw/urbanev/official_2026_05_11/UrbanEVSupplemental.zip  # optional
   data/raw/charged/zenodo_15814263/Hourly.zip
   ```

3. Kiểm tra size, SHA-256 và publisher checksum đã ghi:

   ```sh
   python -m tools.sources verify --dataset urbanev
   python -m tools.sources verify --dataset charged
   ```

   Không chỉ định dataset thì kiểm tra cả hai gói bắt buộc. Muốn kiểm tra cả supplemental, thêm `--include-optional`; khi đó thiếu supplemental cũng trả failure.

   Có thể giữ data trên ổ khác có cùng cây `data/raw/`:

   ```sh
   python -m tools.sources verify --root /path/to/storage-root
   ```

4. Exit code **0**: tất cả file được chọn khớp; **1**: có file thiếu/sai size/checksum; **2**: catalog/path hoặc lỗi đọc không hợp lệ. Tool chỉ đọc, không tải, extract, sửa, quarantine hoặc thay raw. File sai checksum cần giữ riêng để điều tra; không sửa expected hash để làm PASS.

Không chạy `verify --include-optional` nếu chưa chủ định tải supplemental. CI chỉ kiểm tra catalog và synthetic fixtures; không tải hàng trăm MB dữ liệu.

## Phân biệt raw, processed và inputs

- **Raw:** archive nguyên bytes nhận từ publisher. Giữ ngoài Git và bảo toàn làm đầu vào có thể truy vết.
- **Processed:** output do pipeline mới tạo; chưa được xây trong foundation này.
- **Inputs:** split/scalers/windows/tensors do phase tiếp theo tạo; chưa được xây trên foundation mới.

"Raw" không có nghĩa mọi giá trị đều là quan sát vật lý chưa xử lý. UrbanEV station volume đã là estimate/derived; archive có cả raw và processed variants. CHARGED Hourly là dữ liệu đã được publisher xử lý. Checksum PASS chỉ xác nhận đúng bytes đã ghi, không chứng minh upstream causality, dữ liệu không thiếu hay phù hợp mô hình.

Pipeline mới cần tự audit target/unit, schema, time/bin/availability, missing/zero và khả năng tái lập trước khi bàn giao. Không lấy zone-level thay station-level; CHARGED site là cụm charger. Không coi Shenzhen là external độc lập khi chưa có mapping/evidence. Chưa claim strict online-ready.

## Nguồn lịch sử còn ở đâu?

Code và reports trước reset vẫn ở [backup main](https://github.com/HungLD9505/adaptive-retention-ev/tree/master). Các manifest là bằng chứng acquisition cũ, không phải chứng nhận pipeline mới đã chạy. Nếu cần dùng release khác, tạo PR catalog mới kèm provenance và ảnh hưởng protocol; không đổi catalog hiện tại cho khớp file bất kỳ.
