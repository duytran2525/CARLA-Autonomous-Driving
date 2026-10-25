# M56 v5 erratum 5: bỏ kiểm mặt cắt ở STOP_CONFIRMED và lúc vào hộp (ĐỀ XUẤT, chờ Duy duyệt)

**Trạng thái:** PROPOSED. Chưa sửa code, chưa chạy lại.

**Nguồn gốc:** đề xuất này đặt **sau khi thấy** kết quả A/B M (erratum 3) và L (v5f), nên theo nguyên tắc 6 phải được Duy duyệt
và công khai. Mọi kết quả về sau báo theo cả quy tắc cũ và quy tắc mới.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## Lỗi

Consumer (`m56/metrics.py`, có từ pipeline gốc `f1d2c7c`) chỉ phát một số event khi thân xe, chiếu lên mặt hộp theo pháp tuyến,
nằm trọn trong mặt đó (`_section_corridor`):

| Event | Dòng | Spec có đòi không |
|---|---|---|
| E_ENTRY, NPC_ENTRY (frame cắt mặt vào) | 1237 | **Không.** §7.3 (dòng 331): "first front-body contact/crossing boundary" |
| STOP_CONFIRMED của EGO | 1259 | **Không.** §5.3 (dòng 222): tốc độ ≤ 0,10 m/s trong ≥ 0,5 s, mũi xe cách vạch ≥ 0,50 m |
| CLEAR_N_CONFIRMED (mặt ra) | 1249 | **Có.** §5.2, bảng policy: "every vertex downstream of exit ≥ 0.50 m, correct corridor" |
| DESTINATION_CONFIRMED | 1264 | không nói; giữ nguyên |

Hộp xung đột là hộp trục tọa độ bao phần chồng lấn của hai vệt thân xe, và các mặt vào/ra là mặt của hộp đó. Khi một xe rẽ trước
khi vào hộp, đường tâm của nó cắt một mặt **song song** với hướng nó chạy tới. Thân xe khi đó không bao giờ nằm trọn trong mặt
cắt, nên event không bao giờ được phát. Episode vẫn chạy bình thường; chỉ phép kiểm sai.

## Bằng chứng (dựng lại episode bằng `runtime.load_episode`, chỉ đọc)

| Cảnh | Event mất | Frame | Điều kiện khác | Thân xe so với mặt hộp |
|---|---|---|---|---|
| M03-A | NPC_ENTRY | 28947 (mũi vượt station 68,74) | route hợp lệ, vượt station | chìa 1,65 m ra ngoài biên y |
| M06-A | NPC_ENTRY | 32687 | như trên | chìa 0,54 m |
| M07-A | NPC_ENTRY | 35761 | như trên | chìa 2,11 m |
| L01-A | STOP_CONFIRMED | 14217 trở đi (EGO đứng yên tới hết episode) | v = 0, cách vạch 10,41 m ≥ 0,5 | mặt vào là mặt x, EGO chạy theo −y; thân xe ở y −233,3 … −229,6, ngoài biên y của hộp |

Hệ quả online: response driver đọc chính các event này. Ở M03-A, EGO đứng chờ CLEAR_N (không bao giờ có) tới hết episode. Ở
L01-A, EGO dừng nhưng không có STOP_CONFIRMED; episode kết thúc với `OUTER_TIMEOUT`. Vì vậy không thể sửa bằng đánh giá lại
offline; phải chạy lại.

## Thay đổi đề xuất (khuyến nghị: phương án 1)

**Phương án 1 (consumer, khớp chữ của spec):**
- Bỏ conjunct `_section_corridor` ở dòng 1237 (E_ENTRY/NPC_ENTRY) và ở dòng 1259 (STOP_CONFIRMED).
- Giữ nguyên các điều kiện còn lại: actor có `route_valid`, mọi đỉnh thân xe chiếu được lên route, mũi xe vượt station (entry),
  hoặc tốc độ và khoảng cách ≥ 0,50 m (stop).
- Giữ nguyên kiểm mặt cắt ở CLEAR_N (spec đòi) và ở DESTINATION.
- Không đổi kernel F/I/O, không đổi ngưỡng nào.
- **Kiểm:** thêm test cho cả hai trường hợp (xe rẽ vào mặt song song; dừng trước mặt song song); chạy các test bị ảnh hưởng;
  đánh giá lại offline C01-B, vẫn phải ra COMPLETE/VALID với cùng d_yield 10,557 và t_entry 9,6. Sau cùng chạy full suite trên
  byte cuối như kế hoạch.

**Phương án 2 (recipe, không đổi consumer):** nới hộp tới điểm cố định, sao cho thân xe theo route đã lập kế hoạch (chưa thấy
outcome) nằm trong mặt vào tại mọi station từ entry − G − chiều dài xe tới entry. Nhược điểm:
- vạch vào của EGO dời ngược lên 10–15 m ở các cảnh L, nên d_yield và t_entry được đo tới một mặt khác;
- dễ bao luôn phần xung đột không được chọn (`DOMAIN_ENCLOSES_UNSELECTED_CONFLICT`);
- phải tính lại G và run-in.

Claude không khuyến nghị phương án này.

## Chạy lại (P5)

Với các cảnh mà ít nhất một episode thiếu NPC_ENTRY, E_ENTRY hoặc STOP_CONFIRMED **chỉ** vì conjunct này, A/B được chạy lại **đúng
một lần** với code mới.
- **Cách xác định:** chạy script chẩn đoán trên episode cũ và kiểm rằng mọi điều kiện khác đều đúng ở frame tương ứng. Danh sách
  chốt trước khi chạy lại và được ghi vào hồ sơ.
- **Đã chứng minh:** M03, M06, M07, L01.
- **Sẽ kiểm bằng cùng script:** L02, L04–L07, C02, C03.
- Kết quả cũ giữ nguyên làm hồ sơ.

## Không đổi

Mọi ngưỡng (0,10 m/s, 0,50 s, 0,50 m, G, 2,5 m/s²), hộp M (v4 P3), erratum 3 và 4, và các kernel F/I/O.
