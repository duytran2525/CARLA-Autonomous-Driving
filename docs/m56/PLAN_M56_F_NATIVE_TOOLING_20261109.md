# M56 A-SEL2: kế hoạch tooling native cho F (09/11/2026)

Kế hoạch kỹ thuật của Claude, không phải prereg. Các input đã chốt ở `PREREG_M56_F_ASEL2_20261109.md` (phần 1). Product là
`m56-v13`.

## Product đã có sẵn (không phải viết lại)

| Phần | Vị trí |
|---|---|
| Chương trình và kiểm normative cho F01–F06 | `m56/response.py` (`_f_script_contract`, `_forward_contract`) |
| Event F | `m56/metrics.py`: `F01_BRAKE_MARKER`, `NPC_F01_STOP_HOLD_CONFIRMED`, `F01_N_CLEAR`, `N_MOVE`, `F02_END`, F05/F06 … |
| Cặp metric | `m56/metrics.py:20–25` |
| Fixture tổng hợp mẫu | `tests/m56/f01_cases.py` (`f01_fixture`), `f02_cases.py`, `f03_cases.py` |

## Phải viết (theo mẫu `native-io-prepare.py` và `native-io-ab.py`)

1. **`native_f_common.py`**:
   - routes: EGO và NPC trên **cùng một làn** của site R1 (road/section/lane), qua `xodr_routes.lane_points`;
   - sections theo trạm route: `F01_BRAKE_START`, `F01_END`, `DESTINATION` (F01). F02, F05, F06 lấy theo test case tương ứng;
   - responses: EGO A/B theo `f01_response`, đặt lên route thật (như `catalog-recipes.f_recipe`); NPC `NPC_COMMON` với
     `f_script` và `policy_hash`, nominal 17/5;
   - tham số candidate `vN_char` và `d0` (declared), mỗi cái kèm `PARAMETER_RATIONALE`.
2. **`native-f-prepare.py`**:
   - probe 1: hai xe từ đứng yên lên tốc độ danh nghĩa, lấy t_ready;
   - đặt NPC xuất phát sao cho khoảng hở lúc ready là d0;
   - probe 2: đo marker readiness và T_r;
   - giữ đủ các luật cl-v1, spawn nghiêng, spectator và load 600 s.
3. **`native-f-ab.py`**: compile (`compile_fixture` với BODY_FIT, GROUND, RUNIN_ROOM, DESTINATION_ROOM, drivable dv1,
   `driving_regions`, topology `{'category': 'F', 'mechanism': ...}`), admission, rồi `run_ab` (outer 1500 s), rồi pair qua
   `native-v6-pair.py`.
4. **Revision:** `native-v5-revision.py` thêm `asel2_f` (slot F01…F06 → candidate F với `route_recipe` của site), bật bằng
   `M56_ASEL2_F=1`.
5. **Chọn site:** `fill-v4-generate.py` thêm loại F (pool R1/R3, cổng B5 và cổng dốc), offset seed theo prereg F §3.

## Thứ tự

F01 trước (product đầy đủ nhất, chương trình dọc), rồi F05, F02. F06 cần đèn lùi và Δ trong cảnh. F03 và F04' chờ phần 2.

Mỗi cơ chế: test offline (compile + `_forward_contract` OK), rồi một lần chuẩn bị native, rồi một A/B (P5).
