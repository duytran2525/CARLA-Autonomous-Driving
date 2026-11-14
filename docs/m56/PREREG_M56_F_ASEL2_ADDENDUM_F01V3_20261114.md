# M56 A-SEL2: addendum F01-v3, cổng độ dài site của F01 (14/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** Duy [chat] 14/11/2026: "đổi recipe f01 hỏi advisor các làm cho f01 thành công". Advisor được hỏi trước khi viết.

**Tính chất:** đây là luật **sau khi thấy số** lần thứ hai cho F01 (nguyên tắc 6). Lần thứ nhất là addendum F01-v2 (eabacab).
Số đã thấy trước khi viết:
- F01-S1 FAILED (B tông đuôi trong cửa sổ).
- Tìm site thay thế dưới F01-v2: **EMPTY_NO_ELIGIBLE_CANDIDATE** (`docs/m56/M56_F_SITES_REPLACE_F01_20261114.json`, sha256 7eeeeda7…).
- Độ dài các ứng viên còn lại (chẩn đoán offline, mục 2).

Byte của prereg phần 1 và addendum F01-v2 không đổi. F01 được báo dưới cả ba bộ luật (mục 6).

## 1. Thay đổi (chỉ F01, chỉ cổng site)

| | Prereg phần 1 / F01-v2 | F01-v3 |
|---|---|---|
| Nhu cầu độ dài site của F01 (cổng SECTION_SHORT và B5 trục) | 120 + vE²/3 + 20 = 145,33 m | **91,4 m**, tính từ recipe (mục 3) |
| Trần (F, town) = 3, pool, khóa sắp xếp, seed, dốc ≤ 0,02, first-fit | giữ | giữ |
| d0 15,5, run-out +6, EGO A/B | F01-v2 | giữ |

Kiểm tra chính xác vẫn là `F_WINDOW_TOO_SHORT` của native-f-prepare (route NPC ≥ F01_END + 30 m; route EGO ≥ DESTINATION + 15 m).
Cổng site chỉ là bộ lọc trước.

## 2. Chẩn đoán (offline, không chạy native)

- Site đã lấy: Town12 ×3 (F02 451, F05 164, F06 896), Town13 ×1 (F01-S1 1165). Trần chỉ chặn Town12.
- 36 ứng viên bị trần (đều ở Town12) **cũng trượt cổng**: 19 trượt trục, 17 trượt đoạn. Nới trần không giúp gì.
- Không ứng viên nào trong pool có độ dài dùng được ≥ 100 m. Dài nhất:
  - Town06 road 30 section 0 (93,8 m; trục 95,8; phẳng);
  - Town13 road 1058 (trục 87,1; dốc 0,016);
  - Town06 road 17 (52,8 m).

## 3. Cách tính 91,4 m (từ prepare F01-S1, f-v1.2, `m56_v2_prepare_Town13_20261114T124840Z`)

**Số đo của S1** (d0_r 11,352):
- F01_END: 41,03 m trên frame NPC, 57,23 m trên frame EGO. Vậy gốc route NPC nằm trước gốc EGO 16,20 m.
- DESTINATION của EGO: 67,23 m.

**Dưới F01-v2** (d0 15,5):
- Gốc NPC lùi lên thêm 15,5 − 11,352 = 4,15 m, thành 20,35 m.
- Nhu cầu NPC = 20,35 + 41,03 + 30 (TAIL_M) = **91,38 m**.
- Nhu cầu EGO = (67,23 + 4,15 − 4) + 15 = 82,38 m.
- Nhu cầu site = max(91,38; 82,38) = **91,4 m**, cùng frame với độ dài đoạn − 2 m mà gates() dùng.

**Rủi ro chọn số sau khi thấy dữ liệu, ghi rõ:** con số này được tính sau khi đã thấy độ dài ứng viên. Nó cho qua đúng một road
(Town06 road 30, biên ≈ 2,4 m, khoảng 0,7 s run-in của NPC) và loại Town13 road 1058. Quãng ready trên road khác có thể ăn
hết biên đó.

## 4. Luật dừng (chốt trước khi chạy)

1. `f-site-replace.py ... F01-v3 <commit> 91.4` chạy đúng một lần, output vào file mới. File EMPTY được giữ.
2. Nếu không chọn được site, hoặc stage 1 (prepare + compile + admission) của F01-S2 ra `F_WINDOW_TOO_SHORT`, `D0_OUTSIDE_BAND`,
   BLOCKED, không ADMITTED, hoặc trượt cổng mục 5, thì F01 ghi **FAILED, không có cảnh thay thế**. Không chỉnh TAIL_M, biên,
   d0 hay road thêm nữa.
3. Ngân sách thay cảnh B3 (150) chỉ cộng 1 khi có site được chọn.
4. **A/B của F01-S2 chờ Duy duyệt** sau khi xem stage 1. Đây là lần đổi luật sau số thứ hai, khác town, chỉ một road đạt, và
   lô P5 không làm lại được.

## 5. Cổng khoảng hở trước A/B (thay cổng 2 của F01-v2, chốt trước khi thấy plateau S2)

Plateau S1: vE₁ = 3,862, vN₁ = 3,265 m/s. Quãng mất khoảng hở của B từ ready tới F01_N_CLEAR đo ở S1 là 11,85 m, trong cửa sổ
dài khoảng 13,5 s. Response B kích bằng event (TRIGGER rồi N_MOVE, response.py F01), không theo khoảng hở, nên quãng mất chỉ đổi
theo plateau:

- `loss₂ = 11,85 + 13,5 · max(0; (vE₂ − 3,862) − (vN₂ − 3,265))`
- `gap_N = d0_r − loss₂`
- `gap_dest = gap_N − (gap_N + 6) / vE₂ · (vE₂ − vN₂)`

Điều kiện: **gap_dest ≥ 1,0 m**. Cùng với d0_r trong ±0,3 m của 15,5 (`target_gap_at_ready_m` trong prepare.json phải đọc 15,5),
FROZEN, ADMITTED và mọi contract OK.

## 6. Báo cáo F01 dưới ba bộ luật

| Luật | Kết quả F01 |
|---|---|
| Prereg phần 1 (3fb9865) | S1 FAILED; không có thay thế |
| F01-v2 (eabacab) | S1 FAILED; site thay thế EMPTY (sha 7eeeeda7…) |
| F01-v3 (addendum này) | theo kết quả site + stage 1 + A/B (nếu Duy duyệt) |
