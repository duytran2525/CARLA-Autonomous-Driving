# M56 A-SEL2: prereg F, phần 1 (09/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.
Selector: `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`.

**Thẩm quyền:** A-SEL2 §1.4 và §5 (Duy, ngày 08/11/2026: "Claude soạn recipe F", "Claude đổi input F theo thang").

**Thời điểm:** commit trước mọi A/B F. Chưa có số đo F nào. Bản này thay bản nháp `PREREG_M56_F_ASEL2_DRAFT_20261108.md`; bản nháp
được giữ nguyên. Phần 2 (F03 và F04') sẽ commit riêng, trước A/B đầu tiên của hai cơ chế đó.

## 1. Descriptor chung cho 15 phép so F

Hai descriptor, khai báo trên candidate và realized theo `DESCRIPTOR_SPECS_M56_ASEL2_20261108.md` §1:

| Tên | Nghĩa |
|---|---|
| `vN_char` (m/s) | tốc độ đặc trưng của NPC trong cơ chế |
| `d0` (m) | khoảng hở dọc ban đầu giữa thân EGO và thân NPC lúc ready |

Một cặp F đạt khi **cả hai** có Δ ≥ 0,20.

| Cơ chế | `vN_char` | `d0` | So với §8 |
|---|---|---|---|
| F06-ALT1 | 0,5 | 6,8 | giữ nguyên (lùi 0,5 m/s) |
| F03 | trong [0,65; 1,54] (phần 2) | 5,2 | do độ dốc quyết định; site chọn theo khoảng này |
| F05 | 2,0 | 4,0 | giữ nguyên (`NPC_QUEUE_FORWARD 2`) |
| F04' (thay F04) | 2,6 | 8,8 | cơ chế mới (phần 2) |
| F01 | **3,4** | 11,4 | đổi: §8.1 là 3 |
| F02 | 5,0 | 20,0 | giữ nguyên; d0 = ngưỡng gR của §8.1 |

- Mọi cặp lệch nhau ≥ 1,25 lần trên cả hai descriptor. Riêng F03 được xét theo khoảng của nó.
- Input §8 gốc được ghi bên cạnh trong mọi báo cáo.
- Consumer `m56-v13` chỉ đổi đúng một chỗ: tốc độ danh nghĩa NPC của F01 là 17/5 (khóa cứng 3 ở m56-v12). Luật cũ được giữ báo
  song song.

## 2. Recipe phần 1

Theo product hiện có (`response.py` normative F, `metrics.py` event và metric F). Chỉ các giá trị ở §1 thay đổi.

- **F01** (xe trước phanh):
  - EGO 4 m/s. NPC 3,4 m/s, xuất phát trước EGO sao cho khoảng hở lúc ready là d0 = 11,4 m.
  - Marker `F01_BRAKE_START`: NPC phanh về 0 (≥ 1,5 m/s² trong 0,25 s), giữ, rồi chạy lại 3,4 m/s sau
    `NPC_F01_STOP_HOLD_CONFIRMED`.
  - A: dừng thật, rồi đi tiếp sau `N_MOVE`. B: giảm về 2 m/s, rồi về 4 m/s.
  - Cặp metric (`a_peak_025`, `g_front_min_m`). Kết thúc ở `F01_N_CLEAR`.
- **F02** (xe sau áp sát): NPC phía sau ở 5 m/s. EGO 4 m/s (A) hoặc 5,5 m/s (B). Trigger khi gR > 20 → ≤ 20. Cặp
  (`v_mean_E`, `g_rear_min_m`).
- **F05** (khởi hành chậm):
  - NPC đứng trong hàng chờ, cách EGO d0 = 4 m. Nhả sau 3 s, đi 2 m/s.
  - A chờ NPC đi được 2 m. B bò 0,5 m/s tới marker 1 m.
  - Cặp (`d_pre_move_m`, `t_queue_exit_s`).
- **F06-ALT1** (lùi đỗ):
  - NPC có cue số lùi **kèm đèn lùi do tooling đặt** (`VehicleLightState.Reverse`; smoke ngày 09/11 cho thấy đèn không tự bật),
    rồi lùi 2 m ở 0,5 m/s.
  - A giữ yên. B lùi 1 m ở 0,5 m/s.
  - Δ trong cảnh khoảng 0,10 (§8.2) vẫn là rủi ro: phác thảo lý tưởng phải đạt ≥ 0,20 trước khi compile. Nếu không đạt, F06
    được ghi `DIVERSITY_DEFICIT` trước A/B, và không chỉnh gì thêm.

## 3. Chọn site

- Pool R1 của fill v4 trên 11 town, với cổng trục B5 (đoạn thẳng trục ≥ chiều dài cần), cổng dốc ≤ 0,02, và các luật chạy đà.
- Seed: `SEED = int(sha256("M56-F-ASEL2-2026-11-09")[:16 hex], 16)`.
- First-fit theo thứ tự xáo; mỗi cơ chế một site; trần (F, town) = 3; tính chung trần thay cảnh 150.
- Chiều dài cần:
  - F01, F05, F06: 120 m;
  - F02: 110 m;
  - đều cộng thêm chạy đà vE²/3 + 20 m.
