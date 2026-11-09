# M56 A-SEL2: realized descriptor cho F (09/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:**
- `DESCRIPTOR_SPECS_M56_ASEL2_20261108.md` §2 dòng F ("soạn trong prereg F, trước A/B đầu tiên của F");
- `PREREG_M56_F_ASEL2_20261109.md` §1;
- `F_SITE_NOTES_20261109.md` mục 7.

**Thời điểm:** commit trước A/B F đầu tiên. Chưa có episode F nào.

## 1. Quy tắc chung

Giữ nguyên `DESCRIPTOR_SPECS` §1:
- đo trên cả A và B, gộp bằng trung bình cộng A và B;
- nguồn là raw đã seal;
- thiếu event ở một action thì không đếm, và phép so liên quan là `BLOCKED_COMPARABILITY`.

Quy ước cho bảng §2:
- Khoảng hở dọc được đo dọc theo route EGO đã đóng băng (`_metric_station` của các đỉnh thân xe).
- Khung readiness là khung đầu tiên runner xác nhận readiness (đầu cửa sổ validation, t2).

## 2. Theo cơ chế

| Cơ chế | `vN_char_r` (m/s) | `d0_r` (m) |
|---|---|---|
| F01 | tốc độ NPC trung bình trên [`F01_BRAKE_MARKER` − 1 s, `F01_BRAKE_MARKER`] | trạm đuôi NPC − trạm mũi EGO tại khung readiness |
| F02 | tốc độ NPC trung bình trên [`TRIGGER` − 1 s, `TRIGGER`] | trạm đuôi EGO − trạm mũi NPC tại khung readiness |

F05, F06, F03 và F04' sẽ được định nghĩa trong một bản sau, commit trước A/B đầu tiên của từng cơ chế.

## 3. Bản ghi máy đọc được

Trong `PolicyBundle.descriptor_specs['realized_by_category']['F']`:

```text
'vN_char': D('m/s', 'npc_characteristic_speed'), 'd0': D('m', 'initial_longitudinal_gap')
D(unit, quantity) = {'unit', 'physical_quantity', 'aggregation': 'mean_of_A_and_B', 'source_actions': ('A','B'),
                     'event': 'per mechanism: F_REALIZED_DESCRIPTORS_20261109 section 2',
                     'window': 'per mechanism: section 2', 'reference': 'DESCRIPTOR_SPECS 2 (F) + PREREG F 1',
                     'refs': (SourceRef of this file,)}
```

Bản declared dùng cùng các tên đó, với `aggregation` = `'declared_scalar'`, và lấy giá trị từ tham số `vN_char`, `d0` của
candidate.
