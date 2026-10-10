# M65 — Đọc sâu 2 paper counterfactual + DriveWorld-VLA, kiểm tra cả hai lõi

Ngày đọc: 04/10/2026. Đọc FULL TEXT từ PDF gốc (không dùng abstract). File: `~/workspace/paper_verify/`.

---

## 1. Xác minh thông tin paper (từ trong PDF)

| Paper | Tiêu đề (nguyên văn) | Tác giả | Ngày / arXiv ID | Venue |
|---|---|---|---|---|
| P1 | *DriveWorld-VLA: Unified Latent-Space World Modeling with Vision–Language–Action for Autonomous Driving* | Feiyang Jia, Lin Liu, Ziying Song, Caiyan Jia, Hangjun Ye, Xiaoshuai Hao, Long Chen (Beijing Jiaotong Univ. + Xiaomi EV) | 6 Feb 2026 / arXiv:2602.06521v1 [cs.CV] | Chưa có (arXiv preprint) |
| P2 | *How Can Driving World Models Do Counterfactual Prediction?* | Jiaru Zhang, Can Cui, Yi Xu, Xin Ye, Ruqi Zhang, Ziran Wang (Purdue Univ. + Bosch Center for AI) | 12 Aug 2026 / arXiv:2608.11601v1 [cs.CV] | Chưa có (arXiv preprint) |
| P3 (đối chiếu) | *DriveZero: End-to-End Driving Beyond Human Demonstrations* | Xiaomi EV, AD & Robotics L3 Team | 5 Sep 2026 / arXiv:2609.06055v1 [cs.CV] | Technical Report (ghi rõ trong paper, tr.1) |

File PDF: `driveworld-vla.pdf`, `counterfactual-prediction.pdf`, `drivezero.pdf` (P3 đã có sẵn, đọc lại full text để kiểm tra trích dẫn).

---

## 2. Tóm tắt từng paper (từ full text)

### P1 — DriveWorld-VLA (§1, Fig.1, §4)
Thống nhất VLA + world model trong **không gian latent chung** (LLM hidden states làm cầu nối). Ba trụ cột: (1) Feature-Level Sharing; (2) Action-Conditioned "What-If" Reasoning — dùng Diffusion Transformer rollout nhiều candidate actions, đánh giá hậu quả dài hạn; (3) huấn luyện 3 giai đoạn. Stage 3: reward học được R chấm điểm từng quỹ đạo ứng viên, loss action có trọng số reward `L′act = r̂·||A′−A||²` (Eq. 11, tr.5); reward GT lấy bằng **chạy quỹ đạo trong simulator + đánh giá online** (tr.5: "ground-truth rewards obtained by executing the predicted trajectories in a simulator") — tức **scalar reward**, không phải Δresponse. Kết quả: **91.3 PDMS** (NAVSIM-v1), **86.8 EPDMS** (NAVSIM-v2), **0.16** collision rate 3s trên nuScenes (abstract + Fig.1d, tr.1). Chi phí train: ~120h trên 8×H20 (NAVSIM), ~93h trên 8×H20 (nuScenes) (§4, tr.5).

### P2 — Counterfactual Prediction, Purdue/Bosch (§1–§6)
Luận điểm lý thuyết: dự đoán "trực tiếp" (condition trên shared history + action thay thế) **không phải** counterfactual prediction theo thang Pearl — thiếu bước **abduction** (dùng factual continuation để suy ra trạng thái thế giới đã thực hiện) (§3, tr.2–3). Xây benchmark CARLA đối chứng: mỗi case gồm factual log (video RGB + ego trajectory đã chạy) + target trajectory; chạy lại cùng world với action thay thế → counterfactual GT. **Giao thức 3 arm** (§5, tr.6): (i) factual (F, a_obs) — chạy đúng log, sự kiện xảy ra; (ii) counterfactual GT (P) — chạy target trajectory a′, phần còn lại của world replay y hệt; (iii) null (U) — chạy a′ nhưng sự kiện không bao giờ kích hoạt. **186 case** từ 72 placements, 3 towns; 25 frames @10fps, 576×320; 15-frame history chung + 10-frame prediction window. Kết quả (Tab.2, §6.3, tr.9): direct prediction B có recovered fraction **0.23–0.45** (< 0.5, tức gần null hơn là gần counterfactual GT); phương pháp của họ (transport + completion, training-free) nâng lên **0.64–0.70**; LPIPS Vista **0.423 → 0.169**, DrivingWorld **0.291 → 0.211**. Hai world model được đánh giá: Vista (diffusion) và DrivingWorld (autoregressive video GPT) (§6, tr.6).

**Điểm then chốt cho lõi (b)** — paper này DÙNG AGENT SCRIPT SẴN, KHÔNG PHẢN ỨNG:
- §3.1 "Scope" (tr.3): *"the alternative ego action alters the camera viewpoint **while the surrounding environment follows predetermined behaviors**"*; *"driver perception and reaction times are themselves on the order of a second [Green, 2000], **leaving surrounding agents little time to respond**."*
- §5 (tr.6): *"Both follow **predefined open-loop motion scripts**."*
- §Limitations (tr.17): *"The benchmark **scripts the surrounding agents**, which is what makes the matched counterfactual reference obtainable... A natural next step is to... **extend the protocol to closed-loop scenario suites with reactive agents** [Jia et al., 2024, Caesar et al., 2021]."*

Ngoài ra paper này **không supervise trên Δresponse**: nó đo độ trung thực của *video dự đoán* (giữ được sự kiện của episode không), không train planner bằng supervision trên chênh lệch phản ứng.

### P3 — DriveZero (đọc lại full text để kiểm tra trích dẫn)
Hệ thống 3 tầng: DriveRL (teacher đặc quyền train PPO trong "mixed-agent interactive worlds" dựng từ nuPlan logs) → DriveVFM (perception) → DriveZero (planner camera-only chưng cất từ teacher bằng winner-takes-all). Trích dẫn cần kiểm (abstract, tr.1): *"The **goal-conditioned teacher** can moreover be queried under **augmented driving intents**, yielding diverse, goal-consistent supervision that logged data cannot provide."* (§2.3 "Goal augmentation", tr.3): *"augmenting the **route intent** and its associated navigation command before generating teacher supervision... expands each logged scene into **multiple valid supervision targets**."*

Bản chất "goal" ở đây (§2.1, tr.2): *"goal points Gt in the ego frame... specify the **positions the ego vehicle should reach in the near future**"* — biểu diễn 2 điểm từ vị trí tương lai trong log. **Không có deadline.** "Intent" = route intent / navigation command (biến thể lộ trình), **không phải nhãn ý định rời rạc có cấu trúc**. Mục đích của "augmented intents" là **data augmentation cho distillation** (đa dạng hóa supervision), không phải luận điểm về tầng quyết định. "Mixed-agent" (§2.1, tr.2–3): background actors theo log replay / rule-based / learned provider + self-play — tức môi trường train RL có tính tương tác, nhưng supervision là **PPO với scalar reward** ("hard safety events, goal arrival", tr.2) và **trajectory distillation**, không có paired intervention, không có Δresponse. Số liệu: DriveRL 93.57 mean nuPlan (cả reactive và non-reactive mode); DriveZero **95.3 PDMS** navtest (vượt human 94.8), **57.1 EPDMS** navhard, **46.6 HD-Score** HUGSIM (abstract, tr.1).

---

## 3. Kiểm tra lõi (a): goal = (đích, deadline) → ý định rời rạc có cấu trúc

| Paper | Có làm đúng ý (a)? | Lý do |
|---|---|---|
| P1 DriveWorld-VLA | **KHÔNG** | Không có khái niệm goal theo nghĩa của ta (chỉ dùng "goal" nghĩa thông thường: "the goal is to improve safety"); không có intention; không có deadline (grep toàn văn). |
| P2 Purdue/Bosch | **KHÔNG** | Không có goal-conditioning; query là target trajectory cho bài toán video prediction. |
| P3 DriveZero | **GẦN NHƯNG KHÔNG** | Teacher có goal-conditioned và query được dưới "augmented driving intents" — gần về *tinh thần*. Nhưng: (1) goal = waypoint ngắn hạn, **không có deadline**; (2) intent = biến thể lộ trình liên tục, **không phải nhãn rời rạc có cấu trúc** (dọc×ngang+macro); (3) mục đích là **augmentation cho distillation**, không phải luận điểm "ý định có cấu trúc thắng núm vô hướng". |

**Verdict lõi (a): SỐNG.** Không paper nào làm đúng ý (a). Prior art gần nhất bắt buộc cite-and-distinguish: **DriveZero** — teacher goal-conditioned query được dưới nhiều intent (abstract tr.1; §2.3 tr.3), nhưng goal của họ là waypoint ngắn hạn không deadline, intent là biến thể lộ trình cho mục đích augmentation, không phải tầng quyết định ý định rời rạc.

---

## 4. Kiểm tra lõi (b): paired intervention + agent PHẢN ỨNG + supervision trực tiếp trên Δresponse

| Paper | Paired intervention? | Agent phản ứng? | Supervision trên Δresponse? |
|---|---|---|---|
| P1 DriveWorld-VLA | Không (what-if imagination + scalar reward, không paired) | Không (đánh giá trên NAVSIM log-based; reward từ sim execution) | **Không** — loss là reward-weighted imitation `L′act`, reward là scalar |
| P2 Purdue/Bosch | **Có** — giao thức 3 arm factual/counterfactual/null (§5, tr.6) | **KHÔNG** — agent theo "predefined open-loop motion scripts" (§5, tr.6); Scope (tr.3) và Limitations (tr.17) nói rõ; reactive agents là **future work** | **Không** — đo fidelity của video dự đoán, không supervise planner trên Δresponse |
| P3 DriveZero | Không (query đa intent cho augmentation, không đo chênh lệch phản ứng) | Một phần — mixed-agent worlds (log replay/rule-based/learned + self-play) cho train RL, nhưng không có protocol paired | **Không** — supervision là trajectory distillation + PPO scalar reward |

**Verdict lõi (b): SỐNG.** Không paper nào làm đúng tổ hợp cả ba yếu tố. Tinh chỉnh so với ghi nhận cũ ở M28 ("DriveZero giết một phần lõi (b)"): sau khi đọc full text, phần DriveZero "chạm" chỉ là *môi trường interactive + teacher closed-loop* — không có paired intervention, không có Δresponse supervision — nên **không giết luận điểm (b)**; giữ ở mức cite-and-distinguish.

**Prior art gần nhất bắt buộc cite-and-distinguish cho (b):**
1. **Purdue/Bosch (P2)** — tiền lệ trực tiếp cho *giao thức paired* (3 arm factual/counterfactual/null, 186 case CARLA), nhưng open-loop/non-reactive và không Δresponse. Đặc biệt: chính paper này ở Limitations (tr.17) **kêu gọi** mở rộng sang "closed-loop scenario suites with reactive agents" — 1b của ta làm đúng việc đó. Trích limitation này làm động lực trong bài.
2. **DriveWorld-VLA (P1)** — tiền lệ cho "what-if consequence-aware" (imagination + chọn ứng viên), nhưng bằng scalar reward chứ không phải Δresponse có cấu trúc. Distinguish: họ đánh giá hậu quả bằng điểm vô hướng; ta supervise trực tiếp trên chênh lệch phản ứng của xe khác.
3. **DriveZero (P3)** — tiền lệ cho teacher goal-conditioned trong môi trường interactive, nhưng supervision là distillation + scalar RL reward.

---

## 5. Trả lời câu hỏi về trích dẫn DriveZero

*"The goal-conditioned teacher can moreover be queried under augmented driving intents"* (abstract, tr.1; §2.3, tr.3):

- **Chạm lõi (a)?** Có, về tinh thần: teacher điều kiện theo goal và có thể query dưới nhiều intent — cùng họ ý tưởng "goal điều kiện cho ý định". Nhưng **không chạm luận điểm**: goal ≠ (đích, deadline), intent ≠ nhãn rời rạc có cấu trúc, và không có so sánh "cấu trúc vs núm vô hướng".
- **Chạm lõi (b)?** Yếu: "cùng scene query nhiều intent" giống hình thức của paired intervention, nhưng mục đích là augmentation (đa dạng supervision) chứ không phải đo/can thiệp phản ứng; không có Δresponse.
- **Kết luận:** trích dẫn này **gần (a) hơn (b)** về mặt ý tưởng, nhưng không giết lõi nào. Dùng làm cite-and-distinguish cho (a) (như mục 3), và ghi nhận cho (b) rằng "query đa intent trên cùng scene" là kỹ thuật đã có tiền lệ — cái mới của ta là *đo và supervise trên Δresponse của agent phản ứng*.

---

## 6. Hệ quả cho M34 (chọn lõi)

Cả hai lõi **SỐNG** sau M65. Không paper nào trong 3 paper đọc sâu làm đúng ý (a) hay ý (b). Điều chỉnh nhỏ so với M28: DriveZero không "giết một phần lõi (b)" theo nghĩa đe dọa luận điểm — phần overlap (interactive teacher training) không chứa paired intervention hay Δresponse supervision. Giữ nguyên quyết định M34 (chứng minh cả hai lõi), bổ sung 3 cite-and-distinguish bắt buộc vào danh sách trích dẫn: DriveZero (cho a), Purdue/Bosch + DriveWorld-VLA (cho b).

---

## 7. Hệ quả cho thiết kế 1b / M20 — kỹ thuật đáng mượn từ P2

P2 là paper hữu ích nhất cho thiết kế 1b (killer experiment: ép ý định A vs B trên cùng scene+seed, đo phản ứng xe khác):

1. **Giao thức 3 arm** (§5, tr.6) — mượn trực tiếp: (i) factual: chạy ý định mặc định; (ii) counterfactual: ép ý định A (rồi B); (iii) **null**: chạy cùng scene nhưng *không ép ý định* (hoặc ép ý định trung tính) để có baseline "phản ứng khi không can thiệp". Arm null giúp tách tác động của can thiệp khỏi động lực nội tại của scene — P2 dùng null để đo "prediction gần GT hay gần null" (recovered fraction, §6.3); ta dùng tương tự để đo "phản ứng đổi do ý định hay do scene tự diễn biến".
2. **Kỷ luật matched-pair** (§5): shared history + chỉ diverge trong cửa sổ can thiệp. Ánh xạ sang 1b: cùng scene + cùng seed, chỉ khác ý định bị ép, đo trong cửa sổ T đã khóa ở spec.
3. **Metric dạng "recovered fraction"** (§6.3, Tab.2, tr.9): thay vì chỉ báo "có/không khác biệt", định nghĩa chỉ số liên tục so khoảng cách tới GT-can-thiệp vs tới null. Gợi ý cho M22a/M35b: metric 1b nên là dạng *độ phân biệt* (discriminability) chứ không chỉ nhị phân.
4. **Dùng chính Limitation của P2 làm động lực** (tr.17): họ thừa nhận benchmark script sẵn agent và kêu gọi reactive-agent extension — 1b của ta (agent phản ứng + paired intervention) là đúng phần mở rộng đó. Trích dẫn này trong bài để định vị đóng góp.
5. **Cảnh báo từ P2:** hiệu ứng can thiệp của họ đo trên horizon ngắn (~1s, §3.1 Scope) vì "reaction times are on the order of a second". Cho 1b: cửa sổ đo T phải đủ dài để phản ứng của agent kịp biểu hiện — cần pilot (M54) xác nhận T, không mặc định.

Từ P1/P3 cho 1b: ít trực tiếp hơn. P1 nhắc rằng scalar-reward-from-sim là chuẩn đánh giá (ta đi xa hơn bằng Δresponse có cấu trúc). P3 cho tiền lệ "cùng scene, query đa intent" — củng cố tính hợp lệ của thiết kế ép ý định A/B trên cùng scene.

---

## 8. Bảng verdict tổng hợp

| Lõi | Verdict | Prior art gần nhất (cite-and-distinguish bắt buộc) |
|---|---|---|
| (a) goal=(đích, deadline) → ý định rời rạc có cấu trúc | **SỐNG** | DriveZero — teacher goal-conditioned + augmented intents, nhưng goal là waypoint ngắn hạn (không deadline), intent là biến thể lộ trình cho augmentation, không phải tầng quyết định |
| (b) paired intervention + agent phản ứng + supervision Δresponse | **SỐNG** | Purdue/Bosch — giao thức 3-arm paired nhưng agent non-reactive (tự nhận ở Limitations) và không Δresponse; DriveWorld-VLA — what-if bằng scalar reward; DriveZero — interactive teacher nhưng supervision là distillation + PPO scalar |

Không phát hiện paper nào làm đúng ý (a) hay (b) trong 3 paper đọc sâu. Mọi số liệu trên đều trích từ full text PDF gốc; cả 3 paper đều là arXiv preprint/technical report, chưa có venue xuất bản — không trích venue khi viết bài.
