# M56: đăng ký trước v5 (consumer, PID của NPC, miễn review độc lập) (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, người dùng tự xác nhận là Duy, trả lời các câu hỏi:

| Câu hỏi | Duy chọn |
|---|---|
| Mục tiêu | "Release đầy đủ §11" |
| Duyệt | "Consumer v5", "PID tốc độ cao", "Bổ sung cảnh tới 46" |
| PID | "Hiệu chỉnh PID riêng NPC" |
| Reviewer | "khỏi cần người khác bạn tự review" |

**Thứ tự:** file này được commit trước mọi thay đổi code và mọi lần chạy dùng nó.

**Bản chất các thay đổi:** tất cả đều **đặt sau khi đã thấy số native** (từ v2 tới v4). Các quy tắc cũ được giữ nguyên văn,
và mọi kết quả báo theo cả quy tắc cũ lẫn quy tắc mới. Không có ngưỡng metric nào đổi: Delta 0,20, D09, contact
0,20/0,15/0,05, readiness 0,10/0,50 s, horizon 60/76,5 s, deadline 300 s/5 s.

## R0. Review

- Duy miễn review độc lập.
- Mọi review (fixture, W05, D09, C0, release) là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, **không độc lập**.
- Mọi kết quả và mọi bản release mang nhãn "independent review waived by Duy 2026-10-24".
- Spec §11 đòi review độc lập. Vì vậy một release theo v5 là "release theo §11, có miễn trừ review độc lập", không phải
  release đầy đủ theo §11.

## C1. Run-in theo khoảng cách route

**Áp dụng cho:** `evidence._initialization_integrity` (khoảng cách run-in lúc ready).

| | Nội dung |
|---|---|
| Cũ | `-max(section_margin(EGO body, e_entry)) > G`, tức khoảng cách tới mặt phẳng |
| Mới | `e_entry.route_station − max(station trên route EGO của các đỉnh thân EGO) > G`, tức khoảng cách theo route |

Phát hiện native: ở L01, EGO đi vào hộp qua mặt bên, nên khoảng cách mặt phẳng là 0,24 m trong khi khoảng cách route là
32,8 m.

## C2. Normative I/O đọc tốc độ danh nghĩa của response

**Áp dụng cho:** `response._normative_contract`, các nhánh O-A, O-B, I-A, I-B.

| | Nội dung |
|---|---|
| Cũ | `nominal = readiness.targets_mps['EGO']` |
| Mới | `nominal = response.targets['NOMINAL']`. Tập giá trị được phép {6, 7,5, 9,375} không đổi. |

Lý do: theo E6, target readiness là mức ổn định đo được, nên không thể bằng đúng tốc độ danh nghĩa.

## C3. Lateral contract trên route thật

**Áp dụng cho:** `response._lateral_contract`.

| | Nội dung |
|---|---|
| Cũ | route reference phải có đúng 2 điểm, thẳng theo trục +x |
| Mới | route reference là route fixture (waypoint CARLA, mỗi bước ≤ 0,25 m). Đoạn route chứa mọi segment đổi làn phải thẳng: tổng biến thiên heading ≤ 1° trên đoạn đó. |

**Bề rộng và độ tách làn:** đo bằng `lane_width` CARLA và khoảng cách tâm làn, ghi trong `topology.lane_geometry`, được
review như các proof khác.

**Các kiểm tra giữ nguyên:**
- quintic arc;
- độ dài `3·nominal`;
- độ tách = khoảng cách tâm làn;
- các guard REFERENCE_MARKER.

**Trường hợp ngoài phạm vi:** đường cong vẫn là UNSUPPORTED.

## C4. Vùng xung đột rời có review

**Áp dụng cho:** `geometry.compile_fixture`.

| | Nội dung |
|---|---|
| Cũ | các phần giao rời nhau → `DISCONNECTED_CONFLICT_REVIEW_REQUIRED` |
| Mới | được nhận khi có proof `CONFLICT_COMPONENT_SELECTION` đã review |

**Quy tắc chọn thành phần:**
- chọn thành phần chứa điểm gần nhau nhất của hai tâm route;
- các thành phần khác phải cách ≥ 5 m theo route của cả hai xe, nếu không → BLOCKED;
- vùng (domain) bao đúng thành phần đã chọn.

## P-NPC. Hiệu chỉnh PID dọc của NPC

**Phạm vi:**
- chỉ NPC, là chương trình phụ lục tạm, không vào catalog;
- EGO giữ PID gốc theo spec §6.1;
- product: cấu hình stock của NPC đọc `longitudinal_control_dict` từ policy đã review, nếu có; nếu không có thì dùng gốc.

**Probe hiệu chỉnh** (chuẩn bị, không phải A/B):
- NPC đi trên route probe 1 của chính cảnh, target vN, nhả lúc CAPTURE_START + 21/20 s.
- **Lưới thử theo thứ tự cố định:**
  1. (K_P, K_I, K_D) = (1,0; 0,05; 0) gốc
  2. (0,5; 0,05; 0)
  3. (0,3; 0,05; 0)
  4. (0,5; 0,2; 0)
  5. (0,3; 0,2; 0)
  6. (0,2; 0,1; 0)
- **Chọn:** bộ đầu tiên trong lưới có một cửa sổ 2 s (NPC không bị giữ, tốc độ > 0,5) với biên độ ≤ 0,10 m/s, xuất hiện trước
  thời điểm NPC phải có mặt.
- Không bộ nào đạt → `READINESS_NOT_STEADY`.
- Tham số được chọn ghi vào policy của NPC và vào phụ lục.

## Phần chưa thuộc bản này

Catalog fill v2 (bổ sung tới 46 cảnh, ≥ 23 junction) có **đăng ký trước riêng**, viết và commit trước bất kỳ census nào.
