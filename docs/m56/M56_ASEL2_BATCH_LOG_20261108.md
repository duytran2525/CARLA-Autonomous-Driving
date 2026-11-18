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

## M06-S1: nguyên nhân hỏng và thay cảnh lần 5 (11/11, Claude quyết dưới ủy quyền)

**Đính chính:** dòng "M06-S1 FAILED (contact)" ở commit `60f1779` chưa đủ. Có hai nguyên nhân độc lập, cùng xuất hiện ở cả A và B, cùng
các frame. Chẩn đoán chỉ đọc episode đã niêm phong, dùng consumer v12.

1. **NPC không bao giờ CLEAR_N** (hình học của site, đúng như addendum F dự báo cho cảnh lệch trục):
   - Mặt `n_exit` là một mặt của hộp thẳng trục, rộng 4,3 m theo x. NPC đi chéo 13–25° (yaw −103 … −115).
   - Ở frame thứ 442, NPC vượt mặt phẳng `n_exit` (margin 0,13 m). Lúc đó hình chiếu thân xe đã chìa ra ngoài bề rộng mặt cắt
     (`_section_corridor` = False). Từ frame 446 margin ≥ 0,5 m, nhưng hành lang không bao giờ đúng trở lại.
   - Spec §5.2 đòi điều kiện "correct corridor" khi clear, và erratum 5 cố ý giữ nó. Vì vậy **không sửa consumer**.
   - Hệ quả online: A dừng chờ CLEAR tới hết episode (INCOMPLETE). B vào hộp khi NPC chưa clear (`EARLY_ENTRY_BEFORE_NPC_CLEAR`,
     FAILED). Đánh giá lại offline không cứu được, vì controller của A đã chờ đúng event này lúc chạy.
   - Cùng cơ chế, đo lại: C04-S1 và L07 có đúng 2–3 frame hành lang đúng sau vượt mặt (0,10–0,15 s < hold 0,25 s). C03-S1 không có
     frame nào.
2. **CONTACT_PROOF_INVALID và CONTINUOUS_FIT_UNPROVEN:**
   - Có 113 interval với `minimum_road_edge_m` dưới 0,15 m (nhỏ nhất 0,03 m), ở frame 244–356.
   - Phép kiểm fit theo từng actor (`_oriented_fit` trên vùng drivable dv1) cho thấy **NPC** gây ra: 108 interval, đúng lúc NPC
     đang rẽ từ yaw −162 sang −108.
   - M07 (Town05, 08/11) có đúng mẫu này: NPC, 117 interval, trong lúc rẽ. Không cảnh M nào từng PASS.
   - **Rủi ro đã biết, chưa có cổng:** B5 chỉ chặn được nguyên nhân 1. Cảnh thay M06-S2 có NPC rẽ phải 89,9°, nên có thể hỏng giống
     nguyên nhân 2. Một cổng chọn mới cho lỗi này sẽ là luật đặt sau khi thấy số (nguyên tắc 6), phải có addendum riêng. Claude
     **không** đặt cổng đó ở đây.

**Thay cảnh lần 5 (B3):**
- Lần thay này được dời từ "sau Q1" lên bây giờ theo yêu cầu của người dùng. Thứ tự B3 không phụ thuộc kết quả Town13 Q1.
- Theo addendum C: M04 và M07 đang được giữ ở dạng S2, nên lần thay này chỉ có M06.
- State `outputs/m56_asel2_replace_state_5.json` = state 4, cộng hai site đề xuất ở replace 4 (C03-S2 Town13 J4753, C04-S2 Town12
  J9428) vào `assigned` và `tried`. M06-S1 (Town12 J13615) đã có sẵn trong `tried`. Giữ chain = true và axis = true (B5).
- Lệnh: `fill-v4-generate.py outputs/m56_fill_v4_replace5_20261111.json ceb87fa --replace outputs/m56_asel2_replace_state_5.json`.
  - Kết quả: sha256 `c2175bf3`, pool như replace 4 (C 3676, L 1964, M 899).
  - Ứng viên: **M06 → Town12 J18974**, rule lookahead. EGO 322/+2→18996/+2→321/+2; NPC 529/-1→18980/-1→321/+2 (rẽ phải
    −89,9°). Descriptor: vN 2,4, G 25, LrefN 15,27. Số ứng viên bị B5 loại: 353.
- `m56_asel2_replacements.jsonl`: M56-P-M06-S2, consumed 1, used_after 39.
- `run-asel2-queue3c.sh` (chưa chạy lúc sửa): Q3 thêm `replace5` vào `M56_ASEL2_REPLACE`, và thêm `M56-P-M06-S2` vào cuối danh sách
  Town12. Bộ dựng revision tự đặt id S2 (vòng thay đầu tiên của slot M06). Bước chuẩn bị và đúng một A/B chạy như các cảnh khác
  trong batch 2.
- Nhãn: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## Chạy tiếp r3 (11/11 14:59Z) và hẹn dừng an toàn sáng 12/11

- `run-asel2-resume-20261111.sh r3` lúc 14:59:40Z. Q1 Town12 SKIP 4/4 (đã chấm cặp); Town13 RUN 5. Log `outputs/m56_asel2_q3_20261111T145942Z`.
- Người dùng yêu cầu chạy tới 9 h sáng 12/11 rồi dừng an toàn. Claude quyết dưới ủy quyền: đặt `--at 2026-11-12T01:45:00Z` (08:45 giờ
  máy), để việc chờ điểm an toàn vẫn xong quanh 9 h.
- **Sửa lỗi stopper** (phát hiện bằng `--dry` trước khi tới giờ):
  - `procs()` crash vì một tiến trình của phiên khác có dòng lệnh không phải UTF-8. Lúc đó `stdout` là None, nên `AttributeError`.
  - Stopper r3 (chỉ theo file STOP) và stopper hẹn giờ vừa chạy đều sẽ crash lúc kích hoạt, tức là **không dừng được**.
  - Cách sửa: PowerShell xuất UTF-8, decode với `errors='replace'`, và lỗi liệt kê tiến trình chỉ thử lại ở lượt poll sau, không làm
    chết vòng lặp.
  - Kiểm: `asel2-stopper-check.py` ALL_OK; `--dry` trên máy thật liệt kê đúng 11 tiến trình M56, không có tiến trình nào của phiên
    khác.
  - Hai stopper cũ (pid 37316, 39624, đã kiểm cmdline) được kill. Thay bằng `m56_asel2_stopper_r3u` (file STOP + `--at 01:45Z`,
    `--since 14:59Z`).

## Dừng an toàn 12/11, 01:45:20 UTC, và tech fix 5 (raster synchronous)

**Dừng:**
- Stopper `m56_asel2_stopper_r3u` dừng vì tới giờ (TIME). Bản ghi: `outputs/m56_asel2_stop_20261112T014520Z.json`.
- Đã kill 10 tiến trình của mình. `left = []`, cổng 2610 đã đóng, `M56_SAFE_TO_SHUTDOWN.txt` đã được ghi.
- **Không có cặp mới.** C07-S1 (cảnh đầu tiên của Town13) nằm 10 h 43 phút ở raster dv1. Trạng thái NO_FIXTURE, nên không tốn
  quota nào. L03, L06, M01 và M03 chưa bắt đầu.

**Nguyên nhân** (probe `native-raster-speed-probe.py`, log `outputs/m56_raster_speed_probe_Town13_r2.stdout.txt`, Town13 nạp mới, tại
tâm C07):
- Ở chế độ async, mỗi `cast_ray` mất 230–670 ms và mỗi `get_settings` mất 250–790 ms, tức mỗi RPC phải chờ một frame của server. Sau
  12 phút vẫn không nhanh hơn.
- Ở chế độ synchronous, không tick: 4,3–4,5 ms mỗi ray, 0,17 ms mỗi RPC. Sau 200 tick vẫn vậy.
- Quay lại async thì lại chậm (445 ms).
- Raster cảnh đầu sau `load_world` chạy ở async, nên mới chậm hàng giờ.

**Tech fix 5** (chỉ hiệu năng; Claude quyết dưới ủy quyền):
- Trong `native_v2_common.drivable_union`, nếu server đang async thì chuyển sang synchronous (dt 0,05 s), tick một lần, chạy
  raster, rồi khôi phục cài đặt cũ trong `finally` và `wait_for_tick`.
- Lưới, tia, thứ tự quét và nhãn đều giữ nguyên. Cả `native-v2-ab`, `native-io-ab` và `native-f-ab` đều đi qua hàm này.

**Kiểm** (`native-raster-sync-check.py`, Town12 server mới, log `outputs/m56_raster_sync_check_Town12_20261112.stdout.txt`): tính lại
drivable union của các cảnh r2 với code mới, rồi so từng byte WKT với file A/B đã ghi.

| Cảnh | Thời gian | Kết quả |
|---|---|---|
| C02-S1 (cảnh đầu, trước mất 13.776 s) | **43,0 s** | **SAME**, sha `e177dafa5675a709`, 177.127 byte |
| L02-S1 | 38,2 s | **SAME**, sha `d36d08db07bd0b80`, 182.745 byte |

Settings trước và sau raster đều async (đã khôi phục đúng).

**Hệ quả:**
- Không cảnh nào đổi ô raster. Các kết quả cũ giữ nguyên.
- Kiểm này chưa làm trên Town13 vì chưa có WKT tham chiếu. Lý do giống hệt: cùng hàm, cùng lệnh RPC.
- Hàng đợi **chưa** chạy tiếp, theo yêu cầu của người dùng. Lệnh chạy tiếp khi được phép: `bash run-asel2-resume-20261111.sh r4`.

## Đêm 12→13/11: Q2/Q3 chạy, dừng an toàn 23:44:46Z, và chạy tiếp 13/11 (Claude quyết dưới ủy quyền)

Kết quả đêm qua: xem `outputs/m56_asel2_queue_r5.stdout.txt` và `outputs/m56_asel2_stop_20261112T234446Z.json`. Dừng an toàn, không scene nào bị cắt giữa episode.

| Nhóm | Kết quả |
|---|---|
| Q2 O05-S1, O07-S1 | FAILED |
| Q2 O06 | BLOCKED_WITNESS |
| Q2 I08, O04-S1 | prepare `RUNIN_NOT_STRAIGHT` (35,59 m và 46,15 m): scene không đạt, chưa tốn A/B |
| Q2 O08-S2 | BLOCKED_FIXTURE, chưa tốn A/B |
| Q3 Town12 C04-S2 | PASS theo pair chạy với v12 (`pair-v10.log` của cl2 thực chất chạy `M56_CODE=v12`), BLOCKED_WITNESS theo v10abs và v6. Báo cả hai cách (nguyên tắc 6) |
| Q3 Town12 L08-S1, M05-S1, M08-S2 | FAILED |
| Q3 Town12 M06-S2 | BLOCKED_WITNESS |
| Q3 Town12 M07-S2, Town13 M04-S2 | BLOCKED_FIXTURE (không có đèn tín hiệu; probe không có frame), chưa tốn A/B |
| Q3 Town13 C03-S2, C06-S1, L07-S2, M02-S1 | A/B xong, chưa pair khi dừng |

**Nguyên nhân I01-S1, I02-S2, I05-S1, I06, I07-S1 không chạy A/B:** lỗi tooling, không phải lỗi scene. `run-asel2-io.sh` gọi `native-io-selfcheck.py` cho mọi scene, mà self-check này chỉ viết cho loại O (`a.phases['reference_switches']` của EGO A). Với loại I, đổi làn là của EGO B nên `KeyError`. Prereg io-i-v1 mục j nói rõ: "Self-check và replay của O chưa có bản cho I; admission là cổng offline". Cả 5 fixture đều FROZEN và ADMITTED, chưa có thư mục `m56_io_ab_*` nào của chúng, nên lượt A/B P5 còn nguyên.

**Quyết định (Claude quyết dưới ủy quyền, không độc lập):**
1. Bỏ self-check O cho loại I (đúng prereg j); cổng là admission.
2. Chạy chỉ bước `--ab` trên revision có sẵn `m56_c0_partial_io_asel2ioprep_20261112T144015Z`, không prepare lại, không chạy lại queue 3c (nó sẽ chạy lại các A/B đã tiêu P5). Script `run-asel2-resume2.sh`: ghép cặp 4 scene Town13 Q3 dưới v12, rồi I01-S1 làm canary, các scene I còn lại chỉ chạy nếu canary tạo được thư mục `run`.
3. `run-asel2-cl2-pair-town13.sh` chạy pass đầu mà không đặt `M56_CODE` (mặc định là gói m56 của worktree v1), nên nhãn `pair-v10.log` của lần chạy đó không phải v12. Kết quả chuẩn lấy từ pass v12 của resume2 (`pair-v12-town13q3.log`), pass v10abs và v6 giữ nhãn thật.

## Kết quả resume2 (13→14/11, Claude quyết dưới ủy quyền; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent)

**Town13 Q3 (pair xong):** C03-S2, C06-S1, L07-S2 = **PASS theo v12**; BLOCKED_WITNESS theo v10abs và v6 (`m56_asel2_cl2p_20261113T135745Z/pair-v10abs.log`, `pair-v6.log`). M02-S1 = BLOCKED_WITNESS ở mọi quy tắc (A và B INCOMPLETE, thiếu E_ENTRY và DESTINATION). Theo nguyên tắc 6 báo cả hai: **19 cặp theo v12** (15 + C04-S2 + 3 cảnh này), nhưng 4 cặp mới (C04-S2, C03-S2, C06-S1, L07-S2) chỉ PASS theo v12, BLOCKED_WITNESS theo v10abs/v6.

**Q1 Town13 (12/11):** L03-S1 và L06-S1 PASS; C07-S1 FAILED; M01-S1 FAILED (COLLISION_OBSERVED ở cả A, B); M03-S1 BLOCKED_WITNESS.

**5 cảnh I, A/B chạy 1 lần mỗi cảnh, tất cả không thành cặp. Lượt P5 của cả 5 đã tiêu:**

| Cảnh | Pair | Lý do |
|---|---|---|
| I01-S1 | không ghép được (`EPISODE_NOT_SEALED:A`) | Cả A và B dừng ở `runner/stop.json`: `READINESS_NOT_REACHED`; xe chưa tới ready markers |
| I02-S2 | BLOCKED_WITNESS | `INITIALIZATION_INVALID`, `X_END_MISSING` ở cả A và B |
| I05-S1 | FAILED | A: COLLISION_OBSERVED, RESUMED_BEFORE_NPC_MERGED_AHEAD; B: INCOMPLETE (X_END_MISSING) |
| I06 | FAILED | A: COLLISION_OBSERVED, RESUMED_BEFORE_NPC_MERGED_AHEAD; B: COLLISION_OBSERVED, CHANGED_BEFORE_SOURCE_CLEAR |
| I07-S1 | FAILED | A: COLLISION_OBSERVED, UNPLANNED_LANE_CHANGE, RESUMED_BEFORE_NPC_MERGED_AHEAD; B: COLLISION_OBSERVED, CHANGED_BEFORE_SOURCE_CLEAR |

**Sai sót của Claude:** cổng canary tôi đặt trong `run-asel2-resume2.sh` chỉ kiểm có thư mục `run`. I01 có thư mục `run` nhưng cả hai episode dừng ở `READINESS_NOT_REACHED`, nên cổng không chặn và 4 cảnh I còn lại vẫn chạy (đều tiêu lượt P5). Cổng đúng phải đọc `runner/stop.json` của từng episode. Ba cảnh I05, I06, I07 cùng một chữ ký (A tiếp tục trước khi NPC nhập làn, B đổi làn trước khi làn nguồn trống, rồi va chạm), nên có thể là giới hạn của recipe I chứ không phải lỗi từng cảnh. Chưa điều tra sâu.

**Kiểm tra sha:** fixture của A/B khác fixture lúc compile ở cả O05, O06, O07 (đã chạy 12/11) lẫn 5 cảnh I, nên khác sha là bình thường do biến chỉ có ở bước A/B, không phải lệch harness.

**Quyết định:**
1. Không chạy lại cảnh I nào. Không lấy cảnh I từ ngân sách thay thế B3 cho tới khi có phiên bản recipe I mới được ghi nhận và được Duy duyệt.
2. `run-asel2-io.sh` bỏ self-check cho loại I (prereg io-i-v1 j). Hai script `run-io-compile.sh` và `run-io-prepare.sh` chỉ in kết quả, không chặn, nên để nguyên.
3. Chuỗi F (F03 → F01 → F02) chạy từ 14/11 00:50Z với nhãn `r7` (marker `m56_fq_marker_r7` thay `QUEUE3B_DONE`), vì queue 3c không được chạy lại (sẽ lặp lại các A/B đã tiêu P5).

## Chuỗi F r8 (14/11/2026 10:49–11:00Z) và điều tra

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Chạy:** chuỗi r7 chết mà không chạy bước nào (stdout F01/F02 rỗng). Chạy lại thành r8 (`m56_f01_chain_r8`, `m56_f02_chain_r8`, chờ marker của `m56_f03_probe_r7`).
- F01 (Town13, M56-P-F01-S1, road 1165 lane -2): `BLOCKED_FIXTURE` `PROBE1_NOT_STEADY`. Log `outputs/m56_f01_20261114T104923Z`, prepare `m56_v2_prepare_Town13_20261114T104925Z`.
- F02 (Town12, M56-P-F02): `BLOCKED_FIXTURE` `PROBE1_NOT_STEADY`. Log `outputs/m56_f02_20261114T105524Z`, prepare `m56_v2_prepare_Town12_20261114T105525Z`.
- Không A/B nào chạy, nên **không tiêu lượt P5 nào**.
- Lý do `READINESS_NOT_REACHED` ở dòng PROBE là theo thiết kế: `probe()` đặt target 1000 m/s nên probe không bao giờ "ready". Thứ chặn là phép thử steady.
- Bước revision của cả hai chuỗi lỗi `FileNotFoundError` vì script archive đã chuyển `m56_offline_v1` vào thùng rác (lỗi của Claude). Root này đã được đưa về chỗ cũ; lỗi đó không đổi kết quả hai cảnh vì cả hai bị chặn trước bước revision.

**Nguyên nhân gốc:** `native-f-prepare.py` dòng 149 dùng `steady_time(p1, role, nominal)`, tức đòi |v − tốc độ danh nghĩa| ≤ 0,05 m/s suốt 1 s. Bộ điều khiển stock luôn ổn định dưới mức danh nghĩa:
| Cảnh | Xe | Danh nghĩa | Plateau đo được | Biên độ 2 s cuối |
|---|---|---|---|---|
| F01 | EGO | 4,0 | 3,862 | 0,0001 |
| F01 | NPC | 3,4 | 3,265 | 0,0001 |
| F02 | EGO | 4,0 | 3,864 | 0,0002 |
| F02 | NPC | 5,0 | 4,847 | 0,1545 (dao động 4,77–4,92) |

Mọi preparation C/L/M/I/O đều dùng luật khác: đo plateau (biên độ ≤ 0,10 m/s), thử lưới PID khi cần, rồi lấy plateau đo được làm target readiness. Ví dụ cảnh PREPARED: EGO danh nghĩa 4,0 → target 3,862–3,866 (C03-S2, C04-S2, C06-S1, M02-S1, M05-S1, M06-S2, M08-S2). Nên F là ngoại lệ, và với luật hiện tại F không bao giờ qua được. Dòng 166 (target probe 2 = danh nghĩa) cũng sẽ chặn y như vậy.

**Thử lại offline luật plateau trên bản ghi probe 1:**
- F01: plateau EGO 3,862, NPC 3,265, cả hai steady (EGO sau 7,55 s, NPC sau 5,05 s). Sẽ qua.
- F02: EGO qua; NPC dao động 0,15 m/s, không có cửa sổ 2 s nào đạt ≤ 0,10, nên cần lưới PID NPC (`NPC_PID_GRID`) như C/L/M/I/O.
- Khoảng hở lúc ready chưa tính lại offline (cần routes).

**Consumer v13:** `_f_script_contract` chỉ kiểm tốc độ *lệnh* của NPC (F01: 3 hoặc 17/5; F02: 5). Tốc độ lệnh giữ nguyên, nên đổi target readiness sang plateau đo được không chạm contract. Chưa chạy `native-f-offline-check.py` với target đo được.

**Ghi chú khác:** bước prepare của F01/F02 chạy *trước* dòng `export M56_RECIPE=v6 M56_DRIVABLE=dv1`, nên bản ghi prepare không có `m56_recipe: v6` (chuỗi I/O export v6 trước). F03 `ok: false` ở cả 6 mẫu là câu hỏi riêng (probe độ dốc), chưa phân tích.

**Đề xuất (chưa làm, chờ Duy duyệt):** recipe f-v1.1, ghi là luật sau-số (nguyên tắc 6), không sửa byte prereg:
1. Probe 1: thay `steady_time` theo danh nghĩa bằng `P.plateaus` + lưới PID (EGO rồi NPC) + `P.steady_at` theo plateau, đúng như `native-io-prepare.py`.
2. Probe 2: target readiness = plateau đo được ở probe 2 (làm tròn 1/1000), như C/L/M/I/O.
3. Giữ tốc độ danh nghĩa trong các công thức hình học (F01 brake start = mũi NPC + 3 s · vN; F02 khoảng hở 21 m; `nominal_front_t0_m`), vì đó là thay đổi nhỏ nhất.
4. Export `M56_RECIPE=v6 M56_DRIVABLE=dv1` trước bước prepare.
5. Test offline (`native-f-offline-check.py`) rồi mới chạy native: F01 trước, đọc `runner/stop.json` của cả hai episode và kết quả pair, rồi mới tới F02. Tạm dừng archive trong lúc A/B.
Kết quả f-v1 (cả hai BLOCKED_FIXTURE) được giữ trong hồ sơ.

**Archive Drive (sửa lỗi của Claude):** script archive đã chuyển cả root còn đang dùng. Đã dừng (r2), đưa về chỗ cũ 12 root đợt A-SEL2 (dấu thời gian ≥ 20261108) và 27 root chứa `run/` của các cảnh từng PASS (`asel2-release.py --full` cần đọc lại episode đã niêm phong). Danh sách: `outputs/m56_drive_archive_restored_in_place_20261114.txt`. Archive r3 bỏ qua các root đó, root không có dấu thời gian, và giữ thêm `runner/stop.json` tại chỗ.

**Cập nhật 14/11 ~12:20Z:** Duy duyệt f-v1.1 ("làm theo hướng bạn đề xuất"). Đã làm (commit 412f9b6 + script chia hai bước):
- `native-f-prepare.py`: luật plateau + lưới PID như I/O, target probe 2 = plateau đo được; `recipe_rev: f-v1.1` trong prepare.json (trường `recipe` vẫn `f-v1` để revision và native-f-ab nhận).
- `native-f-ab.py`: gắn PID mà preparation đã chọn (như native-io-ab).
- Kiểm offline: `native-f-offline-check.py` với target đo được (F01 3,862/3,265; F02 3,862/4,847) cho F01 và F02 đều `ALL_OK`. Revision offline trên prepare r8 với env mới chạy được (F01 BLOCKED như mong đợi). Chương trình trước readiness của A/B (EGO A/B và `f_npc`: SETTLE 0 → NOMINAL sau CAPTURE_START + 21/20 s) trùng chương trình probe.
- `run-f01-v11.sh`: bước 1 = prepare → revision → compile/admission (không episode), dừng để đọc; bước 2 (`ab <REVF>`) = A/B duy nhất (P5) + pair v13, đọc `run/episodes/<scene>/{A,B}/runner/stop.json`. F02 chỉ chạy sau khi đọc kết quả F01.

**F01 f-v1.1 bước 1 (14/11 12:18–12:45Z):**
- Prepare `m56_v2_prepare_Town13_20261114T121821Z`: **PREPARED** (lần đầu một cảnh F qua prepare native). PID stock (EGO/NPC range 0,0001 m/s); target 3,862 / 3,265 m/s; marker EGO 10,117, NPC 8,987; T_r 4,85 s; `m56_recipe: v6`.
- `d0_realised_m` = **12,96 m** so với d0 đăng ký 11,4 m. Nguyên nhân: shift tính từ thời điểm steady ở probe 1 (`steady_at`), còn readiness ở probe 2 là `first_ready` (sớm hơn ~2,6 s); NPC chậm hơn EGO ~0,6 m/s. Có sẵn trong thiết kế f-v1, không do f-v1.1. Chưa quyết: chạy A/B với d0 thực tế (báo nguyên giá trị) hay sửa prepare cho khớp 11,4 m (chạy lại prepare không tốn P5). Chờ Duy.
- Revision lần đầu lỗi `TypeError` ở `native_f_common.f_routes` (đọc routes-f.json thiếu `plain()`; F chưa từng PREPARED native). Sửa một dòng (cca0f87). Revision `m56_c0_partial_io_asel2fprep_20261114T122622Z`: F01 PREPARED.
- Compile/admission lần 1: CARLA time-out 600 s (lúc đó bộ nhớ ảo còn ~4 GB). Lần 2 (`m56_f_compile_Town13_20261114T123905Z`): **FROZEN** sha `ccf25857…`, **ADMITTED**, contract EGO:A, EGO:B, NPC:NPC_COMMON đều OK. Chưa episode nào, chưa tiêu P5.
- Rủi ro trước A/B: pagefile trên C: tới 22 GB, bộ nhớ ảo có lúc chỉ còn 4 GB; crash giữa episode sẽ tiêu P5 của F01.

**f-v1.2 (14/11 ~12:55Z, Duy [chat] "b"; luật sau-số, nguyên tắc 6; prepare 12,96 m được giữ trong hồ sơ):**
- Kiểm offline trên quan sát probe 1 lúc 12:18Z: theo luật `first_ready` của probe 2, probe 1 cũng "ready" sau ~4,9 s (probe 2: T_r 4,85 s), còn `steady_at` cho 7,55 s. Lệch 2,65 s × 0,597 m/s ≈ 1,58 m, giải thích đủ khoảng lệch 1,56 m.
- Sửa `native-f-prepare.py`: probe 1 lấy khoảng hở tại khung `first_ready` (target = plateau probe 1 làm tròn 1/1000); không có → `READINESS_NOT_REACHED_IN_PROBE1`.
- Dải chấp nhận, chốt trước khi chạy native: |d0_r − d0| ≤ 0,3 m (hàng route cách 0,2 m, `routes_for` đẩy NPC tới hàng kế tiếp, cộng 0,1 m dung sai station của `first_ready`). Ngoài dải: đúng **một** probe sửa (`probe2b`, shift += phần dư); vẫn ngoài dải → `BLOCKED_FIXTURE D0_OUTSIDE_BAND`. Mọi thứ phía sau (routes, pose, target, marker, khung ready) lấy từ probe cuối.
- Áp dụng cho cả F02. `recipe_rev: f-v1.2`.
- Trước A/B: bật watchdog, kiểm stopper r8 còn sống, kiểm bộ nhớ ảo còn trống.

**F01 f-v1.2 bước 1 (14/11 12:48–12:56Z):** prepare `m56_v2_prepare_Town13_20261114T124840Z` **PREPARED**: probe 1 ready sau 4,85 s, probe 2 T_r 4,85 s (khớp); **d0_r = 11,352 m** (đăng ký 11,4; trong dải 0,3 m; không cần `probe2b`); target 3,862 / 3,265; PID stock. Revision `m56_c0_partial_io_asel2fprep_20261114T125450Z`. Compile `m56_f_compile_Town13_20261114T125510Z`: **FROZEN** sha `c36e0a14…`, **ADMITTED**, contract EGO:A/EGO:B/NPC OK. Chưa episode, chưa tiêu P5. Prepare f-v1.1 (d0 12,96) và revision 122622Z giữ trong hồ sơ, không dùng cho A/B.

**F01 A/B (f-v1.2, 14/11 12:59–13:12Z) — lượt P5 của M56-P-F01-S1 đã tiêu.** Root `outputs/m56_f_ab_Town13_20261114T125949Z`, fixture A/B sha `a8955d0a…`, ADMITTED, contract OK, sealed; `runner/stop.json` A và B: CLEANED, không lý do. Pair v13 (`m56_v6_pair_20261114T131144Z`): **FAILED**.
- A: spawn CONFIRMED, physical COMPLETE, witness VALID; a_peak_025 ≈ 7,24 m/s², g_front_min ≈ 6,96 m.
- B: physical FAILED, witness INVALID: `COLLISION_OBSERVED` (khung 2521), kèm `COLLISION_FRAME_MISSING`, `CONTACT_PROOF_INVALID`, `W01_W05_VALIDATION_PENDING`. Metric B UNKNOWN, nên không có so sánh.
- Diễn biến (khoảng hở = khoảng cách tâm − chiều dài xe, làn thẳng): NPC phanh ở 8,05 s; EGO YIELD từ 8,3 s. A dừng hẳn, B giảm về ~1,9 m/s. NPC chạy lại ở 10,8 s; EGO RESUME ở 11,45 s, với khoảng hở A 8,21 m, B 3,66 m. Sau đó EGO chạy 3,86 m/s, NPC 3,27 m/s, cùng làn, khoảng hở giảm ~0,6 m/s. B chạm ở 17,6 s rồi đẩy NPC tới hết episode (22,8 s). A kết thúc ở 24,15 s với khoảng hở còn 3,63 m, tức là **A qua nhờ episode hết trước**, cùng tốc độ khép như B.
- Nguyên nhân: sau cơ chế, EGO (4) nhanh hơn NPC (3,4) trên cùng làn, không có hành vi bám xe. DESTINATION của tooling (`ego_end = ego_front + (F01_END − npc_front) + d0_r + L + 10`) để EGO chạy thêm ~11 s sau RESUME, trong khi khoảng hở của B chỉ đủ ~6 s. Với số danh nghĩa (4,0/3,4/11,4) tốc độ khép cũng là 0,6 m/s, nên đây là hệ quả của tham số đăng ký cộng cách đặt DESTINATION, **không do f-v1.1/f-v1.2**.
- Chưa xác định chính xác: khung F01_N_CLEAR của B so với khung 2521 (va chạm trong hay sau cửa sổ metric). Cần event của product.
- Quyết định (Claude dưới ủy quyền): không chạy lại F01-S1 dưới bất kỳ recipe nào. **F02 bị hoãn**: NPC đuổi từ phía sau nhanh hơn ~1 m/s, phải dự báo khoảng hở sau tối thiểu qua cả A và B trước khi tiêu lượt. Thay recipe hay thay cảnh là quyết định của Duy.

**Đính chính F01 (14/11 ~13:25Z, Claude):** va chạm của B nằm **trong** cửa sổ metric, không phải ở đoạn chạy tới DESTINATION như ghi ở trên. `F01_N_CLEAR` (metrics.py v13) = lúc toàn thân NPC vượt F01_END (= vạch phanh + 20 m) sau N_MOVE. Từ trajectory: mũi NPC đi được 20 + L ≈ 23,7 m sau lúc phanh vào khoảng 18,5 s (A và B như nhau); B chạm ở 17,6 s. Tính với số danh nghĩa (4,0 / 3,4 / 11,4): khoảng hở lúc phanh ~9,6 m, B ở ~2 m/s trong ~3 s khi NPC đứng, còn ~3,6 m lúc chạy lại; khép 0,6 m/s trong ~7 s tới N_CLEAR cần ~4,2 m. Vậy **va chạm của B là hệ quả của chính tham số F01 đã đăng ký** (vE > vN cùng làn, F01_END = +20 m, hành động B), không do tooling. Sửa DESTINATION **không** cứu được F01. Một cảnh thay thế B3 cho F01 với cùng tham số sẽ gần như chắc chắn va chạm y như vậy, nên chưa chạy, chờ Duy quyết về recipe F01.

## 14/11 ~13:40Z: F02 stage 1 (f-v1.2) và tìm site thay thế F01-S2 (Claude dưới ủy quyền)

**F02 stage 1** (`run-f02-v12.sh`, chưa tiêu P5):
- prepare `m56_v2_prepare_Town12_20261114T132922Z`: NPC PID (1/2, 1/20, 0); plateau EGO 3,864 / NPC 4,713; d0_r 21,066 (đích 21, dải ±0,3, không cần probe2b); T_r 4,8.
- compile `m56_f_compile_Town12_20261114T133601Z`: FROZEN bb5e0fc3…, F02_END 102,309, DESTINATION 107,309; ADMITTED; mọi contract OK.
- REVF `outputs/m56_c0_partial_io_asel2f02prep_20261114T133542Z/c0-partial-v5-frozen-revision.json`.
- Kiểm offline trước A/B:
  - Chuỗi event (metrics.py v13 `_detect_f02`): TRIGGER khi khoảng hở sau cắt 20 m với vN > vE, khoảng 1,3 s sau ready. F02_END = mũi EGO danh định lúc TRIGGER + 60.
  - Response (response.py: F02 chỉ một transition sau TRIGGER, A = 4, B = 11/2): EGO B chỉ tăng tốc **sau** TRIGGER, nên TRIGGER vẫn xảy ra.
  - Dự báo A (EGO hằng): khép 0,849 m/s; khoảng hở nhỏ nhất ≈ 5,4 m (≥ 1,0); v_mean_E ≈ 3,86.
  - Dự báo B: khoảng hở ≈ 19–20 m. v_mean_E ≈ 5,0–5,2 (gain EGO mặc định; plateau ở 5,5 chưa đo), Δ ≈ 0,23–0,26. **Biên mỏng**: B cần trung bình ≥ 4,83.
  - Quyết định: chạy A/B F02 (một lần, P5).

**F01-S2 tìm site thay thế** (`f-site-replace.py`, đúng thuật toán đã đăng ký, addendum F01-v2 eabacab):
- Kết quả **EMPTY_NO_ELIGIBLE_CANDIDATE**. Skip: TOWN_CAP 36, SECTION_SHORT 47, B5_AXIS_RUN_SHORT 20, SITE_USED 4.
- Lưu `docs/m56/M56_F_SITES_REPLACE_F01_20261114.json` (sha256 7eeeeda789bbbbd5b035a152923b3c60fe23d5fe6396ba7d7962788ad4d8ed0d).
- Dưới luật đã commit, F01 không có cảnh thay thế. Đang chẩn đoán offline xem ràng buộc nào chặn (trần town hay cổng độ dài/trục). Chưa chạy native F01 nào.
## 14/11 ~13:50Z: F01-v3 (luật sau số lần 2) và site F01-S2 (Claude dưới ủy quyền, đã hỏi advisor)

- Chẩn đoán EMPTY (offline): trần town chỉ chặn Town12, và cả 36 ứng viên bị trần cũng trượt cổng. Ràng buộc thật là cổng độ dài 145,33 m. Không ứng viên nào trong pool có ≥ 100 m.
- Addendum `PREREG_M56_F_ASEL2_ADDENDUM_F01V3_20261114.md` (văn bản ghi 13:50:15Z; commit d95827e; tooling e46ebf1, NEED_M).
  - Nhu cầu site của F01 thành 91,4 m, tính từ prepare S1: NPC = 20,35 + 41,03 + 30.
  - Luật dừng: một lần chọn. Nếu stage 1 hỏng vì bất kỳ lý do nào thì F01 FAILED, không chỉnh thêm.
  - Sàn khoảng hở tính theo plateau S2.
  - A/B F01-S2 chờ Duy.
- Kết quả chọn (13:50:28Z, một lần): **M56-P-F01-S2 = Town06 road 30 section 0, lanes −3/−4** (biên ≈ 2,4 m).
  - Skip: TOWN_CAP 2, B5_AXIS_RUN_SHORT 1, SITE_USED 1.
  - `docs/m56/M56_F_SITES_REPLACE_F01_V3_20261114.json`, sha d470f360….
  - Thay cảnh B3 +1.
- `run-f01-s2.sh` (69af8e5): stage 1 xếp hàng sau F02V12_END (`m56_f01s2_stage1`). Stage 2 từ chối chạy nếu không có câu duyệt của Duy.
## 14/11 14:04Z: F02 A/B (f-v1.2), P5 đã tiêu: **pair v13 PASS** (Claude dưới ủy quyền)

- A/B `outputs/m56_f_ab_Town12_20261114T134404Z`:
  - FROZEN 0f15b6b6…; bản compile-only là bb5e0fc3…, khác vì binding theo phiên (pid/world). Section y hệt: F02_END 102,309, DESTINATION 107,309.
  - ADMITTED; sealed; stop A/B CLEANED, không còn survivor.
- Pair `outputs/m56_v6_pair_20261114T140359Z/M56-P-F02/pair-result.json`:
  - A và B: spawn CONFIRMED, physical COMPLETE, witness VALID; w05 INTEGRITY_VALID.
  - **PASS**. Δ v_mean_E = 0,2323 (dự báo 0,23–0,26, biên mỏng đúng như ghi); Δ g_rear_min = 0,6894.
- Nhãn: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Recipe f-v1.2 là luật sau số (nguyên tắc 6): báo cạnh kết quả f-v1 r8 (BLOCKED ở probe 1).
## 14/11 ~14:23Z: F01-S2 stage 1 (Town06 road 30, F01-v2 + F01-v3), chưa tiêu P5

- Base revision `m56_c0_partial_io_asel2f01s2base_20261114T142058Z`.
- Prepare `m56_v2_prepare_Town06_20261114T142115Z`: PREPARED. target_gap_at_ready_m 15,5 (d0 của addendum đã tới prepare). d0_r 15,591 (lệch 0,091, không cần probe2b). Plateau EGO 3,863 / NPC 3,267. T_r 4,4.
- Section: F01_BRAKE_START 19,62 / F01_END 39,62 (frame NPC); DESTINATION 65,82 (frame EGO). Site [1,0; 94,76]; không có F_WINDOW_TOO_SHORT.
- Compile `m56_f_compile_Town06_20261114T142300Z`: FROZEN cfffa5cf…; ADMITTED; mọi contract OK.
- REVF `outputs/m56_c0_partial_io_asel2f01s2prep_20261114T142245Z/c0-partial-v5-frozen-revision.json`.
- Cổng mục 5 F01-v3: loss₂ = 11,85 (plateau ≈ S1), gap_N ≈ 3,74, **gap_dest ≈ 2,24 m ≥ 1,0: ĐẠT**.
- Trạng thái: **mọi cổng trước A/B đạt; A/B F01-S2 chờ Duy duyệt** (F01-v3 §4.4). Lệnh khi được duyệt:
  `python -I start-detached.py m56_f01s2_ab D:/Git/usr/bin/bash.exe run-f01-s2.sh ab <REVF> "<câu duyệt của Duy>"`.
## 14/11 ~14:29Z: F01-S2, sửa attest trước A/B (theo advisor)

- Lỗi: revision 142245Z niêm phong d0 15,5 và site S2 với câu "PREREG F part 1 … no hand tuning" / "pre-registered F site algorithm". Câu này sai: cả hai là luật sau số. Đã sửa `asel2_f` (00ab60b): entry có `replaces` ghi "AS AMENDED POST-NUMBER (principle 6)" và trích ref tới hai addendum F01-v2/F01-v3.
- Rebuild dùng lại prepare `m56_v2_prepare_Town06_20261114T142115Z`, không probe lại. Compile `m56_f_compile_Town06_20261114T142820Z`: FROZEN fa77cfe0…, section y hệt, ADMITTED, contracts OK. Cổng mục 5 không đổi (gap_dest ≈ 2,24 m).
- **REVF dùng cho A/B:** `outputs/m56_c0_partial_io_asel2f01s2prep_20261114T142805Z/c0-partial-v5-frozen-revision.json`. Bản 142245Z bỏ, không dùng.
- Đính chính mục F02 ở trên: fixture compile-only (bb5e0fc3) và A/B (0f15b6b6) có cùng section/route/response/actor/pose. Hash khác vì đường dẫn thư mục output và biên nhận authority A/B (750 → 988 byte), không phải pid/world.
- Ngân sách thay cảnh B3: 40/150 (F01-S2 +1).
## 14/11 14:37Z: F01-S2 A/B (Duy duyệt), P5 đã tiêu: **pair v13 PASS**

- Duyệt: Duy [chat] 14/11 "duyệt A/B F01-S2". REVF `m56_c0_partial_io_asel2f01s2prep_20261114T142805Z` (bản attest đã sửa).
- A/B `outputs/m56_f_ab_Town06_20261114T143133Z`: FROZEN e2dc126f… (section y hệt compile-only); ADMITTED; sealed; stop A/B CLEANED.
- Pair `outputs/m56_v6_pair_20261114T143721Z/M56-P-F01-S2/pair-result.json`:
  - A và B: spawn CONFIRMED, physical COMPLETE, witness VALID; w05 INTEGRITY_VALID. Không va chạm.
  - **PASS**. Δ a_peak_025 = 0,4029 (dự báo ≈ 0,44); Δ g_front_min = 0,6668 (dự báo ≈ 0,67).
- F01 báo dưới ba luật:
  - prereg gốc: S1 FAILED, không có thay thế;
  - F01-v2: EMPTY;
  - **F01-v3: S2 PASS**. Đây là luật sau số lần 2: nhu cầu site 91,4 m tính sau khi thấy pool, chỉ một road đạt, đổi town.
- Nhãn: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.
## 14/11 ~15:13Z: release partial A-SEL2 (Claude dưới ủy quyền)

- Revision release `outputs/m56_c0_partial_io_asel2release_20261114T150743Z` (`run-asel2-release-revision.sh`, offline): 44 candidate, gồm cả hai preparation F đã PASS (F02 Town12, F01-S2 Town06). F01-S2 mang câu attest POST-NUMBER.
- Dry (product m56-v13), `m56_asel2_release_20261114T150*`:
  - **21 cảnh delivered**: C 7, L 7, O 3, I 2, F 2.
  - So realized: C 20 PASS / 1 DIVERSITY_DEFICIT; L 19 / 2; I 1 PASS; O 3 PASS. F không có so realized vì assembler chỉ so CLMIO và chưa có bảng descriptor F.
  - Deficit: CANDIDATE_COUNT, JUNCTION_SHORTFALL, C0_MISSING, COMPARISON_COVERAGE, AB_PROOF. RELEASE_BLOCKED, không export (đúng luật, không ép).
- `--full` đang chạy detached (`m56_asel2_release_full`, output `m56_asel2_release_20261114T151317Z`), khoảng 10 phút mỗi cảnh.
- Tồn đọng đã kiểm: `COLLISION_FRAME_MISSING` / `CONTACT_PROOF_INVALID` có ở mọi episode có `COLLISION_OBSERVED` (I05-S1 A, I06 A/B, I07-S1 A/B, F01-S1 B). Đây là witness hỏng sau va chạm thật, physical đã FAILED, nên không verdict nào đổi.
## 15/11 02:13: release --full xong (outputs/m56_asel2_release_20261114T151317Z)

- eligible 19/21 PASS. O02, O03: eligibility_error MemoryError() (worker rò RAM, khoảng 24 GB ở cảnh 14). Không phải verdict.
- RELEASE_BLOCKED [CANDIDATE_COUNT, JUNCTION_SHORTFALL, C0_MISSING, COMPARISON_COVERAGE, AB_PROOF]; exported None. Nhãn: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.


## 15/11: sửa RAM của release, chạy lại --full; replacement 6 (C07-S2, L08-S2)

Claude quyết dưới ủy quyền của Duy, theo yêu cầu của người dùng phiên này [chat 15/11]: "làm tiếp ledger rồi chạy lại full suite cho 2 cảnh này, tối ưu để không còn lỗi memory error … đồng thời tiếp tục làm tiếp những cảnh khác".
- Ledger: M56 trạng thái + mục sổ vận hành #140 (main ca8f8ed).
- **Sửa RAM (9305d49):** `asel2-elig-one.py` chạy mỗi cảnh trong một process riêng, cùng các bước như vòng lặp cũ; record được kiểm round-trip encode/decode rồi mới ghi. `--first=` chỉ đổi thứ tự chạy. Chạy lại: nhãn `m56_asel2_release_full2` → `outputs/m56_asel2_release_20261115T054325Z`, O02 và O03 chạy trước. "Full suite cho 2 cảnh" được hiểu là release `--full`. Test suite `tests/m56` vẫn xếp cuối, không chạy chồng việc native.
- **Replacement 6** (B3 + addendum F/B5): C07-S1 và L08-S1 đều trialed FAILED với `CLEAR_N_CONFIRMED_MISSING` (B có thêm `EARLY_ENTRY_BEFORE_NPC_CLEAR`). Cả hai được sinh trước cổng trục B5, mà B5 sinh ra đúng cho lỗi này: C03-S2 và C04-S2 PASS sau replacement 4. State 6 (`asel2-replace-state6.py`) = state 5, cộng M06 → site của M06-S2, cộng tried. `fill-v4-generate.py … ceb87fa --replace state_6` → `outputs/m56_fill_v4_replace6_20261115.json` sha 6a03c656: **C07-S2 Town12 J13032** (vN 46875/4096, G 23/2), **L08-S2 Town12 J4219** (vN 234375/16384, G 5).
- Ngân sách B3 (jsonl): thêm dòng F01-S2 (40; batch log 14/11 đã tính nhưng jsonl còn thiếu), C07-S2 (41), L08-S2 (42). **42/150.**
- Chạy: `run-asel2-repl6.sh` (07e6c93), nhãn `m56_asel2_repl6`. Đợi release ghi report rồi mới chạy `run-asel2-cl2.sh "Town12:M56-P-C07-S2,M56-P-L08-S2"` với v12 + spawn tilt + replacement 1..6. Mỗi cảnh đúng một A/B (P5).
- **Không làm**, vì cần luật mới hoặc quyết định của Duy:
  - các cảnh I (cấm tới khi có recipe I mới);
  - M (chưa M nào PASS; nguyên nhân đã chẩn đoán, chưa có cổng nào chặn được);
  - F03–F06 (decode hoặc capability);
  - O04/O08 (chưa kiểm cổng run-in thẳng của generator O; để sau C/L).
- Ghi chú: revision release (`run-asel2-release-revision.sh`) dùng replacement 1–4, thiếu replacement 5. Vì vậy M06-S2 (BLOCKED_WITNESS, đã A/B) không có trong rows của release. Không ảnh hưởng delivered.
## 15/11: người dùng duyệt recipe mới

- Nguyên văn, người dùng phiên này [chat] 15/11/2026: "tôi duyệt recipe mới bạn hãy làm đi". Lời duyệt này trả lời mục B của
  `docs/m56/M56_FIX_MATRIX_20261115.md` (ed9831b).
- **Phạm vi:** recipe mới cho O08 (độ dài probe), cảnh I (I01, I02, I05–I08), O05/O07 (pha return), O06, F03–F06.
- **Ngoài phạm vi:** M (mục C, luật consumer), mọi luật verdict của consumer, ngưỡng Tag.
- Duyệt trước khi có văn bản recipe. Vì vậy mỗi recipe vẫn phải có prereg riêng, ghi rõ là luật sau số, và commit trước bước native
  đầu tiên. Mỗi prereg phải có:
  - một cổng dự báo trước A/B;
  - luật dừng: một revision cho mỗi loại, hỏng thì không chỉnh thêm;
  - báo kết quả dưới mọi luật trước đó;
  - nêu rõ chạy lại chính cảnh đó dưới version mới hay dùng successor B3.
- Thứ tự: chẩn đoán và prereg làm trước, offline. Code chỉ viết trong file mới hoặc worktree mới. Bước native chỉ chạy sau `REPL7_END`.
  Các file mà batch đang xếp hàng sẽ nạp được giữ đóng băng tới lúc đó.
## 15/11 chiều: recipe mới (người dùng duyệt), làm offline, xếp hàng native

- **Sửa RAM release đã được kiểm:** O02 và O03 đều PASS. Process cha đứng yên ở 1,59 GB qua 10 cảnh (trước đây tăng khoảng 1 GB mỗi cảnh).
- **io-v1.5** (62593d9): probe chuẩn bị dài 60 s cho I/O, áp nguyên văn luật cl-v1 b. Cổng ready ≤ 14 s. Dùng cho O08-S2: EGO ở arc
  192,3 m tại frame 320, còn thiếu 3,8 m mới tới ga quyết định 196,07.
- **io-v1.6** (30462c3, 7ab7cec, 093239d): Dlc_eff = max(3·vE, 18 m). Đây là lệch khỏi spec 7.4, đã ghi rõ.
  - Bằng chứng: O05-S1, O07-S1 và O06 đều có steer 0,8 (full lock), arc lùi 40–52 lần, Dlc ≤ 14,4. O01–O03 có steer 0,12.
  - Builder 
ative-v5-revision-io16.py chỉ áp io-v1.6 trong sel2_io. Bản rebuild v1 đã được assert là byte-giống.
  - So offline với bản không patch: chỉ 5 candidate có vE < 6 thay đổi. O07-S1 bị WINDOW_TOO_SHORT nên dùng successor B3:
    replacement 8, adca3630, **O07-S2 Town12 R148**, ROUTES_OK.
  - Cổng 2.4 (steer trong prepare) không chạy được vì cần guard của runner A/B. Nó được thay, trước mọi bước native, bằng κ_max ≤ 0,0624
    (giá trị của O01). Trên fixture đã niêm: O01 qua, O05-S1 trượt (0,0905).
  - Wrapper prepare 
ative-io-prepare-v16.py có self-test offline: 3 trường hợp đều OK.
- **io-i-v1.2** (52fc169 + bổ sung sàn Dlc): đã chẩn đoán I01, I02, I05, I06, I07.
  - Probe 3 chẵn với A/B, đuôi X = 2L + 10, cổng làn nguồn trống ≤ 2,3 s.
  - Guard tiếp tục của A cần **product v15**.
  - **Chưa code**, nên các cảnh I chưa xếp hàng.
- **F05/F06:** consumer v14 phần 2 chưa làm (hiệu chỉnh dừng native, history refs, proof). Ước lượng 2–3 ngày.
  **F03/F04:** cần erratum C0 cho tham số mechanism. Chưa làm.
- **Hàng đợi native** (đều chờ file HOLD, file này được nhả khi suite 11 xong):
  1. `m56_asel2_repl6b`: C07-S2, L08-S2.
  2. `m56_asel2_repl7`: O04-S2.
  3. `m56_asel2_io16` (696ea72): O05-S1, O06, O07-S2, O08-S2.
- **Ngân sách B3:** 44/150.

## 15/11 tối: kết quả native sau khi HOLD được nhả

Nguồn [repo]: `outputs/m56_asel2_repl6b.stdout.txt`, `m56_asel2_repl7.stdout.txt`, `m56_asel2_io16.stdout.txt`, các log trong
`m56_asel2_cl2_20261115T090414Z`, `m56_asel2_io_20261115T100537Z`, `m56_asel2_io_20261115T101626Z`.

- **Full suite 11** (`m56-full-suite-11-20261115`): 1249 passed, `CHAIN_PASSED`, 2 h 02 min.
- **Release --full2** (`m56_asel2_release_20261115T054325Z`): 21/21 eligibility PASS. RAM của process chính đứng yên. Status vẫn là
  `RELEASE_BLOCKED` (`CANDIDATE_COUNT`, `JUNCTION_SHORTFALL`, `C0_MISSING`, `COMPARISON_COVERAGE`): đây là các thiếu hụt về độ phủ,
  không phải lỗi eligibility.
- **C07-S2, L08-S2** (B5 successors, Town12): cặp PASS dưới consumer m56-v12. Dưới m56-v10 và m56-v6 là `BLOCKED_WITNESS`. Lưu ý: dòng
  echo của `run-asel2-cl2.sh` ghi nhãn "v10:" nhưng thật ra là `pair-v10.log`, chạy với `M56_CODE` = m56-v12.
- **O04-S2** (io-v1.4, `run-asel2-io.sh`): `BLOCKED_FIXTURE EGO_NOT_AT_DECISION_IN_PROBE1`, không có A/B. Phạm vi io-v1.5 (§3) chỉ gồm
  O08-S2, nên O04-S2 **không** được chạy lại dưới io-v1.5. Muốn chạy lại thì phải có quyết định mở rộng phạm vi.
- **O05-S1, O06, O07-S2** (io-v1.6): prepare PREPARED, compile FROZEN, cổng κ đạt. Admission ADMITTED, nhưng contract của
  consumer báo `EGO:A LATERAL_LENGTH_INVALID`, nên runner **không chạy A/B**: không có thư mục `run`, P5 chưa tốn.
  - Nguyên nhân: m56-v12 `response.py` 1490 yêu cầu `length_m == 3 * nominal`, tức Dlc = 3·vE của spec 7.4. Contract này nằm trong
    đường đánh giá của consumer (`evidence._lateral_integrity` gọi `_lateral_contract`).
  - Như vậy sàn Dlc_eff = max(3·vE, 18 m) của io-v1.6 đòi **đổi luật consumer**, và việc đó nằm ngoài phạm vi người dùng đã duyệt
    ("không gồm luật consumer").
  - **Lỗi của Claude:** mục 3b của io-v1.6 ghi "kiểm offline builder", nhưng lần kiểm đó không chạy contract của consumer trên
    response mới, nên không bắt được lỗi này trước khi chạy native.
- **O08-S2** (io-v1.5): probe dài chạy được, ready 10,65 s sau settle (≤ 14 s). Revision builder chặn với `BLOCKED_FIXTURE
  IO_LANE_SEPARATION_MISMATCH`.
  - Khoảng cách làn đo trên trục thế giới tại O_DECISION là 3,2494 m, làm tròn mm ra 3,249. Profile A cần đúng 3,25 (13/4).
  - Lý do: road 1432 lệch trục 0,75° (spec cho phép tới 1°), và hai route lệch nhau 0,05 m theo arc.
  - Theo io-v1.5 §3, O08 ghi **FAILED dưới io-v1.5**. Dưới io-v1.4 thì đã là `BLOCKED_FIXTURE EGO_NOT_AT_DECISION_IN_PROBE1`.
- Bổ sung cho gate G (việc phải làm trước mọi successor I/O mới): kiểm `length == 3·nominal` (contract consumer) và khoảng cách làn
  làm tròn mm tại decision. Phép làm tròn giữ nguyên.


## 15/11 tối: quyết định của người dùng về recipe I và luật 3·vE

Nguồn [chat] 15/11/2026, trả lời ba câu hỏi của Claude:
- **I02-S2:** "Giữ lại, chưa chạy". Cảnh không tiêu P5 dưới io-i-v1.2 và chờ một recipe sửa được mốc đổi làn của B.
- **I01-S1:** "Chạy ngay": prepare + compile + probe 3 (addendum H). Nếu G1/G2/G3 đều đạt thì chạy A/B theo luật đã duyệt.
- **Luật consumer length = 3·vE:** chọn "Duy duyệt đổi (v15)". Theo câu trả lời, người chọn tự xưng là Duy. Nội dung: làm consumer
  m56-v15 chấp nhận Dlc = max(3·vE, 18 m), có prereg, test và full suite trước khi chạy, và báo kết quả dưới cả hai luật.
  - Đây là đổi luật consumer **sau khi thấy số** (nguyên tắc 6). Luật cũ (spec 7.4, Dlc = 3·vE) giữ nguyên văn. Mọi kết quả của
    O05/O06/O07 và I05–I07 phải báo dưới cả luật cũ lẫn luật mới.
  - Claude không kiểm được danh tính người chat (máy dùng chung). Thẩm quyền được ghi theo lời tự xưng.

## 15/11 tối (2): consumer v15 (sàn Dlc), kiểm offline

- Prereg `PREREG_M56_CONSUMER_V15_DLC_FLOOR_20261115.md`. Worktree `m56-v15` (feat/m56-v15) tách từ v13 834e149, commit ff9f1f2.
  - Chỉ một luật đổi: `_lateral_contract` dùng `_io_dlc`, EGO = max(3·vE, 18), NPC = 3·vN. Luật cũ giữ là `dlc_old_rule`.
  - Không gồm v14 WIP và không gồm G4.
- Test `tests/m56/test_v15_dlc_floor.py`: pass, cùng `test_v9_io_nominal.py`, 6 passed.
- Kiểm contract (`v15-contract-acceptance.py`, `outputs/m56_v15_contract_acceptance_20261115.jsonl`):
  - O05-S1, O06, O07-S2 (fixture io16): v13 báo `EGO:A LATERAL_LENGTH_INVALID`; v15 báo OK cả ba response. Sau luật độ dài không
    còn lỗi forward/reference nào bị che.
  - O01, O02, O03, I03, I04 (PASS), I01-S1, I02-S2: v13 và v15 giống hệt, đều OK.
  - Đoạn return của O cũng dài 18 m trong fixture io16, nên luật khớp với từng đoạn.
- Chưa làm: full suite trên byte v15. Chỉ chạy sau `I12_END` (I01-S1 đang chạy native). Sau đó là A/B O05-S1, O06, O07-S2 dưới v15.
- **G4 hoãn:** I05–I07 đều có `COLLISION_OBSERVED` ở A. Chương trình A đóng băng đã chờ `SOURCE_CLEAR_CONFIRMED`
  + `NPC_TARGET_LANE_CONFIRMED` trước khi RESUME. Phải xếp thứ tự TRIGGER / dừng / va chạm / RESUME trên các episode A đã niêm
  trước khi viết G4. Việc này chạy sau `I12_END` vì tốn RAM.
- Hàng đợi I01-S1 (`run-asel2-i12-queue.sh`) chưa được khởi động ở phiên trước. Đã khởi động lúc 12:36Z:
  `outputs/m56_asel2_i12.stdout.txt`.
## 15/11 tối (3): I01-S1, lần khởi động 1 hỏng do hạ tầng

- 12:36Z: hàng đợi được chạy bằng `Start-Process -WindowStyle Hidden`. Server CARLA (pid 35588) chết ngay khi khởi động. Prepare chỉ
  ghi `CONNECT_RETRY` từ 0 tới 7, không có probe, không compile, không A/B, nên P5 chưa tốn.
- Claude đã dừng cây process của chính mình. Dấu vết giữ nguyên:
  - `outputs/m56_asel2_io_20261115T123629Z`;
  - `m56_v2_prepare_Town12_20261115T123650Z` (một file);
  - `m56_asel2_i12.stdout.launch1-server-died.txt`.
- 12:50Z: chạy lại cùng script, cùng byte, từ shell nền của phiên. CARLA chạy bình thường. Đây không phải revision mới của recipe:
  lần đầu không tạo ra số đo nào.
## 15/11 tối (4): I01-S1 được giữ trước A/B; G4 sai chẩn đoán

- Addendum I (`PREREG_M56_IO_I_RECIPE_V1_2_ADDENDUM_I_NPC_LANE_CHANGE_20261115.md`): NPC đánh lái hết cỡ (0,8) ở I05-S1, I06,
  I07-S1. Đoạn đổi làn của NPC là 3·vN = 11,4 / 6,2 / 8,5 m, κ ≥ 0,155. Ở I05 và I06, NPC va vào map. NPC sạch (≤ 0,12) ở I02-S2,
  I03, I04, nơi κ ≤ 0,049.
- NPC của I01-S1 có κ = 0,0834 > 0,0624. Claude đã dừng hai process bash của batch khi batch còn ở prepare: không compile, không
  probe 3, không A/B, P5 chưa tốn. Prepare chạy nốt và tự tắt server.
- G4 không được dựng. v15 (sàn Dlc cho EGO) không giúp các cảnh I tốc độ thấp. Chờ người dùng chọn: sàn NPC, cổng NPC trong probe 3,
  hoặc giữ cảnh.
## 15/11 tối (5): sàn NPC (addendum J), v15 hoàn chỉnh, suite 12, hàng đợi v15

- Người dùng phiên này [chat] chọn "Sàn Dlc cho NPC". Addendum J (`PREREG_M56_NPC_DLC_FLOOR_ADDENDUM_J_20261115.md`): NPC cut-in
  max(3·vN, 18 m) ở prepare (`native-io-prepare-i12j.py`) và ở consumer v15.
  - v15 = v13 + ff9f1f2 + c218f2f. Đã cherry-pick vào `feat/m56-v1` (bd6bf83, ab586bf).
- Kiểm contract dưới v15 (`outputs/m56_v15j_contract_acceptance_20261115.jsonl`):
  - I03, I04, I02-S2, O01: OK.
  - O05-S1, O06, O07-S2: OK.
  - Fixture I01-S1 cũ (NPC 15 m): `NPC LATERAL_LENGTH_INVALID`, đúng như kỳ vọng. Fixture này phải dựng lại bằng i12j.
- Prepare cũ của I01-S1 (io-i-v1.2 G2, trước sàn NPC) chạy tới cuối: PREPARED, server tự tắt. Nó không được dùng, vì batch đã dừng
  trước revision/compile. Kết quả chỉ cho thấy readiness và đuôi G2 đạt ở site này.
- Full suite 12 (`m56-full-suite-12-20261115`) bắt đầu trên byte v15. Hàng đợi `run-asel2-v15-queue.sh`
  (`outputs/m56_asel2_v15q.stdout.txt`) chờ suite 12 `CHAIN_PASSED`, rồi chạy:
  - I01-S1 (i12j);
  - O05-S1, O06, O07-S2 (io16), với M56_CODE = m56-v15.
  - Suite không đạt thì không chạy gì.
- Pair luật cũ (m56-v12) sẽ chạy tay sau, vì là offline: pair không tốn P5.
## 15/11 tối (6): hàng đợi chỉ O, lỗi kẹp NPC, addendum L

- Hàng đợi `run-asel2-v15-queue.sh` và `run-asel2-r9-queue.sh` bị thay trước khi chạy bước nào. Hàng đợi mới
  `run-asel2-v15o-queue.sh` chỉ chạy O: O05-S1, O06, O07-S2 (Town12), O04-S3, O08-S3 (Town13), product m56-v15, sau khi suite 12
  `CHAIN_PASSED`. Chạy detached nhãn `m56_asel2_v15o2` (nhãn `m56_asel2_v15o` bị khóa file stdout).
- I01-S1, I02-S2, I05-S2…I08-S2 giữ lại chờ recipe thời điểm đổi làn của B. I08-S2 bị rút ra vì cùng dạng với I02-S2.
- **Lỗi tìm thấy (addendum L, `PREREG_M56_IO_GAP_GATE_ADDENDUM_L_20261115.md`):** prepare kẹp điểm xuất phát NPC ở đầu road site.
  Khi NPC cần lùi ra trước road đó, gap thực tăng đúng |shift|.
  - I04: 46,42 m thay vì 13,18 m. Cặp I04 đang được tính PASS. Recipe io-v1 đã đặt trước dung sai |gap − spec| ≤ 0,5 m, nên I04
    vi phạm luật đã đăng ký. Claude không đổi status; người dùng quyết.
  - I02-S2 (27,36 thay vì 7,80; BLOCKED_WITNESS), I05-S1 (11,08 thay vì 4,62; FAILED), I01-S1 (21,37 thay vì 6,00; chưa A/B) cũng
    bị kẹp. Kết quả I02-S2 và I05-S1 không phải kết quả ở gap catalog.
  - O01–O07: lệch ≤ 0,42 m, không bị ảnh hưởng.
- Cổng `asel2-io-gap-gate.py` (fail closed, 0,5 m) được gắn vào `run-asel2-io-v16.sh` và `run-asel2-io-i12j.sh` trước compile/A/B.
- Rút lại hai nhận định trước: "I05–I07 không khả thi" và bảng cửa sổ thời gian (`m56_i_b_window_20261115.txt`). Bảng đó dùng gap
  catalog làm gap lúc TRIGGER. I06, I07 thật sự chạy ở gần gap catalog, nên cửa sổ ngắn của chúng vẫn đúng. Successor I05-S2…I08-S2
  chưa có prepare, nên chưa biết gap thực.
- Người dùng phiên này [chat] 15/11 chọn "Hạ I04, làm successor". Progress doc: I04 chuyển từ PASS sang
  `FIXTURE_GAP_NOT_REALISED`. Release 21/21 eligibility của --full2 vẫn đếm I04; lần release sau phải bỏ I04 khỏi danh sách PASS.
  Successor I04 chờ recipe sửa cách đặt NPC (cho NPC xuất phát trên road trước road site, hoặc đòi chỗ lùi ở cổng site offline).
- **Cách ghi khi cổng L chặn (đặt trước mọi số của O04-S3, O08-S3 và các cảnh I sau):** cảnh bị `GAP_NOT_REALISED` hoặc
  `GAP_UNKNOWN` thì không tốn A/B (P5 chưa dùng), slot không bị ghi FAILED. Ghi là `FIXTURE_GAP_NOT_REALISED`. Được prepare lại
  dưới cách đặt NPC đã sửa (recipe mới). Câu "Hỏng thì FAILED, không chỉnh thêm" của addendum K chỉ áp cho A/B đã chạy.
- O08-S2: điểm xuất phát NPC đúng ở `rows[0]` của route probe 1. Shift cần −63,35 m, nhưng route NPC chỉ có 60 m phía sau
  (`NPC_BACK_M`), nên lệch 3,25 m. Đây là giới hạn chỗ lùi, không phải kẹp đầu road. O08-S3 có cùng vE, vN, gap nên rất có thể bị
  cổng L chặn. O04 cũ lệch −0,42 m, sát ngưỡng 0,5 m.
- `native-io-prepare-i13.py` (io-i-v1.3 a, bản nháp bf78050): đặt NPC của cảnh I theo arc, không kẹp ở đầu road site. Tự kiểm
  offline: NPC lùi đúng |shift| (I04 33,4; I02-S2 19,6; I05-S1 6,6; I01-S1 15,2 m). Ở I04, I02-S2, I01-S1, NPC sẽ xuất phát trên
  đoạn nối trong nút giao. Chưa gắn vào script chạy nào. Lần dùng native đầu tiên sẽ chỉ là prepare I01-S1 (không A/B).

## 16/11 rạng sáng: suite 12 rớt, sửa fixture test, ổ C đầy, HOLD

- Suite 12 (`m56-full-suite-12-20261115`, byte v15): `PYTEST_TESTS_FAILED`, 4 failed / 1248 passed (3 h 50). Hàng đợi O
  (`m56_asel2_v15o2`) in `NOT RUN: suite 12 not CHAIN_PASSED`, không chạy cảnh nào.
  - `test_io_complete.py::test_source_producer_public_witness_completes_stop_then_merged_cut_in`,
    `::test_source_cut_in_ab_does_not_turn_two_valid_actions_into_automatic_pass`,
    `::test_source_producer_public_witness_completes_supported_cut_in`,
    `test_lateral_contract.py::test_npc_cut_in_uses_its_own_parallel_reference_and_three_second_scale`.
  - Nguyên nhân: fixture tổng hợp của NPC cut-in dài 3·vN = 15 m (vN = 5). Theo v15/addendum J (đã duyệt), độ dài phải là
    max(3·vN, 18 m) = 18 m, nên consumer chặn `LATERAL_LENGTH_INVALID`. Claude không chạy các file test này trước khi bắt đầu
    suite 12. Đây là lỗi quy trình của Claude.
- Sửa (036688b trên feat/m56-v15, f140093 trên feat/m56-v1): cập nhật fixture theo luật v15. Đoạn NPC 18 m, giữ nguyên điểm cuối
  (17,5→14,5 + 18 = 32,5; ở test lateral 10→7 + 18 = 25). Đây không phải đổi ngưỡng. Ba file test qua: 20 passed.
- **Ổ C còn 0 GB** (pagefile.sys 31 GB; Temp nhỏ). Claude không xóa gì. Claude tạo `outputs/m56_asel2_HOLD`: mọi hàng đợi native
  dừng cho tới khi ổ C có chỗ trống, vì một episode chết vì thiếu RAM/đĩa là một A/B đã tốn mà không chạy lại được. Suite 13 chạy
  được vì nó chạy lại được và basetemp nằm trên ổ D.

## 16/11 sáng: máy tắt 01:28, bỏ full suite, chạy tiếp tìm cảnh

- 01:28 (giờ máy) có lệnh tắt máy từ Start menu (System 1074). Suite 13 chết ở 27% (0 failed tới đó), không có checkpoint/run.json
  nên không resume được. Hàng đợi `m56_asel2_v15o3` và `m56_asel2_i13prep` chết lúc tắt máy (`fork ... 0xC000026B` = lỗi logoff),
  chưa chạy bước native nào, không tốn P5.
- Dọn ổ C (không đụng M56): `npm cache clean --force` + `go clean -cache` = 5,6 GB. C còn 21,7 GB, pagefile 16,6 GB (Windows tự quản).
  Việc thật vẫn là chuyển pagefile sang E (cần người dùng, khởi động lại).
- Người dùng [chat] 16/11: "khoan đã chạy full suite tiếp, full suite chỉ chạy lần cuối thôi, trước hết phải tìm đủ các cảnh".
  Không chạy suite 14. Claude quyết dưới ủy quyền của Duy: cổng của hàng đợi O đổi từ suite 13 sang lượt test tập trung
  `m56-v15-focus-20261116` (mọi file test mà v15 đã sửa: test_v15_dlc_floor, test_io_complete, test_lateral_contract,
  test_catalog, test_f01_normative_response, test_v2_native_hooks, test_evidence). Cây m56/ và tests/m56 của m56-v1 trùng
  feat/m56-v15 (diff rỗng). Lần chạy đầu hỏng vì Claude đưa đường dẫn tuyệt đối (assert của runner); file lỗi đổi tên
  `*.launcherr-abs-path.txt`, chạy lại cùng nhãn.
- HOLD nhả (đổi tên `m56_asel2_HOLD.released_20261116T031833Z`). Bù lại: `asel2-cguard.py` (nhãn `m56_cguard_r16a`) mỗi 60 s ghi
  C trống / pagefile / commit vào `outputs/m56_cguard_*.jsonl`; nếu C < 10 GB hoặc commit còn < 4 GB thì ghi file STOP graceful,
  stopper `m56_asel2_stopper_r16a` dừng ở điểm an toàn (không bao giờ trong cửa sổ A/B). Watchdog `m56_asel2_watchdog_r16a`.
- Hàng đợi: `m56_asel2_v15o4` (O05-S1, O06, O07-S2 Town12; O04-S3, O08-S3 Town13; mỗi cảnh một A/B) -> `m56_asel2_i13prep2`
  (prepare I01-S1, không A/B). Cảnh I khác vẫn giữ chờ recipe thời điểm đổi làn của B.
- Trước lần tắt máy sau: tạo `outputs/m56_asel2_STOP` (graceful) và `<label>.STOP` cho runner test, chờ `M56_SAFE_TO_SHUTDOWN.txt`.
- 03:29Z lượt test tập trung v15 PASS 253/253 (9 phút 33) → hàng đợi `m56_asel2_v15o4` bắt đầu. 03:31Z cguard ngắt:
  commit còn 3,43 GB / giới hạn 48,2 GB (C vẫn 20 GB, pagefile không đổi 16,57 GB). Stopper dừng sạch 03:31:32Z, đang ở prepare
  O05-S1 (record `outputs/m56_asel2_stop_20261116T033132Z.json`): không fixture, không AB_STARTED, không tốn P5. Thư mục dở:
  `m56_v2_prepare_Town12_20261116T032932Z` (chỉ có receipt ủy quyền), log `m56_asel2_io_20261116T032909Z`.
- Nguyên nhân: giới hạn là commit, không phải ổ C. ~30 GB commit đã bị app khác giữ (Chrome 3,5, Claude 3,3, node 2,1, python
  MCP 6, Razer 1...), CARLA Town12 13,8 GB. Claude quyết dưới ủy quyền: không nới ngưỡng 4 GB; thêm bước chờ `room` trước MỌI
  lần bật CARLA trong `run-asel2-io-v16.sh` và `run-asel2-i13-prep.sh` (`asel2-cguard.py --wait-commit-gb`, mặc định 25 GB =
  CARLA ~14 + harness A/B ≤ ~7 + 4 dự phòng; Town13 chưa đo). cguard giữ làm chốt chặn. Launcher `run-asel2-resume-20261116.sh
  SUFFIX` (đổi tên STOP/SAFE cũ, bật stopper/watchdog/cguard, hàng đợi O, rồi prepare I01-S1).
- 03:35Z chạy `r16b`: hàng đợi `m56_asel2_v15o_r16b` đang ROOM_WAIT (commit trống ~18 GB < 25). Chạy được khi người dùng đóng
  bớt app (~7 GB) hoặc đặt pagefile cố định trên E (khi đó phải khởi động lại và chạy launcher với hậu tố mới).
- 10:46 (giờ máy) máy khởi động lại: hàng đợi `r16b` chết khi đang ROOM_WAIT (chưa bật CARLA, không thư mục mới, không P5).
  Thiết lập pagefile lúc đó chưa ăn (registry `?:\pagefile.sys` = tự quản, C:\pagefile.sys 18,4 GB vẫn dùng).
- Người dùng [chat] 16/11 "chuyển pagefile qua ổ E rồi xóa pagefile trong ổ C": Claude chạy script elevated (UAC người dùng duyệt):
  tắt tự quản, xóa mọi setting, `E:\pagefile.sys` cố định 32768–65536 MB (E = NVMe KIOXIA). Có hiệu lực sau khởi động lại;
  khi đó C:\pagefile.sys không còn dùng → kiểm và xóa nếu Windows để lại. Sau đó chạy `run-asel2-resume-20261116.sh r16c`.
- 11:22 khởi động lại: Windows vẫn dùng `C:\pagefile.sys` (TempPageFile=True, commit 49,9 GB = RAM + C; E không dùng, file E
  không bị ghi lúc boot). Ổ E mount sớm (Ntfs 98, 11:22:57). Nguyên nhân: `PagefileOnOsVolume=1` (BitLocker để lại) ép pagefile lên
  ổ OS. Sửa elevated (UAC người dùng duyệt): sao lưu key vào `%USERPROFILE%\MemoryManagement-backup-20261116.reg`, đặt
  `PagefileOnOsVolume=0`, `TempPageFile=0`. Cần khởi động lại; sau đó kiểm E đang dùng, xóa C:\pagefile.sys nếu còn, chạy r16c.
- 11:41 khởi động lại: pagefile đang dùng = `E:\pagefile.sys` 32 GB (không temp), Windows tự xóa C:\pagefile.sys; C trống 35,9 GB,
  commit 63,6 GB (trống 37,9). 04:44Z chạy `r16c`: ROOM_OK 38,7 GB, prepare O05-S1 (Town12) đang chạy, log `m56_asel2_io_20261116T044433Z`.
  (cguard ghi `pagefile_gb: null` vì chỉ đọc C:\pagefile.sys; không ảnh hưởng ngưỡng.)
- r16c: O05-S1, O06, O07-S2 PREPARED (Town12, ~4 phút/cảnh). 05:11:44Z máy tắt từ Start menu (System 1074), không file STOP, lúc
  đang prepare O04-S3 (Town13, probe 1 READINESS_NOT_REACHED, chưa xong prepare): chưa revision/compile/A/B, không tốn P5.
- 09:27Z chạy `r16d` (prepare chạy lại từ đầu, được phép vì prepare không tính P5). Nhắc người dùng: tắt máy phải qua file STOP.
- r16d (log `outputs/m56_asel2_io_20261116T092756Z`, product v15 036688b, tooling fb0ca38): prepare O05-S1, O06, O07-S2 (Town12),
  O08-S3 (Town13) PREPARED; O04-S3 (Town13) không ra SCENE (probe ngắn READINESS_NOT_REACHED, probe dài TICK_ERROR, log dừng sau
  ~40 phút = timeout 2400 s của hàng đợi) → không compile/A/B, không P5.
- **O05-S1: A/B một lần (10:52–11:09Z), pair theo consumer v15 = PASS** (io-v1.6 + v15, luật sau số đã công bố). Pair v10: đang chạy.
- O05-S1 pair v10 (`m56_v6_pair_20261116T113249Z`) = BLOCKED_WITNESS: A `INITIALIZATION_INVALID`, `LATERAL_CONTRACT_INVALID`;
  B `INITIALIZATION_INVALID` (cả hai kèm `W01_W05_VALIDATION_PENDING`). Theo nguyên tắc 6: PASS chỉ dưới v15, chặn dưới v10.
- **O06: A/B một lần (11:48–12:16Z), pair v15 (`m56_v6_pair_20261116T121609Z`) = BLOCKED_WITNESS.** B: spawn CONFIRMED,
  physical COMPLETE, witness VALID, w05 INTEGRITY_VALID. A: spawn CONFIRMED, physical UNKNOWN, witness INVALID
  (`METRIC_CONTEXT_INVALID`, `W05_REVIEW_MISSING`, `ACTION_REGION_WITNESS_UNKNOWN`); w05 A NOT_WRITTEN (metrics/events không
  admissible), metric A v_mean_E / e_lat_peak UNKNOWN. P5 của O06 (v15) đã dùng, không chạy lại. Nguyên nhân A chưa điều tra.
- O06 pair v10 = BLOCKED_WITNESS (A và B `INITIALIZATION_INVALID`, A thêm `LATERAL_CONTRACT_INVALID` và các lý do như dưới v15).
- **O07-S2: A/B một lần, pair v15 (`m56_v6_pair_20261116T133017Z`) = PASS**: A và B spawn CONFIRMED, physical COMPLETE, witness VALID (io-v1.6 + v15, luật sau
  số đã công bố). Pair v10 đang chạy.
- 14:16Z `V15O_END`: O07-S2 pair v10 = BLOCKED_WITNESS. O04-S3 không compile/A/B (prepare không ra SCENE). **O08-S3: addendum L
  `GAP_NOT_REALISED` (gap 55,694, realised 58,582) → không compile/A/B, không P5.** I01-S1 prepare: PREPARED (`I13P_END` 14:29:54Z,
  log `m56_asel2_i13prep_20261116T141719Z`), không A/B theo kế hoạch.
- **Chẩn đoán offline O06 A dưới v15** (không server, không chạy lại; script scratchpad `diag_o06.py`, `diag_o06b.py`, Claude quyết dưới ủy quyền):
  - `METRIC_CONTEXT_INVALID`: 2/1068 khung (3192, 3553). Hình chiếu của EGO lên route rơi đúng đỉnh arc (station 48,4067 giữa
    đoạn 241/242; 101,4109 giữa 506/507). Hai đoạn kề có normal hơi khác ((0,1,0) và (0,0012,1,0)), nên `_map_offset` trả None
    theo luật "một normal duy nhất ở góc" (offset hai phía bằng nhau: 2,344 và 3,5 m). Đây là góc hình học hiếm của consumer
    (vùng nêm vài mm ở phía ngoài chỗ route gãy), không phải lỗi dữ liệu hay harness.
  - `ACTION_REGION_WITNESS_UNKNOWN`: 1 khung (3741, giữa LANE_CHANGE_ONSET 3103 và X_END 3848). Đỉnh thân xe số 4 có y = 3102,7687,
    cạnh dưới hộp EGO_TARGET y = 3102,7681: lệch 0,6 mm, nhỏ hơn bất định 1 mm, nên membership ba trị = None và cả action UNKNOWN.
    Trước đó 528 khung EGO_TARGET = True. EGO chạy sát mép làn đích, chạm dải bất định.
  - B không gặp hai trường hợp này nên VALID. Không đổi verdict: P5 O06 đã dùng. Nếu muốn nới hai luật này thì đó là luật sau số
    (nguyên tắc 6), phải công bố và báo song song. Chưa sửa gì.
- 14:35–15:00Z dọn D (yêu cầu người dùng): 67 thư mục `outputs/m56_v6_pair_*` (trước 16/11, không doc/script/output nào tham chiếu; chấm cặp
  offline, tính lại được từ thư mục A/B vẫn còn) nén tar.zst (33,25 GB → 0,91 GB, kiểm số entry = số file từng thư mục), upload lên
  Google Drive `My Drive/m56-archive/pairs-20261116` (67/67 khớp kích thước byte qua Drive API), rồi xóa trên D và bản tạm trên E.
  Manifest (sha256, md5, số file, byte gốc): `outputs/m56_v6_pair_ARCHIVED_20261116_MANIFEST.json`. Script `archive-pairs-20261116.ps1`.
  D trống 15,2 → 44,8 GB. Còn 80 thư mục pair được tham chiếu (45 GB) giữ nguyên.

## 16/11 tối: sửa bản dọn D, đếm lại cặp, prepare I02-S2 / I04

- **Sửa lỗi của Claude ở bản dọn D:** kiểm "không tham chiếu" chỉ dò tên thư mục trong doc/script, nhưng `asel2-release.py`
  (`latest_pair`) quét mọi `outputs/m56_v6_pair_*/<id>/pair-result.json`. Bản dọn đã đưa lên Drive cặp PASS duy nhất của C07-S2 và
  L08-S2 (15/11). Đã khôi phục từ Drive, sha256 khớp manifest, đủ số file: 6 thư mục 15/11; mọi pair của C03-S1, C04-S1, M06-S2,
  I01-S1 (cảnh chỉ còn trong bản nén); và các pair mới hơn bản tại chỗ của C02, M07, C04-S2 (để "latest" không đổi). Các PASS khác
  trong bản nén đều cũ hơn một PASS còn tại chỗ. Khôi phục tổng 23/67; còn chỉ trên Drive 44 thư mục là lượt chấm lặp, không cảnh nào mất pair mới nhất.
- **Đếm cặp PASS (pair-result tại chỗ, mỗi cảnh ≥ 1 PASS):** 24 cảnh = C01 C02-S1 C03-S2 C04-S2 C05 C06-S1 C07-S2 C08; L01 L02-S1
  L03-S1 L04 L05-S1 L06-S1 L07-S2 L08-S2; O01 O02 O03 O05-S1 O07-S2; I03; F01-S2 F02. I04 bị hạ (addendum L). Theo nguyên tắc 6:
  nhiều cặp chỉ PASS dưới luật sau số (v7/v8/v12/v15, dv1, f-v1.2, F01-v3); O05-S1, O07-S2 chỉ PASS dưới v15 (v10 BLOCKED_WITNESS).
  Con số "23 theo v15 / 21" báo trước đó trong chat là đếm sai (bỏ sót C07-S2, L08-S2 và tính nhầm I04).
- O06 A, thêm: route tham chiếu map của O06 có 146 chỗ gãy với sin góc > 5e-4 (tối đa 1,2e-3); O05-S1 và O07-S2 (PASS) không có chỗ
  nào > 5e-4 (tối đa 3,1e-4). Nên luật "một normal ở góc" của `_map_offset` chạm O06 nhiều hơn hẳn. Chỉ ghi nhận, không đổi luật.
- I01-S1 (io-i-v1.3 a) đạt mục tiêu addendum M §3: PREPARED, cổng L `GAP_OK` (6,163 vs 6,000), builder revision nhận
  (`asel2i13dry` PREPARED). Claude quyết dưới ủy quyền: prepare-only (không compile, không A/B, không P5) cho I02-S2 (Town13) và I04
  (Town06) bằng cùng luật (`run-asel2-i13-prep2.sh`), để biết luật đặt NPC theo arc có qua cổng L ở hai cảnh bị kẹp còn lại không.
  A/B của cảnh I vẫn chờ recipe thời điểm đổi làn của B (G3), chưa viết.
  - Lần 1 (`r16e`, 15:12Z) bị cguard dừng ở ROOM_WAIT (commit còn 4,1 GB, chưa bật CARLA), record `m56_asel2_stop_20261116T151422Z`.
  - Lần 2 (`r16f`, 16:34Z): stopper/watchdog/cguard `*_r16f`, ROOM_OK 36 GB.
- **Prepare-only io-i-v1.3 a (`r16f`, log `m56_asel2_i13prep2_20261116T163425Z`, xong 16:47Z):** I02-S2 (Town13) PREPARED, cổng L
  `GAP_OK` 7,787 vs 7,800 (trước kẹp: 27,36); I04 (Town06) PREPARED, `GAP_OK` 13,014 vs 13,182 (trước kẹp: 46,42). Builder
  revision nhận cả hai. Cùng I01-S1, luật đặt NPC theo arc qua cổng L ở cả 3 cảnh I từng bị kẹp. Không compile/A/B, không P5. A/B
  của I vẫn chờ recipe thời điểm đổi làn của B (G3).
- Dọn D lần 2 (người dùng: D ≥ 80 GB, chuyển lên Drive không nén). `offload-plan-20261116.py` chọn theo đúng luật đọc của
  `asel2-release.latest_pair`: giữ pair mới nhất và PASS mới nhất mỗi cảnh, pair hôm nay, thư mục A/B mà pair giữ lại trỏ tới, A/B
  của cảnh chưa có pair. Chuyển 110 thư mục (33,2 GB: pair lặp, A/B cũ/rỗng, release run 1) và `elig` của release run 2 (11,5 GB,
  tính lại được; giữ `release-report.json`) lên `G:\My Drive\m56-offload-20261116\` (cùng đường dẫn tương đối), không nén.
  `offload-to-drive-20261116.ps1`: robocopy → kiểm số file + byte trên G: → xóa ở D; mỗi đợt ~6 GB chờ cache DriveFS (ổ C) < 3 GB
  và C ≥ 15 GB. Manifest `outputs/m56_offload_20261116_MANIFEST.jsonl`. `m56_offline_v1` giữ (test_cli/test_staging đọc).
- **17/11 dọn D/E (yêu cầu người dùng: chỉ giữ trên cloud):** upload ~0,25 MB/s nên phần còn lại (130 mục, 34,9 GB) chuyển D → `E:\m56-offload-20261116`
  trước (kiểm số file + byte, log `outputs/m56_offload_20261117_E.jsonl`). Hard link giữa các bundle nên D chỉ trống thêm ~23 GB →
  đợt 2 chuyển thêm `m56_offline_v1/{pytest_receipts,source_checkpoints,diagnostics}` và các `m56_v2_ab_Town04–06_*` còn lại sang E,
  để junction ở D (`offload-junction-20261117.ps1`, log `..._junction.jsonl`). `offload-e-to-drive-20261117.py --delete-junctions`
  (detached `m56_offload_cloud_20261117b`): mỗi mục chép E → `G:\My Drive\m56-offload-20261116\<rel>`, chờ DB của DriveFS báo 0
  thao tác chờ và cloud khớp số file + byte, rồi xóa bản E (và junction). Log `outputs/m56_offload_20261117_cloud.jsonl`.
  - **Người dùng [chat] 17/11: "xóa hẳn luôn cả nhóm junction".** Hệ quả: các thư mục A/B cũ của cảnh PASS (Town04–06, tháng 10–11)
    và lịch sử `m56_offline_v1` chỉ còn trên Drive. Trước release `--full` hoặc mọi chẩn đoán đọc chúng phải tải về đúng đường dẫn
    (`robocopy "G:\My Drive\m56-offload-20261116\<rel>" outputs\<rel> /E`). `m56_offline_v1/inputs` (test đọc) giữ trên D.
- **I01-S1 (addendum N, `r17b`):** prepare `BLOCKED_FIXTURE READINESS_NOT_STEADY` (5 probe 1 đều READINESS_NOT_REACHED; hôm qua
  cùng recipe PREPARED). Không compile/A/B, không P5. Không tự prepare lại (tránh chọn lần may), chờ người dùng.
- **I02-S2 (addendum N):** PREPARED, probe 3 qua G1 6,95 s / G3 2,0 s / G5 SOURCE_CLEAR_CONFIRMED − TRIGGER = 3,3 s ≤ 3,5 → A/B một lần
  (P5 dưới version mới đã dùng). Kết quả pair ghi sau.
- **I02-S2 kết quả (A/B `m56_io_ab_Town13_20261117T072227Z`, P5 đã tiêu):** pair dưới m56-v16 `BLOCKED_WITNESS` và dưới m56-v15
  `BLOCKED_WITNESS`. B (đổi làn theo sự kiện) VALID; A `X_END_MISSING`. Chẩn đoán (`asel2-xend-diag.py`): A đi qua X thật
  (arc 136,3 → 157,7, DESTINATION_CONFIRMED). Đuôi xe ở −0,26 mm tại frame 2863, trong dải ±u (u = 1 mm), nên luật crossing
  theo cặp frame bỏ mất sự kiện. → **addendum O / product m56-v17** (`9282d62`, sau khi thấy số, đã công bố). Chấm lại offline
  dưới v17 (`m56_v6_pair_20261117T082600Z`): **PASS**, A và B đều COMPLETE/VALID. v_mean_E A 4,41 / B 7,21 m/s; e_lat_peak
  A 0,004 / B 2,97 m. Báo song song: v16 và v15 BLOCKED_WITNESS (luật cũ).
- **Người dùng [chat] 17/11:** "tối ưu upload hết dữ liệu không cần thiết ở D và E lên G, sửa lại I01-S1 rồi prepare lại, I04 bạn
  tự quyết". I01-S1: nguyên nhân là vòng tốc độ EGO dao động giới hạn, kéo dài tới khoảng 12 s (ngày 16/11 chỉ khoảng 6 s); cửa
  sổ 2 s cố định ngay trước điểm quyết định. → addendum P (io-i-v1.3 b, `native-io-prepare-i14.py`): một lần prepare lại với
  chạy đà ×3/2 (64 → 96 m). I04: Claude quyết dưới ủy quyền của Duy là chạy lại chính I04 dưới version mới (PASS cũ đã hạ theo
  addendum L). Doc `PREREG_M56_IO_I_ADDENDUM_O_P_20261117.md` (`7fd7436`). Batch `r17c` (`run-asel2-io-i17.sh`,
  I01-S1 + I04, product v17, pair dưới v17/v16/v15). Guard r16f đã chết từ khoảng 03:05Z (PID bị dùng lại); đã bật guard r17c
  trước batch.
- **Sự cố tooling:** self-test đầu tiên của `native-io-prepare-i14.py` chạy vào `M.main()`, CARLA khởi động ngoài cguard
  và chết ngay ở BODY_BBOX_ZERO (không có cảnh nào, không P5). Đã sửa: self-test chạy trước mọi import. Thư mục rác đã xóa.
- **Offload đợt 3:** `offload-d-to-e-20261117c.py` chuyển 124 mục D → E: mọi `m56_v2_ab/io_ab/f_ab` cũ và mọi `m56_v6_pair`
  cũ (mọi `pair-result.json` GIỮ trên D cho `latest_pair`), `m56_offline_v1/diagnostics`, và `pytest_receipts` thành
  một file .tar (có 184 symlink). Không chuyển `m56_v2_prepare_*` (builder revision đọc các thư mục 25/10). Đo inode: không có
  hard link (89,6 GB logic = 89,6 GB thật). Uploader viết lại chạy theo lô 3 GB, thử lại khi DB DriveFS bị khóa (bản trước
  chết lúc 15:14 vì `WinError 33`). Cổng xóa vẫn là pending == 0 và mọi mục của lô khớp số file và byte trên cloud. Release
  `--full` hoặc chấm lại cảnh cũ: phải tải về trước (`robocopy "G:\My Drive\m56-offload-20261116\<rel>" outputs\<rel> /E`).

## 17/11 chiều (2): kết quả r17c (I01-S1, I04 dưới product v17); uploader xóa từng file

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Batch `m56_asel2_io_20261117T085656Z` (`ASEL2_IO_END`).

- **I04 (io-i-v1.3 a/b + v17 + G5): PASS** dưới cả m56-v17 (`m56_v6_pair_20261117T095132Z`), m56-v16 (`…102227Z`) và
  m56-v15 (`…104856Z`); ba bản cho cùng kết quả. Prepare PREPARED; probe 3 đạt (t_clear − TRIGGER = 1,45 s ≤ 2,3 s;
  event_clear − TRIGGER = 2,3 s). A/B `m56_io_ab_Town06_20261117T093031Z` (đã tiêu P5 cho version này). A và B đều
  CONFIRMED/COMPLETE/VALID, d09_binds true. v_mean_E: A 6,968, B 11,387 m/s. e_lat_peak: A 0,0004, B 3,240 m. comparisons
  0,3881 | 0,99987. Báo cạnh PASS cũ của I04 (đã bị hạ ngày 15/11 theo addendum L).
- **I01-S1: prepare PREPARED ngay lần đầu** (chạy đà 64 m; retry của addendum P không cần bắn; `io_i13b_first` = null).
  **Probe 3 không đạt: `SOURCE_CLEAR_LATE`, `SOURCE_CLEAR_EVENT_LATE`** (stop `TRIGGER_PLUS_2_3_S`, t_clear = null) →
  `BLOCKED_FIXTURE`, không A/B, không tiêu P5. Chẩn đoán (trace probe 3): NPC 18 km/h (4,71 m/s) có đổi làn; offset lệnh
  là 1,46 m lúc TRIGGER và đạt 3,25 m (= |separation|) lúc +2,25 s. Nhưng xe bám trễ đường lệnh và còn lệch hướng khoảng 8°
  (yaw −171,7°), nên tới +2,3 s một góc thân xe vẫn còn trong làn nguồn. Muốn sửa phải đổi recipe/hình học (NPC bắt đầu đổi
  làn sớm hơn so với mốc TRIGGER, hoặc quãng đổi làn ngắn hơn ở tốc độ thấp), không đổi ngưỡng 2,3 s. Cần addendum Q viết
  trước khi chạy. Chưa làm.
- **Uploader (người dùng [chat] 17/11: "upload xong file nào thì xóa luôn file đó"):** `offload-e-to-drive-20261117.py`
  viết lại. Một luồng chép E → G (tối đa 3 GB đang chờ); vòng chính mỗi 60 s đọc bản sao DB DriveFS và xóa TỪNG file trên E
  khi file đó trên G đã có id cloud (DriveFS giữ id `local-…` tới khi upload xong; đo: `local_stable_ids` ⇔ id `local-%`,
  0 ngoại lệ cả hai chiều) và cùng kích thước. Mục nào hết file thì ghi `DELETED_E` (gỡ junction nếu có). Bản sao DB bị
  "malformed" thì bỏ qua lần đó (bản trước sẽ chết). Chạy lại vẫn an toàn: kiểm G là tập cha của phần còn lại trên E.
  Chạy detached `m56_offload_cloud_20261117d` (đã dừng bản theo lô 20261117c).

## 18/11: ngoại lệ repo, r17q/r/s/t (successor I), nhóm M (addendum R), F, offload

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

- **Ngoại lệ repo:** quyết định 18/11 (skill crfp-project) đưa CARLA-Funny-Moments về chỉ đọc. Người dùng phiên này [chat]
  18/11 chọn "Ngoại lệ: M56 vẫn ở repo cũ": M56 tiếp tục chạy và commit ở repo này, chỉ riêng M56.
- **Successor I (addendum Q, io-i-v1.3 a/b + product m56-v17), không A/B nào chạy, không tiêu P5:**

| Cảnh | Prepare | Cổng chặn |
|---|---|---|
| I05-S2 (Town13) | PREPARED (r17t) | probe 3 `READINESS_PROBE3` (G1) + `SOURCE_CLEAR_EVENT_LATE` |
| I06-S2 (Town13) | PREPARED (r17t) | probe 3 `SOURCE_CLEAR_LATE` (G3) |
| I07-S2 (Town12) | PREPARED (r17q) | probe 3 `SOURCE_CLEAR_LATE` (G3) |
| I08-S2 (Town12) | PREPARED (r17q) | addendum L `GAP_NOT_REALISED` (22,278 vs 24,158) |

  r17q/r17r/r17s: I05-S2, I06-S2 dừng `SCENE_ERROR` RPC 60 s khi stream Town13 dưới áp lực RAM (CARLA 19 GB / 31,6 GB).
  Technical fix 4 (`9f49bf7`): timeout RPC 300 s sau khi nạp Town12/13, chỉ là trần chờ. r17t chạy qua prepare.
  Cùng I01-S1, mọi cảnh I chưa PASS đều dừng ở G3/G1/L. PASS I hiện có: I02-S2 (v17), I03, I04 (v17/v16/v15).
- **Nhóm M:** addendum R (`825a863`), product m56-v18 (`7fe44e9`, khóa `npc_planner`). Mô phỏng hiệu chỉnh
  `m-npc-edge-sim.py`: M01-S1, M06-S2, M08-S2 không giữ được NPC trong vùng drivable ở mọi lookahead; không A/B.
- **F:** F06 `DIVERSITY_DEFICIT`, F04 `BLOCKED_CAPABILITY` (giữ). v18 = v17 + v14 phần 1 (`76e0d90`); test F/lùi/bò/stock
  trên v18 chạy lại 18/11 (lần 17/11 bị Claude Code dừng vì thiếu RAM). Tooling native F05 chưa viết.
- **Offload:** máy khởi động lại 18/11 13:36 (guard, uploader chết). Uploader per-file chạy lại (`m56_offload_cloud_20261118b`),
  mover D → E chạy lại với ngày mới (`m56_offload_d2e_20261118a`: 6 thư mục `m56_io_ab_*` 17/11 + diagnostics + pair dirs,
  `pair-result.json` vẫn giữ trên D). Đã xóa 10 GB rác C: của Claude (8,1 GB `pytest-of-ADMIN` của lần test bị dừng, 2,7 GB
  bản sao DB DriveFS của uploader bị dừng); uploader nay dùng một thư mục snapshot cố định.


### 18/11 (2): M dưới addendum S, F05 dưới addendum T/U

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Người dùng phiên này [chat] 18/11 "làm hết cho tôi".

- **M (addendum S, `1a9883f`/`31e69fd`):**
  - Cổng `S_NPC_EDGE` mô phỏng NPC stock trên connector, khớp 6/6 episode đã niêm.
  - Lap 1 của state 10: cả 8 slot M `EMPTY_NO_ELIGIBLE_CANDIDATE`. Trong 11 town, 277 site M qua B5; biên lớn nhất 0,363 m, dưới ngưỡng 0,45.
  - Không tiêu B3, không A/B.
  - Đường còn lại thuộc quyền Duy: controller NPC không stock, hoặc đổi spec §5.2.
- **F05 addendum T (`1475e9b`, v18 `9d16f43`):**
  - Luật mới: readback steer của creep |steer| ≤ 1/50.
  - Lý do: trên F01/F02 đã niêm, 0/401 khung đang chạy có steer đúng 0 (lớn nhất 0,0072).
  - Luật cũ steer == 0 được giữ và báo song song.
- **F05 addendum U** (doc `PREREG_M56_F05_ADDENDUM_U_20261118.md`, v18 `1f1d038`, tooling `3f1cefe`/`4b4af86`):
  - Hai luật đúng-1-m làm B không bao giờ dừng được native: `progress==1 and uncertainty==0` và `reach` ở `progress==1`. Nay thay bằng "dừng trong khoảng dự trữ 1 m sau stopping bound". Luật cũ giữ.
  - Thêm hook `kit.seal_frame` vào runtime.
  - Đã kiểm trên dữ liệu niêm:
    - Xe đứng yên có pose giống từng bit sau khoảng 15 khung. A và B giống nhau, và hai session (prepare với A/B) cũng giống nhau.
    - Sai số ground ≤ 0,040 m.
    - Body runtime khác bbox của prepare, nhưng giống nhau giữa probe và A/B. Proof vì vậy bám body quan sát được.
  - Tooling: prepare F05 (2 lần settle cho gap chính xác, 4 probe creep cho calibration), builder revision F05 (gate env), compile hai lượt cho CREEP_STOP_BOUND, `F05Kit`, `run-f05-u.sh`.
  - Test v18: 120 test F05 qua; 21 test evaluator chạy lại trên luật U cuối cũng qua.
- **Guard** stopper/watchdog/cguard chạy lại với hậu tố `r18a`.
- **F05 stage 1 r18a:** prepare dừng `SCENE_ERROR INVALID_BODY_TRANSFORM` ở settle1.
  - Nguyên nhân: Town12 là map lớn, nhánh F05 chưa stream site nên actor ngủ và bbox = 0.
  - Đã sửa (`4b4af86`) rồi chạy lại `r18b`. Prepare chạy lại được; không A/B nào chạy, không tiêu P5.
- **F03:** grade probe r7 cho 0/6 site lùi được (pitch 3,5–8,8°), tốc độ lùi đúng 0.
  - Giả thuyết của Claude, chưa kiểm: xe đứng yên bị PhysX cho ngủ, nhả phanh không đánh thức.
  - Probe v2 (`native-f03-rollback-probe.py`) thả xe khi đang chạy. Chỉ chạy sau F05 stage 1.
- **Claude Code dừng vì thiếu RAM:** waiter test/mover, waiter stage 1, và lần chạy offline kit check đầu.
  - Kiểm tay: mover xong (D còn 126 GB trống).
  - Offline kit check chạy lại detached (`m56_f05kit_offline_r18b`).

### 18/11 (3): F05 A/B duy nhất (P5) dưới v18 + addendum T/U

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

- **Prepare r18c** (`m56_v2_prepare_Town12_20261118T091935Z`): PREPARED.
  - d0 thực hiện 4,091 m. Gap settle không đổi qua 311 khung, hai lần settle cho cùng một giá trị.
  - Calibration bò (4 probe):
    - đỉnh tốc độ 1,31 m/s;
    - quãng dừng 0,153 / 0,049 / 0,026 / 0,005 m.
  - Giá trị đặt cho CREEP_STOP_BOUND: bound 0,21 m, vmax 1,42 m/s, boundary 0,77 m, uncertainty 0,01.
  - Hai lần chạy prepare trước bị chặn, đã sửa rồi chạy lại (prepare chạy lại được):
    - r18a: actor ngủ, bbox = 0;
    - r18b: thân EGO ở trạm 0 của route nên gap = None.
- **Compile:** FROZEN, ADMITTED; contract EGO:A, EGO:B, NPC đều OK.
- **A/B** (`m56_f_ab_Town12_20261118T093346Z`, P5 đã tiêu cho F05 dưới v18):
  - A: kết thúc sạch.
  - B: `RESPONSE_BLOCKED` `CREEP_ORIGIN_UNBOUND` ở khung TRIGGER (khung thứ 30). B chưa có số đo nào.
  - Cặp v18 và v13: `BLOCKED_WITNESS`.
- **Nguyên nhân (đã kiểm trên dữ liệu niêm):** lỗi tooling, không phải product.
  - Runner giữ quan sát đầu tiên làm boundary và không đưa vào frames. Kit lại đưa khung đó vào history.
  - Kết quả: TRIGGER trên history có 31 witness (3004…3034), còn của runner có 30 (3005…3034), nên digest khác nhau.
  - Bản kiểm offline tổng hợp không có khung boundary nên không bắt được lỗi này.
- **Sửa** `a032cbf`: kit bỏ quan sát đầu tiên của mỗi episode. Bản kiểm offline nay đưa vào một khung boundary.
- **Không chạy lại A/B (P5).**
  - A/B F05 dưới phiên bản này đã tiêu.
  - Một A/B F05 mới cần quyết định của Duy / người có thẩm quyền: phiên bản mới, hoặc successor B3.
  - Tooling đã sẵn sàng: `bash run-f05-u.sh ab <REVF> <prereg>`.
- **F03 probe v2** (lùi khi đang chạy) đang chạy với nhãn `m56_f03_rollback_r18d`.

### 18/11 (4): Đính chính F03 + probe hợp lệ đầu tiên, sửa test `past_yaw`

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

- **Đính chính mục 18/11 (2):** dòng "grade probe r7 cho 0/6 site lùi được" không phải bằng chứng về capability.
  - r7 có `M56_SPECTATOR=1` nhưng chỉ thử thả từ đứng yên sau khi giữ phanh. Probe không kiểm tra xe có đang được mô phỏng hay không.
  - r18d (probe v2) thiếu `M56_SPECTATOR`. Với cờ này tắt, `stream_to` không làm gì, nên xe ngủ: ga 0,4 trong 6 s không làm xe nhúc nhích ở cả 18 lần chạy. Kết quả r18d vô hiệu.
- **r18e** (`m56_f03_rollback_r18e`, có spectator) là probe hợp lệ đầu tiên. Trên làn hướng lên dốc:

| Site | Thả khi đang chạy, số N | Thả khi đang chạy, số tự động | Từ đứng yên, không phanh |
|---|---|---|---|
| Town12 1062/−1 (3,7°) | lùi, trung bình 2 s **0,946 m/s** | giữ yên (lùi tối đa 0,10) | không chuyển động |
| Town12 1085/1 (3,4°) | **0,854 m/s** | giữ yên (0,08) | không chuyển động |
| Town11 285/−1 (3,3°) | **1,471 m/s** | giữ yên | 2,27 m/s (ngoài khoảng) |

- **Diễn giải:** xe chỉ lùi khi đang chạy và về số N.
  - Đây là đọc số của probe, chưa phải luật.
  - Ba giá trị in đậm nằm trong khoảng vN_char [0,65; 1,54] của PREREG F phần 1.
  - Hướng route: 1062 và 1085 thẳng trục (lệch 0,13° và 0,12°), đạt điều kiện căn trục v14 cho EGO B lùi. Town11 285 lệch trục 7–44°, bị loại.
- **Hệ quả với product:** contract NPC F03 hiện tại (`NPC_HOLD` → `UNPOWERED`, giữ số đọc lại) là thả từ đứng yên, số tự động. Natively F03 vì vậy không thể xảy ra.
  - Đây là một nhận định, không phải số đo trên cảnh.
  - Cần đổi product: thêm pha tiến trước khi thả, và về số N khi `UNPOWERED`.
  - `_detect_f03` không đòi NPC đứng yên trước TRIGGER.
  - Chưa quyết thiết kế F03 phần 2. Đang chạy probe kiểm 2 (`m56_f03_brake_r18f`): thả số N, rồi phanh 0,3 ở TRIGGER + 2 s. Probe này cho biết NPC có dừng không và tổng quãng lùi so với d0 = 5,2 m.
- **Test** `test_reverse_stop_history_cannot_borrow_foreign_or_uncorrelated_packets[past_yaw]` (v18 `8d52959`):
  - Test này fail trên v18 và trên v14, pass trên v17.
  - Nguyên nhân: v14 phần 1 chấp nhận lệch yaw ≤ 1°, nên lỗi giả lập yaw = 1,0° không còn là lỗi.
  - Đã đổi lỗi thành 2°. Ở 1,5° và 2°, guard vẫn chặn (`REVERSE_HISTORY_OBSERVATION_UNBOUND`).
  - `test_reverse_response.py`: 75 passed.
  - Lần chạy F trên v18 (13:43, 2:52:40) cho 569 passed, 1 failed; failure đó chính là test này.
- **Offline kit F05** sau bản sửa boundary (`m56_f05kit_offline_r18d`): PASS.
