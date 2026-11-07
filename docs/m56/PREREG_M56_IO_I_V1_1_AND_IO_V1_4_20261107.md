# M56 io-i-v1.1 (cảnh I) và io-v1.4 (O04, O05): LUẬT ĐẶT SAU KHI THẤY SỐ, 07/11/2026

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:**
- [chat] 07/11/2026, Duy (tự xưng) duyệt hướng này: "1.có, 2.có, 3.có, 4.không cần ts.hằng một mình tôi là được rồi". Sau đó:
  "tôi đã bảo là bạn toàn quyền quyết định không cần tôi duyệt".
- Chi tiết bên dưới do **Claude quyết dưới ủy quyền đó**.
- Sổ: `2ed1924`.

**Đặt sau khi thấy số:**
- I03 (io-i-v1): B `SOURCE_CLEAR_WAIT_EXCEEDED`; A `MERGE_AHEAD_WITNESS_UNKNOWN`.
- O04 `DOMAIN_CROSSING_UNBRACKETED`; O05 `SPAWN_ERROR`.
- **Ngưỡng của spec và consumer không đổi:** chờ ≤ 4 s, nhân chứng ≥ 0,2 m, hộp domain phải có cắt vào và ra. Kết quả của io-i-v1
  và io-v1.3 vẫn giữ và vẫn báo.
- P5: đây là version mới, nên mỗi cảnh được một A/B (I03 cũng vậy, vì quota P5 của I03 thuộc io-i-v1).

## io-i-v1.1

| # | Mục | io-i-v1 (cũ) | io-i-v1.1 |
|---|---|---|---|
| a | Mốc thời gian của TRIGGER | NPC xâm nhập ranh giới khi mũi EGO tới front_t0. Ở I03, đổi làn của EGO bắt đầu 3,80 s sau TRIGGER; onset thật rơi sau 4 s | NPC xâm nhập khi mũi EGO tới **front_t0 + 4·vE − 3,3·v_plateau**. v_plateau là plateau EGO đo ở probe 2. Đổi làn (đã đóng băng, 4·vE sau front_t0) vì vậy bắt đầu khoảng **3,3 s** sau TRIGGER. Lý do chọn 3,3 s: ở I03, làn nguồn được xác nhận trống 2,55 s sau TRIGGER, còn spec cho tối đa 4 s; 3,3 s nằm khoảng giữa. Gap và thời điểm cắt vào (3.d, 3.e) đo tại mốc mới này. front_t0, X, section và domain không đổi |
| b | Đuôi route EGO | X + gap + 2 thân xe + 20 m. Ở I03, NPC đã chạy khoảng 38 m phía trước nên vượt khỏi route EGO; consumer mất `min_front_gap` 0,35 s trước X_END | X + gap + 2 thân xe + 20 m **+ 10·vN** (NPC chạy 10 s khi EGO A đang dừng). Destination không đổi |

## io-v1.4 (O fill)

| # | Mục | Luật |
|---|---|---|
| c | O04: NPC bắt đầu bên trong hộp domain | Sau probe 1, nếu đuôi NPC lúc xuất phát nằm sau decision − 5 m, run-in của EGO được kéo dài thêm (vị trí NPC − (decision − 5))·vE/vN, rồi probe 1 chạy lại **một lần**. Run-in vẫn phải thẳng (≤ 1°, io-v1.3) |
| d | O05: spawn va chạm | Nếu probe 1 không có frame nào và điểm đầu run-in không nằm trên road site, run-in bị cắt để EGO xuất phát ở road-s 0,5 của road site, rồi chạy lại **một lần**. EGO vẫn phải sẵn sàng trước decision |

## Áp dụng

- **I:** I03, I07, I04, I05. Cận lateral theo điểm.
- **O:** O04, O05.
- Một A/B cho mỗi cảnh. Pair theo v9 và v8.
- Nếu lại hỏng vì cùng nguyên nhân thì **không** chỉnh thêm trong phiên này.
