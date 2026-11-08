# M56 signal-phase v1 erratum 5: đèn neo nằm sau điểm xuất phát của NPC (08/11/2026)

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** người dùng phiên này (đã tự xưng Duy ngày 07/11/2026, trao toàn quyền, "không cần tôi duyệt") yêu cầu ngày
08/11/2026: "làm tiếp cho tôi". Claude quyết erratum này dưới ủy quyền đó.

**Thời điểm:** erratum được commit trước lần chuẩn bị lại và A/B của M01. M01 chưa từng có A/B, nên với M01 erratum này không phải
luật đặt sau khi thấy số đo của cảnh. Erratum được viết sau khi M01 bị chặn ở bước chuẩn bị (`NPC_SIGNAL_HOLD_IN_PROBE2`, cl-v1
ngày 08/11), và sau một chẩn đoán chỉ đọc (§1).

## 1. Chẩn đoán (chỉ đọc, không có A/B)

Ba cảnh bị chặn với lý do `NPC_SIGNAL_HOLD_IN_PROBE2`: C06, C07 (sau erratum làn C0) và M01. Dữ liệu lấy từ observation của
probe 2 (frame có lệnh NPC `NPC_TRAFFIC_HOLD`), cộng hai diag chỉ quan sát, không spawn xe, chạy trên server riêng 2610:
`native-signal-chain-diag.py` và `native-signal-m01-diag.py`.

| Cảnh | NPC bị giữ ở đâu | Đèn neo S1 | Kết luận |
|---|---|---|---|
| C07 | đèn **1232**, ở giao lộ trước, khoảng 85 m trước vùng xung đột; 9 frame | 1228, ở giao lộ xung đột | Không có lỗi khách quan (xem dưới) |
| C06 | đèn **2385**, ở giao lộ trước, khoảng 79 m trước vùng xung đột; 13 frame | 2389, ở giao lộ xung đột | Không có lỗi khách quan |
| M01 | đèn **1616**, cách tâm vùng xung đột 4,4 m; 743 frame (37 s) | **1619: vạch dừng ở trạm 121,96 m, nằm SAU điểm xuất phát đã phasing của NPC (139,12 m)** | **Lỗi khách quan** |

**C06, C07.** Nhóm đèn ở giao lộ trước có cùng chu kỳ với nhóm đèn neo:

| Cảnh | Chu kỳ | Đèn trước xanh sau đèn neo |
|---|---|---|
| C07 | 906 tick | 302 tick |
| C06 | 1208 tick | 302 tick |

Độ lệch này không đổi qua mọi chu kỳ quan sát: 7 chu kỳ ở C07, 4 ở C06. Mỗi đèn không đỏ trong 13 s (xanh 10 s, vàng 3 s). NPC
tới đèn trước sớm hơn t_in khoảng 5,5 s (C07) và 6,2 s (C06). Luật S4 cùng erratum 4 đòi đèn neo xanh ít nhất 1 s trước t_in, và
đòi t_out ≤ hết xanh − 1 s.

Với các ràng buộc đó, thời điểm NPC qua đèn trước luôn rơi vào pha đỏ của nó, dù chọn lần lặp nào của neo. Đây là tính chất của
map (làn sóng đỏ ngược chiều NPC) cộng với timing đã đóng băng (D_N, vN). Không có lỗi nào sửa được mà không đổi timing đóng
băng hay cho xe vượt đèn đỏ. **Ghi nhận, không sửa.**

**M01.** Luật S1 (erratum 1, `59744b3`) chọn đèn: trong các đèn dọc làn của vai tới junction exit, lấy đèn có vạch dừng cách
route ≤ 1,0 m và có trạm dừng lớn nhất mà vẫn ≤ trạm vào xung đột. Luật này được áp trên **route dài của probe 1**, trước khi
phasing cắt điểm xuất phát của NPC. Đèn được chọn, 1619, nằm 17 m sau điểm xuất phát cuối, nên không bao giờ gác NPC được. Neo S4 khi
đó suy biến: t_in = t_out = 1,1 s, đúng bằng thời điểm release.

Đèn thật sự giữ NPC là 1616. Vạch dừng của nó nằm ở trạm 60,4 m trên route đã phasing (199,52 m theo tọa độ probe 1), trong khi
trạm vào xung đột là 60,46 m. Vạch dừng lệch ngang 0,08 m, và `get_traffic_lights_from_waypoint` gọi từ điểm xuất phát đã
phasing có trả về đèn này. Vậy 1616 đạt **mọi** tiêu chí S1 trên route cuối.

**Cùng điều kiện ở các cảnh khác** (quét mọi `prepare.json`): L01, L02, L05 cũng có đèn S1 nằm sau điểm xuất phát đã phasing.
- L01 là cặp PASS: probe 2 và A/B của nó không có frame giữ đèn nào, và witness của consumer kiểm trực tiếp việc giữ đèn. Vì vậy
  kết quả L01 không bị ảnh hưởng. Claude ghi lại ở đây để minh bạch, và không chạy lại L01 (P5).
- L02 và L05 bị chặn vì lý do khác (BLOCKED_WITNESS GROUND/CONTACT; mục e). Không chạy lại.

## 2. Luật sửa (`M56_SIG5=1`, chỉ trong `native-v2-prepare.py`)

Sau khi phasing cắt route NPC, nếu trạm dừng của đèn S1 < trạm xuất phát đã phasing:
1. Chạy lại S1 với **đúng các tiêu chí cũ**, trên route NPC đã phasing (trạm vào xung đột đổi sang tọa độ của route đó).
2. Đổi trạm dừng của đèn mới về tọa độ probe 1, như S4 đòi.
3. Quan sát chu kỳ của nhóm đèn mới (S2), rồi đặt lại giới hạn chờ theo v4 P2: max(60 s, chu kỳ + 2 s).
4. Neo S4 và erratum 4 giữ nguyên.

Không tìm được đèn nào thì cảnh bị chặn với lý do `SIGNAL_E5_NO_LIGHT`. Cảnh có đèn S1 nằm trước điểm xuất phát thì không đổi gì.
Trường `signal_e5` của `prepare.json` ghi cả đèn cũ lẫn đèn mới.

## 3. Chạy

- **Chỉ M01.** C06 và C07 không có lỗi khách quan. L01, L02 và L05 không chạy lại, như đã nói ở §1.
- Chuẩn bị lại M01 dưới recipe v6 + cl-v1 + E5, trên cùng revision chuẩn bị với lượt cl-v1 (`m56_c0_partial_v5g_20261025T155258Z`),
  product `m56-v9` `1db746f`. Vùng drivable lúc chuẩn bị giữ như lượt cl-v1.
- Nếu PREPARED: freeze một revision, rồi chạy **đúng một** A/B (P5) dưới version fixture hiện hành dv1 (`M56_DRIVABLE=dv1`, chỉ
  áp lúc A/B, giống C08). Tính pair dưới consumer v9 và v6.
- Cảnh hỏng ở bất kỳ bước nào thì ghi lại, không chỉnh thêm, không chạy lại.
- Script: `run-sig5.sh`.

**Giới hạn phải ghi kèm kết quả:** M01 dùng dv1, là luật vùng drivable đặt sau khi thấy số (của C02, M07, C08). Nếu M01 PASS thì
nó hợp lệ kèm các điều kiện: E5, cl-v1 b (probe dài 60 s), dv1, consumer v6+.

## 4. Kết quả

(điền sau khi chạy)
