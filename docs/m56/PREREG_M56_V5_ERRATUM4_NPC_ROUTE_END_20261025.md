# M56 v5, erratum 4: route NPC dừng trước khúc cua vượt ngân sách ngang — BẢN NHÁP (25/10/2026)

**Trạng thái:** `DRAFT_AWAITING_DUY_APPROVAL`. Quy tắc này đặt **sau khi thấy** kết quả A/B v5 của C01 và C05. Kết quả
được báo theo cả recipe cũ lẫn recipe mới.

**Nhãn:** independent review waived by Duy 2026-10-24 (`CLAUDE_REVIEW_UNDER_DUY_DELEGATION`).

## Phát hiện

Bộ kiểm consumer (`evidence._motion_integrity`) đòi gia tốc ngang tham chiếu, tức v_đích² · κ tính trong cửa sổ ±10 m quanh
vị trí xe, không vượt 2,5 m/s². Nếu vượt thì `REFERENCE_LATERAL_BUDGET_UNPROVEN`.

Trong recipe v2 (tooling của Claude), route NPC kéo dài 15 m + 60 s · vN sau junction, chạy ở tốc độ không đổi, và NPC
vẫn chạy tiếp sau đích của chính nó. Ở hai cảnh, NPC đi vào một khúc cua **sau** vùng xung đột:

| Cảnh | Ảnh hưởng | n_exit | Đích NPC | Khúc cua | v² · κ |
|---|---|---|---|---|---|
| C01 | chỉ action A | 34,4 m | 46,2 m | arc 84,2 m | 2,55 m/s² |
| C05 | cả A và B | 75,7 m | — | arc 164 m | 4,0 m/s² |

Ở cả hai cảnh, mọi event của cảnh (TRIGGER … DESTINATION_CONFIRMED) đều đã có. Ví dụ, C01-B (NPC không tới khúc cua)
được kết luận **WITNESS_VALID, physical COMPLETE**.

## Quy tắc mới

| Mục | Quy tắc |
|---|---|
| Cũ | route và plan NPC dài 15 m + 60 s · vN sau junction |
| Mới | route và plan NPC kết thúc tại s_end = (station đầu tiên sau đích NPC mà vN² · κ(s) > 2,5 m/s²) − 10 m − 1 m. Nếu không có station nào như vậy thì giữ độ dài cũ. κ đo bằng chênh yaw waypoint CARLA như kit. |
| Bắt buộc | s_end ≥ đích NPC + 5 m (chỗ dành cho đích, như compile đòi); nếu không thì `BLOCKED_FIXTURE NPC_ROUTE_CURVATURE`. |

**Áp dụng:** cho mọi cảnh C/L/M. Việc cắt route NPC áp vào route đã chuẩn bị, nên phải chuẩn bị lại các cảnh bị ảnh hưởng.

## Chạy lại

Đây là lỗi recipe/harness đã được chứng minh: phần đuôi route NPC vô nghĩa với tương tác nhưng làm hỏng phép kiểm. Theo P5:
- những cảnh mà một action bị chặn **chỉ** bởi `REFERENCE_LATERAL_BUDGET_UNPROVEN` do khúc cua sau đích NPC được A/B lại
  **đúng một lần**, với recipe mới;
- kết quả cũ giữ nguyên làm hồ sơ.

## Không đổi

Ngưỡng 2,5 m/s², cửa sổ 10 m, mọi ngưỡng metric, và tốc độ NPC trong phần tương tác đều giữ nguyên.
