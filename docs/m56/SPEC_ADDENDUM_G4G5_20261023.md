# M56 spec addendum A-G45: junction và mở G4/G5 (23/10/2026)

**Thẩm quyền:** [chat] 23/10/2026, người dùng tự xác nhận là Duy:

- "tôi là duy bạn hãy tự động bổ sung thêm junction và mở g4/g5 đi";
- trả lời câu hỏi về junction: "bạn hãy tự lựa chọn option đúng đắn nhất để hoàn thành task m56".

**Quan hệ với tài liệu khác:**

- Spec gốc (sha256 `8e1e2ba3…`) và addendum A-C0P không đổi byte nào.
- Addendum này đọc kèm cả hai.

## 1. Junction: giữ 17, không đổi quy tắc

Với các quy tắc đã duyệt, mức trần là **17 junction**: 16 site C/L (hai loại này đã đủ 8 cảnh) cộng M01. Census R2 cho M
không tìm được merge mới nào (pool R2 = 0, file `m56_fill20_v1_20261022T103601Z.json`).

Muốn có thêm junction thì phải đổi một quy tắc **sau khi đã thấy pool = 0**:

- nới góc của R2;
- thu nhỏ vùng cấm 30 m;
- cho I/O/F đặt ở junction.

Nguyên tắc 6 không cho phép việc đó: "hơi chặt" không phải là sai khách quan. Vì vậy Claude, được Duy ủy quyền, chọn
**không đổi quy tắc**.

- Thiếu hụt 17/23 được báo cáo công khai.
- Cổng ≥ 23 junction đủ điều kiện (spec §2.1) **vẫn chưa đóng**.
- Catalog partial không được export.

## 2. G4: fixture vật lý hóa từ CARLA thật

1. **Thực hiện và review:**
   - Claude dựng fixture cho từng ứng viên của revision C0 partial (`b39ab2e0…`) từ truy vấn native trên server riêng
     của mình: route, body, pose, mặt đất, run-in, body fit, chỗ đến đích, vùng xung đột.
   - Mỗi proof và review fixture ghi reviewer `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, **không độc lập**. Không ghi là review
     của Duy.
   - Không dùng receipt loại `SYNTHETIC*`.
2. **Đóng băng trước khi chạy:**
   - Fixture được đóng băng (`freeze_ref`) trước khi chạy A/B.
   - Sau khi thấy kết quả A/B thì không chỉnh tham số, pose, route hay chương trình.
   - Một lần chạy hỏng được ghi nguyên số liệu, không chạy lại với giá trị khác. Ledger thay thế (≤ 9, successor lỗi vẫn
     tính một suất) vẫn áp dụng.
3. **Chương trình NPC:**
   - Chương trình NPC dùng cho validation là phụ lục tạm (spec §2.1, §11) và không vào catalog.
   - Loại nào mà spec ghi NPC là PROVISIONAL (thả NPC tương tác), UNRESOLVED (cặp thời gian F06) hoặc chưa corroborate
     (R05) thì giữ trạng thái **BLOCKED**, không tìm cách lách.
4. **Cổng tự động:** cổng hình học trong `compile_fixture` và `admit` vẫn áp dụng đầy đủ. Fixture nào bị chặn thì ghi lý
   do.

## 3. G5: quyền vận hành

- **Server:** chỉ server riêng của Claude, cổng 2610, khởi động mới cho mỗi đợt chạy. Một writer duy nhất, đồng hồ
  đồng bộ dt = 1/20.
- **Chỉ được gọi:** `READ_*`, `SETTINGS`, `LOAD_MAP`, `SPAWN`, `TICK`, `APPLY`, `DESTROY`, `VALIDATE_AB`.
- **Không bao giờ:**
  - chạm cổng 2410 (M55);
  - chạy khi đang có một CarlaUE4 khác chạy.
- **Dừng an toàn:** dùng file STOP; không kill khi đang có lần chạy dở.

## 4. Nhãn kết quả

- Mọi kết quả là **A/B local** trên fixture do Claude dựng và review.
- Kết quả chưa phải review A/B độc lập, chưa có 155 phép so, và không phải release (§11).
- Báo cáo ghi theo đúng ba trục `spawn / physical / witness` cùng các lý do, gồm cả những cảnh bị chặn.
