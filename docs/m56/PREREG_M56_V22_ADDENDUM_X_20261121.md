# M56 addendum X: product m56-v22, pha tiến của kernel lùi F03 (steer và dung sai bước lùi) và tối ưu tốc độ, 21/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Viết **trước** A/B nào dưới v22. **Luật đặt SAU khi đã thấy số**
(nguyên tắc 6): F03-S1 v21 arm B (`outputs/m56_f_ab_Town12_20261120T192818Z`) lặp GEAR_TRANSITION -> CONTROL FORWARD -> BLOCKED
`REVERSE_APPLIED_CONTROL_UNPROVEN` từ khung 8123 tới 8820 và chạm tường 1500 s (addendum W7). Không đổi byte spec, không đổi ngưỡng Tag.

**Authority.** Duy, [chat] 21/11/2026: "sửa lỗi pha tiến cho F03 trong v22 đi đồng thời dọn những file tạm trong ổ D", rồi "chạy tiếp A/B F03
dưới v22 đồng thời tối ưu code để những A/b này có thể chạy thật nhanh"; và "tiếp tục chạy cho tới sáng và tự duyệt những gì bạn recommend cho tôi".
Ghi nhận là cho phép dựng v22 **và** chạy một A/B F03-S1 dưới v22 (một lần, P5; v22 là phiên bản mới). Không chạy F05.

## X1. Thay đổi product (m56-v22 `d9ecf31` = v21 `27783f0` + ba thay đổi)

1. **steer.** `response.reverse_intent`: điều kiện `readback.steer == 0` chỉ áp cho pha lùi. Pha tiến là PID gốc và có steer (native: -0,00195 tới
   -0,00212 sau mỗi CONTROL FORWARD). `hand_brake` vẫn bị từ chối ở mọi pha. **Luật cũ (v19-v21):** steer khác 0 chặn ở mọi pha.
2. **Bước lùi.** `response._reverse_forward`: một bước lùi (để tính `last_reverse`) là bước lùi **lớn hơn `proof.uncertainty`** đã công bố
   (F03 REVERSE_STOP_BOUND 1/100 m). **Luật cũ (v19-v21):** mọi bước b < a. Lý do (thấy sau khi sửa 1): cổng dữ liệu thật vẫn BLOCKED ở khung 8124 và
   8127, vì nhả dốc sau khi vào số lăn lùi 2,5e-4 m rồi 9,8e-4 m; luật cũ đẩy `last_reverse` qua khung vào số và ra
   `REVERSE_TERMINAL_GEAR_UNPROVEN`. Trôi chậm sau khi vào số vẫn bị **bao cộng dồn** của v21 bắt (`REVERSE_FORWARD_DIRECTION_INVALID`,
   dung sai 1/100 m). Tổng `retreat` vẫn cộng mọi bước lùi (không đổi). Kernel lùi dùng chung với F06-ALT1 nên cũng chịu luật mới (không chạy F06).
3. **Tốc độ, hành vi không đổi.** Cờ `evidence._V22_FAST` (mặc định True; False = đường mã v21 y nguyên):
   đọc quỹ đạo tăng dần (`evidence._read_trajectory_grown`), nhớ kiểm tra từng hàng lịch sử lùi theo khung (`response._ROW_BOUND`),
   nhớ `metrics._directed_speed` và `metrics._frame_capability` theo khung (weak, khóa theo định danh khung, bảo vệ bằng định danh route/fixture).
   Mọi cache chỉ lưu khi hàm tính không ném lỗi.

Không đổi: consumer (`metrics`) luật nào, mọi ngưỡng, bound, tham số prepare, spec, REVF.
Test helper `tests/m56/f03_cases.py`: thêm `ROLLBACK_AT_FORWARD_START` (một bước lùi thuần ở tick tiến đầu tiên) và `REVERSE_UNCERTAINTY` của proof tổng hợp; mặc định 0, nên mọi test cũ chạy y như trước.

## X2. Luật cũ vẫn được báo

A/B dưới v22 được chấm cặp dưới **v22, v21, v20** (v18 và v13 bỏ để tiết kiệm thời gian, công bố ở đây; có thể chấm bù offline sau khi A/B xong).
Kết quả F03-S1 của v19 (FAILED, lỗi điều phối), v20 (FAILED, dung sai 0) và v21 (B hết 1500 s) giữ nguyên, không bị viết lại.

## X3. Cổng trước A/B (tooling, trên dữ liệu thật, chỉ quyết định của producer; không tính metric nào trên episode v21)

1. `tests/m56/test_v22_forward_phase_steer.py`, `test_v22_fast_path_equivalence.py` và nhóm test F03/F05/F06/lùi/bò dưới v22:
   458 test chọn bằng `-k "f03 or f05 or F03 or F05 or creep or reverse or f06 or F06 or v19 or v20 or v21 or v22 or bounded"`, chạy ba nhóm song song trên `d9ecf31`: 133 + 142 + 183 passed, 0 failed, 0 error (`outputs/m56_v22_tests_g{1,2,3}.stdout.txt`). Đối chứng: test steer -0,002 đỏ dưới mã v21 trước khi sửa; dung sai 0 (luật cũ) vẫn chặn bước lùi 2,5e-4 m; vượt dung sai (0,02 m) vẫn chặn; phanh tay vẫn chặn; cờ `_V22_FAST` bật và tắt phát cùng lệnh và cùng sự kiện trên producer khép kín (A và B).
2. `native-v22-f03-forward-gate.py`: điều phối thật của runner trên khung F03 v21 B, kiểm tính xác định (0 lệch) và 10 mẫu pha tiến:
   dưới v21 (`blocked`, đối chứng âm, file `m56_v22_forward_gate_negcontrol_v21.stdout.txt`) 10/10 BLOCKED; dưới v22 (`not_blocked`) 10/10 CONTROL FORWARD.
   Đây là cổng về **bước đầu** của pha tiến (khung 8124-8139).
3. `bench-v22-tick.py`: tương đương mã v21 và v22 trên 14 tick lấy mẫu của F03 v21 B, lệnh giống hệt (so sánh dataclass). Đo trên cùng máy,
   cùng khung: đường v21 0,6 s/tick (117 hàng) -> 3,3 s/tick (875 hàng) chỉ riêng `_commands`; đường v22 `_known_events` + `_commands` trung bình
   0,12 s/tick trên 759 tick (v21 B hết 1500 s vì chi phí này tăng theo O(n) mỗi tick).
4. Cổng A5 đầy đủ (`native-f03-replay.py` trên episode probe-A) dưới v22: `F03_REPLAY_PASS` (`outputs/m56_f03_gate_v22_full.stdout.txt`).
5. Cổng đĩa (D > 80, E > 150, C >= 10 GB) và commit trống >= 32 GB trước khi bật CARLA.
6. Proxy phía consumer trên khung F03 v21 B (chỉ đọc, chỉ xét luật có kích hay không, không tính số đo nào; consumer giống hệt v21):
   - `native-v22-f03-consumer-proxy.py` (`metrics._forward_tail`, `POST_END_UNPLANNED_REVERSE`, so từng bước tâm xe với dung sai CONTINUOUS_GEOMETRY
     1e-3 m): **QUIET**. Sau NPC_STOP_CONFIRMED (8122) có 285 bước giảm station của EGO (vòng lặp BLOCKED của v21 lăn lùi mỗi 3 khung), lớn nhất
     9,77e-4 m, biên nhỏ nhất 2,2e-5 m. File `outputs/m56_v22_consumer_proxy_x.stdout.txt`.
   - `native-v22-f03-window-proxy.py` (logic W4c: `:781` readback lùi ở mọi bước lùi, `:795` last_retreat rồi dừng 0,5 s) trên cửa sổ 8062-8122:
     **QUIET**. 40 bước lùi đều có readback lùi, last_retreat 8105, dừng quan sát được ở 8115. File `outputs/m56_v22_consumer_proxy_window.stdout.txt`.

## X4. Số lần thử (để người đọc tự cân nhắc forking paths)

F03-S1: đây là A/B **thứ tư** (v19 FAILED do lỗi điều phối, v20 FAILED do dung sai 0, v21 B bị chặn vì steer rồi hết 1500 s, v22). Hai lỗi
của kernel (steer, dung sai bước lùi) được tìm thấy **từ dữ liệu của chính F03-S1**; không có lần thử nào bị xóa.

## X5. Rủi ro còn lại (công bố trước khi chạy)

- Pha tiến chỉ được kiểm trên dữ liệu thật ở bước đầu (10 mẫu). Phần sau của pha tiến (tới đích) kiểm bằng producer tổng hợp, chưa có dữ liệu thật.
- Dung sai của consumer `POST_END_UNPLANNED_REVERSE` là 1e-3 m (từng bước), bước lùi lớn nhất quan sát được 9,77e-4 m (biên 2,2e-5 m, rất sát).
  Một lần nhả dốc lăn lùi hơn 1e-3 m trong một tick sẽ làm cặp FAILED theo luật consumer hiện có. Consumer không đổi ở v22; nếu xảy ra, báo như đã đo.
- Rủi ro W4c (`metrics.py:795`, `last_retreat`) giữ nguyên.
- Tốc độ chỉ được đo ở phần `_known_events` + `_commands`; phần ghi bytes lịch sử tích lũy của kit (O(n) byte mỗi tick) giữ nguyên vì định dạng do bằng chứng cố định.
- `outer_s` 1500 s giữ nguyên (là tham số vận hành đã công bố, không đổi). Nếu B vẫn hết giờ, báo như đã đo.

## X6. Một A/B

Chỉ F03-S1, một marker `m56_v22_ab_F03_LAUNCHED` ghi trước khi `room()` chờ. Bất kể B ra sao, báo như đã đo, không chạy lại.
Nếu hạ tầng cắt A/B thì ghi lại và chờ Duy.

## X7. Kết quả F03-S1 dưới v22 (ghi sau A/B, 21/11 16:50Z), như đã đo

- Lần chạy chain đầu (06:52Z) chờ ở `room()` vì commit trống 21-25 GB < 32 GB. Lúc 08:23Z máy bị tắt sạch từ menu Start (event 1074). Khi đó chưa bật CARLA, chưa có marker, thư mục A/B F03-S1 vẫn đúng ba thư mục đã tiêu, nên P5 **chưa** tiêu. Sau khi máy bật lại, bộ canh được bật lại với hậu tố `r22b` và chain được chạy lại, không sửa gì.
- Compile preview `m56_f_compile_Town12_20261121T155050Z`: FROZEN/ADMITTED. Marker `m56_v22_ab_F03_LAUNCHED` 15:53:34Z. Run `outputs/m56_f_ab_Town12_20261121T155336Z/M56-P-F03-S1`: `sealed: true`, `blocked: []`, cả hai arm CLEANED, không OUTER_TIMEOUT. Cả A/B mất khoảng 10 phút (v21: riêng arm B đã chạy hết 1500 s).
- Arm B (308 khung, 8686-8993): TRIGGER 8802, NPC_STOP_CONFIRMED 8862, **DESTINATION_CONFIRMED 8993**. Lệnh EGO: HOLD 117, REVERSE 37, STOPPING 23, FORWARD_GEAR 1, FORWARD 130; **0 BLOCKED**. Kernel lùi v22 chạy trọn từ đầu tới đích.
- Cặp: **FAILED** dưới cả ba luật v22 (`m56_v6_pair_20261121T160346Z`), v21 (`161612Z`) và v20 (`163125Z`); `comparisons [null, null]`, không có số đo so sánh nào.
  - A: CONFIRMED / COMPLETE / VALID.
  - B: physical FAILED, witness UNCERTAIN, với các lý do `POST_END_UNPLANNED_REVERSE`, `REVERSE_COMMAND_REPLAY_UNPROVEN`, `W01_W05_VALIDATION_PENDING`, `F_FULL_ACTION_REVIEW_PENDING`.
- Nguyên nhân của FAILED vật lý (`diag-v22-f03-b.py`, chỉ đọc, file `outputs/m56_v22_f03_b_diag.stdout.txt`): sau NPC_STOP_CONFIRMED có ba bước giảm station tâm EGO vượt dung sai CONTINUOUS_GEOMETRY 1e-3 m. Đó là các khung 8865 (1,464 mm), 8869 (1,705 mm) và 8870 (1,464 mm). Cả ba nằm trong CONTROL FORWARD với readback throttle 0,75, phanh 0, số 1: lúc khởi hành lên dốc sau khi vào số tiến, xe lăn ngược. Năm bước giảm khác nằm trong dung sai. Đây đúng là rủi ro đã công bố ở X5 (biên trên v21 B chỉ còn 2,2e-5 m).
- `REVERSE_COMMAND_REPLAY_UNPROVEN`: đây là lý do UNCERTAIN phía witness (`evidence.py:1071/1073`, việc replay lệnh lùi ném lỗi hoặc ra BLOCKED). v21 B cũng có lý do này. Nó không đổi kết quả FAILED. Nguyên nhân đang được truy offline (`diag-v21-eval-trace.py` trên B, M56_CODE=v22).
- Kết quả được báo như đã đo. Không chạy lại, không đổi luật consumer. Mọi thay đổi tiếp theo cho F03-S1 (một luật consumer đặt sau khi thấy số, hoặc một producer giữ phanh cho tới khi lực kéo đủ, kiểu hill-start) là phiên bản mới cộng với A/B thứ năm, và chờ Duy quyết.