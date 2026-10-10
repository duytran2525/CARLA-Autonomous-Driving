Đây là danh sách 21 câu hỏi cần trả lời khi theo đề xuất "VLM sinh vector latent" cho biểu diễn ý định, tổng hợp ngày 04/10/2026.

Mỗi câu giữ nguyên văn bản gốc lúc đặt ra, kèm trạng thái cập nhật cùng ngày — nhiều câu đã chốt hướng hoặc hoãn sau Gate 1 theo quyết định: killer experiment dùng nhãn rời rạc do script sinh, VLM/vector để sau.

Nhóm A — Về mục 1 (goal):

1. Goal gồm những gì? (đích + nhanh/chậm theo bạn, hay thêm deadline như AI đề xuất?)
→ Trạng thái: ĐÃ CHỐT — goal = (đích từ route, deadline); loại "nhanh/chậm" khỏi định nghĩa goal.
2. Đưa goal dạng số (đích, deadline, thời gian còn lại) vào VLM bằng cách nào — token hay embedding số? VLM có xử lý được suy luận số/thời gian không?
→ Trạng thái: ĐANG MỞ — bắt đầu bằng token (rẻ); có thêm option thứ ba: tính sẵn đặc trưng (slack time) rồi đưa vào bằng embedding.
3. Nếu VLM lờ goal thì lõi (a) mất nền — phát hiện bằng cách nào? (ablation tắt goal)
→ Trạng thái: ĐÃ CHỐT hướng — thêm experiment 0 (goal-sensitivity); bản rẻ: VLM frozen + decoder head nhỏ train trên nhãn script; là việc song song, không thuộc Gate 1.

Nhóm B — Về "kiểm tra quen thuộc":

4. Định nghĩa "quen" thế nào, ngưỡng ở đâu, calibration ra sao? (mục 16)
→ Trạng thái: ĐANG MỞ — cần literature (chat "Paper: VLM intention & World4Drive" đang chạy).
5. VLM pretrain trên web thì "quen" theo chuẩn web — xử lý domain gap với dữ liệu lái xe thế nào?
→ Trạng thái: ĐÃ THỐNG NHẤT một phần — fine-tune theo hướng driving là đúng; nhưng "quen so với cái gì" (tập train) vẫn còn, và có nguy cơ overconfidence sau fine-tune.
6. Không quen thì làm gì cụ thể? (mục 10) — nhánh fallback chưa có
→ Trạng thái: ĐÃ CHỐT hướng — chuyển sang ý định an toàn; cần định nghĩa tập safe luôn khả thi.
7. Thực chất đây là confidence đổi tên → các câu về đo lường và phân vai (mục 3, 11) vẫn phải trả lời, không né được
→ Trạng thái: ĐÃ ĐỒNG Ý.

Nhóm C — Về vector:

8. Bản chất: ý định là vector, hay là nhãn mà vector chỉ là đường dẫn tới? (phải chọn một)
→ Trạng thái: ĐÃ CHỐT — vector là đường dẫn, nhãn là ý định được thực thi; mọi thí nghiệm nhắm vào nhãn.
9. Vector học từ supervision nào? Nhãn Teacher → dính rò rỉ tương lai (mục 9); học gián tiếp qua loss quỹ đạo → có còn mang nghĩa "ý định"?
→ Trạng thái: ĐANG MỞ — cần literature về tradeoff các cách huấn luyện.
10. Chứng minh vector mang ý định chứ không phải feature cảnh: cần probing + can thiệp nhân quả
→ Trạng thái: ĐÃ CHỐT cần experiment; cách thức ĐANG MỞ — cần literature.
11. Tách ngữ cảnh khỏi ý định trong vector thế nào để ablation sạch? (entanglement — chưa có lời giải)
→ Trạng thái: HOÃN sau Gate 1 (bản học) — killer experiment dùng script nên không tồn tại vector fuse để tách.
12. Bộ sinh quỹ đạo có lờ vector đi không? Cần thí nghiệm can thiệp: nhiễu vector → quỹ đạo có đổi đúng hướng?
→ Trạng thái: HOÃN sau Gate 1 — cần paired data (cùng cảnh, 2 ý định, 2 quỹ đạo) + bottleneck nhãn; pipeline dữ liệu dùng chung với lõi (b).

Nhóm D — Về giải mã ra ý định phức:

13. Tập ý định cố định hay cho tổ hợp? Đồng thời [Chậm lại]+[Nhập làn trái] được không? Xung đột ([Tăng tốc]+[Chậm lại]) ai giải quyết?
→ Trạng thái: ĐÃ CHỐT hướng — tổ hợp theo trục dọc × trục ngang (mỗi trục một), xung đột nội-trục triệt tiêu theo cấu trúc (bảng cặp hợp lệ trong spec v5.1).
14. Kỹ thuật rời rạc hóa: Gumbel-softmax hay codebook? Sập codebook thì sao? Tín hiệu nào là chính?
→ Trạng thái: ĐÃ GIẢI QUYẾT cho bản script (classification + cross-entropy là đủ); chỉ quan trọng khi học ý định không nhãn → hoãn sau Gate 1 nếu cần.
15. Giữ ý định qua nhiều bước với vector liên tục: luật giữ là gì? (ngưỡng khoảng cách, trung bình trượt)
→ Trạng thái: ĐÃ CHỐT khung — output trước làm input sau + confidence decay; điều kiện "vẫn thỏa" đo được + biên δ/K đã đưa vào spec v5.1.

Nhóm E — Về thí nghiệm và tính mới:

16. 1a "bật/tắt goal" với vector latent thì thao tác sạch là gì?
→ Trạng thái: HOÃN sau Gate 1 — killer experiment dùng script: nhánh goal-off = w_goal = 0, sạch theo cấu trúc.
17. Paired intervention cho lõi (b): chọn 2 điểm vector nào là 2 ý định khác nhau? Gán nhãn cặp can thiệp ra sao?
→ Trạng thái: HOÃN sau Gate 1 — killer experiment: 2 nhãn script (không cần gán nhãn tay), đo phản ứng mọi xe trong bán kính.
18. World4Drive đã có latent intention encoder → điểm mới của bạn phải là: điều kiện hóa theo mục tiêu + tồn tại qua các bước + vai trò trong response field. Mỗi điểm cần bằng chứng riêng
→ Trạng thái: ĐANG MỞ — cần đọc sâu World4Drive (chat literature đang chạy).
19. Bài test tổng quát hóa: context/cách diễn đạt chưa thấy lúc train → ý định sinh ra có đúng không?
→ Trạng thái: ĐÃ CHỐT nguyên tắc — held-out contexts; cấm finetune trên tập test (contamination); chi tiết sau.

Nhóm F — Về hiệu năng:

20. VLM forward pass có kịp real-time? (mục 25) — giảm nhẹ nhờ chạy tần số thấp + persistence, nhưng phải thiết kế rõ 2 tần số
→ Trạng thái: ĐANG MỞ — cần paper/experiment; rủi ro đã chấp nhận (không model nào đủ → chấp nhận/chỉnh idea).
21. Không có CoT thì cơ chế "suy luận chậm khi tự tin thấp" (mục 10) thay bằng gì?
→ Trạng thái: ĐÃ CHỐT hướng — operationalize "nghĩ nhiều hơn" (vd: sample K ứng viên, chọn an toàn nhất) + tách 2 tín hiệu low-conf (ngữ cảnh lạ vs task phức tạp) + deadline mềm có sàn + đo tỷ lệ trễ hạn; chi tiết chưa khóa.
