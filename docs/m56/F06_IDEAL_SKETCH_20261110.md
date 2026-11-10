# M56 A-SEL2: phác thảo lý tưởng F06 (10/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:**
- `PREREG_M56_F_ASEL2_20261109.md` §2, mục F06-ALT1: "phác thảo lý tưởng phải đạt ≥ 0,20 trước khi compile. Nếu không đạt, F06
  được ghi `DIVERSITY_DEFICIT` trước A/B, và không chỉnh gì thêm."
- Duy ngày 10/11: "làm theo những gì bạn recommended".

**Thời điểm:** trước mọi compile, preparation và A/B F06. Chưa có số đo F06 native nào.

## Phép tính (input đã đăng ký, không chỉnh gì)

Luật của product (`compare_ab`, `metrics.py`): cả hai metric của cặp đều phải có Δ ≥ 1/5, với Δ = |a − b| / max(a, b).

Cặp F06-ALT1 (`_F_CONTRACTS`) đo trên cửa sổ [`TRIGGER`, `NPC_REVERSE_TARGET_STOP_CONFIRMED`]:
- `d_reserve_reverse_m`;
- `g_front_min_m`.

Input:
- khoảng hở trước ban đầu d0 = 6,8 m;
- NPC lùi 2 m;
- A giữ yên;
- B lùi 1 m.

Giả định lý tưởng: chuyển động đúng như đăng ký, không sai số.

| Metric | A | B | Δ |
|---|---|---|---|
| `d_reserve_reverse_m` | 0 | 1 | 1 |
| `g_front_min_m` | 6,8 − 2 = 4,8 | 4,8 + 1 = 5,8 | 1/5,8 = **0,172** |

Δ của `g_front_min_m` nhỏ hơn 0,20.

## Kết luận

- **F06: `DIVERSITY_DEFICIT`**, ghi trước A/B, đúng như prereg.
- Không chỉnh d0, quãng lùi hay tốc độ để vượt ngưỡng.
- F06 bị loại khỏi phạm vi consumer v14. Phạm vi v14 còn lại F05 (creep của B) và F03 (sau grade probe và prereg phần 2).
- Slot F06 tính là một slot không đạt trong báo cáo §11.
- Site đã chọn (Town12 R896) được giữ nguyên, không bị dùng lại cho mục đích khác.
