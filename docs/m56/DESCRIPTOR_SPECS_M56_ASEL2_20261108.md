# M56 A-SEL2: bộ mô tả phép so giữa các cảnh, declared và realized (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** A-SEL2 §1.5 và §4. Duy quyết "Claude soạn, trước A/B" và "Thêm LrefN cho C/L".

**Thời điểm:**
- Bản này được commit **trước** A/B đầu tiên của đợt A-SEL2. Batch `m56_asel2_cl_20261108T083410Z` khi đó mới đang chuẩn bị,
  chưa có A/B nào.
- Theo spec §2.3, định nghĩa realized (event, action nguồn, cách gộp) phải đóng băng trước validation. Với các cảnh mới, điều kiện
  này được thỏa.
- Với 10 cặp đã có A/B từ trước (C01, C05, C08, L01, L04, O01, O02, O03, I03, I04), các định nghĩa này là **đặt sau khi thấy
  số**. Mọi phép so realized có dính tới các cảnh đó phải ghi kèm điều kiện này.

## 1. Quy tắc chung

- Δ(a, b) = |a − b| / max(a, b), giá trị đúng trước mọi làm tròn hiển thị (spec §2.3). Một cặp đạt khi đủ số descriptor có
  Δ ≥ 0,20 theo bảng §2, cộng một review D09 bám đúng cặp đó.
- Không có epsilon. Giá trị bằng 0, thiếu, hoặc không hữu hạn thì không được đếm.
- **Realized:**
  - Mỗi giá trị được đo trên **cả hai** action A và B, tại cùng một event. Cả hai giá trị đều được công khai.
  - Cách gộp đóng băng là **trung bình cộng của A và B**. Không bao giờ chọn action có lợi hơn.
  - Thiếu event ở một action thì descriptor đó không đếm cho cảnh, và phép so liên quan là `BLOCKED_COMPARABILITY`.
- Nguồn của realized là raw đã seal của episode (`native/observation/*.json`, manifest). Không dùng giá trị lệnh hay giá trị
  khai báo.

## 2. Descriptor theo loại

| Loại | Declared (tham số của candidate) | Đạt khi | Realized (event; đại lượng) |
|---|---|---|---|
| C, L | vN (m/s), G (m), LrefN (m) | ≥ 2/3 có Δ ≥ 0,20 | vN_r: tốc độ NPC trung bình trên [t0 − 1 s, t0]. G_r: khoảng cách route từ mũi EGO tới biên E_ENTRY tại t0. LrefN_r: chiều dài arc của route NPC đã đóng băng trong connector |
| M | vN (m/s), G (m) | cả 2 có Δ ≥ 0,20 | vN_r, G_r như C |
| I | vE (m/s), gap (m; tên phụ `gap_m`) | cả 2 có Δ ≥ 0,20 | vE_r: tốc độ EGO trung bình trên [t0 − 1 s, t0]. gap_r: khoảng hở dọc giữa đuôi xe trước và mũi xe sau tại TRIGGER |
| O | vE (m/s), G (m; tên phụ `G_m`, `gap`) | cả 2 có Δ ≥ 0,20 | vE_r như I. G_r: khoảng hở dọc tới NPC tại t0 |
| F | soạn trong prereg F, trước A/B đầu tiên của F | | |

Ghi chú:
- t0 là event đã đóng băng của từng loại: C/L/M theo spec §7.3; I/O theo §7.4.
- **LrefN_r là đại lượng hình học của fixture, không phải đo động.** Nó được đọc từ route NPC đã đóng băng, giống nhau ở A và B.
  Theo A-SEL2 §4, G là hàm của LrefN và vN, nên khi báo cáo phải ghi rủi ro đếm trùng.
- vN, G ở realized có thể khác giá trị khai báo; lệch như thế nào được báo đúng như đo.

## 3. Bản ghi máy đọc được (PolicyBundle.descriptor_specs)

```text
{'by_category': {
  'C': {'vN': D('m/s','npc_speed'), 'G': D('m','ego_trigger_distance'), 'LrefN': D('m','npc_connector_length')},
  'L': (như C),
  'M': {'vN': D('m/s','npc_speed'), 'G': D('m','ego_trigger_distance')},
  'I': {'vE': D('m/s','ego_speed'), 'gap': D('m','trigger_gap', aliases=('gap_m',))},
  'O': {'vE': D('m/s','ego_speed'), 'G': D('m','follow_gap', aliases=('G_m',))}}}
D(unit, quantity) = {'unit', 'physical_quantity', 'aggregation': 'declared_scalar', 'source_actions': ('A','B'),
                     'event': <t0 / TRIGGER của loại>, 'window': <như §2>, 'reference': 'spec 2.3 + A-SEL2 4',
                     'refs': (SourceRef của tài liệu này,)}
```

- Bản realized dùng cùng các tên đó, với `aggregation` = `'mean_of_A_and_B'`.
- Hàm product cho phép so realized (`compare_realized`, m56-v10) phải kiểm:
  - mỗi giá trị theo action có SourceRef đã xác minh sha256;
  - product **tự tính** giá trị trung bình, không nhận giá trị gộp từ bên ngoài;
  - có review `REALIZED_COMPARABILITY_D09` bám đúng cặp.
- Hàm đó được viết sau bản này nhưng phải theo đúng định nghĩa ở đây.
