# M56: probe kiểm `no_rendering_mode` của CARLA (25/10/2026)

**Thẩm quyền:** [chat] 25/10/2026, Duy: "cho bật no_rendering_mode của CARLA cho các lần chạy từ giờ (không có camera nên
không ảnh hưởng metric); ghi công khai trong receipt mỗi lần chạy, và kiểm trước trên một probe rằng vật lý và đèn giao thông
không đổi".

**Probe:** `native-render-probe.py` (commit `831eeab`). Output: `outputs/m56_render_probe_20261025T154927Z.json` và ba file
trial đi kèm.

**Thiết lập:**
- Town04, đồng bộ dt 0,05 với substep 0,01 × 10 như runner.
- EGO là BasicAgent gốc ở 6 m/s (vùng PID dao động, nhạy nhất); NPC là LocalPlanner gốc ở 4 m/s.
- 800 tick, ghi lại 43 đèn giao thông.
- Ba lần thử, mỗi lần một server CARLA mới và một tiến trình Python mới: render bật, render bật, render tắt.

## Sự cố trong lúc chạy (đã sửa)

- **Crash khi nạp lại map:** ở bản đầu của probe, việc nạp lại Town04 trong cùng một server làm CARLA crash hai lần
  (`EXCEPTION_ACCESS_VIOLATION`, cùng call stack; đó là các hộp thoại "Fatal error" Duy thấy). Bản sửa dùng một server mới cho
  mỗi lần thử.
- **Client chết khi dùng server thứ hai:** một tiến trình Python dùng server thứ hai thì client chết không để lại lỗi. Bản
  sửa dùng một tiến trình riêng cho mỗi lần thử.
- Tool chuẩn bị và A/B vốn chỉ dùng một server cho mỗi tiến trình, nên không bị ảnh hưởng.

## Kết quả

### Theo tiêu chí viết trước khi chạy: `pass: false`

Tiêu chí: lệch giữa render tắt và render bật ≤ lệch giữa hai lần bật + 1e-6, và chuỗi trạng thái đèn giống nhau ở mọi tick.

| So sánh | Lệch vị trí EGO | Lệch vị trí NPC | Tick có đèn khác nhau |
|---|---|---|---|
| bật₁ vs bật₂ (nền) | 0,334 m | 0,2005 m | 800/800 |
| bật₁ vs tắt | 0,334 m | 0,2008 m | 800/800 |

Tiêu chí này có hai lỗi thiết kế, do Claude viết:
- **Đèn:** mỗi server mới khởi động đèn ở một pha khác nhau, nên ngay cả hai lần bật cũng khác nhau ở mọi tick. So trạng thái
  tuyệt đối không đo được điều cần đo.
- **Nền:** chỉ có một mẫu, trong khi CARLA lệch giữa các lần khởi động (bật₁ vs bật₂ đã lệch 0,33 m).

### Phân tích đã sửa (đặt sau khi thấy số, ghi công khai)

| So sánh | EGO | NPC |
|---|---|---|
| bật₂ vs tắt | **giống từng bit ở 800/800 tick** (lệch 0,000000 m) | lệch tối đa 0,022 m |
| bật₁ vs bật₂ | lệch 0,334 m, 0/800 tick giống | lệch 0,2005 m |
| bật₁ vs tắt | lệch 0,334 m | lệch 0,2008 m |

- **Đèn:** độ dài pha (bỏ pha dở đầu và cuối) giống hệt ở cả ba lần thử: xanh 200 tick, vàng 61 tick.
- **Tốc độ:** sau tick 400, lần tắt render có trung bình và biên độ trùng chính xác với bật₂ (EGO 5,7959 / 0,4774 m/s; NPC
  3,8566 / 0,0029 m/s).

**Kết luận:** tắt render không làm đổi vật lý hay chu kỳ đèn, vượt quá mức dao động vốn có giữa các lần khởi động CARLA. Lần
tắt render trùng hẳn với một lần bật. Theo điều kiện của Duy, từ 25/10/2026 Claude bật `no_rendering_mode`
(`M56_NO_RENDER=1`) cho các lần chạy. Mỗi receipt A/B và mỗi file chuẩn bị ghi `carla_no_rendering_mode`.

**Nhãn:** independent review waived by Duy 2026-10-24 (`CLAUDE_REVIEW_UNDER_DUY_DELEGATION`).
