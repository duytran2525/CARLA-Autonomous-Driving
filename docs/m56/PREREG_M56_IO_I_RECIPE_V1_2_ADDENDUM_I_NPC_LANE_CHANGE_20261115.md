# M56 io-i-v1.2, addendum I: đổi làn của NPC ở cảnh I (15/11/2026)

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Tính chất:** chẩn đoán **sau khi thấy số**, chỉ đọc file đã niêm. Addendum này sửa chẩn đoán G4 của io-i-v1.2 §2.4. Nó chưa đặt
luật mới nào.

## 1. Bằng chứng

Nguồn: `run/native/observation/*.json` (readback steer, arc) và `collision_ref.json` của các episode io-i-v1.1 đã niêm. Role được
đọc thẳng từ frame observation: actor đầu tiên là EGO, actor thứ hai là NPC.

| Cảnh | NPC: Dlc = 3·vN (m) | κ_max NPC | max \|steer\| NPC | Va chạm |
|---|---|---|---|---|
| I04 | 32,16 | 0,0195 | 0,11 | không |
| I03 | 25,13 | 0,0320 | 0,12 | không |
| I02-S2 | 19,50 | 0,0493 | 0,12 | không |
| **I01-S1** | **15,00** | **0,0834** | chưa có (episode cũ không ready) | — |
| I05-S1 | 11,40 | 0,1555 | **0,80** | A: NPC vào hình học tĩnh, 95,1–104,1 s |
| I07-S1 | 8,52 | 0,2585 | **0,80** (62 lần arc lùi) | A và B: EGO–NPC |
| I06 | 6,22 | 0,5230 | **0,80** | A: NPC vào hình học tĩnh; B: EGO–NPC |

- Ở I05-S1 A, NPC bắt đầu đánh lái quá 0,3 ở 93,8 s, rồi va vào map ở 95,1 s.
- κ_max = (10/√3)·|offset|/Dlc², cùng công thức với cổng io-v1.6 §2b.
- Ngưỡng 0,0624 đến từ EGO: O01 PASS ở 0,0624, O05-S1 xoay ở 0,0905. Dữ liệu NPC thì sạch tới 0,0493 và hỏng từ 0,1555.

## 2. Hệ quả

- **G4 sai chẩn đoán với I05-S1 và I06.** Va chạm ở A là NPC vào map trong lúc NPC đổi làn với tay lái bão hòa. Cách EGO đi tiếp
  không gây ra nó. `RESUMED_BEFORE_NPC_MERGED_AHEAD` đi kèm theo sau, vì NPC không bao giờ nhập làn xong.
  - I07-S1 có va chạm EGO–NPC, nhưng NPC cũng bão hòa (62 lần arc lùi). Vì vậy G4 chưa được chứng minh ở cảnh nào.
  - **G4 không được dựng.**
- Sàn Dlc của io-v1.6 chỉ áp cho EGO. Consumer v15 giữ NPC = 3·vN. **v15 không giúp được các cảnh I tốc độ thấp.**
- **I01-S1 được giữ lại trước A/B** (P5 chưa tốn). κ của NPC là 0,0834, nằm ngoài vùng có bằng chứng sạch (≤ 0,0624) và gần phía
  hỏng.
  - G3 không phải cổng đáng tin cho trường hợp này: NPC xoay ra khỏi hộp làn nguồn vẫn tính là "clear".
  - Batch dừng ở bước prepare. Prepare chạy nốt và tự tắt server. Không có compile, probe 3 hay A/B.

## 3. Các lựa chọn (chờ người dùng)

1. **Sàn Dlc cho NPC:** max(3·vN, 18 m). Lựa chọn này đổi chương trình NPC đóng băng (builder) và luật NPC của consumer. Nếu được
   duyệt, gộp vào v15 trước full suite để chỉ chạy suite một lần.
   - Cửa sổ dài thêm 3 m ở I01-S1, nên phải kiểm lại `WINDOW_TOO_SHORT` bằng builder offline trước.
2. **Cổng NPC trong probe 3 (chỉ chặn):** max |steer| NPC ≤ 0,4 và không có arc lùi > 0,05 m, từ đầu probe tới lúc dừng. Ngưỡng lấy
   nguyên từ io-v1.6 §2.4.
   - Phải viết thành addendum trước khi có frame probe 3 nào của I01.
   - Probe 3 chỉ thấy NPC tới t_clear hoặc TRIGGER + 2,3 s, nên đây là cái nhìn một phần.
3. **Giữ I01-S1** như I02-S2, chờ recipe sau.
