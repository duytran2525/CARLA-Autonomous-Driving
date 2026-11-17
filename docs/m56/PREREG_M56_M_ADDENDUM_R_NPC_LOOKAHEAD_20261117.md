# M56 addendum R: NPC của cảnh M cắt góc khi rẽ; lookahead cố định 3 m (product m56-v18), 17/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. **Luật sau số** (nguyên tắc 6): viết sau khi đọc các episode M đã
niêm, trước mọi số native dưới luật mới.

**Thẩm quyền:** người dùng phiên này [chat] 17/11/2026: "làm F05/F06, F03/F04 và nhóm M trong khi đợi quá trình khác chạy đi".
`M56_FIX_MATRIX_20261115.md` §C ghi mọi đường sửa M là quyết định của Duy; lời yêu cầu này được ghi là lời quyết đó. Claude chọn
đường sửa dưới ủy quyền của Duy.

## 1. Chẩn đoán (chỉ đọc episode đã niêm, episode A, `drivable-union.wkt` của chính cảnh)

Khoảng hở nhỏ nhất từ thân NPC tới mép vùng drivable dv1 (âm = ra ngoài):

| Cảnh | Route danh nghĩa | Quỹ đạo thật | Cắt góc | Khung < 0,15 m |
|---|---|---|---|---|
| M01-S1 | 0,480 | −1,148 | 1,63 | 132 |
| M06-S1 | 0,726 | −0,627 | 1,35 | 107 |
| M06-S2 | 0,605 | −0,685 | 1,29 | 140 |
| M07 (Town05) | 1,106 | −0,150 | 1,26 | 85 |
| M08-S2 | 0,424 | −0,701 | 1,13 | 154 |
| M02-S1 / M03-S1 / M05-S1 | 0,855 / 0,852 / 0,843 | 0,851 / 0,813 / 0,678 | ≤ 0,17 | 0 |

- Mọi cảnh có NPC rẽ đều cắt góc 1,1–1,6 m và ra khỏi vùng drivable → `CONTACT_PROOF_INVALID` / `CONTINUOUS_FIT_UNPROVEN`.
  Các cảnh không cắt góc hỏng vì lý do khác (không thuộc addendum này).
- Nguyên nhân: NPC là `LocalPlanner` stock đã ghim. Nó lái về waypoint đầu tiên cách xe hơn `base_min_distance +
  distance_ratio · v[km/h]` = 3 + 0,5·v (`local_planner.py` dòng 241). Ở 15–30 km/h, lookahead là 10–18 m. Trong nút giao hẹp,
  điều này cắt góc đúng cỡ 1–1,6 m.
- Cổng chọn site **không** sửa được: route danh nghĩa trong làn bình thường chỉ hở 0,4–1,1 m, không site nào chừa được 1,7 m.

## 2. Luật mới (product m56-v18)

- Binding stock đã review của **NPC** được phép mang khóa `npc_planner = {base_min_distance: 3, distance_ratio: 0}` (đúng hai
  khóa, cả hai là số; base > 0, ratio ≥ 0). Khóa này đi vào `opt_dict` của `LocalPlanner`; lookahead thành 3 m cố định (đúng giá
  trị base của stock). EGO không được mang khóa này (`STOCK_BINDING_INVALID`). Không có khóa = stock như cũ.
- Cùng kiểu với `npc_longitudinal` (v5 P-NPC, eda7680). PID ngang, giới hạn steer/throttle/brake, BasicAgent của EGO giữ nguyên.
- Giá trị chọn **trước** mọi số native: 3 m = base của stock, bỏ phần tăng theo tốc độ. Không dò giá trị.

## 3. Cổng trước A/B và luật dừng

- Chỉ cảnh loại M, tooling bật bằng `M56_NPC_PLANNER=1`.
- Cổng mới `NPC_EDGE` sau prepare: trên quỹ đạo probe của NPC, khoảng hở thân NPC tới mép dv1 phải ≥ 0,15 m ở mọi khung (0,15 =
  biên `minimum_road_edge_m` mà contact proof đã dùng). Trượt → BLOCKED_FIXTURE, không A/B.
- Cảnh chạy: M01-S1, M06-S2, M08-S2 (NPC rẽ, hỏng vì cắt góc), mỗi cảnh **một** A/B dưới version mới (giống I04/I02-S2: chạy lại
  chính cảnh dưới version mới, báo cạnh kết quả cũ). M06-S1 không chạy: nó còn hỏng mặt bên `n_exit` (hình học site, B5).
- Pair dưới m56-v18 và m56-v17 (luật cũ: v17 không chấp nhận khóa `npc_planner`, nên cặp dưới v17 được báo đúng như nó trả).
- Hỏng thì ghi FAILED/BLOCKED, không chỉnh lookahead.

## 4. Bổ sung 17/11 tối (trước mọi số native dưới v18): đính chính, mô phỏng hiệu chỉnh, kết luận

- **Đính chính §1:** bản CARLA này tính `get_speed()/3.6` (m/s), nên lookahead stock là 3 + 0,5·v[m/s] ≈ 4–7 m, không phải
  10–18 m. Nguyên nhân vẫn là lookahead, cộng thêm trượt ngang của tâm thân xe khi rẽ (đo được β ≈ 1,26 m × κ, tới 9°).
- **Cổng `NPC_EDGE` thay bằng mô phỏng hiệu chỉnh** (`m-npc-edge-sim.py`, chỉ đọc): luật lái ngang PID stock đúng từng hằng số
  (K_P 1,95, K_I 0,05, K_D 0,2, giới hạn đổi lái 0,1/bước, kẹp 0,8), mục tiêu là điểm plan đầu tiên xa hơn lookahead, xe động học
  với tốc độ đã ghi, độ cong = c·steer và trượt ngang β = atan(l_r·κ), c và l_r khớp bình phương nhỏ nhất trên chính episode.
  Điều kiện hiệu chỉnh (đặt trước khi chạy): với lookahead stock, mô phỏng phải tái tạo khoảng hở nhỏ nhất đã ghi trong TOL = 0,30 m.
  Kết quả: đạt cả 6 cảnh (sai 0,04–0,09 m).
- **Quét (chẩn đoán, luật sau số):** khoảng hở dự báo nhỏ nhất (m)

| Lookahead, K_P | M06-S1 | M06-S2 | M08-S2 | M01-S1 | M07 |
|---|---|---|---|---|---|
| stock 3 + 0,5·v, 1,95 | −0,66 | −0,76 | −0,75 | −1,24 | −0,19 |
| 3 m, 1,95 | −0,21 | −0,30 | −0,37 | −0,56 | +0,12 |
| 2 m, 1,95 | +0,11 | +0,05 | +0,01 | −0,16 | +0,52 |
| 1,5 m, 1,95 | +0,26 | +0,20 | +0,17 | +0,04 | +0,66 |
| 2 m, 3,0 / 4,0 | +0,02 / −0,02 | −0,04 / −0,09 | −0,10 / −0,15 | −0,27 / −0,33 | +0,40 / +0,36 |

- Cổng: dự báo − TOL ≥ 0,15 m, tức dự báo ≥ 0,45 m. **M01-S1, M06-S2, M08-S2 trượt ở mọi lookahead** (1,5 m đã ngắn hơn khoảng cách
  điểm plan 2 m). Tăng K_P làm xấu hơn. Không A/B nào chạy, không tiêu P5.
- **Kết luận:** với controller stock đã ghim, NPC rẽ chỉ giữ được trong vùng drivable ở site có route danh nghĩa hở rộng (M07
  Town05: 1,106 m). Luật v18 giữ nguyên (khóa `npc_planner` chấp nhận mọi base > 0). Giá trị dùng nếu chạy: base 2 m, ratio 0 (ngắn
  nhất còn ≥ khoảng cách điểm plan).
- **Bước tiếp (chưa làm):** cổng chọn site M mới = mô phỏng này trên route danh nghĩa với hằng số xe điển hình (c 0,42, l_r 1,27) và
  tốc độ danh nghĩa, dự báo ≥ 0,45 m; rồi successor B3 cho các slot M. Cần addendum riêng và tiêu ngân sách B3.
