# M56 I/O recipe v1, pilot O03: bản đăng ký trước (ĐÃ DUYỆT)

**Thẩm quyền đã có:** [chat] 26/10/2026, Duy: "Tiếp tục dựng tooling I/O với pilot O, chỉ chuẩn bị".

**Duyệt:** [chat] 27/10/2026, Duy: "duyệt recipe I/O v1 tại 688ad64 cho O03; chạy đúng một A/B (P5), báo nguyên trạng theo nhãn not independent". Văn bản duyệt = bytes tại `688ad64`.

**Trước khi duyệt:** chưa có quyền chạy A/B I/O. Không có A/B I/O nào trước khi Duy duyệt văn bản này. `native-io-ab.py --ab` từ chối chạy
nếu thiếu `M56_IO_PREREG_APPROVED=<commit Duy duyệt>`.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thiết kế:** `DESIGN_M56_IO_TOOLING_20261026.md`.

**Phạm vi:** chỉ O03 (Town06, road 40). Các cảnh I và các cảnh O khác chưa có tooling. Mục b–e của
`PROPOSAL_M56_ROAD_TO_46_20261026.md` vẫn chờ Duy.

**Chưa có số episode nào:** mọi lựa chọn dưới đây được đặt trước mọi episode I/O. Số đã thấy chỉ gồm số chuẩn bị: plateau tốc độ
probe, gap lúc t0 và readiness.

## 1. Consumer và catalog không đổi

- Consumer: `feat/m56-v7` (`59e6207`).
- Catalog đóng băng giữ nguyên:
  - chương trình EGO A/B;
  - target;
  - profile quintic;
  - Dlc, return_start, X, front_t0, gap, vE, vN.
- Không ngưỡng nào đổi.

## 2. Các lựa chọn của Claude (recipe io-v1)

| # | Mục | Lựa chọn |
|---|---|---|
| 1 | Route EGO | Waypoint tâm làn ban đầu của CARLA, mỗi bước ≤ 0,24 m. Từ road-s front_t0 − 100 m (RUNIN 100 m) tới X + 20 m |
| 2 | Route làn đích | Waypoint tâm làn đích trên cùng đoạn road-s. Arc của route này là hình chiếu của từng điểm lên route EGO, nên dùng chung khung arc với route EGO (E1-c: lệch ≤ 0,05 m) |
| 3 | Route NPC | Waypoint tâm làn NPC, kết thúc 30 m sau điểm cuối của EGO |
| 4 | Ánh xạ arc catalog sang native | Một offset duy nhất: d = station native của điểm đầu route catalog. Mọi arc đóng băng (điểm bắt đầu profile, marker của switch) cộng d; mọi độ dài giữ đúng |
| 5 | Route của switch | Switch `TARGET_LANE_CONFIRMED` → route làn đích. Switch `RETURN_LANE_CONFIRMED` → route EGO |
| 6 | Section | Mặt phẳng vuông góc với trục chạy, phủ ngang cả hai làn, z từ đáy route − 1 m tới đỉnh + 3 m. `O_DECISION` = station(front_t0); `O_RETURN_START` = station(front_t0) + return_start; `X` = station(road-s X); `DESTINATION` = X + 5 m (làm tròn lên 1 mm) |
| 7 | `action_regions` | Hai hộp theo trục tọa độ. Theo chiều ngang: từ biên ngoài của làn (theo bề rộng CARLA) tới đường giữa hai tâm làn, nên hai hộp chạm nhau và không chồng nhau. Theo trục chạy: phủ cả route EGO và route làn đích ± 10 m. z như mục 6 |
| 8 | `lane_geometry` | `separation_m` = khoảng cách tâm làn CARLA lúc quyết định, có dấu theo vector phải của CARLA, làm tròn 1 mm. Nếu khác `end_offset` của catalog thì chặn (`IO_LANE_SEPARATION_MISMATCH`). Bề rộng làn lấy từ CARLA |
| 9 | Domain | Hộp theo trục: theo trục chạy từ `O_DECISION` tới `X`, theo chiều ngang phủ cả hai làn. Consumer O không dùng `e_entry`/`e_exit`; hộp này chỉ để compile |
| 10 | `map_reference` | Route EGO, mỗi đoạn một pháp tuyến xy (−dy, dx, 0), vuông góc chính xác với đoạn đó |
| 11 | Pair | (`v_mean_E`, `e_lat_peak`), (m/s, m), (mean_speed, map_lateral_peak), window (TRIGGER, X_END) cho cả hai, reference `map:` + digest |
| 12 | Proof `LANE_CHANGE_PATH` | Hành lang = hộp làn đích × [đuôi EGO, mũi EGO + Dlc + 1 thân EGO] theo trục chạy. Clearance = khoảng cách xy từ thân NPC tới hành lang, làm tròn xuống 0,1 mm. Uncertainty 0,001 |
| 13 | Proof `RETURN_PATH` | Như mục 12, nhưng trên hộp làn ban đầu |
| 14 | Vị trí NPC | Probe 1 đo t0 (mũi EGO tới `O_DECISION`), rồi dời điểm xuất phát NPC dọc làn cho đuôi NPC cách mũi EGO đúng `gap` lúc t0. Probe 2 kiểm lại |
| 15 | Readiness | Như C/L/M (E6): target = plateau đo ở probe 2; marker theo predicate của runner; EGO phải sẵn sàng trước `O_DECISION` |
| 16 | PID | Lưới erratum 2 cho EGO và lưới P-NPC cho NPC, như C/L/M |
| 17 | Stock driver | BasicAgent với `set_offset` (sẵn có trong product). Mỗi switch có một plan riêng: waypoint của làn được switch tới, từ marker trở đi, cách nhau 2 m (`phase_plans`, kèm `fixture_ref`) |
| 18 | Kit, `REFERENCE_LATERAL_BUDGET` | Bound = v² × (độ cong route + (10/√3)·\|Δ\|/L² của mọi đoạn quintic có dịch ngang trong ±10 m). Cận này giữ nguyên cho C/L/M vì các profile của chúng không dịch ngang |
| 19 | NPC | Chương trình annex v2 2.2 (NOMINAL vN sau CAPTURE_START). Không có v6 TURN/PARK, vì route thẳng và O không có CLEAR_N |
| 20 | P5 | Một A/B cho mỗi cảnh trong mỗi version, thêm tối đa một lần chạy lại nếu chứng minh được lỗi harness |
| 21 | Proof `RUNIN_ROOM` | O không có G, nên yêu cầu run-in được hiểu là EGO sẵn sàng trước `O_DECISION`. `required_m` = `G_m` = khoảng cách từ mũi EGO lúc spawn tới mũi EGO lúc sẵn sàng ở probe 2, làm tròn lên. `available_m` = `initial_front_m` = khoảng cách từ mũi EGO lúc spawn tới `O_DECISION`. Các phép kiểm của consumer giữ nguyên |
| 22 | Proof `DESTINATION_ROOM` | exit = `X`; destination = X + 5 m; plan kéo dài thêm 15 m |
| 23 | `BODY_FIT`, `GROUND`, drivable | Như C/L/M v6/v7. Riêng vùng drivable phủ mọi điểm của cả ba route + 20 m, vì route O dài khoảng 200 m |

## 3. Rủi ro đã biết (nói trước, không sửa sau khi thấy số)

- **Biên hộp làn.** `_in_action_region` của consumer trả `None` khi một đỉnh thân xe nằm trong ±0,001 m quanh biên làn. Khi đó
  episode bị UNKNOWN (`ACTION_REGION_WITNESS_UNKNOWN`). Ước lượng của Claude:
  - khoảng 2–3 % cho mỗi lần thân xe cắt biên (2 mm trên khoảng 7 cm mỗi frame);
  - mỗi lần đổi làn cắt biên hai lần, và A đổi làn hai lần;
  - tổng khoảng 10 % cho mỗi episode A.
  Đây là luật đóng băng, không sửa.
- **Plateau EGO thấp hơn nominal.** EGO đạt plateau 9,069 m/s, thấp hơn nominal 9,375 m/s. Readiness dùng plateau (E6), còn
  profile và độ dài đổi làn dùng nominal (catalog).
- **Clearance lúc quay về.** Khoảng trống dự đoán lúc quay về chỉ là ước lượng động học từ số chuẩn bị (self-check mục 4), không
  phải bằng chứng.
- **Khe thời gian lúc quay về (rủi ro lớn nhất).**
  - Đoạn quay về bắt đầu ở một arc cố định: tâm xe tại `O_RETURN_START`.
  - Từ lúc đó, `step_response` đòi `RETURN_CLEAR_CONFIRMED` (đuôi EGO trước mũi NPC ≥ 0,5 m, giữ 0,25 s). Thiếu thì lỗi
    `RETURN_GUARD_MISSING`.
  - Ước lượng động học từ số chuẩn bị: khe là 0,26 s (khoảng 2,3 m). Nếu xác nhận đến trễ hơn khoảng 5 frame, episode A hỏng.
  - Khe này do hình học của spec (gap, return_start, vE, vN) tạo ra, không do recipe.
- **Khe tới X.** Đoạn quay về kết thúc khi tâm xe ở 175,65, còn `X_END` kích hoạt khi tâm xe ở 181,25. Bộ điều khiển ngang stock
  có khoảng 0,62 s để đưa cả thân xe về hộp làn ban đầu. Nếu không kịp:
  - episode bị `MANEUVER_NOT_COMPLETE_BY_X`;
  - hoặc sau X bị `CONTINUOUS_POST_END_LANE_UNPROVEN` (thân xe phải nằm trong làn với dung sai 0,15 m).
- **TRIGGER đi trước profile.** TRIGGER (mũi xe qua `O_DECISION`) đến trước lúc profile đổi làn bắt đầu (tâm xe tại `O_DECISION`)
  khoảng 1,85 m, tức 0,2 s. Đây là hệ quả của việc giữ nguyên arc catalog, vốn tính theo tâm xe. Ca tổng hợp `o_cases` dùng
  0,05 m. Consumer chỉ đòi lần lệch ngang đầu tiên đến sau TRIGGER.
- **Gap lúc t0.** Thực tế 25,13 m, spec 25,35 m. Nguyên nhân:
  - t0 là frame đầu tiên mũi EGO đã qua `O_DECISION`, nên lệch tới 0,45 m (9,07 m/s × 0,05 s);
  - điểm xuất phát NPC bám vào các hàng waypoint cách nhau 0,2 m.

  Dung sai đặt trước: |gap − spec| ≤ 0,5 m.
- **Sample nằm sát mặt section.** Consumer bỏ một lần cắt section nếu frame lấy mẫu nằm trong ±0,001 m quanh mặt phẳng (lần
  cắt đó mất hẳn). Ước lượng: khoảng 0,4 % cho mỗi section (2 mm trên 0,45 m mỗi frame), áp dụng cho TRIGGER, RETURN_MARKER
  và X_END. Replay offline gặp đúng trường hợp này khi đặt mũi xe chính xác lên `O_DECISION`.
- **Mục 21–22 được đặt sau lần compile native đầu tiên.** Lần đó bị chặn vì schema: proof chưa có các khóa mà consumer đòi
  (`outputs/m56_io_compile_O03.log`). Đó là cổng compile, không phải kết quả episode.
- **Đường không theo trục x.** Consumer v5 (`response.py`: `separation = route.y − route.y`) chỉ đúng khi đường chạy theo trục x.
  O03 (road 40, yaw 0,02°) không bị ảnh hưởng. Các site chạy theo trục y (nếu có ở I/O khác) cần một erratum riêng, chưa đề xuất ở
  đây.

## 4. Kết quả chuẩn bị (chỉ chuẩn bị, không có episode)

**Tooling:** `feat/m56-v1` `233c4fb`, `621dfad` (cùng commit chứa văn bản này). **Consumer:** `feat/m56-v7` `59e6207`.

| Bước | Output | Kết quả |
|---|---|---|
| Chuẩn bị | `outputs/m56_v2_prepare_Town06_20261026T163001Z` | PREPARED (chi tiết bên dưới) |
| Revision | `outputs/m56_c0_partial_io_o03_20261026T163218Z` | Đóng băng (sha `10057c74…`). So với revision cùng danh sách nhưng không có O03: chỉ O03 khác; các cảnh còn lại chỉ khác ở đường dẫn output của chính lần build |
| Compile + admission native | `outputs/m56_io_compile_Town06_20261026T164437Z` | Fixture FROZEN (sha `f56e8ec6…`), ADMITTED |
| Compile offline | `native-io-compile-offline.py` | Các map offset đọc đúng 0; 1,75; 3,5 m ở station 110, 150 và 175. Stock driver dry run qua cho EGO A (plan TARGET 34 hàng, plan HOME 12 hàng), EGO B và NPC |
| Self-check | `native-io-selfcheck.py` | PASS. Mục 4 (khe quay về) 0,26 s; mục 5 (khe tới X) 0,62 s |
| Kiểm kit | `native-io-kit-check.py` | PASS |
| Replay động học (lý tưởng, không phải bằng chứng) | `native-io-replay.py` | Chạy qua `detect_events` và `step_response` của consumer, mọi lệnh được chấp nhận. **A:** TRIGGER (frame 61) → TARGET_LANE_CONFIRMED (112) → RETURN_CLEAR_CONFIRMED (165) → RETURN_MARKER (166) → RETURN_LANE_CONFIRMED (217) → X_END (244) → DESTINATION (260); phase cuối HOME. **B:** TRIGGER (61) → X_END (724) → DESTINATION (769); phase cuối FOLLOW |

**Chi tiết chuẩn bị:**
- EGO: plateau 9,069 m/s, có PID (lưới erratum 2, gains 1/2, 1/20, 0).
- NPC: plateau 2,376 m/s, dùng stock.
- EGO sẵn sàng khi mũi xe ở station 27,3 m, trước `O_DECISION` (100,0).
- Gap lúc t0 = 25,13 m.
- Độ tách làn 7/2 (khớp catalog).

**Consumer contract trên fixture native:** lateral, forward (normative) và mọi reference đều OK cho EGO A, EGO B và NPC.

Không có episode I/O nào đã chạy.

## 5. Xin duyệt

Duy duyệt mục 2 (recipe io-v1) cho O03, chạy đúng một A/B (P5), báo kết quả nguyên trạng.
