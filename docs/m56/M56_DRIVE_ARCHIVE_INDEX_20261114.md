# M56 — chỉ mục lưu trữ trên Google Drive (2026-11-14)

**Dành cho agent khác: đọc file này trước khi tìm dữ liệu chạy cũ của M56.**

## Cái gì đã lên Drive, ở đâu

- Vị trí: Google Drive của Duy, ổ `G:\My Drive\M56_ARCHIVE_20261114\<tên root>.tar.zst` (mỗi root trong `outputs/` là một file `.tar.zst`; zstd level 9).
- Danh sách chính xác từng root (đường dẫn Drive, sha256, số file, số byte): `outputs/m56_drive_archive_manifest_20261114.jsonl` (bản sao đã commit: `docs/m56/M56_DRIVE_ARCHIVE_MANIFEST_20261114.jsonl`). Mỗi dòng chỉ có mặt sau khi file đã được đọc lại qua ổ G:, kiểm sha256 và so số file/số byte với nguồn. Việc đọc lại đó có thể đi qua cache cục bộ của Google Drive for Desktop: nó chứng minh file archive đúng, **không** chứng minh Drive đã upload xong lên mây. Trước khi xóa thùng rác local, phải xác nhận trên drive.google.com (hoặc khay Drive báo hết hàng đợi upload).
- Phạm vi: các root `m56_*` trong `outputs/` cũ hơn 3 giờ và nặng ≥ 50 MB. **Chưa nén xong mọi root**: manifest là danh sách duy nhất đúng.
- Từ r3 (14/11 ~12:20Z) script **bỏ qua**: `m56_f_*`; root không có dấu thời gian (như `m56_offline_v1`, là input của revision); root có dấu thời gian ≥ 20261108 (đợt A-SEL2, còn đang phân tích); root chứa một cảnh từng PASS (`asel2-release.py --full` đọc lại episode đã niêm phong và D09 của nó).
- **Có trên Drive nhưng đã đưa về đủ tại chỗ:** các root trong `outputs/m56_drive_archive_restored_in_place_20261114.txt` (39 root, gồm `m56_offline_v1` đưa về trước đó). Bản đầy đủ của chúng nằm ở `outputs/`, không phải trong thùng rác. Bản khung cũ (chỉ có file nhỏ) của chúng nằm ở `_TRASH_UPLOADED_20261114/<root>.skeleton`.

## Cái gì còn ở máy

- Mỗi root đã archive vẫn còn thư mục cũ nhưng chỉ chứa file kết quả nhỏ: `pair-result.json`, `ab-result.json`, `fixture-frozen.json`, `prepare.json`, `a2-bbox.json`, `plan-source.json`, `ab_report.json`, `ab-log.json` và (từ r3) `runner/stop.json`. Với các root archive trước r3, `stop.json` không còn tại chỗ: một root I/O A/B không còn `run/` **không có nghĩa** là chưa chạy A/B; xem manifest và thùng rác.
- `native-v6-pair.py` và `asel2-release.py --full` cần `run/` đầy đủ. Muốn chấm lại một root đã archive, phải lấy lại nó trước.
- Bản đầy đủ của phần nặng (`run/native`, `run/episodes`, `w05-*`, `d09`, journal, ...) đã được **chuyển** (không xóa) sang `outputs/_TRASH_UPLOADED_20261114/<root>/`. Duy tự xóa thư mục đó khi muốn: `Remove-Item -Recurse -Force outputs\_TRASH_UPLOADED_20261114`.
- Nếu thư mục trash đã bị xóa mà cần dữ liệu nặng: tải `<root>.tar.zst` từ Drive, kiểm `sha256` theo manifest, rồi giải nén (`zstd -d` rồi `tar -xf`, hoặc Python `zstandard`) vào `outputs/`.

## Kết quả đã ghi riêng để khỏi phải mở archive

- `docs/m56/M56_RUN_RESULTS_DIGEST_20261114.csv` — mỗi dòng là một `pair-result.json` hoặc `ab-result.json` của mọi lần chạy (root, cảnh, status, witness A/B, physical A/B, số so sánh, lý do chặn). Sinh bằng `run-results-digest.py`.
- Cách đọc: một cảnh có thể xuất hiện nhiều dòng vì được chấm lại dưới nhiều consumer (v6, v10, v12, v13). Dòng `pair` dưới root `m56_v6_pair_*` là lần chấm lại offline, không phải lần chạy CARLA mới. Mỗi cảnh chỉ có đúng một lần A/B native (P5).
- Tổng hợp tại thời điểm ghi: 136 dòng pair (PASS 36, BLOCKED_WITNESS 56, FAILED 44) trên 49 cảnh; 95 dòng ab. Phân tích nguyên nhân và quyết định: `docs/m56/M56_ASEL2_BATCH_LOG_20261108.md`.

## Quy tắc cho agent khác

- Không chạy lại cảnh nào đã có A/B (P5). Không chạy lại cảnh I khi chưa có recipe I mới được Duy duyệt.
- Không sửa byte spec. Kết quả gắn nhãn `CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent`.
- `m56_f_*` và chuỗi F (r7, r8) không nằm trong archive này.
- Digest chỉ có dòng cho cảnh có `pair-result.json` hoặc `ab-result.json`. Cảnh mà pair bị crash (như I01-S1, `EPISODE_NOT_SEALED:A`) không có dòng; xem batch log.
