# Erratum 1 cho runtime-recipe v2 (23/10/2026)

Bản đăng ký trước được sửa: `PREREG_M56_RUNTIME_RECIPE_V2_20261023.md` (sha256 `86e493a8…`, commit d1c91ac). File gốc giữ
nguyên. Erratum này được commit **trước** mọi lần chạy cảnh v2 nào: chưa có probe tốc độ, probe marker hay A/B nào.

Nguồn của mọi phát hiện dưới đây là probe G4 native `outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json`. Probe
đó chỉ đo năng lực, không chạy cảnh.

## E1. Cảm biến va chạm là thiết bị đo của runner, không thuộc ứng viên

Consumer đã đóng băng có hai yêu cầu cùng lúc:

- `_initialization_integrity` đòi actor của fixture đúng bằng {EGO, NPC};
- `_delivery_integrity` đòi registry có đúng 2 cảm biến, mỗi cảm biến trỏ tới id của một xe.

Hai yêu cầu chỉ thỏa được cùng lúc khi cảm biến **không** phải actor của cảnh. Vì vậy §2.1 của bản đăng ký trước đổi như
sau:

- Runner tự spawn một `sensor.other.collision` gắn vào mỗi xe, sau khi spawn xe và trước tick đầu tiên.
- Registry ghi `sensor_id → actor_id`.
- Ứng viên **không đổi** về phần cảm biến.

Đây là sửa phạm vi theo hướng thu hẹp: ứng viên được thêm ít thứ hơn.

## E2. Route lấy từ waypoint của bản đồ CARLA

Lane center tính từ XODR lệch waypoint CARLA tối đa **5,6 cm** trên route EGO của C01, vượt ngân sách xấp xỉ 0,05 m
(spec §5.1).

Route của fixture v2 vì vậy được dựng từ `Map.get_waypoint` / `Waypoint.previous` / `Waypoint.next`, bước 1/4 m:
- đi đúng các road id của route notation đã đóng băng;
- tại junction chọn connector theo road id;
- map hash là sha256 của `to_opendrive()`.

Route notation, vị trí xuất phát của EGO (arc 0) và các quy tắc độ dài không đổi.

## E3. Pose ban đầu (ngoại lệ sai khách quan, theo nguyên tắc 6)

**Phát hiện native:**
- Trước tick đầu, transform của xe mới spawn đọc ra toàn 0.
- Sau tick đầu, x, y, yaw bằng ảnh float32 của pose yêu cầu. Còn z đã giảm 1,8 mm và pitch là 0,007°, vì xe lắng
  xuống theo vật lý.

**Hệ quả:** Quy tắc consumer `a.pose == fixture.poses[role]` (khớp chính xác) không bao giờ thỏa được trên CARLA thật. Đây
đúng là loại sai khách quan mà sổ lấy làm ví dụ: "dung sai 1 micromet cho một chiếc xe đang lắng". Quy tắc này không
phải "hơi chặt".

**Quyết định** (Claude, dưới ủy quyền của Duy ngày 23/10/2026: "bạn hãy tự lựa chọn option đúng đắn nhất để hoàn thành
task m56"; được ghi công khai là đặt sau khi thấy số của probe năng lực, trước mọi A/B):

- **Quy tắc cũ, giữ nguyên văn:** pose quan sát đầu tiên == pose fixture.
- **Quy tắc mới:** pose quan sát đầu tiên khớp pose fixture khi đủ cả ba điều kiện:
  - x, y, yaw bằng ảnh float32 của pose fixture, sai khác ≤ 1e-4 (m hoặc độ);
  - `0 ≤ z_fixture − z_quan_sát ≤ 0,02 m` (khe spawn đã đo ngày 22/10: 5–20 mm);
  - |pitch| và |roll| ≤ 0,1°.
  - Tốc độ ban đầu vẫn phải là 0.
- Mọi kết quả được báo theo **cả hai** quy tắc. Theo quy tắc cũ, mọi episode native đều có `INITIALIZATION_INVALID`.

## E4. Những gì không đổi

Các mục sau không đổi:

- quy tắc canh pha (§3);
- probe và marker (§4);
- phạm vi C/L (§1);
- nhãn kết quả (§6);
- các ngưỡng tiếp xúc, mặt đất và thời gian của spec.
