# M56 A-SEL2 addendum G: offline route gate for I/O replacements (15/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "sửa tất cả những cảnh khác rồi chạy offline test đi". Claude quyết dưới
ủy quyền của Duy. Advisor được hỏi trước khi viết.

**Tính chất:** viết **sau khi thấy số** (nguyên tắc 6). Số đã thấy:
- prepare của O04-S1 và I08 đều dừng ở `RUNIN_NOT_STRAIGHT` (46,15 m và 35,59 m), trước khi tốn A/B;
- `pool_skips` của I/O trong mọi output fill v4 đều rỗng, nghĩa là generator không lọc độ thẳng của đoạn chạy đà.

Addendum này **không đổi ngưỡng, recipe hay consumer**. Nó chỉ chạy trước, ở offline, đúng phép kiểm prepare vẫn làm
(`MAX_YAW_DEV` 1°, các độ dài run-in và tail của `_prepare_o`), để site chắc chắn hỏng ở prepare không tốn CARLA.

## 1. Công cụ

- `native-io-runin-offline.py`: trích **nguyên văn theo tên** các hàm `geometry`, `geometry_fill`, `road_length`,
  `lane_rows`, `lane_rows_through` và hằng `MAX_YAW_DEV`, `RUNIN_M`, `EGO_TAIL_M`, `NPC_BACK_M`, `NPC_TAIL_M` từ
  `native-io-prepare.py` (không sửa file đó). Các hàm chạy trên `carla.Map` dựng offline từ OpenDRIVE của town, không cần server.
- Kết quả cho mỗi candidate: `ROUTES_OK` hoặc `ROUTE_BLOCKED` kèm đúng chuỗi lỗi của prepare.

## 2. Kiểm chứng trên dữ liệu đã niêm (15/11, product m56-v12, revision release)

| Cảnh | prepare thật | offline |
|---|---|---|
| O04-S1 | `RUNIN_NOT_STRAIGHT:856/-2:YAW:46.15m` | giống hệt |
| I08 | `RUNIN_NOT_STRAIGHT:345/4:YAW:35.59m` | giống hệt |
| I02-S2 | route OK, npc_tail_cut 5,392 m | OK, 5,39 m |
| O08-S2, I07-S1 (Town13); O05-S1, O06, O07-S1, I01-S1, I05-S1, I06 (Town12) | route OK | OK |

Khớp 11/11. Mỗi town chạy khoảng 7 giây.

## 3. Luật (chốt trước khi chạy replacement O04)

1. Với một slot I/O được thay theo B3: generator fill v4 (replace mode, không đổi) đề xuất một site. Revision builder dựng
   candidate. Sau đó chạy `native-io-runin-offline.py` trên candidate đó.
2. `ROUTE_BLOCKED` → site vào `tried` (ghi lý do), generator chạy lại để lấy first-fit kế tiếp. Tối đa **5 lượt mỗi slot**.
   Hết 5 lượt mà vẫn hỏng thì slot ghi EMPTY.
3. **Ngân sách B3 tính mọi site được đề xuất**, kể cả site bị gate loại. Cách tính này bảo thủ hơn cách cũ.
4. `ROUTES_OK` không có nghĩa là PREPARED: prepare vẫn là cổng chính xác (probe, readiness, NPC cut, …).
5. Phạm vi hôm nay: **O04**. I08: gate áp được, nhưng cảnh I vẫn bị cấm B3 cho tới khi Duy duyệt recipe I mới, nên chưa sinh
   site. O08: hỏng ở probe chứ không ở route (mục 4), nên gate này không giúp.

## 4. Ghi nhận ngoài phạm vi (đề xuất, chưa làm)

O08-S2 `EGO_NOT_AT_DECISION_IN_PROBE1`:
- vE = 9375/512 ≈ 18,3 m/s, nên run-in = ⌈100·vE/9,375⌉ = 196 m.
- Probe 1 dài 320 frame (16 s), không đủ để xuất phát từ đứng yên rồi đi hết 196 m.
- Chú thích của `RUNIN_M` ghi rõ probe 16 s chỉ được tính cho vE 6 / 7,5.
- Sửa thì phải đổi recipe (độ dài probe theo vE). Đó là luật sau số mới, cần Duy quyết.
