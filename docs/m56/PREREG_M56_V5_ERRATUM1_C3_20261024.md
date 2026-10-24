# M56 v5, erratum 1: các quy tắc C3 mà bản đăng ký trước chưa nói (24/10/2026)

**Thẩm quyền:** Claude, dưới ủy quyền của Duy ngày 24/10/2026 (đã duyệt "Consumer v5"). Đây là
`CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, không độc lập: independent review waived by Duy 2026-10-24.

**Thời điểm:** các quy tắc dưới đây được đặt **sau** khi v4 bị chặn native, nhưng **trước** mọi số I/O của v5. Chưa có cảnh
I/O nào từng được chuẩn bị native. File này được commit trước code C3 và trước mọi lần chuẩn bị I/O.

**Lý do phải viết thêm:** C3 trong bản đăng ký trước (eda7680) chỉ đổi route gốc. Có ba chỗ code khác vẫn giả định route
2 điểm theo trục +x:
- `_reference_response`: phép chuyển sang route làn đích đòi `old.arc == new.arc` và `y + offset == y mới` đúng tuyệt đối,
  điều mà hai route làn CARLA khác nhau không bao giờ thỏa;
- metric (`metrics._in_action_region`) và `geometry._is_box`: hộp làn là hộp thẳng theo trục thế giới;
- dấu của độ tách: ở route trục +x, dấu lấy được từ tâm y của hai hộp.

Không có ngưỡng metric nào đổi.

## E1-a. Chỉ đoạn thẳng theo trục thế giới

Vì hộp làn của metric là hộp thẳng theo trục thế giới, I/O trên route thật chỉ hợp lệ khi:
- heading của route trên **toàn bộ** đoạn chứa các segment đổi làn lệch không quá 1° so với một trục thế giới
  (0°, 90°, 180° hoặc 270°);
- tổng biến thiên heading trên đoạn đó ≤ 1° (C3 gốc).

Không thỏa → `LATERAL_GEOMETRY_UNSUPPORTED`. Đường chéo hay đường cong cần hộp có hướng, tức một thay đổi metric lớn hơn,
không thuộc bản này.

Heading lấy từ `rotation.yaw` của waypoint CARLA, không tính bằng atan2 giữa hai điểm cách 0,25 m.

## E1-b. Độ tách và dấu

| Mục | Quy tắc |
|---|---|
| Định nghĩa | `separation_m` = (tâm làn đích − tâm làn ban đầu) chiếu lên vector right của waypoint CARLA tại điểm bắt đầu đổi làn. Đây là quy ước của `LocalPlanner.set_offset`: dương là bên phải. |
| Nguồn | khâu chuẩn bị tính từ waypoint CARLA, ghi vào `topology.lane_geometry[role]`; không nhập tay |
| Kiểm chéo | consumer tính lại độ tách từ tâm hộp INITIAL và TARGET, chiếu lên vector right của trục. Lệch quá 0,05 m → `LATERAL_SEPARATION_INVALID`. |
| Hộp | hai hộp INITIAL và TARGET phải rời nhau trên trục ngang. Mọi điểm route trên đoạn đổi làn phải nằm trong khoảng ngang của hộp INITIAL. |

## E1-c. Chuyển sang route làn đích

Route mới (làn đích, hoặc làn cũ khi quay về ở O) phải thỏa:
- là route waypoint CARLA, mỗi bước ≤ 0,25 m, cùng `map_hash`, có `continuity`;
- **khung arc thẳng hàng:** với mọi điểm của route mới, |arc của điểm đó − station của nó chiếu lên route cũ| ≤ 0,05 m;
- **liên tục tại marker:** điểm route cũ tại marker, cộng `old_offset` theo vector right, cách điểm route mới tại cùng arc
  không quá 0,05 m;
- offset mới tại marker = 0, và segment đầu của profile mới bắt đầu ở offset 0. Hai điều này giữ nguyên như cũ.

Route 2 điểm trục +x vẫn đi theo quy tắc cũ, giữ nguyên văn và so khớp đúng tuyệt đối.

## Dung sai 0,05 m

Đây là dung sai đo, không phải ngưỡng metric. Nó bao sai số float của vị trí tâm làn CARLA, vốn cỡ 1e-6 đến 1e-3 m. Nó nhỏ
hơn ngưỡng contact nhỏ nhất (0,05/0,15/0,20) và nhỏ hơn nhiều so với bề rộng làn (≈ 3,5 m).

## Báo cáo

Mọi kết quả I/O được báo theo cả hai quy tắc:
- quy tắc cũ: route trục +x, nghĩa là mọi cảnh I/O trên route thật đều `LATERAL_GEOMETRY_UNSUPPORTED`;
- quy tắc mới: quy tắc của erratum này.

## Bổ sung (cùng ngày, trước code C3): làm tròn float

Phép kiểm "mỗi bước ≤ 0,25 m" (C3 gốc và E1-c) cho phép thêm 1e-6 m. Lý do: các waypoint cách đúng 0,25 m trên một đường
xoay vẫn có thể đo ra 0,25000000000000006 m do làm tròn float. Đây là cùng loại dung sai 1e-6 đã dùng cho làm tròn vùng ở
V3.2.
