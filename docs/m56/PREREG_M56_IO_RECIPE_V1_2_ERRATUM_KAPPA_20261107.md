# M56 I/O io-v1.2, erratum cận gia tốc ngang theo điểm (07/11/2026). ĐẶT SAU KHI THẤY SỐ

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:**
- [chat] 07/11/2026, người dùng tự xưng Duy: "tôi cho bạn toàn quyền quyết định không cần hỏi lại tôi thêm cái gì nữa hết, bạn thấy
  hợp lý và làm theo điều bạn recommended, tiếp tục làm việc để hoàn thiện task m56".
- Erratum này do **Claude quyết dưới ủy quyền toàn quyền của Duy**. Duy không review riêng nội dung erratum.
- Ghi sổ: `docs/crfp/crfp-main-ledger.md`, commit `114cba1`.

## Luật cũ (giữ nguyên văn, vẫn được báo)

Prereg I/O v1 (`PREREG_M56_IO_RECIPE_V1_20261026.md`), dòng 18:

> Kit, `REFERENCE_LATERAL_BUDGET` | Bound = v² × (độ cong route + (10/√3)·\|Δ\|/L² của mọi đoạn quintic có dịch ngang trong ±10 m).
> Cận này giữ nguyên cho C/L/M vì các profile của chúng không dịch ngang

Kit io-v1.2 (tooling `070aa0d`) cài câu này là `v² × (max độ cong route trong ±10 m + max độ cong profile trong ±10 m)`.

## Luật mới

`v² × max theo từng điểm route trong ±10 m của (độ cong route tại điểm đó + độ cong quintic dự kiến tại điểm đó)`.
- Cài ở `Kit.lateral_kappa`, tooling `761e45b`. Chỉ bật khi đặt `M56_IO_KAPPA=pointwise`.
- Giá trị này được seal vào receipt của A/B (trường `kit_lateral_bound`, từ tooling của commit chứa file này).
- Ngưỡng consumer 2,5 m/s² **không đổi**. Với C/L/M (không có đoạn dịch ngang), luật mới giống hệt luật cũ.

## Vì sao, và vì sao đây không phải lỗi khách quan

- **Số đã thấy trước khi đặt luật:** O02 A (27/10) cho cận 2,844 > 2,5, nên bị `REFERENCE_LATERAL_BUDGET_UNPROVEN`.
- **Lý do:** luật cũ cộng hai giá trị max của cửa sổ. Ở O02, đoạn đổi làn kết thúc ở station 146,1, còn cung đường 91° bắt đầu
  khoảng 160. Hai đoạn không bao giờ trùng nhau tại cùng một điểm. Cận theo điểm là 2,245, và vẫn là cận trên.
- Luật cũ lỏng nhưng vẫn là một cận trên đúng. Vì vậy đây là **thay đổi phương pháp sau khi thấy số**, không phải lỗi harness hay
  lỗi khách quan.

## Phạm vi và cách báo

- **Áp dụng cho:** lần chạy lại theo P5 của O02 (`M56_IO_KAPPA=pointwise`).
- **O01 chạy lại với luật cũ.** O01 A có cận 2,2453 dưới cả hai luật.
- **Cảnh I/O sau này:** prereg của từng cảnh phải ghi rõ dùng cận nào. Cả hai cận đều được tính và báo.
- **O02 được báo bốn cách:** {luật cũ, luật mới} × {consumer v8, consumer v7}.
  - Theo luật cũ: kết quả của A được suy ra bằng `native-io-kappa-recompute.py` trên trajectory mới. Cận chỉ phụ thuộc tốc độ
    reference và station, nên một episode A trọn vẹn luôn có cận 2,8439, tức là UNPROVEN, và pair là BLOCKED.
- **Điều kiện hợp lệ:** O02 chỉ được đưa vào danh sách cặp hợp lệ kèm điều kiện "chỉ theo cận đặt sau số 06/11", giống cách L04
  được ghi "chỉ hợp lệ theo v7".
