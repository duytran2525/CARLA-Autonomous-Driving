# M56 báo cáo cuối, 23/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Selector: CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT.

**Thẩm quyền đóng:** Duy [chat] 23/11/2026 chọn "Đóng và viết báo cáo", sau khi đã chọn "Dừng: M = KHÔNG ĐẠT".

Chi tiết từng bước nằm trong `docs/m56/M56_ASEL2_BATCH_LOG_20261108.md`. Các luật nằm trong các file `PREREG_M56_*` (addendum A–Z).

## 1. Kết luận

M56 không đạt sàn M132. Release vẫn `RELEASE_BLOCKED` và không có export.

Sàn M132 (Duy duyệt 10/10, trước khi có số thật) đòi 30 cảnh phủ đủ 5 loại tương tác (C, L, M, O, I), mỗi loại ít nhất 6 cảnh. Loại nào dưới 6 cảnh thì không được chấm, tính là KHÔNG ĐẠT và vẫn giữ trong mẫu số. Mục tiêu gốc của M56 là 46 cảnh.

| Loại | Cảnh có cặp PASS | Số | Theo M132 |
|---|---|---|---|
| C | C01, C02-S1, C03-S2, C04-S2, C05, C06-S1, C07-S2, C08 | 8 | được chấm |
| L | L01, L02-S1, L03-S1, L04, L05-S1, L06-S1, L07-S2, L08-S2 | 8 | được chấm |
| O | O01, O02, O03, O05-S1, O07-S2 | 5 | KHÔNG ĐẠT |
| I | I02-S2, I03, I04 | 3 | KHÔNG ĐẠT |
| M | (không có) | 0 | KHÔNG ĐẠT |
| F (tự do) | F01-S2, F02 | 2 | không bắt buộc |

Tổng cộng có 26 cảnh có cặp PASS. Release còn bị chặn bởi `CANDIDATE_COUNT`, `JUNCTION_SHORTFALL`, `C0_MISSING` và `COMPARISON_COVERAGE`. Riêng các deficit này cũng đủ chặn release, kể cả khi sàn M132 đạt.

## 2. Cặp nào chỉ PASS dưới luật đặt sau khi thấy số (nguyên tắc 6)

Mọi cặp sau luôn phải được báo cạnh kết quả dưới luật gốc.

- C07-S2, L08-S2: PASS dưới consumer m56-v12. Dưới v10 và v6 là BLOCKED_WITNESS.
- O05-S1, O07-S2: PASS dưới consumer m56-v15 (sàn Dlc của io-v1.6). Dưới v10 là BLOCKED_WITNESS.
- I02-S2: PASS dưới v17. I04: PASS dưới v17, v16 và v15. Lần chạy này là I04 chạy lại sau khi PASS cũ bị hạ ngày 15/11 (addendum L, gap thực 46,42 m so với spec 13,18 m).
- F01-S2: PASS dưới F01-v3. Đây là luật sau số lần hai: nhu cầu site 91,4 m được chọn sau khi đã thấy pool.
- Nhiều PASS khác chỉ đạt dưới v7/v8/v12, dv1 hoặc f-v1.2. Bảng đầy đủ: `docs/m56/M56_RUN_RESULTS_DIGEST_20261114.csv` cùng các mục sau ngày 14/11 trong batch log.

## 3. Vì sao O, I, M dưới 6

### O (5)
- O04-S3: hai probe dài dừng `TICK_ERROR` ở frame 994, cả lần 16/11 lẫn lần 22/11 (sau fix 4). Kết quả: BLOCKED, không prepare lại (Duy 22/11). Nhận định ở addendum Z §3 rằng đây là timeout nạp tile đã bị bác bỏ; nguyên nhân thật chưa rõ.
- O08-S3: addendum Z sửa đúng lỗi kẹp vị trí xuất phát của NPC; cổng L qua (gap thực 55,380 m, spec 55,694 m). Sau đó self-check trượt `PREDICTED_RETURN_GUARD_MISSING`: thời gian dư 0,000 s, cần > 0,05 s ở vE 18,1 m/s. Kết quả: BLOCKED, không có A/B.
- O06: BLOCKED_WITNESS dưới v15; P5 đã tiêu.

### I (3)
Addendum Q (17/11) chốt các cảnh I còn lại:
- I01-S1 không qua G3 với bất kỳ recipe nào nằm trong luật: vN theo spec, cổng κ buộc Dlc ≥ 17,4 m, ngưỡng 2,3 s giữ nguyên.
- I05-S2 (G1), I06-S2 và I07-S2 (G3), I08-S2 (cổng L) dừng ở cổng mà chúng trượt.
- Duy 22/11 quyết loại I = KHÔNG ĐẠT, không chọn successor mới.

### M (0)
- Các cảnh M đã chạy đều hỏng. M01-S1, M06-S1, M06-S2, M08-S2: NPC cắt góc ra khỏi vùng drivable. Các cảnh còn lại: `COLLISION_OBSERVED`, `E_ENTRY_MISSING`, `CLEAR_N_CONFIRMED_MISSING`, `UNPLANNED_REVERSE`, `SPAWN_ERROR`, `SIGNAL_E5_NO_LIGHT`.
- Addendum R: NPC là `LocalPlanner` stock đã ghim. Kể cả với lookahead 2 m, NPC rẽ vẫn không giữ được trong vùng drivable ở các site có lề hẹp.
- Addendum S (cổng mép làn riêng ≥ 0,45 m): cả 8 slot M đều EMPTY. 0/393 site qua, kể cả khi NPC bám tâm làn lý tưởng (lớn nhất 0,440 m).
- Kiểm khả thi 22–23/11, chỉ báo cáo (Duy chọn "Kiểm khả thi M trước"). Đo tới mép dv1 thật, dựng bằng CARLA đúng như `drivable_union` (phần dựng nhanh khớp `drivable_union` với sai 0,000 m trên 7 trường hợp đã đối chiếu):
  - Cận dưới offline (phần làn của dv1): 0/393 site đạt ≥ 0,45 m.
  - Trên CARLA: 36/101 site đã kiểm, chỉ 1 site qua (Town05 100/-1, 0,95 m). Town12 0/12, Town13 0/22. Ở Town13 phần mặt đường ngoài làn không cộng thêm biên.
  - Lần kiểm dừng khi bộ nhớ gần cạn (xem mục 4). 65 site Town13 chưa được kiểm.
- Duy 23/11 quyết M = KHÔNG ĐẠT. Cổng dv1 không được viết thành addendum.
- Nhận định của Claude: với controller NPC stock đã ghim, loại M khó đạt 6 cảnh ở bất kỳ town nào đã dùng. Đổi controller là đổi spec, việc này nằm ngoài M56.

## 4. Sự cố vận hành cần biết

- **21/11:** máy tắt không sạch (event 41) khi commit headroom còn 7,8 GB trong một A/B.
- **22–23/11:** Town13 với các app đang mở làm tụt 22–30 GB commit chỉ trong vài phút.
  - O04-S3: headroom còn 7,2 GB, Claude tự tắt CARLA.
  - O08-S3 (lần đầu): guard dừng ở 2,36 GB.
  - Kiểm M: headroom chạm 0,08 GB. Windows tự tăng pagefile trên E thêm 32 GB (commit limit từ 63,6 lên 95,6 GB); Claude không đổi pagefile.
- **Sau 03:08Z ngày 23/11:** liệt kê tiến trình qua WMI và `tasklist` bị treo. `own_server` không tắt được CARLA; Claude phải tắt tay bằng `Stop-Process`. Stopper không chạy được.
- **Trạng thái hiện tại:** đã ghi STOP, và `M56_SAFE_TO_SHUTDOWN.txt` được viết tay (không do stopper). Cần khởi động lại máy để hết treo WMI.
- **Các mức guard Duy cho phép khi chấp nhận rủi ro** (cổng bật CARLA 28 GB rồi 20 GB, guard dừng 1 GB) chỉ áp dụng cho các lần chạy 22–23/11. Mặc định vẫn là cổng bật 32 GB và guard dừng 4 GB.

## 5. Những gì còn dùng được

- 26 cảnh có cặp PASS (bảng ở mục 1), cùng file `pair-result.json` của chúng trên D.
- Các loại C và L đủ 8 cảnh. Theo M132, kết quả của C và L được chấm, còn O, I, M tính là KHÔNG ĐẠT trong mẫu số.
- Suite `tests/m56` trên m56-v23 qua 1314/1314 (suite 15, 22/11).
- Công cụ kiểm offline (`native-io-runin-offline.py`, `native-io-npcback-offline.py`, `m-site-edge-gate.py`, `native-m-dv1-feasibility.py`) và số liệu trong `outputs/m56_m_margin_estimate_20261122/`.

## 6. Không làm

- Không hạ sàn M132 và không bỏ loại nào khỏi sàn. Làm vậy là đổi tiêu chí sau khi đã thấy số (nguyên tắc 6), và M132 tự ghi rằng sàn không được hạ.
- Không chạy lại cảnh nào đã tiêu P5. Không sửa byte nào của spec, của prereg đã commit, hay của ngưỡng Tag.
