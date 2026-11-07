# M56 io-v1.3 + consumer v9: O04, O05, O07 (07/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** ủy quyền toàn quyền của Duy (tự xưng, 07/11/2026). Mọi quyết định dưới đây do Claude quyết dưới ủy quyền đó.

**Bản đăng ký trước:**
- `PREREG_M56_V9_IO_NOMINAL_SERIES_20261107.md` (`ce26bf7`).
- `PREREG_M56_IO_RECIPE_V1_3_FILL_O_20261107.md` (`de4c5cf`), kèm addendum A–D (`601433d`, `84e9a13`, `e5b09b0`, `7206078`).
- Tất cả được commit trước lần chuẩn bị có kết quả.

**Code:**
- Consumer `feat/m56-v9` `1db746f`: 420 test bị ảnh hưởng qua. 10 lỗi môi trường tái hiện y hệt trên v8.
- Tooling `feat/m56-v1` `7206078`.

## 1. Bốn lỗi code tìm ra trước khi có kết quả (addendum A–D)

| # | Lỗi | Sửa |
|---|---|---|
| A | Sáu candidate I/O fill20 v1 mang `k` đơn vị `index`, schema từ chối. Chúng **chưa bao giờ decode được**. | Áp F2-5 (`409911e`): k vào rationale; hai review được ràng buộc lại kèm lý do |
| B | Điểm đầu của route catalog nằm đúng s ≈ 0, CARLA chiếu vào connector | Chiếu điểm có arc ≥ 1 m |
| C | Kẹp ở L − 0,01 m làm `lane_rows` bước ra khỏi road | Kẹp ở [0,5; L − 0,5] |
| D | Compile đọc `c.parameters['Dlc']` | Dlc lấy từ đoạn đổi làn đã đóng băng |

Không lỗi nào đổi luật hình học §3 của prereg. Mỗi lần sửa là một commit riêng.

## 2. Kết quả chuẩn bị và compile

Chuẩn bị: lần (d), revision `outputs/m56_c0_partial_io_fillOv13d_20261107T141635Z`. Compile: `outputs/m56_io_compile_Town06_20261107T141930Z`.

| Cảnh | k, vE | Chuẩn bị | Compile, admission (v9) | Self-check | Replay offline |
|---|---|---|---|---|---|
| O04 (Town06 R37) | 4; 11,719 m/s | PREPARED. Plateau EGO 11,388, NPC 2,376; gap lúc t0 32,54 (catalog 32,955); route EGO 1149 → 37 → 1037 | **BLOCKED_FIXTURE `DOMAIN_CROSSING_UNBRACKETED`** | — | — |
| O05 (Town04 R39) | 0; 4,8 m/s | **BLOCKED_FIXTURE `PROBE1_NO_FRAMES`**: `SPAWN_ERROR:EGO`, "collision at spawn position". Điểm spawn đầu run-in nằm trên connector 1091 trong junction 1082 | — | — | — |
| O07 (Town06 R38) | −1; 3,84 m/s | PREPARED. Plateau EGO 3,705, NPC 2,376; gap lúc t0 9,07 (8,876); NPC tail cut 9,39 m (J332) | **FROZEN, ADMITTED**; EGO A, EGO B, NPC đều OK | PASS | A: chuỗi event đầy đủ, step_response OK; B: OK |

**Vì sao O04 bị chặn:**
- Consumer đòi cả route EGO lẫn route NPC phải đi vào và ra khỏi hộp domain [decision, X] ở giữa route.
- NPC của O04 bắt đầu ở road-s 70,44, tức là **bên trong** hộp [65,78; 158,65].
- Lý do: gap 33 m lớn hơn quãng NPC đi được (khoảng 2,4 m/s) trong lúc EGO chạy 125 m run-in.
- Đây là hệ quả hình học của cảnh cộng với luật run-in, không phải lỗi code.

**Theo §4.4:** O04 và O05 giữ BLOCKED. Phiên này không đổi tham số nào để cứu hai cảnh.

**Đề xuất cho một prereg sau** (đặt **sau khi** thấy số chuẩn bị, phải công khai như vậy):
- O05: spawn bên trong R39, với run-in ngắn hơn hoặc điểm spawn được kiểm va chạm.
- O04: route NPC bắt đầu trước hộp domain, ví dụ NPC chờ ở điểm xa hơn rồi xuất phát theo timer.

## 3. A/B O07 (đang chạy)

- Một A/B theo P5: `M56_IO_PREREG_APPROVED=7206078`, `M56_IO_KAPPA=pointwise`, product v9 `1db746f`.
- Pair theo v9 và theo v8.
- Theo v8, các cảnh có k ∉ {1, 2, 3} bị chặn ngay lúc admission.
