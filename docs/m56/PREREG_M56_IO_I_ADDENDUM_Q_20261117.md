# M56 addendum Q: I01-S1 đóng ở G3; chạy các successor I05-S2…I08-S2, 17/11/2026

**Nhãn:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

**Thẩm quyền:** recipe I mới được người dùng duyệt [chat] 15/11/2026 ("tôi duyệt recipe mới bạn hãy làm đi"; phạm vi gồm I01,
I02, I05–I08). Người dùng phiên này [chat] 17/11/2026: "tiếp tục hoàn thành m56". Claude quyết dưới ủy quyền của Duy.
Viết **trước** mọi bước native của I05-S2…I08-S2.

## 1. I01-S1: BLOCKED_FIXTURE ở G3, không sửa thêm

- r17c (io-i-v1.3 a/b + product m56-v17): prepare PREPARED ngay lần đầu, cổng L và κ đạt. Probe 3 trượt `SOURCE_CLEAR_LATE` (G3,
  t_clear − TRIGGER ≤ 2,3 s) và `SOURCE_CLEAR_EVENT_LATE`. Không A/B, không tiêu P5.
- Đo offline (biên thân NPC so với mặt cắt `I_SOURCE_BOUNDARY`, hình học của product): TRIGGER khi đỉnh đầu tiên qua biên;
  đỉnh cuối còn −0,075 m lúc +2,35 s, ngoại suy qua 0 ở khoảng +2,45 s. I04 với cùng cách đo: qua 0 ở +1,45 s.
- Nguyên nhân là động học, không phải recipe đặt NPC. TRIGGER bám chuyển động thật của NPC, nên dời điểm bắt đầu đổi làn chỉ dời
  TRIGGER theo. Thời gian cắt qua biên = bề rộng thân xe (cộng góc lệch) / vận tốc ngang. Vận tốc ngang do vN = 5 m/s (spec,
  18 km/h) và Dlc = 18 m quyết định. Dlc không giảm được: κ quintic ≈ 5,77·3,25/Dlc² vượt cổng 0,0624 khi Dlc < 17,4 m
  (addendum J); ở 17,4 m thời gian chỉ giảm khoảng 3 %, vẫn trượt.
- **Kết luận:** I01-S1 không đạt G3 dưới mọi recipe nằm trong luật (spec vN, cổng κ, ngưỡng 2,3 s đều giữ). Ghi BLOCKED_FIXTURE
  cuối cùng. Không nới G3 (sẽ là luật sau số).

## 2. I05-S2, I06-S2, I07-S2, I08-S2

- Các cảnh này là successor B3 đã nhận ở replacement 9 (15/11, `m56_fill_v4_replace9_c4_20261115.json`) và có trong revision
  từ đó, nhưng bị giữ lại chờ recipe mốc đổi làn của B. Recipe đó nay đã có: addendum N (B giữ làn tới SOURCE_CLEAR rồi đổi, G5),
  addendum O (product m56-v17), addendum P (io-i-v1.3 b).
- I08-S2 trước đây được rút khỏi danh sách giữ vì cùng dạng với I02-S2. I02-S2 nay đã PASS dưới v17, nên I08-S2 chạy cùng đợt.
- **Quy trình:** y như r17c (`run-asel2-io-i17q.sh`, bản sao của `run-asel2-io-i17.sh`, chỉ đổi chuỗi thẩm quyền và thêm cặp
  dưới m56-v13). Prepare io-i-v1.3 a/b → cổng gap L → compile → cổng κ → probe 3 (G1/G2/G3/G5) → **một** A/B mỗi cảnh (P5).
  Hỏng ở cổng nào thì cảnh đó dừng ở đó, không chỉnh thêm.
- **Báo kết quả** dưới m56-v17, m56-v16 (luật cũ của O), m56-v15 (luật cũ của N) và m56-v13 (luật Dlc cũ = 3·vE, theo quyết
  định 15/11: kết quả I05–I07 phải báo dưới cả luật cũ lẫn luật mới).
