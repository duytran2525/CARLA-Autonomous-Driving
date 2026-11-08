# M56 erratum E6 cho bước chuẩn bị: approach NPC theo D_N (08/11/2026; bản nháp, chưa áp dụng)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** A-SEL2 (Duy, ngày 08/11/2026); Claude quyết dưới ủy quyền "toàn quyền".

**ĐẶT SAU KHI THẤY SỐ:**
- L08 gốc (ngày 25/10) và L08-S1 (08/11, `m56_asel2_cl_20261108T083410Z`) đều ra `PHASING_ROOM`. Với L08-S1, D_N = 211,1 m,
  trong khi NPC có 158,9 m, nên điểm xuất phát rơi vào −54,0 m.
- Erratum này không đổi ngưỡng đo nào. Nó chỉ đổi độ dài route probe mà tooling dựng cho NPC.

## 1. Lỗi

- Bước chuẩn bị v2 dựng approach NPC **cố định 150 m** (`native-v2-prepare.py:160`, `want['NPC'] = 150.`).
- Luật phasing đã đóng băng (prereg v2 §4, `t_N = t_E − (LrefN + 5)/(2 vN)`, `D_N = d_N(t_N − 21/20)`) có thể đòi D_N lớn hơn
  thế. Đó là khi EGO chậm (L: 2 m/s, nên t_E lớn) đi cùng NPC nhanh (k cao). Khi ấy luật phasing không thể thỏa, chỉ vì route
  probe quá ngắn.
- Con số 150 m là một lựa chọn kỹ thuật lúc dựng route, không phải một tham số của cảnh.

## 2. Luật sửa (dự kiến)

1. Nếu sau phasing có `s0 = n_entry − front_off − D_N < 0`, dựng lại route NPC với `approach = 150 + (−s0) + 20` m (cùng
   `route_rows`, cùng luật đi thẳng ngược dòng).
2. Chạy lại probe 1 **một lần**, nhãn `probe1-e6`, rồi tính lại D_N.
3. Nếu vẫn `s0 < 0` thì giữ `PHASING_ROOM`. Không lặp lại lần nữa.
4. Mọi luật khác giữ nguyên: S1 và E5 về đèn, luật cua v6 d, readiness.
5. Áp cho **mọi** slot gặp `PHASING_ROOM`, không chỉ L08.

## 3. Rủi ro phải ghi kèm

Phần approach kéo dài có thể đi qua junction phía trên. Luật chạy đà của fill v4 (§3) chỉ phủ 150 m trên road vào, nên đèn ở
junction phía trên vẫn có thể giữ NPC lại, như C06/C07. Trường hợp đó do S1/E5 và luật `NPC_SIGNAL_HOLD_IN_PROBE2` xử lý, như
mọi cảnh khác.

## 4. Áp dụng

Bản nháp này **chưa** được áp vào code. Code chỉ được sửa sau khi batch `m56_asel2_cl_20261108T083410Z` kết thúc, và bản này
phải được commit trước lượt chuẩn bị lại đầu tiên dùng nó.
