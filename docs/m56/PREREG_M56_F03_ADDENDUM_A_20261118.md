# M56 PREREG F phần 2 F03, addendum A (18/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thời điểm viết:** trước mọi prepare, compile và A/B của F03. Số duy nhất đã có là các probe capability r18e/f/g của PREREG phần 2 §1. Chưa có số nào về cảnh F03.

**Ngoại lệ nguyên tắc 6, công khai:** A1 được chọn sau khi đọc dịch chuyển lùi 1,90 m của r18f. Như phần 2, đây là probe vật lý, không phải cảnh, A/B hay metric.

**Thẩm quyền:** người dùng phiên này, [chat] 18/11: "hãy làm luôn f03 native tooling đi". Claude quyết dưới ủy quyền của Duy.

Hai lỗi thiết kế lộ ra khi bắt đầu viết tooling F03, trước khi chạy gì.

## A1. Product: NPC rời làn sau khi dừng (m56-v19 `dbd1a38`)

**Vấn đề:**
- EGO và NPC cùng một làn. d0 = 5,2 m (phần 1) là khoảng hở trước khi NPC bắt đầu trôi; r18f cho dịch chuyển lùi tịnh 1,90 m. Vậy ở A, sau khi NPC dừng, khoảng hở còn khoảng 3,3 m.
- Sau `NPC_STOP_CONFIRMED`, EGO chạy FORWARD 2 m/s (stock) tới DESTINATION. Cap `DESTINATION_ROOM` cần `exit_to_destination_m ≥ 5`. EGO sẽ đâm NPC đang đỗ trong làn, và collision thì FAILED.
- Bản tổng hợp `tests/m56/f03_cases.py` né được chuyện này vì NPC nằm trên một route dốc riêng.

**Luật mới:** biến thể `neutral-in-motion` (chỉ khi có `phases['release']`) thêm đúng một hàng thứ tư:

```
... → F03_BRAKE 0 after TRIGGER + 2 s → NPC_CLEAR 2 m/s after NPC_STOP_CONFIRMED + 0   (stock, như F05 NPC_QUEUE_FORWARD 2)
```

- Bản ba hàng của `eb9560c` bị thay thế. Chưa episode nào dùng nó.
- **Luật cũ, giữ nguyên:** không có cờ thì hàng `RESTART` sau `NPC_STOP_CONFIRMED` vẫn bị chặn (fault `restart` trong `test_f03_normative_response.py`).
- `NPC_CLEAR` nằm sau cửa sổ metric (TRIGGER → NPC_STOP_CONFIRMED). `_detect_f03` và cặp metric không đổi, nên luật dừng §5 (đổi metric) không kích hoạt.
- `_forward_tail` vẫn cấm station của NPC giảm sau khi dừng. Nếu NPC trôi lùi lúc nhả phanh để chạy tiếp, đó là FAILED, không chỉnh gì.
- Test: `test_v19_f03_neutral_release.py`, thêm các fault `clear_before_stop`, `fast_clear` và `no_clear` (bản ba hàng). 53 passed.

## A2. Tooling: readiness và cách đo d0 (không đổi product)

**Vấn đề:** phần 2 §3–§4 ghi "readiness lúc đứng yên, như F05". Runner settle 1 s rồi giữ 0,5 s, nên ready sớm nhất là khoảng 1,5 s sau CAPTURE_START. NPC_APPROACH bắt đầu ở 21/20 s, nên NPC không thể đứng yên lúc ready.

**Sửa (chỉ là chữ trong tooling):**
- Readiness dùng mẫu NOMINAL của F01/F02, cùng mốc 21/20. NPC: target là tốc độ trung bình đo được trong 1 s trước lệnh UNPOWERED (luật plateau f-v1.1, làm tròn 1/1000, dải ≤ 0,10 m/s, > 0,5), marker trên đường tiến. EGO: target 0, marker ở chỗ đứng.
- Ready phải đến trước lệnh UNPOWERED (CAPTURE_START + 81/20). Nếu không, `BLOCKED_FIXTURE`.
- **d0** theo đúng chữ phần 1: khoảng hở thân xe EGO-front → NPC-rear, đo ở khung của lệnh UNPOWERED đầu tiên. Đích 5,2, dải sai 0,3. Prepare chọn khoảng hở lúc spawn bằng 5,2 trừ quãng tiến đo được trong một probe, rồi kiểm lại bằng probe thứ hai.
- **DESTINATION:** F03 không có section END. Mốc exit là station mũi EGO lúc ready. DESTINATION ở exit + 6 m (như bản tổng hợp); plan end ≥ DESTINATION + 5.

## Không đổi

- vA, d1, d2, luật phanh, `_detect_f03`, metric, ngưỡng Δ ≥ 0,20.
- Site Town12 1062/−1, successor 1085/1.
- EGO B `bounded-reverse-stop-v2`, trần 2 m.
- P5: một A/B. Pair dưới v19 và dưới v18.

## A3. Probe trước A/B (thay cho "một probe của prepare", §4 phần 2)

- Probe prepare không chạy được kịch bản NPC F03 thật: kịch bản này cần fixture đã compile và kit (ROLLBACK, cửa sổ phát hiện). Vì vậy episode do runner ghi để replay là **một episode A duy nhất trên fixture đã đóng băng** (`native-f-ab.py --probe-a`).
  - Kit ghi cả các trường của B (`reverse_corridors`, `reverse_history_ref`) để replay kernel B.
  - Episode này không ghép cặp, không phải A/B, không tính vào P5.
- Gate `native-f03-replay.py`:
  - `detect_events` cho TRIGGER và NPC_STOP_CONFIRMED, không có WITNESS_UNKNOWN;
  - thứ tự phase của NPC đúng;
  - kernel B (`reverse_intent`) trả REVERSE trong 2 s sau TRIGGER;
  - evaluator của product trên probe-A: physical không FAILED, không COLLISION_OBSERVED, có DESTINATION_CONFIRMED;
  - khoảng TRIGGER → NPC_STOP_CONFIRMED đo được ≥ `stop_confirmed_s` của trial đã chọn + 1/20 s (A4).
  - Không đạt thì không chạy A/B; ghi lại đúng như đo.
- Kết quả của probe-A (verdict, khoảng hở) **không được** đổi bất kỳ tham số nào. Nó chỉ là cổng chạy / không chạy.
- Calibration REVERSE_STOP_BOUND dùng probe API trực tiếp, sao đúng luật kernel v2, trên pose EGO đã đóng băng (không có NPC). Quyết định STOPPING dùng vmax tạm 1,5 m/s; biên cuối dùng vmax đo được.

## A4. Biên dừng lùi của EGO B phải vừa cửa sổ (viết trước mọi số của trial lùi)

**Vấn đề:** evaluator F03 B (metrics, nhánh F03/F06) đòi lần lùi cuối của EGO và một lần dừng giữ 0,5 s (`_observed_stop`) **nằm trong** cửa sổ TRIGGER → NPC_STOP_CONFIRMED. Nếu không, kết quả là `RESERVATION_STOP_NOT_CONFIRMED`. Theo r18f, cửa sổ đó khoảng 2,05 + 0,9 + 0,5 ≈ 69/20 s. Biên `2 − bound − 0,02` (khoảng 1,7 m) ở 0,5–0,8 m/s rất có thể không vừa.

**Luật:**
- Bốn trial lùi với biên b ∈ {1/2, 4/5, 6/5, 8/5} m (thay cho {4/5, 6/5, 8/5, 2}). Mỗi trial ghi `stop_confirmed_s`: thời gian từ tick REVERSE đầu tiên tới khi dừng xác nhận 0,5 s (11 khung ≤ 0,1 m/s).
- `bound` và `vmax` như cũ: lấy trên cả bốn trial, cộng lề.
- `stopping_boundary_m` là b lớn nhất thỏa cả hai điều kiện:
  - b + bound + 0,01 ≤ 2 − 0,01;
  - `stop_confirmed_s(b)` + 1/20 ≤ 69/20 − 1/2.
- Không có b nào thỏa thì `BLOCKED_FIXTURE F03_REVERSE_TOO_SLOW_FOR_WINDOW`.
- Cặp metric chỉ cần Δ ≥ 0,20, nên một biên nhỏ là đủ.
- Gate probe-A (A3) kiểm lại cửa sổ thật trên episode native.

## A1 (bổ sung, m56-v19 `4021c9d`)

Code NPC F03 của v18 ghi đè mọi lệnh stock bằng phanh 0,3 hoặc trôi. Với biến thể mới, ghi đè này sẽ biến NPC_APPROACH và NPC_CLEAR thành lệnh giữ phanh. Giờ ghi đè chỉ áp cho các phase có target 0. Mọi phase của F03 v18 đều có target 0, nên luật cũ giữ nguyên từng byte. Test `test_stock_phases_are_not_brake_holds`; 56 passed.


## A5. v20: sửa điều phối lùi của runner (viết SAU khi đã thấy kết quả A/B v19; công bố theo nguyên tắc 6)

Nhãn: CLAUDE_REVIEW_UNDER_DUY_DELEGATION (advisor đã xem trước khi viết).

**Đã xảy ra.** A/B F03 của v19 chạy một lần duy nhất (P5 đã tiêu thụ), thư mục `outputs/m56_f_ab_Town12_20261118T192541Z/M56-P-F03-S1`.
- Nhánh A chạy đủ: NPC HOLD → APPROACH → UNPOWERED → F03_BRAKE → CLEAR; EGO giữ rồi tiến.
- Nhánh B: EGO **không vào số lùi**, xe chạy tiến (REVERSE_CONTROL_MISMATCH, FORWARD_RESCUE_BEFORE_RELEASE, d_reverse 0).
- Cặp dưới v19: FAILED, so sánh null (metric nhánh B UNKNOWN, khung rỗng). Cặp dưới luật v18 (`m56_v6_pair_20261118T200402Z`): FAILED, nhánh A physical UNKNOWN, nhánh B có NORMATIVE_RESPONSE_INVALID. Đánh giá offline: cả hai nhánh INVALID.
- Hai kết quả này được báo đúng như đo, dưới cả luật v19 (`m56_v6_pair_20261118T194532Z`) lẫn v18. Không có cặp PASS cho F03-S1.

**Nguyên nhân (tái hiện offline trên episode probe-A r19d, không cần CARLA).** `runtime._bounded` kiểm `isinstance(meta, dict)`. Sau khi đáp ứng được giải mã và đóng băng (`FrozenResponse`), `phases` là `mappingproxy`, nên `_bounded` luôn False và runner gửi `step_response` thay vì `reverse_intent`. Consumer (`evidence._phase_integrity`) dùng `Mapping`. Runner lệch chính luật điều phối của consumer: đây là **lỗi sản phẩm**, không phải lỗi tooling.

**Sửa (m56-v20 `22c57cf` = v19 + một thay đổi: `_bounded` dùng `Mapping`).**
- Không đổi spec, ngưỡng Tag, tham số, fixture, evidence, metrics. `git diff v19..v20` chỉ gồm `m56/runtime.py` và test.
- `test_v20_bounded_dispatch.py`: 3 test, đỏ trước sửa, xanh sau (190 s). Bộ giả lập F03 giờ có `dispatch='runtime'`: giải mã fixture rồi gọi `runtime._commands` thật.

**Vì sao v20 là phiên bản mới hợp lệ theo P5.** F05 trước đó hỏng do tooling (cùng phiên bản chạy lại được). Ở đây runner của sản phẩm lệch consumer của sản phẩm, nên đổi sản phẩm là phải và cần một phiên bản mới; A/B v19 giữ nguyên như đã đo, không bị xóa hay viết lại.

**Công bố các điều đã thấy.**
- Số của nhánh A v19 đã thấy (g_front_min ≈ 3,06 m, d_reverse 0) trước khi viết v20. Không có dòng code, tham số, hay fixture nào của v20 phụ thuộc vào chúng.
- Không diễn tập nhánh B. Dùng lại nguyên byte artifact r19d (REVF, prepare, probe-A, `m56_f_sites_f03_20261118.json`); không prepare lại. d0 5,25 m, NPC 0,695 m/s, T_r 3,3 s, biên dừng 1/2 m như cũ.

**Cổng mới trước A/B v20 (tooling).** `native-f03-replay.py` giờ kiểm `runtime._bounded(B)` và gọi `runtime._commands` thật cho mỗi khung từ TRIGGER tới +2 s: phải ra REVERSE, `reverse`, `manual_gear_shift`, gear −1, steer 0, throttle trong [0; 0,4]. Chế độ đầy đủ chạy thêm evaluator (không FAILED, không COLLISION_OBSERVED, có DESTINATION_CONFIRMED) và đòi TRIGGER → NPC_STOP_CONFIRMED đo được ≥ `stop_confirmed_s` + 1/20. Trên probe-A r19d (TRIGGER 8353, NPC_STOP 8413, DESTINATION 8541): dưới v19 **FAIL** (`bounded_B=false`, kernel đầu ra CONTROL), dưới v20 **PASS** (REVERSE từ 8353, 41 lệnh, throttle ≤ 0,39).

**Cổng đĩa (yêu cầu của Duy 19/11).** Không khởi động CARLA nếu D: trống < 80 GB hoặc E: trống < 150 GB: `asel2-cguard.py --wait-commit-gb` chờ cả hai ngưỡng, và `native_v2_common.own_server` từ chối khởi động. Không đổi luật guard khi đang chạy (không ghi STOP vì D/E).
