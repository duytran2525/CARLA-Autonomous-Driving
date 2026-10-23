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
