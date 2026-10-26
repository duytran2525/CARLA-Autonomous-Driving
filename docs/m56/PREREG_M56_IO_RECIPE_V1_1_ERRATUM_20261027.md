# M56 I/O recipe v1.1: erratum sửa harness sau A/B O03 (27/10/2026)

**Thẩm quyền:** ủy quyền đêm 27/10/2026 của người dùng phiên này, nguyên văn: "Tự chạy và tự quyết định làm theo recommended đến
9h sáng mai". Quyết định do **Claude đưa ra dưới ủy quyền, chưa phải Duy duyệt**. Duy xem lại lúc 9h.

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Nguồn gốc:** đặt **sau khi thấy** kết quả lần chạy lại P5 của O03 (`outputs/m56_io_ab_Town06_20261026T185956Z`). Kết quả đó:
- cả hai episode đã chạy trọn, đủ event;
- nhưng không có metric: `METRIC_CONTEXT_INVALID`; A còn có `PLAN_SOURCE_WITNESS_INVALID` và `PHASE_EVENT_WITNESS_UNKNOWN`; B có
  `FOLLOW_GAP_UNKNOWN`.

Cả ba lỗi đều là lỗi harness, chứng minh offline trên dữ liệu đã seal (§2). **Không ngưỡng, luật consumer hay tham số spec nào
đổi.**

## 1. Thay đổi so với v1 (`688ad64`)

| # | Thành phần | v1 | v1.1 |
|---|---|---|---|
| 1 | Kit, `metric_context.map_reference` | Lấy thẳng mapping từ topology. Ref lồng bên trong là mapping thường, nên runner không seal source route | Record có kiểu: DirectedRoute EGO của fixture và các SourceRef continuity của nó. Cùng giá trị; kit tự kiểm `digest == pair.reference` |
| 2 | Product runtime, `plan_refs` theo frame | Luôn là route fixture | Route reference đang hiệu lực (sau reference switch) của lệnh đã tạo frame. Response không có switch (C/L/M) giữ nguyên |
| 3 | Recipe mục 1, đuôi route EGO | X + 20 m | X + gap + 2 thân xe + 20 m (O03: khoảng 53 m), để mũi NPC phía trước vẫn nằm trên route EGO tới X_END ở B |

## 2. Bằng chứng offline (trên lần chạy lại đã seal)

1. **Source route chưa được seal.** Trên cả 484 frame của A và 1027 frame của B, source của `map_reference`
   (`routes-io.json`, NATIVE_ROUTE) không có trong `evidence.source`.
   - Ở C01 (v6), source route có mặt, vì kit C/L/M đặt một DirectedRoute có kiểu vào context.
   - Runner chỉ seal các SourceRef object nó tìm thấy trong integrity của frame.
2. **Plan witness sai sau switch.** Consumer đòi plan witness khớp với route reference đang hiệu lực
   (`_reference_response(response, command.cause).route`). Sau switch TARGET, đó là route làn đích, nhưng runtime vẫn ghi route
   fixture.
   - Vì vậy `_frame_integrity` báo invalid, rồi `_authenticated_events` trả None, dẫn tới `PHASE_EVENT_WITNESS_UNKNOWN`.
3. **Gap không đo được ở B.** Có 103 frame mà `min_front_gap` là None, từ khi tâm EGO ở station khoảng 169,8.
   - Lúc đó mũi NPC đã ra khỏi đầu cuối route EGO (199,4).
   - Gap nhỏ nhất đo được là 20,84 m, nên đây không phải vi phạm khoảng cách.

## 3. Kiểm trước khi chạy

- **Prep v1.1:** `outputs/m56_v2_prepare_Town06_<utc>` (PREPARED); revision `outputs/m56_c0_partial_io_o03v11_20261026T192717Z`.
- **Compile native:** `outputs/m56_io_compile_Town06_20261026T192724Z`, FROZEN, ADMITTED, contract OK. Plan kết thúc ở 232,2.
- **Self-check:** PASS.
- **Kit:** digest của map reference có kiểu khớp pair reference.
- **Test product:** 59 test runtime qua. Trước đó đã qua: 307 test reference switch, 348 test I/O/metrics và test perf.

## 4. Chạy

Một A/B O03 theo v1.1 (P5: một A/B cho mỗi cảnh trong mỗi version). Báo kết quả nguyên trạng, kèm cả hai lần chạy v1 trước đó.
