# M56 A-SEL2 addendum K: replacement 9 (I05–I08, O04, O08) và cổng khoảng cách làn offline (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "trong khi đợi chạy full suite thì tiếp tục sửa các cảnh còn lại đi". Lời này
nối tiếp lời duyệt recipe 15/11 (0319e85) và lựa chọn sàn NPC (addendum J).

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Addendum được viết sau lỗi O08-S2 (`IO_LANE_SEPARATION_MISMATCH`), trước mọi
bước native của các successor dưới đây.

## 1. Cổng khoảng cách làn offline (mới)

`native-io-sepgate-offline.py`:
- Tại road-s của decision, lấy hai waypoint XODR (làn EGO, làn đích) trên `carla.Map` offline.
- Khoảng cách theo trục thế giới, làm tròn mm như `io_geometry`, phải bằng offset của đoạn đổi làn đóng băng (O: EGO A, I: EGO B).
- Phải có thêm biên: |raw − offset| < 0,25 mm. Lý do: prepare đo trên điểm route của chính nó. Ở O08-S2, waypoint cho 3,24951 còn
  prepare cho 3,24936. Nên giá trị waypoint sát biên làm tròn không dự báo được prepare.
- Kết quả: `SEP_OK` / `SEP_MARGINAL` / `SEP_MISMATCH` / `SEP_BLOCKED` (đường không thẳng trục). Chỉ `SEP_OK` được đi tiếp.
- Kiểm trên dữ liệu đã biết:
  - O08-S2 cho `SEP_MARGINAL`, khớp lỗi thật;
  - O05-S1, O06, O07-S2 và I01-S1 cho `SEP_OK`, khớp với việc chúng compile được.

## 2. Phạm vi

- **I05, I06, I07:** successor B3 theo io-i-v1.2 §3, dưới io-v1.6 + addendum H + J.
- **I08:** successor B3 theo io-i-v1.2 §3. Site cũ hỏng ở `RUNIN_NOT_STRAIGHT`.
- **O08:** successor B3. O08-S2 ghi FAILED dưới io-v1.5, và lỗi thuộc về site: road 1432 lệch trục, khoảng cách làn sát biên làm
  tròn. io-v1.5 (probe dài) giữ cho slot O08.
- **O04:** successor B3. O04-S2 chưa tốn A/B (prepare io-v1.4 `EGO_NOT_AT_DECISION_IN_PROBE1`). Cổng mới cho O04-S2 là
  `SEP_MARGINAL` (3,24951), tức nó gần như chắc sẽ hỏng ở builder như O08-S2. io-v1.5 (probe dài) áp cho slot O04, mở rộng §3 của
  io-v1.5.
- Mọi slot giữ một A/B (P5).
- Thay thế theo vòng giống addendum G, tối đa 5 lap mỗi slot. Mọi site được đề xuất đều tính vào ngân sách.

## 3. Kết quả các lap (đều offline)

| Slot | Lap → site (town/road) | Kết quả |
|---|---|---|
| I07 | 1: Town12 R685 | gate G OK, sep OK → **I07-S2** |
| I08 | 1: Town12 R260 | OK → **I08-S2** |
| I05, I06 | 1: Town13 R504; 2: Town13 R906 | lap 1: `IO_ROAD_NOT_AXIS_ALIGNED`; lap 2 OK → **I05-S2, I06-S2** |
| O08 | 1: R345; 2: R1330; 3: R1330; 4: Town13 R302 | 1–3: `RUNIN_NOT_STRAIGHT` / không thẳng trục / sát biên; lap 4 OK → **O08-S3** |
| O04 | 2: R345; 3: R1330; 4: R936; 5: Town13 R930 | 2–4: `RUNIN_NOT_STRAIGHT` / sát biên; lap 5 OK → **O04-S3** |

- Đã đề xuất 14 site, nên ngân sách B3 lên **58/150**.
- File cuối: `outputs/m56_fill_v4_replace9_c4_20261115.json`, gộp các entry được chấp nhận bằng `asel2-replace9-merge.py`.
- Revision kiểm: `m56_c0_partial_io_asel2io16r9c4_20261115T131809Z`, không có cờ builder. Mỗi cặp (loại, town) ≤ 3.

## 4. Chạy

- Sau `V15Q_END`, chạy `run-asel2-r9-queue.sh` với product m56-v15:
  - I05-S2, I06-S2 (Town13), I07-S2, I08-S2 (Town12) qua `run-asel2-io-i12j.sh`;
  - O04-S3, O08-S3 (Town13) qua `run-asel2-io-v16.sh`.
- Mỗi cảnh một A/B (P5). Hỏng thì FAILED, không chỉnh thêm.
- Báo kết quả dưới v15 và v12.
