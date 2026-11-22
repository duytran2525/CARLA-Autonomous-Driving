# M56 addendum Z: prepare lại O04-S3 và O08-S3 (chỗ lùi của NPC), 22/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** Duy [chat] 22/11/2026 trả lời câu hỏi của Claude:
- "Loại I": chọn "Ghi I = KHÔNG ĐẠT".
- "Loại O": chọn "Duyệt cả hai cảnh": kiểm offline trước, viết addendum, prepare lại O04-S3 và O08-S3; cảnh nào qua cổng
  thì chạy một A/B.

Addendum này được viết và commit **trước** mọi bước native của lần chạy này. Không cảnh nào trong hai cảnh từng có A/B,
nên P5 của chúng chưa dùng.

## 1. Loại I: KHÔNG ĐẠT theo M132

- Addendum Q (17/11) §1: I01-S1 không qua được G3 dưới mọi recipe nằm trong luật (vN 5 m/s theo spec, cổng κ buộc Dlc ≥ 17,4 m,
  ngưỡng 2,3 s giữ nguyên). Q §2 đặt trước luật dừng: cảnh hỏng ở cổng nào thì dừng ở đó, không chỉnh thêm. I05-S2 (probe 3, G1),
  I06-S2 và I07-S2 (G3 `SOURCE_CLEAR_LATE`), I08-S2 (cổng L `GAP_NOT_REALISED`) vì vậy là kết quả cuối.
- Loại I có 3 cảnh có cặp PASS (I02-S2, I03, I04), dưới 6. Theo M132, loại I không được chấm, tính là KHÔNG ĐẠT và giữ trong mẫu
  số. Không chọn successor I mới.
- Đính chính: câu hỏi Claude gửi Duy lúc đầu ghi rằng 5 cảnh I "chờ recipe G3 chưa viết". Câu đó dựa trên batch log 16/11 và bỏ
  qua addendum Q ngày 17/11. Claude đã báo lại, và Duy quyết lại dựa trên thông tin đúng.

## 2. O08-S3: chỗ lùi của NPC không đủ (lỗi khách quan của prepare)

Số liệu từ prepare r16d (`outputs/m56_v2_prepare_Town13_20261116T102058Z/M56-P-O08-S3/prepare.json`, gap gate
`outputs/m56_asel2_io_20261116T092756Z/gap-M56-P-O08-S3.log`):
- gap 55,694 m, vE 18,31 m/s, vN 2,5 m/s, road 302, làn NPC −1, `through`. Lần thử đầu: NPC xuất phát 23,60 m sau mốc quyết định,
  nên io-v1.4 c kéo dài run-in lên 406 m.
- Shift cần −63,527 m. Hàng route của NPC chỉ lùi `NPC_BACK_M` = 60 m từ điểm đoán ban đầu (rear cách mốc quyết định gap + L).
  `next(...)` trong `_prepare_o` vì vậy lặng lẽ lấy hàng đầu tiên. NPC xuất phát ở road-s 131,16, tức 0,6 m trước mốc quyết định
  (131,76), thay vì khoảng 4,1 m trước mốc. Cổng L đo gap thực 58,582 m (lệch 2,888 m > 0,5 m) → `GAP_NOT_REALISED`.
- Nguyên nhân nằm ở hằng số, không ở cảnh. Luật io-v1.4 c đòi NPC xuất phát ít nhất 5 m trước mốc quyết định, tức shift khoảng
  −(gap + L + 5). Với `NPC_BACK_M` = 60 m, mọi cảnh có gap lớn hơn khoảng 51 m đều bị kẹp. Luật cổng L ngày 15/11 (batch log, đặt
  trước mọi số của O04-S3 và O08-S3) cho phép đúng việc này: cảnh bị L chặn thì không tốn A/B, slot không bị ghi FAILED, và được
  prepare lại dưới cách đặt NPC đã sửa.

**Luật mới (recipe io-z):** `NPC_BACK_M` = max(60, gap + L + 15) m cho từng cảnh. Số 15 = 5 m của io-v1.4 c cộng 10 m dư cho sai
số động học của shift. Số này lấy từ luật io-v1.4 c, không khớp theo số của O08-S3. Với O08-S3: 55,694 + 3,705 + 15 = 74,40 m,
vượt |shift| 63,527 m. Cảnh có gap + L + 15 ≤ 60 dựng đúng các hàng như trước.

## 3. O04-S3: chỉ là lỗi hạ tầng, recipe giữ nguyên

- r16d: bốn probe ngắn kết thúc với `READINESS_NOT_REACHED`, trong episode có giới hạn ready 15 s của runner. Run-in được kéo lên
  171 m theo io-v1.4 c. Hai probe dài (io-v1.5, giới hạn ready 60 s) đều dừng `TICK_ERROR` ở đúng frame 994. Sau đó prepare treo
  cho tới khi bị `timeout 2400` của hàng đợi giết, không có sự kiện SCENE.
- Lần đó chạy trước technical fix 4 (17/11, `9f49bf7`, timeout RPC 300 s sau khi nạp Town12/13). Fix 4 sinh ra từ đúng loại lỗi
  này: Town13 stream tile và chặn một RPC hơn 60 s khi RAM căng. Cùng một frame ở cả hai probe khớp với việc nạp tile theo vị trí
  xe (nhận định của Claude).
- Kiểm offline (`native-io-npcback-offline.py`, bản đồ OpenDRIVE Town13, không server): gap 32,955 m nên `NPC_BACK_M` vẫn 60 m.
  Hàng NPC lùi tới 23,34 m trước mốc quyết định, đủ cho io-v1.4 c. Recipe của O04-S3 vì vậy không đổi.
- Với O08-S3, công cụ offline dừng ở `geometry` (`CATALOG_ROUTE_NOT_ON_SITE_LANE`, road 185): bản đồ offline chiếu điểm catalog
  lên road nối trước road 302, còn server thì không. Vì vậy mục 2 dựa trên hình học mà server đã ghi: hàng NPC mới bắt đầu ở road-s
  khoảng 116,8 (131,76 + 55,694 + 3,705 − 74,40) trên road 302 / làn −1. Đoạn này nằm trong phần road 302 / làn −1 mà route EGO của chính prepare đó đã dựng
  (road 185 → 302 từ s ≈ 0).

## 4. Cách làm

- `native-io-prepare-z.py`: nạp `native-io-prepare-v16.py` (io-v1.5 + io-v1.6) làm module, không sửa file nào đã đóng băng. Đặt
  `NPC_BACK_M` theo mục 2 trước mỗi `_prepare_o`, rồi trả về 60 sau đó. prepare.json ghi thêm `npc_back_m` và `recipe_io_z`.
  Self-test: `--selftest`.
- `run-asel2-io-z.sh`: bản sao của `run-asel2-io-v16.sh`, chỉ khác bốn chỗ: script prepare, mức commit headroom mặc định 32 GB,
  trần thời gian prepare 3600 s (trước là 2400 s; đây chỉ là trần chờ, giống fix 4), và chuỗi thẩm quyền.
- `run-asel2-oz-queue.sh`: product m56-v15 `036688b` + spawn tilt, replacements 1..9, giống như `run-asel2-v15o-queue.sh`.
  Thứ tự: base revision → prepare → cổng L → compile → self-check → cổng κ → **một** A/B mỗi cảnh (P5) → cặp dưới consumer v15
  và v10.
- **Luật dừng:** mỗi cảnh một lần prepare. Hỏng ở cổng nào thì dừng ở đó và ghi lại, không chỉnh thêm, không prepare lần nữa nếu
  chưa có quyết định của Duy. Ngưỡng và cổng (L 0,5 m, κ, ready 14 s, G2) giữ nguyên.

## 5. Báo cáo

- Kết quả của từng cặp báo dưới consumer v15 (luật sau số đã công bố 15/11) và v10, giống các cảnh O anh em (O05-S1, O07-S2).
- Loại O có 5 cảnh có cặp PASS (O01, O02, O03, O05-S1, O07-S2). Chỉ cần một trong hai cảnh PASS là O đạt 6 và được chấm.
- Dù O đạt hay không, sàn M132 vẫn không đạt: loại M có 0 cảnh và loại I có 3 cảnh.
