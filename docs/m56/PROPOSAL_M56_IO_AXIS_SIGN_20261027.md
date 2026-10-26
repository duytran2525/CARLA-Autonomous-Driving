# M56: đề xuất sửa dấu separation của guard quay về trên đường không chạy theo +x (27/10/2026), CHỜ DUY QUYẾT

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Đây là đề xuất; Claude không áp dụng và chưa chạy cảnh nào.

## Vấn đề (đọc code consumer `m56/response.py`, khoảng dòng 469; không cần số episode)

Trong `step_response` của O-A, consumer chọn guard như sau:
- `separation = route_ref.transforms[0].y − route.transforms[0].y`;
- `returning = ... or offset * separation < 0`.

Offset tính theo vector phải của CARLA, (−sin yaw, cos yaw). Hai cách tính chỉ khớp nhau khi đường chạy theo +x (yaw ≈ 0), như
O03.

| Site | Cảnh | Hướng | Hệ quả |
|---|---|---|---|
| Town06 R40 | O03 / I03 | yaw ≈ 0 | Đúng |
| Town04 R45 | O01 / I01 | yaw ≈ −180 | Dấu của separation bị đảo. Khi đã sang làn đích, đoạn quay về bị coi là "đi ra", nên consumer đòi `LANE_CHANGE_PATH_CLEAR` thay vì `RETURN_CLEAR_CONFIRMED` + `RETURN_PATH_CLEAR` |
| Town05 R37 | O02 / I02 | yaw ≈ −90 | separation theo y bằng 0, nên consumer chỉ dựa vào số segment để phát hiện quay về |

Phép kiểm `_lateral_axis_v5` lúc compile thì đã xét đúng trục và dấu, nên lỗi chỉ nằm ở cách chọn guard trong lúc chạy.

## Đề xuất

Tính `separation` theo trục ngang và dấu của `_axis_right`, giống `_lateral_axis_v5`:
- lấy hiệu tọa độ trên trục ngang, nhân với dấu của vector phải;
- trên O03 kết quả giống hệt luật cũ.

Cần thêm test cho ba hướng: 0, −90 và 180.

## Xin quyết

Duy duyệt hoặc bác, dưới dạng erratum consumer. Erratum này cần có trước mọi A/B của O01/O02/I01/I02.
