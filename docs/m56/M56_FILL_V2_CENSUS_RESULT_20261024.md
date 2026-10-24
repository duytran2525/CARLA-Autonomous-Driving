# M56: kết quả census fill v2 (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, người dùng phiên này (tự xác nhận là Duy) chọn "Duyệt 409911e". Census chạy đúng byte
của 409911e (đăng ký trước cùng code đã kiểm bằng `git diff 409911e` trước khi chạy).

**Output:** `outputs/m56_fill_v2_20261024T152517Z.json`, sha256 `46bc88b78da36b83bf29a94663eeb359c1657a741147c5c2c75a60691a8c1e74`.

**Nhãn:** người chọn là `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`. Independent review waived by Duy 2026-10-24.

## Kích thước pool theo bốn cách (đăng ký trước §6)

| Cách | R1 | R2 (M) | R3 (F03) |
|---|---|---|---|
| (a) đúng code fill20 | 166 | 0 | 8 |
| (b) + sửa lỗi F2-1, F2-4 | 166 | 1 | 4 |
| (c) + F2-2 rẽ phải ≤ 100° | 166 | 38 | 4 |
| (d) + F2-3 nối laneSection (quy tắc v2) | 166 | 38 | 4 |

- Ở (d), có 18 corridor nối được 2 đoạn. Corridor dài nhất là 184 m.
- R1 của fill20 lúc 22/10 là 174. Con số 166 ở đây nhỏ hơn vì danh sách loại trừ đã đổi sang site của 31 cảnh hiện có.

## Gán

| Chỗ | Kết quả | Site | Quy tắc cho phép |
|---|---|---|---|
| M02 | PROPOSED | Town04 J1368 | F2-2, rẽ phải 82,2° |
| M03 | PROPOSED | Town05 J1126 | F2-2, rẽ phải 90,4° |
| M04 | PROPOSED | Town04 J1103 | F2-2, rẽ phải 87,9° |
| M05 | PROPOSED | Town06 J838 | F2-2, rẽ phải 89,3° |
| M06 | PROPOSED | Town05 J2240 | F2-2, rẽ phải 90,8° |
| M07 | trống | — | không ứng viên nào đủ độ dài trong giới hạn town |
| M08 | PROPOSED | Town07 J123 | F2-2, rẽ phải 89,8° |
| F02 | PROPOSED | Town06 road 48 | R1 |
| F03 | PROPOSED | Town04 road 40 | R3, chiều lên dốc (F2-4) |
| I06, O06, I08, O08 | trống | — | cần corridor 215–322 m; dài nhất là 184 m |
| F05, F06 | trống | — | không còn road tự do đủ 120 m trong giới hạn town |

**Theo quy tắc cũ (fill20):** cả 6 cảnh M mới đều không có. Chúng chỉ tồn tại nhờ F2-2, một bước nới quy tắc đặt sau khi
thấy pool R2 = 0 và được Duy duyệt.

## Hệ quả cho §11

| Hạng mục | Kết quả |
|---|---|
| Catalog | 39/46 cảnh, nên **release §11 vẫn chưa đạt** (cần đúng 46) |
| Chỗ còn trống | I06, I08, O06, O08, M07, F05, F06 |
| Junction | 23 (16 C/L, M01, cộng 6 M mới) |

Cổng ≥ 23 junction đủ điều kiện chỉ đóng khi **cả 23** junction đều có cảnh giao hàng được admit. M01, C07 và C08 hiện còn
bị chặn.

Theo đăng ký trước §5.6, chỗ trống được để trống và không nới thêm. Muốn lấp tiếp thì phải có một quyết định mới, công khai.
