# M56 addendum Y: product m56-v23, khởi hành lên dốc của kernel lùi F03 (giữ phanh khi vào số tiến) và admit nguồn của proof dừng, 22/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Viết **trước** A/B nào dưới v23. **Luật đặt SAU khi đã thấy số**
(nguyên tắc 6): F03-S1 v22 arm B (`outputs/m56_f_ab_Town12_20261121T155336Z`) tới DESTINATION_CONFIRMED với 0 BLOCKED, nhưng cặp FAILED
vì `POST_END_UNPLANNED_REVERSE` (addendum X7). Không đổi byte spec, không đổi ngưỡng Tag, không đổi luật consumer.

**Authority.** Duy, [chat] 22/11/2026: "làm tiếp", rồi chọn phương án "v23 hill-start (Recommended)" khi được hỏi bước tiếp theo cho F03-S1.
Nội dung phương án: "Producer giữ phanh cho tới khi lực kéo tiến đủ (chống lăn ngược), sửa luôn lỗi admit reverse-stop-bound.json; không đổi
luật consumer. Cần A/B thứ năm cho F03-S1 (P5 v23)." Ghi nhận là cho phép dựng v23 **và** chạy một A/B F03-S1 dưới v23 (một lần, P5;
v23 là phiên bản mới). Không chạy F05, không chạy F06. Sau đó Duy viết: "tiếp tục chạy các job tới sáng và tự động phê duyệt nếu có vấn đề gì,
cứ làm theo những gì bạn recommended". Mọi quyết định trong đêm được ghi là tự duyệt theo ủy quyền này; các giới hạn cố định (P5, byte spec,
ngưỡng Tag, cổng đĩa và commit, không push) giữ nguyên.

## Y1. Thay đổi

1. **Product, giữ phanh khi khởi hành (m56-v23 `321ee7f` = v22 `d9ecf31` + một thay đổi trong `m56/response.py`).**
   Trong `HILL_HOLD_S` = 1 s đầu tiên của pha FORWARD, kernel lùi gửi lệnh CONTROL FORWARD tường minh `HILL_HOLD_CONTROL`
   (throttle 0,75, steer 0, phanh 0,3, số 1, không lùi, không manual). Sau đó kernel gửi lệnh tiếp nối gốc như v22 (control None,
   PID của BasicAgent). Lệnh giữ được gửi ở cả tick chuyển pha (lệnh FORWARD đầu tiên do `reverse_intent` phát) và ở các tick sau
   (`_reverse_forward`), khi `frame.simtime - state.start < HILL_HOLD_S`.
   - Lý do: ở v22 B, sau khi vào số tiến và nhả phanh, hộp số tự động không cho lực kéo trong khoảng 0,35 s. Xe EGO lăn ngược 1,46-1,71 mm
     mỗi tick trên dốc 3,75 độ (khung 8864-8870). Ba bước vượt dung sai từng bước 1e-3 m của consumer.
   - Chọn số: throttle 0,75 là throttle lớn nhất của PID gốc, cũng là giá trị PID phát lúc đứng yên (readback v22 B). Phanh 0,3 là phanh
     giữ đã dùng ở pha HOLD và ở cuối pha lùi. `HILL_HOLD_S` = 2 lần `gear_switch_time` mặc định của CARLA (0,5 s, theo tài liệu).
     Số này không được khớp theo 0,35 s đã thấy.
   - Phạm vi: chỉ EGO, chỉ fixture có `mechanism == 'F03'`. F06-ALT1 dùng chung kernel nhưng không bị đổi. Ego A (chương trình bước)
     và NPC không đi qua kernel lùi nên không bị đổi. `HILL_HOLD_S = 0` trả về đúng luật cũ.
   - **Luật cũ (v19-v22):** gửi lệnh tiếp nối gốc (phanh 0) ngay từ tick FORWARD đầu tiên.
2. **Tooling, admit nguồn của proof dừng (sau cờ).** `native_v2_kit.finish`: khi `M56_KIT_ADMIT_STOP_BOUND=1`, kit niêm phong thêm
   `stop_bound_sources(fixture)`. Đó là raw ref của proof REVERSE_STOP_BOUND và CREEP_STOP_BOUND, cùng ref review và authority ref của chúng.
   - Lý do: ở v22 B, raw ref `M56-P-F03-S1\reverse-stop-bound.json` không nằm trong nguồn được admit của arm. Consumer vì vậy không replay
     được lệnh lùi (`ADMITTED_SOURCE_FALSE` 191 lần ở `evidence.py:1061`) và ra `REVERSE_COMMAND_REPLAY_UNPROVEN` (addendum X7).
   - Luật admit của consumer giữ nguyên: nguồn vẫn phải được niêm phong lúc chạy. Kit chỉ niêm phong thêm đúng các file mà proof đã khai.
   - Không có cờ (mọi A/B trước) thì kit giữ nguyên từng byte. Chỉ chain v23 đặt cờ.

Không đổi: consumer (`metrics`, `evidence`), mọi ngưỡng, bound, tham số prepare, spec, REVF, `outer_s`.
Test helper `tests/m56/f03_cases.py`: thêm mô hình trễ ăn số `ENGAGE_TICKS` / `ROLLBACK_PER_TICK`. Trong ENGAGE_TICKS tick FORWARD đầu
tiên, xe không có lực kéo: phanh > 0 thì xe đứng yên, phanh 0 thì xe lùi ROLLBACK_PER_TICK. Sau đó tick có phanh > 0 vẫn đứng yên. Mặc
định 0, nên mọi test cũ chạy y như trước. Đây là mô hình của độ trễ native, không phải hiệu chỉnh.

## Y2. Luật cũ vẫn được báo

A/B dưới v23 được chấm cặp dưới **v23 và v22**. v22 có consumer giống hệt v23 nhưng kernel replay là luật cũ, nên v22 sẽ thấy các lệnh giữ
như lệnh không khớp. v21 và v20 bỏ để tiết kiệm thời gian, công bố ở đây; có thể chấm bù offline sau.
Kết quả F03-S1 của v19 (FAILED, lỗi điều phối), v20 (FAILED, dung sai 0), v21 (B hết 1500 s) và v22 (FAILED, lăn ngược khi khởi hành)
giữ nguyên, không bị viết lại.

## Y3. Cổng trước A/B (tooling; trên dữ liệu thật chỉ xét quyết định của producer, không tính metric mới nào trên episode v22)

1. `tests/m56/test_v23_hill_hold.py` (5 test) và nhóm test F03/F05/F06/lùi/bò dưới v23: 463 test chọn bằng
   `-k "f03 or f05 or F03 or F05 or creep or reverse or f06 or F06 or v19 or v20 or v21 or v22 or v23 or bounded"`, chạy ba nhóm song song
   (`outputs/m56_v23_tests_g{1,2,3}.stdout.txt`) trên `321ee7f`. Kết quả: 155 + 154 + 154 passed, 0 failed, 0 error.
   Lần chạy đầu bị mất output (khởi chạy qua `cmd.exe /c` dưới DETACHED_PROCESS, stdout rỗng; file giữ lại với hậu tố `_lost_cmd`),
   nên đã chạy lại toàn bộ, không đổi mã.
   - Đối chứng: luật cũ (`HILL_HOLD_S = 0`) với trễ ăn số 5 tick, 1,5 mm mỗi tick, ra `POST_END_UNPLANNED_REVERSE`. Đó là lỗi v22 tái hiện
     trong vòng khép kín.
   - Luật mới với cùng trễ: không có `POST_END_UNPLANNED_REVERSE`, và không có lý do `*COMMAND*` nào (consumer replay đúng lệnh giữ).
   - 20 lệnh FORWARD đầu là `HILL_HOLD_CONTROL`, sau đó là control None, với cả hai cách điều phối (trực tiếp và `runtime._commands`).
   - Ego A và NPC không bao giờ nhận lệnh giữ.
2. `native-v23-f03-hold-gate.py`: điều phối thật của runner trên khung F03 v22 B, từ TRIGGER tới khung 8900.
   - Tính xác định: 0 lệch.
   - Dưới v23 (`hold`, file `outputs/m56_v23_hold_gate_final.stdout.txt`): 38 lệnh từ khung vào số 8863, đều CONTROL FORWARD.
     20 lệnh đầu (8863-8882) là throttle 0,75 + phanh 0,3, rồi control None từ 8883.
   - Đối chứng âm dưới v22 (`stock`, file `outputs/m56_v23_hold_gate_negcontrol_v22.stdout.txt`): held 0.
3. `native-v22-f03-forward-gate.py not_blocked` dưới v23 (khung F03 v21 B): 0 lệch, 10/10 CONTROL FORWARD
   (`outputs/m56_v23_forward_gate_final.stdout.txt`).
4. Cổng A5 đầy đủ (`native-f03-replay.py` trên episode probe-A) dưới v23: `F03_REPLAY_PASS` (`outputs/m56_f03_gate_v23_full.stdout.txt`).
5. `native-v23-admit-proxy.py` trên arm B của v22, mã v22, chỉ đọc (`outputs/m56_v23_admit_proxy_v22B.stdout.txt`): giả lập việc kit niêm
   phong `stop_bound_sources`. Có 2 ref; 1 ref cần giả lập (`reverse-stop-bound.json`), bytes và sha256 khớp. Kết quả **ADMIT_PROXY PASS**:
   không còn lý do `*COMMAND*` nào. Lý do còn lại là `POST_END_UNPLANNED_REVERSE` (lăn ngược, việc của thay đổi 1),
   `F_FULL_ACTION_REVIEW_PENDING` và `W01_W05_VALIDATION_PENDING`.
6. Cổng đĩa (D > 80, E > 150, C >= 10 GB) và commit trống >= 32 GB trước khi bật CARLA.

## Y4. Số lần thử (để người đọc tự cân nhắc forking paths)

F03-S1: đây là A/B **thứ năm** (v19 FAILED do lỗi điều phối, v20 FAILED do dung sai 0, v21 B bị chặn vì steer rồi hết 1500 s, v22 FAILED do
lăn ngược khi khởi hành, v23). Ba lỗi của kernel (steer, dung sai bước lùi, khởi hành lên dốc) và lỗi admit đều được tìm thấy **từ dữ liệu
của chính F03-S1**. Không có lần thử nào bị xóa.

## Y5. Rủi ro còn lại (công bố trước khi chạy)

- Chưa đo trên CARLA việc throttle 0,75 + phanh 0,3 có giữ được xe trên dốc hay không. Nếu phanh thắng, xe đứng yên; nếu throttle thắng, xe
  bò tiến (không phải lùi). Mô hình tổng hợp giả định xe đứng yên.
- Chưa đo việc 1 s có đủ cho hộp số ăn số hay không (v22: không có lực kéo khoảng 0,35 s).
- Lúc nhả phanh sau 1 s, PID gốc nhận lái. Nếu lực kéo khi đó nhỏ hơn thành phần trọng lực dọc dốc, xe vẫn có thể lùi hơn 1e-3 m trong một
  tick, và cặp FAILED theo luật consumer hiện có.
- Pha tiến sau lệnh giữ (tới đích) chỉ được kiểm bằng producer tổng hợp. Trên dữ liệu thật mới chỉ kiểm quyết định của producer.
- Sửa admit chỉ được kiểm offline bằng proxy trên v22 B. Bundle thật có cờ được tạo lần đầu trong A/B này.
- `F_FULL_ACTION_REVIEW_PENDING` và `W01_W05_VALIDATION_PENDING`: ở arm A của v22 hai lý do này được giải trong bước chấm cặp (A VALID,
  reasons rỗng). Chưa biết chúng có được giải cho B hay không khi B không còn FAILED.
- Rủi ro W4c (`metrics.py:795`, `last_retreat`) và rủi ro tốc độ ghi lịch sử của kit giữ nguyên (addendum X5).

## Y6. Một A/B

Chỉ F03-S1, một marker `m56_v23_ab_F03_LAUNCHED` ghi trước khi `room()` chờ. Bất kể B ra sao, báo như đã đo, không chạy lại.
Nếu hạ tầng cắt A/B thì ghi lại và chờ Duy.
