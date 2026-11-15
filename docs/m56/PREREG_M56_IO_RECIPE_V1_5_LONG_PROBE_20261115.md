# M56 I/O recipe io-v1.5: probe chuẩn bị dài cho O/I (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "tôi duyệt recipe mới bạn hãy làm đi". Lời này trả lời mục B của
`M56_FIX_MATRIX_20261115.md`. Ghi tại batch log 0319e85.

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6), đặt sau khi thấy prepare O08-S2 BLOCKED. Recipe này áp **nguyên văn**
luật cl-v1 b (đã dùng cho C/L/M, `native-v2-prepare.py` dòng 267–272) sang prepare I/O. Không đổi ngưỡng, consumer, hay runner
A/B.

## 1. Bằng chứng (frame đã niêm, probe 1 O08-S2, `m56_v2_prepare_Town13_20261112T143059Z`)

- vE = 9375/512 ≈ 18,31 m/s, nên run-in = 196 m. Ga quyết định nằm ở 196,07 m.
- EGO đạt plateau 18,15 m/s ở khoảng frame 240 (12 s). Tới frame 320 (16 s, hết `READY_LIMIT_S` 15 s + 1 s settle), EGO mới ở arc
  **192,3 m**, còn thiếu **3,8 m** (≈ 0,2 s). Runner dừng `READINESS_NOT_REACHED`, prepare ghi `EGO_NOT_AT_DECISION_IN_PROBE1`.
- Hai đường retry của io-v1.4 không áp dụng: (d) là spawn hỏng ngoài road site, (c) là NPC xuất phát sau ga quyết định.

## 2. Luật io-v1.5 (chỉ ở prepare)

1. Probe 1 của một cảnh O hoặc I dừng `READINESS_NOT_REACHED` mà EGO **chưa bao giờ** tới ga t0 (`dec_t`). Khi đó mọi probe chuẩn
   bị **còn lại** của cảnh (probe 1 chạy lại, grid PID, probe 2) chạy với `READY_LIMIT_S = LONG_PROBE_S = 60` (giống cl-v1 b).
   Ghi `io_v15_probe_ready_limit_s = 60` vào prepare.json.
2. Runner của A/B giữ nguyên **15 s** (product không đổi).
3. **Cổng dự báo trước A/B** (mới, chốt trước khi chạy): gọi frame ready của probe 2 là `fr`, frame settle đầu là `settled`. Yêu
   cầu `fr.simtime − settled.simtime ≤ 14,0 s` (biên 1 s so với 15 s). Không đạt → `BLOCKED_FIXTURE READY_AFTER_AB_LIMIT`,
   không compile, không A/B.
4. Mọi cổng hiện có của prepare, compile, self-check và admission giữ nguyên.

## 3. Phạm vi và luật dừng

- **O08-S2**: chưa tốn A/B, nên prepare lại **chính cảnh này** dưới io-v1.5. P5 không đổi: vẫn một A/B nếu qua mọi cổng.
- Cảnh I chỉ dùng io-v1.5 khi recipe I mới (io-i-v1.2, prereg riêng) cũng áp dụng.
- Một revision. Nếu O08-S2 vẫn BLOCKED, hoặc A/B không cho cặp PASS, thì O08 ghi FAILED dưới io-v1.5. Không chỉnh thêm limit,
  biên hay run-in.
- Báo O08 dưới mọi luật: io-v1.4 là BLOCKED_FIXTURE `EGO_NOT_AT_DECISION_IN_PROBE1`; io-v1.5 là kết quả mới.

## 4. Cách làm (không sửa file đang đóng băng)

- `native-io-prepare-v15.py` (file mới) nạp `native-io-prepare.py` dưới dạng module, bọc `P.probe` để áp luật 2.1, và thêm cổng
  2.3 sau probe 2. Byte của `native-io-prepare.py` không đổi, nên gate G (addendum G) vẫn hợp lệ.
- Chỉ chạy native sau `REPL7_END`, khi không còn HOLD.
