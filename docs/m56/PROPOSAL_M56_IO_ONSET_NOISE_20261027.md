# M56: đề xuất luật onset ngang chịu nhiễu cho I/O (27/10/2026), CHỜ DUY QUYẾT

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Nguồn gốc:** luật đề xuất được đặt **sau khi thấy** episode A của O03 v1.1. Đây là thay đổi luật consumer, nên theo nguyên tắc 6
Claude **không tự áp dụng**, kể cả dưới ủy quyền đêm. Mọi số liệu theo luật mới chỉ để tham khảo, cho tới khi Duy quyết.

## Vấn đề (đo trên episode đã seal `outputs/m56_io_ab_Town06_20261026T193247Z`, action A)

**Luật đóng băng, gồm hai phần:**
- **Đi ra** (`metrics._lateral_departure`): xét từ TRIGGER, frame **đầu tiên** có offset bản đồ thay đổi **bất kỳ** là frame quyết
  định.
  - Thay đổi lớn hơn 2u (u = 0,001 m) thì đó là onset.
  - Thay đổi trong khoảng 0 < Δ ≤ 2u thì kết luận `LANE_CHANGE_ONSET_UNCERTAIN`, dẫn tới `OUTBOUND_ONSET_UNPROVEN`.
- **Quay về** (`_o_return_action`): khi đã ở làn đích, mọi lần offset giảm ≤ 2u đều bị ghi `RETURN_LATERAL_START_UNCERTAIN`.

**Tín hiệu native thực tế:**
- Trước TRIGGER, offset ổn định ở 0,0001 m, mỗi frame dao động tối đa 0,04 mm (trung bình 0,02 mm). Dao động này không bao giờ
  đúng bằng 0.
- Frame TRIGGER có Δ = +0,01 mm, nên theo luật cũ kết quả là UNCERTAIN ngay lập tức.
- Chuyển động ngang thật bắt đầu ở frame +6 (0,09 mm), vượt 2u ở frame +12 (2,15 mm), và đạt offset đỉnh 3,468 m.

Luật này viết cho tín hiệu tổng hợp, vốn bằng hằng số tuyệt đối trước khi đổi làn. Với xe native, onset đi ra **không bao giờ**
chứng minh được.

## Đề xuất

Các thay đổi ≤ 2u được coi là nhiễu và bỏ qua, chứ không làm episode thành UNCERTAIN:
- onset là frame đầu tiên có |Δ| > 2u;
- điểm bắt đầu quay về là lần giảm đầu tiên > 2u.

Không đổi:
- ngưỡng 2u;
- các phép kiểm `OUTBOUND_BEFORE_DECISION` và `RETURN_STARTED_BEFORE_FIXED_MARKER`;
- các proof đường đi.

## Đánh giá offline theo cả hai luật (chỉ tham khảo)

`native-io-draft-onset-eval.py`: vá trong bộ nhớ, không đổi byte của consumer. Kết quả ghi trong `M56_IO_O03_RESULT_20261027.md`.

## Xin quyết

1. Duy duyệt hoặc bác luật trên, dưới dạng consumer v8 (erratum).
2. Nếu duyệt: đánh giá lại offline episode O03 v1.1 đã seal, không chạy CARLA, và báo theo cả hai luật (giống cách làm với v7 FIT).
