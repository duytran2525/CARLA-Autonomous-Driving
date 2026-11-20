# M56 addendum W: product m56-v21, dung sai hướng chuyển động cho kernel lùi (F03/F06) và bò (F05), 20/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Viết **trước** A/B nào dưới v21. **Luật đặt SAU khi đã thấy số**
(nguyên tắc 6): F03-S1 v20 arm B bị chặn vì một bước tiến +2,187e-4 m (addendum A6), F05 v20 arm B bị chặn vì một bước lùi
−1,164e-7 m (addendum V7). Không đổi byte spec, không đổi ngưỡng Tag.

**Authority.** Duy, [chat] 20/11/2026: "làm v21 cho tôi", trả lời đề xuất v21 chung cho F03 và F05 (addendum A6, V7). Ghi nhận là cho phép dựng v21
**và** chạy một A/B cho mỗi cảnh F03-S1 và F05 dưới v21 (một lần mỗi cảnh, P5).

## W1. Thay đổi product (m56-v21 `27783f0` = v20 `22c57cf` + đúng một luật)

- Hàm chung `response._envelope_violation(stations, direction, tolerance)`: vị trí đầu tiên lệch **ngược hướng** quá `tolerance` so với vị trí
  tốt nhất từ trước tới đó (max chạy cho hướng tới, min chạy cho hướng lùi). Đây là **bao (envelope)**, không phải dung sai từng bước: trôi chậm
  ngược hướng vẫn cộng dồn và vẫn hỏng (ở 20 Hz, dung sai từng bước 1/100 m sẽ cho lọt 0,2 m/s trôi ngược).
- `tolerance` = `proof.uncertainty` đã công bố từ trước mọi số đo: REVERSE_STOP_BOUND F03 1/100 m, CREEP_STOP_BOUND F05 0,01 m. Không chỉnh theo
  2,19e-4 hay 1,16e-7 (cả hai nhỏ hơn hai tới năm bậc).
- Chỗ áp dụng:
  - `reverse_intent` (lùi, F03 và F06-ALT1): `REVERSE_RESERVATION_NOT_MAINTAINED` (trước: `any(b>a)`);
  - `_reverse_forward`: `REVERSE_RESERVATION_NOT_MAINTAINED` trước khi vào số tới, `REVERSE_FORWARD_DIRECTION_INVALID` sau đó (trước: `b>a`, `b<a`);
  - `_creep_guard` (F05): `CREEP_DIRECTION_INVALID` (trước: `step<0`); `progress` = max đã đạt trừ gốc (≥ tổng ròng của v20, bảo thủ hơn
    với dự trữ 1 m);
  - consumer `metrics` (bộ dò sự kiện bò F05): dừng dò khi vi phạm bao (trước: dừng ở mọi bước giảm), `progress` như producer. Producer và
    consumer gọi cùng một hàm (bài học v20: lệch producer/consumer).
- Với `tolerance` = 0 hàm này đúng bằng luật cũ (test `test_zero_tolerance_is_the_v20_rule`).
- Không đổi: `metrics.py:781` (bước lùi phải có điều khiển lùi) và `:795` (`last_retreat`), tổng `retreat` (vẫn cộng mọi bước lùi, bảo thủ),
  mọi ngưỡng, bound, tham số prepare. F06-ALT1 dùng chung kernel lùi nên cũng chịu luật mới (không chạy F06).
- **Bỏ qua (công bố):** cho BLOCKED kết thúc episode. Đó là chi phí (một B bị chặn chạy tới tường 25 phút), không phải tính đúng.

## W2. Luật cũ vẫn được báo

Mỗi A/B dưới v21 được chấm cặp cả dưới v21 lẫn v20 (luật cũ dung sai 0), v18 (và v13 cho F05). Nếu consumer v20 từ chối, đó là kết quả theo
luật cũ. Kết quả v20 của F03-S1 (FAILED) và F05 (BLOCKED) giữ nguyên, không bị viết lại.

## W3. Cổng trước A/B (tooling, trên dữ liệu thật, chỉ quyết định của producer; không tính metric nào trên episode v20)

1. `tests/m56/test_v21_direction_envelope.py`: đỏ dưới v20, xanh dưới v21 (luật cũ = dung sai 0, nhiễu native đo được nằm trong dung sai,
   vượt dung sai vẫn hỏng, trôi chậm cộng dồn vẫn hỏng).
2. `native-v21-f03-gate.py`: điều phối thật của runner trên các khung 7557–7559 của F03 v20 B: dưới v20 BLOCKED (đối chứng âm), dưới v21 REVERSE.
3. `native-f05-v20-gate.py` trên 31 khung của F05 v20 (chạy lại) B: dưới v20 `CREEP_DIRECTION_INVALID` ở 3770 (đối chứng âm), dưới v21 không lỗi.
4. Bộ test F03/F05/F06/lùi/bò của product dưới v21 (chọn `-k`), kết quả ghi ở batch log.
5. Cổng đĩa (D > 80, E > 150, C ≥ 10 GB) và commit trống ≥ 32 GB trước mỗi lần bật CARLA; chạy lần lượt, một CARLA một lúc.

## W4. Artifact dùng lại nguyên byte

F03-S1: prepare r19d và REVF `m56_c0_partial_io_asel2f03prep_20261118T181450Z` (sha `fd6243...`). F05: prepare r18c và REVF
`m56_c0_partial_io_asel2f05prep_20261118T092923Z` (sha `e1b578...`). Không prepare lại, không diễn tập B.

## W5. Một A/B mỗi cảnh

Thứ tự: F05 trước (B ngắn hơn), rồi F03-S1. Mỗi cảnh một marker riêng ghi trước khi `room()` chờ. Bất kể B ra sao, báo như đã đo, không chạy lại.
Nếu hạ tầng cắt một A/B thì ghi lại và chờ Duy.
