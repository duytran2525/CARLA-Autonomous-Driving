# Erratum 4 cho signal-phase v1: điểm neo duy nhất gần nhất (24/10/2026)

**Thẩm quyền:** [chat] 24/10/2026, người dùng tự xác nhận là Duy:

> cho phép điểm neo lùi tới tick gần nhất mà gói pha là duy nhất (ghi công khai, cả hai quy tắc), rồi chuẩn bị lại và
> chạy A/B C01, C02 một lần.

**Thứ tự:** erratum này được commit **trước** lần chuẩn bị lại.

**Tính chất:** đây là thay đổi quy tắc **đặt sau khi thấy kết quả chuẩn bị v3** (C01 bị `SIGNAL_ANCHOR_AMBIGUOUS` ở k = 41).
Chưa có A/B v3 nào.

## Quy tắc cũ (S4 cùng erratum 2–3, giữ nguyên văn)

- Vị từ là gói pha tại đúng k tick trước lúc Green.
- Nếu gói đó xuất hiện nhiều hơn một lần trong chu kỳ → `SIGNAL_ANCHOR_AMBIGUOUS`.

## Quy tắc mới

1. **Chọn tick neo:**
   - Lấy `k' ≥ k` nhỏ nhất (tức lùi thêm tick về trước lúc Green) mà gói pha tại đó **duy nhất** trong chu kỳ tham
     chiếu.
   - Ghi lại cả `k` và `k'`.
2. **Mốc xanh mới:** `T_g' = t_in − 2 s − (k' − k)/20`.
3. **Điều kiện bắt buộc, không đạt → BLOCKED_FIXTURE:**
   - đèn phải xanh từ ít nhất 1 s trước `t_in`, tức `k' ≤ round(20·t_in) − 20`; không đạt → `SIGNAL_TIMING_INFEASIBLE`;
   - `t_out ≤ T_g' + (N_G + N_Y)/20 − 1 s`; không đạt → `SIGNAL_TIMING_INFEASIBLE`;
   - không có `k'` nào thỏa → `SIGNAL_ANCHOR_AMBIGUOUS`.
4. **Báo cáo:** mọi kết quả ghi cả hai quy tắc. Với C01, quy tắc cũ cho `SIGNAL_ANCHOR_AMBIGUOUS`, nghĩa là theo quy
   tắc cũ thì không có A/B.

## Chuẩn bị lại C02

- Ở chuẩn bị v3, probe 1 của C02 bị `BLOCKED_SIGNAL_ADMISSION`. Spec §484 ghi "no phase hunt/reload/rerun".
- Theo yêu cầu nêu rõ của Duy ("chuẩn bị lại … C01, C02"), C02 được chuẩn bị lại **một lần**. Đây là quyết định của Duy,
  ghi công khai, và chỉ áp dụng cho probe chuẩn bị, không áp dụng cho A/B.
- Nếu lại quá hạn thì ghi nguyên, không thử thêm.

## Không đổi

Các mục sau giữ nguyên:

- prereg v3 (V3.1–V3.4);
- các erratum E1–E6;
- signal-phase v1 cùng erratum 1–3;
- giới hạn chờ 60 s;
- quy tắc mỗi cảnh chỉ một A/B.
