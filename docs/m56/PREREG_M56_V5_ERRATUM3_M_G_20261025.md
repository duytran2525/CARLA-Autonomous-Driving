# M56 v5, erratum 3: G và LrefN của các cảnh M mới theo spec §6.2 — BẢN NHÁP (25/10/2026)

**Trạng thái:** `DRAFT_AWAITING_DUY_APPROVAL`. Spec §6.2 ghi: "Changing LrefN/assumptions/G needs independent
rationale/version approval before an attempt, never outcome tuning". Vì vậy chưa chạy gì theo file này.

**Nhãn:** independent review waived by Duy 2026-10-24 (`CLAUDE_REVIEW_UNDER_DUY_DELEGATION`).

## Lỗi

Khi dựng M02–M08 (`native-v5-revision.py`), Claude đã:
- đặt **G = GL**, tức chuỗi `GL(k) = 4·(13/10)^(k−1)` của fill20 §4;
- **không** gán `LrefN`, nên khâu chuẩn bị canh pha NPC bằng giá trị mặc định 20 m.

Spec §6.2 định nghĩa G cho mọi cảnh C/L/M, có M01–M04 trong bảng §6.3 (M01: LrefN 51,69 m, G 46 m):

```text
G0 = vE²/(2·a_design) + vE·tau + vE·(LrefN + vehicle_length_budget + clear_budget)/(2·vN) + stop_margin
G  = ceil(G0 / 0,50 m) · 0,50 m
a_design 1,50; tau 0,50; vehicle_length_budget 4,50; clear_budget 0,50; stop_margin 0,50
LrefN = road/@length của connector NPC
```

## Sửa

| Mục | Quy tắc |
|---|---|
| vN | theo đúng chuỗi k đã đăng ký (fill v2/v3) |
| vE | 4 m/s (mainflow) |
| G | theo §6.2 |
| LrefN | `road/@length` của connector nhánh (NPC), đọc từ XODR |
| GL | không còn là G; chỉ còn dùng trong quy tắc độ dài của census, như đã đăng ký |

| Cảnh | vN (m/s) | LrefN (m) | G đã dùng (sai) | G theo §6.2 | Road vào mainflow (m) | Cần cho run-in (m) |
|---|---|---|---|---|---|---|
| M02 | 3,75 | 44,31 | 5,2 | 34,5 | 236,8 | 59,8 |
| M03 | 4,6875 | 18,45 | 6,76 | 18,0 | 45,5 | 43,3 |
| M04 | 5,859 | 18,54 | 8,79 | 16,0 | 49,9 | 41,3 |
| M05 | 7,324 | 30,26 | 11,42 | 17,5 | 65,2 | 42,8 |
| M06 | 2,4 | 18,28 | 3,08 | 27,5 | 87,6 | 52,8 |
| M07 | 1,536 | 16,25 | 1,82 | 35,5 | 113,1 | 60,8 |
| M08 | 1,92 | 11,26 | 2,37 | 25,0 | 33,8 | 50,3 |

**M08:** road vào ngắn hơn mức cần. Khâu chuẩn bị nối route ngược lên phía trước (`route_rows`); nếu vẫn không đủ thì cảnh
bị chặn `RUNIN_ROOM`. Không đổi G để lách.

## Hệ quả và cách chạy

1. Dựng lại M02–M08 với G và LrefN mới; chuẩn bị lại native (M04 cũng chuẩn bị lại, vì quy tắc canh pha thay đổi).
2. A/B **đúng một lần** cho mỗi cảnh M đã PREPARED. Lần chạy này thay cho lần chạy lại được phép do lỗi harness/recipe
   (P5).
3. Mọi lần A/B M trước đây (v5d, đêm 24–25/10, và M08 ngày 25/10) được giữ nguyên làm hồ sơ, với nhãn "recipe defect: G =
   GL, LrefN default".

## Thời điểm

Lỗi được phát hiện **sau khi thấy** kết quả A/B của M08: NPC đi qua vùng xung đột 6 s trước khi EGO tới. Tuy vậy, bản sửa
là áp đúng một quy tắc spec đã có sẵn, không phải chọn giá trị mới. Mọi kết quả được báo theo cả recipe cũ lẫn recipe mới.
