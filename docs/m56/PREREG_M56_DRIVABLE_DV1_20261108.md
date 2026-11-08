# M56 dv1: vùng drivable gồm lề, mặt giao lộ và phủ toàn route (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này (đã tự xưng Duy ngày 07/11/2026, trao toàn quyền) yêu cầu trong chat ngày 08/11/2026: "sửa
vùng drivable gồm cả lề và giao lộ trong lúc chờ full suite đi". Claude quyết chi tiết dưới ủy quyền đó.

**ĐÂY LÀ LUẬT ĐẶT SAU KHI THẤY SỐ.** C02, M07 (BLOCKED_WITNESS: CONTACT, FIT, ngày 26/10) và C08 (BLOCKED_WITNESS: CONTACT, FIT,
ngày 08/11) đã có kết quả dưới vùng drivable v6. Kết quả theo luật cũ được giữ nguyên, và mọi báo cáo phải ghi theo cả hai luật.
Ngưỡng không đổi: proof CONTACT vẫn đòi mép đường > 0, FIT vẫn đòi thân xe nằm trong union đã đóng băng của fixture.

## 1. Chẩn đoán (chỉ đọc, không có A/B)

Độ sâu lớn nhất mà một đỉnh footprint của xe nằm ngoài union v6 (`edge_depth.py` trên các episode đã seal):

| Cảnh | Actor | Số frame có đỉnh ra ngoài | Sâu nhất | Mặt tại điểm đó (`native-edge-surface-diag.py`) |
|---|---|---|---|---|
| C02 | NPC | 34 | 0,199 m | làn **Shoulder** 32/+2 (0,5 m), nhãn Roads |
| M07 | NPC | 84 | 0,303 m | mặt giao lộ **Roads/RoadLines**, không thuộc làn nào; điểm kề 0,25 m là Sidewalks |
| M06 | NPC | 5 | 0,068 m | mặt giao lộ Roads; điểm kề là Shoulder 2281/−3 |
| C08 | NPC | 74 (A) / 36 (B) | 50,9 m | NPC chạy ra khỏi phạm vi dựng union (bán kính tính từ điểm spawn) ở cuối episode |
| L02 | — | 0 | — | không xe nào ra ngoài; lỗi nằm ở chỗ khác (GROUND) |

Vậy union v6 thiếu ba thứ:
- làn Shoulder: chỉ quad của làn Driving được dựng;
- dải mặt đường mỏng ở giao lộ: raster 0,5 m lại bị co 0,25 m;
- phạm vi: bán kính lấy theo điểm spawn, không theo route.

## 2. Recipe dv1 (`M56_DRIVABLE=dv1`, chỉ trong `native_v2_common.drivable_union` và `native-v2-ab.py`)

1. **Quad làn:** làn `Driving` **và** `Shoulder` (waypoint mỗi 0,5 m, theo bề rộng làn), sau đó đóng khe 0,25 m như v6.
2. **Raster mặt đường:** lưới **0,25 m** (v6: 0,5 m), mỗi ô được tính là mặt đường nếu tia đầu tiên chạm nhãn Roads hoặc
   RoadLines (như v6). Phần mặt đường được co **0,125 m**, bằng nửa ô, để mép vẫn bảo thủ (v6: 0,25 m).
3. **Phạm vi:** bán kính = max(90 m, điểm xa nhất của **mọi điểm route** EGO/NPC tính từ tâm + 20 m). Raster phủ hành lang 12 m
   quanh toàn bộ route, không cắt theo bán kính.

Sidewalks, Parking, Median và mọi nhãn khác vẫn nằm ngoài union. Các proof khác (GROUND, BODY_FIT lúc spawn, run-in) giữ nguyên
code.

## 3. Phạm vi chạy

- Chỉ các cảnh có lý do CONTACT/FIT xuất phát từ union: **C02, M07, C08**.
  - M06 không chạy, vì nó còn `NPC_UNPLANNED_REVERSE` (FAILED), không liên quan tới union.
  - L02 không chạy, vì không có xe nào ra khỏi union.
- Không chuẩn bị lại. Fixture được compile lại từ đúng lần chuẩn bị đã dùng cho A/B cũ (C02: `m56_v2_prepare_Town04_20261026T112631Z`;
  M07: `m56_v2_prepare_Town05_20261026T095528Z`; C08: `m56_v2_prepare_Town06_20261108T012553Z`). Chỉ union (và các box
  `driving_regions` suy ra từ nó) thay đổi.
- **P5:** dv1 là một version mới của fixture, nên mỗi cảnh được **một** A/B. Recipe v6, product `m56-v9` `1db746f`, pair dưới
  consumer v9 và v6.
- Cảnh vẫn hỏng thì ghi lại; không chỉnh thêm, không chạy lại.
- Các cặp đã PASS (C01, C05, L01, L04, …) **không** chạy lại; kết quả của chúng vẫn là kết quả dưới union v6.
