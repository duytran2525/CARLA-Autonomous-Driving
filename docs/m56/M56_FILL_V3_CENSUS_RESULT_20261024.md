# M56: kết quả census fill v3 (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, Duy: "duyệt bản đăng ký trước fill v3 tại commit 4a26a66; chạy census đúng byte đó và
ghi nguyên kết quả".

**Kiểm byte:** trước khi chạy, `git diff 4a26a66` không có khác biệt ở các file `PREREG_M56_FILL_V3_20261024.md`,
`fill-v3-generate.py`, `fill-v2-generate.py` và `fill20-generate.py`.

**Output:** `outputs/m56_fill_v3_20261024T153441Z.json`, sha256 `cf21b042db87557fc96c31eacab6af441c75ed8b6b171580133724e1091dbde5`.

**Nhãn:** người chọn là `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`. Independent review waived by Duy 2026-10-24. Mọi quy
tắc F3-* đều đặt sau khi thấy số (đăng ký trước §0).

## Pool

| Mục | Giá trị |
|---|---|
| R1 theo quy tắc v2, với danh sách loại trừ v3 | 149 |
| R1 theo quy tắc v3 (F3-1, sau khi bỏ chuỗi là đuôi của chuỗi khác) | 87 |
| … trong đó có đi qua junction | 32 |
| Corridor dài nhất (v3) | 353 m (Town05) |
| Đoạn thẳng-theo-trục dài nhất (F3-0) | 113 m |
| R2 còn lại | 32 |

Con số 149 nhỏ hơn 166 của fill v2 vì vùng cấm 30 m đã mở rộng quanh 6 junction M mới, và hai road F02/F03 đã bị dùng.

## Gán

| Chỗ | Kết quả | Site | Quy tắc | Tham số |
|---|---|---|---|---|
| I06 | PROPOSED | Town04, road 47 → J764 → road 48; 227 m, đoạn thẳng 113 m | F3-1; **k = −2 nhờ F3-2** (k = 5 cần 245 m) | vE 3,072, vN 2,072, gap 2,73 |
| O06 | PROPOSED | cùng site với I06 | F3-1; k = −2 nhờ F3-2 | vE 3,072, vN 2,5, G 6,83, returnstart 87,7 |
| I08, O08 | trống | — | k = 6, 7, 8 cần 322 / 431 / 590 m và đoạn thẳng 130 / 161 / 199 m; k = −3, −4 cho vE ≤ 3 | — |
| M07 | PROPOSED | Town05 J2086, rẽ phải 90,0° | F2-2; **k = −2 nhờ F3-2** (k = 6, 7 không có ứng viên) | vN 1,536, GL 1,82 |
| F05, F06 | trống | — | xem bên dưới | — |

**Vì sao F05/F06 trống:**
- Corridor ≥ 120 m chỉ có ở ba nơi: Town06 (12, nhưng đã đủ trần F = 3), Town04 (5, đều dùng road 47/48 của I06/O06) và
  Town05 (2).
- Cả hai corridor Town05 (353 m) đều đi qua J2086, junction vừa được gán cho M07 ngay trước bước F.
- Theo §3 của đăng ký trước, junction đã gán bị loại cho các lần gán sau. Thứ tự gán (I/O → M → F) là thứ tự đã đăng ký.

**Theo quy tắc v2:** cả 7 chỗ đều trống. 3 cảnh mới chỉ có nhờ F3-1 và F3-2.

## Hệ quả

| Hạng mục | Kết quả |
|---|---|
| Catalog | **42/46** cảnh. Còn trống I08, O08, F05, F06, nên **release §11 vẫn chưa đạt**. |
| Junction | 24 (16 C/L cộng M01–M08; M đã đủ 8). Cổng cần ≥ 23 junction đủ điều kiện, tức là được hỏng tối đa 1. |
| Junction bị corridor đi qua | J764 (Town04): ghi lại, không tính là junction của catalog |

**Lưu ý cho khâu chuẩn bị:**
- I06/O06 chạy ở 3,072 m/s. Probe cho thấy EGO ổn định ở 3,84 m/s, còn 3,07 m/s chưa đo.
- Đoạn thẳng 113 m chỉ dư 16 m so với mức cần 96,9 m của O06.

Theo đăng ký trước §3.4, chỗ trống được để trống và không nới thêm.
