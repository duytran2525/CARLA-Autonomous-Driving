# M56 addendum T: F05 (khởi hành chậm), những gì product và tooling còn thiếu, 18/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Viết **trước** mọi số native của F05 (F05 chưa từng prepare).

**Thẩm quyền:** người dùng phiên này [chat] 17/11 "làm F05/F06, F03/F04 và nhóm M", [chat] 18/11 "làm hết cho tôi".
Claude quyết dưới ủy quyền của Duy.

## 1. Luật product đổi (m56-v18, luật sau số đối với dữ liệu F01/F02, trước số F05)

- `_creep_guard` (B bò 0,5 m/s) đòi readback steer **đúng bằng 0**. Đo trên 6 episode F01/F02 đã niêm (EGO BasicAgent stock trên
  route R1 thẳng trục): 0/401 khung đang chạy có steer đúng 0, |steer| lớn nhất 0,0011–0,0072. Luật cũ làm B của F05 không bao giờ
  bò được (`CREEP_CONTROL_UNPROVEN`), không phải vì xe lệch.
- Luật mới: |steer| ≤ 1/50 (≈ 2,8 × giá trị lớn nhất đã đo). Lệch ngang vẫn bị chặn bởi luật căn trục 0,15 m của v14 phần 1.
  Luật cũ giữ là `_creep_steer_old_rule`; kết quả F05 báo dưới cả hai. Test `test_v18_creep_steer_tolerance`.
- Luật lùi (F03 B, F06) **không** đổi: lệnh lùi do tooling tự gửi với steer 0, readback 0 là đạt được.

## 2. Tooling còn phải viết (chưa có gì cho F05)

1. **Prepare F05** (`native-f-prepare.py` thêm F05): NPC đứng trong làn cách EGO d0 = 4 m, EGO dừng sau; readiness theo plateau.
2. **Probe hiệu chỉnh `CREEP_STOP_BOUND`** (`bounded-forward-creep-stop-v1`) trên chính site Town12 R164: EGO bò 0,5 m/s rồi
   phanh 0,3, lặp vài lần, lấy biên bất lợi của quãng dừng và tốc độ max; proof bám hash response/route/body/recipe/stock config.
   Điều kiện product: boundary + bound + uncertainty ≤ 1 m.
3. **Kit:** mỗi khung ghi `creep_history_ref` (trajectory đã niêm tới khung đó, ≤ 1532 khung), `creep_fixture_ref`, và proof
   `QUEUE_PATH` (`bounded-queue-exit-corridor-v1`, khoảng hở trước ≥ 0,2 m + uncertainty, raw refs đúng khung).
4. Realized F05 commit trước A/B; một A/B (P5); pair dưới v18 và v13 (luật steer cũ đi kèm v13).
- Luật dừng: một revision cho mỗi bước; hỏng thì ghi đúng như đo.
