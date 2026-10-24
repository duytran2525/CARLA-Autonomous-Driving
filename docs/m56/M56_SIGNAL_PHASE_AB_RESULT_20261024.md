# M56: canh pha đèn và A/B native lần đầu (23–24/10/2026)

**Kết luận:**
- Bước canh pha đèn **hoạt động**: NPC không còn bị đèn đỏ làm lệch pha.
- Hai cảnh C01 và C02 đã đi hết chuỗi: chuẩn bị → C0 v2.1 → `compile_fixture` → freeze → `admit` → A/B trên CARLA thật,
  mỗi action chạy đúng một lần.
- **Chưa có số A/B hợp lệ nào.** Cả 4 episode (C01 A/B, C02 A/B) dừng với `TICK_ERROR`. Verdict của consumer: spawn
  CONFIRMED, physical UNKNOWN, witness INVALID.
- Nguyên nhân là hai giới hạn có tính cấu trúc (§3), cộng một lỗi trong kit của Claude.

**Thẩm quyền:**
- **Duy (tự xác nhận trong chat) đã yêu cầu:**
  - viết đăng ký trước cho bước canh pha đèn (`phase_predicate`) và chạy lại chuẩn bị C/L;
  - "Cho chạy v2.1": chạy fixture đúng prereg đúng một lần;
  - "tự quyết định để sáng mai có kết quả hoàn chỉnh".
- **Reviewer:** mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, không độc lập.

## 1. Đăng ký trước canh pha đèn

| Tài liệu | Commit | Nội dung |
|---|---|---|
| `PREREG_M56_SIGNAL_PHASE_V1_20261023.md` | b4b6a22 | vị từ pha chỉ quan sát, chờ ≤ 60 s, không đổi đèn (spec §484); neo sao cho đèn NPC xanh từ 2 s trước khi NPC tới vùng dừng |
| Erratum 1 | 59744b3 | chọn đúng đèn của làn NPC: "đèn đầu tiên do API trả về" có stop waypoint lệch route NPC 107,7 m |
| Erratum 2 | 425e8b1 | đồng hồ đèn đỏ (`get_elapsed_time`) đứng ở 0 sau khoảng 2 s nên không dùng làm đồng hồ pha được |
| Erratum 3 | 00221e5 | gói pha = trạng thái và đồng hồ của cả nhóm đèn, vì khoảng đỏ toàn bộ ~2 s không có đèn nào đang hoạt động |

Chu kỳ đèn đo được (Town04): xanh 200 tick, vàng 61 tick, đỏ 947 tick, tổng 60,4 s.

## 2. Chuẩn bị (16 C/L, 4 town)

Nguồn: `outputs/m56_v2_prepare_Town0{4,5,6,7}_20261023T16*`.

| Kết quả | Cảnh |
|---|---|
| PREPARED: neo pha, NPC không bị giữ frame nào ở probe 2 | **C01** (T_r 3,40 s, khoảng trống 48,0 m), **C02** (T_r 5,65 s, khoảng trống 35,9 m) |
| `READINESS_NOT_STEADY`: NPC nhanh chưa ổn định trước TRIGGER | C04, C05, L01, L03, L04, L06, L07, L08 |
| `DISCONNECTED_CONFLICT_REVIEW_REQUIRED`: quy tắc compiler đóng băng | C03, L02 |
| Công cụ dựng route chưa dựng được (giới hạn công cụ) | C06, L05, C07, C08 |

**C0 partial v2.1:** `outputs/m56_c0_partial_v2.1_20261023T171407Z` (sha `81045497…`). Các file v1 không đổi byte nào.

## 3. A/B native, mỗi cảnh chạy một lần

### Lần chạy v2.0: hỏng do harness, giữ lại

- **Nguồn:** `outputs/m56_v2_ab_Town04_20261023T165444Z`.
- **Diễn biến:** fixture C01/C02 được compile, freeze và ADMITTED, nhưng mọi episode đều `READINESS_NOT_REACHED`.
- **Nguyên nhân:** trình dựng revision của Claude ghi readiness bằng tốc độ danh nghĩa (4/3), không phải mức ổn định E6
  (3,863/2,87).
- **Kiểm chứng:** quỹ đạo trùng probe 2 từng frame (tất định). Chạy `runtime._ready` với mục tiêu E6 trên chính quỹ đạo
  đó thì đạt ở 4,45 s.
- **Nhãn:** `HARNESS_DEFECT_RUN`. Duy cho chạy v2.1 đúng một lần.

### Lần chạy v2.1 (lần chạy duy nhất được phép)

Nguồn: `outputs/m56_v2_ab_Town04_20261023T171457Z`.

| Cảnh, action | Fixture | spawn | physical | witness | Dừng |
|---|---|---|---|---|---|
| C01 A | `0fe820de…` | CONFIRMED | UNKNOWN | INVALID | `TICK_ERROR` `STOCK_CONTROL_INVALID`, frame 423 |
| C01 B | như trên | CONFIRMED | UNKNOWN | INVALID | như trên |
| C02 A | `45de161a…` | CONFIRMED | UNKNOWN | INVALID | `TICK_ERROR` `STOCK_CONTROL_INVALID`, frame 396 |
| C02 B | như trên | CONFIRMED | UNKNOWN | INVALID | như trên |

**Đã đạt:**
- Readiness đạt theo E6.
- EGO nhận TRIGGER và dừng trước vùng xung đột (C01: 23,8 m).
- NPC đi qua junction, không bị đèn giữ.
- Các phép kiểm đã qua: initialization theo E3/E5 (theo quy tắc cũ thì cả hai xe đều trượt), W01, mặt đất từng frame,
  metric context, delivery (A).

### Nguyên nhân dừng và các phép kiểm còn trượt

1. **CLEAR_N không bao giờ được xác nhận** (cấu trúc, thuộc thiết kế §5 của prereg v2):
   - Vùng xung đột là hộp ôm sát phần giao của hai swept volume, nên mặt cắt `n_exit` chỉ rộng 2,0 m (C01) hoặc 1,94 m
     (C02).
   - Thân NPC rộng 1,79 m. Phép kiểm "đúng hành lang" của consumer đòi cả thân nằm trong mặt cắt, nên NPC đã vượt
     `n_exit + 0,5 m` mà vẫn không được tính là clear (0 frame đạt).
   - EGO chờ mãi; NPC chạy hết plan; LocalPlanner gốc trả về phanh khẩn (brake 1,0 > 0,3); validator dừng episode.
2. **`OFFSET_ROUTE_MISMATCH` và `PLAN_SOURCE_WITNESS_INVALID`** (cấu trúc):
   - Consumer đòi `response.route == fixture.routes[role]`.
   - Response EGO đóng băng ở C0 mang route XODR lấy mẫu 1 m. Compiler lại đòi bước ≤ 0,25 m và route theo waypoint CARLA
     (E2).
   - Vì vậy response EGO của C/L đã đóng băng **không thể** khớp với một fixture compile được, nếu không tạo phiên bản
     response mới.
3. **`MOTION_PROOF_INVALID` và `CONTACT_PROOF_INVALID`** (lỗi kit của Claude):
   - Recipe trỏ tới file `.wkt`, mà consumer chỉ đọc nguồn JSON.
   - Số đo tự thân thì qua: mép đường nhỏ nhất 0,75 m (≥ 0,15), sai số mặt đất lớn nhất 0,027 m (≤ 0,05).
   - Kit đã được sửa sau lần chạy và **chưa** chạy lại.
4. **`PHASE_EVENT_WITNESS_UNKNOWN`:** hệ quả của (1) và (2).

**Phát hiện thêm về sản phẩm:** `runtime.load_episode` (resume/export offline) chỉ nạp lại 5 luồng gốc, không nạp các
luồng review/proof mới. Muốn đánh giá lại offline thì phải tự thêm các luồng đó.

## 4. Trạng thái M56 và các quyết định cần Duy

- **Catalog:** C0 partial 31/46, 17 junction, không export.
- **G4/G5:** 2/16 C/L đã đi hết chuỗi native một lần, có **0 số A/B hợp lệ**. Theo quyết định "đúng một lần", C01 và C02
  không được chạy lại.
- **Muốn có số A/B thì cần quyết định mới:**
  - phiên bản response EGO mới, có route theo waypoint ≤ 0,25 m (đổi ứng viên sau C0);
  - quy tắc vùng xung đột cho mặt cắt clear đủ rộng, ví dụ theo bề rộng làn thay vì hộp ôm sát;
  - một lần chạy mới, sau khi đã sửa kit.
- **Full suite 8:** đang chạy trên `4a82570`, 338/1177 test qua, 0 lỗi lúc viết báo cáo. Các thay đổi sau đó
  chỉ nằm ở tooling của WS, không đụng tới các byte mà suite đang kiểm. Chưa push gì.

## 5. Runtime-recipe v3 (24/10/2026)

**Đăng ký trước:** `PREREG_M56_RUNTIME_RECIPE_V3_20261024.md`, commit ab1fb09, trước mọi lần chạy. Gồm ba điểm:
- V3.1: response EGO dùng route waypoint của fixture;
- V3.2: vùng xung đột rộng ≥ W + 1 m, với W = 3,5 m;
- V3.3: route NPC kéo dài phía hạ nguồn thêm 15 + 60·vN m.

**Chuẩn bị v3:** `outputs/m56_v2_prepare_Town04_20261024T024739Z`, chỉ C01 và C02. Cả hai bị chặn **trước A/B**:

| Cảnh | Kết quả | Chi tiết |
|---|---|---|
| C01 | `SIGNAL_ANCHOR_AMBIGUOUS` | Vùng rộng hơn đẩy `n_entry` lùi 1,3 m, nên t_in = 4,03 s và k = 41 tick trước lúc xanh. Tick đó là tick **đầu tiên** của khoảng đỏ toàn bộ: cả 4 đèn Đỏ, mọi đồng hồ = 0, và trạng thái này lặp lại ở mỗi lần chuyển trong chu kỳ. Với k = 40, gói pha đã là duy nhất. |
| C02 | `BLOCKED_SIGNAL_ADMISSION` ở probe 1 | Vị từ "đèn 1622 vừa xanh" không xuất hiện trong 60 s, vì chu kỳ 60,4 s dài hơn giới hạn chờ 60 s của spec §484. Lúc bắt đầu chờ, chu kỳ đang ở vị trí bất lợi. |

**Quyết định:**
- Không chạy lại, không dịch điểm neo, không nới thời gian chờ (spec §484, prereg v3).
- Không đóng băng C0 partial v3, vì không còn cảnh v3 nào chạy được.
- Không có A/B v3 nào được chạy.

**Kết luận cho M56:**
- Vẫn **0 số A/B hợp lệ**.
- Lần A/B duy nhất của C01 và C02 là lần v2.1 (§3).
- Với đèn tín hiệu, cửa sổ khả thi rất hẹp:
  - chu kỳ 60,4 s nhỉnh hơn 60 s;
  - khoảng đỏ toàn bộ dài 41 tick không phân biệt được ở tick đầu tiên.
- Muốn có số A/B thì cần Duy quyết một trong các hướng sau, đều là đổi quy tắc:
  - cho phép neo ở tick gần nhất mà gói pha là duy nhất;
  - thời gian chờ dài hơn một chu kỳ;
  - chọn site C không có đèn.

## 6. v3 cùng signal-phase erratum 4: A/B native, mỗi cảnh một lần (24/10/2026)

**Thẩm quyền:** erratum 4 (commit 7374ed7) được đặt sau khi thấy kết quả chuẩn bị v3 và báo theo cả hai quy tắc. Theo
quy tắc cũ, C01 là `SIGNAL_ANCHOR_AMBIGUOUS` và không có A/B. C02 được chuẩn bị lại một lần theo quyết định của Duy.

**Đầu vào:**
- Chuẩn bị: `outputs/m56_v2_prepare_Town04_20261024T025829Z`. Cả C01 và C02 PREPARED, NPC không bị đèn giữ.
- C0 partial v3: `outputs/m56_c0_partial_v3_20261024T031543Z` (sha `ba365ef7…`).
- A/B: `outputs/m56_v2_ab_Town04_20261024T031822Z`.

**Lần đầu M56 có số đo native.** Các số dưới đây là **số đo thô, chưa được nhận** cho một cặp A/B hợp lệ.

| Cảnh, action | Trục sau W05 | Event | `d_yield_m` | `t_entry_s` | Lý do còn lại |
|---|---|---|---|---|---|
| C01 A | CONFIRMED / INCOMPLETE / UNCERTAIN | TRIGGER, NPC_ENTRY, CLEAR_N_CONFIRMED | 2,046 (VALID) | INCOMPLETE | `TICK_ERROR` `COMMAND_ORDER` khi RESUME; thiếu E_ENTRY, DESTINATION |
| C01 B | CONFIRMED / UNKNOWN / INVALID | TRIGGER, NPC_ENTRY, CLEAR_N, E_ENTRY, **DESTINATION_CONFIRMED** | 10,557 (VALID) | 9,60 (VALID) | **chỉ** `DELIVERY_PROOF_INVALID` |
| C02 A | CONFIRMED / INCOMPLETE / INVALID | TRIGGER, STOP, NPC_ENTRY, CLEAR_N_CONFIRMED | 2,048 (VALID) | INCOMPLETE | `COMMAND_ORDER`; contact; fit |
| C02 B | CONFIRMED / UNKNOWN / INVALID | đủ tới DESTINATION_CONFIRMED | 9,421 (VALID) | 8,35 (VALID) | delivery; contact; fit |

### Đã được giải quyết

- **Vùng xung đột rộng theo làn (V3.2):** CLEAR_N giờ được xác nhận.
- **Route response EGO (V3.1):** hết `OFFSET_ROUTE_MISMATCH` và `PLAN_SOURCE_WITNESS_INVALID`.
- **Phần còn lại:** kit (contact/motion trên C01), initialization (E3/E5), W01, mặt đất, metric context và W05 đều qua.

### Lỗi harness đã sửa sau lần chạy (chưa chạy lại)

1. **`COMMAND_ORDER`** (commit 962febb): lệnh dừng tường minh không ghi frame vào phiên stock, nên RESUME bị coi là
   ngắt quãng.
2. **`DELIVERY_PROOF_INVALID` ở B** (commit 153678a): lifecycle và fence của cảm biến từ episode A còn lại khi chạy B
   (4 kênh thay vì 2).

### Giới hạn đo ở C02 (chưa chứng minh, không phải phán quyết)

- Cận dưới khoảng cách tới mép đường âm tới −0,106 m trong 99 frame đầu, trùng nhau ở A và B, trong pha tiếp cận. Thân
  xe nhô ra ngoài đa giác vùng lái mà Claude dựng từ waypoint 0,5 m.
- `CONTINUOUS_FIT_UNPROVEN` cũng đến từ các hộp vùng lái dựng bằng lưới. Có thể là lỗi của công cụ đo, cũng có thể là xe
  thật sự sát mép; chưa phân biệt được.

### Kết luận

- **Chưa có cặp A/B hợp lệ nào**, nên không làm được phép so D09.
- Hiệu số thô (**không được nhận**, chỉ để định hướng) của `d_yield_m` giữa A và B: C01 0,806; C02 0,783.
- Muốn có cặp hợp lệ thì cần Duy cho chạy thêm **một** lần với hai bản sửa harness (v3.1, cùng fixture và recipe).
- Riêng C02 vẫn có thể bị chặn bởi giới hạn đo mép đường.
