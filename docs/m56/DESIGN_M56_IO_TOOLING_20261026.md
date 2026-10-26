# M56: thiết kế tooling native cho I/O (26/10/2026)

**Bối cảnh:**
- Duy, 26/10/2026: "Tiếp tục dựng tooling I/O với pilot O, chỉ chuẩn bị". Recipe P3 cho I/O đã được duyệt ở v4.
- Consumer v5 C2 (normative đọc `targets['NOMINAL']`) và C3 (lateral contract trên route thật) đã được duyệt.
- Chưa cảnh I/O nào từng được chuẩn bị native.

**Không có A/B I/O nào** trước khi Duy duyệt bản đăng ký trước recipe I/O (§4).

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

## 1. Consumer đòi gì (đọc từ code đã đóng băng và ca tổng hợp `tests/m56/o_cases.py`)

| Thành phần | Yêu cầu |
|---|---|
| Pair | `('v_mean_E','e_lat_peak')`; đơn vị `('m/s','m')`; window `('TRIGGER','X_END')`; reference `map:` + digest của `map_reference` |
| `map_reference` | `{'method':'segment-map-normal-v1','route','normals','refs'}`; mỗi segment của route một pháp tuyến |
| Sections | O: `O_DECISION`, `O_RETURN_START`, `X`, `DESTINATION`. I: `I_SOURCE_BOUNDARY`, `X`, `DESTINATION` |
| Event | O: TRIGGER khi mũi EGO vượt `O_DECISION`; RETURN_MARKER khi vượt `O_RETURN_START`; X_END khi toàn thân xe vượt `X`. I: TRIGGER khi NPC lấn qua biên làn nguồn. Ngoài ra có các event TARGET/RETURN_LANE_CONFIRMED |
| `topology` | `category`; `action_regions` (EGO_INITIAL, EGO_TARGET là hộp theo trục tọa độ); với I thêm `npc_regions`; `lane_geometry[role] = {'separation_m', 'lane_width_m': {'initial','target'}}`; `driving_regions`; `drivable_ref` (FIT v7) |
| Route của response | đúng route fixture của role; mỗi bước ≤ 0,25 m (waypoint CARLA) |
| Đoạn đổi làn | thẳng (tổng biến thiên hướng ≤ 1°) **và** song song một trục tọa độ (lệch ≤ 1°); hộp INITIAL/TARGET rời nhau trên trục ngang; độ tách = khoảng cách tâm hai hộp ± 0,05 m |
| Profile | quintic, đoạn đổi làn dài đúng 3 × nominal, độ lệch = độ tách làn; ngân sách gia tốc ngang (100/3)·Δ²·v⁴/L⁴ ≤ 6,25 |
| Nominal | EGO ∈ {6; 7,5; 9,375}; NPC của I ∈ {5; 6,5; 8,125} |
| Reference switch | `{'cause','event','marker_arc_m','route','profile'}`; event ∈ {TARGET_LANE_CONFIRMED, RETURN_LANE_CONFIRMED, NPC_TARGET_LANE_CONFIRMED}; route của switch là route làn song song; transition có guard `REFERENCE_MARKER:<cause>` |
| Proof theo frame (online) | `lane_change_path` (`LANE_CHANGE_PATH`, `bounded-lane-change-corridor-v1`; limits gồm fixture_hash, frame, actors_hash, from/to_region_hash, route_hash, minimum_clearance_m) và `return_path` (`RETURN_PATH`, `bounded-return-corridor-v1`). Cả hai cần clearance − uncertainty ≥ 0,2 m và review gắn đúng digest |
| `metric_context` theo frame | thêm `map_reference` |

## 2. Khả thi của site (OpenDRIVE, kiểm offline)

| Site | Cảnh | Đoạn thẳng song song trục của làn | Trong cửa sổ của spec |
|---|---|---|---|
| Town06 road 40 | I03, O03 | toàn bộ 470 m | đủ |
| Town05 road 37 | I02, O02 | 205 m (s 301–506) | khoảng 99 m |
| Town04 road 45 | I01, O01 | 128 m (s 279–407) | khoảng 61 m; đổi làn đi và về cần khoảng 60 m, sát nút |

Sáu cảnh I04/O04, I05/O05, I07/O07 (cùng I06/O06 đang đề xuất) có vE nằm ngoài tập consumer cho phép. Đây là mục c của
`PROPOSAL_M56_ROAD_TO_46_20261026.md`; tooling chưa làm các cảnh này.

## 3. Đã có sẵn trong catalog đóng băng

- Chương trình EGO A/B và NPC (O: NPC 2,5 m/s; I: chương trình PROVISIONAL).
- Target và profile quintic (trên arc tổng hợp).
- Tham số Dlc, X, gap, front_t0, return_start, vE, vN.
- Ký hiệu làn, ví dụ O03: `E-3→-4→-3, N-3`.

## 4. Tham số Claude phải tự chọn (vào bản đăng ký trước recipe I/O)

1. **Ánh xạ arc tổng hợp sang station native.** Đặt điểm bắt đầu đổi làn, `O_DECISION`, `O_RETURN_START` và `X` trên route
   CARLA. Đề xuất: giữ nguyên các khoảng cách của spec, tính từ điểm đầu đoạn thẳng song song trục.
2. **Route:** waypoint làn CARLA nội suy mỗi 0,25 m. Route của switch là làn đích song song.
3. **`action_regions`:** hộp theo trục từ biên làn CARLA (bề rộng `lane_width`) trên đoạn thẳng. `lane_geometry` lấy từ
   CARLA.
4. **Hành lang của `LANE_CHANGE_PATH`:**
   - đề xuất: phần làn đích từ mũi EGO lùi 1 thân xe tới mũi EGO + Dlc + 1 thân xe;
   - clearance = khoảng cách nhỏ nhất từ thân NPC tới hành lang;
   - uncertainty theo `CONTINUOUS_GEOMETRY`.
5. **Hành lang của `RETURN_PATH`:** tương tự, trên làn ban đầu.
6. **`map_reference.normals`:** pháp tuyến xy của từng segment route EGO.
7. **Vị trí xuất phát NPC (gap) và readiness/marker:** theo E6 như C/L/M.
8. **PID của EGO ở 6–9,4 m/s:** dùng lưới erratum 2.

## 5. Kế hoạch

1. **`native-io-prepare.py`:** route 0,25 m, region, section, `lane_geometry`, `map_reference`, switch, probe readiness (không
   A/B).
2. **Bộ sinh proof theo frame trong kit:** `lane_change_path`, `return_path`, `map_reference`. Test với ca tổng hợp và với frame
   native.
3. **Nhánh I/O trong `native-v2-ab.py`.**
4. **Pilot:** O03 (Town06), chỉ chuẩn bị.
5. **Bản đăng ký trước recipe I/O → Duy duyệt → A/B.**
