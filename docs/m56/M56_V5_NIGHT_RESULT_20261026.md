# M56 v5: kết quả đêm 25–26/10/2026 (erratum 4, 5, 6)

**Ủy quyền:**
- [chat] 25/10/2026, Duy duyệt erratum 5, phương án 1 (`b52a166`).
- [chat] 26/10/2026, Duy: "bây giờ tôi đi ngủ từ đây đến 7h bạn tự quyết định làm theo lựa chọn bạn recommend cho tôi là được".
- Claude không dùng ủy quyền này để đổi ngưỡng hay P5. Mọi việc thuộc loại đó được để lại thành đề xuất ở mục 4.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Môi trường chạy:**
- CARLA `no_rendering_mode` bật (ghi trong mọi receipt); W05 chạy hoãn.
- Mỗi lần chỉ một server riêng trên cổng 2610.
- Không có crash CARLA nào sau 22:36 ngày 25/10.

## 1. Đã làm

| Việc | Commit / output | Ghi chú |
|---|---|---|
| Erratum 5 (consumer: bỏ conjunct mặt cắt ở entry và STOP) | `4936593` trên `feat/m56-e5`; tài liệu `9c80d8e`, `453b048` | 2 test mới (hỏng với code cũ); 442 test qua; C01 đánh giá lại byte-identical với v5f ở cả A và B |
| Danh sách chạy lại erratum 5 (chứng minh bằng so event cũ/mới trên episode đã seal) | `outputs/m56_e5_rerun_list.json` (sha256 `d73e6def…`) | 11 cảnh: C02, C03, L01, L02, L04–L07, M03, M06, M07. Không chạy lại M05, C01, C05 (event không đổi) |
| A/B chạy lại, mỗi cảnh một lần | chuỗi `run-v5-e5.sh` (`c8ac440`); A/B ở `m56_v2_ab_Town04_20261025T170853Z`, `…Town05_20261025T173506Z`, `…Town07_20261025T180142Z` | — |
| Chạy lại theo erratum 4 (C01, C05) | `m56_v2_ab_Town04_20261025T164906Z`, `m56_v2_ab_Town05_20261025T165244Z` | Lần chạy lại duy nhất P5 cho phép |
| Erratum 6 (auditor chấp nhận lệnh giữ NPC do đèn) | `8cbfc4d` trên `feat/m56-e6`; tài liệu `62b28b9` | Quyết theo ủy quyền đêm. Chỉ đánh giá lại offline: `m56_v2_ab_Town0{4,5,7}_20261025T182405Z` |

## 2. Kết quả A/B (thô; báo theo quy tắc e5 và e6)

Lý do W05_REVIEW_MISSING và W01_W05_VALIDATION_PENDING có ở mọi episode nên không ghi lại trong bảng.

| Cảnh | Ep | Event | d_yield (m) | t_entry (s) | Lý do còn lại (e6) | e6 bỏ được so với e5 |
|---|---|---|---|---|---|---|
| C01 (e4) | A | 5/6 | 2,046 | 12,6 | DESTINATION_MISSING, TICK_ERROR (NPC hết plan) | — |
| C01 (e4) | B | 6/6 | 10,557 | 9,6 | (chỉ W05) | — |
| C05 (e4) | A | 5/6 | 2,046 | 8,6 | CONTINUOUS_FIT, DESTINATION_MISSING, TICK_ERROR | — |
| C05 (e4) | B | 5/6 | 7,626 | 6,35 | như A | — |
| C02 | A | 6/6 | 2,048 | 11,1 | CONTACT, FIT, LATERAL_BUDGET | TARGET/PHASE mismatch |
| C02 | B | 6/6 | 9,421 | 8,35 | CONTACT, FIT | — |
| C03 | A | 2/6 | — | — | GROUND, CONTACT, FIT, LATERAL; NPC tới không kịp | TARGET/PHASE mismatch |
| C03 | B | 4/6 | — | 9,3 | như A, cộng EARLY_ENTRY | TARGET/PHASE mismatch |
| L01 | A | 6/6 | 0,518 | 12,6 | CONTACT, FIT | — |
| L01 | B | 2/6 | — | — | YIELD_SPEED_FLOOR → RESPONSE_BLOCKED | — |
| L02 | A | 6/6 | 0,521 | 10,7 | GROUND, CONTACT, FIT | — |
| L02 | B | 2/6 | — | — | YIELD_SPEED_FLOOR | — |
| L04 | A | 6/6 | 0,503 | 8,7 | CONTACT, FIT, LATERAL, NPC_UNPLANNED_REVERSE | — |
| L04 | B | 2/6 | — | — | YIELD_SPEED_FLOOR | — |
| L05 | A | 6/6 | 0,533 | 7,55 | CONTACT, LATERAL, FIT | — |
| L05 | B | 2/6 | — | — | YIELD_SPEED_FLOOR | — |
| L06 | A | 6/6 | 0,514 | 6,7 | INITIALIZATION, GROUND, CONTACT, FIT, LATERAL | — |
| L06 | B | 2/6 | — | — | YIELD_SPEED_FLOOR | — |
| L07 | A | 3/6 | — | — | GROUND, CONTACT, FIT, LATERAL; thiếu CLEAR_N | TARGET/PHASE mismatch |
| L07 | B | 2/6 | — | — | YIELD_SPEED_FLOOR | — |
| M03 | A | 6/6 | 2,061 | 9,0 | CONTACT, LATERAL, FIT | — |
| M03 | B | 6/6 | 7,725 | 6,75 | CONTACT, LATERAL, FIT | — |
| M06 | A | 6/6 | 2,048 | 13,7 | CONTACT, FIT, NPC_UNPLANNED_REVERSE | — |
| M06 | B | 6/6 | 11,972 | 10,35 | như A | — |
| M07 | A | 6/6 | 2,056 | 16,95 | CONTACT, FIT | — |
| M07 | B | 6/6 | 14,146 | 13,05 | CONTACT, FIT | — |

**Tình trạng:** vẫn chưa có cặp A/B hợp lệ nào. Ở cấp episode, C01-B sau W05 là COMPLETE / VALID, không còn lý do nào (cả lần v5f lẫn lần chạy lại theo erratum 4). So với tối qua thì đã tiến xa: M03, M06, M07 và C02 có đủ cả 6 event ở cả A và B, còn
L01, L02, L04, L05, L06 có đủ 6 event ở A.

## 3. Chẩn đoán các rào còn lại (chỉ đọc)

1. **Vùng drivable quá hẹp (CONTACT_PROOF, phần lớn CONTINUOUS_FIT).** Đây là rào lớn nhất, và là lỗi đo.
   - Vùng drivable của tooling chỉ là hợp các ô của làn `Driving`. Mọi đỉnh thân xe nằm ngoài vùng này đều nằm trên mặt đường
     thật.
   - Bằng chứng: probe trên world trống (`native-surface-probe.py`, `outputs/m56_surface_probe_Town0{4,5}_*.json`) bắn tia tại
     các đỉnh ra ngoài sâu nhất. Mọi tia đều trúng `Roads` hoặc `RoadLines`. Theo map, các điểm đó thuộc làn `Shoulder` (C02,
     M03, M07), làn `Parking` (L04), hoặc mặt giao lộ không thuộc làn nào (M03, M07).
   - Độ sâu thân NPC ra ngoài vùng: C02 0,32 m, M07 0,56 m, L04 0,77 m, M03 0,99 m.
   - Đóng khe (r = 0,25 m hoặc 1,0 m) không giúp, vì đây là cả một dải mặt đường bị loại ra chứ không phải khe hở.
   - Cũng vì vùng hẹp này mà FIT của EGO hỏng, kể cả khi EGO ở xa mép:
     - C05-A: mép ≥ 0,35 m nhưng 25 khoảng hỏng FIT;
     - C02-A: hỏng ngay từ vị trí xuất phát;
     - L01-A, L04-A cũng hỏng.
   - Ngoài ra, các ô 0,5 m chạm biên bị bỏ đi trước khi trừ thêm 0,15 m.
   - *(Bản trước của mục này, viết lúc 02:00, gọi đây là "NPC cắt góc thật". Nhận định đó sai: probe cho thấy các điểm đó đều là
     mặt đường.)*
2. **LATERAL_BUDGET là thật và luôn do NPC ở khúc rẽ.**
   - Đỉnh v²κ: M03 3,54; C02 3,2; L04 5,82 m/s². EGO luôn dưới 1 m/s².
   - Với vN 3–4 m/s ở khúc rẽ gắt của giao lộ, mức này vượt 2,5. Chỉ có thể sửa ở recipe (tốc độ NPC khi rẽ).
   - Khe hở thật trong vùng drivable (82–613 lỗ, chu vi tới chỉ 0,04 m) là chuyện nhỏ hơn. Đóng khe r = 0,25 m sửa được
     M05-NPC (−0,0 → 2,47 m) và L01-EGO (0,114 → 0,852 m).
3. **GROUND_PROOF:** probe trên world trống (`native-ground-probe.py`, `outputs/m56_ground_probe_*.json`) tái hiện đúng lỗi 1,98 m:
   - ở một số góc xe, tia bắn từ 2 m phía trên lọt qua khe trên mesh va chạm của mặt đường Town06 và trúng `NONE` ở −1,98 m;
   - các góc ngay bên cạnh trúng `Roads` ở 0 m.
   - Đây là lỗi của phép đo một tia trong kit, không phải xe rời mặt đất. Muốn sửa phải đo lại online.
4. **YIELD_SPEED_FLOOR ở mọi L-B.** Lấy L01-B làm ví dụ:
   - EGO giảm từ 2 về 1 m/s với brake bão hòa ở 0,3;
   - sau năm tick giảm đều khoảng 2,6 m/s², tới 1,23 m/s thì vận tốc rơi xuống 0,30 m/s trong một tick;
   - không có va chạm (collision rỗng), và quãng dịch chuyển (0,04 m trong 0,05 s) khớp với một cú khựng thật;
   - driver vì vậy dừng episode khi v < 0,5 m/s.
   - Muốn sửa phải đổi recipe PID/brake của EGO cho phase YIELD.
5. **C03:** route NPC đi qua hai giao lộ có đèn trước giao lộ xung đột. NPC bị giữ khoảng 24 s ở mét 78,8, rồi lại bị giữ ở mét
   129,3, trong khi giao lộ xung đột ở mét 141,8. NPC xuất phát quá xa phía trước; đây là lỗi thiết kế fixture.
6. **C01-A, C05:** NPC hết plan đã cắt theo erratum 4, rồi `TICK_ERROR STOCK_CONTROL_INVALID`. Erratum 4a đã được đề xuất
   (`8a9ddb2`).
7. **Không chuẩn bị được:**
   - C07, C08: `NO_OUTGOING`, ký hiệu làn trong catalog (−2) không khớp map (−3);
   - L03: C4 `CONFLICT_COMPONENTS_TOO_CLOSE`;
   - C04, M04: `READINESS_NOT_STEADY`;
   - C06: `NPC_SIGNAL_HOLD_IN_PROBE2`;
   - L08: `PHASING_ROOM`;
   - M02, M08: EGO xuất phát ở chỗ va chạm;
   - M01: chưa chuẩn bị.

## 4. Chờ Duy quyết

**Điểm chính: P5 đã dùng hết.** Mọi cảnh đã chạy đêm nay đều đã dùng lần chạy lại P5. Vì vậy mọi sửa đổi dưới đây đều cần thêm
một lần chạy cho các cảnh không còn lượt chạy lại.

**Claude khuyến nghị:** như đã làm với v5, Duy duyệt **một bản v6 gộp** (recipe + consumer). Bản này chỉ chứa những sửa đã được
kiểm offline đêm nay. Mỗi cảnh được **một A/B mới** dưới v6, kèm W05 và D09. Cách còn lại là mỗi rào một erratum, và lần nào cũng
cần một ngoại lệ P5.

| # | Thành phần v6 đề xuất | Bằng chứng | Tác động dự kiến |
|---|---|---|---|
| a | Erratum 4a: NPC dừng hẳn sau CLEAR_N, trước khi hết plan | TICK_ERROR ở C01-A, C05-A, C05-B | C01: B đã COMPLETE/VALID sau W05, còn A chỉ thiếu DESTINATION |
| b | Vùng drivable gồm cả `Shoulder`, `Parking` và mặt giao lộ (hoặc lấy từ nhãn `Roads`), kèm đóng khe | probe nhãn bề mặt; phân tích mép | CONTACT và phần lớn FIT ở C02, M03/M06/M07, L01–L05, C05 |
| c | Đo mặt đất nhiều tia (bỏ hit `NONE` khi có `Roads` trong vòng ±5 cm) | probe mặt đất: tia lọt khe mesh (mới kiểm ở M05) | GROUND_PROOF ở M05; L02, L06, L07, C03 có cùng lý do nhưng chưa probe |
| d | Tốc độ NPC khi rẽ (để v²κ ≤ 2,5) | phân rã LATERAL | LATERAL ở M03, C02-A, L04–L07 |
| e | PID/brake của EGO ở YIELD | L01-B (v rơi 1,23 → 0,30 m/s) | mọi L-B |
| f | Erratum 6 (xác nhận hoặc bác) | đã kiểm | bỏ TARGET/PHASE mismatch ở 4 episode |
| g | Tooling eligibility: đưa bundle W05 vào `compare_ab` và tạo review D09 | `compare_ab` hiện đánh giá lại từ `load_episode`, không thấy W05 | điều kiện để ra cặp PASS đầu tiên |

Ngoài v6: C03 (NPC đi qua hai giao lộ có đèn) cần đặt lại điểm xuất phát của NPC, còn C07/C08 cần sửa ký hiệu làn trong catalog.

Kết quả cũ đều giữ nguyên làm hồ sơ. Chưa có gì được push hay merge.
