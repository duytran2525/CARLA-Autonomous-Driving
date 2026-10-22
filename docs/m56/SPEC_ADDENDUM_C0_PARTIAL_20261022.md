# M56 spec addendum A-C0P — partial C0 (22/10/2026)

**Thẩm quyền:** [chat] 22/10/2026, người dùng tự xác nhận là Duy: "Duyệt đóng băng C0 partial 31/46: cho phép version spec
mới chấp nhận honest partial count, ghi công khai, và tôi duyệt review C0."

**Quan hệ với spec gốc:** spec `2026-10-07-m56-catalog-and-validation-design.md` (sha256 `8e1e2ba3…`) **không đổi byte nào**.
Addendum này là version mới, đọc kèm spec. Nó mở rộng §11 ("Failure delivers honest partial counts/IDs/reasons/raw, not
synthetic final catalog") sang bước C0.

## 1. Quy tắc

1. **C0 partial:** một revision có ít hơn 46 ứng viên được đóng băng thành C0 partial **chỉ khi** đủ cả ba điều kiện:
   - deficit xây dựng duy nhất còn lại là số lượng (`CANDIDATE_COUNT`);
   - không loại nào vượt target (C/I/L/M/O ≤ 8, F ≤ 6);
   - có review C0 của Duy bind đúng revision và ledger site.

   Mọi cổng khác vẫn chặn như spec gốc: town (Town04–07, ≥ 3 town), ≤ 3 cảnh/(loại, town), danh tính site và cap 2,
   proof M, recipe đầy đủ.
2. **Nhãn:** receipt C0 mang `kind = C0_PARTIAL`. Mọi báo cáo phải ghi số thật (31/46) và lý do của từng chỗ thiếu.
3. **Validation:** C0 partial cho phép bước validation (A/B) trên đúng các ứng viên đã đóng băng. Điều này không cấp quyền
   runtime: G4/G5 vẫn là cổng riêng.
4. **Release/export không đổi:** §11 vẫn đòi đủ 46 entry, ≥ 23 junction đủ điều kiện và 155 phép so. Một catalog partial
   **không bao giờ** được export thành catalog cuối.
5. **Thay thế ứng viên:** C0 partial không mở chỗ trống cho việc tự chọn thêm. Thêm ứng viên sau C0 cần một quyết định
   mới, công khai.

## 2. Revision được đóng băng theo addendum này

31 ứng viên trên 25 site vật lý, trong đó 17 junction. Chỗ thiếu và lý do:

| Chỗ thiếu | Lý do |
|---|---|
| I06, I08, O06, O08 | không có laneSection đủ dài theo quy tắc đăng ký trước (dd2954c) |
| M05–M08 | không có merge branch→mainflow mới (R2) |
| M02–M04 | loại khi áp chuẩn R2 cho mọi M (Duy 22/10) |
| F02 | trùng mặt đường với I05/O05 (cap 2) |
| F03 | làn đi xuống dốc nên NPC lăn ngược sẽ đi xa ego |
| F05, F06 | không còn road dài chưa dùng trong cap town |

Người chọn 20 chỗ mới là Claude theo thuật toán đăng ký trước, **không độc lập**. Review danh tính site, recipe và M là
review của Claude dưới ủy quyền của Duy. Review C0 là của Duy.
