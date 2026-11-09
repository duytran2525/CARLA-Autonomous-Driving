# M56 A-SEL2: ghi chú recipe native F02 (09/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. **Thẩm quyền:** A-SEL2 §1.4 và §5, cùng `PREREG_M56_F_ASEL2_20261109.md`
(F02: NPC 5 m/s phía sau, EGO 4 m/s ở A và 5,5 m/s ở B, trigger khi gR > 20 → ≤ 20; `vN_char` 5, `d0` 20).

**Thời điểm:** commit trước mọi preparation và A/B F02. Chưa có số đo F02 nào.

Chương trình EGO/NPC, cặp metric và event (`_detect_f02`) lấy nguyên của product v13. Ghi chú này chỉ ghi các chi tiết native
mà prereg không nói tới.

1. **Route.** EGO và NPC dùng chung route của làn site, chạy hết section. NPC đứng ở đầu route, EGO đứng ở trạm phía trước.
   - Lý do: metric `min_rear_gap` chiếu NPC lên route EGO. Nếu cắt route EGO thì NPC nằm trước điểm đầu route, phép chiếu trả
     `None`, và trigger không bao giờ nổ.
   - Product không đòi pose nằm ở arc 0.
2. **Khoảng hở lúc readiness.** Mục tiêu là `d0 + (vN − vE) · 1 s = 21 m`. Nhờ vậy `TRIGGER` (gR = 20 m) đến khoảng 1 s sau
   readiness, như trong composition tổng hợp của product (khoảng 0,95 s). Nếu gR lúc readiness đúng bằng 20 m thì điểm cắt
   ngưỡng rơi ngay tại readiness.
   - Declared `d0` vẫn là 20.
   - `d0_r` được đo đúng như định nghĩa (khoảng hở lúc readiness) và báo nguyên giá trị.
3. **Section** (trạm EGO):
   - `nominal_front_t0_m` = mũi EGO lúc readiness + vE · (d0_r − 20)/(vN − vE). Giá trị này lấy từ probe 2 của preparation, không
     phải từ episode.
   - `F02_END = nominal_front_t0_m + 60` đúng tuyệt đối, theo `_detect_f02`.
   - `DESTINATION = F02_END + 5 m`. Với A, NPC nhanh hơn 1 m/s, nên khoảng hở còn khoảng 2,5 m khi tới đích. Composition tổng
     hợp dùng +7,25 m.
4. **Run-in.** Cap `RUNIN_ROOM` lấy mốc là `nominal_front_t0_m`.
