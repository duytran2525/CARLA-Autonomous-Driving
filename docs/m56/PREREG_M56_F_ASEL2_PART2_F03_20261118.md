# M56 PREREG F phần 2: F03 (xe trước trôi lùi trên dốc), 18/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thời điểm viết:** trước mọi prepare, compile và A/B của F03. Chưa có số nào về cảnh F03.

**Ngoại lệ nguyên tắc 6, công khai:** cách thả NPC (đang chạy rồi về số N) được chọn **sau khi** đọc các probe capability r18e, r18f và r18g. Đây là ngoại lệ dành cho cổng thăm dò. Các probe này chỉ đo vật lý của xe trên dốc; chưa có cảnh, chưa có A/B, chưa có metric.

**Thẩm quyền:**
- Người dùng phiên này, [chat] 18/11: "làm hết cho tôi" và "theo dõi tiến trình hiện tại và làm tiếp".
- Bộ nhớ 2026-11-10: Duy vắng mặt, Claude quyết theo đề xuất của chính mình.
- Claude quyết dưới ủy quyền của Duy. PREREG F phần 1 (`3fb9865`) để dành F03 cho phần 2.

## 1. Bằng chứng capability (probe quan sát, xe vehicle.audi.a2, không phải cảnh)

| Probe | Kết quả |
|---|---|
| r7 (09/11) và r18d | Không phải bằng chứng (đính chính ở batch log 18/11 (4)). r7 chỉ thả từ đứng yên. r18d để xe ngủ vì thiếu `M56_SPECTATOR`. |
| r18e | Lùi chỉ xảy ra khi xe **đang chạy rồi về số N**. Thả từ đứng yên sau phanh: không chuyển động. Đang chạy rồi thả ở số tự động: xe giữ yên. |
| r18f/r18g (phanh 0,3 từ TRIGGER + 2 s, đúng luật `_detect_f03`) | Town12 1062/−1: lùi trung bình 2 s là 0,946 m/s, đỉnh 1,56, dừng sau 0,9 s, dịch chuyển tịnh 1,90 m. Town12 1085/1: 0,854 m/s, đỉnh 1,40, dừng, 1,29 m. |

- Cả hai giá trị lùi trung bình nằm trong khoảng vN_char [0,65; 1,54] của phần 1.
- Cả hai dịch chuyển tịnh đều nhỏ hơn nhiều so với d0 = 5,2 m.
- Cả hai site đều thẳng trục: 0,13° và 0,12°, đạt luật căn trục v14 cho EGO B lùi.

## 2. Luật product đổi (m56-v19 = v18 + đúng thay đổi này)

**Luật cũ, giữ nguyên:** contract NPC F03 của v18.
- Biến thể `NPC_HOLD → UNPOWERED → F03_BRAKE`, hoặc biến thể legacy.
- Lệnh `UNPOWERED` sao lại số đọc lại (readback gear).
- Natively F03 dưới luật cũ không thể xảy ra (theo r18e). Đây là một nhận định, không phải số đo trên cảnh. Mọi kết quả đều báo dưới cả hai luật.

**Luật mới:** thêm một biến thể contract `approach`. Biến thể này chỉ có khi khóa `phases['release'] == 'neutral-in-motion'` (`f_script` vẫn giữ đúng `{mechanism, policy_hash}`); không có khóa thì mọi byte giữ như cũ. Product: m56-v19 `eb9560c`, test `test_v19_f03_neutral_release.py`.

```
NPC_HOLD 0 → NPC_APPROACH vA          after CAPTURE_START + d1   (stock LocalPlanner, như NOMINAL)
           → UNPOWERED 0              after CAPTURE_START + d2   (d2 > d1)
           → F03_BRAKE 0              after TRIGGER + 2 s        (không đổi)
```

- `vA = 4/5 m/s`, `d1 = 21/20 s` (RELEASE), `d2 = d1 + 3 s`. Các giá trị đóng băng ở đây.
- Lệnh của `UNPOWERED` trong biến thể này: throttle 0, brake 0, steer 0, hand_brake False, `manual_gear_shift True`, `gear 0`. Đây là số N, không phải số lùi.
- `F03_BRAKE` vẫn theo luật cũ: brake 0,3, ở cùng số N.
- `_detect_f03` **không đổi**: trigger khi lùi ≥ 0,2 m/s trong 0,25 s, không có lực kéo (unpowered), đang trôi xuống.

## 3. Recipe và site

- **Site:** pool R3 grade của fill v4 (|dốc| ≥ 0,05 trên ≥ 40 m). Xếp theo độ dài grade run, lấy site đầu tiên thỏa cả ba điều kiện:
  - làn hướng lên dốc;
  - grade segment thẳng trục (lệch ≤ 1°);
  - probe neutral-in-motion cho vN trong [0,65; 1,54].
  - Theo thứ tự đó: **Town12 road 1062, lane −1**. Successor (B3) là Town12 1085/1.
- **Vị trí xe:** EGO đứng sau NPC trên cùng làn, cả hai đứng yên. d0 = 5,2 m là khoảng hở thân xe lúc ready (readiness khi đứng yên, như F05), dải sai 0,3 m.
- **Pha EGO:**
  - A: giữ yên (`HOLD_ACTION_MOVED` nếu > 0,1 m/s).
  - B: lùi theo luật `bounded-reverse-stop-v2`, trần 2 m, không đổi.
- **Metric:** cặp F03 của product (`d_reverse_m`, `g_front_min_m`), cửa sổ TRIGGER → NPC_STOP_CONFIRMED. Một cặp F đạt khi cả hai Δ ≥ 0,20 (phần 1).

## 4. Tooling (đường code mới, F01, F02, F05 không đổi)

- **Prepare F03:** settle cả hai (như F05), đặt d0, readiness lúc đứng yên.
  - Một probe NPC chạy biến thể `approach` của product, EGO giữ yên. Probe ghi lại: TRIGGER có xảy ra, vN thực, NPC dừng, gap nhỏ nhất.
  - Nếu gap ≤ 0,2 m hoặc không có TRIGGER thì `BLOCKED_FIXTURE`.
- **Calibration REVERSE_STOP_BOUND** (v2) cho EGO lùi trên chính dốc này. Làm như calibration bò của F05 (addendum U §4.3): bốn probe, đặt biên với cùng các lề.
- **Kit (per frame):**
  - `rollback` (`ROLLBACK`, `unpowered-grade-motion-v1`, `gravity_along_reverse_mps2 = g·sin(pitch)` > 0);
  - `reverse_corridor`;
  - `reverse_history_ref`, bỏ khung boundary (bài học F05, `a032cbf`).
- **Trước A/B:** replay **một episode do runner native ghi** (một probe của prepare) qua kit, `detect_events` và các hàm step. Không chỉ dùng bản kiểm offline tổng hợp.
- **Chuỗi:** stage 1 rồi **một** A/B (P5) dưới v19. Pair dưới v19, và dưới v18 (luật cũ).

## 5. Luật dừng

- Prepare hoặc compile bị chặn thì ghi đúng như đo, không chỉnh ngưỡng.
- Một A/B đã tiêu thì không chạy lại (P5).
- Nếu luật mới của product kéo theo phải đổi metric, thì dừng lại và đề xuất F03' cho Duy. Không chồng thêm luật sau-số.
