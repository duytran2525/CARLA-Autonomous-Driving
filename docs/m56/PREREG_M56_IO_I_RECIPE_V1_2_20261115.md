# M56 recipe I io-i-v1.2 (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "tôi duyệt recipe mới bạn hãy làm đi". Lời này trả lời mục B của
`M56_FIX_MATRIX_20261115.md` (batch log 0319e85).

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Mọi cảnh I đã A/B một lần dưới io-i-v1.1, và recipe này được viết từ chính
các lần hỏng đó. Kết quả cũ giữ nguyên: dưới io-i-v1.1, I01-S1, I02-S2, I05-S1, I06, I07-S1 không có cặp; I03, I04 PASS.

## 1. Chẩn đoán (frame đã niêm, chỉ đọc JSON)

| Cảnh | vE | Lỗi | Nguyên nhân đã thấy |
|---|---|---|---|
| I01-S1 | 6,0 | A, B `READINESS_NOT_REACHED` | Probe 2 ready ở 6,2 s, nhưng trong A/B tốc độ EGO dao động 4,27–5,32 m/s (target 5,338) từ 4 s tới khoảng 12 s, trong lúc NPC chạy song song ở làn bên, lệch 1–3 m. Marker EGO ở arc 19 m bị vượt khi EGO chưa ổn định, nên runner không bao giờ ready. Probe không đại diện cho A/B. |
| I02-S2 | 7,5 | A `X_END_MISSING` | X_END cần **cả thân** EGO qua X (rear/min, metrics.py 2193–2198), tức front ≥ X + L = 140,0 m. Route EGO kết thúc ở X + 5 = 141,3 m. Episode A kết thúc bình thường ở front 137,1 m. |
| I02-S2 | 7,5 | B `RESPONSE_BLOCKED: LANE_CHANGE_GUARD_MISSING` | Profile B đóng băng bắt đầu dịch ngang ở một arc cố định. Tới arc đó mà `SOURCE_CLEAR_CONFIRMED` / `LANE_CHANGE_PATH_CLEAR` chưa có thì runner chặn (m56-v12 response.py, `LANE_CHANGE_GUARD_MISSING` dòng 480). |
| I05-S1, I06, I07-S1 | 4,8 / 3,1 / 3,8 | A va chạm + `RESUMED_BEFORE_NPC_MERGED_AHEAD`; B va chạm + `CHANGED_BEFORE_SOURCE_CLEAR` | Tốc độ thấp, chênh vN = vE − 1. EGO A đi tiếp trước khi NPC nhập làn xong; EGO B đổi làn trước khi làn nguồn trống. Hai cảnh PASS (I03, I04) có vE 9,4 và 11,7. |

Đuôi route X + 5 m giống hệt ở I03/I04 (PASS). Vậy nó chỉ là điều kiện cần cho X_END, chưa phải nguyên nhân duy nhất.

## 2. Luật io-i-v1.2

Chỉ prepare và compile; consumer và ngưỡng không đổi.

1. **Probe chẵn với A/B (G1).** Sau probe 2, prepare chạy thêm **probe 3** bằng đúng chương trình EGO A, chương trình NPC và gain
   PID của fixture sẽ compile. Đây là probe chuẩn bị, không phải A/B, nên không tính P5. Probe 3 phải đạt readiness của runner
   trong **≤ 14,0 s** kể từ frame đầu. Không đạt → `BLOCKED_FIXTURE READINESS_PROBE3`.
2. **Đuôi X (G2).** Route EGO của cảnh I kết thúc ở **X + 2L + 10 m** (L = chiều dài thân EGO), thay cho X + 5 m. Compile kiểm
   `destination − X ≥ L + 10`.
3. **Làn nguồn trống trước khi B đổi làn (G3, cổng dự báo).** Trong probe 3, đo `t_clear`: frame đầu tiên mà mọi đỉnh bbox của
   NPC đã rời hộp làn nguồn (hộp `EGO_TARGET` của fixture). Đo `t_trig`: frame TRIGGER (NPC vượt `I_SOURCE_BOUNDARY`). Yêu cầu
   `t_clear − t_trig ≤ 2,3 s`. Ở trigger target của io-i-v1.1, profile B bắt đầu đổi làn khoảng 3,3 s sau TRIGGER, nên còn biên
   1 s. Không đạt → `BLOCKED_FIXTURE SOURCE_CLEAR_LATE`.
4. **Đi tiếp của A (G4), cần product v15.** `RESUMED_BEFORE_NPC_MERGED_AHEAD` cho thấy chương trình A không gắn việc đi tiếp với
   sự kiện NPC đã nhập làn phía trước. Sửa = guard ở runtime: A chỉ được tăng tốc lại sau `NPC_MERGED_AHEAD`. Đây là thay đổi
   product, nên phải làm trong worktree mới `m56-v15`, có test riêng, và chạy full suite trên byte cuối trước khi dùng.
   **Chưa làm hôm nay.** Khi chưa có v15, cảnh I nào có G1–G3 đạt mà A vẫn có rủi ro này thì ghi rõ trong báo cáo.

5. **Sàn Dlc (bổ sung trước mọi bước native, 15/11):** profile đổi làn của EGO B ở I dùng **Dlc_eff = max(3·vE, 18 m)** và
   cổng `LANE_CHANGE_UNSTABLE` trong probe 3, theo io-v1.6 (`PREREG_M56_IO_RECIPE_V1_6_DLC_FLOOR_20261115.md`). Bằng chứng nằm ở
   O; ở I chỉ có I07-S1 với max |steer| 0,52 ở Dlc 11,52, còn I05/I06 có B chưa kịp đổi làn. Lý do được thêm sau 52fc169 nhưng trước
   mọi số mới của I.

## 3. Phạm vi, P5, luật dừng

- Dưới version mới (io-i-v1.2), P5 cho phép **một A/B mỗi cảnh**. Chạy lại chính cảnh nào và chạy successor B3 cho cảnh nào được
  chốt như sau:
  - **I01-S1, I02-S2**: chạy lại chính cảnh. Nguyên nhân nằm ở tooling (probe không đại diện, đuôi route), không do site.
  - **I05-S1, I06, I07-S1**: luật được suy ra từ chính lần hỏng của các cảnh này, nên dùng **successor B3** (gate G của addendum G
    + G1–G3). Nếu prepare của successor không qua G3, slot ghi EMPTY.
  - **I08**: successor B3 qua gate G. Site cũ hỏng ở `RUNIN_NOT_STRAIGHT`.
- Mọi cảnh I trên cũng dùng io-v1.5 (probe dài) nếu probe 1 của chúng rơi vào trường hợp đó.
- Một revision. Cảnh nào hỏng dưới io-i-v1.2 thì ghi FAILED, không chỉnh thêm 14,0 s / 2,3 s / đuôi route.
- Báo cáo I dưới cả io-i-v1.1 và io-i-v1.2.

## 4. Thứ tự làm

1. Code nằm trong file mới (`native-io-prepare-i12.py`, bọc `native-io-prepare.py`), không sửa file đang đóng băng. Viết sau
   `REPL7_END`.
2. Kiểm offline: G2 tính lại trên route của prepare đã niêm. Kỳ vọng I02-S2 cũ trượt G2, I03/I04 cũ qua sau khi kéo dài. G3 đo lại
   trên probe 2 đã niêm của I03/I04 (PASS) và các cảnh hỏng. Ngưỡng 2,3 s **không đổi** theo kết quả đo: nếu I03/I04 trượt G3 thì
   ghi rõ, và G3 thành luật gây trượt chứ không được nới.
3. Native: prepare (probe 1–3), compile, admission, rồi mỗi cảnh một A/B, chỉ khi không có HOLD.
