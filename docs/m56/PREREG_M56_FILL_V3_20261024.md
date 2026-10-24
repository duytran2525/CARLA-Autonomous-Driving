# M56: đăng ký trước catalog fill v3 (7 chỗ còn trống) — BẢN NHÁP (24/10/2026)

**Trạng thái:** `DRAFT_AWAITING_DUY_APPROVAL`.

- Duy yêu cầu: "soạn bản nháp đăng ký trước fill v3 cho I06, I08, O06, O08, M07, F05, F06; ghi rõ mọi bước nới quy tắc là
  đặt sau khi thấy số; anh duyệt trước khi chạy".
- Chưa chạy census nào theo file này. Code chỉ được kiểm bằng XODR tổng hợp (`fill-v3-selfcheck.py`), không chạy trên
  bản đồ thật.
- Census chạy trên đúng commit được Duy duyệt.

**Người chọn:** Claude, theo thuật toán, **không độc lập**. Independent review waived by Duy 2026-10-24
(`CLAUDE_REVIEW_UNDER_DUY_DELEGATION`).

## 0. Mọi thay đổi ở đây đều đặt SAU KHI THẤY SỐ

Claude đã thấy những số sau trước khi viết file này:

**Output fill v2:** `outputs/m56_fill_v2_20261024T152517Z.json`, sha256 `46bc88b7…`; 8/15 chỗ được lấp.

**Chẩn đoán chỗ trống** (chạy lại các hàm của fill v2, không gán gì):

| Chỗ | Số đã thấy |
|---|---|
| I/O 06, 08 | Corridor R1 dài nhất theo town: Town04 113 m, Town05 64 m, Town06 184 m, Town07 không có. Town06 đã đủ trần I và O (3). Độ dài cần là 215–322 m (k = 5, 6). |
| M07 | k = 6 cần road vào nhánh ≥ 62,8 m và road vào mainflow ≥ 40,2 m. Hai ứng viên đạt độ dài là J1197 và J1593, đều ở Town04, nơi M đã đủ trần. Ở các town còn lại, ứng viên dài nhất có nhánh 51,6 m. |
| F05, F06 | Không còn corridor tự do ≥ 120 m ở Town04/05/07; Town06 đã đủ trần F. |

**Probe PID native**, mức 4,8–11,7 m/s, dẫn tới erratum 2 (PID EGO).

Vì vậy mỗi thay đổi dưới đây đều mang nhãn "đặt sau khi thấy số", và kết quả được báo theo cả quy tắc v2 lẫn v3.

## 1. Giữ nguyên

- XODR và hash như fill20/v2.
- Mọi điều kiện R1 trên các laneSection thường; R2 cùng F2-1, F2-2; độ dài fill20 §3.
- Công thức tham số và chuỗi k.
- Trần ≤ 3 cho mỗi (loại, town), cap 2 cho mỗi site, ≥ 3 town.
- **8 cảnh của fill v2 giữ cố định** và bị loại trừ như 31 cảnh C0. Vùng cấm 30 m mở rộng thêm quanh 6 junction M mới.
- **Seed:** `int(sha256("M56-FILL-V3-PREREG-2026-10-24")[:16 hex], 16)`.
- **Code:** `fill-v3-generate.py`, commit cùng file này. Code dùng lại `fill-v2-generate.py`, và kiểm sha256 của output v2
  trước khi chạy.

## 2. Thay đổi

### F3-0. Điều kiện khả thi cho I/O (siết)

Corridor của một cặp I/O phải chứa một đoạn thẳng, nằm ngoài junction, có độ dài ≥ 3·vE (I) và ≥ returnstart + 3·vE (O).
Trên đoạn đó, mọi heading lệch ≤ 1° so với một trục thế giới, và tổng biến thiên ≤ 1°.

- **Lý do:** erratum 1 của v5 (22c5cd4) chỉ nhận đổi làn trên đoạn thẳng song song trục. Điều kiện này đã có trước mọi
  số I/O; ở đây nó chỉ được đưa sớm lên bước census.
- **Hệ quả:** điều kiện này làm pool **nhỏ đi**.

### F3-1. Corridor đi thẳng xuyên junction (nới)

| | Nội dung |
|---|---|
| Cũ (v2) | chuỗi dừng ở junction |
| Mới | chuỗi được đi tiếp qua một junction khi thỏa **mọi** điều kiện bên dưới |

**Điều kiện:**
- có đúng một connection, từ road hiện tại, ánh xạ cả hai làn của corridor;
- connecting road thỏa hình học, độ dốc và bề rộng của R1;
- heading đổi ≤ 2° từ lối ra road hiện tại tới lối vào road kế tiếp;
- không có đèn giao thông trong 50 m trước junction;
- junction không thuộc catalog hoặc vùng cấm 30 m;
- road kế tiếp là road thường.

**Vạch broken:** không đòi trong junction. Đoạn đổi làn vẫn phải nằm trên phần không phải junction, theo F3-0.

**Danh tính site:** site là cả chuỗi. Các junction bị đi qua được ghi lại, không được tính là junction của catalog, và bị
loại khỏi các lần gán sau.

### F3-2. Chỉ số k dự phòng (nới)

Khi chỉ số k đã đăng ký không có ứng viên, thử lần lượt các chỉ số kế tiếp theo thứ tự cố định, bỏ qua chỉ số đã dùng:

| Chỗ | k đăng ký | Dự phòng, theo thứ tự |
|---|---|---|
| I/O 06 | 5 | −2, 7, −3, 8, −4 |
| I/O 08 | 6 | −2, 7, −3, 8, −4 |
| M07 | 6 | 7, −2, 8, −3, 9 |

- I và O dùng chung một k (cùng site). Bỏ k nào cho vE ≤ 3, vì returnstart của O khi đó vô hạn.
- **Tính đa dạng:** các k khác nhau cho vE (hoặc vN) cách nhau ít nhất 5/4 lần, và gap/G/GL cách nhau 13/10 lần. Vì vậy
  Delta ≥ 1/5 tính đúng bằng phân số, không làm tròn. Phép so 155 vẫn được kiểm riêng ở bước audit.

### F05, F06

Không có quy tắc riêng. Chúng chỉ hưởng F3-1, với độ dài 120 m như cũ.

## 3. Thứ tự gán

1. I06/O06, rồi I08/O08: chọn corridor đầu tiên trong pool R1 v3 đã xáo bằng `Random(SEED + 1)`.
2. M07: chọn trong pool R2 còn lại, xáo bằng `Random(SEED + 3)`.
3. F05, rồi F06: xáo bằng `Random(SEED + 4)`.
4. Chỗ nào không có ứng viên thì để trống. Không nới thêm.

## 4. Báo cáo

**Kích thước pool:**
- R1 theo quy tắc v2;
- R1 theo quy tắc v3, và số corridor có đi qua junction;
- độ dài lớn nhất, và đoạn thẳng-theo-trục lớn nhất;
- R2 còn lại.

**Mỗi cảnh** ghi các k đã thử, quy tắc nào cho phép nó, và độ dài cần.

**Theo quy tắc v2:** cả 7 chỗ này đều trống.

## 5. Rủi ro đã biết (chưa giải quyết bằng file này)

- **PID của EGO:** vE lớn (k = 7 cho 22,9 m/s) chưa được probe. Erratum 2 xử lý nếu PID gốc không ổn định.
- **Tooling chuẩn bị I/O chưa tồn tại.** Mọi cảnh I/O, cũ và mới, đều còn chờ khâu này.
- **Release §11:** dù cả 7 chỗ được lấp, release vẫn cần mọi cảnh giao hàng được và đủ 23 junction đủ điều kiện. M01, C07,
  C08, F04 và F01 hiện còn bị chặn.
