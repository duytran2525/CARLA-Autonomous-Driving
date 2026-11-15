# M56 io-i-v1.2, addendum H: probe 3 sau compile (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "tôi duyệt recipe mới bạn hãy làm đi" (batch log 0319e85), và "làm recipe I
trước đi" (15/11, tối).

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Addendum này được viết:
- sau các A/B io-i-v1.1 đã niêm của I01–I07;
- sau dự báo offline ở mục 4, chạy trên chính các frame đã niêm đó;
- trước mọi bước native của io-i-v1.2.

Addendum **không đổi** 14,0 s (G1), 2,3 s (G3) hay đuôi X + 2L + 10 m (G2). Con số mới duy nhất là giới hạn dừng ở mục 2.3.

## 1. Vì sao cần addendum

io-i-v1.2 mục 2.1 đặt probe 3 trong prepare, chạy bằng "đúng chương trình EGO A … của fixture sẽ compile". Cách này không chạy được,
vì cùng lý do với io-v1.6 §2b: chương trình A/B thật cần các guard sự kiện (TRIGGER, SOURCE_CLEAR_CONFIRMED, …). Các guard đó chỉ tồn
tại sau compile, khi runner A/B đã được bind với fixture. Vì vậy:

- **Probe 3 chạy sau compile và trước A/B, trong cùng process A/B.** Nó dùng cùng fixture đã niêm, cùng backend và cùng server.
  Nhờ vậy A/B chạy đúng trên fixture mà probe 3 đã kiểm.
- Probe 3 gọi **chính `runtime.run_episode` của product** với action A. Không viết lại vòng lặp runner, vì một bản chép có thể lệch
  khỏi runner, và "probe không đại diện cho A/B" chính là lỗi I01.

## 2. Luật

1. **Namespace riêng:** probe 3 ghi vào `<scene>/probe3`, không bao giờ vào `<scene>/run` hay `episodes/<scene>`. Không đưa nó cho
   consumer cặp nào. Probe 3 không phải A/B và không tính P5.
2. **Cắt ngắn:** episode dừng ở frame đầu tiên thỏa một trong ba điều kiện:
   - đã thấy t_clear;
   - đã quá TRIGGER + 2,3 s;
   - chưa có TRIGGER và đã quá ready + 20 s.

   Cơ chế cắt: trong riêng episode probe 3, `runtime.VALIDATION_S` được đặt về 0. Runner tự dừng ở bước kiểm validation của nó, rồi
   cleanup và seal như mọi episode.
   - Ở cảnh I, EGO A chỉ bắt đầu nhường sau TRIGGER. Vậy probe 3 cho thấy tối đa 2,3 s đầu của phản ứng A. Mốc đổi làn của B
     (khoảng 3,3 s sau TRIGGER) không bao giờ xuất hiện trong probe 3.
3. **Giới hạn 20 s khi không có TRIGGER:** đây là con số mới, đặt sau khi thấy số. Nó chỉ chặn probe 3 khỏi trở thành một episode A
   đầy đủ (60 s). Cảnh hết 20 s mà không có TRIGGER thì G3 không thể đạt, và bị ghi `SOURCE_CLEAR_LATE`. Trên frame đã niêm,
   ready → TRIGGER dài 8,35–10,75 s (mục 4). Bản nháp đầu đặt 10 s, và mức đó sẽ cắt nhầm I05-S1 và I06, nên đã nâng lên 20 s
   trước mọi bước native.
4. **G1:** ready − frame đầu ≤ 14,0 s. "Ready" dùng chính predicate `_ready` của runner, chạy lại trên cùng các frame, với cùng mốc
   settle (frame đầu tiên ≥ SETTLE_S sau boundary). Không đạt → `BLOCKED_FIXTURE READINESS_PROBE3`.
5. **G3:** t_clear − TRIGGER ≤ 2,3 s.
   - t_clear là frame đầu tiên ≥ TRIGGER mà mọi đỉnh body của NPC nằm ngoài hộp `EGO_TARGET` (làn nguồn), tính theo giới hạn xy của
     hộp. Điểm nằm trên biên tính là còn trong hộp.
   - Thời điểm `SOURCE_CLEAR_CONFIRMED` của product (giữ 0,25 s) được ghi bên cạnh nếu xuất hiện trước lúc dừng, nhưng không dùng
     làm cổng.
   - Không đạt → `BLOCKED_FIXTURE SOURCE_CLEAR_LATE`.
6. **G2 (kiểm trên fixture):** DESTINATION − X ≥ L + 10 m, với L = 2 × half-length của body EGO native (`a2-bbox.json`). Không đạt →
   `BLOCKED_FIXTURE IO_I12_TAIL_SHORT`.
7. Mọi cổng đạt → `runtime.run_ab` không đổi (một A, một B). Có cổng không đạt → không A/B, ghi `<scene>/io-i12-gates.json`.

## 3. Phạm vi cập nhật

- **I01-S1, I02-S2:** chạy lại chính cảnh, theo io-i-v1.2 §3. vE = 6 và 7,5, nên Dlc = 3·vE ≥ 18 m. Sàn io-v1.6 không đổi gì với hai
  cảnh này, và contract consumer `length == 3·nominal` vẫn đạt.
- **I08:** successor B3 qua gate G (vE 18,3).
- **I05-S1, I06, I07-S1 (successors):** vE = 4,8 / 3,07 / 3,84, nên Dlc_eff = 18 m ≠ 3·vE. Native 15/11 cho thấy contract consumer
  (m56-v12 `response.py` 1490, gọi từ `evidence._lateral_integrity`) chặn mọi profile có Dlc ≠ 3·vE: O05-S1, O06, O07-S2 đều dừng
  ở `LATERAL_LENGTH_INVALID`, không có A/B.
  - Đổi contract đó là đổi luật consumer, nằm ngoài phạm vi người dùng đã duyệt.
  - Vì vậy ba successor này **chờ quyết định của người dùng**. Không dựng, không chạy native cho tới khi có quyết định.
  - G4 (guard đi tiếp của A, product v15) cũng chỉ cần cho nhóm này.
- Trước mọi successor I/O mới, gate G thêm hai kiểm offline:
  - `length == 3·nominal`;
  - khoảng cách làn làm tròn mm tại decision phải bằng separation của profile (lỗi O08-S2 15/11).

## 4. Dự báo offline trên frame đã niêm (io-i-v1.1)

Script dự báo chỉ đọc episode B đã niêm (`trajectory.json`) và chạy `detect_events` cùng `_ready` của m56-v12, giới hạn ở 30 s
đầu. t_clear tính theo mục 2.5, với `world_vertices(body, pose)` của product: đỉnh body trong frame là tọa độ cục bộ của xe, và
bản nháp đầu đã dùng nhầm chúng.

| Cảnh (io-i-v1.1) | Kết quả cũ | ready (G1 ≤ 14) | ready → TRIGGER | t_clear − TRIGGER (G3 ≤ 2,3) | `SOURCE_CLEAR_CONFIRMED` − TRIGGER |
|---|---|---|---|---|---|
| I03 | PASS | 6,10 | 9,35 | 1,65 | 2,55 |
| I04 | PASS | 7,40 | 8,50 | 1,45 | 2,15 |
| I02-S2 | A `X_END_MISSING`, B `LANE_CHANGE_GUARD_MISSING` | 6,85 | 8,35 | **2,05** | chưa có khi B dừng (≈ 3,1 s sau TRIGGER) |
| I05-S1 | va chạm, `CHANGED_BEFORE_SOURCE_CLEAR` | 4,25 | 10,75 | **2,60** | chưa có |
| I06 | như trên | 3,45 | 10,75 | không có trong episode | chưa có |
| I07-S1 | như trên | 4,40 | 9,90 | không có trong episode | chưa có |
| I01-S1 | A, B `READINESS_NOT_REACHED` | episode không seal, không có trajectory | — | — | — |

Đọc bảng (nhận định của Claude):
- G1 đạt ở mọi cảnh có trajectory. I01-S1 chưa từng ready trong A/B, và io-i-v1.2 không đổi gì ở động lực học trước ready. Vì vậy
  dự báo I01-S1 **dừng ở G1** (`READINESS_PROBE3`), không tốn A/B.
- G3 chặn I05-S1/I06/I07-S1 đúng với lỗi cũ của chúng, và cho qua I03/I04.
- **G3 không dự báo được lỗi B của I02-S2.** t_clear hình học là 2,05 s, nên I02-S2 qua G3. Nhưng episode B đã niêm lại hỏng đúng ở
  guard của B: tới mốc đổi làn (≈ 3,1 s sau TRIGGER) vẫn chưa có `SOURCE_CLEAR_CONFIRMED`.
  - Sự kiện của product luôn trễ hơn t_clear hình học: 0,70 s ở I04, 0,90 s ở I03, và hơn 1,05 s ở I02-S2. Lý do là product đòi
    biên 0,5 m qua ranh làn, đòi corridor, và giữ 0,25 s.
  - Giả định của io-i-v1.2 §2.3 ("còn biên 1 s") không đúng với I02-S2.
  - Nếu chạy đúng như đã viết, I02-S2 sẽ tiêu A/B duy nhất của nó, và B nhiều khả năng hỏng lại như cũ.
- Đổi định nghĩa hay ngưỡng của G3 lúc này là đổi cổng sau khi thấy số. Việc đó cần người dùng quyết; addendum này không làm.

## 5. Cách làm

- `native-io-prepare-i12.py`: nạp `native-io-prepare-v16.py` (io-v1.5 + io-v1.6), biên dịch lại `_prepare_o` từ chính byte của nó
  với một biểu thức thay thế: đích EGO của cảnh I = X + 2L + 10 m. Không sửa file nào đang đóng băng.
- `native-io-ab-i12.py`: nạp `native-io-ab.py`, thay `runtime.run_ab` bằng G2 → probe 3 → G1/G3 → `run_ab` gốc.
- Self-test offline: `test-native-io-ab-i12.py`.
- Batch `run-asel2-io-i12.sh`, chạy với product m56-v12 + spawn tilt, I01-S1 (Town12) và I02-S2 (Town13). Pair dưới m56-v12 và
  m56-v10.
- Luật dừng giữ như io-i-v1.2 §3: một revision. Hỏng thì FAILED, không chỉnh thêm.
