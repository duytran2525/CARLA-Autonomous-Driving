# Erratum 1 cho signal-phase v1: chọn đèn điều khiển NPC (23/10/2026)

Erratum này sửa §S1 của `PREREG_M56_SIGNAL_PHASE_V1_20261023.md` (commit b4b6a22). File gốc giữ nguyên. Erratum được commit
**trước** lần chạy lại.

## Phát hiện native

Nguồn: `outputs/m56_v2_prepare_Town04_20261023T154309Z/M56-P-C01`.

1. Quy tắc S1 cũ chọn "đèn đầu tiên do `get_traffic_lights_from_waypoint` trả về". Với route NPC dài 150 m, cách này
   chọn đèn OpenDRIVE 1625, mà stop waypoint của đèn này cách route NPC **107,7 m**. Đèn đó không điều khiển làn của
   NPC.
2. Ở probe 2, NPC bị giữ 210 frame trong khi đèn 1625 đang xanh. Lệnh giữ đến từ đèn thật ở junction xung đột.
3. Chu kỳ quan sát được: xanh 200 tick, vàng 61 tick, đỏ 947 tick, tổng 1208 tick = 60,4 s. Con số này lớn hơn mức chờ
   60 s của spec §484, nên có điểm neo sẽ bị `BLOCKED_SIGNAL_ADMISSION`. Trường hợp đó được ghi nguyên, không nới.

## S1 mới

- `L_N` là đèn, trong số các đèn mà `get_traffic_lights_from_waypoint` trả về dọc route NPC tới cửa ra junction, có ít
  nhất một stop waypoint cách route NPC **≤ 1,0 m** theo phương ngang.
- Nếu có nhiều đèn như vậy, chọn đèn có station dừng lớn nhất mà vẫn ≤ `n_entry`, tức đèn của junction xung đột.
- Không có đèn nào thỏa → làn NPC không có đèn tại junction xung đột, không dùng vị từ.

Quy tắc cũ, giữ nguyên văn: "đèn đầu tiên do API trả về". Đây là sửa lỗi đo, đặt sau khi thấy lần chạy đó, và chưa có A/B
nào. Các mục S2–S6 không đổi.
