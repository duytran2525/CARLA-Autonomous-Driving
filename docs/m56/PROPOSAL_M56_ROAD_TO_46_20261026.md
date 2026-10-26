# M56: đường tới 46 cảnh. Hiện trạng và các quyết định cần Duy (26/10/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Mọi con số trong file
này là phân tích offline trên dữ liệu đã seal, không có A/B mới.

## 1. Hiện trạng

**Cặp A/B hợp lệ (v6):** 3 cặp (C01, L01, C05), xem `M56_V6_RESULT_20261026.md`.

**Mục tiêu §11:** 46 cảnh, ≥ 23 junction đủ điều kiện, mỗi cảnh có A/B hợp lệ, 155 phép so, rồi export.

| Nhóm | Số cảnh trong catalog | Trạng thái |
|---|---|---|
| C/L/M | 24 | 3 PASS. Bị chặn (i): C03, L05, L06, M03, M05. Không chuẩn bị được: C04, C06, C07, C08, L03, L08, M01, M02, M04, M08. Còn hỏng: C02, L02, L04, L07, M06, M07 |
| I/O | 12 đã đóng băng (I01–I05, I07, O01–O05, O07); I06, O06 mới đề xuất | chưa cảnh nào từng được chuẩn bị native (chưa có tooling) |
| F | F01, F03, F04 | F01 chưa có recipe; F04 thiếu năng lực (proof cửa xe) |
| Chỗ trống | I08, O08, F05, F06 | fill v3 không tìm được ứng viên theo luật đã đăng ký |

**Kết luận:** ngay cả khi mọi việc kỹ thuật đều thành công, §11 vẫn không đạt nếu thiếu các quyết định ở §2. Catalog hiện tối đa
42/46; 5 cảnh bị chặn theo (i); F04 thiếu năng lực; 6 cảnh I/O mâu thuẫn với consumer (§2.c).

## 2. Các quyết định cần Duy

### a. FIT có xét hướng thân xe (consumer v7). Đề xuất: duyệt

Luật hiện tại so hộp bao trục tọa độ của thân xe với các ô 0,5 m cũng theo trục tọa độ. Khi xe đi chéo hoặc vào cua, hộp này lớn hơn
thân xe rất nhiều, nên luật hỏng dù xe vẫn nằm trên mặt đường.

**Luật đề xuất:** hình bao lồi của các đỉnh thân xe ở hai frame của mỗi khoảng, nới 0,15 m (ngưỡng cũ) cộng phần dư của góc quay
như kit, phải nằm trong vùng drivable đã đóng băng của fixture.

Phân tích offline trên episode v6 đã seal (`outputs/m56_fit_oriented_20261026.jsonl`), số khoảng hỏng FIT:

| Cảnh | Luật hiện tại (A / B) | Luật đề xuất (A / B) | Lý do khác còn lại |
|---|---|---|---|
| C01, L01, C05 (PASS) | 0 / 0 | 0 / 0 | không |
| **L04** | NPC 112 / 112 | **0 / 0** | không. Δ = 0,87 và 0,253, nên **sẽ thành PASS** |
| L02 | 666 / 496 | 0 / 0 | GROUND, CONTACT |
| L07 | 581 / 435 | 0 / 0 | thiếu event (A), vào sớm (B) |
| M06 | 356 / 295 | NPC 41 / 41 | CONTACT, NPC lùi |
| M07 | 470 / 470 | NPC 155 / 155 | CONTACT |
| C02 | 243 / 243 | 131 / 131 | CONTACT |

- Không phần online nào đọc FIT (kit dựng các khoảng motion lúc seal, consumer đánh giá offline), nên áp dụng luật mới chỉ cần
  **đánh giá lại offline, không cần chạy lại**.
- Luật đặt sau khi thấy số; báo theo cả hai luật.

### b. Bốn chỗ trống của catalog (I08, O08, F05, F06)

Fill v3 không tìm được ứng viên theo luật đã đăng ký. Cần một luật lấp mới, đăng ký trước khi chạy census. Các hướng có thể chọn:
- cho F05/F06 dùng corridor qua J2086 (hiện đã gán cho M07);
- nới hạn k cho I08/O08;
- hoặc chấp nhận release dưới 46. Lựa chọn này đổi §11, nên chỉ Duy và TS. Hằng quyết.

### c. Sáu cảnh I/O mâu thuẫn với consumer

Normative contract (consumer v5 C2, đã duyệt) chỉ cho phép vE của EGO thuộc {6; 7,5; 9,375} m/s. Nhưng catalog đang có:

| Cảnh | k | vE | Kết quả |
|---|---|---|---|
| I04, O04 | 4 | 11,72 | ngoài tập cho phép |
| I05, O05 | 0 | 4,8 | ngoài tập cho phép |
| I07, O07 | −1 | 3,84 | ngoài tập cho phép |
| I06, O06 (đề xuất) | −2 | 3,072 | ngoài tập cho phép |

- Các cảnh này sẽ nhận `LATERAL_NOMINAL_INVALID` dù tooling làm tốt đến đâu.
- Có vẻ đây là lỗi "đơn vị k" mà báo cáo 24/10 đã nêu nhưng chưa sửa: với k = 0, spec cho vE = 6 nhưng catalog ghi 4,8, lệch một
  bậc 5/4.
- Cần quyết định: sửa tham số catalog (k → vE theo đúng spec) cho 6 cảnh và chuẩn bị lại, hoặc mở rộng tập cho phép của consumer.
- Chỉ I01–I03 và O01–O03 là nhất quán ngay bây giờ.

### d. F04: năng lực cửa xe

Spec §5.4 đòi proof bao cửa xe đã hiệu chuẩn. Có thể dựng proof đó bằng một probe CARLA (mở cửa, đo bbox theo thời gian). Việc
này cần một spec addendum.

### e. Phương án (i) cho C03, L05, L06, M03, M05

Nếu muốn tính 5 cảnh này vào 46, cần chọn (ii) (NPC giảm tốc trong xung đột, kèm probe có event) hoặc (iii) (hạ vN trong catalog).

## 3. Việc Claude làm tiếp mà không cần quyết định mới

1. **Tooling I/O.** Pilot là một cảnh O (O01–O03), chỉ chuẩn bị. Sau đó viết bản đăng ký trước cho recipe I/O, liệt kê mọi tham
   số Claude tự chọn. Bản này phải trình Duy trước bất kỳ A/B I/O nào, giống cổng đã đặt cho v6.
2. **Ghép code.** Product v6 đang ở `feat/m56-v6`. Khâu export cần merge vào nhánh chính và chạy full suite trên byte cuối.
