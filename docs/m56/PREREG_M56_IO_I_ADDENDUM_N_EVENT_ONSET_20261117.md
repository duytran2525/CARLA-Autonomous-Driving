# M56 addendum N: lượt B của cảnh I đổi làn theo sự kiện (17/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 17/11/2026 chọn "Đổi làn theo sự kiện (Recommended)". Câu hỏi đã nêu rõ: đây là
product v16, B giữ làn tới khi có SOURCE_CLEAR_CONFIRMED + LANE_CHANGE_PATH_CLEAR, hạn 4 s giữ nguyên.

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Viết sau các A/B io-i-v1.1 đã niêm (I02-S2 B `LANE_CHANGE_GUARD_MISSING`)
và dự báo addendum H §4. Viết trước mọi bước native dùng nó.

## 1. Vấn đề

Profile ngang của EGO B ở cảnh I bắt đầu ở một arc cố định (I02-S2: 110,06 m, khoảng 3,1 s sau TRIGGER). Chương trình B đã có pha
CHANGE sau `SOURCE_CLEAR_CONFIRMED` (đòi TRIGGER + `LANE_CHANGE_PATH_CLEAR`). Nhưng offset được tính chỉ theo arc. Tới arc đó mà sự
kiện chưa có thì runner chặn `LANE_CHANGE_GUARD_MISSING`. Sự kiện của product đến sau t_clear hình học 0,7–1,05 s (biên 0,5 m, giữ
0,25 s). Dự báo I02-S2: khoảng 3,45 s sau TRIGGER.

## 2. Luật (product m56-v16, nhánh `feat/m56-v16`, tách từ v15 036688b)

1. `response.commanded_offset(arc, reference, response, cause)`. Với **EGO, category I, action B**, nếu chương trình có transition
   `after_event = SOURCE_CLEAR_CONFIRMED`: ở mọi pha **trước** pha đó, offset = offset đầu profile (0). Từ pha đó trở đi: đúng
   `desired_offset(arc)` của profile đóng băng, không dịch. Mọi response khác: `desired_offset` như v15.
2. Runtime (`step_response`) và **kiểm offset của consumer** (`evidence._offset_integrity`, `OFFSET_PROGRAM_MISMATCH`) cùng dùng
   hàm này. **Công bố:** đây là một thay đổi ở consumer. Trong câu hỏi, Claude đã nói "luật chấm giữ nguyên". Các cổng hành vi giữ
   nguyên (`CHANGED_BEFORE_SOURCE_CLEAR`, `SOURCE_CLEAR_WAIT_EXCEEDED` 4 s, `LANE_CHANGE_PATH_STALE`, contract ngang, Dlc), nhưng
   phép kiểm offset lệnh phải theo luật mới thì mới khớp.
3. **Bước tham chiếu (công bố):** khi sự kiện đến sau arc bắt đầu cố định, offset tham chiếu nhảy từ 0 vào giữa profile.
   q(u) = 10u³ − 15u⁴ + 6u⁵, u = trễ·vE/Dlc. I02-S2 (vE 7,5, Dlc 22,5, offset 3,25 m): trễ 0,35 s → khoảng 4 cm; trễ 0,9 s (sát
   hạn 4 s) → khoảng 0,5 m. Không làm mượt (mượt cần lưu arc lúc vào pha, tức đổi schema).
4. Program không có transition SOURCE_CLEAR (fixture tổng hợp cũ, C/L/M/O/F): không đổi gì.

## 3. Cổng G5 (tooling `native-io-ab-i16.py`, bọc `native-io-ab-i12.py`)

- Probe 3 (action A, cùng fixture/server, store riêng, addendum H) không dừng ở t_clear hình học nữa. Nó chạy tới khi thấy
  `SOURCE_CLEAR_CONFIRMED` hoặc tới TRIGGER + 4 s.
- **G5:** `SOURCE_CLEAR_CONFIRMED − TRIGGER ≤ 3,5 s`, không đạt thì `BLOCKED_FIXTURE SOURCE_CLEAR_EVENT_LATE`: không A/B, P5 chưa
  tốn. 3,5 s chừa 0,5 s cho onset quan sát trước hạn 4 s của product.
- G1 (ready ≤ 14 s), G2 (đuôi X), G3 (t_clear − TRIGGER ≤ 2,3 s) giữ nguyên.
- Giả định (nhận định): sự kiện nguồn trống phụ thuộc chủ yếu vào NPC; chương trình NPC giống nhau ở A và B. Probe 3 chạy A.

## 4. Phạm vi, P5, luật dừng

- Prepare: `native-io-prepare-i13.py` (io-i-v1.3 a + J + G2), cổng L. Đã chạy prepare-only 16/11: I01-S1, I02-S2, I04 đều GAP_OK.
- **A/B lần này: I01-S1 và I02-S2**, mỗi cảnh một A/B dưới version mới (io-i-v1.3 a + v16 + G5). Lý do chạy lại chính cảnh: io-i-v1.2
  §3 (nguyên nhân ở tooling).
- **I04: chưa A/B.** Ngày 15/11 người dùng chọn "Hạ I04, làm successor". Việc chạy lại chính I04 hay làm successor B3 là quyết định
  của người dùng.
- Pair dưới m56-v16 (luật mới) và m56-v15 (luật cũ). Dưới v15, B sẽ chặn `OFFSET_PROGRAM_MISMATCH` nếu có giữ làn; đó là kết quả của
  luật cũ và được báo song song.
- Một revision. Hỏng thì FAILED, không chỉnh 3,5 s / 4 s.
- Full suite chạy một lần ở cuối (lệnh người dùng 16/11). Trước A/B: test tập trung của các file v16 sửa.
