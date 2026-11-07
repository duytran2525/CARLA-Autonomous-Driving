# M56 mục d (F04) và e (năm cảnh có NPC rẽ): quyết định 07/11/2026

**Thẩm quyền:**
- Duy (tự xưng) duyệt "3.có" cho d và e, rồi nói "bạn toàn quyền quyết định không cần tôi duyệt".
- Các quyết định dưới đây là của **Claude dưới ủy quyền toàn quyền của Duy**, kèm nhãn not independent.

## e. C03, L05, L06, M03, M05: giữ phương án (i), tức là chặn

**Số liệu** (route NPC native của lần chuẩn bị gần nhất, công thức `route_kappa` của kit; ngân sách 2,25 = 0,9 × 2,5 m/s²):

| Cảnh | vN catalog | κ max (1/m), bán kính | vN tối đa để không cần pha TURN | Giá trị trong chuỗi vN(k) = 3·(5/4)^(k−1) |
|---|---|---|---|---|
| C03 | 4,688 (k = 3) | 0,2154 (4,6 m) | 3,232 | 3,000 (k = 1) |
| L05 | 7,324 (k = 5) | 0,1671 (6,0 m) | 3,670 | 3,000 (k = 1) |
| L06 | 9,155 (k = 6) | 0,4611 (2,2 m) | 2,209 | 1,920 (k = −1) |
| M03 | 4,688 (k = 3) | 0,1610 (6,2 m) | 3,739 | 3,000 (k = 1) |
| M05 | 7,324 (k = 5) | 0,1125 (8,9 m) | 4,472 | 3,750 (k = 2) |

**(iii), hạ vN:** C03, L05 và M03 sẽ cùng rơi về k = 1, còn M05 về k = 2. Các k đó đã thuộc về cảnh khác cùng loại, trong khi catalog
đóng băng dùng mỗi k một lần cho mỗi loại (chuỗi FILL20 / spec §6.1). Trùng vN sẽ phá quy tắc khác biệt giữa các cảnh (spec §6.4:
≥ 2 tham số lệch ≥ 20%), mà quy tắc này là điều kiện của release và của 155 phép so.

**(ii), NPC giảm tốc trong vùng xung đột:** đổi tốc độ vN đã đóng băng đúng ở chỗ phép đo diễn ra, nên làm đổi bản chất tương tác.
Hướng này còn cần probe chuẩn bị mô hình được event của C/L/M.

**Quyết định:** giữ (i). Năm cảnh vẫn `BLOCKED_FIXTURE` (`NPC_TURN_BEFORE_EXIT` / `NPC_TURN_SPEED`). Release ghi số lượng thật
kèm lý do này.

## d. F04: năng lực bao cửa xe

- Spec §5.4 đòi một proof bao cửa xe đã hiệu chuẩn.
- CARLA 0.9.16 có `Vehicle.open_door()`/`close_door()`, nhưng không có API trả về hình học cửa. `bounding_box` của actor không đổi
  khi cửa mở.
- Một kích thước cửa ước tay thì không phải là proof hiệu chuẩn.
- **Quyết định:** F04 `BLOCKED_CAPABILITY` (`DOOR_ENVELOPE_UNMEASURABLE`). Mở lại được nếu có nguồn đo hình học cửa, ví dụ mesh của
  blueprint hoặc đo bằng cảm biến trong một probe, kèm addendum spec.
