# M56 addendum V: F05, thêm một A/B dưới m56-v20 (20/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Viết **trước** khi chạy A/B này và trước mọi số đo của F05.
Nó mở rộng addendum T/U (`PREREG_M56_F05_ADDENDUM_T_20261118.md`, `PREREG_M56_F05_ADDENDUM_U_20261118.md`). Không đổi byte spec,
không đổi ngưỡng Tag, không đổi luật T/U.

**Authority.** Duy, [chat] 20/11/2026, trả lời câu hỏi "chạy cái nào" (ba lựa chọn: F05 dưới v20, F03 v21, chỉ guard và uploader):
chọn "F05 dưới v20". Câu hỏi đã nêu rõ rằng mọi cảnh còn lại đã dùng hết lượt A/B duy nhất của phiên bản hiện tại. Đây là quyết
định của người có thẩm quyền theo mục "Một A/B F05 mới cần quyết định của Duy" trong batch log 18/11 (3).

## V1. Đây là chạy lại cùng code F05, không phải sửa product

- A/B F05 dưới v18 (`outputs/m56_f_ab_Town12_20261118T093346Z/M56-P-F05`) **vẫn là đã tiêu và vẫn được báo như đã đo**:
  arm A kết thúc sạch; arm B dừng `RESPONSE_BLOCKED` `CREEP_ORIGIN_UNBOUND` ở khung TRIGGER (khung thứ 30, 30 khung đã thấy)
  vì lỗi tooling của kit (`a032cbf`: kit đưa khung boundary vào history, runner thì không: 31 so với 30 witness TRIGGER).
  Cặp dưới v18 và v13: `BLOCKED_WITNESS`, `comparisons` null. **Không có số đo F05 nào (d, khoảng dừng, khoảng cách) được tính
  từ lần đó**, nên không luật hay tham số nào của lần chạy này phụ thuộc vào một số đo F05.
- `git diff 8d52959 22c57cf` (v18 → v20) chỉ chạm: nhánh `release` của F03 trong `response.py` (chỉ khi `phases['release']`),
  `runtime._bounded` (chỉ đúng với meta `mechanism` F03 hoặc F06-ALT1), và test của F03. **Không dòng nào của đường F05/creep
  đổi.** Nên v20 hành xử với F05 giống hệt v18. Nhãn "v20" là phiên bản product hiện tại; lý do một A/B mới là quyết định của Duy
  ở trên, không phải một sửa lỗi product.
- Hệ quả cho cách đọc: kết quả sẽ được báo là "F05 một A/B dưới v20 (code F05 giống v18)", cạnh A/B v18 chưa có số.

## V2. Luật: không đổi

- Luật T (steer |steer| ≤ 1/50) và luật U (dừng trong dự trữ 1 m sau stopping bound) giữ nguyên là luật chính cho lần chạy này;
  luật cũ (steer == 0, đúng 1 m) tính song song và báo cả hai, như đã đăng ký ở addendum T/U.
- Chấm cặp ba lần: dưới v20, dưới v18 và dưới v13 (như `run-f05-u.sh`, thêm v20).
- Không có luật nào được đặt sau khi thấy số. Mọi ngưỡng, bound và tham số prepare lấy nguyên từ addendum T/U.

## V3. Artifact dùng lại nguyên byte, không diễn tập B

- Prepare r18c (`outputs/m56_v2_prepare_Town12_20261118T091935Z`: d0 4,091 m, gap settle không đổi qua 311 khung, hai lần settle cùng một
  giá trị, bốn probe bò: đỉnh 1,31 m/s, quãng dừng 0,153 / 0,049 / 0,026 / 0,005 m, CREEP_STOP_BOUND 0,21 m, vmax 1,42 m/s,
  boundary 0,77 m, uncertainty 0,01) và revision đã đóng băng
  `outputs/m56_c0_partial_io_asel2f05prep_20261118T092923Z/c0-partial-v5-frozen-revision.json`
  (sha256 `e1b578183e4b10007cbbcf3d4101e7df35beb49d9b19297905a0bf0a2ee5fcf3`, kiểm trước khi chạy). Không prepare lại.
- Không chạy B nào ngoài A/B. Fixture vẫn được biên dịch lại trong phiên A/B (gắn với boot/world của phiên); một lần biên dịch xem
  trước (không episode, không tiêu P5) chạy ngay trước A/B để kiểm FROZEN và ADMITTED.

## V4. Cổng offline mới trước A/B (tooling; bài học của A/B F03 v20)

A/B F03 dưới v20 qua cổng chỉ kiểm điều phối lệnh và hỏng ở bước chưa từng chạy (bước dừng lùi, rồi seal). Với F05, B chưa từng
chạy native quá khung TRIGGER. Vì vậy:

1. `native-f05-v20-gate.py` phát lại **arm B thật của v18** (30 khung, gồm khung TRIGGER bị chặn) dưới `M56_CODE=m56-v20`:
   bỏ các trường creep mà kit cũ đã ghi, kit đã sửa (`a032cbf`) sinh lại từng khung (khung boundary tới `seal_frame` trước và bị bỏ,
   như native), `step_response` điều khiển chương trình B. PASS khi: các `cause` đã ghi trước TRIGGER được tái tạo; **khung TRIGGER
   không còn bị chặn** (phát ra `CREEP`); `kit.active_target` nhận mọi lệnh đã ghi (cả 30 khung thật lẫn 552 lệnh của episode B
   tổng hợp hoàn chỉnh creep → dừng → forward). Đối chứng âm: với kit **trước** `a032cbf` cổng FAIL ở khung TRIGGER
   (`CREEP_HISTORY_OBSERVATION_UNBOUND`); với kit hiện tại PASS.
2. `test-f05-kit-offline.py` dưới v20: episode B tổng hợp đầy đủ qua `F05Kit.seal_frame` và `step_response` tới FORWARD, đủ các sự kiện
   của evaluator.
3. Test F05 của product dưới v20 (chọn `-k "f05 or creep or F05"` trên `tests/m56`), kết quả ghi ở batch log.
4. Cổng đĩa của Duy (19/11): D trống > 80 GB, E trống > 150 GB, cộng C ≥ 10 GB và commit ≥ 25 GB, kiểm trong `room()` trước mỗi lần bật CARLA.

## V5. Rủi ro còn lại, công bố trước

- Bước creep → dừng → forward của B chỉ được kiểm trên episode tổng hợp, chưa trên dữ liệu native. Nếu B hỏng ở đó, đó là kết quả đo của
  một lượt A/B duy nhất và **không chạy lại** (P5).
- Chi phí mỗi khung của runner tăng theo độ dài episode (A/B F03 v20: từ 0,2 s lên 2–3 s ở khung 600+, tường ngoài 25 phút).
  Arm A của F05 dưới v18 chạy khoảng 9 phút. Nếu B chạm `OUTER_TIMEOUT` thì đó là kết quả được báo như đã đo.
- Một A/B, một lần. Marker `outputs/m56_f05_v20_ab_LAUNCHED` ghi **trước** khi `room()` chờ. Nếu chuỗi chết trong lúc chờ, kiểm tra xem có
  thư mục `outputs/m56_f_ab_Town12_*` mới chứa `M56-P-F05` (ngoài `20261118T093346Z`) trước khi coi P5 là đã tiêu; nếu không có thì xóa marker.
