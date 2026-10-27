# M56 I/O recipe io-v1.2: mở rộng sang O01 (Town04) và O02 (Town05), bản đăng ký trước (ĐÃ DUYỆT)

**Thẩm quyền đã có:** [chat] 27/10/2026, Duy: "chuẩn bị O01/O02 theo recipe I/O v1.1 + consumer v8 (chỉ chuẩn bị), rồi soạn bản
đăng ký trước mở rộng recipe cho hai site này để tôi duyệt trước A/B".

**Duyệt:** [chat] 27/10/2026, Duy: "duyệt PREREG_M56_IO_RECIPE_V1_1_O01_O02_20261027 (io-v1.2: dời cửa sổ site O01 +95, O02 +24; RUNIN theo vE; mốc hộp làn trung điểm) tại 90bc7a3; chạy đúng một A/B mỗi cảnh với consumer v8, báo theo v8 và v7." Văn bản được duyệt là bytes tại `90bc7a3`.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Nền:**
- recipe I/O v1 (`688ad64`, đã duyệt) + erratum v1.1 (`PREREG_M56_IO_RECIPE_V1_1_ERRATUM_20261027.md`);
- consumer v8 (`feat/m56-v8` `5635d6c`, đã duyệt, gồm luật dấu separation theo trục cho O01/O02/I01/I02).

**Chưa có số episode nào của O01/O02.** Số đã thấy chỉ là số chuẩn bị (§4).

## 1. Vấn đề cần Duy quyết: cửa sổ site của spec nằm trên đoạn cong

Luật consumer đóng băng `_lateral_axis_v5` đòi đoạn chứa các segment đổi làn phải:
- thẳng (tổng biến thiên hướng ≤ 1°);
- song song với một trục tọa độ (lệch ≤ 1°).

Hình học OpenDRIVE (planView) và route catalog đóng băng cho thấy:

| Cảnh | Đường, làn (chạy theo chiều s giảm) | Đoạn thẳng của đường | Cửa sổ spec (đổi làn → kết thúc quay về) | Hướng trong cửa sổ spec (catalog) |
|---|---|---|---|---|
| O01 | Town04 R45, làn +3 → +4 → +3 | s 282,59–404,31 (hướng chạy 180,21°) | front_t0 = 280 → 220. Nằm hẳn trên cung 90° (s 0–282,59) | −179,6° … −159,4° (khoảng 20°) |
| O02 | Town05 R37, làn +2 → +3 → +2 | s 304,28–397,88 (hướng chạy 90,84°) | front_t0 = 360 → 294. 10 m cuối nằm trên cung 91° (s 146,85–304,28) | −90,8° … −84,5° (khoảng 6°) |

Nếu giữ đúng cửa sổ spec, cả hai cảnh sẽ bị chặn ngay lúc compile (`LATERAL_GEOMETRY_UNSUPPORTED`).

## 2. Đề xuất: dời cửa sổ site dọc theo đường (giữ mọi khoảng cách của spec)

`front_t0` và `X` dời cùng một lượng Δ (road-s). Các tham số Dlc, return_start, gap, vE, vN và mọi độ dài của catalog giữ nguyên.
Lượng dời được ghi vào `prepare.json` (`site_shift_s`, `site_shift_travel_m`), và offset arc catalog cộng thêm đúng lượng đó theo
chiều chạy.

| Cảnh | Δ đề xuất | front_t0 / X mới (road-s) | Khoảng hợp lệ của front_t0 | Lề tới hai đầu đoạn thẳng |
|---|---|---|---|---|
| O01 | +95 | 375 / 311,25 | [342,59; 404,31] | 29,3 m và 32,4 m |
| O02 | +24 | 384 / 314,25 | [370,28; 397,88] | 13,9 m và 13,7 m |

Δ được chọn để cửa sổ nằm khoảng giữa đoạn thẳng, trước khi có số episode nào. **Đây là thay đổi tham số site của spec §7.4 cho
hai cảnh, nên cần Duy duyệt.**

Phương án khác:
- (ii) bỏ O01/O02 khỏi catalog I/O, hoặc thay bằng site khác;
- (iii) một erratum consumer cho phép đoạn đổi làn cong. Phương án này không đề xuất ở đây.

## 3. Các mục khác của recipe (io-v1.2 cho O01/O02; O03 giữ v1.1)

Tất cả các lựa chọn dưới đây được đặt trong lúc chuẩn bị, trước mọi episode, nên cần Duy duyệt cùng §2.

| # | Mục | v1.1 (O03) | io-v1.2 (O01/O02) | Lý do (đo ở bước chuẩn bị) |
|---|---|---|---|---|
| a | RUNIN | 100 m | ⌈100 · vE / 9,375⌉: O01 64 m, O02 80 m (O03 vẫn 100) | Với 100 m, probe 16 s không tới được `O_DECISION` ở vE 6 và 7,5 m/s (`EGO_NOT_AT_DECISION_IN_PROBE1`) |
| b | Mốc của hộp làn | Tâm làn tại `O_DECISION` | Tâm làn tại trung điểm của [`O_DECISION`, `DESTINATION` + 3 m] | O02 lệch trục 0,84°, nên tâm làn trôi ngang 1,03 m từ `O_DECISION` tới X. Với mốc cũ, chỗ trống (thân xe + buffer 0,15 m) trong hộp `EGO_INITIAL` là **−0,44 m**: B sẽ hỏng `UNPLANNED_LANE_CHANGE`, A hỏng `MANEUVER_NOT_COMPLETE_BY_X`. Với mốc mới là **+0,13 m**; O01 từ 0,44 lên 0,57 m |
| c | Bề ngang của section | Hai làn, đo tại `O_DECISION` | Hai làn trên toàn route (tính cả độ trôi) + 0,5 m | Ở replay O02 B, X_END không kích hoạt vì thân xe ra ngoài bề ngang của section |
| d | Các mục khác | | Giữ nguyên v1 + v1.1: đuôi route EGO X + gap + 2 thân xe + 20 m; NPC; PID; proof | |

Separation vẫn đo tại `O_DECISION` (3,5 m). Khoảng cách giữa tâm hai hộp vẫn là 3,5 m, đúng như consumer đòi.

Riêng hướng đường: consumer v8 chọn guard quay về theo trục và dấu của vector phải. Hướng chạy là:
- O01: 180,2°, trục x, dấu −;
- O02: 90,8°, trục ngang là x, dấu +.

Lưu ý: hướng chạy 90,84° của O02 lệch trục 0,84°, gần sát giới hạn 1°.

## 4. Kết quả chuẩn bị (chỉ chuẩn bị, không có episode)

**Phiên bản:**
- Tooling `feat/m56-v1` `e465cc3`; consumer `feat/m56-v8` `5635d6c`.
- Biến môi trường: `M56_IO_SITE_SHIFT="M56-P-O01=95,M56-P-O02=24"`, `M56_IO_BOX_ANCHOR=midpoint`.
- Revision: `outputs/m56_c0_partial_io_o0102v12_20261027T033452Z`.

| | O01 (Town04) | O02 (Town05) |
|---|---|---|
| Chuẩn bị | PREPARED | PREPARED |
| Plateau EGO / NPC (m/s) | 5,731 / 2,376 (nominal 6) | 7,212 / 2,376 (nominal 7,5) |
| PID của EGO | Lưới erratum 2 (1/2, 1/20, 0) | Như O01 |
| Mũi EGO lúc sẵn sàng / `O_DECISION` (m) | 22,4 / 63,08 | 26,8 / 80,15 |
| Gap lúc t0 (spec) | 14,75 m (15) | 19,54 m (19,5) |
| Compile + admission native | FROZEN `fcf477f0…`, ADMITTED, contract OK | FROZEN `bb3d348c…`, ADMITTED, contract OK |
| Self-check: khe quay về / khe tới X | 0,65 s / 0,98 s | 0,36 s / 0,78 s |
| Replay A (consumer v8) | Đủ event, theo đúng thứ tự, từ TRIGGER tới DESTINATION; step_response OK | Như O01 |
| Replay B | Như A; phase cuối FOLLOW | Như A; phase cuối FOLLOW |

**Lưu ý thêm:**
- Ở O02, điểm bắt đầu profile đổi làn (tâm xe) sớm hơn section `O_DECISION` 2,2 cm. Sai khác này đến từ offset arc catalog
  (phép chiếu cộng lượng dời).
- TRIGGER vẫn đến trước lúc tâm xe bắt đầu dời ngang khoảng 1,8 m, nên onset vẫn sau TRIGGER.

Không có episode nào của O01/O02 đã chạy.

## 5. Xin duyệt

1. Duyệt cách dời cửa sổ site ở §2 (O01: Δ = +95; O02: Δ = +24) và các mục a–c ở §3 (io-v1.2), hoặc chọn (ii) / (iii).
2. Nếu duyệt, mỗi cảnh chạy đúng một A/B (P5), báo theo consumer v8 và v7.
