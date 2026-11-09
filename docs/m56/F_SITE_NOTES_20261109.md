# M56 A-SEL2: ghi chú cài đặt chọn site F (09/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Selector: `CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT`.

Bản này ghi các chi tiết cài đặt mà `PREREG_M56_F_ASEL2_20261109.md` §3 không nói rõ. Nó được commit cùng
`f-site-generate.py`, **trước** lần chạy duy nhất của bộ sinh. Chưa có kết quả chọn site F nào. Bộ chữ của prereg giữ nguyên.

1. **Pool.** Là pool R1 của fill v4, tức `chains_v3` của fill v3, chạy trên 11 town (hash XODR như fill v4). Các site bị loại:
   - junction và road của revision chạy;
   - mọi site mà các file fill v4 đã đề xuất hoặc xếp hàng (bản gốc và các vòng thay): road của I/O, junction của C/L/M
     (kèm vùng neo 30 m).
2. **Cổng.** Cổng chỉ xét trên laneSection của site, vì `native-f-prepare.py` dựng cả hai route trên đúng section đó. Gọi
   chiều dài cần là `need = L + vE²/3 + 20`. Các cổng:
   - chiều dài section trừ 2 m phải ≥ `need`;
   - đoạn thẳng theo trục (B5, cách tính `axis_run` của fill v3) trên section phải ≥ `need`;
   - |độ dốc| ≤ 0,02 tại mọi điểm cách 1 m trên section.
3. **vE dùng cho chạy đà.** Theo tốc độ EGO lớn nhất của cơ chế, phía bất lợi: F01 4; F02 5,5 (B); F05 2; F06 0.
4. **Thứ tự.**
   - Một lần xáo với seed của §3. First-fit theo thứ tự slot F01, F02, F05, F06.
   - Mỗi road chỉ dùng một lần. Trần (F, town) = 3.
   - F03 và F04' sẽ chạy ở phần 2, trên cùng thứ tự xáo, giữ nguyên các site đã chọn ở phần 1.
5. **Id và trần thay cảnh.**
   - F01 thành `M56-P-F01-S1`; candidate C0 `M56-P-F01` được ghi `REPLACED_BY`.
   - F02, F05, F06 lấp slot trống với id `M56-P-F0x`.
   - Mỗi site được admit tiêu 1 lần trong trần 150 (A-SEL2 §2).
6. **Không đụng site của nhau.** Vòng thay fill v4 nào chạy sau bản này phải đưa road của các site F vào danh sách `tried` của
   state, để không chọn lại các road đó.
7. **Realized** của `vN_char` và `d0` sẽ được đóng băng trong một bản ghi riêng, trước A/B F đầu tiên.
