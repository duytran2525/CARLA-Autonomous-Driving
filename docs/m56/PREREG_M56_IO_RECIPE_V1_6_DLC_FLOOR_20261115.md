# M56 I/O recipe io-v1.6: sàn độ dài đổi làn (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "tôi duyệt recipe mới bạn hãy làm đi" (batch log 0319e85).

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6), viết sau khi thấy O05-S1, O07-S1 FAILED và O06 BLOCKED_WITNESS. Recipe
đổi Dlc = 3·vE của spec 7.4 cho các cảnh vE thấp, nên đây là **lệch khỏi spec 7.4**, và phải ghi như vậy ở mọi nơi trích kết quả.

## 1. Bằng chứng (episode A đã niêm, chỉ đọc JSON)

| Cảnh | vE | Dlc = 3·vE | offset | max \|steer\| | lần arc lùi | kết quả |
|---|---|---|---|---|---|---|
| O01 | 6,0 | 18,00 | 3,5 | 0,12 | 1 | PASS |
| O02 | 7,5 | 22,50 | 3,5 | 0,12 | 1 | PASS |
| O03 | 9,4 | 28,12 | 3,5 | 0,12 | 1 | PASS |
| O05-S1 | 4,8 | 14,40 | 3,25 | **0,80** | 40 | FAILED |
| O07-S1 | 3,8 | 11,52 | 3,25 | **0,80** | 47 | FAILED |
| O06 | 3,1 | 9,22 | 3,5 | **0,80** | 52 | BLOCKED_WITNESS |

- O05-S1 A, từ 16 s tới 22 s: steer lên full lock 0,8. Arc tụt từ 74,0 về 68,9 m. EGO lệch tối đa 7,9 m so với tâm làn đầu, tức
  xe xoay vòng, rồi mới ổn định ở làn đích (3,0–3,2 m).
- Các lý do `RETURN_STARTED_BEFORE_FIXED_MARKER`, `GROUND/CONTACT_PROOF_INVALID`, `CONTINUOUS_FIT_UNPROVEN`, và ở O06
  `METRIC_CONTEXT_INVALID` / `ACTION_REGION_WITNESS_UNKNOWN`, đều nhất quán với việc xe xoay vòng và ra ngoài vùng drivable. Đây là
  **nhận định của Claude**: chưa chạy lại consumer để chứng minh từng lý do.
- Ranh giới: Dlc ≥ 18 m đều ổn, Dlc ≤ 14,4 m đều xoay. Cả 6 cảnh dùng controller stock và chương trình đóng băng giống nhau.

## 2. Luật io-v1.6

1. Ở compile của cảnh O (đoạn đổi làn outbound của EGO A), và của cảnh I (đoạn đổi làn của EGO B, xem io-i-v1.2 mục 2.5):
   **Dlc_eff = max(3·vE, 18 m)**. 18 m là Dlc nhỏ nhất đã PASS (O01). Mọi phần khác của profile giữ nguyên.
2. Hình học cửa sổ đi theo Dlc_eff đúng công thức spec: `X = decision + return_start + Dlc_eff + 3,75` (O); I là
   `X = front_t0 + 4·vE + Dlc_eff + 3,75`. Mốc `TARGET_LANE_CONFIRMED` = đầu đoạn + Dlc_eff.
3. Giá trị gốc 3·vE và Dlc_eff đều ghi vào fixture và prepare.json (`dlc_spec_m`, `dlc_eff_m`).
4. **Cổng dự báo trước A/B:** probe chuẩn bị bằng đúng chương trình EGO A (O) hoặc EGO B (I) của fixture phải có
   **max |steer| ≤ 0,4** và **không có lần arc lùi > 0,05 m** trong đoạn đổi làn. Không đạt → `BLOCKED_FIXTURE LANE_CHANGE_UNSTABLE`.
   Cổng này cần một probe dùng chương trình B/A thật. Với I, đó là probe 3 của io-i-v1.2. Với O, đó là probe 3 mới, cũng là probe
   chuẩn bị và không tính P5.

## 3. Phạm vi, P5, luật dừng

- O05-S1, O07-S1, O06: **chạy lại chính cảnh** dưới io-v1.6 (P5: một A/B cho version mới). Nguyên nhân là độ dài đổi làn so với vE,
  không phải site. Successor B3 sẽ mang cùng vE theo ladder và hỏng giống hệt. Đây là lựa chọn post-hoc và được ghi rõ.
- O01–O03, O04-S2, O08-S2: vE ≥ 6 nên Dlc_eff = 3·vE, luật không đổi gì với chúng.
- Một revision. Hỏng dưới io-v1.6 thì ghi FAILED, không chỉnh 18 m / 0,4 / ngưỡng.
- Báo O05/O06/O07 dưới io-v1.4 (kết quả cũ) và io-v1.6.

## 4. Cách làm

Code trong file mới, bọc compile/prepare I/O. Chạy sau `REPL7_END`, khi không có HOLD. Trước native: kiểm offline rằng
compile mới cho ra Dlc_eff/X đúng công thức trên candidate của O05/O06/O07, và O01–O03 cho ra fixture giống hệt byte cũ (trừ
trường ghi chú).
