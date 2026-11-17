# M56 addendum O (X_END bị bỏ sót trong dải bất định) và addendum P (chạy đà dài hơn cho I01-S1), 17/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 17/11/2026: "sửa lại cảnh I01-S01 rồi prepare lại, I04 bạn tự quyết".
Addendum O do Claude quyết dưới ủy quyền của Duy, sau khi đọc kết quả I02-S2.

## Addendum O: product m56-v17 (nhánh `feat/m56-v17`, tách từ v16 c7c32ba)

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Viết sau khi pair I02-S2 (A/B io-i-v1.3 a + v16 + G5) trả
`BLOCKED_WITNESS` dưới cả m56-v16 lẫn m56-v15. Lý do: A `X_END_MISSING`, B VALID.

1. **Lỗi đo.** `_detect_io.crossing` đòi một cặp frame liên tiếp (a, b) thỏa `extreme(a) + u ≤ 0` và `extreme(b) − u > 0`
   (u = bất định hình học liên frame, ở đây 1 mm). Nếu một mẫu rơi vào (−u, +u], không cặp nào thỏa, nên sự kiện mất hẳn.
   I02-S2 A: đuôi EGO ở −0,26 mm tại frame 2863, rồi +0,36 m tại frame 2864. EGO đi qua X thật (arc 136,3 → 157,7,
   `DESTINATION_CONFIRMED` ở frame 2917). Xác suất xảy ra khoảng 2u / bước ≈ 0,6 % mỗi lần đi qua, đúng kiểu lỗi hiếm.
2. **Luật mới.** Mẫu "chắc chắn trước" (`extreme + u ≤ 0`) gài khóa cho (actor, mặt cắt, id). Crossing bắn ở mẫu "chắc chắn
   sau" đầu tiên trên một chuỗi cặp frame liên tục không đứt. Witness của sự kiện là cả chuỗi frame từ mẫu "chắc chắn trước"
   cuối cùng; khi không có mẫu trong dải, chuỗi chỉ gồm một cặp, giống hệt luật cũ. Khóa bị hủy khi: thiếu proof liên tục,
   `route_valid` sai, ra khỏi corridor, margin không tính được, hoặc mẫu đã chắc chắn sau mà chưa bắn.
3. **Phạm vi:** TRIGGER, RETURN_MARKER, X_END của I/O (một hàm). C/L/M không đổi. Khi actor đi qua mặt cắt một chiều (không lùi
   qua lại), mọi sự kiện luật cũ bắt được thì luật mới bắt ở đúng frame đó, với đúng witness đó. Luật mới chỉ thêm các sự
   kiện luật cũ bỏ sót.
4. **Test.** `test_io_section_touch.py` trước đây khẳng định `uncertain_predecessor` thì không có sự kiện, tức chính hành vi
   lỗi. Nay test đòi sự kiện ở frame 142 với witness {140, 141, 142}. `touch_only` (không bao giờ qua) vẫn không có sự kiện.
5. **I02-S2:** chấm lại offline (pair, không chạy lại A/B; P5 không đổi) dưới m56-v17. Báo cạnh kết quả v16 và v15
   (`BLOCKED_WITNESS`).

## Addendum P: io-i-v1.3 b, prepare I01-S1 lại (`native-io-prepare-i14.py`)

**Tính chất:** viết trước lần prepare dùng nó. Prepare không tiêu P5.

1. **Nguyên nhân I01-S1 `READINESS_NOT_STEADY` (17/11).** Cùng recipe, cùng cờ: ngày 16/11 PREPARED (EGO range 0,073 m/s
   với gain 1/5, 1/10), ngày 17/11 chặn (0,141). Vết tốc độ: sau khi tăng tốc, vòng tốc độ EGO dao động kiểu giới hạn
   (vượt 6 m/s → throttle 0 → giảm 3,5 m/s² → tụt 4,3 m/s). Ngày 16/11 tắt sau 1 chu kỳ (~6 s), ngày 17/11 kéo dài 4 chu kỳ
   (~12 s). Cửa sổ đo cố định là 2 s trước điểm quyết định, chạy đà 64 m (~12–13 s), nên lần này vẫn còn dính dao động.
2. **Sửa.** Cảnh loại I bị `READINESS_NOT_STEADY` ở probe 1 được prepare lại **đúng một lần**, chạy đà ×3/2 (I01-S1:
   64 → 96 m, thêm khoảng 6 s). Ngưỡng 0,10 m/s và cửa sổ 2 s giữ nguyên. Lưới gain và kết quả lần đầu được ghi vào
   `prepare.json` (`io_i13b_first`). Vẫn hỏng thì BLOCKED, không thử tiếp.
3. **Sau prepare:** các cổng như addendum N (L, κ, probe 3 G1/G2/G3/G5), rồi một A/B dưới product **m56-v17**, pair dưới
   v17 và v15.

## I04: Claude quyết dưới ủy quyền của Duy

- Chạy lại **chính I04** (không làm successor B3), cùng cách xử lý như I02-S2. Lý do: PASS cũ của I04 đã bị hạ (15/11,
  addendum L: khoảng cách lúc t0 là 46,4 m thay vì 13,2 m, lỗi tooling kẹp NPC vào site road). io-i-v1.3 a sửa đúng lỗi
  đó (prepare-only 16/11: GAP_OK). Successor cần sinh cảnh mới, nhiều bất định hơn. Kết quả mới là kết quả của I04 dưới
  version mới, báo cạnh PASS cũ đã hạ. Không có chuyện chọn lần may: lần cũ không còn được tính.
- Một A/B dưới io-i-v1.3 a/b + m56-v17 + G5. Hỏng thì FAILED, không chỉnh ngưỡng.
