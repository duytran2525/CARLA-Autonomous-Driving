# M56: đăng ký trước bước canh pha đèn tín hiệu (signal-phase v1, 23/10/2026)

**Thẩm quyền:** [chat] 23/10/2026, người dùng tự xác nhận là Duy: "viết đăng ký trước cho bước canh pha đèn tín hiệu
(phase_predicate) để NPC không bị đèn đỏ làm lệch pha, rồi chạy lại chuẩn bị C/L."

**Thứ tự cam kết:**
- File này được commit **trước** mọi lần chạy native dùng nó.
- Nó bổ sung cho runtime-recipe v2 (d1c91ac và các erratum 737acbc, 94c56b3) và không đổi quy tắc nào trong đó.

**Spec áp dụng (§484, §486):**
- NPC tuân thủ đèn gốc.
- Không đổi trạng thái hay thời lượng của đèn: không freeze, không reset, không all-green.
- Vị từ pha được đóng băng; chờ ≤ 60 giây mô phỏng; raw được giữ.
- Quá hạn thì `BLOCKED_SIGNAL_ADMISSION`, không săn pha, không reload, không chạy lại.
- A và B dùng chung vị từ, nhưng không giả định pha thực tế giống nhau.

Mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, không độc lập. Quy tắc chọn điểm neo ở S4 là của Claude.

## S1. Đèn điều khiển NPC

- `L_N` là đèn đầu tiên mà `World.get_traffic_lights_from_waypoint(wp, d)` trả về, với `wp` là waypoint xuất phát của
  NPC và `d` là quãng route NPC tới cửa ra junction.
- Không có đèn nào thì NPC đi qua junction không đèn: không có vị từ, mọi bước khác giữ nguyên v2.
- Đèn của EGO cũng được xác định và ghi lại, nhưng chỉ để báo cáo. EGO bỏ qua đèn theo spec §6.1 và §482.

## S2. Chu kỳ đèn quan sát được (chỉ quan sát)

1. Trước probe, runner tick đồng bộ 120 s mô phỏng mà không có actor nào và ghi trạng thái của `L_N` ở mỗi tick.
2. `N_G`, `N_Y`, `N_R` là số tick của mỗi trạng thái, đếm giữa hai lần chuyển trạng thái liền nhau. Chúng được đối chiếu
   với `get_green_time`, `get_yellow_time`, `get_red_time` và ghi kèm.
3. Nếu một trạng thái quan sát được hai lần mà số tick khác nhau, hoặc không quan sát được đủ một chu kỳ → BLOCKED_FIXTURE,
   lý do `SIGNAL_CYCLE_UNSTABLE`.

## S3. Gói pha mà runner quan sát mỗi tick

Gói pha gồm `{light: id, state: Green|Yellow|Red, tick_in_state: n}`, với
`n = round(20 · TrafficLight.get_elapsed_time())`: thời gian đã trôi trong trạng thái hiện tại, do CARLA báo, chỉ đọc.

Mỗi gói được ghi raw. Vị từ là một gói cụ thể; runner so khớp bằng phép bằng nhau, như `runtime.run_episode` đã có.
Tick khớp vị từ là `f_p`. Mọi thời gian dưới đây đo từ `f_p`, tức `t = (frame − f_p) / 20`.

## S4. Điểm neo

**Định nghĩa trên quỹ đạo probe 1** (NPC đi route dài, không có đèn đỏ trước khi tới vùng dừng):

- Station dừng `s_stop`: station trên route NPC của stop waypoint của `L_N` (`TrafficLight.get_stop_waypoints`) gần route
  NPC nhất.
- `t_in`: lúc mặt trước NPC tới `s_stop − 5 m`.
- `t_out`: lúc mặt sau NPC qua `s_stop + 5 m`.

**Tính `t_in` và `t_out`:**
- Lấy từ đường cong quãng đường `d_N(t)` của probe 1, áp cho vị trí xuất phát NPC đã đặt theo v2 §3.
- Các frame NPC bị giữ ở đèn đỏ bị loại. Sau lần giữ đầu tiên, phần còn lại ngoại suy tuyến tính bằng mức ổn định
  `v_N` (erratum 3).

**Chọn điểm neo:**
- Đèn `L_N` phải chuyển sang Green tại `T_g = t_in − 2 s`, tức `k = round(20 · T_g)` tick sau `f_p`.
- Lùi `k` tick trong chu kỳ Green → Yellow → Red → Green (độ dài `N_G`, `N_Y`, `N_R`) để ra trạng thái và
  `tick_in_state` tại `f_p`. Đó là vị từ `{light, state, tick_in_state}`.
- Nếu `k ≤ 0`: tại `f_p` đèn đã xanh được `−k` tick (cần `−k < N_G`).

**Điều kiện thời gian:**
- Cần `t_out ≤ T_g + (N_G + N_Y)/20 − 1 s`, tức NPC rời vùng dừng ít nhất 1 s trước khi đèn đỏ.
- Không đạt → BLOCKED_FIXTURE, lý do `SIGNAL_TIMING_INFEASIBLE`.

## S5. Áp dụng

- **Probe 1** chạy với vị từ `{light, state: Green, tick_in_state: 0}` cho mọi cảnh có đèn, để đo `d_N` khi NPC được đi.
- **Probe 2, marker và A/B** dùng vị từ ở S4.
- Vị từ được ghi vào `environment.phase_predicate` của ứng viên v2 và đi vào fixture qua `compile_fixture`.
- Mọi quy tắc canh pha EGO/NPC và readiness của v2 (§3, §4, E6) không đổi. Vị từ chỉ chọn lúc spawn.

## S6. Thất bại và nhãn

| Tình huống | Kết quả |
|---|---|
| Chờ vị từ quá 60 s | `BLOCKED_SIGNAL_ADMISSION`, không chạy lại |
| NPC vẫn bị giữ ở đèn đỏ trong probe 2 | `NPC_SIGNAL_HOLD_IN_PROBE2`, ghi nguyên số tick bị giữ |
| A/B vẫn có đèn đỏ | ghi nguyên văn, không chạy lại |

Những điểm sau giữ nguyên, không quyết ở đây:

- L ở junction có đèn: spec §2.2 đòi "final no-light evidence" cho L. Vị từ không thay được bằng chứng đó; đây vẫn là
  một cổng riêng.
- Tín hiệu C ở Town06 là một cổng chứng minh riêng (§486).
