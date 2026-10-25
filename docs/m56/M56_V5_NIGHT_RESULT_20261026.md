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

**Tình trạng:** vẫn chưa có cặp A/B hợp lệ nào. So với tối qua thì đã tiến xa: M03, M06, M07 và C02 có đủ cả 6 event ở cả A và B, còn
L01, L02, L04, L05, L06 có đủ 6 event ở A.

## 3. Chẩn đoán các rào còn lại (chỉ đọc)

1. **NPC cắt góc khi rẽ (CONTACT_PROOF, CONTINUOUS_FIT)** là rào lớn nhất.
   - NPC đi theo `LocalPlanner` gốc và ra ngoài hợp các làn Driving ở góc trong của khúc rẽ. Độ sâu đỉnh thân xe ra ngoài:
     C02 0,32 m, M07 0,56 m, L04 0,77 m, M03 0,99 m.
   - Đóng khe (r = 0,25 m hoặc 1,0 m) không đổi được gì, nên đây là hành vi thật, không phải artefact. Chỉ có thể sửa ở recipe
     (NPC chậm hơn ở khúc rẽ, hoặc plan dày hơn), mà đó là quyết định của Duy.
2. **Khe hở trong vùng drivable.**
   - Vùng drivable (hợp các ô lane) có 82–613 lỗ. Một số là khe hở giữa các ô, chu vi tới chỉ 0,04 m.
   - Đóng khe r = 0,25 m sửa được M05-NPC (−0,0 → 2,47 m) và L01-EGO (0,114 → 0,852 m), mà không làm đổi các cảnh khác.
   - Đây là đề xuất, chưa áp dụng.
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

## 4. Chờ Duy quyết (Claude không tự làm, vì đụng tới P5 hoặc phép đo)

| # | Đề xuất | Tác động dự kiến |
|---|---|---|
| a | Erratum 4a (NPC dừng hẳn sau CLEAR_N, trước khi hết plan), cộng một lần chạy lại thứ hai cho C01, C05 | C01 là ứng viên gần nhất cho cặp hợp lệ đầu tiên: B đã sạch, A chỉ thiếu DESTINATION |
| b | Đóng khe vùng drivable r = 0,25 m | sửa phần khe hở (M05, L01-A); không sửa phần NPC cắt góc |
| c | Đo mặt đất nhiều tia (ví dụ lấy hit `Roads` gần nhất trong vòng ±5 cm) | bỏ lỗi 1,98 m; cần chạy lại |
| d | Recipe NPC ở khúc rẽ (giảm tốc hoặc plan dày hơn) | rào chung của C02, M03/M06/M07, L04/L05 |
| e | Recipe PID/brake của EGO ở YIELD (L-B) | mọi L-B |
| f | Xác nhận hoặc bác erratum 6 (quyết theo ủy quyền đêm) | bỏ TARGET/PHASE mismatch ở 4 episode |

Kết quả cũ đều giữ nguyên làm hồ sơ. Chưa có gì được push hay merge.
