# M56: báo cáo cuối (partial native, 24/10/2026)

**Kết luận:** M56 kết thúc ở mức **partial native trung thực**. Catalog không đạt điều kiện release theo spec §11:

- C0 partial có 31/46 cảnh và 17/23 junction;
- chưa có review độc lập;
- chưa có 155 phép so;
- không export.

Pipeline G4/G5 đã chạy được trên CARLA thật từ đầu đến cuối: chuẩn bị, C0, compile, freeze, admit, A/B, đánh giá offline,
W05. Lần đầu M56 có số đo native (`d_yield_m`, `t_entry_s`). Mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, không độc
lập. Mọi kết quả là A/B local.

**Quyết định cuối** (Claude, dưới ủy quyền của Duy ngày 24/10, "tự lựa chọn quyết định phù hợp nhất"): **giữ nguyên
consumer đã đóng băng**. Lý do: bên tạo ra kết quả, không độc lập, sửa các bộ kiểm sau khi đã thấy kết quả chính là điều
nguyên tắc 6 cấm. Các đề xuất sửa consumer ở §5 dành cho một version sau, có review độc lập.

## 1. Chuỗi thẩm quyền

Mỗi tài liệu dưới đây đều được commit **trước** mọi lần chạy dùng nó.

| Tài liệu | Commit |
|---|---|
| addendum A-C0P, A-G45 | — |
| prereg v2 | d1c91ac |
| erratum E1–E6 | 737acbc, 94c56b3 |
| signal-phase v1 cùng erratum 1–4 | b4b6a22, 59744b3, 425e8b1, 00221e5, 7374ed7 |
| prereg v3 | ab1fb09 |
| prereg v4 (P1, P2, P3, P5) | ccea1cc |

Các thay đổi quy tắc **đặt sau khi thấy số** đều được ghi công khai và báo theo cả hai quy tắc:
- E3/E5: pose và tốc độ ban đầu;
- E6: mốc readiness bằng mức ổn định đo được;
- erratum 4: điểm neo duy nhất gần nhất;
- P1: cửa sổ đo mức ổn định của NPC;
- P2: thời gian chờ pha đèn.

Không có ngưỡng metric nào bị đổi.

## 2. Kết quả theo cảnh (31 cảnh của C0 partial)

| Nhóm | Cảnh | Trạng thái | Nguyên nhân (đo native) |
|---|---|---|---|
| C/L đã chạy A/B | C01, C02 | xem §3 | — |
| C/L đã chạy A/B | L01 | đã chạy một lần, không có episode hợp lệ | A: `OUTER_TIMEOUT` (harness, đã sửa); B: `CONTINUOUS_YIELD_SPEED_FLOOR`; cả hai `INITIALIZATION_INVALID` vì phép kiểm run-in đo theo mặt phẳng, mà EGO rẽ vào qua mặt bên (0,24 m so với 32,8 m theo route) |
| PID gốc dao động | C04, C05, C06, L04, L05, L06, L07, L08 | BLOCKED `READINESS_NOT_STEADY` | NPC nhanh (vN ≥ 5,9 m/s): PID dọc đổi liên tục giữa ga 0,75 và phanh 0,3 (C04: 4,4–6,5 m/s); spec §6.1 cấm sửa PID |
| Vùng xung đột rời | C03, L02, L03 | BLOCKED | quy tắc compiler đóng băng (P4) |
| Route builder | C07, C08 | BLOCKED | bắt nhầm làn ở Town06; NPC 11,4 và 14,3 m/s nên nhiều khả năng cũng dính chặn PID |
| M | M01 | BLOCKED `READINESS_NOT_STEADY` | EGO đi 117 m qua cụm junction; cửa sổ E6 nằm ngoài probe 16 s; biên độ tốc độ 0,24 m/s |
| I/O | I01–I05, I07, O01–O05, O07 | BLOCKED | normative đòi target readiness của EGO đúng bằng 6 / 7,5 / 9,375 m/s, mâu thuẫn với E6; lateral contract chỉ hỗ trợ route thẳng 2 điểm theo trục +x |
| F | F01 | BLOCKED | chưa dựng recipe trong tuần; phụ thuộc các chương trình NPC PROVISIONAL |
| F | F04 | BLOCKED_CAPABILITY | chưa có proof bao cửa xe (spec §5.4) |

## 3. A/B native của C01 và C02

### v2.1 (23/10): hỏng do harness

Fixture sai mục tiêu readiness, nên `READINESS_NOT_REACHED`.

### v3 (24/10, một lần)

| Cảnh, action | Event | `d_yield_m` | `t_entry_s` | Chặn |
|---|---|---|---|---|
| C01 A | TRIGGER, NPC_ENTRY, CLEAR_N_CONFIRMED | 2,046 | — | `COMMAND_ORDER` (harness, đã sửa 962febb) |
| C01 B | đủ tới DESTINATION_CONFIRMED | 10,557 | 9,60 | `DELIVERY_PROOF_INVALID` (harness, đã sửa 153678a) |
| C02 A | như C01 A | 2,048 | — | `COMMAND_ORDER`; contact/fit |
| C02 B | đủ tới DESTINATION | 9,421 | 8,35 | delivery; contact/fit |

**Lưu ý về độ lệch spec:** các episode v3 chạy 453–584 s thời gian thực, trong khi spec §7.1 chỉ cho 300 s. Giới hạn
900 s là lỗi tooling của Claude. Theo đúng spec, các episode này đã phải dừng `OUTER_TIMEOUT`. Kết quả được báo theo cả
hai cách đọc.

### v3.1 (sau suite 9, một lần, với đủ các bản sửa harness)

*(điền sau khi chạy)*

## 4. Thay đổi sản phẩm và kiểm chứng

| Commit | Nội dung |
|---|---|
| 4a82570 | hook đo native tùy chọn; điểm plan có thể gọi đích danh làn; quy tắc trạng thái ban đầu E3/E5 (kèm báo cáo theo quy tắc cũ) |
| 962febb | lệnh tường minh ghi nhận frame vào phiên stock |
| 153678a | bản ghi thiết bị đo theo từng episode |
| 5188358 | dò event C/L tiếp tục từ trạng thái đã lưu: kết quả y hệt, nhanh ~50 lần (đối chiếu trên quỹ đạo native 521 frame) |

**Full suite:**
- suite 7: 1174/1174 qua, trên e9d48a1;
- suite 8: 1177/1177 qua, trên 4a82570;
- suite 9: chạy trên 962febb + 153678a;
- suite cuối: chạy trên các byte cuối cùng.

## 5. Đề xuất cho version sau (cần review độc lập)

1. **Run-in:** đo khoảng cách theo route, không theo mặt phẳng, khi EGO đi vào vùng qua mặt bên (L).
2. **Normative I/O:** kiểm `response.targets['NOMINAL']` thay vì target readiness (target này đã bằng mức ổn định theo
   E6).
3. **Lateral contract:** hỗ trợ route thật, không chỉ route 2 điểm trục +x.
4. **PID:** quyết định rõ về PID dọc gốc ở tốc độ cao (dao động giới hạn), hoặc chọn vN thấp hơn.
5. **Vùng xung đột rời:** thêm đường review cho trường hợp này trong compiler.
6. **Catalog:** sửa đơn vị `k` của I/O; bổ sung cảnh lên 46 và junction lên 23 bằng quy tắc mới, đặt trước khi thấy số.
