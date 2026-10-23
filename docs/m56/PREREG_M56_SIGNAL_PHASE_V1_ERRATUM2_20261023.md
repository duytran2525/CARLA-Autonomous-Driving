# Erratum 2 cho signal-phase v1: gói pha theo nhóm đèn (23/10/2026)

Erratum này sửa §S3 và §S4 của signal-phase v1 (b4b6a22 và erratum 1, 59744b3). Nó được commit **trước** lần chạy lại.
Chưa có A/B nào.

## Phát hiện native

Nguồn: `m56_v2_prepare_Town04_20261023T15*` (C01, đèn 1609).

Khi một đèn đang **đỏ**, `TrafficLight.get_elapsed_time()` chỉ tăng trong khoảng 2 s đầu, sau đó đứng ở 0 suốt phần
còn lại của pha đỏ. Ví dụ chuỗi quan sát được là 10, 22, 34, rồi 0, 0, 0.

Hệ quả:
- Vị từ `('Red', 0)` khớp ở hàng trăm tick trong mỗi chu kỳ, nên điểm neo bị mơ hồ.
- Ở probe 2, NPC bị giữ 210 frame.
- Như vậy `tick_in_state` của S3 không phải là đồng hồ pha.

## S3 mới (gói pha)

```text
{light: odr của L_N, state: trạng thái của L_N,
 active: odr của đèn đang Green hoặc Yellow trong nhóm của L_N (get_group_traffic_lights) hoặc None,
 active_state: trạng thái của đèn đó,
 active_tick: round(20 · get_elapsed_time()) của đèn đó}
```

Mỗi thời điểm trong nhóm chỉ có một đèn xanh hoặc vàng, và đồng hồ của đèn đó chạy đều (đã quan sát: xanh 0…199, vàng
0…60). Vì vậy bộ năm giá trị trên xác định vị trí trong chu kỳ. Gói pha chỉ đọc, được ghi raw ở mỗi tick.

## S4 bổ sung

- **Chuỗi tham chiếu:** chuỗi gói pha của một chu kỳ đầy đủ quan sát được ở S2 (120 s), bắt đầu tại tick đầu tiên
  `L_N` chuyển sang Green.
- **Vị từ:** gói pha tại vị trí cách tick Green đầu tiên `k` tick về trước, lấy trên chuỗi đó theo modulo chu kỳ.
- **Tính duy nhất:** nếu gói này xuất hiện nhiều hơn một lần trong chu kỳ → BLOCKED_FIXTURE, lý do
  `SIGNAL_ANCHOR_AMBIGUOUS`.
- **`k ≤ 0`:** cần `−k < N_G`, nếu không → `SIGNAL_TIMING_INFEASIBLE`. Đây là điều §S4 đã viết, nay hiện thực đúng.

Quy tắc cũ (S3 `tick_in_state`) giữ nguyên văn trong file gốc; nó là phép đo hỏng, không phải một ngưỡng. Các mục S1
(erratum 1), S2, S5, S6 không đổi.
