# M56 v5 erratum 6: auditor chấp nhận lệnh NPC_TRAFFIC_HOLD hợp lệ của producer

**Trạng thái:** CLAUDE DECIDED UNDER DELEGATION. Duy duyệt trước bằng ủy quyền chung: "[chat] 26/10/2026: bây giờ tôi đi ngủ từ đây
đến 7h bạn tự quyết định làm theo lựa chọn bạn recommend cho tôi là được". Duy cần xác nhận hoặc bác lúc 7h. Mọi kết quả đều báo
theo cả quy tắc cũ và quy tắc mới.

**Nguồn gốc:** sửa đổi đặt **sau khi thấy** kết quả chạy lại theo erratum 5 (C02).

**Code:** nhánh `feat/m56-e6` (từ `feat/m56-e5`).

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## Lỗi (bên trong product, không phải ngưỡng)

Khi witness `npc_controls` không ở trạng thái CLEAR (NPC bị đèn hoặc biển giữ lại):
- **Producer** (`response.step_response`) phát lệnh với cause `NPC_TRAFFIC_HOLD`, target 0 và brake 0,3.
- **Hợp đồng stock** (`response.apply_intent`, dòng 137–139) chấp nhận đúng lệnh đó.
- **Auditor** (`evidence._target_integrity` và `_phase_integrity`) lại đòi cause phải là một phase của program, nên báo
  `TARGET_PROGRAM_MISMATCH` và `PHASE_PROGRAM_MISMATCH`.

Hai bên của cùng một hợp đồng đã đóng băng mâu thuẫn nhau. Đây là lỗi khách quan, không phải một ngưỡng.

| Episode | Lệnh giữ NPC | Kết quả audit cũ (e5) | Kết quả audit mới (e6) |
|---|---|---|---|
| C02-A (chạy lại theo erratum 5) | 41 | TARGET + PHASE mismatch | không còn |
| C02-B | 0 | sạch | sạch (không đổi) |
| M03-A (lần chạy erratum 3) | 527 | TARGET + PHASE mismatch | TARGET hết; PHASE còn* |

\* Phần PHASE còn lại ở M03-A là đúng: episode đó chạy online với consumer cũ, nên EGO không bao giờ đi tiếp; khi phát lại
theo e5 thì phase phải lệch. M03 đã có trong danh sách chạy lại theo erratum 5.

## Thay đổi

- `_target_integrity`: lệnh `NPC_TRAFFIC_HOLD` của NPC được so với target 0 km/h. Nó vẫn mismatch nếu khác 0 hoặc nếu actor là
  EGO.
- `_phase_integrity`: lệnh `NPC_TRAFFIC_HOLD` của NPC chỉ hợp lệ khi đủ ba điều kiện:
  - target 0 km/h;
  - witness `npc_controls` đã seal của chính frame phát lệnh có status khác CLEAR (kiểm bằng `_reverse_priority`, cùng hàm product
    vẫn dùng);
  - mọi witness ref đều được admit.

  Thiếu bất kỳ điều kiện nào thì vẫn là `PHASE_PROGRAM_MISMATCH`.
- Không đổi ngưỡng, producer, consumer event hay kernel F/I/O.

## Kiểm

- `tests/m56/test_v5_erratum6_traffic_hold.py`: hỏng với code cũ, qua với code mới.
- So audit cũ và mới trên dữ liệu thật như bảng trên (`outputs/m56_e6_check_{old,new}.log`).
- 303 test bị ảnh hưởng đều qua.

## Áp dụng

Chỉ là sửa auditor offline: hành vi online không đổi, nên **không cần chạy lại**. Các episode đã seal được đánh giá lại offline
(`native-v5-reeval.py` với `M56_CODE` trỏ tới e6). Kết quả ghi ra thư mục mới; kết quả cũ giữ nguyên.
