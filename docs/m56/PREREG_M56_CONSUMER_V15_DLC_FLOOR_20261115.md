# M56 consumer v15: sàn Dlc cho đổi làn của EGO ở I/O (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** [chat] 15/11/2026 tối, người chat tự xưng là Duy, chọn "Duy duyệt đổi (v15)" (batch log 8bc6740). Nội dung lời duyệt:
consumer m56-v15 chấp nhận Dlc = max(3·vE, 18 m), có prereg, test và full suite trước khi chạy, và báo kết quả dưới cả hai luật.
Claude không kiểm được danh tính người chat vì máy dùng chung, nên thẩm quyền được ghi theo lời tự xưng.

**Tính chất:** đổi luật consumer **sau khi thấy số** (nguyên tắc 6). Các số đã thấy trước khi viết:
- các episode A io-v1.4 của O05-S1, O06, O07-S1 (đánh lái hết cỡ, xe xoay vòng);
- kết quả native 15/11: O05-S1, O06, O07-S2 dừng ở `EGO:A LATERAL_LENGTH_INVALID` và không có A/B.

Luật cũ được giữ nguyên văn.

## 1. Luật cũ (spec 7.4, consumer ≤ v14)

m56-v13 `response.py`, `_lateral_contract`: mọi đoạn đổi làn của I/O phải có `length_m == 3 * nominal`, cho cả EGO lẫn NPC. Luật cũ
được giữ dưới tên `dlc_old_rule` (report-only).

## 2. Luật mới (v15)

- **EGO** (O: A, cả đoạn đi ra lẫn đoạn return; I: B): `length_m == max(3·vE, 18 m)`, **bằng đúng**, Fraction.
- **NPC** (I): giữ đúng `3·vN`. io-v1.6 không đổi profile của NPC.
- Mọi kiểm khác của `_lateral_contract` giữ nguyên: số đoạn, separation, switch, marker guard và độ cong quintic trong `desired_offset`.
- Đây là chỗ duy nhất trong product dùng 3·nominal làm luật: đã grep `io_dlc`, `Dlc`, `3*` trong `m56/`. Chỗ còn lại là `catalog.py`
  377/670, sinh catalog spec 7.4 v1. Chỗ đó không đổi, vì các cảnh catalog v1 (O01–O03, I03, I04) có vE ≥ 6.

## 3. Dòng version

- v15 tách từ **v13** (834e149), là product mà full suite 11 (CHAIN_PASSED, 15/11) đã kiểm: package `m56` của m56-v1 trùng v13.
- v14 là WIP (F05/F06) và **không** nằm trong v15.
- v13 khác v12 duy nhất ở luật F01 NPC nominal (response.py). Phần đó không chạm I/O.

## 4. Kiểm trước khi dùng

1. Test mới `tests/m56/test_v15_dlc_floor.py`.
2. Kiểm offline `v15-contract-acceptance.py`: vòng contract của `native-io-ab.py` chạy dưới v13 và v15 trên:
   - fixture io16 đã compile của O05-S1, O06, O07-S2: kỳ vọng v13 báo `LATERAL_LENGTH_INVALID` và v15 báo OK cho mọi response;
   - fixture đã niêm của các cảnh PASS O01–O03, I03, I04, cùng fixture I01-S1 và I02-S2: kỳ vọng v13 và v15 cho kết quả giống hệt.

   Kết quả ghi vào batch log.
3. Full suite trên byte cuối của v15. Chỉ chạy sau `I12_END`, không chạy cùng lúc với CARLA.
4. Chỉ sau khi (1)–(3) đạt mới được chạy A/B dưới v15.

## 5. Phạm vi, P5, báo cáo

- Mở được: **O05-S1, O06, O07-S2**. P5 vẫn chưa tiêu, vì lần chạy 15/11 không có A/B. Cổng κ io-v1.6 §2b đã đạt.
  - Mỗi cảnh một A/B dưới io-v1.6 + v15, dùng batch `run-asel2-io-v16.sh` với `M56_CODE` = m56-v15.
  - Pair dưới v15 và v12.
- **Chưa mở: I05–I07 (successors).** Các A io-i-v1.1 của chúng đều có `COLLISION_OBSERVED`. Chưa kiểm được va chạm xảy ra trước hay
  sau lệnh RESUME, nên chẩn đoán G4 (io-i-v1.2 §2.4) chưa được xác nhận. v15 **không** gồm G4.
- **Báo cáo:**
  - O05/O06/O07 dưới luật cũ: "không chạy được A/B, `LATERAL_LENGTH_INVALID`". Dưới v15: kết quả mới.
  - Kết quả ở các version trước (io-v1.4) giữ nguyên.
- Một revision. Hỏng dưới v15 thì ghi FAILED, không chỉnh 18 m.
