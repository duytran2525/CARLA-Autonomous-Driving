# M56 — chỉ mục lưu trữ trên Google Drive (2026-11-14)

**Dành cho agent khác: đọc file này trước khi tìm dữ liệu chạy cũ của M56.**

## Cái gì đã lên Drive, ở đâu

- Vị trí: Google Drive của Duy, ổ `G:\My Drive\M56_ARCHIVE_20261114\<tên root>.tar.zst` (mỗi root trong `outputs/` là một file `.tar.zst`; zstd level 9).
- Danh sách chính xác từng root (đường dẫn Drive, sha256, số file, số byte): `outputs/m56_drive_archive_manifest_20261114.jsonl` (bản sao đã commit: `docs/m56/M56_DRIVE_ARCHIVE_MANIFEST_20261114.jsonl`). Mỗi dòng chỉ có mặt sau khi đã tải lại file từ Drive, kiểm sha256 và so số file/số byte với nguồn.
- Phạm vi: các root `m56_*` trong `outputs/` (pair `m56_v6_pair_*`, A/B `m56_v2_ab_*`, `m56_io_ab_*`, `m56_offline_v1`, ...) cũ hơn 3 giờ và nặng ≥ 50 MB, đã chạy xong hoặc FAILED. Không động tới `m56_f_*` (chuỗi F) và các root nhỏ.

## Cái gì còn ở máy

- Mỗi root vẫn còn thư mục cũ nhưng chỉ chứa file kết quả nhỏ: `pair-result.json`, `ab-result.json`, `fixture-frozen.json`, `prepare.json`, `a2-bbox.json`, `plan-source.json`, `ab-report.json`, `ab-log.json`. Các bước pair, ledger, release đọc các file này.
- Bản đầy đủ của phần nặng (`run/native`, `run/episodes`, `w05-*`, `d09`, journal, ...) đã được **chuyển** (không xóa) sang `outputs/_TRASH_UPLOADED_20261114/<root>/`. Duy tự xóa thư mục đó khi muốn: `Remove-Item -Recurse -Force outputs\_TRASH_UPLOADED_20261114`.
- Nếu thư mục trash đã bị xóa mà cần dữ liệu nặng: tải `<root>.tar.zst` từ Drive, kiểm `sha256` theo manifest, rồi giải nén (`zstd -d` rồi `tar -xf`, hoặc Python `zstandard`) vào `outputs/`.

## Kết quả đã ghi riêng để khỏi phải mở archive

- `docs/m56/M56_RUN_RESULTS_DIGEST_20261114.csv` — mỗi dòng là một `pair-result.json` hoặc `ab-result.json` của mọi lần chạy (root, cảnh, status, witness A/B, physical A/B, số so sánh, lý do chặn). Sinh bằng `run-results-digest.py`.
- Cách đọc: một cảnh có thể xuất hiện nhiều dòng vì được chấm lại dưới nhiều consumer (v6, v10, v12, v13). Dòng `pair` dưới root `m56_v6_pair_*` là lần chấm lại offline, không phải lần chạy CARLA mới. Mỗi cảnh chỉ có đúng một lần A/B native (P5).
- Tổng hợp tại thời điểm ghi: 136 dòng pair (PASS 36, BLOCKED_WITNESS 56, FAILED 44) trên 49 cảnh; 95 dòng ab. Phân tích nguyên nhân và quyết định: `docs/m56/M56_ASEL2_BATCH_LOG_20261108.md`.

## Quy tắc cho agent khác

- Không chạy lại cảnh nào đã có A/B (P5). Không chạy lại cảnh I khi chưa có recipe I mới được Duy duyệt.
- Không sửa byte spec. Kết quả gắn nhãn `CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent`.
- `m56_f_*` và chuỗi F (r7) không nằm trong archive này.
