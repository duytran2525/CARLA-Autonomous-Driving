# Erratum 3 cho runtime-recipe v2: mốc readiness (23/10/2026)

## Thẩm quyền

Quyết định này đặt **sau khi đã thấy số của probe năng lực**, và trước mọi A/B.

[chat] 23/10/2026, người dùng tự xác nhận là Duy, chọn phương án (a) cho câu hỏi sau:

> Với PID gốc, readiness (|v − đích| ≤ 0,10) không bao giờ đạt trên CARLA thật (EGO 3,863/4 m/s, 1,887/2 m/s). Bạn
> chọn cách nào? … Đồng thời xin bạn phê chuẩn E3/E5.

Phương án (a) nguyên văn:

> (a) Đích = mức ổn định đo: mốc readiness của mỗi xe = tốc độ ổn định đo được của PID gốc trong probe (vd 3,863),
> dung sai 0,10 giữ nguyên; tốc độ danh nghĩa 4/2 của chương trình không đổi. Phê chuẩn E3/E5. Chạy tiếp G4 + A/B
> cho các cảnh qua được.

Như vậy E3 và E5 (erratum 1 và 2) đã được Duy phê chuẩn.

## Dữ liệu dẫn tới quyết định

Nguồn: probe 1 Town04, `outputs/m56_v2_prepare_Town04_20261023T*`.

| Xe | Đích | Tốc độ ổn định đo được |
|---|---|---|
| EGO (C) | 4 m/s | 3,863 m/s |
| EGO (L) | 2 m/s | 1,887 m/s |
| NPC | 3 m/s | 2,87 m/s |

**Nguyên nhân có tính cấu trúc:** PID dọc gốc trong `E:/Carla/PythonAPI/carla/agents/navigation/controller.py` chỉ
lấy tổng sai số của 10 mẫu cuối (`_error_buffer = deque(maxlen=10)`; `_ie = sum(self._error_buffer) * self._dt`). Tức
là không có tích phân thật, nên luôn còn sai số tĩnh. Spec §6.1 cấm sửa PID.

## E6. Quy tắc mới, thay §4 của bản đăng ký trước

Quy tắc cũ (§2.3 và §4) giữ nguyên văn. Mọi kết quả báo theo cả hai quy tắc; theo quy tắc cũ, mọi episode C/L có
`READINESS_NOT_REACHED`.

1. **Cửa sổ trước TRIGGER của probe:**
   - `T_end` là frame đầu tiên mà mặt trước EGO cách `e_entry` không quá `G + 1 m`.
   - Cửa sổ là `[T_end − 2 s, T_end]`.
2. **Mức ổn định** của mỗi xe là tốc độ trung bình trong cửa sổ trên, làm tròn tới 1/1000 m/s.
   - Nếu biên độ tốc độ (max − min) trong cửa sổ lớn hơn 0,10 m/s → BLOCKED_FIXTURE, lý do `READINESS_NOT_STEADY`.
3. **Mục tiêu readiness:** `readiness.targets_mps` = mức ổn định của từng xe. Tốc độ danh nghĩa trong response (EGO
   4/2, NPC vN) không đổi.
4. **Canh pha** (§3):
   - `t_E = T_end + (G + 1) / v_E`, với `v_E` là mức ổn định của EGO;
   - trong `t_N = t_E − (LrefN + 5)/(2·v_N)`, `v_N` là mức ổn định của NPC;
   - `d_N(t)` vẫn là quãng đường NPC đo được trong probe 1.
5. **T_r và marker** (lấy từ probe 2):
   - `T_r` là frame sớm nhất thỏa vị từ readiness của chính runner (`runtime._ready`: 11 frame liền, 0,50 s;
     |v − mức ổn định| ≤ 0,10; station bám marker − mức ổn định·Δt trong ±0,10), khi lấy marker bằng station tại
     chính frame đó;
   - marker = station tại `T_r`, làm tròn tới 1/1000 m;
   - kiểm `RUNIN_ROOM` như cũ: mặt trước EGO tại `T_r` phải cách `e_entry` hơn `G + 1 m`.
6. **Không có lần thử thứ hai:** nếu A/B không tái lập marker trong ±0,10 m thì ghi nguyên `READINESS_NOT_REACHED`,
   không probe lại.

## Không đổi

Vẫn giữ nguyên:

- dung sai 0,10 m/s;
- hold 0,50 s;
- thời hạn 15 s;
- PID gốc;
- các tốc độ danh nghĩa;
- phạm vi C/L;
- mọi ngưỡng tiếp xúc và thời gian.
