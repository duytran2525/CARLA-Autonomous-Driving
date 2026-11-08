# M56 fill v4 (A-SEL2): đăng ký trước thuật toán chọn cảnh cho 36 slot (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.
Selector: `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`.

**Thẩm quyền:** spec addendum A-SEL2 (`SPEC_ADDENDUM_SELECTION_EXPANSION_20261108.md`, `9fa85f8`, §4 `3f63959`), do Duy quyết
ngày 08/11/2026 ([chat]).

**Thời điểm và giới hạn:**
- Bản này được commit **trước khi** chạy bộ sinh `fill-v4-generate.py`.
- Trước bản này đã có một census offline (`asel2-census.py`, `asel2-ladder3b.py`), chỉ đếm pool và kiểm tính khả thi của thang
  tham số. Census không gán cảnh nào và không đo số nào của cảnh.
- Các quy tắc site dưới đây (đèn, dốc, chiều dài chạy đà) được viết **sau khi đã thấy** các lỗi C06, C07 (đèn ở giao lộ
  trước), M01 (đèn), M02 (dốc) và C06/L05/M01 (thiếu chỗ chạy đà). Đây là luật chọn cảnh có thông tin từ lỗi đã quan sát; nó
  không phải ngưỡng đo.
- Claude không chọn tay ứng viên nào.

## 1. Đầu vào

- **Town và hash:** đúng bảng §1 của A-SEL2 (11 town, không có Town03).
- **Giữ lại** 10 cảnh có cặp hợp lệ: C01, C05, C08, L01, L04, O01, O02, O03, I03, I04. Chúng tính vào cap (loại, town), cap
  site và thang tham số.
- **Slot cần lấp (36):**
  - C02, C03, C04, C06, C07;
  - L02, L03, L05, L06, L07, L08;
  - M01–M08;
  - I01, I02, I05, I06, I07, I08;
  - O04, O05, O06, O07, O08;
  - F01–F06. F nằm trong prereg F riêng, bộ sinh này không chọn F.
- **Loại trừ:** mọi junction và road của 39 ứng viên trong revision C0 mới nhất
  (`m56_c0_partial_io_audit_20261108T032727Z`), cùng vùng 30 m quanh anchor của các junction đó (quy ước fill v2).
- **Seed:** `SEED = int(sha256("M56-FILL-V4-ASEL2-2026-11-08")[:16 hex], 16)`.

## 2. Tham số của slot (giữ như đã đăng ký; không chỉnh theo site)

- **C:** k = số slot (C02 → k = 2, …); vE = 4; vN = 3·(5/4)^(k−1); LrefN = `road/@length` của connector NPC;
  G = `derive_g(vE, vN, LrefN)` của product.
- **L:** như C, nhưng vE = 2.
- **M:**
  - k theo chuỗi đã đăng ký: M01 1, M02 2, M03 3, M04 4, M05 5, M06 0, M07 6, M08 −1;
  - vE (mainflow) = 4; vN = 3·(5/4)^(k−1);
  - LrefN = connector của branch; G = `derive_g`.
  - Với M05–M08, cách tính này thay chuỗi GL của fill20. Lý do là mọi M dùng chung một công thức §6.2. Đây là đổi tham số của
    slot trống/hỏng, có ghi công khai.
- **I:**
  - k: I01 1, I02 2, I05 0, I06 −2 (fill v3), I07 −1, I08 6 (fill v2);
  - vE = 6·(5/4)^(k−1); vN = vE − 1; gap = 6·(13/10)^(k−1).
- **O:**
  - k: O04 4, O05 0, O06 −2, O07 −1, O08 6;
  - vE như I; vN = 2,5; G = 15·(13/10)^(k−1); returnstart theo §7.4.

## 3. Ứng viên site (tính tất định từ XODR)

**C và L** (quy tắc của `asel2-census.py`, đã kiểm trên 14 dòng C/L của spec §6.3 tìm thấy trên map):
- Một connection là: road/lane vào → connector/lane → road/lane ra; Δheading theo fill v2 `heading_change_fixed`, dương là rẽ trái.
- **C:** EGO và NPC đều đi thẳng (|Δh| ≤ 10°), từ hai road vào khác nhau, với hướng vào lệch nhau 60–120° (hoặc 240–300°).
- **L:** EGO rẽ trái (60° ≤ Δh ≤ 120°); NPC đi thẳng từ hướng ngược lại (hướng vào lệch 150–210°).
- Hai tâm làn của connector cắt nhau trên mặt bằng, và chênh cao tại giao điểm ≤ 2 m.

**M:** `merges_v2(town, wide=True)` của fill v2 (R2 + F2-1 + F2-2). EGO là mainflow, NPC là branch.

**Quy tắc chạy đà (C, L, M; mới trong v4):**
- Gọi đoạn chạy đà của một vai là đoạn dài `need` m ngay trước junction, trên road vào của vai đó:
  - EGO: need = G + vE²/3 + 20 (đúng mức `junction_recipe` đòi);
  - NPC: need = 150 m (đúng approach của probe 1).
- Road vào phải dài ≥ need, để cả đoạn chạy đà nằm trên một road, không qua junction nào khác.
- Trên đoạn chạy đà:
  - không có `signal` dynamic nào;
  - |độ dốc dọc| ≤ 0,02, lấy mẫu mỗi 1 m;
  - mọi đoạn `planView` là `line` hoặc `arc` có |curvature| ≤ 1/50 m⁻¹.
- Không có đèn dynamic trong 50 m trước junction xung đột, trên cả hai road vào (fill v2 `signal_near_fixed`).

**I và O:** pool R1 của fill v3 (`chains_v3`, kèm `axis_run` F3-0), trên 11 town. Độ dài cần theo fill20/fill v3:
`need_i`, `need_o`, và `need_axis` = max(3vE, returnstart + 3vE). Lane, road và hướng đi giữ quy ước fill v3.

## 4. Thang so sánh (A-SEL2 §1.5 và §4)

Một ứng viên chỉ được nhận vào slot nếu phép so khai báo với **mọi** cảnh đang giữ cùng loại (10 cảnh giữ lại, cộng các cảnh
đã gán trước nó trong lượt này) đều đạt:

| Loại | Điều kiện đạt |
|---|---|
| C, L | ≥ 2 trong (vN, G, LrefN) có Δ ≥ 0,20 |
| M | vN và G đều có Δ ≥ 0,20 |
| I | vE và gap đều có Δ ≥ 0,20 (đúng theo chuỗi khi các k khác nhau) |
| O | vE và G đều có Δ ≥ 0,20 (đúng theo chuỗi khi các k khác nhau) |

Δ là `delta` của product: |a−b|/max(a, b).

## 5. Gán

1. Mỗi loại một pool, sắp theo khóa ổn định (town, junction/road, connector, lane, hướng), rồi xáo bằng
   `Random(SEED + offset)`. Offset: C 11, L 12, M 13, I 14, O 15.
2. Slot được gán lần lượt theo id tăng dần trong từng loại, thứ tự loại C, L, M, I, O. Mỗi slot lấy ứng viên **đầu tiên** trong
   thứ tự đã xáo thỏa đồng thời các điều kiện sau:
   - junction chưa dùng (C, L, M dùng chung một tập junction, để mỗi junction tính một lần cho cổng 23);
   - road chưa vượt cap 2 site;
   - cap ≤ 3 cho (loại, town);
   - đủ độ dài theo §3;
   - đạt thang §4.
3. Không có ứng viên nào thì slot ghi `EMPTY_NO_ELIGIBLE_CANDIDATE`.
4. **Hàng thay thế:**
   - Với mỗi slot, bộ sinh ghi thêm 30 ứng viên kế tiếp thỏa §3 theo đúng thứ tự xáo.
   - Khi một cảnh hỏng (sau đúng một A/B, hoặc bị chặn ở bước chuẩn bị), slot của nó lấy ứng viên đầu tiên trong hàng còn thỏa
     §4–§5 với tập cảnh đang giữ lúc đó.
   - Mỗi lần admit tiêu 1 lượt của trần 150 (A-SEL2 §1.2). Hết hàng thì slot báo `QUEUE_EXHAUSTED`.

## 6. Tooling đóng băng cho cả đợt

Commit tooling ghi ở output của bộ sinh; product `m56-v9` `1db746f`, rồi `m56-v10` khi có. Biến môi trường:

| Phạm vi | Biến |
|---|---|
| Mọi lượt | `M56_NO_RENDER=1`, `M56_RECIPE=v6`, `M56_SPECTATOR=1` |
| C/L/M chuẩn bị | `M56_SIG5=1` (cl-v1 luôn bật trong code) |
| C/L/M A/B | `M56_DRIVABLE=dv1` |
| I/O | `M56_IO_BOX_ANCHOR=midpoint`, `M56_IO_KAPPA=pointwise`; không có site shift |

- Trong đợt **không thêm erratum** cho từng lỗi.
- Lỗi harness chỉ được xử lý theo spec §4: version kỹ thuật, giữ raw, không chạy lại tự động.
- Lỗi của cảnh thì ghi lại, rồi slot lấy cảnh thay từ hàng.

## 7. Output

`outputs/m56_fill_v4_<stamp>.json`, ghi kiểu create-exclusive. Nội dung:
- seed, sha256 của prereg này, hash các XODR, kích thước pool;
- với mỗi slot: ứng viên được gán và hàng thay thế, với đủ trường để dựng candidate (notation road/lane→connector/lane→road/lane
  cho C/L/M; road/section/lanes/travel cho I/O), tham số và lý do loại cho từng ứng viên bị bỏ qua (đếm).

## Addendum A (08/11/2026): first-fit có nhìn trước

**Thời điểm:** viết sau lần chạy đầu của bộ sinh, commit `90c1be5`. Output `outputs/m56_fill_v4_20261108.json` (sha256
`3c750762…`) được giữ nguyên. Lần chạy đó lấp 28/30 slot; M05 và M07 rỗng. Chưa có cảnh nào được chuẩn bị hay chạy A/B, nên
đây là đổi thuật toán chọn sau khi thấy output chọn. Nó không phải luật đặt sau khi thấy số đo.

**Lý do (khách quan):**
- First-fit tham lam ở §5.2 cho 6 slot M đầu lấy các giá trị G 14 / 18 / 22,5 / 28,5 / 36 / 48 m, mỗi bước cách nhau 1,25–1,33
  lần. Không còn khe nào cho M05 (k = 5) và M07 (k = 6): lý do loại là `LADDER` (191 lần) và `TOWN_CAP`.
- Census `asel2-census.py` đã chứng minh có cách gán cả 8 slot M. Vậy chỗ trống đến từ thứ tự tham lam, không phải từ nguồn site.

**Luật mới cho §5.2:**
- Mỗi slot vẫn duyệt ứng viên theo đúng thứ tự xáo.
- Một ứng viên chỉ được nhận nếu, sau khi nhận nó, **các slot còn lại của cùng loại vẫn còn ít nhất một cách gán**. Cách gán đó
  phải thỏa §3–§5: junction hoặc road chưa dùng, cap (loại, town), độ dài, và thang §4. Việc kiểm do một phép tìm vét cạn tất
  định thực hiện.
- Nếu không ứng viên nào giữ được tính khả thi cho các slot còn lại, slot lấy ứng viên first-fit cũ như §5.2. Các slot sau có
  thể rỗng.
- Hàng thay thế (§5.4) dùng cùng luật này với tập cảnh đang giữ lúc thay.

Mọi điều khác của prereg giữ nguyên.

## Addendum B (08/11/2026): thủ tục thay cảnh và hai cổng tĩnh

**Thời điểm:** sau lượt thí điểm Town11 (`M56_ASEL2_BATCH_LOG_20261108.md`). M04-S1 và M07-S1 bị chặn ở bước chuẩn bị với
`NPC_TURN_BEFORE_EXIT`, đây là luật v6 d đã đóng băng. Cũng lúc đó, trình dựng revision loại I02-S1 và O08 với
`WINDOW_TOO_SHORT`: `io_recipe` chỉ dựng trên một road. Chưa có A/B nào. Không chỉnh tham số nào của cảnh nào.

**B1, cổng cua của NPC (tính offline, cùng ngưỡng với v6 d):**
- Một ứng viên C/L/M bị bỏ qua khi `vN² · κmax` của connector NPC lớn hơn 2,25 m/s². κmax là |curvature| lớn nhất trong các bản
  ghi `arc` của connector đó.
- Áp cho 19 pick C/L/M hiện có, cổng này đúng bằng kết quả: chỉ M04 (4,09) và M07 (10,11) vượt.
- B1 chỉ là áp sớm luật v6 d để không tiêu lượt thay cho cảnh chắc chắn hỏng. v6 d ở bước chuẩn bị vẫn giữ nguyên.

**B2, trình dựng recipe:**
- Một ứng viên I/O bị bỏ qua khi cửa sổ cần (`vE²/3 + 20 + x_rel + 15` m, theo đúng `io_recipe`) dài hơn laneSection của road
  site.
- Ứng viên bị B1 hoặc B2 bỏ qua chưa được admit, nên không tiêu lượt (spec §4: proposal chưa admit thì chỉ ghi lại, không trial).

**B3, thay cảnh:**
- Slot có cảnh hỏng (đã trial) lấy successor kế tiếp: duyệt theo đúng thứ tự xáo của pool, với luật nhìn trước của addendum A,
  với tập cảnh đang giữ lúc đó, và loại trừ mọi site đã từng gán.
- Successor thứ n của một slot có id `M56-P-<slot>-S<n+1>`.
- Mỗi successor được admit tiêu 1 lượt của trần 150. Ghi vào `outputs/m56_asel2_replacements.jsonl`, chỉ nối thêm.
- Slot mà ứng viên ban đầu bị B2 loại thì lấy ứng viên kế tiếp theo cùng luật, không tiêu lượt.

## Addendum C (08/11/2026): M04 và M07

**Thời điểm:** commit trước khi có bất kỳ kết quả chuẩn bị hay A/B nào của các cảnh M ở Town12/13 (M05, M06, M08 ở Town12;
M01, M02, M03 ở Town13). Thay cảnh lần 1 (`outputs/m56_fill_v4_replace1_20261108.json`) cho thấy M04 và M07 không còn ứng viên:
- cổng cua B1 loại khoảng 490/586 site M;
- các site còn lại đều ở Town12/13, nơi trần (M, town) đã đủ 3.

**Luật:**
1. Không bao giờ dời một cảnh **đã trial** (đã chuẩn bị hay đã A/B) sang site khác để nhường trần cho slot khác. Tập cảnh đang
   giữ chỉ đổi khi có cảnh hỏng, theo B3.
2. M04 và M07 được ghi là `EMPTY_CAP_AND_B1`. Mỗi khi một cảnh M ở một town hỏng (theo B3) làm trống một suất (M, town), thì
   **trước khi** thay chính slot đó, bộ sinh chạy B3 cho M04 rồi M07, theo thứ tự đó, với tập cảnh đang giữ lúc ấy. Slot hỏng
   lấy successor sau cùng, nếu còn.
3. M04-S1 và M07-S1 (Town11, `BLOCKED_FIXTURE NPC_TURN_BEFORE_EXIT`) là cảnh đã trial và hỏng. Chúng không bao giờ được tính vào
   số đếm, catalog hay release. Trình dựng revision đánh dấu chúng `FAILED_TRIALED` (`M56_ASEL2_FAILED`).

Hệ quả phải báo: nếu không cảnh M nào ở Town12/13 hỏng thì loại M chỉ có 6 cảnh, nên không đạt 46 và tối đa 22 junction.

## Addendum D (08/11/2026): cổng dốc tại điểm xuất phát (B4)

**Thời điểm:** trong batch `m56_asel2_cl_20261108T083410Z`, trước bất kỳ A/B nào của đợt.
- Kiểm pitch ở frame đầu probe 2 của các cảnh PREPARED: C04-S1 có EGO 0,697°, M05-S1 có EGO −0,971°. Product đòi |pitch| ≤ 0,1°
  tuyệt đối ở frame quan sát đầu tiên (`m56/evidence.py` `_initial_state_matches`). Hai cảnh này vì vậy sẽ hỏng
  `INITIALIZATION_INVALID` ở A/B, đúng như M02 gốc.
- C06-S1 và M02-S1 cần pitch NPC khoảng 1° (cl-v1 a), nên cũng sẽ hỏng như vậy.
- Nguyên nhân: luật chạy đà ở §3 cho |độ dốc| ≤ 0,02 (khoảng 1,15°), lỏng hơn cổng 0,1° của product. Lỗi nằm ở luật chọn của
  Claude, không phải ở ngưỡng đo.

**B4 (áp cho mọi successor từ nay):**
- |độ dốc dọc| ≤ 0,0015 (khoảng 0,086°, dưới 0,1° với biên nhỏ), lấy mẫu mỗi 1 m:
  - EGO: tại 10 m đầu của đoạn chạy đà (quanh điểm spawn);
  - NPC: trên **toàn bộ** 150 m chạy đà, vì điểm xuất phát sau phasing có thể nằm ở bất kỳ đâu trong đó.
- Thêm điều kiện: road không có `superelevation` nào khác 0 trên các đoạn đó, để roll cũng ≤ 0,1°.
- B4 là luật chọn, đặt sau khi thấy lỗi dự đoán được. Nó không đổi ngưỡng 0,1° của product. Ứng viên bị B4 loại thì chưa admit,
  nên không tiêu lượt.

**Hệ quả với các cảnh hiện có:**
- C06-S1 và M02-S1 được xếp là hỏng: chúng đã trial ở bước chuẩn bị, và không có luật nào cứu được mà vẫn qua cổng 0,1°.
  Sửa kỹ thuật 2 không áp cho chúng.
- C04-S1 và M05-S1 vẫn chạy A/B như batch đã định, và kết quả được ghi đúng như đo.
