# M56: đăng ký trước runtime-recipe v3 (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, người dùng tự xác nhận là Duy:

> viết đăng ký trước v3: (1) phiên bản response EGO mới dùng route waypoint ≤0,25 m, (2) vùng xung đột theo bề rộng làn
> để mặt cắt clear đủ rộng; rồi chuẩn bị và chạy A/B C01, C02 một lần.

**Thứ tự:** file này được commit **trước** mọi lần chạy native của v3.

**Quan hệ với các tài liệu khác:** v3 kế thừa nguyên v2 cùng các erratum E1–E6 (d1c91ac, 737acbc, 94c56b3) và
signal-phase v1 cùng erratum 1–3 (b4b6a22, 59744b3, 425e8b1, 00221e5). Chỉ những mục dưới đây thay đổi.

**Phạm vi:**
- Chỉ C01 và C02, hai cảnh PREPARED ở C0 partial v2.1.
- Mỗi cảnh chạy **đúng một** A/B. Có gì ghi nguyên đó, không chạy lại, không chỉnh sau khi thấy kết quả.

**Reviewer:** mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, không độc lập.

## V3.1. Phiên bản response EGO mới

- **Chỉ thay route:** response EGO A và B của mỗi cảnh giữ nguyên `targets`, `profile` và `phases`, khớp từng byte với
  bản đóng băng ở C0.
- **Route mới:** `route` được thay bằng đúng route EGO của fixture, tức chuỗi waypoint CARLA theo notation đã đóng băng
  (E2), với mọi dây cung ≤ 0,25 m.
- **Hash:** tính lại theo quy tắc `hashed()` của `catalog-recipes.py`.
- **Lý do:** consumer đã đóng băng đòi `response.route == fixture.routes[EGO]` (`OFFSET_ROUTE_MISMATCH`) và đòi route của
  plan trùng route của response (`PLAN_SOURCE_WITNESS_INVALID`). Route XODR lấy mẫu 1 m của C0 không thể đồng thời
  compile được và trùng route fixture.
- **Nhãn:** ứng viên bị đổi sau C0. Duy duyệt ngày 24/10, ghi công khai trong revision C0 partial v3.

## V3.2. Vùng xung đột theo bề rộng làn

- **Định nghĩa:** gọi `O` là hộp AABB của phần giao các swept volume EGO∩NPC, và `W` là `lane_width` lớn hơn trong hai
  làn EGO và NPC. `lane_width` lấy từ waypoint CARLA của mỗi route tại điểm gần tâm `O` nhất.
- **Quy tắc:** vùng `R` là `O` được nới **đối xứng quanh tâm** theo x và theo y, sao cho mỗi chiều ngang ≥ `W + 1,0 m`.
  Chiều đứng ±1 m như v2.
- **Lý do:** mặt cắt clear rộng ~2 m (≈ thân xe 1,79 m) khiến phép kiểm hành lang không bao giờ đạt. Vùng mới chứa
  trọn `O`, nên mọi kiểm tra của `compile_fixture` vẫn áp dụng y nguyên. Nếu route cắt góc hoặc cắt mơ hồ thì cảnh bị
  BLOCKED_FIXTURE.

## V3.3. Route NPC phía hạ nguồn

- **Phát hiện:** ở v2.1, NPC chạy hết plan khi episode còn chạy, và LocalPlanner gốc trả về phanh khẩn (1,0 > 0,3).
- **Quy tắc:** route NPC kéo dài qua cửa ra junction thêm `min(sẵn có, 15 + 60 · vN)` m, theo các liên kết làn với quy
  tắc đi thẳng (xoay ít nhất).
- **Destination của NPC:** không đổi, vẫn là cửa ra + 5 m.

## V3.4. Chuẩn bị lại và A/B

- **Chuẩn bị:** chạy lại theo v2 §3–§4, E6 và signal-phase v1 cho C01 và C02 với V3.1–V3.3. Probe, mức ổn định, marker
  và vị từ pha được tính lại.
- **Kit:** dùng bản đã sửa ngày 24/10 (nguồn recipe là JSON). Bản này chưa từng được dùng cho A/B nào.
- **C0 partial v3:** = v2.1 với C01 và C02 thay theo V3.1–V3.3.
- **A/B:** mỗi cảnh chạy đúng một lần. Báo cáo ghi ba trục và các lý do, theo cả quy tắc cũ lẫn mới khi có.
