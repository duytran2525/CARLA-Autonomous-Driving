# M56: đăng ký trước runtime-recipe v4 (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, người dùng tự xác nhận là Duy:

- mục tiêu 1 tuần: chọn "Partial native";
- gói `PROPOSAL_M56_V4_BUNDLE_20261024.md`: duyệt **P1, P2, P3, P5**; P4 giữ BLOCKED; P6 là tooling.

**Thứ tự:** file này được commit trước mọi lần chạy dùng nó.

**Quan hệ với các tài liệu trước:** v4 kế thừa nguyên v2 (E1–E6), signal-phase v1 (erratum 1–4) và v3 (V3.1–V3.4).

**Báo cáo:** mọi thay đổi ở đây đều **đặt sau khi đã thấy số**. Kết quả báo theo cả quy tắc cũ lẫn quy tắc mới. Không có
ngưỡng metric nào đổi: Delta 0,20, D09, contact 0,20/0,15/0,05, readiness 0,10/0,50 s, horizon 60/76,5 s.

**Reviewer:** mọi review là `CLAUDE_REVIEW_UNDER_DUY_DELEGATION`, không độc lập. Kết quả là A/B local, không phải release.

## P1. Mức ổn định của NPC (C/L)

**Probe 1:**
- `v_N` = tốc độ trung bình của NPC trong **cửa sổ 2 s muộn nhất** của probe 1 thỏa đồng thời:
  - NPC không bị giữ đèn trong cửa sổ;
  - biên độ tốc độ ≤ 0,10 m/s;
  - cửa sổ kết thúc không muộn hơn khung cuối của probe.
- Không có cửa sổ như vậy → `READINESS_NOT_STEADY`.
- Mức ổn định và cửa sổ đo của EGO giữ nguyên E6.

**Probe 2 (target readiness của NPC):**
- Target = trung bình của cửa sổ 2 s muộn nhất thỏa cùng điều kiện, kết thúc không muộn hơn `T_end` của EGO.
- Không có → `READINESS_NOT_STEADY`.

**T_r, marker, kiểm `RUNIN_ROOM`:** giữ nguyên E6.5. Cả hai xe phải cùng thỏa vị từ readiness của runner.

## P2. Thời gian chờ pha đèn

- Giới hạn chờ vị từ pha = **max(60 s, chu kỳ quan sát được + 2 s)**.
- Giá trị này được ghi vào `environment.phase_wait_limit_s` của ứng viên và của fixture. Runner đọc giá trị đó; nếu không
  có thì dùng 60 s như cũ.
- Vẫn không săn pha, không reload, không đổi đèn.

## P3. Runtime recipe cho các loại khác

- **O (6 cảnh):**
  - NPC đi trước ở 2,5 m/s không đổi, theo chương trình phụ lục tạm (spec §6.1, §7.4);
  - EGO giữ chương trình đã đóng băng; route của response được thay bằng route fixture, như V3.1;
  - `action_regions` và các mặt cắt suy từ làn CARLA, với bề rộng làn dùng như V3.2;
  - readiness và marker lấy theo E6.
- **I (6 cảnh):** dùng chương trình NPC đề xuất của spec §7.4 làm phụ lục tạm, gắn nhãn **PROVISIONAL** trong mọi kết
  quả. Spec §1.2 xếp "Interactive NPC release" là PROVISIONAL; Duy duyệt dùng nó với nhãn đó.
- **M01:** proof `MERGE_TRANSITION` theo phương pháp `branch-to-mainflow-geometry-topology`. Vùng chuyển tiếp là hộp theo
  bề rộng làn quanh điểm nhập của connector branch vào làn đích (V3.2).
- **F01:** chương trình NPC đề xuất của spec §8, nhãn **PROVISIONAL**.
- **F04:** `BLOCKED_CAPABILITY`, vì spec §5.4 đòi proof bao cửa xe đã hiệu chuẩn mà hiện chưa có.
- **Giữ nguyên quy tắc chung:** quy tắc nào chưa đủ chi tiết để hiện thực mà không phải tự chọn tham số mới thì cảnh đó
  BLOCKED, kèm lý do. Claude không tự đặt ngưỡng mới.

## P5. Quy trình trong tuần

- **Full suite:** chỉ chạy một lần ở cuối tuần; trong tuần, mỗi thay đổi chạy test nhắm vào phần đổi.
- **Chạy native:** nối tiếp tự động, kể cả ban đêm. Mỗi lúc chỉ một server, cổng 2610, không bao giờ cổng 2410.
- **A/B:** mỗi cảnh **một** lần. Được chạy lại **tối đa một lần** chỉ khi đủ cả ba điều kiện:
  - lỗi nằm ở harness hoặc tooling của Claude;
  - lỗi được chứng minh offline trên dữ liệu đã seal;
  - có commit sửa lỗi.
  Cả hai lần chạy đều được báo cáo.
- **Lỗi của cảnh** (vật lý, event, metric): không bao giờ chạy lại.

## Giữ BLOCKED

- C03, L02 (P4);
- F04 (P3).
