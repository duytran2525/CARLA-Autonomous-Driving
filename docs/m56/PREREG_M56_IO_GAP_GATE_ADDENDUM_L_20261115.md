# M56 A-SEL2 addendum L: cổng gap thực tại t0 cho I/O (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này [chat] 15/11/2026: "trong khi đợi chạy full suite thì tiếp tục sửa các cảnh còn lại đi".

**Tính chất:** luật **sau khi thấy số** (nguyên tắc 6). Ngưỡng **không mới**: recipe io-v1
(`PREREG_M56_IO_RECIPE_V1_20261026.md`, mục "Gap lúc t0") đã đặt trước "|gap − spec| ≤ 0,5 m". Code chưa bao giờ kiểm ngưỡng
đó. Addendum này chỉ thêm phần kiểm, trước mọi bước native tiếp theo.

## 1. Lỗi tìm thấy

- `native-io-prepare.py` dòng 377–379:
  - shift = decision trên làn NPC + gap − đuôi NPC lúc t0 ở probe 1;
  - điểm xuất phát NPC là hàng đầu tiên **trên road site R** ở tại hoặc sau s_n.
- Nếu shift âm và s_n nằm trước đầu road R, NPC bị kẹp ở đầu road R. Gap thực lớn thêm đúng |shift|.
- Không cổng nào so `gap_at_t0_probe2` với gap catalog.
- Gap lúc TRIGGER đo trong episode B bằng `gap_at_t0_probe2` trừ 0,4–0,8 m ở cả sáu cảnh I đã seal. Vậy prepare.json dự báo được
  gap thật, còn gap catalog thì không.
- Số liệu: `outputs/m56_i_gap_fidelity_20261115.txt`, quét mọi prepare I/O: `outputs/m56_io_gap_sweep_20261115.txt`.

| Cảnh | gap catalog | gap thực (probe 2) | shift | Kết quả đã ghi |
|---|---|---|---|---|
| I04 | 13,18 | 46,42 | −33,60 | PASS |
| I02-S2 | 7,80 | 27,36 | −19,63 | BLOCKED_WITNESS |
| I01-S1 | 6,00 | 21,37 | −15,40 | NO_PAIR (chưa A/B) |
| I05-S1 | 4,62 | 11,08 | −6,69 | FAILED |
| O08-S2 | 55,69 | 58,94 | −63,35 | FAILED (lỗi sep, addendum K) |

- Mọi prepare O khác và I03, I06, I07, I07-S1: |lệch| ≤ 0,42 m.

## 2. Cổng

- `asel2-io-gap-gate.py PREP/SCENE`: đọc `prepare.json`.
  - `GAP_OK` khi |gap_at_t0_probe2 − geometry.gap| ≤ 0,5 m.
  - Ngược lại `GAP_NOT_REALISED`. Không có file hoặc không có gap thì `GAP_UNKNOWN`. Fail closed.
- Gọi trong `run-asel2-io-v16.sh` và `run-asel2-io-i12j.sh`, ngay sau kiểm `PREPARED`, trước compile và A/B. Bị chặn thì cảnh không
  tốn A/B.
- Tự kiểm trên dữ liệu cũ: chặn I04, O08-S2, O04-S2 (không có gap); cho qua I03, O04, O05-S1, O06, O07-S2.

## 3. Không làm ở đây

- Không đổi status của I04, I02-S2, I05-S1. Việc I04 PASS khi gap thực 46 m (vi phạm dung sai đã đăng ký) do người dùng quyết.
- Không sửa cách đặt NPC. Sửa (cho NPC xuất phát trên road trước R, hoặc đòi chỗ lùi ở cổng site offline) cần recipe mới.
- Cảnh I successor (I05-S2…I08-S2) chưa có prepare, nên chưa biết gap thực của chúng.
