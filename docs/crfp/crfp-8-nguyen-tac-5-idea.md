# TÁM NGUYÊN TẮC VÀ NĂM IDEA NGHIÊN CỨU

> Duyệt ngày 09/10/2026. Tám nguyên tắc là điểm đối chiếu bất biến cho mọi quyết định trong dự án. Năm idea là đóng góp khoa học của paper.

---

## TÁM NGUYÊN TẮC

---

### Nguyên tắc 1: Tầm nhìn là end-to-end từ cảm biến

Ngày 08/10 đã quyết: paper này hướng đến một hệ thống lái xe tự hành hoàn chỉnh, đi từ cảm biến thô — camera, LiDAR — đến hành động lái, nhắm main track A*. Đây không phải là một ý tưởng đang cân nhắc mà là quyết định đã chốt, ghi trong G0.3 của khung 3-4 (lưu ý: G0.3 hiện chỉ có trong bản nháp khung, chưa có hàng tương ứng trong bảng Main — cần tạo M76 để ghi nhận).

Hệ quả của nguyên tắc này: mọi thứ chưa làm — nhánh VLM, perception, backbone — đều đang ở trạng thái **hoãn**, không phải đã bỏ, càng không phải chưa từng tồn tại. Tuyên bố đã bỏ tầm nhìn e2e là vi phạm nguyên tắc 1. Module hiện tại chỉ là Phase 1 — chứng minh lõi bằng cách rẻ nhất — để dọn đường cho Phase 2 là hệ thống hoàn chỉnh.

Nguyên tắc này là điểm đối chiếu cho mọi quyết định về hướng đi: không được tuyên bố bỏ tầm nhìn e2e. Tuy nhiên, được phép và phải nêu rõ phương án lùi (fallback) — ví dụ nếu Gate 2 không đạt thì paper sẽ thu hẹp thành dạng nào. Việc thảo luận trung thực về phương án lùi không vi phạm nguyên tắc này; chỉ việc từ bỏ tầm nhìn mới vi phạm. (Hiện tại phương án lùi cho Gate 2 chưa được định nghĩa — cần bổ sung.)

---

### Nguyên tắc 2: Năm idea nghiên cứu của dự án; quyết định kỹ thuật không được gọi là idea

Dự án này có 5 idea nghiên cứu — tức là 5 ý tưởng khoa học của người đề xuất:

Một là ý định có cấu trúc điều kiện theo mục tiêu. Hai là CRFP — học phản ứng của xe khác theo ý định của mình. Ba là biến thể VLM — encode ý định thành vector. Bốn là thiết kế teacher — phân biệt script, teacher VLM và student. Năm là confidence học từ sai số của chính model.

(Lưu ý: M34 trong sổ Main chỉ chốt hai lõi (a) và (b) dựa trên kill-search. M15 về intent-conditioned attention là cơ chế kiến trúc thuộc idea 2 (CRFP) — cầu nối giữa ý định có cấu trúc (idea 1) và dự đoán phản ứng. Phân loại idea ở đây phản ánh ý tưởng nghiên cứu, không phải kết luận về tính mới đã được kiểm chứng.)

Ngoài ra có những thứ quan trọng nhưng **không phải** idea: thiết kế 5 arm chỉ là bộ máy thí nghiệm để kiểm chứng idea 1. Việc đổi M55 sang comparative study chỉ là quyết định cách làm việc. Nguyên tắc sửa V5.1 chỉ là phương pháp luận đảm bảo trung thực.

Lưu ý về mức độ chứng minh: hiện tại chỉ idea 1 và 2 có thí nghiệm đang chạy (M21, Gate 1). Idea 3, 4, 5 là định hướng cho Phase 2 — chúng là idea thật của thiết kế nhưng chỉ nên vào danh sách "đóng góp" của paper khi đã có thí nghiệm riêng chứng minh. Liệt kê idea chưa có bằng chứng vào phần contribution sẽ vi phạm nguyên tắc 4.

Nguyên tắc này cấm việc đánh đồng hai loại. Khi viết paper, phần "contribution" chỉ được liệt kê những idea đã có bằng chứng. Khi reviewer hỏi "cái mới ở đâu", câu trả lời phải từ các idea này, không được lôi thiết kế 5 arm ra như thể đó là đóng góp khoa học.

---

### Nguyên tắc 3: "Chưa ai làm" chỉ có nghĩa là "chưa thấy trong tập đã đọc"

Đây là quy tắc [Đ] được đặt ra từ đầu và nó phải được tuân thủ tuyệt đối trong mọi phát biểu về tính mới.

Khi nói "chưa có paper nào làm paired intervention cho Δresponse", điều đó chỉ có nghĩa là trong số các paper team đã đọc — khoảng vài chục paper qua kill-search 15/16/17 và quét cộng đồng — chưa thấy ai làm. Nó không có nghĩa là trên toàn thế giới chưa ai làm, vì team chưa đọc hết thế giới.

Câu nói đúng và mạnh nhất mà sổ cho phép là: "không paper nào trong tập đã đọc trùng từ 2/3 vế của lõi (b) trở lên". Đây là phát biểu có bằng chứng — bằng chứng là danh sách paper đã đọc và bảng so sánh. Mọi cách diễn đạt vượt quá phạm vi này đều vi phạm nguyên tắc 3.

Nguyên tắc này bảo vệ dự án khỏi bị reviewer bắt bẻ: chỉ cần một reviewer tìm ra một paper chưa đọc mà trùng ý tưởng, toàn bộ claim "chưa ai làm" sẽ sụp. Nhưng claim "chưa thấy trong tập đã đọc gồm X, Y, Z paper" thì không ai bắt bẻ được vì nó trung thực về phạm vi.

---

### Nguyên tắc 4: Giả thuyết khác với tiền đề

"Idea mạnh hơn SOTA" hiện tại là **giả thuyết** — một niềm tin cần được kiểm chứng bằng thực nghiệm. Nó chưa phải là **tiền đề** — một điều đã được chứng minh mà ta được phép xây dựng tiếp trên đó.

Sự khác biệt này quyết định cách hành xử: với giả thuyết, ta thiết kế thí nghiệm để kiểm tra nó, ta chuẩn bị cho cả hai khả năng đúng và sai, ta không ra quyết định như thể nó đã đúng. Với tiền đề, ta được phép dùng nó làm nền tảng cho suy luận tiếp theo.

Hiện tại, không một quyết định nào trong dự án được phép dựa trên tiền đề "idea mạnh hơn SOTA". Mọi kế hoạch — từ chọn benchmark, đăng ký ngưỡng, đến viết paper — phải được thiết kế sao cho vẫn hợp lệ ngay cả khi kết quả cuối cùng cho thấy idea không hơn SOTA. Nếu D không thắng C ở Gate 1, dự án vẫn có đường đi (thu hẹp claim), vì ta chưa bao giờ đặt cược toàn bộ vào giả thuyết.

Nguyên tắc này cấm các phát biểu những câu như "vì idea mạnh nên chắc chắn sẽ..." — mọi dự đoán về kết quả đều phải đi kèm với "nếu số liệu ủng hộ".

---

### Nguyên tắc 5: Hai AI đồng ý không phải là bằng chứng

Đây là quy tắc được đặt ra ngày 04/10 cho việc làm việc với AI thứ hai, và nó áp dụng cho mọi AI tham gia.

Khi có sự đồng thuận rằng "idea này hay", sự đồng thuận đó **không** tạo ra bằng chứng. Bằng chứng chỉ đến từ dữ liệu: số liệu thực nghiệm, paper đã đọc, source code đã kiểm tra.

Nguyên tắc này có hai tác dụng. Một là chống lại sự tự ru ngủ — cảm giác "cả hai AI đều thấy đúng thì chắc là đúng" rất dễ chịu nhưng rất nguy hiểm trong nghiên cứu. Hai là buộc mọi claim phải truy về được nguồn gốc: khi một AI nói "X đúng", có thể kiểm tra "bằng chứng là gì" và AI đó phải chỉ ra được dữ liệu cụ thể, không được trả lời "vì Claude cũng nói vậy".

---

### Nguyên tắc 6: Không đổi ngưỡng sau khi thấy số

Mọi tiêu chí đánh giá — ngưỡng đạt/rớt, định nghĩa "thắng", cách tính metric — phải được khóa **trước** khi chạy thí nghiệm và nhìn thấy kết quả. Sau khi đã thấy số thì cấm sửa luật chơi.

Lý do: một khi đã thấy số, mọi điều chỉnh ngưỡng đều có nguy cơ — dù vô thức — là để cho kết quả đẹp hơn. Đây là một trong những lỗi phương pháp luận nghiêm trọng nhất trong khoa học thực nghiệm.

Ngoại lệ duy nhất, giới hạn chặt: chỉ áp dụng cho cổng thăm dò kiểu M21 (go/no-go, không phải bằng chứng trong bài). Nếu phát hiện ngưỡng cũ sai một cách khách quan ở cổng thăm dò (ví dụ ngưỡng 1e-6 m cho reversal là phi vật lý vì xe lắng 0,1 mm khi dừng), thì được phép đổi — nhưng phải **công khai** rằng tiêu chí mới được đặt sau khi thấy số, ghi rõ lý do, và tiêu chí mới phải được khóa cho mọi lần kiểm sau. Đúng như những gì đã làm với K1b ở V5.3: spec §3.2 ghi rõ K1b cũ không hợp lệ, §3.4 khóa K1b mới, §5 công khai việc đổi tiêu chí hai lần.

Với ngưỡng đã đóng băng ở Tag (Tag-B, Tag-C): **không có ngoại lệ**. Đã khóa là khóa.

Nguyên tắc này là bộ lọc cho mọi đề xuất thay đổi phương pháp đánh giá trong tương lai.

---

### Nguyên tắc 7: Phân biệt script, teacher VLM, student và đánh giá về quyền dùng thông tin đặc quyền

Ba vai trò khác nhau, ba quy định khác nhau — đã khóa trong thiết kế:

**Script** (máy sinh nhãn): ĐƯỢC dùng trạng thái đặc quyền từ simulator để sinh nhãn ý định. Đó chính là nhiệm vụ của nó — tạo ra ground truth để huấn luyện. Script cũng là trần chất lượng: teacher giỏi nhất cũng chỉ bằng script. M69 còn yêu cầu lý do mẫu lấy từ chính phép tính của script (khoảng cách xe trước, gap làn) — tức là dùng đặc trưng đặc quyền làm target train, không phải input lúc suy luận.

**Teacher VLM** (nếu train): chỉ được thấy observation (những gì cảm biến thấy) và goal (đích + deadline). Phải học cách suy luận ý định từ thông tin hạn chế như ngoài đời thật, không được xem đáp án đặc quyền. Hướng teacher có thông tin đặc quyền có tiền lệ trong ngành (kiểu "Learning by Cheating" — chưa kiểm chứng lại từ nguồn gốc) — nhưng trong thiết kế này, teacher VLM phải học cách không gian lận.

**Student và đánh giá:** chỉ observation + goal. Cấm tuyệt đối dùng thông tin đặc quyền lúc suy luận hoặc lúc chấm điểm.

Thứ tự sinh bắt buộc cho teacher VLM: **lý do trước, ý định sau**. Model phải nhìn cảnh, suy ra lý do ("làn trái thoáng, xe phía trước đang chậm lại"), rồi từ lý do đó mới quyết định ý định ("vượt"). Cấm làm ngược — tức là đã biết trước đáp án "vượt" rồi mới bịa lý do cho hợp lý. Được gọi đó là hậu nghiệm, là dối trá: lý do phải là nguyên nhân sinh ra quyết định, không phải đồ trang trí gắn thêm sau.

Nguyên tắc này định hình toàn bộ kiến trúc teacher và cách đánh giá nó. Mọi đề xuất thay đổi teacher trong tương lai đều phải đối chiếu: vai trò nào được phép dùng đặc quyền, vai trò nào không?

---

### Nguyên tắc 8: Đọc Gate 1 theo M62 đã khóa

Gate 1 không phải là nơi để kết luận "paper này có hơn SOTA không". Theo M62, Gate 1 chỉ trả lời hai câu hỏi hẹp:

Với lõi (a): **D có thắng C không?** — cả hai cùng nhìn trước, chỉ khác cách biểu diễn ý định (rời rạc có cấu trúc vs núm vô hướng). Ngưỡng thắng sẽ khóa ở Tag-C (M66, hiện vẫn Mở — giá trị chỉ có sau pilot M64). Nếu D thắng thì (a) sống. Nếu D xấp xỉ C thì (a) không chết mà **thu hẹp** thành claim khiêm tốn hơn: "điều kiện theo mục tiêu + nhìn trước giúp ích" — và cấm tuyệt đối việc đổi trọng tâm sang so sánh C vs B sau khi đã thấy số.

Với lõi (b): cần **hai điều kiện đồng thời**. Một là thí nghiệm 1b (M20) cho thấy phản ứng của NPC đổi theo ý định của ego một cách có hệ thống, theo ngưỡng sẽ khóa ở Tag-B. Hai là pilot M68 cho thấy predictor nhỏ học được mapping từ ý định sang phản ứng — biến thể 3 (có Δresponse) phải cho tín hiệu thắng hai biến thể còn lại. (Ngưỡng M68 và D2 hiện chưa có — cần đăng ký trước khi chạy.)

Và điều quan trọng nhất: chữ "sống" ở Gate 1 cho lõi (b) chỉ có nghĩa là **tiền đề đứng được** — tức là hiện tượng có thật, đáng để đầu tư tiếp. Nó không có nghĩa là đã chứng minh xong. Chứng minh đầy đủ về việc giám sát trên Δresponse có hiệu quả thuộc về M29, làm sau Gate 1.

Nguyên tắc này là điểm đối chiếu cho mọi diễn giải về kết quả Gate 1 trong tương lai. Bất kỳ ai — người thực hiện, Dũng, hay reviewer — muốn nói "Gate 1 chứng minh X" đều phải kiểm tra X có nằm trong phạm vi M62 cho phép không.

---

## NĂM IDEA NGHIÊN CỨU

---

### Idea 1: Ý định có cấu trúc điều kiện theo mục tiêu

Bạn bắt đầu từ một sự khó chịu rất cụ thể với cách giới xe tự lái hay nói chuyện. Người ta hay bảo "lái tốt" là "lái an toàn", "lái mượt", "lái nhanh" — nhưng những từ này không đo được, không viết thành code được. Bạn không thể bảo máy tính "hãy lái an toàn" vì máy không hiểu "an toàn" quy ra con số là gì.

Thay vào đó, cách tiếp cận là vứt bỏ toàn bộ cách nói mơ hồ và thay bằng một định nghĩa cứng như đá: mục tiêu của xe là một cặp gồm **đi đâu** và **đến khi nào**. Đi đâu là một tọa độ trên bản đồ. Đến khi nào là một mốc thời gian cụ thể — ví dụ 8 giờ 30 phút sáng phải có mặt. Không còn "nhanh" hay "chậm" trừu tượng nữa. Chỉ còn một câu hỏi duy nhất có thể trả lời bằng có hoặc không: xe có đến đúng nơi đúng giờ không.

Từ mục tiêu đó, xe phải ra quyết định liên tục trong lúc chạy. Các paper trước đây thường cho model output ra một con số vô hướng mà họ gọi là "k" — một cái núm vặn trừu tượng. Vấn đề là không ai giải thích được cái núm đó có nghĩa là gì trong thế giới thật. Khi xe xử lý sai, không thể biết là do núm vặn sai hay do yếu tố khác, vì núm vặn không có ngữ nghĩa để mà debug.

Bạn thay cái núm vô nghĩa đó bằng một cấu trúc ý định ba tầng, mỗi tầng đều nói bằng ngôn ngữ con người hiểu được. Tầng thứ nhất là dọc — xe định làm gì theo chiều tiến về phía trước: tăng tốc lên, giữ nguyên tốc độ hiện tại, giảm tốc xuống, hay dừng hẳn lại. Tầng thứ hai là ngang — xe định làm gì theo chiều làn đường: cứ đi thẳng trong làn hiện tại, nhập sang làn bên trái, nhập sang làn bên phải, rẽ trái ở ngã tư, rẽ phải ở ngã tư. Tầng thứ ba là macro — những hành động phức tạp kéo dài nhiều giây mà không thể gói gọn trong một quyết định đơn lẻ: vượt qua xe phía trước, nhường đường cho xe khác đi trước.

Điểm then chốt: một khi đã chọn ý định thì phải **giữ nó qua nhiều bước thời gian**. Giống hệt cách con người lái xe ngoài đời. Khi đã quyết định vượt, xe sẽ thực hiện cả một chuỗi hành động liên tục: nhìn gương chiếu hậu, bật xi nhan, hơi đánh lái sang làn bên cạnh, tăng tốc để vượt qua, rồi mới từ từ trở lại làn cũ. Không thể cứ mỗi 0.05 giây lại đổi ý một lần — đang vượt dở lại thôi không vượt nữa, rồi một giây sau lại quyết định vượt tiếp. Cái tính liên tục, cái sự cam kết với một quyết định trong nhiều giây, chính là thứ mà cái núm vô hướng không bao giờ thể hiện được.

Khi chứng minh ý tưởng này, không chọn con đường dễ. Con đường dễ là so sánh "có nhìn trước" với "không nhìn trước" — vì ai cũng biết nhìn trước thì hơn không nhìn, so như vậy thắng là chắc. Thay vào đó, so sánh hai thứ **cùng nhìn trước** với nhau. Một bên là D — dùng ý định rời rạc có cấu trúc được đề xuất. Một bên là C — dùng núm vô hướng như các paper trước. Cả hai đều được nhìn trước quãng đường như nhau, đều được tuning công bằng như nhau. Nếu trong điều kiện công bằng đó mà D vẫn thắng C, thì mới chứng minh được chính cái cấu trúc rời rạc này có giá trị nội tại — chứ không phải thắng nhờ yếu tố nào khác.

---

### Idea 2: CRFP — học cách xe khác sẽ phản ứng theo ý định của mình

Đây là idea tham vọng nhất và cũng là trung tâm của cả paper. Nó ra đời từ một tình huống quen thuộc: xe đang chạy trên đường và muốn chuyển sang làn bên trái, trong khi có một xe khác đang chạy song song bên cạnh. Cách xử lý tự nhiên là bật xi nhan, rồi hơi lấn sang trái một chút để "thăm dò". Nếu xe kia giảm tốc nhường đường thì chuyển làn; nếu xe kia tăng tốc ép lên thì thôi, chờ cơ hội khác. Tức là **quyết định phụ thuộc trực tiếp vào việc dự đoán người khác sẽ phản ứng ra sao với hành động của mình**.

Các mô hình xe tự lái trong tập đã đọc chưa làm được điều này một cách đầy đủ. Cách chúng dự đoán hành vi của xe khác là: nhìn vào quá khứ của xe đó trong vài giây vừa rồi, rồi ngoại suy ra tương lai — chưa tính đến việc chính hành động mà mình sắp làm sẽ khiến người ta thay đổi hành vi. Kết quả là hiện tượng "frozen robot" — xe tự lái đứng im không dám làm gì vì không mô hình hóa được tương tác hai chiều.

Đề xuất là học trực tiếp mối quan hệ hai chiều này. Với mỗi ý định cụ thể, xe khác sẽ phản ứng cụ thể ra sao. Không phải đoán chung chung kiểu "xe kia trong 5 giây tới sẽ đi đâu" — mà là một câu hỏi có điều kiện rất cụ thể: "nếu ý định là vượt ngay bây giờ thì xe bên cạnh sẽ nhường bao nhiêu mét; còn nếu ý định là đi thẳng thì nó sẽ giữ nguyên tốc độ". Cái "nếu... thì..." này chính là bản chất của tư duy phản thực — counterfactual thinking — mà con người dùng mỗi ngày khi lái xe nhưng các mô hình trong tập đã đọc chưa làm được đầy đủ.

Để có dữ liệu huấn luyện, phương pháp được dùng là paired intervention — can thiệp theo cặp. Trong tập paper đã đọc, chưa thấy ai kết hợp cả ba yếu tố: paired (cùng cảnh chạy hai lần chỉ đổi ý định), NPC có phản ứng thật (không bị đóng băng), và giám sát trực tiếp trên chênh lệch phản ứng. Purdue/Bosch (2608.11601) đã làm paired 3-arm nhưng NPC không phản ứng — ngược với ta. DTPP gần nhất với ý tưởng P(others | ego plan) nhưng không có paired intervention. Điểm mới nằm ở sự kết hợp cả ba, không phải từng yếu tố riêng lẻ.

Cách làm: lấy đúng một cảnh giao thông duy nhất. Chạy nó hai lần y hệt nhau về mọi mặt — vị trí các xe, thời tiết, đèn đường, mọi thứ đều giống nhau. Chỉ khác đúng một thứ duy nhất: lần chạy thứ nhất ép xe thực hiện ý định A; lần chạy thứ hai ép thực hiện ý định B. Rồi đo xem phản ứng của các xe khác chênh lệch nhau bao nhiêu giữa hai lần chạy. Cái chênh lệch này — được gọi là delta response — chính là tác động nhân quả thuần khiết của ý định, đã loại bỏ mọi yếu tố gây nhiễu khác vì mọi thứ khác đều được giữ nguyên.

Rồi thay vì để model tự mò mẫm học từ dữ liệu thô, thiết kế này **giám sát trực tiếp** trên chênh lệch phản ứng. Trong lúc huấn luyện, model được cho thấy: cùng một cảnh, khi ý định là vượt thì xe bên cạnh nhường 2 mét, khi ý định là đi thẳng thì giữ nguyên — và phải học quy luật này. Điểm khác biệt với các phương pháp chỉ dự đoán quỹ đạo chung chung trong tập đã đọc là việc giám sát trực tiếp trên tín hiệu tương tác.

Về mặt kiến trúc (M15): ý định điều kiện hóa attention của model theo maneuver chiến thuật — không phải command tĩnh như prior work (giả thuyết, cần ablation so sánh attention vs concat để kiểm chứng). Ý tưởng là khi ý định là "vượt", attention của model tập trung vào những vùng không gian và những xe liên quan đến việc vượt; khi ý định là "đi thẳng", attention chuyển sang vùng khác. Cơ chế này là cầu nối giữa ý định có cấu trúc (idea 1) và dự đoán phản ứng (idea 2): ý định không chỉ là nhãn đầu ra mà còn định hướng cách model nhìn cảnh để dự đoán phản ứng phù hợp. (Cite-and-distinguish cần làm: 2006.03347, 1909.05003, SSR 2409.18341 — prior work dùng command tĩnh.)

---

### Idea 3: VLM sinh ý định — encode thành vector giàu ngữ cảnh

Theo mục tiêu G0.3, VLM sinh ý định là thành phần chính của hệ thống e2e (không phải biến thể phụ). Idea này đề xuất một cách cụ thể để VLM biểu diễn ý định: encode thành vector.

Xuất phát từ sự không thỏa mãn với nhãn rời rạc khô khan. Nhãn kiểu "VUOT" hay "GIU_LAN" tuy rõ ràng nhưng vứt bỏ hết ngữ cảnh: cùng là "vượt" nhưng vượt trên cao tốc vắng khác hẳn vượt trong phố đông xe máy, mà nhãn thì giống nhau.

Đề xuất: encode ý định thành một **vector** vừa chứa ngữ cảnh vừa chứa ý định. Vector khi ở ngã tư đông đúc sẽ khác vector khi ở cao tốc vắng, dù ý định đều là "vượt". Từ vector giàu thông tin này mới decode ra quyết định.

(Lưu ý: dạng đầu ra cuối cùng của VLM trong hệ thống chính — nhãn rời rạc hay vector — vẫn Mở ở M46. Idea này mô tả phương án vector; phương án nhãn rời rạc cũng đang được cân nhắc.)

Idea này hiện được dùng làm bộ công cụ probing để kiểm tra model có hiểu ý định trong ngữ cảnh hay chỉ học vẹt nhãn, và đang hoãn sau Gate 1.

---

### Idea 4: Thiết kế teacher — phân biệt script, teacher VLM và student

Khi cần tạo dữ liệu huấn luyện, thiết kế này phân biệt ba vai trò với ba quy định khác nhau về quyền dùng thông tin đặc quyền.

**Script** được dùng trạng thái đặc quyền từ simulator để sinh nhãn ý định — đó chính là nhiệm vụ của nó: tạo ra ground truth. Script cũng là trần chất lượng, teacher giỏi nhất cũng chỉ bằng script.

**Teacher VLM** (nếu huấn luyện) chỉ được thấy observation và goal. Phải học cách suy luận ý định từ thông tin hạn chế như ngoài đời thật. Hướng teacher có thông tin đặc quyền có tiền lệ trong ngành (kiểu "Learning by Cheating" — chưa kiểm chứng lại từ nguồn gốc), nhưng trong thiết kế này teacher VLM không được phụ thuộc vào đặc quyền.

**Student và đánh giá** chỉ observation + goal, cấm tuyệt đối dùng đặc quyền.

Về thứ tự sinh dữ liệu cho teacher VLM: bắt buộc **lý do trước, ý định sau**. Model nhìn cảnh, suy ra lý do ("làn trái thoáng, xe phía trước đang chậm lại"), rồi từ đó mới quyết định ý định ("vượt"). Cấm làm ngược — đã biết đáp án rồi mới bịa lý do là giải thích hậu nghiệm. Lý do phải là nguyên nhân sinh ra quyết định, không phải đồ trang trí gắn thêm sau.

Về cách huấn luyện: sinh nhiều mẫu bằng script, lọc bằng rejection sampling, huấn luyện có giám sát (SFT). Không dùng reinforcement learning.

---

### Idea 5: Confidence học từ chính những lần thất bại của model

Ban đầu team gọi khái niệm này một cách nôm na là "độ quen" — model cảm thấy tình huống này có quen thuộc với mình không. Cách gọi đó quá mơ hồ, không đo được, không code được, nên được đổi toàn bộ khung khái niệm sang predictive uncertainty — độ bất định trong dự đoán — và chia nó ra làm hai loại rất rõ ràng, mỗi loại có nguyên nhân khác nhau và cách xử lý khác nhau.

Loại thứ nhất là do **ngữ cảnh lạ**. Model chưa bao giờ thấy cảnh này trong lúc huấn luyện. Ví dụ lúc train chỉ cho xem ngã tư 4 nhánh, giờ ra đường gặp ngã tư 6 nhánh lạ hoắc. Loại này thì giải pháp là thu thập thêm dữ liệu hoặc cảnh báo cho hệ thống dự phòng.

Loại thứ hai là do **bản chất của task vốn đã khó**. Dù đã cho model xem cả nghìn tình huống tương tự mà nó vẫn hay sai. Ví dụ điển hình là đoán ý định của xe máy trong phố đông ở Việt Nam — xe máy lạng lách bất quy tắc đến mức dù có bao nhiêu dữ liệu cũng khó đoán chính xác. Loại này thì không giải quyết bằng thêm dữ liệu được, mà phải thiết kế hệ thống chấp nhận sự bất định đó — ví dụ đi chậm lại, giữ khoảng cách xa hơn.

Nhưng điểm mấu chốt làm nên sự khác biệt của idea này nằm ở **nguồn gốc** của độ tự tin. Cái confidence này **không phải do thầy dán nhãn cho**. Không ai bảo model "tình huống này khó 8 điểm, tình huống kia dễ 3 điểm". Thay vào đó, nó được học từ chính lịch sử thất bại của model. Model tự nhìn lại quá khứ của mình: "những lần trước tao tự tin 90% mà sai bét nhè, vậy lần này gặp tình huống na ná như vậy thì tao chỉ dám tự tin 60% thôi". Đây là cách học rất giống con người — rút kinh nghiệm từ chính những lần mình vấp ngã, chứ không phải từ lời thầy dạy suông. Một đứa trẻ bị bỏng tay một lần sẽ tự biết sợ lửa, không cần ai phải giảng cho nó về nhiệt độ sôi của nước.
