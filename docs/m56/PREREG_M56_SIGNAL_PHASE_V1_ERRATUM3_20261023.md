# Erratum 3 cho signal-phase v1: gói pha gồm cả nhóm đèn (23/10/2026)

Erratum này sửa §S3 (bản erratum 2, 425e8b1). Nó được commit **trước** lần chạy lại. Chưa có A/B nào.

## Phát hiện native

Nguồn: `m56_v2_prepare_Town04_20261023T16*`, cảnh C01, đèn 1609.

Giữa hai pha xanh có một khoảng **đỏ toàn bộ** dài khoảng 2 s (`get_red_time` = 2 s): không đèn nào trong nhóm xanh
hay vàng. Trong khoảng đó, gói pha của erratum 2 đều là `{active: None}` và lặp lại ở mọi khoảng chuyển.

Điểm neo theo S4 rơi đúng vào khoảng này: `k` = 39 tick trước khi 1609 chuyển xanh. Kết quả là C01 bị
`SIGNAL_ANCHOR_AMBIGUOUS`.

Trong khoảng đỏ toàn bộ vẫn có một đồng hồ chạy: `get_elapsed_time()` của đèn vừa chuyển đỏ tăng trong khoảng 2 s đầu
(đã thấy ở lần chạy trước: 10, 22, 34).

## S3 mới (gói pha)

```text
{light: odr của L_N,
 group: [[odr, state, round(20 · get_elapsed_time())] cho mọi đèn trong get_group_traffic_lights(), sắp theo odr]}
```

Gói này là toàn bộ trạng thái quan sát được của nhóm, chỉ đọc và được ghi raw ở mỗi tick. Quy tắc duy nhất của S4 không
đổi: nếu gói neo xuất hiện nhiều hơn một lần trong chu kỳ tham chiếu thì vẫn là `SIGNAL_ANCHOR_AMBIGUOUS`.

## Giữ nguyên

- Gói của erratum 2 được giữ nguyên văn.
- Không đổi ngưỡng, `k`, chu kỳ hay điều kiện thời gian nào.
- Các mục S1 (erratum 1), S2, S4, S5, S6 không đổi.
