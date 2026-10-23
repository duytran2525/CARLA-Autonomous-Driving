# M56: đăng ký trước runtime-recipe v2 (23/10/2026)

**Thẩm quyền:** [chat] 23/10/2026, người dùng tự xác nhận là Duy, chọn "Approve v2" cho câu hỏi:

> G4/G5 are open, but all 31 frozen scenes lack the data the runner needs (readiness markers, collision sensors, NPC
> program, NPC start distance for phasing) … Do you approve a 'runtime-recipe v2' version, pre-registered and
> committed before any CARLA run, with Claude's phasing rule (not independent) disclosed?

**Thứ tự cam kết:**
1. File này được commit **trước** mọi lần chạy native của v2.
2. Probe native ở §4 là bước chuẩn bị của G4, không phải A/B. Nó dừng trước khi TRIGGER có thể xảy ra.
3. Sau khi có số A/B, không đổi quy tắc nào trong file này.

**Giới hạn phải ghi kèm mọi kết quả:**
- Quy tắc canh pha ở §3 là cách Claude đọc lý do của spec §6.2. Đây không phải quy tắc của spec và cũng không độc lập.
- Mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`.

## 1. Phạm vi

- **Có trong v2:** 16 ứng viên C và L của revision C0 partial `b39ab2e0…` (C01–C08, L01–L08).
- **Không có trong v2:**
  - M01, I, O, F giữ nguyên v1 và có trạng thái BLOCKED, lý do `RUNTIME_RECIPE_MISSING`.
  - Lý do để ngoài: M cần thêm proof `MERGE_TRANSITION`, còn I/O/F cần `action_regions` và các bằng chứng riêng của từng
    loại. Chúng không nằm trong lần đăng ký này.
- **Giữ nguyên:**
  - mọi trường đã đóng băng ở C0: site, town, category, route notation của EGO và NPC, tham số G/vE/vN/LrefN, response
    A/B của EGO, vị trí xuất phát của EGO, weather, light;
  - spec gốc và các addendum A-C0P, A-G45 không đổi byte nào.

## 2. Phần thêm vào ứng viên

1. **Cảm biến va chạm:**
   - EGO và NPC mỗi xe có một actor `sensor.other.collision`, role lần lượt là `EGO_COLLISION` và `NPC_COLLISION`.
   - Mỗi cảm biến gắn vào xe của mình (`attach_to_role`) với pose tương đối 0, tốc độ ban đầu 0.
2. **Chương trình NPC** (phụ lục tạm, không vào catalog, spec §2.1 và §11):
   - FrozenResponse `NPC / NPC_COMMON`.
   - Pha `SETTLE` (0) → `NOMINAL` (vN) sau `CAPTURE_START + 21/20 s`; không có chuyển pha nào khác.
   - NPC đi trên route NPC của chính ứng viên, offset ngang 0.
3. **Readiness:** `environment.readiness = {targets_mps, markers_m}`.
   - `targets_mps`: EGO = vE (C 4, L 2), NPC = vN.
   - `markers_m`: lấy theo §4.
4. **Điểm xuất phát của NPC:** lấy theo §3. Route NPC kéo dài hoặc rút ngắn ở phía thượng nguồn của cùng lane, theo
   `xodr_routes.extend` (quy tắc đi thẳng đã khai báo). Destination của NPC = cửa ra junction + 5 m, đo trên route mới.

## 3. Quy tắc canh pha (của Claude)

Lý do của spec §6.2 là: "braking room + reaction + **half characteristic NPC occupancy interval**". Vì vậy, khi EGO
không phản ứng, NPC phải bắt đầu chiếm vùng xung đột trước lúc EGO tới đó nửa khoảng chiếm chỗ:

```text
t_N = t_E − (LrefN + 4.5 + 0.5) / (2 · vN)
```

- `t_E`: thời điểm mặt trước EGO tới `e_entry` nếu EGO không phản ứng. Ngoại suy từ probe: `t_E = T_r + (e_entry −
  front_E(T_r)) / vE`.
- `t_N`: thời điểm mặt trước NPC tới `n_entry`.
- Khoảng cách xuất phát của NPC: `D_N = d_N(t_N − 21/20)`, với `d_N(t)` là quãng đường từ lúc đứng yên mà probe đo được
  ở tốc độ đích vN.
- NPC không cần hoặc không thể xuất phát sớm hơn EGO: chương trình NPC nhả cùng lúc với EGO, và không có độ trễ âm.
- Các trường hợp BLOCKED_FIXTURE:
  - `t_N − 21/20` nhỏ hơn thời gian NPC cần để đạt vN ổn định → lý do `PHASING_INFEASIBLE`;
  - không kéo dài đủ được route ở thượng nguồn → lý do `PHASING_ROOM`.

## 4. Probe native và marker

1. **Probe 1, tốc độ.** Mỗi ứng viên chạy một lần trên server riêng.
   - Spawn EGO và NPC theo recipe v1, rồi chạy đúng chương trình của chúng. Pha SETTLE và NOMINAL không phụ thuộc
     A/B: trước TRIGGER, response A và B giống nhau.
   - Ghi trạng thái mỗi frame.
   - Dừng khi mặt trước EGO còn cách `e_entry` một khoảng `G + 1 m`, hoặc sau 40 s mô phỏng. Hủy hết actor.
   - Kết quả là `d_E(t)`, `d_N(t)` và `t_E`.
2. **Đặt lại NPC** theo §3.
3. **Probe 2, marker.** Chạy lại giống probe 1 với NPC ở vị trí mới.
   - `T_r` = frame đầu tiên mà, trong 1,0 s liền trước đó, cả hai xe có |tốc độ − đích| ≤ 0,05 m/s.
   - `markers_m` = station của mỗi xe tại `T_r`, làm tròn tới 1/1000 m.
   - BLOCKED_FIXTURE nếu tại `T_r` mặt trước EGO cách `e_entry` không quá `G + 1 m` (lý do `RUNIN_ROOM`).
4. **Nếu A/B lệch probe:** khi chạy A/B, nếu readiness lệch marker quá 0,1 m thì kết quả được ghi nguyên là
   `READINESS_NOT_REACHED`. Không probe lại, không chỉnh marker.

## 5. Bằng chứng G4 (phương pháp kiểm, không đổi nội dung cảnh)

| Bằng chứng | Phương pháp |
|---|---|
| Body | bbox thật của `vehicle.audi.a2` đọc từ actor đã spawn; chiều dài ≤ 4,5 m, nếu vượt thì BLOCKED_CAPABILITY |
| Route | lane center từ XODR lấy mẫu mỗi 1/4 m; so với waypoint của bản đồ CARLA |
| Mặt đất | `world.ground_projection` tại các đỉnh đáy thân xe; sai số mặt đất ≤ 0,05 m |
| Vùng xung đột | hộp của phần giao các swept volume EGO∩NPC, do `compile_fixture` tính |
| Vùng lái | các hộp trục song song nằm hoàn toàn trong hợp các làn xe chạy XODR của các road trên route |
| Tiếp xúc, chuyển động, thời gian | các ngưỡng của spec §5.2 và §7.1 giữ nguyên |
| Va chạm | recipe `recorded-ack-fence-v1` |

Recipe `recorded-ack-fence-v1`:
- Fence là một tick sau frame cuối.
- `request_id` là frame của tick đó; ack là lúc `world.tick` trả về đúng frame đó và hàng đợi callback đã rỗng.
- `remaining` = số gói còn chờ.

## 6. Nhãn kết quả

- **Loại kết quả:** mỗi cảnh cho ra A/B local, mỗi episode ghi đủ ba trục spawn / physical / witness cùng các lý do.
- **Lần chạy:** mỗi action chạy đúng một lần. Lần chạy hỏng được ghi lại, không chạy lại.
- **Không phải release:** kết quả không phải release và không thay review A/B độc lập.
- **Vẫn còn thiếu:** junction 17/23 và 155 phép so.
