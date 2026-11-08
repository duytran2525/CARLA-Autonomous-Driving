# M56 release §11: số đếm thật, bản partial (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** ngày 07/11/2026, Duy (tự xưng) quyết rằng release §11 dưới 46 cảnh do Duy một mình quyết ("4.không cần ts.hằng một
mình tôi là được rồi"), và trao toàn quyền cho Claude. Báo cáo này do Claude lập dưới ủy quyền đó.

**Đây không phải catalog release.** Spec §11: "Failure delivers honest partial counts/IDs/reasons/raw, not synthetic final catalog."
`export_catalog` của product (`m56/catalog.py:490`) chỉ ghi file khi `_release_deficits` rỗng. Hàm này cố định cứng 46 ứng viên,
≥ 23 junction đủ điều kiện, 155 phép so PASS và A/B PASS cho mọi ứng viên. Claude không đổi các cổng này và không gọi export. Mục 5
liệt kê các deficit, suy ra từ code của hàm đó (không chạy hàm).

**Bytes cuối:** product `feat/m56-v9` `1db746f`, đã merge cục bộ vào `feat/m56-v1` (`a23c09f`); `m56/` và `tests/m56` trùng byte
với v9. Không push. Full suite trên bytes cuối: `m56-full-suite-10b-20261108` (1237 test), kết quả ở mục 6.

## 1. Đếm theo loại

| Loại | Mục tiêu | Đề xuất (C0 partial) | Có A/B dưới version hiện hành | Cặp hợp lệ |
|---|---|---|---|---|
| C | 8 | 8 | 3 (C01, C02, C05) | 2: C01, C05 |
| L | 8 | 8 | 4 (L01, L02, L04, L07) | 2: L01, L04 |
| M | 8 | 8 | 3 (M02, M06, M07) | 0 |
| I | 8 | 6 (I01–I05, I07) | 6 | 2: I03, I04 |
| O | 8 | 6 (O01–O05, O07) | 5 (O01, O02, O03, O05, O07) | 3: O01, O02, O03 |
| F | 6 | 3 (F01, F03, F04) | 0 | 0 |
| **Tổng** | **46** | **39** | **21** | **9** |

Theo luật đóng băng gốc chỉ có 3 cặp hợp lệ (C01, L01, C05).

## 1b. Spawn, action outcome theo từng episode (21 A/B × 2 = 42 episode)

Mỗi cảnh lấy kết quả pair dưới consumer mà báo cáo của nó dùng (`outputs/m56_v6_pair_*/<cảnh>/pair-result.json`).

| Trường | Đếm | Ghi chú |
|---|---|---|
| spawn CONFIRMED | 38 / 42 | UNKNOWN: M02 A và B (`INITIALIZATION_INVALID`), I05 A và B |
| physical COMPLETE | 21 / 42 | 18 episode của 9 cặp PASS, cộng O05 B, O07 B, I01 A |
| witness VALID | 21 / 42 | cùng tập với COMPLETE |

| Cảnh | A (spawn / physical / witness) | B |
|---|---|---|
| C01, C05, L01, L04, O01, O02, O03, I03, I04 | CONFIRMED / COMPLETE / VALID | CONFIRMED / COMPLETE / VALID |
| C02, L02, M07 | CONFIRMED / UNKNOWN / INVALID | CONFIRMED / UNKNOWN / INVALID |
| L07 | CONFIRMED / INCOMPLETE / UNCERTAIN | CONFIRMED / FAILED / UNCERTAIN |
| M02 | UNKNOWN / UNKNOWN / INVALID | UNKNOWN / UNKNOWN / INVALID |
| M06, I07 | CONFIRMED / FAILED / INVALID | CONFIRMED / FAILED / INVALID |
| O05 | CONFIRMED / UNKNOWN / UNCERTAIN | CONFIRMED / COMPLETE / VALID |
| O07 | CONFIRMED / FAILED / UNCERTAIN | CONFIRMED / COMPLETE / VALID |
| I01 | CONFIRMED / COMPLETE / VALID | CONFIRMED / INCOMPLETE / UNCERTAIN |
| I02 | CONFIRMED / FAILED / INVALID | CONFIRMED / INCOMPLETE / UNCERTAIN |
| I05 | UNKNOWN / FAILED / INVALID | UNKNOWN / INCOMPLETE / INVALID |

## 2. Cặp hợp lệ và điều kiện kèm theo

| Cặp | Hợp lệ theo |
|---|---|
| C01, L01, C05 | mọi luật |
| L04 | consumer v7+ (FIT có xét hướng thân xe) |
| O03, O01 | consumer v8 |
| O02 | v8 + cận lateral theo điểm (erratum `ce3fc43`, đặt sau khi thấy số) |
| I03 | io-i-v1.1 (đặt sau khi thấy số) + cận theo điểm; v8 và v9 |
| I04 | io-i-v1.1 + cận theo điểm + v9 (chuỗi nominal) |

## 3. Từng ứng viên không có cặp hợp lệ

| Cảnh | Trạng thái | Lý do | Nguồn |
|---|---|---|---|
| C02 | BLOCKED_WITNESS | CONTACT, FIT | `M56_V7_RESULT_20261026.md` |
| C03 | BLOCKED_FIXTURE | `NPC_TURN_BEFORE_EXIT` (mục e, phương án i) | `DECISION_M56_ITEMS_D_E_20261107.md` |
| C04 | BLOCKED_FIXTURE | `READINESS_NOT_STEADY` | `M56_V5_NIGHT_RESULT_20261026.md` |
| C06 | BLOCKED_FIXTURE | `NPC_SIGNAL_HOLD_IN_PROBE2` | như trên |
| C07, C08 | BLOCKED_FIXTURE | route EGO đóng băng ở C0 bị lỗi: C07 chạy trên làn Shoulder 0,5 m (`13/-2`); C08 xuất phát trong junction, không có làn Driving hướng nam trong 3 m | `M56_CL_V1_RESULT_20261108.md` §3 |
| L02 | BLOCKED_WITNESS | GROUND, CONTACT | `M56_V7_RESULT_20261026.md` |
| L03 | BLOCKED_FIXTURE | C4 `CONFLICT_COMPONENTS_TOO_CLOSE` | `M56_V5_NIGHT_RESULT_20261026.md` |
| L05 | BLOCKED_FIXTURE | `NPC_TURN_SPEED` (mục e) | `DECISION_M56_ITEMS_D_E_20261107.md` |
| L06 | BLOCKED_FIXTURE | `NPC_TURN_BEFORE_EXIT` (mục e) | như trên |
| L07 | FAILED | thiếu CLEAR_N, E_ENTRY, DESTINATION; B có EARLY_ENTRY | `M56_V7_RESULT_20261026.md` |
| L08 | BLOCKED_FIXTURE | `PHASING_ROOM` | `M56_V5_NIGHT_RESULT_20261026.md` |
| M01 | BLOCKED_FIXTURE | `NPC_SIGNAL_HOLD_IN_PROBE2` (cl-v1 b) | `M56_CL_V1_RESULT_20261108.md` |
| M02 | BLOCKED_WITNESS | `INITIALIZATION_INVALID`: điểm xuất phát trên dốc −1,35°, giới hạn pitch ban đầu 0,1° | như trên |
| M03, M05 | BLOCKED_FIXTURE | `NPC_TURN_BEFORE_EXIT` (mục e) | `DECISION_M56_ITEMS_D_E_20261107.md` |
| M04 | BLOCKED_FIXTURE | `READINESS_NOT_STEADY` | `M56_V5_M_E3_RESULT_20261025.md` |
| M06 | FAILED | CONTACT, FIT, `NPC_UNPLANNED_REVERSE` | `M56_V7_RESULT_20261026.md` |
| M07 | BLOCKED_WITNESS | CONTACT, FIT | như trên |
| M08 | BLOCKED_FIXTURE | `PROBE1_NO_FRAMES`: EGO va chạm lúc spawn trong junction, kể cả với pitch theo waypoint | `M56_CL_V1_RESULT_20261108.md` |
| I01 | BLOCKED_WITNESS | B `X_END_MISSING`; đổi làn trước khi làn nguồn được xác nhận trống | `M56_IO_V1_1_V1_4_RESULT_20261108.md` |
| I02 | FAILED | `TRIGGER_MISSING` (road lệch trục 0,84°) | như trên |
| I05, I07 | FAILED | va chạm; lề 3,3 s không đủ ở vE thấp | như trên |
| O04 | BLOCKED_FIXTURE | `EGO_NOT_AT_DECISION_IN_PROBE1` (io-v1.4 c) | như trên |
| O05 | BLOCKED_WITNESS | A `ACTION_REGION_WITNESS_UNKNOWN` | như trên |
| O07 | FAILED | EGO không vượt được NPC | `M56_IO_FILL_O_V13_RESULT_20261107.md` |
| F01, F03 | BLOCKED | chưa có runtime recipe (chương trình NPC của spec §8 còn PROVISIONAL) | `PROPOSAL_M56_ROAD_TO_46_20261026.md` |
| F04 | BLOCKED_CAPABILITY | CARLA 0.9.16 không có API hình học cửa xe | `DECISION_M56_ITEMS_D_E_20261107.md` |

**Chưa được đề xuất (7 chỗ):** I06, I08, O06, O08, F02, F05, F06. Các đợt fill v2 và v3 đã hết ứng viên đủ điều kiện, và prereg của
chúng ghi "để trống, không nới thêm".

## 4. Site và junction

- Revision C0 partial cuối (`outputs/m56_c0_partial_io_clv1_20261107T233626Z`): 39 ứng viên, 32 site, 24 junction site.
- Junction đủ điều kiện, tức có cảnh giao hàng được (Claude đếm, chưa chạy `audit_diversity`): 4, gồm site của C01, C05, L01, L04.
  Spec cần ≥ 23. Các cặp hợp lệ của O và I nằm trên road site, không phải junction.

## 4b. Phép so giữa các cảnh (155 = 5 × C(8,2) + C(6,2))

- **Declared:** spec §6.4 tự ghi thiếu hụt của quy tắc khác biệt (≥ 2 tham số lệch ≥ 20%): 15/28 cặp C, 9/28 cặp L và 1/6 cặp M
  chưa đạt theo số khai báo. Claude **chưa chạy** `audit_diversity` trên revision cuối, nên không có số declared mới.
- **Realized:** một phép so chỉ realized được khi cả hai cảnh cùng loại đều có A/B hợp lệ. Hiện có 6 cặp như vậy: C01–C05,
  L01–L04, O01–O02, O01–O03, O02–O03, I03–I04, tức **6/155**. Chưa phép so nào được audit hay review, vì audit của product đòi đủ
  46 cảnh.

## 4c. Thay thế

- 26 đề xuất của Astra (đã neo ngày 10/10/2026). 13 chỗ còn lại do thuật toán prereg của Claude lấp qua fill20, fill v2, fill v3
  (`CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`).
- I06, O06 được đề xuất ở fill v3, rồi bị loại vì chỉ có một road.
- Chưa có lần thay cảnh hỏng nào (quota tối đa 20%), vì việc thay cần người chọn có thẩm quyền.

## 5. Deficit của release (suy từ `_release_deficits`, `m56/catalog.py:454`)

| Deficit | Vì sao |
|---|---|
| `CANDIDATE_COUNT` | 39 ứng viên, không phải 46 |
| `JUNCTION_SHORTFALL` | 4 junction đủ điều kiện, cần ≥ 23 |
| `COMPARISON_COVERAGE` | 155 phép so giữa các cảnh cần mọi cảnh có A/B hợp lệ. Hiện chỉ 9/46 cảnh có, nên chưa có phép so REALIZED nào được audit |
| `AB_PROOF` | 30 trong 39 ứng viên không có A/B PASS |

Theo spec, kết quả là `RELEASE_BLOCKED` kèm số đếm thật ở trên. Không có catalog tổng hợp nào được ghi ra.

## 6. Full suite trên bytes cuối

`m56-full-suite-10b-20261108`: 1237 test, launch tách khỏi Claude Code qua `start-guarded.ps1`, với `--retain failed --floor-gb 7
--cap-gb 9`. Mức sàn dung lượng được hạ vì ổ D chỉ còn 17,5 GB trống; suite 9 có đỉnh namespace 6,4 GB. Bắt đầu 08/11/2026. Kết
quả: **đang chạy**, sẽ bổ sung vào đây.

## 7. Muốn tới 46 thì cần gì (nhận định của Claude, không phải quyết định)

Mỗi hướng dưới đây là một version mới hoặc một lần đổi trường C0 đã đóng băng, nên phải ghi công khai là luật đặt sau khi thấy số:
- C/L/M: vùng drivable gồm cả Shoulder và mặt giao lộ (CONTACT/FIT); ước lượng ground nhiều tia; đặt lại điểm xuất phát C0 khỏi
  dốc và khỏi junction (M02, M08); sửa route C0 của C07/C08.
- I: lề TRIGGER theo thời gian NPC làm trống làn nguồn ở từng vN; ranh giới theo tâm làn thật (I01, I02, I05, I07).
- F: recipe NPC của spec §8, và năng lực đo cửa xe cho F04.
- 7 chỗ chưa được đề xuất cần selector có thẩm quyền chọn (ngoài phạm vi ủy quyền của Claude).
