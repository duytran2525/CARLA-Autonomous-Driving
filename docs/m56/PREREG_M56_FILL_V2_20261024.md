# M56: đăng ký trước catalog fill v2 (lấp 15 chỗ, nhắm ≥ 23 junction) (24/10/2026)

**Trạng thái:** `DRAFT_AWAITING_DUY_APPROVAL`. Duy chọn "Bổ sung cảnh tới 46" với điều kiện "anh duyệt quy tắc trước khi
chạy". Vì vậy chưa chạy census nào theo file này. File được commit trước, rồi chờ Duy duyệt đúng commit này; nếu Duy sửa thì
ra commit mới, và census chạy trên commit đã duyệt.

**Người chọn:** Claude, theo thuật toán, **không độc lập**. Đã thấy kết quả 1b/M21, output fill20 (pool R2 = 0) và các số
native v2–v4. Mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`: independent review waived by Duy 2026-10-24.

**Bản chất:** mọi quy tắc đổi so với fill20 (`PREREG_M56_FILL20_20261022.md`, sha256 `4def064b…`) đều **đặt sau khi thấy
output fill20**. Mỗi thay đổi được đánh dấu là "sửa lỗi khách quan" hay "nới quy tắc", và kết quả được báo theo cả quy tắc
cũ lẫn quy tắc mới. Không có ngưỡng metric nào đổi.

## 1. Chỗ trống cần lấp (15)

| Loại | Đã có | Cần | ID mới |
|---|---|---|---|
| M | M01 | 7 | M02–M08 |
| I | I01–I05, I07 | 2 | I06, I08 |
| O | O01–O05, O07 | 2 | O06, O08 |
| F | F01, F04 | 4 | F02, F03, F05, F06 |

**Junction:** hiện có 17 (16 site C/L, cộng M01). C và L đã đủ 8 cảnh. Junction mới chỉ đến từ M, nên tối đa là 17 + 7 = 24.
Cổng §2.1 đòi ≥ 23 junction **đủ điều kiện**, tức là junction có cảnh giao hàng (delivery) được admit. Nghĩa là trong 24
junction chỉ được hỏng tối đa 1.

## 2. Đầu vào (đã khóa)

- **XODR:** cùng bốn file và cùng sha256 như fill20 §1.
- **Seed:** `SEED = int(sha256("M56-FILL-V2-PREREG-2026-10-24")[:16 hex], 16) = 17444868385921929488`.
- **Code:** `.superpowers/sdd/2026-10-07-m56-catalog-and-validation/fill-v2-generate.py`, commit cùng file này. Nó dùng lại các
  hàm của `fill20-generate.py` và chỉ thay F2-1 đến F2-4. Chỗ nào văn bản chưa nói rõ thì code ghi cách hiểu vào mục
  `resolutions` của output.
- **Loại trừ:** site của 31 cảnh trong C0 partial (17 junction, 8 nonjunction; theo `site-ledger-packet.json` của C0 v4),
  cùng vùng cấm 30 m quanh anchor của 17 junction đó.
- **M02–M04 cũ** đã bị loại khỏi catalog ngày 22/10. Junction của chúng **không** bị loại trừ: một chuẩn chung cho mọi M
  (spec §2.2). Chúng được xét lại như mọi junction khác, không được ưu tiên.

## 3. Thay đổi quy tắc

### F2-1. R2: heading ở đầu road vào (sửa lỗi khách quan)

| | Nội dung |
|---|---|
| Cũ (fill20) | heading của road vào lấy ở **cuối** road nếu `successor` của road là một junction bất kỳ |
| Mới | lấy ở đầu của road vào **chạm đúng junction J**: `successor elementId == J` thì lấy cuối, `predecessor elementId == J` thì lấy đầu |

Quy tắc cũ sai khi road có junction ở cả hai đầu và đi vào J từ đầu của nó: khi đó Δheading tính ra từ sai đầu road.

### F2-2. R2: góc branch (nới quy tắc)

| | Nội dung |
|---|---|
| Cũ | branch: 10° < \|Δheading\| ≤ 45°, hai chiều |
| Mới | branch: 10° < \|Δheading\| ≤ 45°, hai chiều; **hoặc** 45° < \|Δheading\| ≤ 100° chỉ với rẽ phải (Δheading < 0 theo quy ước XODR ngược chiều kim đồng hồ) |

**Giữ nguyên:**
- đúng một connection mainflow, \|Δ\| ≤ 10°, vào cùng lane đích T;
- hai road vào đều là road thường;
- không có đèn giao thông trên road vào trong 50 m trước J;
- proof `MERGE_TRANSITION` ở khâu chuẩn bị (branch connector nhập vào lane đích);
- độ dài fill20 §3.

**Lý do:**
- Spec §2.2 đòi proof hình học/topology branch→mainflow, và nói "shared outgoing lane is insufficient".
- Một lượt rẽ phải nhập vào làn đi thẳng ở junction không đèn là branch nhập vào mainflow; proof của nó là
  `MERGE_TRANSITION`.
- Rẽ trái bị loại vì cắt qua luồng ngược chiều, đó là cảnh L.
- Mức 45° của fill20 là lựa chọn của Claude, không có trong spec.

### F2-3. R1: corridor nối nhiều laneSection (nới quy tắc)

| | Nội dung |
|---|---|
| Cũ | một corridor là **một** laneSection |
| Mới | một corridor là một chuỗi tối đa các laneSection liên tiếp của cùng road, nối tiếp qua link road–road không qua junction |

**Điều kiện:**
- cặp lane liên tục: cùng id, hoặc nối qua `lane/link`;
- mọi điều kiện R1 đúng trên **từng** đoạn: broken mark, curvature ≤ 1/500, \|độ dốc\| ≤ 0,02, width ≥ 3,0;
- độ dài là tổng các đoạn.

**Lý do:** ranh giới laneSection là chi tiết soạn file XODR (chẳng hạn đổi bề rộng ở lane khác), không phải chỗ đứt vật
lý. **Site** của corridor là cả chuỗi, và cap 2 tính trên cả chuỗi.

### F2-4. R3 (F03): chiều đi (sửa lỗi khách quan)

| | Nội dung |
|---|---|
| Cũ | chiều xuống dốc |
| Mới | chiều **lên dốc** |

Lý do: cơ chế F03 cần NPC lăn ngược **về phía** ego. Với chiều xuống dốc thì NPC lăn ngược đi xa ego, đúng như lý do loại
F03 ngày 22/10.

### F2-5. Đơn vị tham số `k` (sửa lỗi khách quan)

Chỉ số `k` của I/O trong revision cũ có đơn vị không được hỗ trợ (candidates[23], phát hiện 23/10). Ở revision mới, `k` có
đơn vị `1` (không thứ nguyên). Giá trị không đổi.

## 4. Tham số (giữ nguyên chuỗi của fill20 §4)

| Loại | Chỉ số k | Tham số |
|---|---|---|
| I06 | 5 | vE = 6·(5/4)^4 = 14,6484375 m/s; vN = vE − 1; gap = 6·(13/10)^4 |
| I08 | 6 | vE = 6·(5/4)^5 = 18,310546875 m/s; vN = vE − 1; gap = 6·(13/10)^5 |
| O06 | 5 | vE = 6·(5/4)^4; vN = 2,5; G = 15·(13/10)^4 |
| O08 | 6 | vE = 6·(5/4)^5; vN = 2,5; G = 15·(13/10)^5 |

M và F lấy tham số theo công thức của fill20 §4. Chỉ số k của M:
- M02–M04 dùng lại chuỗi gốc k = 2, 3, 4 (các chỉ số này trống từ khi M02–M04 cũ bị loại);
- M05–M08 dùng k = 5, 0, 6, −1 như fill20 §4.

## 5. Gán tất định

1. **Thứ tự gán:** như fill20 §5, nhưng xáo bằng `Random(SEED + offset)`, offset I = 1, O = 2, M = 3, F = 4.
2. **I/O:** I06 và O06 ở chung một corridor, I08 và O08 ở chung một corridor khác.
3. **M:** mỗi junction là một site và chỉ có một M.
4. **Ràng buộc toàn catalog** (tính cả 31 cảnh hiện có):
   - ≤ 3 cảnh mỗi (loại, town);
   - mỗi site ≤ 2 lần;
   - ≥ 3 town.
5. **Không đủ ứng viên:** để trống và báo cáo; không nới thêm.

## 6. Báo cáo theo hai quy tắc

Census in ra kích thước pool theo bốn cách:

| Cách | Áp dụng |
|---|---|
| (a) | đúng code fill20 |
| (b) | fill20 với hai bản sửa lỗi khách quan (F2-1, F2-4) |
| (c) | (b) cộng F2-2 |
| (d) | (b) cộng F2-2 và F2-3, đây là quy tắc v2 dùng để gán |

Mỗi cảnh mới ghi quy tắc nào cho phép nó, chẳng hạn "M nhờ F2-2 (rẽ phải 78°)".

## 7. Sau census

Thứ tự các bước tiếp theo:
1. review danh tính site;
2. revision C0 mới (vẫn `C0_PARTIAL` cho tới khi đủ 46);
3. chuẩn bị native và A/B theo recipe v2–v5.

**Nhãn:** `selector = CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`. Mọi kết quả mang câu "independent review waived by Duy
2026-10-24".
