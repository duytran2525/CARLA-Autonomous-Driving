# M56 erratum C0: làn của C07 và C08 (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này (đã tự xưng Duy ngày 07/11/2026, trao toàn quyền) yêu cầu trong chat ngày 08/11/2026: "sửa
c07 và c08 đi". Claude quyết cách sửa dưới ủy quyền đó.

**Thời điểm:** commit trước mọi lần chuẩn bị và A/B của C07, C08 sau erratum. Hai cảnh chưa từng có A/B, nên với chính chúng
erratum này không phải là luật đặt sau khi thấy số. Erratum được đặt sau khi chẩn đoán map (`M56_CL_V1_RESULT_20261108.md` §3),
nhưng chẩn đoán đó không đo bất kỳ số nào của cảnh.

**Spec không đổi byte nào.** Notation sai nằm ở các dòng §6.3 của spec. Erratum được áp khi dựng revision C0 partial
(`native-v5-revision.py`, `C0_LANE_ERRATUM`), và ghi vào mỗi actor (`route_recipe.c0_erratum`) cùng environment của candidate
(`c0_erratum_lanes`).

## 1. Lỗi khách quan

Kiểu làn đọc từ OpenDRIVE đã pin (`E:/Carla/.../OpenDrive/Town06.xodr`):

| Cảnh | Actor | Notation catalog | Kiểu làn trong XODR |
|---|---|---|---|
| C07 | EGO | `13/-2→453/-2→14/-2` | cả ba là **Shoulder, rộng 0,5 m** |
| C08 | EGO | `55/+1→652/+1→54/+1` | cả ba là **Shoulder, rộng 0,5 m** |
| C08 | NPC | `50/-2→680/-2→51/-2` | cả ba là **Shoulder, rộng 0,5 m** |

Hệ quả: route v1 đóng băng của các actor này chạy dọc lề đường. Builder native không tìm được làn ra (`NO_OUTGOING`), nên cả hai
cảnh không chuẩn bị được.

Đã quét notation của cả 39 ứng viên trong revision cuối: chỉ có ba notation trên trỏ vào làn không phải Driving. NPC của C07
(`57/-1→545/-1→58/-1`) là Driving.

## 2. Luật sửa

Mỗi làn Shoulder được thay bằng **làn Driving đầu tiên cùng phía, đi ra xa đường tham chiếu**. Road, connector và junction giữ
nguyên.

| Cảnh | Actor | Sau erratum | Kiểm |
|---|---|---|---|
| C07 | EGO | `13/-3→453/-3→14/-3` | cả ba là Driving 3,5 m; junction 452 `13 -3 → 453 -3`; `453/-3 → 14/-3` |
| C08 | EGO | `55/+4→652/+4→54/+4` | cả ba là Driving 3,5 m; junction 582 `55 4 → 652 4`; `652/+4 → 54/+4` |
| C08 | NPC | `50/-3→680/-3→51/-3` | cả ba là Driving 3,5 m; junction 582 `50 -3 → 680 -3`; `680/-3 → 51/-3` |

Route v1 của EGO (response A/B) và destination được dựng lại từ notation đã sửa bằng chính `junction_recipe` của catalog. Tham số
(G, vE, vN, LrefN), site, weather và chương trình response không đổi. LrefN là chiều dài road connector, nên cũng không đổi.

## 3. Chạy

- Freeze một revision C0 partial có erratum, rồi chuẩn bị C07 và C08 (Town06) dưới recipe v6, product `m56-v9` `1db746f`, kèm luật
  cl-v1 (đã có trước). Luật v6 về NPC rẽ vẫn áp dụng.
- Mỗi cảnh PREPARED chạy đúng một A/B (P5), rồi tính pair dưới consumer v9 và v6. Báo cáo theo cả hai.
- Cảnh hỏng hay bị chặn ở bất kỳ bước nào thì ghi lại, không chỉnh thêm.

**Giới hạn phải ghi kèm kết quả:** C07 và C08 sau erratum là cảnh đã được Claude sửa (not independent). Selector gốc chọn
notation trên làn Shoulder; erratum chỉ dời sang làn xe kề bên, theo một luật máy móc.

## 4. Kết quả (08/11/2026)

Revision erratum `outputs/m56_c0_partial_io_c0e_20261108T012523Z`; chuẩn bị `outputs/m56_v2_prepare_Town06_20261108T012553Z`;
revision cuối `outputs/m56_c0_partial_io_clv1_20261108T013122Z`; log `outputs/m56_cl_v1_20261108T012552Z`. Product `1db746f`,
tooling `074fae3`.

| Cảnh | Chuẩn bị | A/B (một lần, P5) | Pair v9 | Pair v6 |
|---|---|---|---|---|
| C07 | BLOCKED_FIXTURE `NPC_SIGNAL_HOLD_IN_PROBE2` (route dựng được; NPC dừng đèn trong probe 2, luật v4) | — | — | — |
| C08 | PREPARED, T_r 7,3 s | `outputs/m56_v2_ab_Town06_20261108T013131Z`, FROZEN, ADMITTED | BLOCKED_WITNESS | BLOCKED_WITNESS |

C08, cả A và B: spawn CONFIRMED, physical UNKNOWN, witness INVALID; lý do `CONTACT_PROOF_INVALID`, `CONTINUOUS_FIT_UNPROVEN`.
Đây là cùng nhóm lỗi với C02 và M07. **Đính chính:** bản đầu của câu này ghi rằng mục b (vùng drivable gồm mặt đường) chưa được
duyệt. Điều đó sai: v6 b đã được duyệt và đã có trong code. Nguyên nhân thật của C08 là NPC chạy ra khỏi phạm vi dựng union (xem
`PREREG_M56_DRIVABLE_DV1_20261108.md` §1). Dưới dv1, C08 PASS (§4 của tài liệu đó). Pair: `outputs/m56_v6_pair_20261108T014116Z` (v9) và `..._014720Z` (v6).

Erratum làm hai cảnh chạy được tới bước chuẩn bị, nhưng không thêm cặp hợp lệ nào. Tổng vẫn 9 cặp. Theo prereg, không chỉnh thêm
và không chạy lại.
