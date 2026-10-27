# M56 consumer v8: onset ngang chịu nhiễu và dấu separation theo trục (ĐÃ DUYỆT)

**Thẩm quyền:** [chat] 27/10/2026, Duy: "duyệt PROPOSAL_M56_IO_ONSET_NOISE_20261027 thành consumer v8 (erratum); đánh giá lại offline
O03 v1.1 đã seal, báo theo cả hai luật. Duyệt luôn PROPOSAL_M56_IO_AXIS_SIGN cho O01/O02/I01/I02."

**Nguồn gốc:**
- Luật onset được đặt **sau khi thấy** episode A của O03 v1.1. Mọi kết quả phải báo theo cả luật v7 và luật v8.
- Luật dấu separation không dựa trên số episode nào; nó đến từ việc đọc code.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Code:** `feat/m56-v8` `5635d6c`, tách từ `feat/m56-v7` `7da367b` (đã gồm các bản sửa hiệu năng I/O và `plan_refs`).

## Luật

| # | Chỗ áp dụng | Cũ (v7) | Mới (v8) |
|---|---|---|---|
| 1 | `metrics._lateral_departure` (onset đi ra của O-A và I-B) | Xét từ TRIGGER, frame đầu tiên có offset thay đổi bất kỳ là frame quyết định. Thay đổi 0 < Δ ≤ 2u thì kết luận `LANE_CHANGE_ONSET_UNCERTAIN` | Thay đổi Δ ≤ 2u là nhiễu và bị bỏ qua. Onset là frame đầu tiên có Δ > 2u |
| 2 | `metrics._o_return_action` (điểm bắt đầu quay về) | Mọi lần giảm ≤ 2u đều bị ghi `RETURN_LATERAL_START_UNCERTAIN` | Lần giảm ≤ 2u là nhiễu. Điểm bắt đầu quay về là lần giảm đầu tiên > 2u |
| 3 | `response.step_response` O-A, chọn guard quay về | `separation` = hiệu tọa độ y | `_lateral_separation`: hiệu trên trục ngang, nhân với dấu của vector phải CARLA (`_axis_right`), giống `_lateral_axis_v5`. Trên route theo +x, kết quả giống hệt v7 |

**Không đổi:** ngưỡng 2u; `OUTBOUND_BEFORE_DECISION`; `RETURN_STARTED_BEFORE_FIXED_MARKER`; các proof đường đi; mọi phép kiểm
khác.

## Áp dụng

- **Luật 1–2:** không có phần online nào đọc chúng, nên không cần chạy lại. Episode O03 v1.1 đã seal được đánh giá lại offline
  bằng `native-v6-pair.py` với `M56_CODE=../m56-v8`.
- **Luật 3:** nằm trong `step_response`, tức là online. Nó chỉ có hiệu lực ở các A/B sau này của O01/O02/I01/I02.
  - Với O03 (+x), luật 3 cho kết quả giống hệt v7. Do đó việc đánh giá lại offline không bị ảnh hưởng.
- **Test:** `tests/m56/test_v8_io_onset_axis.py` (nhiễu dưới mức uncertainty bị bỏ qua và tìm ra onset thật; dấu separation ở các
  hướng 0, 180, −90 và −180,2).
