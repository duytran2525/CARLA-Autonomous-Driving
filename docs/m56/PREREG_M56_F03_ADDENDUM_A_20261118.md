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
  - kernel B (`reverse_intent`) trả REVERSE trong 2 s sau TRIGGER.
  - Không đạt thì không chạy A/B; ghi lại đúng như đo.
- Kết quả của probe-A (verdict, khoảng hở) **không được** đổi bất kỳ tham số nào. Nó chỉ là cổng chạy / không chạy.
- Calibration REVERSE_STOP_BOUND dùng probe API trực tiếp, sao đúng luật kernel v2, trên pose EGO đã đóng băng (không có NPC). Quyết định STOPPING dùng vmax tạm 1,5 m/s; biên cuối dùng vmax đo được.
