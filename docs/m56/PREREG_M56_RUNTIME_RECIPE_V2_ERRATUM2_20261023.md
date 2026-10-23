# Erratum 2 cho runtime-recipe v2 (23/10/2026)

Erratum này được commit **trước** mọi lần chạy cảnh v2. Bản đăng ký trước, erratum 1 và spec không đổi byte nào.

## E5. Tốc độ ở lần quan sát đầu tiên (ngoại lệ sai khách quan, theo nguyên tắc 6)

Theo E3 (erratum 1), tốc độ ban đầu phải đúng bằng 0. Dữ liệu native cho thấy điều này không thể đạt được.

**Dữ liệu:** Ở frame quan sát đầu tiên của lần chạy engineering ngày 22/10
(`m56_native_engineering_ab_20261022T070259Z`, `pre_observation_ref`), mỗi xe có tốc độ vz ≈ −0,029 m/s và vx ≈ −0,0006
m/s. Đây là chuyển động lắng của xe trong bước vật lý đầu tiên sau khi spawn.

**Hệ quả:** quy tắc `velocity == (0,0,0)` không bao giờ thỏa được trên CARLA thật, giống như quy tắc về pose ở E3.

**Quyết định** (Claude, dưới ủy quyền của Duy ngày 23/10/2026; đặt sau khi thấy số của lần quan sát năng lực, trước mọi
A/B của v2):

- Quy tắc cũ được giữ nguyên văn và vẫn được báo cáo.
- Quy tắc mới:
  - tốc độ ban đầu khai báo của actor vẫn phải là 0;
  - tốc độ quan sát được ở frame đầu tiên phải ≤ 0,10 m/s. Đây là đúng ngưỡng mà spec dùng cho settle và
    `STOP_CONFIRMED`; không có số mới.
- Code:
  - `m56/evidence.py::_initial_state_matches` hiện thực quy tắc mới, gồm cả pose theo E3;
  - `initial_state_old_rule` liệt kê các xe trượt quy tắc cũ, để báo cáo theo cả hai quy tắc.
