# M56 I/O recipe io-v1.3: O04, O05, O07 (các cảnh O của catalog fill), đăng ký trước, 07/11/2026

**Nhãn:** independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:**
- [chat] 07/11/2026, người dùng tự xưng Duy, ủy quyền toàn quyền ("làm theo điều bạn recommended … hoàn thiện task m56").
- Bản này do **Claude quyết dưới ủy quyền đó**. Không phải Duy review.

**Trạng thái lúc đăng ký:** chưa có lần chuẩn bị, compile hay episode nào của O04, O05, O07. Số liệu duy nhất đã dùng là hình
học tĩnh: OpenDRIVE và route catalog đóng băng (§2).

## 1. Nền

- **Consumer v9** (`PREREG_M56_V9_IO_NOMINAL_SERIES_20261107.md`), nhánh `feat/m56-v9`. Các cảnh này có k = 4 / 0 / −1, nên dưới
  v8 chúng bị chặn ngay lúc admission.
- **Recipe:** io-v1 (`688ad64`) + erratum v1.1 + io-v1.2 (`90bc7a3`).
  - RUNIN = ⌈100·vE / 9,375⌉.
  - Hộp làn neo ở trung điểm của [`O_DECISION`, `DESTINATION` + 3 m].
  - Section phủ hai làn trên toàn route.
  - Đuôi route EGO = X + gap + 2 thân xe + 20 m.
- **Cận gia tốc ngang của kit:** dùng cận theo điểm (`M56_IO_KAPPA=pointwise`, erratum `ce3fc43`) và báo cả hai cận. Ba road
  đều thẳng (§2), nên hai cận dự kiến bằng nhau.

## 2. Hình học (OpenDRIVE và catalog, không có số episode)

| Cảnh | Road (làn đầu → làn đích) | Hướng | Road dài | Cửa sổ đã đóng băng trong catalog (decision → X, road-s) | Native cần (EGO; NPC) |
|---|---|---|---|---|---|
| O04 | Town06 R37 (−6 → −7) | −0,23°, line | 199,5 | 65,8 → 158,7 | −59,2 … 220,6; NPC tới 250,6 |
| O05 | Town04 R39 (−2 → −3) | 179,77°, line + cung 1,4 m | 133,9 | 27,7 → 89,7 | −24,3 … 130,3; NPC tới 160,3 |
| O07 | Town06 R38 (−3 → −4) | −0,23°, line | 144,1 | 24,9 → 92,8 | −16,1 … 130,7; NPC tới 160,7 |

- Cửa sổ đổi làn và quay về nằm trọn trong road của catalog. Luật trục của consumer (thẳng, lệch ≤ 1°) vì vậy đúng như với O03.
- Run-in và đuôi route vượt ra ngoài road và phải đi qua connector của junction:
  - **O04:** đi lùi qua connector 1149 (thẳng 71,3 m, −0,23°), đi tiếp qua 1037 (thẳng 44,7 m) tới R38.
  - **O05:** đi lùi qua connector 1091. 28 m cuối của 1091 thẳng ở 179,767°; run-in chỉ cần 24,3 m. Đi tiếp qua 1184 (thẳng
    53 m).
  - **O07:** đi lùi qua 1037 (thẳng). Phía sau R38 là junction 332, nơi làn nhập vào road 5 (có cung). Vì vậy đuôi NPC bị cắt
    ở đó (§3.c).

## 3. Các mục mới của io-v1.3

| # | Mục | Luật |
|---|---|---|
| a | Hình học từ catalog fill | decision = road-s của điểm đầu route EGO A trong catalog + arc bắt đầu đoạn đổi làn đã đóng băng. Dlc = độ dài đoạn đó, phải bằng 3·vE. gap = G_m; return_start = returnstart_m; X = decision + return_start + Dlc + 3,75 (spec §7.4). NPC đi ở làn đầu. **Không dời site.** |
| b | Route qua connector | Trong road của catalog: như cũ. Ngoài hai đầu road: đi theo phần nối tiếp của làn trong CARLA (`next` / `previous`, chọn waypoint có yaw gần nhất) đúng bằng quãng còn thiếu. Mọi điểm phải lệch ≤ 1° so với hướng road. EGO và route làn đích vi phạm thì cảnh `BLOCKED_PREPARATION`. |
| c | Đuôi NPC | Như b, nhưng nếu vi phạm 1° thì route NPC bị **cắt** trước điểm vi phạm. Quãng bị cắt ghi vào `npc_tail_cut_m`. Phần cắt chỉ là lề NPC_TAIL 30 m sau đuôi EGO. |
| d | Tra road-s | Mọi phép đổi giữa road-s và station chỉ dùng các điểm của road catalog. Với route chỉ nằm trên một road (O01–O03), kết quả không đổi. |

## 4. Quy trình và luật dừng

1. Chạy `run-io-prepare.sh` (`M56_CODE=m56-v9`, `M56_IO_BOX_ANCHOR=midpoint`, không đặt `M56_IO_SITE_SHIFT`) cho ba cảnh, mỗi
   cảnh trên server riêng 2610.
2. Một cảnh chỉ được chạy A/B nếu đủ tất cả: `PREPARED`; fixture `FROZEN` + `ADMITTED` (v9); self-check qua; replay offline A/B
   qua (`native-io-replay.py`); ước tính thời gian online xấu nhất < 270 s.
3. **Mỗi cảnh đúng một A/B (P5).** `M56_IO_PREREG_APPROVED=<commit của file này>`, `M56_IO_KAPPA=pointwise`. Sau đó chạy pair
   theo v9 và theo v8.
4. **Không chỉnh tham số sau khi thấy số.** Cảnh nào không đạt bước 2 thì để BLOCKED, ghi lý do, và **không** chạy lại với
   tham số khác trong phiên này. Muốn đổi thì phải có một prereg mới, công khai là đặt sau khi thấy số chuẩn bị.
5. **Báo cáo:** nguyên trạng theo v9 và v8 × hai cận (§1).
