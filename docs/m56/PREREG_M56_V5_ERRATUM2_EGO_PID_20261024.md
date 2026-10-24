# M56 v5, erratum 2: lưới PID dọc cho EGO khi PID gốc không ổn định (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, người dùng phiên này (trước đó tự xác nhận là Duy) chọn "Lưới PID cho EGO". Mô tả của
lựa chọn:

> Dùng cùng lưới với NPC, thử PID gốc trước; chỉ đổi ở cảnh mà PID gốc không ổn định. Đây là thay đổi §6.1, ghi công
> khai, báo theo cả hai quy tắc. Cái giá: bộ điều khiển EGO khác nhau giữa các cảnh, ảnh hưởng tính so sánh giữa cảnh
> của I/O.

Review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`: independent review waived by Duy 2026-10-24.

**Thời điểm:** quy tắc được đặt **sau khi thấy số** của probe native báo cáo:
- `outputs/m56_ego_pid_probe_20261024T151157Z.json` và `…T152143Z.json`, trên một đoạn thẳng 860 m ở Town06;
- PID gốc của EGO dao động 0,14–2,1 m/s trong dải 4,8–11,7 m/s, và ổn định ở 3,84, 4, 14,6, 18,3 m/s.

Chưa có cảnh I/O nào từng được chuẩn bị native. File này được commit trước code.

## Quy tắc

| Mục | Quy tắc |
|---|---|
| Cũ (§6.1) | EGO luôn dùng PID dọc gốc (K_P 1, K_I 0,05, K_D 0) |
| Mới | lưới cố định giống P-NPC: (1; 0,05; 0) gốc → (0,5; 0,05; 0) → (0,3; 0,05; 0) → (0,5; 0,2; 0) → (0,3; 0,2; 0) → (0,2; 0,1; 0) |
| Chọn | bộ đầu tiên mà cửa sổ E6 của EGO (2 s trước T_end ở probe 1) có biên độ ≤ 0,10 m/s |
| Không bộ nào đạt | `READINESS_NOT_STEADY` |

- **PID gốc vẫn là lựa chọn đầu.** Cảnh nào PID gốc đạt thì không đổi gì; đó là mọi C/L/M hiện có, vì EGO chạy 2–4 m/s.
- **Product:** khóa binding `ego_longitudinal` chỉ cho EGO, cùng kiểm tra như `npc_longitudinal` (dt 1/20, số chính xác).
  Không có khóa thì dùng PID gốc.
- **Ghi lại:** tham số được chọn ghi vào policy của EGO, vào file chuẩn bị và vào báo cáo của từng cảnh.

## Báo cáo theo hai quy tắc

| Quy tắc | Cảnh dùng PID khác gốc |
|---|---|
| Cũ | `READINESS_NOT_STEADY` |
| Mới | kết quả A/B, kèm nhãn "EGO PID per erratum 2: (K_P, K_I, K_D)" |

Phép so giữa các cảnh I/O ghi rõ cảnh nào dùng bộ điều khiển EGO nào.

## Ngoài phạm vi

- PID ngang của EGO không đổi.
- Các giới hạn ga, phanh, lái không đổi.
- Ngưỡng readiness 0,10 m/s / 0,50 s không đổi.
