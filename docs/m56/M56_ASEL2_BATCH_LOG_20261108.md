# M56 A-SEL2: nhật ký đợt chạy (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

Tooling đóng băng theo §6 của `PREREG_M56_FILL_V4_ASEL2_20261108.md`. Lỗi harness được xử lý theo spec §4: version kỹ thuật, giữ
raw, không chạy lại tự động. Lỗi của cảnh thì ghi lại, rồi slot lấy cảnh thay từ hàng.

## Sửa kỹ thuật 1: body bbox bằng 0 trên map lớn

- **Lượt thí điểm Town11** (`outputs/m56_asel2_cl_20261108T082335Z`, tooling `6f69609`, product v10 `88dd311` merge `ecc90c1`):
  - M04-S1 và M07-S1 đều có `SCENE_ERROR INVALID_BODY_TRANSFORM` ở bước chuẩn bị, trước mọi probe. Không có A/B nào, nên quota
    P5 không bị dùng.
  - Raw được giữ ở `outputs/m56_v2_prepare_Town11_20261108T082350Z`.
- **Nguyên nhân:** xe đo bounding box được spawn ở spawn point 0 của map. Trên Town11, điểm này nằm ngoài
  `actor_active_distance` (2.000 m) tính từ spectator, nên actor ở trạng thái dormant. CARLA trả extent = 0 (file `a2-bbox.json`),
  và `m56.geometry.world_vertices` loại body này. Assert ngân sách 4,5 m ở tooling không bắt được trường hợp này, vì 0 ≤ 4,5.
- **Sửa** (`native-v2-prepare.py`, `native-io-prepare.py`):
  - trước khi spawn xe đo, stream spectator tới spawn point 0 (`stream_to`, chỉ bật khi `M56_SPECTATOR=1`);
  - sau khi spawn, assert mọi extent > 0 (`BODY_BBOX_ZERO`).
- Cảnh và giao thức không đổi. Chạy lại bước chuẩn bị của hai cảnh này. Đây là chuẩn bị, không phải A/B.

## Kiểm biên realized trên dữ liệu đã seal (chỉ đọc)

Script `asel2-realized-margin-check.py`. Định nghĩa đóng băng ở `8bdf074`: tốc độ trung bình trên [TRIGGER − 1 s, TRIGGER], lấy
trung bình A và B. Ở bản kiểm này, TRIGGER được dùng thay t0. Mục đích là xem độ hụt tốc độ thật so với danh nghĩa có kéo Δ của
các cặp k liền kề xuống dưới 0,20 hay không. Nếu có, cổng 155 REALIZED sẽ bất khả thi ngay từ thiết kế.

| Cảnh | Vai | Danh nghĩa (m/s) | Đo (A = B) |
|---|---|---|---|
| O01, O02, O03 | EGO | 6 / 7,5 / 9,375 | 5,7305 / 7,2115 / 9,0685 |
| I03, I04 | EGO | 9,375 / 11,72 | 9,0685 / 11,3876 |
| C01, C05, C08 | NPC | 3 / 7,32 / 14,31 | 2,8701 / 7,0396 / 13,9914 |

- Δ realized của các cặp k liền kề: O01–O02 = 0,2054; O02–O03 = 0,2048; I03–I04 = 0,2037. Cả ba **đều qua**, nhưng biên chỉ
  khoảng 0,004.
- Độ hụt tương đối giảm dần khi tốc độ tăng (4,5% → 2,8%), nên Δ của cặp liền kề nhỉnh hơn 0,20 một chút.
- Đây là số đo trên dữ liệu cũ. Nó không thay đổi định nghĩa nào. Cảnh mới vẫn phải được đo riêng.

## Phát hiện: L08 bị giới hạn cấu trúc (PHASING_ROOM)

- Batch `m56_asel2_cl_20261108T083410Z`: L08-S1 (Town12, J5719) ra `BLOCKED_FIXTURE PHASING_ROOM` ở bước chuẩn bị.
- Số đo: luật phasing đòi D_N = 211,1 m, nhưng NPC chỉ có 158,9 m trước điểm vào xung đột, nên điểm xuất phát rơi vào −54,0 m.
  Với vE = 2 m/s (loại L), EGO mất khoảng 20 s mới tới vùng xung đột; với vN = 14,31 m/s (k = 8), NPC cần khoảng 211 m chạy đà.
- Approach probe của NPC được dựng cố định 150 m (`native-v2-prepare.py:160`). Vì vậy **mọi site** cho L08 đều sẽ hỏng y như
  vậy. L08 gốc cũng từng hỏng với lý do này (ngày 25/10). Giới hạn đến từ tham số slot (vE, vN) cộng với độ dài route mà tooling
  dựng, không đến từ site.
- **Chưa làm gì:** không sửa code giữa batch. Mọi sửa đổi, ví dụ dựng route NPC dài theo D_N, sẽ là erratum đặt sau khi thấy số.
  Erratum đó phải được công khai, áp cho mọi slot (không chỉ L08), và được commit trước lượt chuẩn bị lại.

## Các việc xử lý sau batch (ghi ngay khi thấy, trước khi xử lý)

| Cảnh | Kết quả bước chuẩn bị | Xử lý dự kiến |
|---|---|---|
| L08-S1 | `PHASING_ROOM` (D_N 211 > 150 m) | erratum E6 (bản nháp `ERRATUM_M56_PREPARE_E6_NPC_APPROACH_20261108.md`), đặt sau khi thấy số |
| M08-S1 | `SIGNAL_E5_NO_LIGHT` (luật E5 đã đăng ký) | giữ luật. Cảnh hỏng làm trống suất (M, Town12), nên theo addendum C: B3 cho M04, rồi M07, rồi M08 |
| C06-S1 | `PROBE2_NO_FRAMES`: `SPAWN_ERROR:NPC` ở probe 1 (cl-v1 a cứu bằng pitch) và lại ở probe 2 | **sửa kỹ thuật 2:** tư thế NPC ở probe 2 phải giữ pitch theo waypoint mà cl-v1 a đã gán ở probe 1 (luật cũ áp nhất quán). Chuẩn bị lại; chưa có A/B |
| L07-S1 | `SCENE_ERROR SECTIONS_BLOCKED:EGO:DOMAIN_CROSSING_UNBRACKETED` (luật compiler đóng băng; hình học của site) | cảnh hỏng, slot L07 lấy cảnh thay theo B3 (tiêu 1 lượt) |

## Dừng an toàn theo yêu cầu (08/11/2026, khoảng 14:20 UTC)

Người dùng yêu cầu: "hãy dừng an toàn cho tôi rồi tạo handoff". Claude đã dừng hàng đợi `run-asel2-queue.sh` (lúc đó vẫn đang
chờ, chưa chạy bước nào), watchdog, batch 1 và server CarlaUE4 riêng trên cổng 2610. Không còn tiến trình nào, cổng 2610 đã trống.

**Batch 1** (`m56_asel2_cl_20261108T083410Z`, revision `m56_c0_partial_io_asel2prep_20261108T114946Z`, product v10 lúc chạy):
- **A/B đã chạy xong cả hai episode, quota P5 đã dùng dưới version này:** C02-S1, C03-S1, C04-S1, L02-S1. Cả 4 đều có
  `spawn UNKNOWN` với lý do `INITIALIZATION_INVALID`. Raw nằm ở `outputs/m56_v2_ab_Town12_20261108T115001Z/`.
  **Chưa chạy pair** (`native-v6-pair.py`) cho cảnh nào.
- **Bị dừng trước khi chạy episode nào** (quota P5 chưa dùng): L05-S1, đang ở bước raster vùng drivable. M05-S1, M06-S1 và
  toàn bộ cảnh PREPARED ở Town13 (C07, L03, L06, M01, M03) chưa chạy.
- **Đầu mối INITIALIZATION_INVALID** (chẩn đoán sơ bộ, chưa kết luận): ở frame quan sát đầu, x lệch tư thế đóng băng khoảng
  2–4 cm, trong khi luật `_initial_state_matches` đòi |dx| ≤ 1e-4. Thứ tự các trường pose trong script chẩn đoán chưa được kiểm,
  nên các cột pitch/roll in ra là sai. Nghi vấn: hiện tượng chỉ có trên map lớn, ở tọa độ |y| khoảng 5000 m, ví dụ do float32
  hoặc do bước stream. Phải chẩn đoán trước khi chạy bất kỳ A/B nào trên map lớn nữa.

## 09/11/2026: chẩn đoán batch 1 và các sửa

| Phát hiện | Xử lý |
|---|---|
| `INITIALIZATION_INVALID`: x/y lệch 0,06–0,49 mm, bằng độ phân giải float32 ở tọa độ khoảng 5 km | Duy: dung sai 1 mm, product v12 (A-SEL2 §8) |
| `OUTER_TIMEOUT`: chờ pha khoảng 226 s, rồi 0,2–0,3 s/tick | Duy: outer 1500 s (A-SEL2 §9) |
| C03-S1, C04-S1 FAILED: NPC đi chéo, vùng xung đột thẳng trục, `CLEAR_N` không đạt | cổng trục B5 (fill addendum F); thay bằng C03-S2, C04-S2 |
| `load_world` timeout 60 s trên Town12 | sửa kỹ thuật 3: timeout 600 s |

**Chuẩn bị L08-S1 với E6** (`outputs/m56_v2_prepare_Town12_20261109T125853Z`, lúc đầu chạy để profile):
- E6 kéo dài route NPC thêm 74,1 m.
- Kết quả **PREPARED**: D_N = 211,1 m, T_r = 7,7 s, khoảng hở mũi EGO lúc ready là 22,2 m.
- Slot L08 đã bị chặn cấu trúc từ ngày 25/10. Batch 2 sẽ chuẩn bị lại L08-S1 bằng đúng tooling này, nên kết quả được kỳ vọng
  giống hệt.

## Sửa kỹ thuật 4 (09/11/2026): raster dv1 nhanh hơn, kết quả không đổi

- py-spy trên A/B C02-S1 (Town12, đang chạy): trong `drivable_union`, 50% thời gian là `cast_ray` (khoảng 148.000 lần gọi) và 33%
  là phép kiểm `prepared.contains` cho từng điểm của lưới hành lang (khoảng 544.000 điểm).
- Phép kiểm hành lang được đổi sang `shapely.contains_xy` vector hóa: cùng các điểm lưới float64, cùng thứ tự i ngoài / j trong.
- Đã kiểm boolean y hệt: 200.000 điểm ngẫu nhiên, cộng 77.150 ô trên một hành lang ở tọa độ Town12. Danh sách ô và union kết quả
  vì vậy không đổi.
- A/B đang chạy lúc sửa (C02-S1…M06-S1, Town12) đã nạp code cũ từ trước. Các lượt chạy sau dùng code mới.
- 09/11 khoảng 14:55 UTC: dừng có chủ đích lượt A/B Town12 của hàng đợi 3 (`outputs/m56_v2_ab_Town12_20261109T132009Z`). Lúc dừng
  nó vẫn ở raster dv1 của C02-S1 sau 95 phút: chưa có FIXTURE, chưa có episode, nên **quota P5 chưa dùng**. Khởi động lại thành
  hàng đợi 3b để dùng sửa kỹ thuật 4. Smoke F đã chạy xong, nên được bỏ khỏi 3b.

## F phần 1 (09/11/2026): chọn site, revision, tooling F01

**Chọn site.** Bộ sinh `f-site-generate.py` cùng ghi chú cài đặt `F_SITE_NOTES_20261109.md` được commit ở 9677a51 **trước**
lần chạy duy nhất. Kết quả: `outputs/m56_f_sites_20261109.json`, sha256 `1fba8d39…`, pool 107. Không slot nào trống.

| Slot | Site | Rule | Bị bỏ qua |
|---|---|---|---|
| F01 | Town13 R1165 S0, làn −2 | F3-1 | B5 2 |
| F02 | Town12 R451 S0, làn −1 | F2-3 | B5 12, section ngắn 17, site đã dùng 1 |
| F05 | Town12 R164 S0, làn −2 | R1 | B5 17, section ngắn 25, site đã dùng 2 |
| F06 | Town12 R896 S0, làn −2 | F3-1 | B5 24, section ngắn 35, site đã dùng 3 |

**Revision base F.** `outputs/m56_c0_partial_io_asel2fbase_20261109T153007Z`, chưa có preparation F:
- `M56-P-F01-S1` thay `M56-P-F01` (C0, Town06 R49). Thao tác này tiêu 1 lần trong trần 150.
- Đã kiểm offline: candidate decode được; EGO A/B qua `_forward_contract` (v13); script NPC F01 17/5 qua `_f_script_contract`;
  với nominal 4, contract trả `F_SCRIPT_POLICY_INVALID` như mong đợi.
- Bản dựng trước đó, `…asel2fbase_20261109T152720Z`, có tham số `mechanism` với units rỗng. Decoder strict từ chối tham số này
  (`UNSUPPORTED_UNIT`). Bản đó bị bỏ, vẫn được giữ lại.
- **Phát hiện kèm theo:** candidate C0 `M56-P-F01` và `M56-P-F04` cũng mang tham số đó, nên cũng không decode được.

**Realized F01/F02:** `F_REALIZED_DESCRIPTORS_20261109.md`, commit trước mọi A/B F.

**Chuỗi F01** `run-f01-after-f03.sh` (commit 52b8f68; chạy tách rời với nhãn `m56_f01_chain2`; lần khởi động `m56_f01_chain` gọi nhầm bash của WSL và thoát ngay mà không làm gì). Chuỗi chờ hàng đợi 3b và probe F03
xong, rồi:
1. prepare;
2. dựng revision;
3. compile, admission và contract;
4. **một** A/B (P5), chỉ khi FROZEN, ADMITTED và mọi contract OK;
5. ghép cặp dưới v13.

**Sửa trước khi chạy (09/11, chưa có số F nào):**
- Chuỗi `m56_f01_chain2` vẫn đang chờ, chưa chạy bước nào. Đã dừng đúng tiến trình bash của nó.
- Script đã sửa:
  - bỏ bước compile riêng, vì `--ab` tự compile, admit và kiểm contract trước episode;
  - bỏ mọi `timeout`, vì timeout giết giữa episode sẽ tiêu quota P5 và bỏ lại server mồ côi. Watchdog lo trường hợp treo.
- `native-f-ab.py` không còn tác dụng phụ khi import. Có thêm test compile offline `native-f-offline-check.py`: prepare giả trên
  trục x, drivable là một hộp. Kết quả: fixture compile được, cặp metric đúng `_F_CONTRACTS['F01']`, ba response qua
  `_forward_contract`, section brake ở trạm EGO 77,05 m (= 32,05 + 45).
- Kiểm XODR cả bốn site: section dài hơn mức cần, lệch trục tối đa 0,59° trên toàn cửa sổ, dốc tối đa 1,7%.
- Ghi F01-S1 vào `m56_asel2_replacements.jsonl`: 37/150.

**F05 và F06 bị chặn ở product, chưa phải ở recipe (09/11):**
- Guard creep F05 B (`_creep_stop_proof`, `_creep_guard`) và guard lùi F06 (`REVERSE_ALIGNMENT_UNSUPPORTED`) cùng đòi hai điều
  ở mọi khung hình:
  - route chỉ 2 điểm theo +x;
  - pose của actor có pitch/yaw/roll đúng bằng 0 và y bằng y của route.
- Hai guard này còn đòi một proof `CREEP_STOP_BOUND`/`REVERSE_STOP_BOUND` hiệu chỉnh sẵn. Docstring tự ghi rằng native
  qualification "cannot be obtained by this pure arithmetic producer".
- Native không bao giờ thỏa được các điều kiện này. Muốn có F05/F06 thì cần một version product mở rộng (consumer v14, công
  khai). Việc đó chưa làm.

**F02** (`F02_RECIPE_NOTES_20261109.md`, trước mọi số đo F02):
- `M56-P-F02` (Town12 R451) lấp slot trống. Trần thay cảnh: 38/150.
- Revision `outputs/m56_c0_partial_io_asel2fbase2_20261109T160045Z`, 44 candidate.
- Tooling đã tổng quát hóa:
  - prepare: lead/follower;
  - section theo trạm EGO;
  - box bắt đầu sau route khởi đầu muộn hơn;
  - script NPC F02;
  - builder EGO F02 lấy từ composition `f02_cases` của product.
- Test offline `native-f-offline-check.py`:
  - F01 cho cùng section và domain như trước khi sửa, nên chuỗi F01 không đổi hành vi.
  - F02 compile được, `F02_END − nominal_front_t0 = 60` đúng tuyệt đối, cặp metric khớp, ba contract OK.
- Chuỗi `run-f02-after-f01.sh` chờ `F01_END`.

**Thời gian raster ở hàng đợi 3b (09/11, 16:56 UTC):**
- A/B C02-S1 (Town12) vẫn ở raster dv1 sau khoảng 2 giờ. Đọc biến local qua py-spy được i = 270/436 (lưới 436 × 1249), tức khoảng
  62%. Ước tính raster mất 3,2 giờ cho một cảnh, nghĩa là khoảng 70 ms cho mỗi `cast_ray` trên Town12.
- Với khoảng 30 cảnh, hàng đợi 3b có thể chạy vài ngày. Tooling không được đổi giữa batch. Chưa có cách tăng tốc nào cho ra
  đúng y hệt các ô.

## Dừng an toàn 10/11 (yêu cầu của người dùng, khoảng 17:15 UTC ngày 09/11)

**Đã dừng** (chỉ các tiến trình của Claude):
- bash của hàng đợi 3b;
- các chuỗi chờ: probe F03, chuỗi F01 `m56_f01_chain3`, chuỗi F02 `m56_f02_chain`;
- A/B Town12 (`native-v2-ab.py`) cùng CarlaUE4 của nó trên cổng 2610;
- watchdog;
- lượt test offline v14.

Sau khi dừng, cổng 2610 trống.

**Trạng thái lúc dừng:**
- Log `outputs/m56_asel2_q3_20261109T145441Z/ab-Town12.log` chỉ có SCENES, SERVER_LAUNCHED và STREAM_TO (C02-S1). Lượt A/B vẫn
  đang ở raster dv1, khoảng 62%: chưa có FIXTURE, chưa có episode. **Chưa tốn quota P5 nào.** Raster khoảng 2 giờ của C02-S1
  phải chạy lại.
- Các chuỗi F01/F02 chưa chạy bước nào.
- Test regression v14 (18 file F03/F05/F06 tổng hợp) bị dừng ở khoảng 88%, chưa có test nào hỏng. Cần chạy lại.

**Chạy tiếp:** chạy một lần `bash run-asel2-resume-20261110.sh r1`.
- Script này khởi động lần lượt: watchdog, hàng đợi 3b (từ đầu), probe F03, chuỗi F01, chuỗi F02. Các bước nối với nhau qua
  marker trong stdout của nhãn mới.
- File chờ của các chuỗi giờ nhận biến môi trường `M56_WAIT_QUEUE`, `M56_WAIT_F03`, `M56_WAIT_F01`. Mặc định vẫn là nhãn cũ.

**Chạy tiếp 10/11, 02:49 UTC:** `bash run-asel2-resume-20261110.sh r1`. Các nhãn mới gồm `m56_asel2_watchdog_r1`,
`m56_asel2_queue_r1`, `m56_f03_probe_r1`, `m56_f01_chain_r1` và `m56_f02_chain_r1`, tất cả chạy bằng Git bash. Hàng đợi 3b chạy lại
Q1 từ đầu. Test regression v14 cũng được chạy lại.

## Quyết định F ngày 10/11 (Claude quyết dưới ủy quyền: "làm theo những gì bạn recommended")

**F06: `DIVERSITY_DEFICIT`** (`F06_IDEAL_SKETCH_20261110.md`, 2b6a987, trước mọi A/B).
- Phác thảo lý tưởng cho `g_front_min_m` là 4,8 so với 5,8 m, Δ = 0,172 < 0,20. Kết quả ghi đúng như prereg F §2 yêu cầu, không
  chỉnh gì.
- **Hệ quả cho release:** thiếu F06 thì chỉ còn tối đa 10 trên 15 phép so F, nên 46 cảnh và 155 phép so §11 **không còn đạt được**
  dù các cảnh khác ra sao. Từ đây mục tiêu là release partial trung thực, xếp việc theo số đếm mỗi việc thêm được.

**F05: chưa dựng.** Đây là quyết định ưu tiên, không phải `DIVERSITY_DEFICIT`, vì luật phác thảo trong prereg chỉ áp cho F06.
- Composition của chính product (`test_f05_complete.py`) khẳng định `NUMERIC_FAILED` với Δ 4/25 = 0,16.
- Phác thảo dùng động học native thật: EGO L02-S1 trên Town12 lên khoảng 1,9 m/s sau khoảng 0,3 s, rồi giữ khoảng 1,88 m/s. Theo
  phác thảo này, t_queue_exit của A ≈ 6,48 s và của B ≈ 4,99 s, nên Δ ≈ 0,23: chỉ sát ngưỡng.
- Chi phí của v14 cho F05 lớn hơn kế hoạch. Ngoài luật căn trục và hiệu chỉnh, mỗi tick còn phải kiểm lại toàn bộ history. Đo
  trên v14 lúc CARLA đang chạy: NPC 0,37–0,9 s mỗi lần gọi khi history khoảng 300 frame, EGO 2–3,7 s, có một lần vọt lên 19,9 s.
  Muốn chạy được thì cần thêm thay đổi kiểm tăng dần trong product.
- F05 có thể được làm lại sau, nếu mọi việc có lợi hơn đã xong.

**v14:** dừng ở phần 1 (luật căn trục, 0e2d233). Không merge cho tới khi giải thích được lỗi `BLOCKED_CONTROLLER` lúc có lúc không
trong composition F06. Lỗi xuất hiện một lần, lúc CARLA đang chạy, rồi không lặp lại.

**Bộ sinh realized F01/F02** (b6dfaa4): `native_f_realized.py` chỉ dùng hàm của product (`detect_events`, `runtime._ready`,
`_metric_station`, `world_vertices`), kèm `native-f-realized-check.py` (ALL_OK trên composition: F01 vN_char A/B 20/7 và 5, d0 15,95;
F02 vN_char 5, d0 20,95). Được commit trước mọi A/B F.

**Máy tắt 10/11 khoảng 03:46 UTC** (mọi tiến trình con chết với 0xC000026B, máy khởi động lại lúc 14:10 UTC). C02-S1 mới ở raster dv1,
chỉ có `a2-bbox.json`, chưa có FIXTURE hay episode, nên không dùng quota P5 nào. **Chạy tiếp 14:5x UTC:**
`bash run-asel2-resume-20261110.sh r2` (các nhãn `*_r2`). Hàng đợi 3b chạy lại Q1 từ đầu. Claude quyết dưới ủy quyền.

**Nguyên nhân máy tắt 10/11:** sự kiện Kernel-Power 105 lúc 03:14 UTC báo mất nguồn AC (AcOnline=false, pin 40146/43715 mWh).
Máy chạy pin dưới tải CARLA cho tới khi bị cắt cứng khoảng 03:39 UTC (Kernel-Power 41, bugcheck 0, không phải do nút nguồn hay
Windows Update). Khi chạy pin, máy còn ngủ sau 180 s rảnh; khi cắm AC thì không bao giờ ngủ. Nguyên nhân là nguồn điện, không phải
tải, nên các job offline vẫn chạy song song được. Đã gửi một thông báo nhờ giữ sạc cắm liên tục.

**F04': chưa dựng** (Claude quyết dưới ủy quyền, sau khi hỏi advisor). Đây là quyết định ưu tiên, giống F05, không phải
`BLOCKED_CAPABILITY` hay `DIVERSITY_DEFICIT`.
- F04 của product không phải khung dùng lại được. Nhánh NPC (`response.py` v13 khoảng dòng 528–545) bắt NPC đỗ yên: steer 0 và tốc
  độ ≤ 0,1. Nhánh này cấm thay cửa bằng PID stock. Vật cản lấy từ capability `door_geometry` (`calibrated-door-envelope-v1`), chạy
  xuyên evidence, metrics và response: khoảng 88 chỗ tham chiếu và 7 file test. Vì vậy F04' là một cơ chế mới, không phải biến thể.
- Bước "NPC lùi về" của A là lùi có đánh lái, nằm ngoài luật căn trục thẳng của v14 phần 1. Bản thân v14 cũng đang bị giữ.
- Trần lợi ích: +1 cảnh và tối đa +3 phép so (với F01, F02, F03), mỗi phép so chỉ có nếu cảnh kia cho cặp hợp lệ. Điều khiển ngang
  tốc độ thấp của stock đã từng hỏng ở O07, I05 và I07.
- Hệ quả: prereg F phần 2 chỉ còn F03, không cần 5 lập luận cặp F04'. Không chỉnh lại bản nháp cho vừa product.

**Thứ tự việc offline:** F03 B dùng lùi (`_reverse_inputs`), nên cần v14 khi chạy native. Vì vậy việc giải thích lỗi
`BLOCKED_CONTROLLER` lúc có lúc không của v14 nằm trên đường găng của F03 và được làm trước. Regression v14 đang chạy lại lúc 15:0x
UTC.

**Giải thích lỗi `BLOCKED_CONTROLLER` của v14** (CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent):
- Lần hỏng duy nhất (02:53 UTC 10/11, NPC frame 209, phase start 109/20) chạy trên đúng code đã commit 0e2d233. Sau commit không có
  sửa nào. Cùng code đó chạy sạch về sau: PYTHONHASHSEED 0–3 với cả A và B, `dbg_v14`, `time_guard14` (495 lần gọi). Vậy đây không
  phải lỗi logic phụ thuộc thứ tự hash. Các cache khóa theo `id()` (`response.py` 112, 231; `metrics.py` 281, 1049, 1147, 1173) đều
  kiểm `is` hoặc giữ weakref nên không thể dùng nhầm id.
- Lần hỏng đó bắt đầu 4 s sau khi r1 khởi động CARLA, lúc Town12 đang nạp và RAM cùng I/O chịu tải nặng nhất. `evidence._source_bytes`
  đổi mọi `OSError` thành `None`, nên kiểm reverse fail-closed thành `ValueError` rồi thành `BLOCKED_CONTROLLER`. Code này giống hệt
  v13; v14 chỉ sửa `response.py`.
- Tiêm một `OSError` tạm thời (WinError 1450) vào lần đọc `_source_bytes` đầu tiên trong lời gọi NPC ở frame 209 (file
  `frozen-stop-NPC.json`) tái hiện **đúng y** chữ ký `(209, 'NPC', BLOCKED_CONTROLLER, start=109/20)`.
- Kết luận: cơ chế đủ để gây lỗi và tái hiện chính xác. Nguyên nhân trực tiếp (lỗi đọc I/O tạm thời lúc thiếu tài nguyên) chưa quan
  sát được, chỉ suy ra. Đây không phải hồi quy logic của v14, nên v14 không còn bị giữ vì lỗi này; còn chờ kết quả regression.
- Rủi ro native: một lỗi đọc tạm thời trong episode sẽ thành `BLOCKED_CONTROLLER` và tốn quota P5. Đường lùi đọc lại nguồn frozen ở
  mỗi tick nên phơi nhiều hơn. Biện pháp vận hành: không chạy job offline nặng song song với episode F native.

**Đính chính mục trên** (sau khi hỏi advisor):
- Sai về thời điểm. r1 khởi động CARLA lúc 02:49:15 và có STREAM_TO lúc khoảng 02:51; lần hỏng bắt đầu lúc 02:53:42, tức 4,5 phút sau
  khởi động. Lúc đó Town12 đã nạp xong và đang raster, giống hệt điều kiện của các lần chạy sạch sau này. Lập luận "đỉnh tải lúc nạp
  map" bị rút lại.
- Phép tiêm chỉ chứng minh một lỗi đọc là **đủ** để gây lỗi. `start=109/20` chỉ là simtime của frame 209, nên mọi ngoại lệ bị bắt
  trong lời gọi NPC frame 209 đều cho cùng bộ giá trị đó.
- Trạng thái v14: **chưa kết luận**, vẫn bị giữ. Phép thử phân biệt là chạy lại B trên đúng thư mục gốc tạm của lần hỏng
  (`tmpyuq43w6i`) qua nhiều hash seed.
- Không thêm retry vào `_source_bytes`: nguyên nhân chưa quan sát được, và đây là đường fail-closed dùng chung cho mọi category.
- Quy tắc vận hành được mở rộng: không chạy job offline nào trong lúc có bất kỳ episode native nào, không riêng F.

**Phép thử phân biệt lỗi v14** (`outputs/m56_v14_flake_diag/`, gồm `fixed_root.py` và `seed0..7.log`):
- Cách chạy: arm B chạy trên đúng thư mục gốc tạm của lần hỏng (`%TEMP%\tmpyuq43w6i`), với PYTHONHASHSEED 0–7.
- Kết quả: **8/8 OK**. `observed-149.json` hash `98dc07a4…` ở cả 8 lần, trùng với traceback của lần hỏng, nên byte input được tái hiện
  y hệt.
- NPC đọc `frozen-stop-NPC.json` lần đầu ở frame 149 và đọc lại mỗi frame sau đó, nên frame 209 không phải ranh giới đường code.
- Kết luận: loại trừ được logic phụ thuộc dữ liệu hoặc thứ tự hash. Cách đọc "lỗi môi trường, tức một lần đọc nguồn thất bại tạm
  thời" vẫn đứng vững, nhưng **vẫn chỉ là suy luận**, vì nguyên nhân trực tiếp chưa quan sát được.
- v14 không còn bị giữ vì lỗi này, chỉ chờ regression. Quy tắc vận hành giữ nguyên: không chạy job offline trong episode native.
  `_source_bytes` giống hệt nhau trên v1, v12, v13 và v14.
- Ghi chú vận hành: scratchpad của phiên trước bị dọn giữa chừng lúc khoảng 15:56 UTC. Các log và chẩn đoán từ giờ đặt trong
  `outputs/`.

**Regression v14** (0e2d233, `outputs/m56_v14_flake_diag/v14_regression.txt`): `tests/m56/test_f0[356]*.py` và `test_v14_*.py`
cho **189 passed** sau 1:03:07. v14 phần 1 đã sẵn sàng để merge cho F03, nhưng chỉ merge sau khi grade probe và prereg F phần 2 của
F03 xong. Claude quyết dưới ủy quyền.

**File STOP cho hàng đợi và dừng an toàn sáng 11/11** (Duy yêu cầu: "thêm file stop cho hàng đợi, tôi cần dừng an toàn vào lúc 8h
sáng mai để tắt máy"):
- **Công cụ mới:** `asel2-stopper.py`, kèm `asel2-stopper-check.py` (ALL_OK). Script chạy song song với hàng đợi chứ không sửa script
  bash đang chạy, vì bash đọc script dần trong lúc chạy.
- **Cách kích hoạt:** tạo file `outputs/m56_asel2_STOP` (dừng êm), hoặc để tới giờ `--at`. Nội dung file là `now` thì dừng ngay, kể
  cả giữa episode: cảnh đó thành INFRA_INTERRUPTED và mất quota.
- **Khi nào không an toàn:** cảnh mới nhất của một job A/B native đã có `fixture-frozen.json` nhưng chưa có `ab-result.json`; hoặc có
  `native-v6-pair` / `native-v5-revision` đang chạy. Với io và f, toàn bộ đoạn từ fixture tới cảnh kế tiếp được coi là không an toàn,
  cho chắc.
- **Cách dừng:** chỉ kill tiến trình của mình, theo thứ tự bash chuỗi, rồi python, rồi CarlaUE4 trên 2610. Sau đó ghi
  `outputs/m56_asel2_stop_<utc>.json` (trạng thái từng cảnh) và `outputs/M56_SAFE_TO_SHUTDOWN.txt`.
- **Đã khởi động:** nhãn `m56_asel2_stopper_r2`, `--at 2026-11-10T23:45:00Z` (06:45 giờ máy). Trường hợp xấu nhất là một episode
  window khoảng 55 phút, nên dừng xong trước 08:00. Claude quyết dưới ủy quyền.
- **Khi chạy tiếp sau lần dừng này,** hàng đợi 3b **không** được chạy lại từ đầu, vì các A/B đã chạy thì đã tốn quota P5. Cần một
  resume bỏ qua những cảnh DONE, dựa trên bản ghi dừng.
- Lưu ý: checkpoint của watchdog đánh dấu AB_STARTED cho mọi cảnh có mặt trong sự kiện SCENES, nên không được dùng nó một mình để
  chạy tiếp.

## Kết quả Q1 r2, Town12 (`outputs/m56_v2_ab_Town12_20261110T145403Z`, chấm cặp v12, CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent)

| Cảnh | Cặp v12 | Δ của 2 metric | Ghi chú |
|---|---|---|---|
| C02-S1 | **PASS** | ≈0,782; 55/207 ≈ 0,266 | raster dv1 mất khoảng 3,5 h; CLEAR_N có xảy ra |
| L02-S1 | **PASS** | ≈0,898; 59/195 ≈ 0,303 | |
| L05-S1 | **PASS** | ≈0,866; 45/149 ≈ 0,302 | |
| M06-S1 | FAILED | –; – | A: CONTACT_PROOF_INVALID, không có CLEAR_N, E_ENTRY và DESTINATION. B: EARLY_ENTRY_BEFORE_NPC_CLEAR, CONTACT_PROOF_INVALID |

- **Điều kiện kèm theo:** các cặp PASS này được tính dưới các luật A-SEL2 hậu-số (addendum 8: x/y 1 mm; addendum 9: outer 1500 s;
  dv1). Dưới luật đóng băng gốc thì không cặp nào hợp lệ (nguyên tắc 6).
- **Tổng hiện tại:** 13 cặp hợp lệ có điều kiện (10 cặp cũ cộng C02-S1, L02-S1, L05-S1).
- **M06-S1:** đã dùng hết quota P5 trên phiên bản này. Theo B3 nó là ứng viên thay bằng successor (cổng B5); việc thay được quyết sau
  khi xong Q1. Không tinh chỉnh gì sau thất bại.

**Sửa công cụ dừng và chạy tiếp** (sau khi advisor rà; Claude quyết dưới ủy quyền):
- **Queue 3c:** cổng chặn đọc stdout của mọi lượt chạy `m56_asel2_queue_r*`. Việc này ngăn lượt chạy tiếp thứ hai chạy lại Q2/Q3 từ cảnh
  đầu.
- **`asel2-q1-remaining.py`:** nhãn lấy từ sự kiện trong log `ab-<Town>.log`. Các cảnh SCENE_ERROR, BLOCKED_FIXTURE, NOT_ADMITTED,
  INFRA_INTERRUPTED và NO_RUN_DIR đều bị SKIP. Chạy lại bất kỳ cảnh SKIP nào phải là một quyết định có ghi log.
- **`asel2-stopper.py`:**
  - Chế độ compile của io-ab và f-ab (không có `--ab`) được coi là an toàn.
  - Root cũ hơn `--since` bị bỏ qua.
  - `--at` không còn bắt buộc.
  - `M56_SAFE_TO_SHUTDOWN.txt` chỉ được ghi khi không còn tiến trình nào và cổng 2610 đã đóng.
  - Bản kiểm tra vẫn ALL_OK.
- **`run-asel2-resume-20261111.sh`:** đổi tên (không xóa) file SAFE và STOP cũ, rồi khởi động một stopper chỉ chạy theo file STOP.
- **Stopper tối nay** được thay bằng `m56_asel2_stopper_r2b`, `--at 2026-11-11T00:00:00Z` (07:00 giờ máy). Bằng chứng từ Town12: 4 cảnh
  hết 63 phút, mỗi cửa sổ episode khoảng 10–15 phút, chấm cặp khoảng 5 phút mỗi cảnh. Vì vậy thường dừng xong trước khoảng 00:30Z;
  trường hợp xấu nhất vẫn trước 01:00Z (08:00).
- **Còn mở:** nếu lần dừng sau rơi vào Q2/Q3 (io/cl2) thì cần một resume dựa trên bằng chứng cho hai bước đó. 3c sẽ từ chối chạy.

**Bằng chứng cho câu "không cặp nào hợp lệ dưới luật đóng băng gốc"** (Town12, r2): theo `ab-Town12.log`, sự kiện AB của C02-S1,
L02-S1, L05-S1 và M06-S1 đều có `old_initial_rule_failures = ['EGO','NPC']` ở cả A và B. Nghĩa là trạng thái ban đầu x/y vi phạm luật
1e-4 cũ (addendum 8 nới thành 1 mm), nên dưới luật cũ cả 4 episode đều không hợp lệ.

## Dừng an toàn 11/11, 00:00:14 UTC (07:00 giờ máy)

- Stopper `m56_asel2_stopper_r2b` dừng vì tới giờ (TIME). Bản ghi: `outputs/m56_asel2_stop_20261111T000014Z.json`.
- Đã kill 10 tiến trình của mình. Không còn tiến trình nào sót lại, cổng 2610 đã đóng, `M56_SAFE_TO_SHUTDOWN.txt` đã được ghi.
- Trạng thái lúc dừng: Q1 Town12 xong 4/4, đã chấm cặp. Town13: C07-S1 đang ở raster dv1 (khoảng 4 h 10 phút, chưa có FIXTURE),
  nên **không tốn quota nào**. L03, L06, M01 và M03 chưa bắt đầu.
- **Chạy tiếp:** `bash run-asel2-resume-20261111.sh r3`, chạy một lần từ thư mục tooling. Kế hoạch của queue 3c lúc dừng: Town12 SKIP
  4/4 (đã chấm cặp); Town13 RUN C07-S1, L03-S1, L06-S1, M01-S1 và M03-S1. Sau đó là Q2 I/O, Q3 batch 2, F03, F01, F02 như queue 3b.
- Raster của C07-S1 phải chạy lại từ đầu, mất khoảng 4 h hoặc hơn.
