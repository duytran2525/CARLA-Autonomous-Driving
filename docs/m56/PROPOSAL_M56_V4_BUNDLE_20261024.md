# M56: gói đề xuất v4 cho 1 tuần "partial native" (24/10/2026, chờ Duy duyệt)

**Mục tiêu do Duy chọn:** "Partial native". Trong 1 tuần, càng nhiều cảnh trong 31 cảnh của C0 partial có A/B native thật càng
tốt, kèm báo cáo cuối cho từng cảnh.

**Nằm ngoài mục tiêu:**
- đủ 46 cảnh và 23 junction;
- review độc lập;
- export catalog.

**Cách duyệt:** mỗi mục dưới đây được duyệt riêng. Mục nào được duyệt sẽ vào **prereg v4**, commit trước mọi lần chạy
dùng nó. Mục nào không được duyệt thì cảnh liên quan giữ BLOCKED.

**Mọi thay đổi quy tắc ở đây đều đặt sau khi đã thấy số** (probe, A/B v2.1, A/B v3). Chúng được ghi công khai, báo cáo theo
cả hai quy tắc, và không đụng tới ngưỡng metric nào (Delta 0,20, D09, contact, readiness 0,10).

## P1. NPC nhanh: đo mức ổn định trong cửa sổ của chính NPC (C/L)

- **Hiện tại (E6):** mức ổn định đo trong cửa sổ trước TRIGGER của EGO. NPC nhanh (vN ≥ 5,9 m/s) vẫn đang tăng tốc trong
  cửa sổ này, nên bị `READINESS_NOT_STEADY`. Đây là nguyên nhân chặn C04, C05, L01, L03, L04, L06, L07, L08.
- **Đề xuất:**
  - mức ổn định của NPC = tốc độ trung bình trong 2 s cuối trước `t_N` ở probe 1, khi NPC không bị giữ và biên độ
    ≤ 0,10;
  - EGO giữ nguyên E6;
  - T_r và marker giữ nguyên E6.5. Cả hai xe phải ổn định; nếu không thì `RUNIN_ROOM` hoặc `READINESS`.

## P2. Thời gian chờ pha đèn ≥ một chu kỳ

- **Hiện tại:** spec §484 cho chờ ≤ 60 s. Chu kỳ quan sát được là 60,4 s, nên một số điểm neo bị `BLOCKED_SIGNAL_ADMISSION`
  tùy lúc bắt đầu chờ.
- **Đề xuất:** chờ ≤ max(60 s, chu kỳ quan sát được + 2 s). Vẫn không săn pha, không reload, không đổi đèn.

## P3. Runtime recipe cho I/O, M01, F

- **O (6 cảnh):**
  - NPC đi trước ở 2,5 m/s không đổi (spec §6.1, §7.4), chương trình phụ lục tạm;
  - EGO giữ chương trình đã đóng băng;
  - `action_regions` và các mặt cắt lấy từ làn CARLA theo cách của V3.
- **I (6 cảnh):** spec ghi việc thả NPC tương tác là **PROVISIONAL**. Đề xuất dùng đúng chương trình NPC đề xuất của spec
  §7.4 làm phụ lục tạm, gắn nhãn PROVISIONAL trong mọi kết quả.
- **M01:** proof `MERGE_TRANSITION` lấy từ hình học connector CARLA, với vùng chuyển tiếp là hộp theo bề rộng làn như V3.2.
- **F (F01, F04):**
  - F04 cần proof cho cửa xe mà spec §5.4 chưa có, nên đề xuất ghi `BLOCKED_CAPABILITY` ngay;
  - F01 dùng chương trình NPC đề xuất của spec §8, nhãn PROVISIONAL.

## P4. Hai cảnh có vùng xung đột rời nhau (C03, L02)

**Đề xuất: giữ BLOCKED.** Muốn gỡ thì phải sửa compiler đã đóng băng để cho chọn thành phần có review. Việc đó tốn
thời gian mà chỉ thêm được 2 cảnh.

## P5. Quy trình trong tuần

- **Full suite:** chỉ chạy một lần ở cuối tuần. Mỗi thay đổi trong tuần chạy test nhắm vào phần đổi.
- **Chạy native:** nối tiếp tự động, kể cả ban đêm.
- **Số lần A/B mỗi cảnh:**
  - mặc định đúng một lần;
  - được chạy lại **tối đa một lần** chỉ khi lỗi nằm ở harness hoặc tooling của Claude, không phải ở cảnh. Điều kiện là
    lỗi phải được chứng minh offline trên dữ liệu đã seal, kèm commit sửa, và cả hai lần chạy đều được báo cáo.
- **Lỗi của cảnh** (vật lý, event, metric) thì không bao giờ chạy lại.

## P6. Tooling (không phải quy tắc, chỉ ghi công khai)

- Sửa route builder cho C06, L05, C07, C08.
- Làm đa giác vùng lái chính xác hơn, để phân biệt lỗi công cụ với vi phạm mép đường thật.
- Tăng tốc phần đánh giá offline mà không đổi ngưỡng.
