# M56 addendum J: sàn Dlc cho đổi làn của NPC ở cảnh I (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026 tối chọn "Sàn Dlc cho NPC (Recommended)". Câu hỏi ghi rõ đây là đổi chương
trình NPC đóng băng và đổi luật consumer, và cần Duy. Câu trả lời không tự xưng lại danh tính. Trong cùng phiên, người chat đã tự xưng
là Duy khi duyệt v15 (batch log 8bc6740). Claude không kiểm được danh tính.

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Nó được viết sau addendum I (bảng NPC: sạch khi κ ≤ 0,049, bão hòa khi
κ ≥ 0,155) và trước mọi bước native dùng nó. Luật cũ (spec 7.4 / io-i-v1, NPC = 3·vN) giữ nguyên văn.

## 1. Luật

1. **Prepare** (`native-io-prepare-i12j.py`, nạp `native-io-prepare-i12.py`): đoạn cut-in của NPC ở cảnh I dài
   **Dlc_N = max(3·vN, 18 m)**. Mọi phần khác của `npc_cut` giữ nguyên: điểm bắt đầu = trạm NPC lúc t0 − u·Dlc_N, và các cổng
   `NPC_CUT_OUTSIDE_ROUTE`, `NPC_CUT_BEFORE_READY`.
2. **Consumer v15:** `_io_dlc` áp max(3·v, 18 m) **bằng đúng** cho cả EGO lẫn NPC. Phần này mở rộng prereg v15 §2, vốn ghi NPC giữ
   3·vN. Luật cũ vẫn là `dlc_old_rule`.
3. Với offset ≤ 3,5 m, sàn 18 m cho κ_max ≤ 0,0624, đúng giá trị O01 (PASS). Không thêm cổng κ mới cho NPC.

## 2. Phạm vi

- **I01-S1:** vN = 5, nên Dlc_N đổi từ 15 m lên 18 m (κ 0,0834 → 0,0579). Chạy lại chính cảnh theo io-i-v1.2 §3 + addendum H + J.
  P5 vẫn một A/B. Trước đó cảnh được giữ, chưa tốn A/B.
- I02-S2, I03, I04: vN ≥ 6, nên luật không đổi gì.
- I05–I07 (successors): mở về nguyên tắc. Mỗi cảnh vẫn cần successor B3 qua gate G và builder io16. Việc này chưa làm.
- Một revision. Hỏng thì FAILED, không chỉnh 18 m.

## 3. Thứ tự

1. Consumer v15 (EGO + NPC floor) được cherry-pick vào `feat/m56-v1`, rồi chạy full suite trên byte cuối. Suite chỉ chạy khi không có
   CARLA.
2. Sau `CHAIN_PASSED`:
   - I01-S1 qua `run-asel2-io-i12j.sh` với `M56_CODE` = m56-v15;
   - O05-S1, O06, O07-S2 qua `run-asel2-io-v16.sh` với `M56_CODE` = m56-v15.
3. Pair dưới v15 (luật mới) và v12 (luật cũ). Dưới v12, A/B không chạy được vì `LATERAL_LENGTH_INVALID`, và điều đó được ghi như kết
   quả dưới luật cũ.
