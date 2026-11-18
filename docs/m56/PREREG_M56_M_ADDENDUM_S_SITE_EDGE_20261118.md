# M56 addendum S: cổng chọn site M theo mô phỏng NPC stock (NPC_EDGE_SITE) và successor B3 cho M01–M08, 18/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. **Luật sau số** (nguyên tắc 6): viết sau khi đọc các episode M
đã niêm (addendum R §1, §4), trước mọi số native của các successor.

**Thẩm quyền:** người dùng phiên này [chat] 17/11: "làm F05/F06, F03/F04 và nhóm M"; [chat] 18/11: "làm hết cho tôi".
`M56_FIX_MATRIX_20261115.md` §C: đường sửa M (cách chọn site) là quyết định của Duy; Claude quyết dưới ủy quyền của Duy.

## 1. Cổng

`m-site-edge-gate.py` (chỉ đọc OpenDRIVE). Mô phỏng NPC đi qua làn connector của nút giao bằng đúng luật lái ngang PID stock
(addendum R §4), lookahead 2 m (giá trị đã chọn ở addendum R), tốc độ vN danh nghĩa của slot, hằng số xe c = 0,414,
l_r = 1,27 (trung bình 5 episode M rẽ đã niêm), thân 4,90 × 2,12 m. Biên = min (nửa bề rộng làn − |khoảng cách góc thân
tới tâm làn|). **Đạt khi biên ≥ 0,45 m** (0,15 của contact proof + TOL 0,30 của mô phỏng).

Kiểm trên 6 episode đã niêm (vN 3, trước mọi số mới): M06-S2 −0,088, M01-S1 −0,245, M08-S2 −0,057 → trượt (đúng: cả ba ra
khỏi drivable). M02-S1 0,712, M03-S1 0,681, M05-S1 0,653 → đạt (đúng: cả ba không cắt góc). Khớp 6/6.

## 2. Thay cảnh

- `fill-v4-generate.py` thêm luật `S_NPC_EDGE` (chỉ cho M, chỉ khi state có `npc_edge: true`; không có cờ thì giữ nguyên mọi
  byte cũ), đặt sau `B3_TRIED`.
- State 10 (`asel2-replace-state10.py`) = state 9 lap 5 + kết quả replacement 9 đã nhận (c4) vào `assigned`/`tried`; slot mở:
  M01…M08 (mọi slot M, chưa slot nào PASS); giữ `chain`, `axis` (B5). Mỗi slot một successor (S<n+1>), tính vào ngân sách 150.
- Native: prepare như M cũ (`run-asel2-cl2.sh`), product **m56-v18**, NPC mang `npc_planner = {2, 0}` (addendum R),
  rồi **một** A/B mỗi cảnh PREPARED (P5); pair dưới v18 và v12 (luật cũ).
- Hỏng thì ghi đúng như đo, không chỉnh cổng.

## 3. Kết quả lap 1 (18/11, offline, trước mọi số native)

- `m56_fill_v4_replace10_1_20261118.json` (sha 9f6456ed…): **cả 8 slot M `EMPTY_NO_ELIGIBLE_CANDIDATE`**. Mỗi slot có 383–393
  ứng viên qua mọi luật cũ nhưng trượt `S_NPC_EDGE`; ứng viên còn lại trượt B1/B5/run-in như trước.
- Kiểm không phải lỗi đo (`edgedist`, cùng code path): 277 site M qua B5; biên lớn nhất 0,363 m (Town13 759/-1→18948/-1→1057/-3,
  rẽ phải 90°, làn 3,5 m), không site nào ≥ 0,45. Bề rộng làn connector: 2,75 m (116), 3,0 (108), 3,25 (31), 3,5 (12), 2,5 (10),
  đúng giá trị OpenDRIVE (một laneSection). Ba site M từng không cắt góc (M02-S1, M03-S1, M05-S1, biên 0,65–0,71) đã ở `tried`.
- **Kết luận:** dưới controller NPC stock đã ghim (kể cả lookahead 2 m), không còn site M nào trong 11 town đạt cổng đã đăng ký.
  Các slot M ghi `EMPTY` dưới addendum S; không nới ngưỡng 0,45 (nguyên tắc 6), không tiêu ngân sách B3 (0 entry PROPOSED).
  Đường còn lại thuộc quyền Duy: đổi controller NPC (không còn là stock) hoặc đổi spec §5.2 / vùng drivable.
