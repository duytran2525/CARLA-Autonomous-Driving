# M56 A-SEL2: addendum F01-v2 cho prereg F phần 1 (14/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** Duy [chat] 14/11/2026: "đổi recipe f01 hỏi advisor các làm cho f01 thành công"; trước đó "dùng cảnh thay thế b3 cho f01".

**Thời điểm và tính chất:** đây là luật **sau khi thấy số** (nguyên tắc 6). Đã có một A/B F01 (M56-P-F01-S1, Town13, recipe f-v1.2):
pair v13 **FAILED** (A hợp lệ; B tông đuôi NPC ở 17,6 s, trong cửa sổ, trước F01_N_CLEAR ~18,5 s). Kết quả đó được giữ và báo
nguyên trong mọi báo cáo, cạnh kết quả dưới addendum này. Byte của `PREREG_M56_F_ASEL2_20261109.md` không đổi.

## 1. Thay đổi

| | Prereg phần 1 | Addendum F01-v2 |
|---|---|---|
| `d0` của F01 (m) | 11,4 | **15,5** |
| `vN_char` của F01 | 3,4 | 3,4 (không đổi; consumer v13 chỉ nhận 3 hoặc 17/5) |
| EGO A / B | dừng / giảm về 2 m/s | không đổi (response của product) |
| Đoạn chạy sau F01_END tới DESTINATION | +10 m | **+6 m** (tooling; v13 DESTINATION_ROOM đòi ≥ 5 m) |
| Site | M56-P-F01-S1 (Town13 road 1165, đã tiêu P5) | **M56-P-F01-S2**: thay thế B3, chọn bằng đúng thuật toán đã đăng ký |

`d0` là đòn bẩy duy nhất không cần consumer mới. Chạy NPC bằng vE (để hết khép khoảng hở) cần consumer v14, nên không làm ở đây.

## 2. Vì sao 15,5 m

- **Độ đa dạng** (DESCRIPTOR_SPECS §1: Δ = |a − b| / max(a, b) ≥ 0,20):
  - declared: so F02 (20) Δ = 0,225; so F04' (8,8) Δ = 0,432; F06 (6,8), F05 (4) lớn hơn nữa. Dải hợp lệ của F01 là [11,0; 16,0].
  - realized: F02 có d0_r ≈ 21 (d0 + (vN − vE)·1 s), nên F01 d0_r tới 16,8 vẫn đạt. Dải chấp nhận ±0,3 m vẫn nằm trong.
- **Không va chạm**, ước lượng từ episode B đã seal của S1:
  - TRIGGER của F01 là lúc NPC phanh theo kế hoạch (metrics.py v13 `_detect_f`), vạch phanh = mũi NPC lúc ready + 3 s · vN. Diễn biến
    sau ready không phụ thuộc d0, nên khoảng hở B mất từ ready tới F01_N_CLEAR là hằng số: S1 mất ≈ 11,85 m (11,35 → chạm).
  - d0 = 15,5 → khoảng hở B tại F01_N_CLEAR ≈ 3,65 m. Sau đó EGO cần (3,65 + 6) m ở 3,86 m/s ≈ 2,5 s, khép 0,6 m/s ≈ 1,5 m,
    nên còn ≈ 2,15 m tại DESTINATION.
- **Tương phản A/B dự kiến** (PASS cần cả hai metric có Δ ≥ 0,20): a_peak_025 A ≈ 7,24, B ≈ 4,08 m/s² (đo trên trajectory S1, Δ ≈ 0,44);
  g_front_min A ≈ 11,1, B ≈ 3,65 m (Δ ≈ 0,67).

## 3. Cổng trước A/B (chốt trước mọi lần chạy native)

1. d0_r trong ±0,3 m của 15,5 (luật f-v1.2, tối đa một probe sửa).
2. **Sàn khoảng hở:** dự báo khoảng hở nhỏ nhất của B qua tới DESTINATION, dùng plateau probe 2 của chính site S2:
   `gap_N = d0_r − 11,85`; `gap_dest = gap_N − (gap_N + 6) / vE_plat · (vE_plat − vN_plat)`. Phải **≥ 1,0 m**, nếu không thì
   không chạy A/B và báo Duy.
3. FROZEN, ADMITTED, mọi contract OK (như cũ).
Mỗi cảnh đúng một A/B (P5). S1 không bao giờ chạy lại.

## 4. Site thay thế

`f-site-replace.py`: cùng pool, khóa sắp xếp, seed, cổng (độ dài 120 m + vE²/3 + 20, trục, dốc ≤ 0,02) và trần (F, town) = 3 như
`f-site-generate.py`. Mọi site lần chạy gốc đã lấy vẫn bị coi là đã dùng và vẫn tính vào trần town. Chọn first-fit kế tiếp cho F01.
Các entry khác (F02, F05, F06) được chép nguyên byte. Tính vào trần thay cảnh 150.
