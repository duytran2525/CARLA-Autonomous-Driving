# M56 A-SEL2: prereg F (BẢN NHÁP, 08/11/2026, chưa có hiệu lực)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** A-SEL2 §1.4 và §5 (Duy, ngày 08/11/2026: "Claude soạn recipe F", "Claude đổi input F theo thang").

**Trạng thái:** bản nháp thiết kế. Chỉ trở thành prereg sau ba điều kiện:
1. có kết quả smoke test capability (`native-f-capability-smoke.py`: F03 trôi dốc, witness số lùi của F06);
2. khoảng `vN_char` của F03 được chốt từ số đo đó;
3. được commit trước A/B F đầu tiên.

## 1. Hai descriptor chung cho 15 phép so F

Mỗi giá trị cách giá trị kế tiếp ≥ 1,29 lần, cao hơn ngưỡng 1,25, để chừa biên cho realized. Ở C/L/M/I/O, biên realized đo được chỉ
khoảng 0,004 (nhật ký đợt chạy).

| Cơ chế | `vN_char` (m/s) | Nguồn / thay đổi so với §8 | `d0` (m) | Nghĩa của d0 |
|---|---|---|---|---|
| F06 lùi đỗ | 0,5 | §8.2 giữ nguyên (lùi 0,5 m/s) | 6,8 | khoảng hở trước của EGO đang giữ yên |
| F03 trôi dốc | trong [0,65; 1,54] | do độ dốc quyết định; chốt sau smoke | 5,2 | khoảng hở trước khi NPC bắt đầu trôi |
| F05 khởi hành chậm | 2,0 | §8.1 giữ nguyên (`NPC_QUEUE_FORWARD 2`) | 4,0 | EGO dừng sau hàng chờ |
| F04' (thay F04) | 2,6 | mới | 8,8 | khoảng cách tới NPC lấn làn lúc TRIGGER |
| F01 xe trước phanh | **3,4** | §8.1 là 3 → đổi thành 3,4 | 11,4 | khoảng hở trước lúc NPC bắt đầu phanh |
| F02 xe sau áp sát | 5,0 | §8.1 giữ nguyên (NPC phía sau 5 m/s) | 20,0 | đúng ngưỡng trigger gR ≤ 20 m của §8.1 |

Kiểm Δ của cặp gần nhau nhất:
- `vN_char`: 2,6/3,4 = 0,765 (Δ 0,235); 2,0/2,6 (Δ 0,231). F03 phải nằm trong [0,65; 1,54] mới cách được F06 và F05.
- `d0`: 5,2/6,8 = 0,765; 6,8/8,8 = 0,773; 8,8/11,4 = 0,772; 4,0/5,2 = 0,769. Tất cả đều Δ ≥ 0,227.

**Thay đổi input §8 được giữ ở mức tối thiểu:** F01 vN 3 → 3,4, cộng thêm `d0` khai báo cho mọi cơ chế. Input §8 gốc được ghi bên
cạnh trong mọi báo cáo.

## 2. Từng cơ chế (nháp)

- **F01:** NPC chạy trước ở 3,4 m/s. Tới marker thì phanh xuống 0 (≥ 1,5 m/s² trong 0,25 s), giữ 2 s, rồi chạy lại 3,4 m/s. EGO
  ở 4 m/s. A dừng thật rồi đi tiếp sau khi NPC chạy lại; B giảm còn 2 m/s rồi về 4 m/s. Cặp metric theo product:
  `a_peak_025`, `g_front_min_m`.
- **F02:** NPC phía sau ở 5 m/s, EGO 4 m/s (A) hoặc 5,5 m/s (B). Trigger khi gR > 20 → ≤ 20. Cặp `v_mean_E`, `g_rear_min_m`.
- **F05:** NPC đứng trong hàng chờ ≥ 1 s, EGO dừng sau. Nhả NPC sau 3 s, NPC đi 2 m/s. A chờ NPC đi được 2 m; B bò 0,5 m/s tới
  marker 1 m. Cặp `d_pre_move_m`, `t_queue_exit_s`.
- **F03:** EGO giữ yên sau NPC trên dốc ≥ 5%. NPC thả phanh ở số N và trôi lùi. Phanh của chương trình kích hoạt sau 2 s kể từ
  TRIGGER. A giữ yên; B lùi tối đa 2 m ở 0,5 m/s (ngoại lệ lùi có chặn). Cặp `d_reverse_m`, `g_front_min_m`. **Cần smoke.**
- **F06:** NPC đỗ, có cue số lùi và đèn lùi, rồi lùi 2 m ở 0,5 m/s. A giữ yên; B lùi 1 m ở 0,5 m/s. §8.2 ghi Δ trong cảnh khoảng
  0,10: phải chỉnh tham số giữ/lùi cho tới khi phác thảo lý tưởng đạt ≥ 0,20, rồi mới đóng băng. **Cần smoke cho witness số lùi.**
- **F04' (thay F04 cửa xe):** một NPC đỗ sát lề bất ngờ lấn 1 m vào làn EGO rồi dừng. EGO chọn giữa (A) dừng chờ NPC lùi về,
  và (B) lách trong làn với offset ≤ 0,75 m nếu đủ chỗ. Cơ chế này phải khác F01 (phanh dọc), F05 (khởi hành) và I (cắt làn để
  nhập), theo định nghĩa (trigger, cấu trúc quyết định) ở §2.2. Cần 5 lập luận cặp mới (04'–01, 04'–02, 04'–03, 04'–05, 04'–06).

## 3. Việc kỹ thuật kèm theo (không thuộc prereg)

- **Product v12:**
  - tham số hóa các kiểm F đang khóa cứng §8 (`response.py` khoảng dòng 300–370: F01 nominal 3 thành 3,4; thêm F04');
  - descriptor F theo §1;
  - test cho từng thay đổi.
- **Tooling native F** (compile fixture, prepare, A/B) theo mẫu `native-io-*`: site lấy từ pool R1/R3 của fill v4 trên 11 town,
  dùng spawn nghiêng và spectator.
- **Chọn site F:** fill v4 §5 cùng các addendum B–E, áp cho F với pool R1 (F01, F02, F04', F05, F06) và R3 (F03).

## 4. Smoke test capability, lần 1 (09/11/2026; `native-f-capability-smoke.py`, Town04)

- **F06:** `reverse=True` cho readback gear −1, và xe lùi được 0,455 m/s sau 3 s ở throttle 0,3. **Đèn lùi không tự bật**
  (`light_state` NONE). Tooling F06 phải đặt `VehicleLightState.Reverse` cho cue số lùi kèm đèn, và witness phải đọc lại đèn.
- **F03: chưa kết luận.** Probe chọn điểm "dốc nhất" của road 40 nhưng thật ra chỉ dốc 0,0027. Lỗi nằm ở cách probe dò dốc, nên
  xe không trôi. Phải test lại trên một site R3 có độ dốc ≥ 0,05 (`native-f03-grade-probe.py`).
