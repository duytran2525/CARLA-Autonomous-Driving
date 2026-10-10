# Kill Search: Quét 3 cộng đồng về luận điểm CRFP

Ngày quét: 08/10/2026. Phương pháp: 3 subagent chạy song song, đọc sâu (không đọc lướt).
Luận điểm CRFP: các hệ E2E hiện tại thiếu cấu trúc điều kiện P(phản ứng môi trường | hành động ego);
CRFP điều kiện hóa theo ý định rời rạc của ego và supervise trực tiếp Δresponse (chênh lệch phản ứng).

---

## A. r/SelfDrivingCars + cộng đồng forum kỹ thuật

### Giới hạn truy cập (ghi nhận trung thực)
- `browser.search` không index nội dung Reddit; `browser.open` bị policy block toàn bộ domain reddit.com.
- Không đọc được thread r/SelfDrivingCars nào trực tiếp. Các phát hiện dưới đây từ forum/cộng đồng kỹ thuật
  lân cận mà search engine index được. Nếu cần bằng chứng trực tiếp từ subreddit, cần delegate
  cho agent có live browser.

### A1. Wayve GAIA-4 (03/08/2026) — TRỰC TIẾP, ủng hộ luận điểm
- URL: https://wayve.ai/thinking/gaia-4/
- Nội dung: world model sinh counterfactual cho simulation ("simulates the outcome when the AI Driver
  chooses to proceed rather than yield"). Nhưng chế độ mặc định **world-on-rails** được định nghĩa công khai:
  "every other agent in the scene keeps the exact behavior it showed in the real-world log.
  The other road users do not react to the ego vehicle." Extension "Reactive agents" chỉ là công cụ
  sinh scenario cho validation an toàn, không phải training objective, không điều kiện hóa theo
  intent rời rạc, không supervise Δresponse.
- Đánh giá: TRỰC TIẾP. Bằng chứng từ industry leader (2026) rằng paradigm SOTA mặc định KHÔNG mô hình
  P(phản ứng agent khác | hành động ego) — đúng luận điểm CRFP.
- Đe dọa novelty: KHÔNG (ngược lại, ủng hộ luận điểm: khoảng trống được thừa nhận công khai).

### A2. TeslaMotorsClub "Autonomous Car Progress" p.33 (2019) — TRỰC TIẾP (phát biểu vấn đề)
- URL: https://teslamotorsclub.com/tmc/threads/autonomous-car-progress.99413/page-33
- Nội dung: comment #651: "you have to be able to predict what other actors on the road are doing
  & you need to predict what they will do **as a result of your car taking a particular action**."
  Comment #653: "the challenge is to know what other vehicles/people are going to do **if you do 'x'**."
  Cả ba comment đặt vấn đề ở dạng mở/chưa giải được, không đưa giải pháp.
- Đe dọa novelty: KHÔNG (chỉ phát biểu vấn đề, không có giải pháp kỹ thuật).

### A3. TMC p.326 — trích Drago Anguelov (Waymo) — GIÁN TIẾP
- URL: https://teslamotorsclub.com/tmc/threads/autonomous-car-progress.99413/page-326
- Nội dung: "prediction and planning are interrelated since your actions will affect the actions of
  other road users but in turn their actions will affect your actions... Waymo is still working out
  the best way to combine prediction and planning together."
- Đe dọa novelty: KHÔNG (phát biểu định hướng, không phải công trình kỹ thuật).

### A4. Waymo simulation (2020) — GIÁN TIẾP
- URL: https://siliconangle.com/2020/04/28/waymo-shares-new-details-autonomous-vehicle-simulation-efforts/
- Nội dung: simulator với "reactive agents... who respond to the new position of our vehicle" —
  phục vụ huấn luyện/eval planner trong sim, không phải training objective counterfactual.
- Đe dọa novelty: KHÔNG.

### A5. M2I (MIT, 2022) — GIÁN TIẾP
- URL: https://scitechdaily.com/predicting-others-behavior-on-the-road-with-artificial-intelligence/
  (paper arXiv:2202.11884)
- Nội dung: "marginal predictor" + "conditional predictor" đoán agent nhường đường dựa trên hành động
  của agent đi trước — điều kiện hóa phản ứng theo hành động của *một agent khác* (quan hệ agent↔agent),
  không phải ego→other; không có intent rời rạc của ego hay Δresponse supervision.
- Đe dọa novelty: KHÔNG (tiền lệ gần nhất của conditional prediction nhưng sai trục).

### A6. INTERACT (arXiv 2311.12943) — GIÁN TIẾP
- URL: https://fetcher.alphaxiv.org/v2/pdf/2311.12943v4.pdf
- Nội dung: "predicts human intent conditioned on the future robot action" — đúng công thức
  P(intent | hành động robot) nhưng trong **human-robot manipulation**, không phải lái xe.
- Đe dọa novelty: KHÔNG (khác domain; đáng trích related work như tiền lệ khái niệm).

---

## B. Cộng đồng CARLA (forum + GitHub)

### B1. 🔴 ParkDiffusion++ — FLAG NOVELTY MẠNH NHẤT
- URL: https://arxiv.org/abs/2602.20923v1 (PDF: https://arxiv.org/pdf/2602.20923)
- Ngày: 02/2026
- Nội dung (đã đọc abstract + qualitative/ablation): dự đoán quỹ đạo joint đa-agent **có điều kiện theo
  ý định rời rạc của ego** cho automated parking: (1) ego intention tokenizer dự đoán tập nhỏ ý định
  endpoint rời rạc; (2) bộ dự đoán joint có điều kiện theo từng ý định; (3) safety-guided denoiser;
  (4) **counterfactual knowledge distillation** — teacher EMA + denoiser sinh pseudo-target thể hiện
  "agent khác phản ứng thế nào với ý định ego thay thế". Qualitative: khi điều kiện hóa theo ý định
  counterfactual, agent khác thể hiện hành vi phản ứng hợp lý (xe nhường tránh xung đột, người đi bộ
  nhường khi ego tăng tốc). Ablation: pcf=0.50 tốt nhất.
- Đánh giá: TRỰC TIẾP — overlap gần nhất với CRFP ở mức ý tưởng.
- Khác biệt CRFP giữ được: (a) domain bãi đỗ xe tốc độ thấp (Dragon Lake Parking + inD), không phải
  giao thông chung; (b) supervision bằng pseudo-target từ distillation, không đo trực tiếp trong
  simulator có kiểm soát; (c) không có Δresponse như đại lượng được đo và supervise trực tiếp giữa
  các ý định; (d) là mô hình diffusion dự đoán, không phải giao thức thí nghiệm nhân quả trong CARLA.
- Hành động: **bắt buộc trích related work + định vị khác biệt explicit**:
  CRFP = "đo trực tiếp bằng simulator thay vì distill pseudo-target".

### B2. "How Can Driving World Models Do Counterfactual Prediction?" (Purdue/Bosch, 08/2026) — TRỰC TIẾP (phương pháp)
- URL: https://arxiv.org/html/2608.11601v1
- Nội dung (đã đọc §1–3, §5): benchmark CARLA 186 case, mỗi case 3 arm: factual log (F),
  counterfactual ground truth (chạy lại world với ego action khác — P), null reference (U).
  Đo "recovered fraction" của world model (Vista, DrivingWorld). Điểm then chốt: paper **giả định
  explicit** rằng trong chân trời ngắn, "alternative ego action does not alter how surrounding agents
  evolve" — NPC chạy open-loop script cố định, KHÔNG phản ứng với ego.
- Đánh giá: trực giao với CRFP về đối tượng đo (họ đo thay đổi viewpoint, CRFP đo phản ứng NPC).
  Đây là bằng chứng tốt cho related work: ngay cả paper benchmark counterfactual cũng né phần
  NPC-reactive — chính là gap CRFP lấp. Thiết kế 3-arm F/P/U **đáng tham khảo cho M21**.

### B3. Simulation-Closure Framework (survey, AnXu-ITS, 30/08/2026) — TRỰC TIẾP (framing)
- URL: https://github.com/anxu-its/anxu-its.github.io/blob/HEAD/_portfolio/01-driving-world-models.md
  (SSRN working paper 7383662)
- Nội dung: formal hóa 3 chế độ feedback của simulator học được: Replay-Constrained → Ego-Responsive
  (ego đổi nhưng NPC không phản ứng) → **Traffic-Reactive** (NPC nhường/vượt/phanh theo độ lệch quỹ đạo
  counterfactual của ego). Tầng "Traffic-Response Validity" được định nghĩa bằng
  "matched counterfactual ego interventions and repeated multi-agent rollouts".
- Đánh giá: khung lý thuyết để CRFP tự định vị — CRFP là công trình đo **Traffic-Response Validity**
  bằng can thiệp ego có kiểm soát trong CARLA. Survey chỉ đặt tên tầng, không implement đo Δresponse.

### B4. Interventional Behavior Prediction (Berkeley, 2022) — GIÁN TIẾP
- URL: https://arxiv.org/pdf/2204.08665v1
- Nội dung: phân biệt CBP (điều kiện hóa theo plan tương lai của ego, ngầm giả định agent khác "biết
  trước" plan) với IBP (interventional — agent khác chỉ phản ứng theo từng timestep). Phê phán CBP
  chính là lý do CRFP phải đo phản ứng thực trong simulator thay vì điều kiện hóa mù.

### B5. IJP — Interactive Motion Planning (2023) — GIÁN TIẾP, ủng hộ motivation
- URL: http://arxiv.org/pdf/2310.18301v2
- Nội dung: tác giả thừa nhận explicit: "no supervision is added… to force the result of the subsequent
  joint optimization to match the ego-conditioned ground truth. **The main missing piece is
  counterfactual traffic data, which is not available in general.**"
- Đánh giá: bằng chứng "cộng đồng thừa nhận thiếu dữ liệu counterfactual" — CRFP sinh nó bằng CARLA.
  Trích làm motivation.

### B6. DT-Drive (Pennada et al., 2026) — GIÁN TIẾP
- URL: https://olek-osikowicz.github.io/assets/pdf/2026/pennada2026dtdrive.pdf
- Nội dung: record–modify–deterministic-replay trên CARLA; các entity khác replay đúng trajectory
  đã log (non-reactive). Có chữ "counterfactual/what-if" nhưng NPC không phản ứng.

### B7. CounterScene (arXiv 2603.21104v1) — GIÁN TIẾP
- URL: https://github.com/tydqsoft/counterscene
- Nội dung: counterfactual nhưng ngược hướng — can thiệp lên **NPC** để tạo tình huống nguy hiểm,
  không phải đo phản ứng NPC theo ý định ego.

### B8. NAVSIM v2 — reactive traffic agents (IDM) — GIÁN TIẾP
- URL: https://github.com/autonomousvision/navsim/blob/HEAD/docs/traffic_agents.md
- Nội dung: hỗ trợ traffic agent reactive (IDM) bên cạnh log-replay; issue #70 giải thích triết lý
  "phản ứng có ý nghĩa với hành vi của ego". Không phải CARLA (nuPlan-based); là harness benchmark,
  không nghiên cứu đo Δresponse.

### B9. sbrett9/carla issue #27 (~08/2026) — GIÁN TIẾP, kỹ thuật đáng chú ý
- URL: https://github.com/sbrett9/carla/issues/27
- Nội dung (đã đọc toàn issue): đo 23.5 phút ambient traffic (~50 xe): Traffic Manager đàm phán junction
  thuần hình học/đối xứng (so sánh geodesic boundary của swept path), không có khái niệm quyền ưu tiên
  hay ý định rẽ; có thể deadlock đối xứng.
- Đánh giá: bằng chứng thực nghiệm rằng NPC của CARLA TM KHÔNG có mô hình phản ứng theo ý định —
  củng cố quyết định của CRFP là script NPC thay vì trông chờ TM.

### B10. CARLA Leaderboard 2.0 / scenario_runner; Scenic NHTSA; Inverted AI; sd2 — GIÁN TIẾP
- NPC "phản ứng" dạng trigger script để **test ego** (HardBreakRoute, cut-in...), không đo phản ứng
  theo ý định ego, không có Δresponse. Inverted AI là sản phẩm thương mại tạo NPC reactive.
  justinbrianhwang/sd2 dùng counterfactual cho chẩn đoán perception, không liên quan NPC response.

### Forum / GitHub discussions — kết quả tìm kiếm
- **CARLA Discourse (carla.discourse.group):** tìm `traffic manager ego react` → **0 kết quả**.
  Không thread nào thảo luận đo phản ứng NPC hay thí nghiệm counterfactual.
- **GitHub Discussions carla-simulator/carla:** tìm `counterfactual` / `"what if" ego` → không ra
  discussion liên quan.
- **GitHub issues:** các thread về NPC reactivity đều ở dạng bug report / feature request
  (vd #8793, #9230) — cộng đồng than phiền NPC "không phản ứng" chứ không ai nghiên cứu đo phản ứng.

---

## C. Twitter/X

### Giới hạn truy cập (ghi nhận trung thực)
- Backend search không index X cho chủ đề kỹ thuật này (`site:x.com`, `site:twitter.com` → 0 kết quả).
- X chặn fetch ẩn danh; mirror xstalk lỗi upstream. Chỉ đọc đầy đủ được **1 thread** qua mirror
  threadreaderapp.com. Đây là giới hạn công cụ, không phải bằng chứng "không ai thảo luận".
- Khuyến nghị: khi có live browser hoặc X API, quét các tài khoản: @rowancheung, @_akhaliq, @ylecun,
  @Waymo, @Motional, tác giả các paper World4Drive/Drive-WM/AD-E2E-JEPA.

### C1. Thread @Christiano92 — Tesla AI Day 2021 (20/08/2021) — GIÁN TIẾP
- URL: https://threadreaderapp.com/thread/1428506761342955521.html (mirror; đã đọc toàn bộ)
- Nội dung: live-tweet Tesla AI Day. Điểm chính: "prediction" là mảng còn thiếu trong stack Tesla 2021;
  theo tác giả, Tesla chạy "FSD Planner lên các xe khác" — tức **không thực sự dự đoán xe khác sẽ làm gì**
  mà giả định xe khác hành xử như chính planner của FSD; đối lập với Waymo chạy mạng dự đoán đa mode.
- Đánh giá: chạm vào điểm mù CRFP nêu ở mức bình luận định tính (2021), không có nội dung
  counterfactual hay P(phản ứng|hành động ego). Không đe dọa novelty.

### C2. Post @Waymo (x.com/Waymo/status/1917353329547465210) — KHÔNG LIÊN QUAN
- Chỉ xác định được URL (embed trong file GitHub về cập nhật dịch vụ Waymo One); không đọc được nội dung.
  Ngữ cảnh cho thấy là tin dịch vụ/thương mại.

### Bối cảnh bổ sung ngoài X (ghi rõ nguồn, để cân nhắc)
- **Motional "nuReasoning" (Threads, 24/09/2026):** https://www.threads.com/@motionaldrive/post/Dd5OPukiG5L —
  nhãn "counterfactual reasoning" nhưng là counterfactual về **hành động của ego** (explainability),
  KHÔNG phải P(phản ứng xe khác | ý định ego). GIÁN TIẾP, không đe dọa novelty.
- **AD-E2E-JEPA (LeCun et al., arXiv 28/09/2026):** world model action-conditioned cho planning,
  không tách mô hình phản ứng agent khác theo ý định rời rạc, không supervise Δresponse. GIÁN TIẾP.
- **DTPP (arXiv 2310.05885, paper):** "Ego-conditioned prediction... predicts distinct and reasonable
  responses from interacting agents" — công trình gần nhất với khung P(others|ego plan) ở mức paper;
  khác CRFP ở chỗ không dùng ý định rời rạc + không supervise trực tiếp chênh lệch phản ứng.
  **Đáng đối chiếu khi viết related work.**

---

## D. Đánh giá đe dọa novelty — tổng hợp

| Mức | Nội dung | Lý do |
|---|---|---|
| 🔴 Cao | **ParkDiffusion++** (02/2026) | Ý định ego rời rạc + counterfactual distillation của phản ứng agent khác — overlap ý tưởng lõi. CRFP khác biệt: đo trực tiếp bằng CARLA (không distill), supervise Δresponse, domain giao thông chung (không phải parking). **Bắt buộc trích + định vị explicit.** |
| 🟡 Trung bình | **DTPP** (2023) | Ego-conditioned prediction gần nhất với khung P(others\|ego plan); khác ở không intent rời rạc, không supervise Δresponse trực tiếp. |
| 🟡 Trung bình | **Counterfactual prediction benchmark** (08/2026) | Validate phương pháp CARLA matched-counterfactual nhưng giả định NPC open-loop — bổ trợ thay vì đe dọa; trích để làm nổi bật gap. |
| 🟡 Trung bình | **CBP/IBP literature** (2021–2022) | Điều kiện hóa theo plan ego trên dữ liệu thật (không counterfactual); IJP gọi counterfactual traffic data là "missing piece" — CRFP chính là miếng ghép đó. |
| 🟢 Thấp | Còn lại | Không đo Δresponse theo ý định ego. |

**Nhận định cuối:** Không ai đang làm thí nghiệm "đo phản ứng NPC trong CARLA theo ý định rời rạc
của ego + supervise Δresponse". Hướng đi CRFP vẫn mới. Rủi ro novelty lớn nhất là ParkDiffusion++
ở mức ý tưởng (xuất bản 02/2026) — cần định vị khác biệt rõ trong paper:
**simulator-measured causal response vs distilled pseudo-targets; Δresponse supervision;
general driving domain.**

---

## E. Ý tưởng/hướng đáng tham khảo từ cộng đồng

1. **Thiết kế 3-arm F/P/U** (Purdue/Bosch counterfactual benchmark): factual log / counterfactual
   ground truth / null reference — khung matched-counterfactual sạch, đáng tham khảo cho M21.
2. **Khung "Traffic-Response Validity"** (Simulation-Closure survey): đặt tên chính xác tầng mà CRFP đo —
   dùng để định vị paper trong related work.
3. **Bằng chứng TM không có mô hình ý định** (sbrett9/carla#27): củng cố quyết định script NPC
   trong thí nghiệm CRFP; có thể trích như bằng chứng thực nghiệm.
4. **Trích dẫn IJP** ("counterfactual traffic data... not available in general") làm motivation:
   CRFP sinh chính dữ liệu đó bằng CARLA.
5. **INTERACT** (robotics): tiền lệ khái niệm P(intent|hành động robot) ngoài driving — trích related work.
6. **M2I** (MIT): tiền lệ gần nhất của conditional prediction (sai trục ego) — trích để phân biệt.

---

## F. Việc còn lại (giới hạn công cụ)
- r/SelfDrivingCars: cần live browser để đọc thread thật (reddit.com bị policy block).
- X/Twitter: cần live browser (đăng nhập) hoặc X API; threadreaderapp là mirror đọc được tốt nhất hiện tại.
- Cả hai giới hạn trên là giới hạn công cụ, không phải bằng chứng âm tính.
